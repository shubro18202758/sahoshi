/**
 * Raster icons from the brand SVGs (static/brand): the PWA icons, the Apple touch icon and the legacy favicon.png.
 * Needs a headless Chrome through puppeteer (PUPPETEER_FROM: a folder whose node_modules holds puppeteer; CHROME: the
 * browser binary). Deterministic for one Chrome build.
 *   PUPPETEER_FROM=… CHROME=… node scripts/brand/render_icons.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const STATIC = path.resolve(HERE, '../../services/command-deck/static');
const require = createRequire(path.join(process.env.PUPPETEER_FROM ?? '/home/sandy050405/argus/sahoshi/frontend', 'package.json'));
const puppeteer = require('puppeteer');
const CHROME = process.env.CHROME ?? '/home/sandy050405/.cache/puppeteer/chrome/linux_arm-153.0.8010.36/chrome-linux-arm64/chrome';

// [source svg, output png, size, full-bleed tile colour (maskable icons need a full square) or null]
const JOBS = [
	['brand/favicon.svg', 'favicon.png', 32, null],
	['brand/sahoshi-app-icon.svg', 'brand/icon-192.png', 192, null],
	['brand/sahoshi-app-icon.svg', 'brand/icon-512.png', 512, null],
	['brand/sahoshi-mark.svg', 'brand/icon-maskable-512.png', 512, '#000000'],
	['brand/sahoshi-mark.svg', 'brand/apple-touch-icon.png', 180, '#000000'],
];

const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox'] });
try {
	const page = await browser.newPage();
	for (const [src, out, size, tile] of JOBS) {
		const svg = readFileSync(path.join(STATIC, src), 'utf8');
		// a maskable icon keeps its art inside the central 80 % safe zone, on a full-bleed tile
		const inner = tile ? `<div style="width:${size}px;height:${size}px;background:${tile};display:grid;place-items:center"><img src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}" style="width:${size * 0.62}px;height:${size * 0.62}px"></div>`
			: `<img src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}" style="width:${size}px;height:${size}px;display:block">`;
		await page.setViewport({ width: size, height: size, deviceScaleFactor: 1 });
		await page.setContent(`<html><body style="margin:0;background:transparent">${inner}</body></html>`);
		await page.screenshot({ path: path.join(STATIC, out), omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } });
		console.log('ok', out);
	}
} finally {
	await browser.close();
}
