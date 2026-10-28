<script lang="ts">
	/**
	 * A camera's road state (PLAN §2.4 D) on its object page: no live CCTV frame reaches Sahoshi, so the officer reads a
	 * credited SAMPLE still ("Sample still · not live") or uploads one, and the on-premises vision model answers the road
	 * state — waterlogged, blocked, tree fall, stalled vehicle, crash debris, congested, clear — with its own (uncalibrated)
	 * confidence, a water-depth band read against wheels and kerbs, a rough vehicle count and a short rationale, labelled
	 * UNVERIFIED-CAMERA. "Send to the board" creates one unverified camera report (field/board.ts) for an officer to
	 * confirm. Roads and vehicles only: the page never asks about people, and the service refuses if anything does.
	 * The still is read from memory and never stored.
	 */
	import { onDestroy, untrack } from 'svelte';
	import { t } from '$lib/i18n/strings';
	import { inBox } from '$lib/city';
	import type { ObjectRow } from '$lib/workspace/types';
	import Glyph from '../Glyph.svelte';
	import { loadSegments } from '../public/geometry';
	import '../field/packs.field';
	import '../field/packs.field.core';
	import { FieldApiError, readRoadState } from '../field/api';
	import { writeBoardEntry } from '../field/board';
	import { boardDraftFromReading, nearestSegment, officerOf, sendableState, VEHICLE_KEYS, type RoadState } from '../field/model';
	import { SAMPLE_STILLS, sampleFor, type SampleStill } from '../field/samples';
	import Panel from './Panel.svelte';

	let { row, lang, officer }: { row: ObjectRow; lang: string; officer: string | null } = $props();
	const L = (key: string, ...args: unknown[]) => t(lang, key, ...args);

	const GLYPH: Record<string, string> = {
		waterlogged: 'wave',
		blocked: 'cone',
		tree_fall: 'alert',
		stalled_vehicle: 'car',
		crash_debris: 'alert',
		congested: 'car',
		clear: 'checkc',
		unknown: 'info',
	};
	const VEH_ART: Record<string, string> = { cars: 'car', buses: 'bus', two_wheelers: 'two_wheeler', autos: 'auto_rickshaw' };

	// the page is keyed by its URN, so the camera never changes under this panel
	let sample = $state<SampleStill>(untrack(() => sampleFor(row.id)));
	let upload = $state<{ url: string; blob: Blob } | null>(null);
	let phase = $state<'idle' | 'reading' | 'done'>('idle');
	let reading = $state<RoadState | null>(null);
	let refusal = $state<string | null>(null);
	let problem = $state<string | null>(null);
	let send = $state<{ state: 'idle' | 'sending' | 'sent' | 'error'; eventId?: string; detail?: string }>({ state: 'idle' });
	let fileInput = $state<HTMLInputElement | null>(null);
	let ctl: AbortController | null = null;

	const who = $derived(officerOf(officer));
	const src = $derived(upload?.url ?? sample.src);
	const segId = $derived(typeof row.props.segment_id === 'number' ? (row.props.segment_id as number) : null);

	function choose(s: SampleStill) {
		if (phase === 'reading') return;
		if (upload) URL.revokeObjectURL(upload.url);
		upload = null;
		sample = s;
		clear();
	}

	function clear() {
		reading = null;
		refusal = null;
		problem = null;
		phase = 'idle';
		send = { state: 'idle' };
	}

	function onFile(e: Event) {
		const f = (e.currentTarget as HTMLInputElement).files?.[0];
		(e.currentTarget as HTMLInputElement).value = '';
		if (!f) return;
		if (f.type !== 'image/jpeg' && f.type !== 'image/png') {
			problem = L('fld_rs_bad_image');
			return;
		}
		if (upload) URL.revokeObjectURL(upload.url);
		upload = { url: URL.createObjectURL(f), blob: f };
		clear();
	}

	async function read() {
		if (phase === 'reading') return;
		ctl?.abort();
		ctl = new AbortController();
		clear();
		phase = 'reading';
		try {
			const blob = upload ? upload.blob : await (await fetch(sample.src, { signal: ctl.signal })).blob();
			const ans = await readRoadState(blob.type ? blob : new Blob([blob], { type: 'image/jpeg' }), ctl.signal);
			if (ans.ok) reading = ans.reading;
			else refusal = ans.reason || L('fld_rs_refused');
			phase = 'done';
		} catch (err) {
			if (err instanceof DOMException && err.name === 'AbortError') return;
			phase = 'idle';
			problem = err instanceof FieldApiError && err.kind === 'busy' ? L('fld_rs_busy') : err instanceof FieldApiError && err.status === 415 ? L('fld_rs_bad_image') : L('fld_failed');
		}
	}

	async function toBoard() {
		if (!reading || !who || send.state === 'sending' || send.state === 'sent') return;
		send = { state: 'sending' };
		try {
			let seg = segId;
			if (seg === null && row.lon !== null && row.lat !== null) seg = nearestSegment([row.lon, row.lat], [...(await loadSegments()).values()])?.segmentId ?? null;
			if (seg === null) {
				send = { state: 'error', detail: L('fld_no_road') };
				return;
			}
			const draft = boardDraftFromReading(
				reading,
				{ id: row.id, label: row.sublabel ? `${row.sublabel} (${row.id})` : row.label, lon: row.lon, lat: row.lat, sample: upload ? null : sample.id },
				seg,
				who,
				Date.now(),
				row.lon !== null && row.lat !== null && inBox(row.lon, row.lat),
			);
			if (!draft) return;
			const out = await writeBoardEntry(draft);
			send = { state: 'sent', eventId: out.eventId };
		} catch (err) {
			send = { state: 'error', detail: L('fld_send_failed', err instanceof FieldApiError ? err.detail : String(err)) };
		}
	}

	onDestroy(() => {
		ctl?.abort();
		if (upload) URL.revokeObjectURL(upload.url);
	});
</script>

<Panel title={L('fld_rs_title')} testid="obj-road-state" data-phase={phase} data-state={reading?.state ?? ''}>
	<div class="rs">
		<div class="grid">
		<div class="left">
			<figure class={['still', phase === 'reading' && 'scanning']}>
				<img {src} alt={upload ? L('fld_rs_uploaded') : sample.caption} width="1024" height="682" decoding="async" />
				<span class="chip" data-label="SAMPLE"><Glyph name={upload ? 'eyeoff' : 'flask'} size={14} />{upload ? L('fld_rs_uploaded') : L('fld_rs_sample')}</span>
				{#if phase === 'reading'}<span class="scan" aria-hidden="true"></span><span class="busy"><span class="spin light" aria-hidden="true"></span>{L('fld_rs_reading')}</span>{/if}
				{#if !upload}<figcaption>{L('fld_rs_credit', sample.author, sample.licence)} · <a href={sample.source} target="_blank" rel="noopener noreferrer">Wikimedia Commons</a></figcaption>{/if}
			</figure>
			<div class="strip" role="group" aria-label={L('fld_rs_pick')}>
				{#each SAMPLE_STILLS as s (s.id)}
					<button type="button" class={['th', !upload && sample.id === s.id && 'is-selected']} aria-pressed={!upload && sample.id === s.id} onclick={() => choose(s)} title={s.caption} disabled={phase === 'reading'}>
						<img src={s.src} alt={s.caption} width="96" height="64" loading="lazy" decoding="async" />
					</button>
				{/each}
				<button type="button" class={['th', 'up', upload && 'is-selected']} onclick={() => fileInput?.click()} disabled={phase === 'reading'} aria-label={L('fld_rs_upload')} title={L('fld_rs_upload')} data-testid="rs-upload">
					<Glyph name="plus" size={18} /><span>{L('fld_rs_upload_short')}</span>
				</button>
				<input bind:this={fileInput} type="file" accept="image/jpeg,image/png" hidden onchange={onFile} />
			</div>
		</div>

		<div class="answer" aria-live="polite">
			{#if reading}
				<div class="state" data-state={reading.state}>
					<span class={['ico', `s-${reading.state}`]}><Glyph name={GLYPH[reading.state] ?? 'info'} size={26} /></span>
					<div>
						<b class="name">{L(`fld_state_${reading.state}`)}</b>
						<span class="tag" data-label="UNVERIFIED-CAMERA"><Glyph name="unverified" size={14} />{L('fld_tag_camera')}</span>
					</div>
				</div>
				{#if reading.confidence !== null}
					<div class="conf" title={L('fld_rs_conf_note')}>
						<div class="bar"><i style:width={`${Math.round(reading.confidence * 100)}%`}></i></div>
						<span class="fig">{L('fld_rs_conf', reading.confidence.toFixed(2))}</span>
					</div>
					<p class="meta">{L('fld_rs_conf_note')}</p>
				{/if}
				{#if reading.depth && reading.depth !== 'none'}
					<p class="kv"><span class="k">{L('fld_rs_depth')}</span><b>{L(`fld_depth_${reading.depth}`)}</b></p>
				{/if}
				<div class="veh">
					<span class="k">{L('fld_rs_vehicles')}</span>
					<ul>
						{#each VEHICLE_KEYS as k (k)}
							<li>
								<img src={`/illustrations/vehicles/${VEH_ART[k]}.svg`} alt="" width="40" height="24" />
								<b class="fig">{reading.vehicles[k] ?? '—'}</b>
								<span>{L(`fld_veh_${k}`)}</span>
							</li>
						{/each}
					</ul>
				</div>
				{#if reading.rationale}
					<blockquote lang="en"><span class="k">{L('fld_rs_rationale')}</span>{reading.rationale}</blockquote>
				{/if}
				{#if reading.filtered}<p class="meta">{L('fld_rs_filtered')}</p>{/if}
				{#if reading.model}<p class="meta fig">{L('fld_rs_model', reading.model, (reading.latencyS ?? 0).toFixed(1))}</p>{/if}

				{#if send.state === 'sent'}
					<div class="sent" role="status" data-testid="rs-sent"><Glyph name="checkc" size={20} /><span>{L('fld_sent')}</span><a href={`/o/event:${send.eventId}`}>{L('fld_open')}</a></div>
				{:else if sendableState(reading.state)}
					<button type="button" class="primary" disabled={!who || send.state === 'sending'} title={who ? undefined : L('fld_need_officer')} onclick={() => void toBoard()} data-testid="rs-send">
						<Glyph name="send" size={18} />{send.state === 'sending' ? L('fld_sending') : L('fld_send_board')}
					</button>
					<p class="meta">{L('fld_rs_send')}</p>
					{#if !who}<p class="meta">{L('fld_need_officer')}</p>{/if}
					{#if send.state === 'error'}<p class="problem" role="alert">{send.detail}</p>{/if}
				{:else}
					<p class="meta">{L('fld_rs_nothing')}</p>
				{/if}
				<button type="button" class="ghost again" onclick={() => void read()}><Glyph name="spark" size={18} />{L('fld_rs_read')}</button>
			{:else if refusal}
				<div class="refused" data-testid="rs-refused"><Glyph name="shield" size={20} /><div><b>{L('fld_rs_refused')}</b><p>{refusal}</p></div></div>
			{:else}
				<div class="cta">
					<span class="ico big"><Glyph name="spark" size={28} /></span>
					<p>{L('fld_rs_no_live')}</p>
					<button type="button" class="primary" onclick={() => void read()} disabled={phase === 'reading'} data-testid="rs-read">
						{#if phase === 'reading'}<span class="spin" aria-hidden="true"></span>{L('fld_rs_reading')}{:else}<Glyph name="spark" size={18} />{L('fld_rs_read')}{/if}
					</button>
					{#if problem}<p class="problem" role="alert">{problem}</p>{/if}
				</div>
			{/if}
		</div>
		</div>
	</div>

	<p class="rule"><Glyph name="shield" size={16} />{L('fld_rs_rule')} {L('fld_rs_modelled_site')}</p>
</Panel>

<style>
	.rs {
		container-type: inline-size;
	}

	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(280px, 1fr);
		gap: 22px;
		align-items: start;
	}

	.left {
		display: flex;
		flex-direction: column;
		gap: 10px;
		min-width: 0;
	}

	.still {
		position: relative;
		margin: 0;
		overflow: hidden;
		border-radius: var(--v3-radius-m);
		background: var(--v3-s2);
	}

	.still img {
		display: block;
		width: 100%;
		height: auto;
		aspect-ratio: 3 / 2;
		object-fit: cover;
		transition: filter var(--v3-dur-3) var(--v3-ease);
	}

	.still.scanning img {
		filter: saturate(0.5) brightness(0.62);
	}

	.busy {
		position: absolute;
		left: 50%;
		top: 50%;
		display: inline-flex;
		align-items: center;
		gap: 10px;
		padding: 10px 16px;
		border-radius: 20px;
		background: var(--v3-glass);
		color: var(--v3-t1);
		font-size: 14px;
		font-weight: 650;
		transform: translate(-50%, -50%);
	}

	.chip {
		position: absolute;
		top: 12px;
		left: 12px;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		height: 28px;
		padding: 0 12px;
		border: 1px dashed var(--v3-line-3);
		border-radius: 14px;
		background: var(--v3-glass);
		color: var(--v3-t1);
		font-size: var(--v3-text-meta);
		font-weight: 650;
	}

	.scan {
		position: absolute;
		left: 0;
		right: 0;
		top: 0;
		height: 2px;
		background: var(--v3-brand);
		box-shadow: 0 0 18px 6px var(--v3-brand-veil), 0 0 2px 1px var(--v3-brand);
		animation: scan 2.2s ease-in-out infinite alternate;
	}

	@keyframes scan {
		from {
			top: 2%;
		}
		to {
			top: 96%;
		}
	}

	figcaption {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		padding: 18px 12px 8px;
		background: linear-gradient(180deg, var(--v3-photo-scrim-none), var(--v3-photo-scrim));
		color: var(--v3-photo-ink);
		font-size: var(--v3-text-micro);
		line-height: var(--v3-lh-micro);
	}

	figcaption a {
		color: inherit;
	}

	.answer {
		display: flex;
		flex-direction: column;
		gap: 12px;
		min-width: 0;
	}

	.state {
		display: flex;
		align-items: center;
		gap: 14px;
		animation: rise var(--v3-dur-3) var(--v3-ease);
	}

	@keyframes rise {
		from {
			transform: translateY(6px);
			opacity: 0;
		}
	}

	.ico {
		display: grid;
		place-items: center;
		flex: none;
		width: 52px;
		height: 52px;
		border-radius: 50%;
		background: var(--v3-s3);
		color: var(--v3-t1);
	}

	.ico.s-waterlogged {
		background: var(--v3-brand-veil);
		color: var(--v3-brand-text);
	}

	.ico.s-clear {
		background: var(--v3-ok-veil);
		color: var(--v3-ok-text);
	}

	.ico.big {
		width: 60px;
		height: 60px;
		background: var(--v3-ai-veil);
		color: var(--v3-ai-text);
	}

	.name {
		display: block;
		font-size: var(--v3-text-title);
		line-height: var(--v3-lh-title);
		font-weight: 700;
	}

	.tag {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		margin-top: 4px;
		height: 26px;
		padding: 0 10px;
		border: 1px dashed var(--v3-dashed);
		border-radius: 13px;
		color: var(--v3-t2);
		font-size: var(--v3-text-meta);
		font-weight: 650;
	}

	.conf {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.bar {
		flex: 1;
		height: 6px;
		overflow: hidden;
		border-radius: 3px;
		background: var(--v3-s3);
	}

	.bar i {
		display: block;
		height: 100%;
		border-radius: 3px;
		background: var(--v3-t1);
		animation: grow var(--v3-dur-3) var(--v3-ease);
	}

	@keyframes grow {
		from {
			width: 0;
		}
	}

	.fig {
		font-variant-numeric: tabular-nums;
	}

	.meta {
		margin: 0;
		color: var(--v3-t3);
		font-size: var(--v3-text-meta);
		line-height: var(--v3-lh-meta);
	}

	.k {
		display: block;
		color: var(--v3-t3);
		font-size: var(--v3-text-meta);
		font-weight: 650;
	}

	.kv {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 10px;
		margin: 0;
		padding: 10px 12px;
		border-radius: var(--v3-radius-s);
		background: var(--v3-s2);
	}

	.veh ul {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 8px;
		margin: 6px 0 0;
		padding: 0;
		list-style: none;
	}

	.veh li {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 2px;
		padding: 10px;
		border-radius: var(--v3-radius-s);
		background: var(--v3-s2);
		font-size: var(--v3-text-micro);
		line-height: var(--v3-lh-micro);
		color: var(--v3-t2);
	}

	.veh img {
		height: 22px;
		width: auto;
		opacity: 0.9;
	}

	.veh b {
		color: var(--v3-t1);
		font-size: var(--v3-text-heading);
		line-height: var(--v3-lh-heading);
	}

	blockquote {
		margin: 0;
		padding: 10px 14px;
		border-left: 3px solid var(--v3-line-3);
		color: var(--v3-t1);
		font-size: 14px;
		line-height: 20px;
	}

	.primary,
	.ghost {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		min-height: var(--v3-ctl-lg);
		padding: 0 18px;
		border-radius: 22px;
		font: inherit;
		font-weight: 650;
		cursor: pointer;
	}

	.primary {
		border: none;
		background: var(--v3-primary-bg);
		color: var(--v3-primary-ink);
	}

	.primary:hover:not(:disabled) {
		background: var(--v3-primary-hover);
	}

	.primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.ghost {
		align-self: flex-start;
		border: 1px solid var(--v3-line-3);
		background: none;
		color: var(--v3-t1);
	}

	.ghost:hover {
		background: var(--v3-s3);
	}

	.cta {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 14px;
		padding: 8px 0;
	}

	.cta p {
		margin: 0;
		color: var(--v3-t2);
	}

	.spin {
		width: 16px;
		height: 16px;
		border: 2px solid var(--v3-line-3);
		border-top-color: var(--v3-primary-ink);
		border-radius: 50%;
		animation: spin 0.9s linear infinite;
	}

	.spin.light {
		border-top-color: var(--v3-t1);
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.refused {
		display: flex;
		gap: 12px;
		padding: 14px;
		border-radius: var(--v3-radius-m);
		background: var(--v3-s2);
	}

	.refused p {
		margin: 4px 0 0;
		color: var(--v3-t2);
	}

	.problem {
		margin: 0;
		padding: 10px 12px;
		border-radius: var(--v3-radius-s);
		background: var(--v3-s2);
		font-size: 14px;
	}

	.sent {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 14px;
		border-radius: var(--v3-radius-m);
		background: var(--v3-ok-veil);
		color: var(--v3-ok-text);
		font-weight: 650;
	}

	.sent span {
		flex: 1;
	}

	.sent a {
		color: var(--v3-t1);
	}

	.strip {
		display: grid;
		grid-template-columns: repeat(7, minmax(0, 1fr));
		gap: 8px;
	}

	.th {
		min-width: 0;
		aspect-ratio: 3 / 2;
		height: auto;
		padding: 0;
		overflow: hidden;
		border: 2px solid transparent;
		border-radius: var(--v3-radius-s);
		background: var(--v3-s2);
		cursor: pointer;
		opacity: 0.72;
		transition: opacity var(--v3-dur-1) var(--v3-ease), border-color var(--v3-dur-1) var(--v3-ease);
	}

	.th img {
		display: block;
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.th:hover {
		opacity: 1;
	}

	.th.is-selected {
		border-color: var(--v3-t1);
		opacity: 1;
	}

	.th.up {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 2px;
		border: 1px dashed var(--v3-line-3);
		color: var(--v3-t2);
		font: inherit;
		font-size: 11px;
		line-height: 13px;
		text-align: center;
		opacity: 1;
	}

	.th.up span {
		overflow: hidden;
		max-width: 100%;
		padding: 0 2px;
	}

	.th:focus-visible,
	.primary:focus-visible,
	.ghost:focus-visible {
		outline: 2px solid var(--v3-brand);
		outline-offset: 2px;
	}

	.rule {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		margin: 0;
		color: var(--v3-t2);
		font-size: var(--v3-text-meta);
		line-height: var(--v3-lh-meta);
	}

	.rule :global(.v3-glyph) {
		flex: none;
		margin-top: 1px;
		color: var(--v3-t3);
	}

	@container (max-width: 720px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.scan,
		.state,
		.bar i,
		.spin {
			animation: none;
		}
	}
</style>
