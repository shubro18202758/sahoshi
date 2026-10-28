/**
 * showcase/console_shots.mjs — the README / deck / evidence screenshot set, taken on the running deck.
 *
 *   node scripts/showcase/console_shots.mjs [--origin http://127.0.0.1:5373] [--out docs/screenshots]
 *        [--only home,map-3d] [--signin 'Demo duty officer'] [--list]
 *
 * NOT a test: a camera. Each shot opens one page of the deck (console pages at 1440 × 900 in a signed-in
 * context; the public pages /citizen and /driver at 390 × 844 in a separate, anonymous context), optionally
 * sets the language cookie (sahoshi_lang: bn | en | hi), performs the shot's few clicks (open a layer, start the
 * 23 Sep 2025 replay, hold the mic), waits for the page to settle and saves a JPEG (quality 88). Nothing is
 * edited afterwards.
 *
 * SAFETY (the live deck, :5373): every non-GET /api/* request is answered 503 here and never reaches the deck,
 * except the on-premises AI services' compute calls (speech, vision, twin, hydro replay, forecast refresh), the
 * assistant's chat turn, the flow layer's live read (a POST) and the session itself — the shots can never write
 * the live city (no approval, no dispatch, no event, no plan is ever sent). Response
 * bodies are never logged (the signed-in /gods-eye/mode answer carries the ion token). The operator PIN is read
 * at run time by scripts/lib/deck_session.mjs and never printed.
 *
 * Exit: 0 every requested shot saved; 1 any shot failed (the others are still saved).
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { puppeteerCookies, signIn, signOut } from '../lib/deck_session.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const require = createRequire(path.join(ROOT, 'frontend', 'package.json'));
const puppeteer = require('puppeteer-core');
const CHROME = process.env.CHROME_PATH
	|| `${process.env.HOME}/.cache/puppeteer/chrome/linux_arm-153.0.8010.36/chrome-linux-arm64/chrome`;

const argv = process.argv.slice(2);
const opt = (name, dflt) => {
	const i = argv.indexOf(name);
	return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : dflt;
};
const ORIGIN = opt('--origin', 'http://127.0.0.1:5373').replace(/\/+$/, '');
const OUT = path.resolve(opt('--out', path.join(ROOT, 'docs', 'screenshots')));
const ONLY = opt('--only', '').split(',').map((s) => s.trim()).filter(Boolean);
const OFFICER = opt('--signin', 'Demo duty officer');
/** A WAV the fake microphone plays (the voice-report shot: a synthetic Bengali report from the speech service's TTS). */
const AUDIO = opt('--fake-audio', null);
const LIVE = new URL(ORIGIN).port === '5373';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const CONSOLE = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true };

// ── helpers the shots use ──────────────────────────────────────────────────
/** Click the first element whose visible text matches (a button, link, tab or chip). */
async function clickText(page, re, { selector = 'button, a, [role="tab"], [role="button"], label, summary', timeout = 15000 } = {}) {
	const src = re.source;
	const flags = re.flags;
	const t0 = Date.now();
	while (Date.now() - t0 < timeout) {
		const ok = await page.evaluate((sel, s, f) => {
			const rx = new RegExp(s, f);
			const els = [...document.querySelectorAll(sel)].filter((e) => {
				const r = e.getBoundingClientRect();
				return r.width > 0 && r.height > 0 && rx.test((e.innerText || e.getAttribute('aria-label') || e.title || '').trim());
			});
			if (!els.length) return false;
			els[0].scrollIntoView({ block: 'center' });
			els[0].click();
			return true;
		}, selector, src, flags);
		if (ok) return true;
		await sleep(500);
	}
	throw new Error(`no clickable element matching ${re}`);
}

/** Wait until the page's text matches (or the timeout passes — then the shot is still taken, and flagged). */
async function waitText(page, re, timeout = 30000) {
	const t0 = Date.now();
	while (Date.now() - t0 < timeout) {
		const hit = await page.evaluate((s, f) => new RegExp(s, f).test(document.body?.innerText || ''), re.source, re.flags).catch(() => false);
		if (hit) return true;
		await sleep(700);
	}
	return false;
}

/** Wait for the God's-eye photoreal tiles (the canvas reports them on window.__GODS_EYE__). */
async function waitTiles(page, timeout = 150000) {
	const t0 = Date.now();
	while (Date.now() - t0 < timeout) {
		const s = await page.evaluate(() => {
			const g = window.__GODS_EYE__ || {};
			const p3d = g.layerStats?.['photoreal-3d'] ?? null;
			return { via: p3d?.via ?? null, loaded: p3d?.initialTilesLoaded ?? p3d?.detail?.initialTilesLoaded ?? null };
		}).catch(() => null);
		if (s && s.via === 'ion' && s.loaded === 1) return true;
		await sleep(3000);
	}
	return false;
}

/** Build a /gods-eye share hash (share-link.ts v=2 format). */
function godsEyeHash({ lat, lon, alt, heading = 20, pitch = -45, layers }) {
	const p = new URLSearchParams();
	p.set('v', '2');
	p.set('lat', lat.toFixed(6));
	p.set('lon', lon.toFixed(6));
	p.set('alt', alt.toFixed(6));
	p.set('heading', heading.toFixed(6));
	p.set('pitch', pitch.toFixed(6));
	p.set('roll', '0');
	p.set('style', 'raw');
	p.set('layers', layers.join(','));
	return `#${p.toString()}`;
}

/** Click the first visible element matching a CSS selector (optionally whose aria-label / text matches). */
async function clickSel(page, sel, re = null, timeout = 30000) {
	const t0 = Date.now();
	while (Date.now() - t0 < timeout) {
		const ok = await page.evaluate((q, s, f) => {
			const rx = s ? new RegExp(s, f) : null;
			const el = [...document.querySelectorAll(q)].find((e) => {
				const r = e.getBoundingClientRect();
				if (!(r.width > 0 && r.height > 0)) return false;
				return !rx || rx.test(`${e.getAttribute('aria-label') || ''} ${e.innerText || ''} ${e.title || ''}`);
			});
			if (!el) return false;
			el.scrollIntoView({ block: 'center' });
			el.click();
			return true;
		}, sel, re ? re.source : null, re ? re.flags : '');
		if (ok) return true;
		await sleep(700);
	}
	throw new Error(`no element ${sel}${re ? ` matching ${re}` : ''}`);
}

/** Click an element even when the layout hides it (a collapsed rail's text control). */
async function clickHidden(page, sel, timeout = 30000) {
	const t0 = Date.now();
	while (Date.now() - t0 < timeout) {
		if (await page.evaluate((q) => { const e = document.querySelector(q); if (!e) return false; e.click(); return true; }, sel)) return true;
		await sleep(700);
	}
	throw new Error(`no element ${sel}`);
}

/** Pick a road through the top bar's search (the omnibar selects it and the map flies to it). */
async function omniPick(page, query) {
	await clickSel(page, '[data-shell="command-search"]');
	await sleep(900);
	await page.keyboard.type(query, { delay: 40 });
	await sleep(3000);
	await page.keyboard.press('Enter');
	await sleep(9000);
}

/** Click a road on the canvas: the canvas hook (window.__GODS_EYE__.locate) gives the on-screen point of each visible,
 *  uncovered entity of a layer (wl: waterlogging, seg: traffic flow, fc: forecast); the first preferred id wins. */
async function pickRoad(page, prefix, prefer = []) {
	const pts = await page.evaluate((p) => window.__GODS_EYE__?.locate?.(p) ?? [], prefix).catch(() => []);
	if (!pts.length) throw new Error(`no visible ${prefix} entity to pick`);
	const byId = new Map(pts.map((q) => [q.id, q]));
	const hit = prefer.map((id) => byId.get(`${prefix}${id}`)).find(Boolean) ?? pts[Math.floor(pts.length / 2)];
	await page.mouse.click(hit.x, hit.y);
	await sleep(5000);
	return hit.id;
}

/** Zoom the map out over the canvas centre (mouse wheel). */
async function wheelOut(page, ticks = 3, dy = 400) {
	await page.mouse.move(640, 480);
	for (let i = 0; i < ticks; i++) { await page.mouse.wheel({ deltaY: dy }); await sleep(900); }
}

/** The Map page on its flat 2D city basemap (the 3D tool off): draped lines read clearly in software WebGL. */
async function map2d(page) {
	const is3d = await page.$eval('[data-map-tool="3d"]', (b) => b.getAttribute('aria-pressed') === 'true' || b.classList.contains('is-pressed')).catch(() => false);
	if (is3d) await clickSel(page, '[data-map-tool="3d"]').catch(() => {});
	await sleep(6000);
}

/** Turn a Map layer on (the Layers sheet's switch), then close the sheet. */
async function mapLayer(page, id, on = true) {
	await clickSel(page, '[data-testid="v3-map-layers"]');
	await sleep(800);
	const pressed = await page.$eval(`button[data-layer="${id}"]`, (b) => b.getAttribute('aria-checked') === 'true').catch(() => null);
	if (pressed !== on) await clickSel(page, `button[data-layer="${id}"]`);
	await sleep(600);
	await page.keyboard.press('Escape');
}

// ── the set (docs/screenshots/README.md) ───────────────────────────────────
/** The map shots' camera: North and Central Kolkata (College Street, Thanthania, Shyambazar), seen from the south. */
const NORTH = (layers) => godsEyeHash({ lat: 22.5420, lon: 88.3560, alt: 5200, heading: 15, pitch: -42, layers });
const SHOTS = [
	{ name: 'landing', url: '/welcome', view: CONSOLE, lang: 'bn', public: true, wait: 5000 },
	{ name: 'home', url: '/', view: CONSOLE, lang: 'en', wait: 20000 },
	{ name: 'home-bn', url: '/', view: CONSOLE, lang: 'bn', wait: 40000,
		// scrolled to the City row (Air · Heat · Cyclone · River · Quake) and the decision strip
		act: async (page) => { await page.evaluate(() => { const el = [...document.querySelectorAll('h2, h3')].find((h) => /^শহর$|^City$/.test(h.textContent.trim()));
			el?.scrollIntoView({ block: 'center' }); }); await sleep(3000); } },
	{ name: 'map-waterlogging', url: '/map?replay=2025-09-23' + godsEyeHash({ lat: 22.5750, lon: 88.3650, alt: 14000, heading: 0, pitch: -89, layers: ['waterlog'] }), view: CONSOLE, lang: 'en', wait: 15000,
		act: async (page) => {
			await waitText(page, /hindsight/i, 60000);
			await map2d(page);
			await clickText(page, /^05:30$/).catch(() => {});
			// the hindsight roads are on screen before one is picked (the canvas reports what it can click)
			// (the draped lines land batch by batch: wait until the visible count holds steady)
			const t0 = Date.now();
			let last = -1, steady = 0;
			while (Date.now() - t0 < 150000 && steady < 4) {
				const n = await page.evaluate(() => (window.__GODS_EYE__?.locate?.('wl:') ?? []).length).catch(() => 0);
				steady = n >= 10 && n === last ? steady + 1 : 0;
				last = n;
				await sleep(3000);
			}
			await sleep(5000);
			await pickRoad(page, 'wl:', [1058, 1055, 1057, 1053, 1025, 1027, 1033, 1019]).catch(() => {});
			await sleep(6000);
		} },
	{ name: 'map-forecast', url: '/map' + NORTH(['photoreal-3d', 'flow', 'forecast', 'events', 'units']), view: CONSOLE, lang: 'en', wait: 15000,
		act: async (page) => {
			await mapLayer(page, 'forecast', true);
			await sleep(9000);
			await pickRoad(page, 'seg:', [1058, 1053, 1062, 1057, 1051]);
			await sleep(8000);
		} },
	{ name: 'map-air', url: '/map' + godsEyeHash({ lat: 22.5600, lon: 88.3450, alt: 30000, heading: 0, pitch: -89, layers: ['air', 'events'] }),
		view: CONSOLE, lang: 'en', wait: 15000,
		act: async (page) => {
			// the 2D city map (the flat basemap): every air site visible at once
			await map2d(page);
			await mapLayer(page, 'air', true).catch(() => {});
			await sleep(10000);
			await pickRoad(page, 'aq:', []).catch(() => {});
			await sleep(5000);
		} },
	{ name: 'replay-2025-09-23', url: '/map?replay=2025-09-23' + godsEyeHash({ lat: 22.5520, lon: 88.3620, alt: 15000, heading: 0, pitch: -89, layers: ['waterlog'] }), view: CONSOLE, lang: 'en', wait: 15000,
		act: async (page) => {
			await waitText(page, /hindsight/i, 60000);
			await map2d(page);
			// the draped hindsight roads land batch by batch: wait until the layer reports its roads drawn
			const t0 = Date.now();
			while (Date.now() - t0 < 90000) {
				const n = await page.evaluate(() => { const s = window.__GODS_EYE__?.layerStats?.waterlog; return s ? (s.drawn ?? s.count ?? s.detail?.drawn ?? 0) : 0; }).catch(() => 0);
				if (n > 0) break;
				await sleep(2000);
			}
			await sleep(15000);
		} },
	{ name: 'decide-ai', url: '/decide', view: CONSOLE, lang: 'en', wait: 25000,
		act: async (page) => {
			// the twin's signal-timing card (a real mouse click: the queue's own handler selects it)
			const t0 = Date.now();
			let h = null;
			while (!h && Date.now() - t0 < 90000) {
				h = await page.evaluateHandle(() => [...document.querySelectorAll('[data-testid="ai-queue-card"]')]
					.find((e) => /signal timing|re-time/i.test(e.getAttribute('aria-label') || '')) || null);
				if (!(await h.evaluate((e) => !!e))) { h = null; await sleep(1500); }
			}
			if (!h) throw new Error('no signal-timing card in the queue');
			await h.evaluate((e) => e.scrollIntoView({ block: 'center' }));
			await sleep(500);
			await h.click();
			await sleep(7000);
		} },
	{ name: 'decide-waterlogging', url: '/decide', view: CONSOLE, lang: 'en', wait: 12000,
		act: async (page) => {
			await clickHidden(page, '[data-testid="ai-exercise"]');
			await waitText(page, /exercise/i, 60000);
			await sleep(5000);
			await clickSel(page, '[data-testid="ai-queue-card"]', /reroute|divert|waterlog/i, 60000);
			await sleep(5000);
		} },
	{ name: 'object-segment', url: '/o/segment:1033', view: CONSOLE, lang: 'en', wait: 20000 },
	{ name: 'voice-report', url: '/', view: CONSOLE, lang: 'bn', wait: 8000, audio: true,
		act: async (page) => {
			await clickSel(page, '[data-testid="field-report-open"]');
			await sleep(1500);
			const hold = await page.waitForSelector('[data-testid="field-hold"]', { visible: true, timeout: 15000 });
			const box = await hold.boundingBox();
			await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
			await page.mouse.down();
			await sleep(6500);
			await page.mouse.up();
			await page.waitForSelector('[data-testid="field-result"]', { visible: true, timeout: 120000 });
			await sleep(2500);
		} },
	{ name: 'road-state', url: '/o/camera:EM-J12', view: { width: 1440, height: 1320 }, lang: 'en', wait: 10000,
		act: async (page) => {
			await clickSel(page, 'button.th', /rain|water/i, 20000).catch(() => {});
			await sleep(800);
			await clickSel(page, '[data-testid="rs-read"]');
			await waitText(page, /confidence|waterlogged|depth/i, 240000);
			// the click scrolls the card into view; the shot shows the page from its header, model line included
			await page.evaluate(() => {
				window.scrollTo(0, 0);
				for (const el of document.querySelectorAll('*')) if (el.scrollTop > 0) el.scrollTop = 0;
			});
			await sleep(3000);
		} },
	{ name: 'plan', url: '/plan', view: CONSOLE, lang: 'en', wait: 12000 },
	{ name: 'assistant', url: '/assistant', view: CONSOLE, lang: 'en', wait: 8000,
		act: async (page) => {
			await clickText(page, /where was the stolen/i);
			await sleep(5000);
			// the answer streams; wait until the send control is usable again (the stream ended)
			const t0 = Date.now();
			while (Date.now() - t0 < 180000) {
				const busy = await page.evaluate(() => !!document.querySelector('[data-testid="v3-ask"]')?.disabled || /thinking|reading the city/i.test(document.body.innerText)).catch(() => true);
				if (!busy) break;
				await sleep(2000);
			}
			await sleep(4000);
		} },
	{ name: 'advisories', url: '/comms', view: CONSOLE, lang: 'en', wait: 15000 },
	{ name: 'analyst-workspace', url: '/analyst', view: CONSOLE, lang: 'en', wait: 15000 },
	{ name: 'situation-wall', url: '/ops', view: CONSOLE, lang: 'en', wait: 15000 },
	{ name: 'map-3d', url: '/gods-eye' + godsEyeHash({ lat: 22.5480, lon: 88.3560, alt: 2600, heading: 20, pitch: -32,
		layers: ['photoreal-3d', 'events', 'units', 'signals', 'cameras', 'traces'] }), view: CONSOLE, lang: 'en', wait: 15000, tiles: true },
	{ name: 'imagery', url: '/v3-gallery', view: CONSOLE, lang: 'en', wait: 6000,
		act: async (page) => { await page.evaluate(() => document.getElementById('g-photos')?.scrollIntoView({ block: 'start' })); await sleep(4000); } },
	{ name: 'citizen', url: '/citizen', view: PHONE, lang: 'bn', public: true, wait: 12000,
		act: async (page) => {
			await page.select('[data-testid="water-road"]', '1058').catch(() => {});
			await sleep(3000);
			// the road's waterlogging status, its Listen button and Air today below it
			await page.evaluate(() => document.querySelector('[data-testid="air-card"]')?.scrollIntoView({ block: 'end' }));
			await sleep(600);
			await page.evaluate(() => { const c = document.querySelector('[data-testid="air-card"]'); let el = c?.parentElement;
				while (el && el.scrollHeight <= el.clientHeight) el = el.parentElement; (el || document.scrollingElement).scrollBy(0, 40); });
			await sleep(2500);
		} },
	{ name: 'driver', url: '/driver', view: PHONE, lang: 'bn', public: true, wait: 8000 },
];

if (argv.includes('--list')) {
	for (const s of SHOTS) console.log(`${s.name.padEnd(22)} ${s.url}`);
	process.exit(0);
}

const todo = SHOTS.filter((s) => (!ONLY.length || ONLY.includes(s.name)) && (!s.audio || AUDIO));
for (const s of SHOTS) if (s.audio && !AUDIO && (!ONLY.length || ONLY.includes(s.name))) console.log(JSON.stringify({ shot: s.name, skipped: 'needs --fake-audio <wav>' }));
fs.mkdirSync(OUT, { recursive: true });

function guard(page, errors) {
	page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 200)));
	page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 200)); });
	if (!LIVE) return;
	page.setRequestInterception(true);
	page.on('request', (req) => {
		const u = new URL(req.url());
		const compute = /^\/api\/(speech|vision|twin|hydro|forecast)\//.test(u.pathname)
			|| u.pathname.endsWith('/api/v1/traffic/live') || u.pathname === '/api/session'
			|| u.pathname === '/api/convoy/chat/stream' || u.pathname === '/api/convoy/chat';
		if (u.pathname.startsWith('/api/') && req.method() !== 'GET' && !compute) {
			errors.push(`blocked live write ${req.method()} ${u.pathname}`);
			return req.respond({ status: 503, contentType: 'application/json', body: '{"error":"console_shots: live writes refused"}' });
		}
		return req.continue();
	});
}

const browser = await puppeteer.launch({
	executablePath: CHROME,
	headless: 'new',
	args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--use-gl=angle',
		'--ignore-gpu-blocklist', '--window-size=1440,900', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
		...(AUDIO ? [`--use-file-for-fake-audio-capture=${path.resolve(AUDIO)}%noloop`] : [])],
});
let session = null;
let failures = 0;
const report = [];
try {
	session = await signIn(ORIGIN, OFFICER);
	if (AUDIO) await browser.defaultBrowserContext().overridePermissions(ORIGIN, ['microphone']).catch(() => {});
	const pub = await browser.createBrowserContext();
	for (const s of todo) {
		const errors = [];
		const ctx = s.public ? pub : browser.defaultBrowserContext();
		const page = await ctx.newPage();
		try {
			await page.setViewport(s.view);
			const host = new URL(ORIGIN).hostname;
			const cookies = [{ name: 'sahoshi_lang', value: s.lang || 'en', domain: host, path: '/' }];
			if (!s.public && session && session.gate !== false) cookies.push(...puppeteerCookies(session));
			await page.setCookie(...cookies);
			guard(page, errors);
			await page.goto(ORIGIN + s.url, { waitUntil: 'networkidle2', timeout: 120000 }).catch((e) => errors.push('goto: ' + e.message.slice(0, 160)));
			if (s.tiles) await waitTiles(page);
			await sleep(s.wait ?? 6000);
			if (s.act) await s.act(page).catch((e) => errors.push('act: ' + e.message.slice(0, 200)));
			if (s.settle) await sleep(s.settle);
			const file = path.join(OUT, `${s.name}.${s.png ? 'png' : 'jpg'}`);
			await page.screenshot(s.png ? { path: file } : { path: file, type: 'jpeg', quality: 88 });
			report.push({ shot: s.name, file, errors: errors.slice(0, 6) });
			console.log(JSON.stringify({ shot: s.name, file: path.relative(ROOT, file), errors: errors.slice(0, 6) }));
		} catch (e) {
			failures++;
			console.log(JSON.stringify({ shot: s.name, failed: String(e).slice(0, 240) }));
		} finally {
			await page.close().catch(() => {});
		}
	}
} finally {
	if (session && session.gate !== false) await signOut(session).catch(() => {});
	await browser.close();
}
process.exit(failures ? 1 : 0);
