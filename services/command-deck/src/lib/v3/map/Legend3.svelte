<script lang="ts">
	/**
	 * Legend3 (V3-SPEC §5.6) — three lines, because colour means only state: orange, a decision waits; a red
	 * ring, a stolen or watchlisted vehicle; teal, a protected route. Shape and words carry it too (never colour
	 * alone). Hidden at 1366 px, where the Now list says the same in words. While their layers are on, two more:
	 * sky, a road at waterlogging risk (the hydro nowcast, modelled); white dashes, a road forecast over 0.8 V/C. And
	 * while the city-feed layers are on: the air-quality sites on the band ladder (green · amber · red · black, larger
	 * when worse), and the cyclone track with its bearing marker ($lib/cityfeeds).
	 */
	import { t } from '$lib/i18n/strings';
	import Glyph from '../Glyph.svelte';
	import './packs.map3';
	import '$lib/ai/packs.ai';
	import '$lib/cityfeeds/packs.feeds';

	let {
		lang,
		hideLabel = null,
		onhide = null,
		water = false,
		forecast = false,
		air = false,
		cyclone = false,
	}: { lang: string; hideLabel?: string | null; onhide?: (() => void) | null; water?: boolean; forecast?: boolean; air?: boolean; cyclone?: boolean } = $props();
</script>

<div class="lg v3-glass" role="note" aria-label={t(lang, 'v3m_legend')} data-testid="v3-legend" data-ge-keepout>
	<span><i class="dot" aria-hidden="true"></i>{t(lang, 'v3m_lg_decide')}</span>
	<span><i class="ring" aria-hidden="true"></i>{t(lang, 'v3m_lg_alert')}</span>
	<span><i class="bar" aria-hidden="true"></i>{t(lang, 'v3m_lg_route')}</span>
	{#if water}<span data-legend="water"><i class="water" aria-hidden="true"></i>{t(lang, 'ai_lg_water')}</span>{/if}
	{#if forecast}<span data-legend="forecast"><i class="fcast" aria-hidden="true"></i>{t(lang, 'ai_lg_forecast')}</span>{/if}
	{#if air}<span data-legend="air"><i class="aq" aria-hidden="true"><b class="g"></b><b class="a"></b><b class="r"></b><b class="k"></b></i>{t(lang, 'cf_lg_air')}</span>{/if}
	{#if cyclone}<span data-legend="cyclone"><i class="cyc" aria-hidden="true"></i>{t(lang, 'cf_lg_cyclone')}</span>{/if}
	{#if onhide}<button type="button" class="x" aria-label={hideLabel} title={hideLabel} onclick={onhide}><Glyph name="close" size={14} /></button>{/if}
</div>

<style>
	.lg {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 10px 14px;
		border: 1px solid var(--v3-glass-border);
		border-radius: var(--v3-radius-m);
		background: var(--v3-glass-surface);
		box-shadow: var(--v3-elev-1);
		color: var(--v3-t2);
		font-size: var(--v3-text-micro);
		line-height: var(--v3-lh-micro);
		pointer-events: auto;
	}

	span {
		display: flex;
		align-items: center;
		gap: 8px;
		white-space: nowrap;
	}

	.water {
		display: inline-block;
		width: 16px;
		height: 5px;
		border-radius: 3px;
		background: var(--v-map-water);
	}

	.fcast {
		display: inline-block;
		width: 16px;
		height: 0;
		border-top: 3px dashed var(--v3-t1);
	}

	.aq {
		display: inline-flex;
		align-items: center;
		gap: 2px;
	}

	.aq b {
		display: inline-block;
		border-radius: 50%;
	}

	.aq .g {
		width: 6px;
		height: 6px;
		background: var(--v-band-green);
	}

	.aq .a {
		width: 8px;
		height: 8px;
		background: var(--v-band-amber);
	}

	.aq .r {
		width: 10px;
		height: 10px;
		background: var(--v-band-red);
	}

	.aq .k {
		width: 12px;
		height: 12px;
		background: var(--v-band-black-fill);
		box-shadow: 0 0 0 1px var(--v-band-black-hairline);
	}

	.cyc {
		width: 16px;
		height: 4px;
		border-radius: 2px;
		background: var(--v-band-red);
	}

	.x {
		position: absolute;
		top: 4px;
		right: 4px;
		display: grid;
		place-items: center;
		width: 22px;
		height: 22px;
		border: 0;
		border-radius: 11px;
		background: none;
		color: var(--v3-t2);
		cursor: pointer;
	}

	.x:hover {
		background: var(--v3-s3);
	}

	.x:focus-visible {
		outline: 2px solid var(--v3-brand);
		outline-offset: 2px;
	}

	.lg:has(.x) {
		padding-right: 32px;
	}

	i {
		display: inline-block;
		flex: none;
	}

	.dot {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: var(--v3-decide);
	}

	.ring {
		width: 12px;
		height: 12px;
		border: 3px solid var(--v3-alert);
		border-radius: 50%;
		box-sizing: border-box;
	}

	.bar {
		width: 16px;
		height: 4px;
		border-radius: 2px;
		background: var(--v3-route);
	}
</style>
