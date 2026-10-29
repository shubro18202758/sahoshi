// The README's logo and symbol strips (PNG, so they read the same in GitHub's light and dark themes):
//   node scripts/brand/render_readme_strips.mjs   → docs/brand/{agencies,sources,vehicles,events}.png
// Marks are drawn as-is from services/command-deck/static (logos/NOTICE.md lists owners and licences).
import { readFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(process.env.PUPPETEER_FROM ?? new URL('../../frontend/package.json', import.meta.url));
const puppeteer = require('puppeteer');
const root = resolve(here, '../..');
const stat = resolve(root, 'services/command-deck/static');
const out = resolve(root, 'docs/brand');
mkdirSync(out, { recursive: true });

const uri = (rel) => {
	const buf = readFileSync(resolve(stat, rel));
	const mime = rel.endsWith('.svg') ? 'image/svg+xml' : 'image/png';
	return `data:${mime};base64,${buf.toString('base64')}`;
};

const STRIPS = {
	agencies: { plate: '#f4f4f4', items: [
		['logos/kp.png', 'Kolkata Police'], ['logos/kmc.png', 'KMC'], ['logos/wbp.svg', 'West Bengal Police'],
		['logos/bpc.png', 'Bidhannagar Police'], ['logos/hcp.png', 'Howrah City Police'], ['logos/wbsdma.png', 'WB Disaster Mgmt'],
		['logos/nkda.png', 'NKDA'], ['logos/wbtc.png', 'WBTC'], ['logos/metro.svg', 'Metro Railway'],
	] },
	sources: { plate: '#f4f4f4', items: [
		['logos/imd.png', 'IMD'], ['logos/ndma.png', 'NDMA'], ['logos/ndma-sachet.png', 'Sachet alerts', '#1c3d6e'],
		['logos/openstreetmap.svg', 'OpenStreetMap'], ['logos/open-meteo.png', 'Open-Meteo'],
		['logos/copernicus.png', 'Copernicus DEM'], ['logos/cesium.svg', 'Cesium'],
	] },
	vehicles: { plate: '#161616', items: [
		['artwork/vehicles/ambulance.svg', 'Ambulance (108)'], ['artwork/vehicles/patrol.svg', 'Patrol'],
		['artwork/vehicles/taxi.svg', 'Taxi'], ['artwork/vehicles/bus.svg', 'WBTC bus'], ['artwork/vehicles/toto.svg', 'Toto'],
		['artwork/vehicles/auto_rickshaw.svg', 'Auto'], ['artwork/vehicles/fire_tender.svg', 'Fire tender'],
		['artwork/vehicles/convoy.svg', 'Protected movement'],
	] },
	events: { plate: '#161616', items: [
		['artwork/events/flooding.svg', 'Waterlogging'], ['artwork/events/weather.svg', 'Weather'],
		['artwork/events/cyclone.svg', 'Cyclone'], ['artwork/events/mass_gathering.svg', 'Puja crowds'],
		['artwork/events/procession.svg', 'Procession'], ['artwork/events/green_corridor.svg', 'Green corridor'],
		['artwork/events/road_accident.svg', 'Road accident'], ['artwork/events/work_zone.svg', 'Work zone'],
	] },
};

const browser = await puppeteer.launch({ headless: 'new', executablePath: process.env.CHROME ?? `${process.env.HOME}/.cache/puppeteer/chrome/linux_arm-153.0.8010.36/chrome-linux-arm64/chrome`, args: ['--no-sandbox'] });
const page = await browser.newPage();
for (const [name, { plate, items }] of Object.entries(STRIPS)) {
	const dark = plate !== '#f4f4f4';
	const tiles = items.map(([src, label, own]) => `
		<figure><div class="tile"${own ? ` style="background:${own}"` : ''}><img src="${uri(src)}"></div><figcaption>${label}</figcaption></figure>`).join('');
	await page.setViewport({ width: 1600, height: 400, deviceScaleFactor: 2 });
	await page.setContent(`<html><head><style>
		body { margin: 0; background: #000; font: 600 15px Inter, 'Helvetica Neue', Arial, sans-serif; }
		#s { display: inline-flex; gap: 14px; padding: 18px; background: #000; }
		figure { margin: 0; width: 150px; text-align: center; }
		.tile { height: ${dark ? 120 : 96}px; border-radius: 14px; background: ${plate}; display: flex; align-items: center;
			justify-content: center; border: 1px solid ${dark ? '#2e2e2e' : '#dcdcdc'}; }
		img { max-width: ${dark ? 128 : 112}px; max-height: ${dark ? 92 : 64}px; }
		figcaption { color: #cbcbcb; margin-top: 8px; font-size: 13px; }
	</style></head><body><div id="s">${tiles}</div></body></html>`);
	await page.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))));
	const el = await page.$('#s');
	await el.screenshot({ path: resolve(out, `${name}.png`) });
	console.log(`wrote docs/brand/${name}.png`);
}
await browser.close();
