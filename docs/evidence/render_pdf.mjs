// Render docs/evidence/evidence.html to Sahoshi_Evidence.pdf (A4): node docs/evidence/render_pdf.mjs
import { createRequire } from 'node:module';
const require = createRequire(process.env.PUPPETEER_FROM ?? '/home/sandy050405/argus/sahoshi/frontend/package.json');
const puppeteer = require('puppeteer');
const here = new URL('.', import.meta.url).pathname;
const browser = await puppeteer.launch({ headless: 'new', executablePath: process.env.CHROME ?? '/home/sandy050405/.cache/puppeteer/chrome/linux_arm-153.0.8010.36/chrome-linux-arm64/chrome', args: ['--no-sandbox', '--allow-file-access-from-files'] });
const page = await browser.newPage();
await page.goto(`file://${here}evidence.html`, { waitUntil: 'networkidle0' });
await page.pdf({ path: `${here}Sahoshi_Evidence.pdf`, format: 'A4', printBackground: true, preferCSSPageSize: true });
await browser.close();
console.log('wrote', `${here}Sahoshi_Evidence.pdf`);
