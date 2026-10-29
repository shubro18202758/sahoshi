#!/usr/bin/env python3
"""Build docs/evidence/evidence.html — the prototype-evidence document — from the repository's own outputs.

Run:   python3 docs/evidence/make_evidence.py && node docs/evidence/render_pdf.mjs
Reads: scripts/impact_results.json (modelled impact), docs/screenshots/*.jpg, docs/diagrams/*.png,
       services/speech/eval/results.json and services/vision/eval/results.json (evaluations),
       docs/evidence/facts.json (test totals and live readiness, refreshed by the release run).
Every figure carries its label: LIVE, OBSERVED, MODELLED, SIMULATED or EMULATED.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
IMPACT = json.loads((ROOT / "scripts" / "impact_results.json").read_text())
FACTS = json.loads((HERE / "facts.json").read_text())
SHOTS = ROOT / "docs" / "screenshots"
DIAG = ROOT / "docs" / "diagrams"


def e(s: str) -> str:
    return html.escape(s, quote=True)


def img(path: Path, alt: str, cls: str = "") -> str:
    if not path.exists():
        return f'<div class="missing {cls}">[{e(path.name)}]</div>'
    rel = path.relative_to(HERE.parent.parent)
    return f'<img class="{cls}" src="../../{rel.as_posix()}" alt="{e(alt)}">'


def shot(name: str, caption: str) -> str:
    return f'<figure>{img(SHOTS / name, caption)}<figcaption>{e(caption)}</figcaption></figure>'


def table(head: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{e(h)}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"


def fmt(n: float) -> str:
    return f"{n:,.0f}"


def build() -> str:
    sc, vip, amb = IMPACT["scenarios"], IMPACT["vip_corridor_central"], IMPACT["ambulance"]
    f = FACTS
    parts: list[str] = []
    parts.append(f"""
<section class="cover">
  {img(ROOT / 'docs/deck/assets/lockup-night.png', 'Sahoshi', 'lockup')}
  <h1>Prototype evidence</h1>
  <p class="tag">Not by stopping. <b>By steering.</b></p>
  <p class="sub">One live picture of Kolkata's roads, rain and crowds for the traffic police, KMC, disaster response and
  ambulance (108) crews. On-premises open-source AI proposes; a named officer decides.</p>
  <p class="meta">{e(f['as_of'])} · github.com/shubro18202758/sahoshi · MIT licence</p>
</section>""")
    parts.append(f"""
<section>
  <h2>1 · What exists today</h2>
  <ul class="facts">
    <li><b>A working system on one on-premises AI computer</b> — {e(f['readiness'])}: road store, live traffic ingest, decision engine,
        operator console (Bengali, English, Hindi), event emulator, OSINT ingest, three local language/embedding model hosts.</li>
    <li><b>Five AI services</b> running beside it: corridor forecasting (Chronos-2), waterlogging nowcast (rain × Hooghly tide × terrain × pumps),
        a signal-timing traffic twin, Bengali voice (speech-to-text and read-aloud) and camera road state (Qwen3-VL).</li>
    <li><b>Real Kolkata roads</b>: {e(f['network'])} from OpenStreetMap; {e(f['gazetteer'])}.</li>
    <li><b>Open feeds wired in</b>: {e(f['feeds'])}.</li>
    <li><b>Quality</b>: {e(f['tests'])}.</li>
  </ul>
  <p class="note">Labels used throughout: <b>LIVE</b> (a real open feed), <b>OBSERVED</b> (a measured record), <b>MODELLED</b> (computed
  under stated assumptions), <b>SIMULATED</b> (an exercise scenario), <b>EMULATED</b> (a stand-in for a feed that needs an agency's access).</p>
</section>""")
    parts.append(f"""
<section>
  <h2>2 · The problem, in Kolkata</h2>
  {table(['What', 'Fact', 'Source'], [
      ['Cloudburst at high tide', '251.6 mm in 24 h on 22–23 Sep 2025, the heaviest in about four decades; roads went under within the hour; 8–12 deaths, most by electrocution; metro, rail and ~30 flights disrupted', 'IMD; Reuters/PTI via Dawn, Business Standard'],
      ['Drainage and the river', 'Outfall gates close at high tide on the Hooghly — the same rain waterlogs far faster', 'KMC/ADB FFEWS project; port statements'],
      ['Flood warning infrastructure', 'KMC is building India\'s first city-level Flood Forecasting & Early Warning System (ADB) — sensors in canals, pumping stations and junctions', 'ADB "Toward Resilient Kolkata"; Millennium Post'],
      ['Durga Puja', '10,000+ police a day, ~30% on traffic; goods-vehicle restrictions; pandal-route apps', 'Kolkata Police via Millennium Post (2025)'],
      ['Bridges', 'Howrah Bridge: ~1 lakh vehicles and ~1.5 lakh pedestrians a day', 'Wikipedia; Deccan Herald (approximate)'],
      ['Coordination', 'Traffic police, KMC, WBSDMA, the power utility and ambulance (108) each hold one piece; coordination by phone and radio', 'observed practice'],
  ])}
</section>""")
    parts.append(f"""
<section>
  <h2>3 · The screens</h2>
  <div class="grid">
    {shot('home.jpg', 'Home — what needs the officer now, Rain · Tide, the next two hours')}
    {shot('map-waterlogging.jpg', 'Map — waterlogging risk on every road, with its drivers labelled')}
    {shot('decide-ai.jpg', 'Decide — a signal-timing proposal tested in the traffic twin against doing nothing')}
    {shot('decide-waterlogging.jpg', 'Decide — reroute, ambulance window, live-wire hazard request, Bengali advisory')}
    {shot('object-segment.jpg', 'A road — two-hour forecast with its band, waterlogging class and drivers')}
    {shot('voice-report.jpg', 'A field report spoken in Bengali becomes a structured, unverified report')}
    {shot('road-state.jpg', 'Camera road state — roads and vehicles only; person questions are refused')}
    {shot('replay-2025-09-23.jpg', 'Replay of the 22–23 Sep 2025 storm (IMD-observed rain, modelled ponding)')}
    {shot('citizen.jpg', 'Citizen page — waterlogging on your road, with Listen')}
    {shot('home-bn.jpg', 'The console in Bengali')}
  </div>
</section>""")
    parts.append(f"""
<section>
  <h2>4 · Architecture</h2>
  <figure class="wide">{img(DIAG / '01-2-system-context.png', 'System context')}<figcaption>System context — everything runs on premises; the deck is the only network-facing port.</figcaption></figure>
  <figure class="wide">{img(DIAG / '02-3-1-containers-and-ports.png', 'Containers and ports')}<figcaption>Services and ports.</figcaption></figure>
</section>""")
    parts.append(f"""
<section>
  <h2>5 · The AI, measured</h2>
  {table(['Capability', 'Model (licence)', 'Result', 'Label'], f['ai_rows'])}
  <p class="note">{e(f['ai_note'])}</p>
</section>""")
    parts.append(f"""
<section>
  <h2>6 · Expected impact (MODELLED)</h2>
  {table(['Measure', 'Value', 'Basis'], [
      ['Junction-freeze delay', f"{sc['central']['reduction_factor']:,.0f}× less (range {sc['conservative']['reduction_factor']:,.0f}×–{sc['optimistic']['reduction_factor']:,.0f}×)", 'rolling ~2.5 min holds instead of a 25 min freeze (central case); delay scales with the square of the hold'],
      ['VIP movement, Nabanna → airport', f"{fmt(vip['commuter_minutes_baseline'])} → {fmt(vip['commuter_minutes_platform'])} commuter-minutes", f"{vip['junctions']} junctions, {vip['km']:.0f} km on the Kolkata network"],
      ['Ambulance (108)', f"≈ {fmt(amb['minutes_returned_per_year'])} golden-hour minutes a year", f"{amb['trips_crossing_per_movement_day']:.0f} crossing trips per movement-day (assumption)"],
      ['Waterlogging warning', '45–120 minutes before deep water', 'replay of 22–23 Sep 2025 on IMD-observed rain'],
  ])}
  <p class="note">Model outputs on Kolkata's OpenStreetMap network under stated assumptions (IMPACT_REPORT.md) — not field measurements, and never a claim about lives saved.</p>
</section>""")
    parts.append(f"""
<section>
  <h2>7 · Tests and quality</h2>
  {table(['Suite', 'Result'], f['test_rows'])}
</section>""")
    parts.append("""
<section>
  <h2>8 · Implementation and cost</h2>
  <table><thead><tr><th>When</th><th>What</th></tr></thead><tbody>
  <tr><td>Month 0–1</td><td>Read-only data MoU: Kolkata Traffic Police (CCTV stills, signal plans), KMC (FFEWS), WBSDMA (alerts), the ambulance (108) operator; nodal officers.</td></tr>
  <tr><td>Month 1–2</td><td>Install the on-premises unit in the pilot control room; switch adapters from EMULATED to LIVE as access arrives.</td></tr>
  <tr><td>Month 2–4</td><td>Shadow mode — Sahoshi proposes, officers work as usual, weekly comparison.</td></tr>
  <tr><td>Month 5–12</td><td>Live pilot in one division through the monsoon and Durga Puja; officers approve every action.</td></tr>
  <tr><td>Month 12</td><td>Independent review; city-wide plan.</td></tr></tbody></table>
  <table><thead><tr><th>Cost item</th><th>Pilot (12 months)</th></tr></thead><tbody>
  <tr><td>On-premises AI units (2, one as backup)</td><td>₹8–10 lakh</td></tr>
  <tr><td>Engineering (3 × 6 months + 1 × 6 months)</td><td>₹29 lakh</td></tr>
  <tr><td>Water-level sensors where FFEWS has none (optional)</td><td>₹4 lakh</td></tr>
  <tr><td>Training and SOP workshops</td><td>₹2 lakh</td></tr>
  <tr><td>Backup connectivity</td><td>₹0.5 lakh</td></tr>
  <tr><td>Contingency (15%)</td><td>≈ ₹6–7 lakh</td></tr>
  <tr><td><b>Total pilot</b></td><td><b>≈ ₹45–55 lakh</b></td></tr>
  <tr><td>City-wide, two years</td><td>≈ ₹2–2.5 crore; running ≈ ₹40–60 lakh a year</td></tr>
  <tr><td>Software licences</td><td>₹0 — open models, OpenStreetMap, Sahoshi (MIT)</td></tr></tbody></table>
</section>
<section>
  <h2>9 · Scalability — a city is a folder</h2>
  <p>Everything city-specific lives in a City Pack (<code>cities/&lt;id&gt;/</code>): the OpenStreetMap extract and corridors, gazetteer, agencies,
  emergency numbers, plate format, languages, scenarios and impact parameters. The prototype was first built for another Indian city; the same
  build tools now produce Kolkata, and a test builds both. Next packs: Howrah and Bidhannagar (inside the Kolkata pack), Siliguri,
  Asansol–Durgapur, Patna and Ranchi (Hindi is already first-class).</p>
  <h2>10 · Guardrails</h2>
  <ul class="facts">
    <li>Vehicles only — no faces, no persons; number plates masked until a named duty officer is on duty.</li>
    <li>The AI proposes; a named officer approves every action; no answer — the current plan holds; every decision audited.</li>
    <li>Honest labels on every number and every feed not yet connected.</li>
    <li>Events, not people: news and social signals are aggregate and about places; posters are never stored or scored.</li>
    <li>No e-challan can be approved against a theft victim.</li>
    <li>On-premises, retention limits, in the spirit of the DPDP Act 2023.</li>
  </ul>
</section>
<section class="sources">
  <h2>Sources</h2>
  <ol>
    <li>Reuters / PTI on the 22–23 Sep 2025 Kolkata rain — dawn.com/news/1944310; business-standard.com (2025-09-23)</li>
    <li>ADB, "Toward Resilient Kolkata: India's first comprehensive city-level flood forecasting and early warning system" — adb.org/publications/toward-resilient-kolkata</li>
    <li>Millennium Post — KMC unveils city-level flood forecasting warning system; Kolkata Police Puja Bandhu app; 10K police for Puja duty (2025)</li>
    <li>Howrah Bridge — en.wikipedia.org/wiki/Howrah_Bridge; Deccan Herald</li>
    <li>Census of India 2011 — Kolkata Municipal Corporation and urban agglomeration population</li>
    <li>Model cards: amazon/chronos-2, google/timesfm-2.5, Qwen/Qwen3-VL-8B-Instruct, perplexity-ai/pplx-embed, bengaliAI Whisper-medium, kenpath/svara-tts-v1 (Hugging Face)</li>
    <li>OpenStreetMap contributors (ODbL 1.0); Copernicus DEM GLO-30; Open-Meteo; NDMA SACHET; GDACS; USGS</li>
  </ol>
</section>""")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Sahoshi — prototype evidence</title>
<style>
@page {{ size: A4; margin: 14mm 13mm; }}
body {{ font-family: Inter, 'Noto Sans Bengali', sans-serif; color: #111; font-size: 10.5pt; line-height: 1.45; }}
h1 {{ font-size: 30pt; margin: 18mm 0 4mm; }} h2 {{ font-size: 15pt; margin: 0 0 3mm; border-bottom: 1px solid #ddd; padding-bottom: 2mm; }}
section {{ page-break-inside: avoid; margin-bottom: 8mm; }} section.cover {{ page-break-after: always; background: #000; color: #fff;
  margin: -14mm -13mm 0; padding: 22mm 18mm; height: 269mm; box-sizing: border-box; }}
.cover .lockup {{ height: 15mm; }} .cover .tag {{ font-family: 'Noto Sans Bengali'; font-size: 34pt; font-weight: 700; margin: 6mm 0; }}
.cover .tag b {{ color: #a6a6a6; }} .cover .sub {{ font-size: 13pt; color: #cbcbcb; max-width: 150mm; }} .cover .meta {{ margin-top: 120mm; color: #a6a6a6; }}
table {{ border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; font-size: 9.5pt; }} th, td {{ border-bottom: 1px solid #e3e3e3; text-align: left; padding: 1.6mm 2mm; vertical-align: top; }}
th {{ background: #f3f3f3; }} .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }}
figure {{ margin: 0; }} figure img {{ width: 100%; max-height: 92mm; object-fit: contain; background: #f6f6f6; border: 1px solid #ddd; border-radius: 2mm; }} figcaption {{ font-size: 8.5pt; color: #555; margin-top: 1mm; }}
figure.wide img {{ max-height: 110mm; object-fit: contain; }} .note {{ font-size: 8.8pt; color: #555; }} .facts li {{ margin-bottom: 1.5mm; }}
.missing {{ border: 1px dashed #bbb; padding: 10mm; color: #999; text-align: center; }} .sources {{ font-size: 8.8pt; }}
</style></head><body>{''.join(parts)}</body></html>"""


if __name__ == "__main__":
    out = HERE / "evidence.html"
    out.write_text(build(), encoding="utf-8")
    print("wrote", out)
