// Render the Sahoshi lockups (SVG) to PNG for the deck: node docs/deck/render_brand.mjs
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(process.env.PUPPETEER_FROM ?? new URL('../../frontend/package.json', import.meta.url));
const puppeteer = require('puppeteer');
const here = dirname(fileURLToPath(import.meta.url));
const brand = resolve(here, '../../services/command-deck/static/brand');
const jobs = [
  ['sahoshi-lockup.svg', 'lockup-night.png', 1400],
  ['sahoshi-lockup-stacked.svg', 'lockup-stacked-night.png', 900],
  ['sahoshi-mark.svg', 'mark-night.png', 512],
];
const browser = await puppeteer.launch({ headless: 'new', executablePath: process.env.CHROME ?? `${process.env.HOME}/.cache/puppeteer/chrome/linux_arm-153.0.8010.36/chrome-linux-arm64/chrome`, args: ['--no-sandbox'] });
const page = await browser.newPage();
for (const [src, out, width] of jobs) {
  const svg = readFileSync(resolve(brand, src), 'utf8');
  await page.setContent(`<html><body style="margin:0;background:transparent"><div id="b" style="width:${width}px">${svg.replace('<svg', '<svg style="width:100%;height:auto;display:block"')}</div></body></html>`);
  const el = await page.$('#b');
  writeFileSync(resolve(here, 'assets', out), await el.screenshot({ omitBackground: true }));
  console.log('wrote', out);
}
await browser.close();
