/**
 * air layer — the ten WBPCB/CPCB air-quality monitoring sites, each banded by India's National AQI (indicative).
 *
 * Data: GET /api/cityfeeds/feeds/air (services/cityfeeds through the deck proxy), every 10 min with back-off. The
 * values are Open-Meteo's air-quality model (CAMS) at the sites, not the stations' own readings; the National AQI is
 * CPCB's breakpoint table applied to the modelled 24-hour PM2.5 and PM10 means (INDICATIVE). Each pick text says so.
 *
 * SYMBOLOGY (colour only for meaning, no new colour token): the EXISTING band ladder — Good and Satisfactory
 * --v-band-green, Moderate --v-band-amber, Poor and Very poor --v-band-red, Severe --v-band-black-fill with the
 * --v-band-black-hairline ring ($lib/cityfeeds/model TONE_TOKEN) — on a dot that ALSO grows with the band
 * (airRadius: 8 px Good … 18 px Severe, so the meaning never rides on colour alone), a soft 450 m veil of the same
 * band under it, and a label "AQI 62". It never reads --v-act, --v-data or --v-tool.
 *
 * Pick ids `aq:<site id>` → URN `place:aq_<site id>` (an air-quality site is a place, never a person).
 */

import type { GodsEyeLayer, GodsEyeLayerContext, GodsEyeLayerInstance } from '../registry';
import { DRAPE_Z, clampedDot, clampedLabel, drapeAudit, drapedEllipse, ground } from './draping';
import { canvasFont, cssVar } from '../theme';
import { inkAlpha, mapInk } from '../hud/map/symbols';
import { createPoller, type Poller } from '$lib/ai/poll';
import { getAir } from '$lib/cityfeeds/client';
import { TONE_TOKEN, airRadius, toneOf, worstBandIndex } from '$lib/cityfeeds/model';
import type { AirView } from '$lib/cityfeeds/types';

export const AIR_PICK_PREFIX = 'aq:';

/** The band ladder's fallbacks (Cesium needs a colour even before the tokens resolve; never a new palette). */
const FALLBACK: Record<string, string> = { '--v-band-green': 'seagreen', '--v-band-amber': 'goldenrod', '--v-band-red': 'indianred', '--v-band-black-fill': 'black', '--v-band-black-hairline': 'indianred', '--v-map-marker': 'gray' };

function createAirLayer(): GodsEyeLayerInstance {
	let ctx: GodsEyeLayerContext | null = null;
	let active = false;
	let poller: Poller | null = null;
	let air: AirView | null = null;
	let feed: 'loading' | 'ok' | 'down' | 'not-deployed' = 'loading';
	let lastSig = '';
	const ids: string[] = [];
	let hint = 'loading air quality';
	let detail: Record<string, number> = {};

	const ink = (token: string) => cssVar(token) || FALLBACK[token] || 'gray';

	function draw() {
		if (!ctx || !active) return;
		const { cesium, viewer } = ctx;
		const stations = air?.stations ?? [];
		const sig = JSON.stringify([stations.map((s) => [s.id, s.naqi?.aqi ?? null, s.naqi?.band ?? null]), ink('--v-band-green'), ink('--v-band-red')]);
		if (sig === lastSig) return;
		lastSig = sig;
		for (const id of ids) viewer.entities.removeById(id);
		ids.length = 0;
		const labelInk = cesium.Color.fromCssColorString(mapInk('label-ink'));
		const halo = cesium.Color.fromCssColorString(mapInk('casing'));
		for (const s of stations) {
			const band = s.naqi?.band ?? null;
			const tok = TONE_TOKEN[toneOf('air', band)];
			const fill = ink(tok.fill);
			const ring = tok.ring ? ink(tok.ring) : mapInk('casing');
			const veil = viewer.entities.add({
				id: `${AIR_PICK_PREFIX}veil-${s.id}`,
				position: ground(cesium, s.lon, s.lat),
				ellipse: drapedEllipse(cesium, { radiusM: 450, material: cesium.Color.fromCssColorString(inkAlpha(fill, 0.2)), z: DRAPE_Z.zone }),
			});
			ids.push(veil.id);
			const aqiText = s.naqi ? `AQI ${s.naqi.aqi}` : 'AQI —';
			const pm = s.pm25_24h != null ? ` PM2.5 24-hour mean ${s.pm25_24h} µg/m³, PM10 ${s.pm10_24h ?? '—'} µg/m³.` : '';
			const entity = viewer.entities.add({
				id: `${AIR_PICK_PREFIX}${s.id}`,
				position: ground(cesium, s.lon, s.lat),
				billboard: clampedDot(cesium, { pixelSize: airRadius(band) * 2, color: cesium.Color.fromCssColorString(fill), outlineColor: cesium.Color.fromCssColorString(ring), outlineWidth: 2 }),
				label: clampedLabel(cesium, {
					text: aqiText,
					font: canvasFont('600 12px var(--v-font-ui)'),
					fillColor: labelInk,
					outlineColor: halo,
					outlineWidth: 3,
					style: 2,
					verticalOrigin: 1,
					pixelOffset: new cesium.Cartesian2(0, -(airRadius(band) + 6)),
				}),
				description: `Air quality at ${s.name}: indicative National AQI ${s.naqi ? `${s.naqi.aqi}, ${s.naqi.band_en}` : 'unavailable'} (CPCB bands on modelled values, not the station's own reading).${pm} Model: Open-Meteo air-quality (CAMS). Site position: ${s.coord_source}.`,
			});
			ids.push(entity.id);
		}
		const worst = worstBandIndex(stations.map((s) => s.naqi?.band));
		detail = { sites: stations.length, worst_band: worst, drawn: stations.length };
		if (feed === 'not-deployed') hint = 'air quality feed not deployed on this deck';
		else if (feed === 'down' && !air) hint = 'air quality feed unreachable — nothing drawn';
		else if (!air) hint = 'loading air quality';
		else hint = `${stations.length} sites, indicative National AQI (modelled; CPCB bands)${air.city ? `, worst ${air.city.aqi} ${air.city.band_en} at ${air.city.worst_site_name}` : ''}`;
	}

	return {
		async status() {
			return { configured: true };
		},
		init(layerCtx) {
			ctx = layerCtx;
		},
		activate() {
			active = true;
			poller = createPoller(
				async () => {
					try {
						air = await getAir();
						feed = 'ok';
					} catch (err) {
						feed = err instanceof Error && err.name === 'AiNotDeployed' ? 'not-deployed' : 'down';
						throw err;
					} finally {
						lastSig = '';
						draw();
						ctx?.notify();
					}
				},
				{ baseMs: 600_000 },
			);
			poller.start();
			draw();
		},
		deactivate() {
			active = false;
			poller?.stop();
			poller = null;
			if (ctx) for (const id of ids) ctx.viewer.entities.removeById(id);
			ids.length = 0;
			lastSig = '';
			detail = {};
		},
		refresh() {
			lastSig = '';
			poller?.kick();
			draw();
		},
		restyle() {
			lastSig = '';
			draw();
		},
		handlePick(pickId) {
			return pickId.startsWith(AIR_PICK_PREFIX);
		},
		urnOf(pickId) {
			const id = pickId.slice(AIR_PICK_PREFIX.length);
			return /^[a-z_]+$/.test(id) ? `place:aq_${id}` : null;
		},
		coverageStats() {
			return {
				count: detail.sites ?? 0,
				loading: feed === 'loading',
				hint,
				error: feed === 'down' && !air ? 'air quality feed down' : null,
				detail: ctx ? { ...detail, ...drapeAudit(ctx.viewer, ids) } : detail,
				via: 'cityfeeds/air',
			};
		},
		destroy() {
			this.deactivate();
		},
	};
}

export const airLayer: GodsEyeLayer = {
	id: 'air',
	name: 'Air quality (National AQI, modelled)',
	label: 'AIR',
	requiresKeyId: null,
	pickPrefix: AIR_PICK_PREFIX,
	defaultOn: false,
	group: 'intelligence',
	create: createAirLayer,
};
