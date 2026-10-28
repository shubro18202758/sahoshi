#!/usr/bin/env python3
"""Render the Sahoshi deck (docs/deck/Sahoshi_Deck.pptx) from the repository's own numbers and screenshots.

Run:   /path/to/python-with-python-pptx docs/deck/make_deck.py
Then:  soffice --headless --convert-to pdf --outdir docs/deck docs/deck/Sahoshi_Deck.pptx
Inputs:
  scripts/impact_results.json        the modelled impact figures (the same source as IMPACT_REPORT.md)
  docs/screenshots/*.jpg             the product screenshots (a missing one renders as a labelled empty frame)
  docs/deck/assets/*                 brand lockups (render_brand.mjs) and reference photos (from static/photos)
  scripts/brand/photos/manifest.json photo credits
Every figure on a slide says what it is: LIVE, MODELLED, SIMULATED or EMULATED.
"""
from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
SHOTS = ROOT / "docs" / "screenshots"
IMPACT = json.loads((ROOT / "scripts" / "impact_results.json").read_text())
PHOTOS = {p["slug"]: p for p in json.loads((ROOT / "scripts" / "brand" / "photos" / "manifest.json").read_text())}
OUT = HERE / "Sahoshi_Deck.pptx"

BLACK = RGBColor(0x00, 0x00, 0x00)
S1 = RGBColor(0x11, 0x11, 0x11)
S2 = RGBColor(0x1A, 0x1A, 0x1A)
S3 = RGBColor(0x2E, 0x2E, 0x2E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
T2 = RGBColor(0xCB, 0xCB, 0xCB)
T3 = RGBColor(0xA6, 0xA6, 0xA6)
TAXI = RGBColor(0xFF, 0xC8, 0x00)  # the mark's colour, used only for the brand moment
BLUE = RGBColor(0x7F, 0xA8, 0xF7)  # links / AI, sparingly
LATIN = "Inter"
BENGALI = "Noto Sans Bengali"

W, H = Inches(13.333), Inches(7.5)


def is_bengali(s: str) -> bool:
    return any("ঀ" <= c <= "৿" for c in s)


def font(run, size, color=WHITE, bold=False, italic=False, text=""):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    f.name = BENGALI if is_bengali(text) else LATIN
    rpr = run._r.get_or_add_rPr()
    for tag, face in (("a:latin", LATIN), ("a:cs", BENGALI)):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set("typeface", face)


def bg(slide, color=BLACK):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def box(slide, x, y, w, h, color, line=None):
    shp = slide.shapes.add_shape(1, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(0.75)
    shp.shadow.inherit = False
    return shp


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP):
    """paras: list of (text, size, color, bold) or (runs, size, color, bold) where runs is a list of (text, color, bold)."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, (content, size, color, bold, *rest) in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = rest[0] if rest else PP_ALIGN.LEFT
        p.space_after = Pt(size * 0.45)
        runs = content if isinstance(content, list) else [(content, color, bold)]
        for t, c, b in runs:
            r = p.add_run()
            r.text = t
            font(r, size, c, b, text=t)
    return tb


def picture(slide, path: Path, x, y, w=None, h=None, label=None):
    if path.exists():
        if w is not None and h is not None:
            # fit inside the box at the picture's own aspect ratio, centred (never stretched)
            from PIL import Image
            iw, ih = Image.open(path).size
            scale = min(w / iw, h / ih)
            pw, ph = int(iw * scale), int(ih * scale)
            return slide.shapes.add_picture(str(path), x + (w - pw) // 2, y + (h - ph) // 2, pw, ph)
        return slide.shapes.add_picture(str(path), x, y, w, h)
    frame = box(slide, x, y, w or Inches(6), h or Inches(3.4), S2, line=S3)
    text(slide, x + Inches(0.2), y + Inches(0.2), (w or Inches(6)) - Inches(0.4), Inches(0.6),
         [(f"[ screenshot: {label or path.name} ]", 12, T3, False)])
    return frame


def cover_picture(slide, path: Path, x, y, w, h):
    """Fill the frame, cropping the photo to its aspect."""
    pic = slide.shapes.add_picture(str(path), x, y, w, h)
    from PIL import Image
    iw, ih = Image.open(path).size
    fr, ir = w / h, iw / ih
    if ir > fr:
        cut = (1 - fr / ir) / 2
        pic.crop_left = pic.crop_right = cut
    else:
        cut = (1 - ir / fr) / 2
        pic.crop_top = pic.crop_bottom = cut
    return pic


def credit(slug: str) -> str:
    p = PHOTOS.get(slug, {})
    return f"Reference photo · not live · {p.get('author', '')} · {p.get('license_short', '')} · Wikimedia Commons"


def footer(slide, n: int):
    text(slide, Inches(0.6), Inches(7.05), Inches(8), Inches(0.3),
         [([("Sahoshi", WHITE, True), ("  ·  সাহসী  ·  Kolkata", T3, False)], 10, T3, False)])
    text(slide, Inches(12.2), Inches(7.05), Inches(0.6), Inches(0.3), [(str(n), 10, T3, False, PP_ALIGN.RIGHT)])


def kicker_title(slide, kicker: str, title: str, y=Inches(0.55)):
    text(slide, Inches(0.6), y, Inches(12), Inches(0.35), [(kicker, 13, T3, True)])
    text(slide, Inches(0.6), y + Inches(0.42), Inches(12.1), Inches(1.0), [(title, 30, WHITE, True)])


def fmt(n: float) -> str:
    return f"{n:,.0f}"


def build() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    blank = prs.slide_layouts[6]
    imp = IMPACT
    n = 0

    def slide():
        nonlocal n
        n += 1
        s = prs.slides.add_slide(blank)
        bg(s)
        return s

    # 1 · title (poster)
    s = slide()
    cover_picture(s, ASSETS / "howrah-bridge-night.jpg", Inches(5.2), 0, Inches(8.133), H)
    shade = box(s, Inches(5.2), 0, Inches(1.4), H, BLACK)
    shade.fill.fore_color.rgb = BLACK
    s.shapes.add_picture(str(ASSETS / "lockup-night.png"), Inches(0.6), Inches(0.9), height=Inches(0.62))
    text(s, Inches(0.6), Inches(2.0), Inches(6.2), Inches(2.4), [
        ("থামিয়ে নয়,", 54, WHITE, True),
        ("সামলে।", 54, TAXI, True),
    ])
    text(s, Inches(0.6), Inches(4.35), Inches(6.0), Inches(2.0), [
        ("Keep Kolkata moving.", 24, WHITE, True),
        ("One live picture of Kolkata's roads, rain and crowds for the traffic police, KMC, disaster response and "
         "ambulance (108) crews. The AI proposes; a named officer decides.", 15, T2, False),
    ])
    text(s, Inches(0.6), Inches(6.55), Inches(6), Inches(0.3),
         [("Open source (MIT) · runs on one on-premises AI computer · github.com/shubro18202758/sahoshi", 11, T3, False)])
    text(s, Inches(7.2), Inches(7.08), Inches(5.9), Inches(0.3), [(credit("howrah-bridge-night"), 9, T3, False, PP_ALIGN.RIGHT)])

    # 2 · the problem
    s = slide()
    kicker_title(s, "THE PROBLEM", "Kolkata loses its roads to the same few shocks, every year")
    cards = [
        ("251.6 mm", "of rain in 24 h on 22–23 Sep 2025 — the heaviest in about four decades; roads went under within the hour, 8–12 people died, most by electrocution in waterlogged streets (IMD; Reuters/PTI)."),
        ("High tide", "closes the outfall gates on the Hooghly — the same rain waterlogs far faster when it meets a high tide."),
        ("10,000+", "police a day on Durga Puja duty, about 30% on traffic, with ad-hoc one-ways and goods-vehicle bans (Kolkata Police, 2025)."),
        ("≈ 1 lakh", "vehicles a day on Howrah Bridge alone; one breakdown cascades across both banks."),
        ("15–45 min", "corridor freezes for VIP movements between Nabanna, the city and the airport."),
        ("One picture missing", "traffic police, KMC, WBSDMA, the power utility and ambulance (108) each hold a piece — coordination runs on phone and radio."),
    ]
    for i, (big, body) in enumerate(cards):
        cx = Inches(0.6) + (i % 3) * Inches(4.1)
        cy = Inches(2.05) + (i // 3) * Inches(2.4)
        box(s, cx, cy, Inches(3.9), Inches(2.2), S1)
        text(s, cx + Inches(0.25), cy + Inches(0.22), Inches(3.45), Inches(1.9), [
            (big, 24, WHITE, True), (body, 12, T2, False)])
    footer(s, n)

    # 3 · the answer
    s = slide()
    kicker_title(s, "SAHOSHI", "See · Decide · Act — one shared, Bengali-first picture")
    steps = [
        ("See", "Roads, live traffic, rain, the Hooghly tide, pumps, IMD/NDMA alerts, Bengali and English news, field reports spoken in Bengali, camera road state — on one map."),
        ("Look ahead", "Corridor congestion forecast 15–120 min ahead with uncertainty; a waterlogging nowcast ranks every road by risk with its lead time."),
        ("Decide", "One proposal at a time with what changes if approved: a diversion, a signal-timing change tested in a traffic twin, a rolling hold instead of a freeze, an ambulance window, a live-wire hazard request."),
        ("Act", "A named officer approves or rejects — nothing acts on its own; no answer, the plan holds. Advisories go out in বাংলা, English and हिंदी, read aloud."),
    ]
    for i, (h, b) in enumerate(steps):
        cx = Inches(0.6) + i * Inches(3.1)
        box(s, cx, Inches(2.05), Inches(2.9), Inches(3.3), S1)
        text(s, cx + Inches(0.22), Inches(2.25), Inches(2.5), Inches(3.0), [(h, 20, WHITE, True), (b, 12, T2, False)])
    picture(s, SHOTS / "home.jpg", Inches(0.6), Inches(5.55), Inches(12.1), Inches(1.35), label="home.jpg")
    footer(s, n)

    # 4 · map: waterlogging + forecast
    s = slide()
    kicker_title(s, "THE LIVE MAP", "Waterlogging risk and the next two hours, on every road")
    picture(s, SHOTS / "map-waterlogging.jpg", Inches(0.6), Inches(1.9), Inches(7.6), Inches(4.75), label="map-waterlogging.jpg")
    text(s, Inches(8.5), Inches(1.95), Inches(4.3), Inches(4.8), [
        ("Rain × tide × terrain × pumps", 16, WHITE, True),
        ("Rain: Open-Meteo, LIVE. Tide: Hooghly model at Garden Reach, MODELLED. Terrain: Copernicus 30 m DEM and OSM drains. Pumps: KMC FFEWS adapter, EMULATED until access.", 12, T2, False),
        ("Risk class 0–3 per road, depth band, lead time to deep water — and the drivers behind it, each labelled.", 12, T2, False),
        ("Forecast", 16, WHITE, True),
        ("Chronos-2 forecasts every corridor 15–120 min ahead with p10–p90 bands; crossings of 0.8 V/C become diversion proposals before the queue forms. SIMULATED traffic until Kolkata traffic is recorded.", 12, T2, False),
    ])
    footer(s, n)

    # 5 · decide
    s = slide()
    kicker_title(s, "DECIDE", "The AI proposes. A named officer decides.")
    picture(s, SHOTS / "decide-ai.jpg", Inches(0.6), Inches(1.9), Inches(7.6), Inches(4.75), label="decide-ai.jpg")
    text(s, Inches(8.5), Inches(1.95), Inches(4.3), Inches(4.8), [
        ("Tested before it is shown", 16, WHITE, True),
        ("Every signal-timing proposal is simulated in a cell-transmission traffic twin of Kolkata against doing nothing: delay, queues, cross streets, the whole network. It is offered only if it helps without moving the jam.", 12, T2, False),
        ("Accountable", 16, WHITE, True),
        ("Evidence, what changes, confidence and assumptions on every card. Approve or reject is recorded with the officer's name. No answer: the current plan holds.", 12, T2, False),
        ("Explained in two languages", 16, WHITE, True),
        ("A local language model writes the rationale in English and Bengali; any number not in the twin's metrics is rejected.", 12, T2, False),
    ])
    footer(s, n)

    # 6 · field: voice + vision
    s = slide()
    kicker_title(s, "FROM THE FIELD", "Bengali voice reports and camera road state")
    picture(s, SHOTS / "voice-report.jpg", Inches(0.6), Inches(1.9), Inches(6.0), Inches(3.75), label="voice-report.jpg")
    picture(s, SHOTS / "road-state.jpg", Inches(6.75), Inches(1.9), Inches(6.0), Inches(3.75), label="road-state.jpg")
    text(s, Inches(0.6), Inches(5.8), Inches(6.0), Inches(1.2), [
        ("An officer speaks in Bengali; the on-premises speech model returns place · kind · severity with the transcript — an unverified field report for a named officer to confirm. Audio is not stored.", 12, T2, False)])
    text(s, Inches(6.75), Inches(5.8), Inches(6.0), Inches(1.2), [
        ("Qwen3-VL reads waterlogged / blocked / tree-fall / stalled bus / clear — roads and vehicles only. It refuses any question about people and never reads plates.", 12, T2, False)])
    footer(s, n)

    # 7 · citizens
    s = slide()
    kicker_title(s, "FOR CITIZENS", "Check your road — in বাংলা, read aloud")
    picture(s, SHOTS / "citizen.jpg", Inches(0.6), Inches(1.9), Inches(3.2), Inches(4.95), label="citizen.jpg")
    picture(s, SHOTS / "driver.jpg", Inches(4.0), Inches(1.9), Inches(3.2), Inches(4.95), label="driver.jpg")
    text(s, Inches(7.6), Inches(1.95), Inches(5.2), Inches(4.9), [
        ("Plain words, own language", 16, WHITE, True),
        ("Waterlogging on your road, the tide and the rain, holds and diversions — in বাংলা, English and हिंदी, with a Listen button (synthetic voice).", 12, T2, False),
        ("Honest by design", 16, WHITE, True),
        ("Anything simulated or emulated says so; an officer's unverified report never reaches the public page.", 12, T2, False),
        ("Ambulance (108) crews", 16, WHITE, True),
        ("A one-tap green-corridor request that a named duty officer approves.", 12, T2, False),
    ])
    footer(s, n)

    # 8 · AI stack
    s = slide()
    kicker_title(s, "OPEN, ON-PREMISES AI", "2025–26 open-source models, all on one computer in the control room")
    rows = [
        ("Forecast", "Chronos-2 (Apache-2.0)", "Zero-shot corridor forecasts; error 55% below the seasonal baseline in backtest (SIMULATED history)"),
        ("Waterlogging", "Rain × tide × DEM × pumps", "Replay of 22–23 Sep 2025 on IMD-observed rain: 13 of 13 reported places flagged"),
        ("Signal twin", "Cell-transmission model + Webster / max-pressure", "Shockwave speed within 0.2% of theory; a 30-min city run in 0.12 s"),
        ("Speech", "Bengali Whisper (Apache-2.0), Svara-TTS", "11.5% word error, place matched 53/60 (synthetic round trip)"),
        ("Vision", "Qwen3-VL-8B (Apache-2.0)", "11 of 12 road states right; 9 of 9 refusal probes refused"),
        ("Assistant", "Local Gemma-class LLM + retrieval", "Answers grounded in the live picture; numbers checked against tool results"),
    ]
    y = Inches(1.95)
    for a, b, c in rows:
        box(s, Inches(0.6), y, Inches(12.1), Inches(0.72), S1)
        text(s, Inches(0.8), y + Inches(0.18), Inches(2.1), Inches(0.5), [(a, 14, WHITE, True)])
        text(s, Inches(2.9), y + Inches(0.18), Inches(3.9), Inches(0.5), [(b, 12, T2, False)])
        text(s, Inches(6.9), y + Inches(0.18), Inches(5.7), Inches(0.5), [(c, 12, T2, False)])
        y += Inches(0.8)
    text(s, Inches(0.6), Inches(6.75), Inches(12), Inches(0.3),
         [("No data leaves the control room; it keeps working when the internet fails in a cyclone. No licence fees.", 12, T3, False)])
    footer(s, n)

    # 9 · impact (modelled)
    s = slide()
    kicker_title(s, "EXPECTED IMPACT · MODELLED", "Delay grows with the square of a freeze — so rolling holds change everything")
    sc = imp["scenarios"]
    vip = imp["vip_corridor_central"]
    amb = imp["ambulance"]
    figs = [
        (f"{sc['central']['reduction_factor']:,.0f}×",
         f"less junction-freeze delay (central case; range {sc['conservative']['reduction_factor']:,.0f}×–{sc['optimistic']['reduction_factor']:,.0f}×)"),
        (f"{fmt(vip['commuter_minutes_baseline'])} → {fmt(vip['commuter_minutes_platform'])}",
         f"commuter-minutes per VIP movement on the Nabanna → airport corridor ({vip['junctions']} junctions, {vip['km']:.0f} km)"),
        (f"≈ {fmt(amb['minutes_returned_per_year'])}", "golden-hour minutes a year returned to ambulance (108) trips"),
        ("45–120 min", "warning before a road goes under (2025 replay, IMD rain)"),
    ]
    for i, (big, lab) in enumerate(figs):
        cx = Inches(0.6) + (i % 2) * Inches(6.1)
        cy = Inches(2.05) + (i // 2) * Inches(2.25)
        box(s, cx, cy, Inches(5.9), Inches(2.05), S1)
        text(s, cx + Inches(0.3), cy + Inches(0.25), Inches(5.3), Inches(1.7), [(big, 34, WHITE, True), (lab, 13, T2, False)])
    text(s, Inches(0.6), Inches(6.62), Inches(12), Inches(0.4),
         [("Model outputs on Kolkata's OpenStreetMap network under stated assumptions (IMPACT_REPORT.md) — not field measurements, and never a claim about lives saved.", 11, T3, False)])
    footer(s, n)

    # 10 · guardrails
    s = slide()
    kicker_title(s, "GUARDRAILS", "Built to strengthen public institutions — safely")
    rules = [
        ("Vehicles only", "No faces, no persons, no tracking of individuals. Number plates stay masked until a named duty officer is on duty."),
        ("Human in charge", "The AI only proposes. A named officer approves every action; with no answer, the current plan holds. Every decision is audited."),
        ("Honest labels", "LIVE, MODELLED, SIMULATED, EMULATED — on every number and every feed that is not yet connected."),
        ("Events, not people", "News and social signals are aggregate, about places and situations; posters are never stored or scored."),
        ("Fair enforcement", "No e-challan can be approved against a theft victim; penalties are recommendations a human reviews."),
        ("Data stays home", "On-premises, retention limits, in the spirit of the DPDP Act 2023."),
    ]
    for i, (h, b) in enumerate(rules):
        cx = Inches(0.6) + (i % 3) * Inches(4.1)
        cy = Inches(2.05) + (i // 3) * Inches(2.35)
        box(s, cx, cy, Inches(3.9), Inches(2.15), S1)
        text(s, cx + Inches(0.25), cy + Inches(0.22), Inches(3.45), Inches(1.9), [(h, 17, WHITE, True), (b, 12, T2, False)])
    footer(s, n)

    # 11 · plan + cost
    s = slide()
    kicker_title(s, "IMPLEMENTATION", "A 12-month pilot through one monsoon and one Durga Puja")
    plan = [
        ("Month 0–1", "Read-only data MoU: Kolkata Traffic Police, KMC (FFEWS), WBSDMA, ambulance (108); nodal officers named."),
        ("Month 1–2", "Install the on-premises unit; City Pack finalised for the pilot division; adapters switched from EMULATED to LIVE."),
        ("Month 2–4", "Shadow mode: Sahoshi proposes, officers work as usual; weekly comparison."),
        ("Month 5–12", "Live pilot (e.g. Esplanade – Park Street – Rashbehari – Gariahat) through the monsoon and Puja; officers approve."),
        ("Month 12", "Independent review; city-wide roll-out over the next year."),
    ]
    y = Inches(1.95)
    for a, b in plan:
        text(s, Inches(0.6), y, Inches(1.6), Inches(0.6), [(a, 13, WHITE, True)])
        text(s, Inches(2.2), y, Inches(5.3), Inches(0.9), [(b, 12, T2, False)])
        y += Inches(0.9)
    box(s, Inches(7.9), Inches(1.95), Inches(4.8), Inches(4.75), S1)
    text(s, Inches(8.15), Inches(2.15), Inches(4.3), Inches(4.4), [
        ("Cost", 18, WHITE, True),
        ("Pilot, 12 months: ≈ ₹45–55 lakh", 14, WHITE, True),
        ("Two on-premises AI units ₹8–10 lakh · engineering ₹29 lakh · optional sensors ₹4 lakh · training ₹2 lakh · 15% contingency.", 12, T2, False),
        ("City-wide, two years: ≈ ₹2–2.5 crore", 14, WHITE, True),
        ("Running cost ≈ ₹40–60 lakh a year.", 12, T2, False),
        ("Software licences: ₹0", 14, WHITE, True),
        ("Open models, OpenStreetMap, Sahoshi under MIT — existing CCTV, control rooms and FFEWS sensors are reused.", 12, T2, False),
    ])
    footer(s, n)

    # 12 · scalability
    s = slide()
    kicker_title(s, "SCALABILITY", "A city is a folder")
    text(s, Inches(0.6), Inches(1.95), Inches(6.2), Inches(4.8), [
        ("The engine — live picture, forecasting, nowcast, voice, vision, decision loop, console — is the same everywhere. "
         "A City Pack holds what differs: the OpenStreetMap extract and corridors, gazetteer, agencies and emergency numbers, plate format, "
         "UI languages, local scenarios and impact parameters.", 13, T2, False),
        ("The prototype proves it: it was first built for another Indian city, and the same build tools now produce Kolkata; a test builds both.", 13, T2, False),
        ("Per district: about 1–2 weeks of local data work, local adapters (CCTV, signals, flood sensors) and local SOPs. The software, models and hardware stay the same.", 13, T2, False),
    ])
    nxt = [("Howrah · Bidhannagar", "already inside the Kolkata pack"), ("Siliguri", "gateway to the North-East; NH10/NH31 choke-points"),
           ("Asansol–Durgapur", "industrial corridor"), ("Patna · Ranchi", "Bihar and Jharkhand; Hindi already first-class")]
    for i, (a, b) in enumerate(nxt):
        cy = Inches(1.95) + i * Inches(1.18)
        box(s, Inches(7.4), cy, Inches(5.3), Inches(1.0), S1)
        text(s, Inches(7.65), cy + Inches(0.15), Inches(4.9), Inches(0.8), [(a, 15, WHITE, True), (b, 11, T2, False)])
    footer(s, n)

    # 13 · evidence
    s = slide()
    kicker_title(s, "EVIDENCE", "It runs today")
    ev = [
        ("Working prototype", "Console, citizen and driver pages, five AI services and the traffic twin, on one on-premises unit."),
        ("Real Kolkata roads", "49 junctions, 65 road segments, 125 km from OpenStreetMap; the Nabanna → airport route is 29 km."),
        ("Thousands of automated tests", "Python suites, the console's unit and browser tests, contract replays and Rust tests — run on every change."),
        ("Open source", "github.com/shubro18202758/sahoshi — setup, technical design, sample data and test cases."),
    ]
    for i, (h, b) in enumerate(ev):
        cy = Inches(1.95) + i * Inches(1.2)
        text(s, Inches(0.6), cy, Inches(5.8), Inches(1.1), [(h, 16, WHITE, True), (b, 12, T2, False)])
    picture(s, SHOTS / "replay-2025-09-23.jpg", Inches(6.8), Inches(1.95), Inches(5.9), Inches(3.7), label="replay-2025-09-23.jpg")
    text(s, Inches(6.8), Inches(5.75), Inches(5.9), Inches(0.9),
         [("Replay of 22–23 Sep 2025 on IMD-observed rain (OBSERVED rain, MODELLED ponding): every news-reported waterlogged place on the network was flagged — the night almost the whole city flooded.", 11, T3, False)])
    footer(s, n)

    # 14 · thank you
    s = slide()
    cover_picture(s, ASSETS / "hooghly-dusk.jpg", 0, 0, W, H)
    veil = box(s, 0, 0, W, H, BLACK)
    veil.fill.fore_color.rgb = BLACK
    # semi-transparent veil
    sp = veil.fill._xPr.find(qn("a:solidFill"))
    clr = sp[0]
    alpha = clr.makeelement(qn("a:alpha"), {"val": "62000"})
    clr.append(alpha)
    s.shapes.add_picture(str(ASSETS / "lockup-stacked-night.png"), Inches(5.42), Inches(1.4), height=Inches(1.6))
    text(s, Inches(1.5), Inches(3.45), Inches(10.33), Inches(1.4), [("ধন্যবাদ", 54, WHITE, True, PP_ALIGN.CENTER)])
    text(s, Inches(1.5), Inches(4.65), Inches(10.33), Inches(1.4), [
        ("Thank you", 26, WHITE, True, PP_ALIGN.CENTER),
        ("github.com/shubro18202758/sahoshi", 14, T2, False, PP_ALIGN.CENTER),
    ])
    text(s, Inches(1.5), Inches(7.05), Inches(10.33), Inches(0.3), [(credit("hooghly-dusk"), 9, T3, False, PP_ALIGN.CENTER)])

    prs.save(OUT)
    print("wrote", OUT, n, "slides")


if __name__ == "__main__":
    build()
