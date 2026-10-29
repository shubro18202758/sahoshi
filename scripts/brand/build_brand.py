#!/usr/bin/env python3
"""Sahoshi identity: the mark, the wordmark, the lockups, the app icon and the favicon — generated from this one file.

Pure python3 stdlib, deterministic. Text is never set with a font at run time: the wordmark outlines come from
glyphs.json (Inter, SIL OFL 1.1, outlined once by outline_text.py).

THE MARK — a route that steers, drawn as an S.
  One chamfered centreline draws a geometric S on the 64 grid (the chamfers keep Howrah Bridge's angular steel in the
  bends). It is stroked as one continuous road of constant width with round ends: traffic is never stopped, it is
  steered round the bends. Past the road's far end sits one dot in the accent blue (#276EF1): the place the movement
  is steered to. Everything else is white on night, black on paper, currentColor in mono. That dot is the ONLY colour
  in the identity: no warm hue (never the decision orange or the alert red), no gradient, no filter, no image.
  At 32 px and below the solid mark (a heavier road, a larger dot) stands in.

Run:  python3 build_brand.py [outdir]     (default: services/command-deck/static/brand)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'services', 'command-deck', 'static', 'brand')

ACCENT = '#276EF1'       # the one accent: links and the AI in the deck, the destination dot in the mark
INK = '#FFFFFF'          # night ink
PAPER_INK = '#000000'    # day ink
TILE = '#000000'
TILE_EDGE = '#FFFFFF'    # the app icon's hairline (at 14 % opacity) keeps the tile's edge on a black home screen

with open(os.path.join(HERE, 'glyphs.json'), encoding='utf-8') as fh:
    GLYPHS = json.load(fh)


def f(v):
    s = f'{v:.2f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def pd(P, close=False):
    return 'M' + 'L'.join(f'{f(x)} {f(y)}' for x, y in P) + ('Z' if close else '')


# ── geometry ──────────────────────────────────────────────────────────────────────────────────────────────────
T, B, L, R, C = 13.0, 51.0, 14.0, 50.0, 8.5     # top and bottom bar, left and right side, chamfer
M = (T + B) / 2
W_ROAD = 8.0       # the road's width (the mark at 40 px and up)
W_SOLID = 9.5      # the solid mark's road (32 px and below): heavier, so it holds at 16 px
DOT = (L - 0.5, B) # the destination: past the road's far end, on the bottom bar's line
GAP = 6.0          # the clear space between the road's end cap and the dot

# the road: from the top bar's open end (right) round both bends to the bottom bar, stopping short of the dot
CENTRE = [(R, T), (L + C, T), (L, T + C), (L, M - C), (L + C, M), (R - C, M), (R, M + C), (R, B - C), (R - C, B)]


def road_path(end_x):
    pts = CENTRE + [(end_x, B)]
    return pd(pts)


def mark_body(col, accent, road=W_ROAD, dot_r=None):
    """The S road in `col`, the destination dot in `accent`."""
    r = dot_r if dot_r is not None else road * 0.62
    end_x = DOT[0] + r + GAP + road / 2
    return (f'<path d="{road_path(end_x)}" fill="none" stroke="{col}" stroke-width="{f(road)}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{f(DOT[0])}" cy="{f(DOT[1])}" r="{f(r)}" fill="{accent}"/>')


def mark_full(col, accent):
    return mark_body(col, accent)


def mark_solid(col, accent):
    """The small-size mark (≤ 32 px): the same S, a heavier road and a larger dot, so both hold at 16 px."""
    return mark_body(col, accent, W_SOLID, W_SOLID * 0.66)


# ── text ──────────────────────────────────────────────────────────────────────────────────────────────────────
def text(key, x, baseline, scale, col):
    g = GLYPHS[key]
    return f'<path transform="translate({f(x)} {f(baseline)}) scale({f(scale)})" d="{g["d"]}" fill="{col}"/>', g['advance'] * scale


def svg(w, h, body, label=None, extra=''):
    lab = f' role="img" aria-label="{label}"' if label else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" width="{f(w)}" height="{f(h)}"{lab}{extra}>'
            f'{body}</svg>\n')


LABEL = 'Sahoshi'


def word(x, cap_top, cap, ink):
    """'Sahoshi' set with cap height `cap` from `cap_top`; returns (svg, width)."""
    la = GLYPHS['latin']
    k = cap / la['cap']
    p, w = text('latin', x - la['bbox'][0] * k, cap_top + cap, k, ink)
    return p, (la['bbox'][2] - la['bbox'][0]) * k


def mark_g(inner, x, y, size):
    return f'<g transform="translate({f(x)} {f(y)}) scale({f(size / 64)})">{inner}</g>'


def lockup(ink, mark_col, accent, mono=False):
    """The horizontal lockup: the mark, then 'Sahoshi' with its cap height at 36 % of the mark."""
    h = 64
    body = mark_g(mark_full(mark_col, accent), 0, 0, 64)
    cap = 23.0
    words, w = word(74, (h - cap) / 2, cap, ink)
    W = 74 + w + 2
    extra = ' fill="currentColor"' if mono else ''
    return svg(W, h, body + words, LABEL, extra)


def stacked(ink, mark_col, accent):
    cap = 26.0
    la = GLYPHS['latin']
    wl = (la['bbox'][2] - la['bbox'][0]) * cap / la['cap']
    W = max(wl, 104) + 24
    msize = 104
    body = mark_g(mark_full(mark_col, accent), (W - msize) / 2, 0, msize)
    words, _ = word((W - wl) / 2, msize + 14, cap, ink)
    return svg(W, msize + 14 + cap + 6, body + words, LABEL)


def wordmark(ink):
    cap = 26.0
    words, w = word(2, 12, cap, ink)
    return svg(w + 4, 50, words, LABEL)


def app_icon():
    # black tile, the white S road and the blue destination; a hairline keeps the tile's edge on a black home screen
    return svg(64, 64, f'<rect width="64" height="64" rx="15" fill="{TILE}"/>'
               f'<rect x=".75" y=".75" width="62.5" height="62.5" rx="14.25" fill="none" stroke="{TILE_EDGE}" stroke-opacity=".14" stroke-width="1.5"/>'
               + mark_g(mark_full(INK, ACCENT), 8, 8, 48), LABEL)


def favicon():
    # the tab icon: the solid mark (the heavier road holds at 16 px), white and blue on a black tile
    return svg(32, 32, f'<rect width="32" height="32" rx="7" fill="{TILE}"/>' + mark_g(mark_solid(INK, ACCENT), 2, 2, 28))


FILES = {
    'sahoshi-mark': lambda: svg(64, 64, mark_full(INK, ACCENT), LABEL),
    'sahoshi-mark-day': lambda: svg(64, 64, mark_full(PAPER_INK, ACCENT), LABEL),
    'sahoshi-mark-mono': lambda: svg(64, 64, mark_full('currentColor', 'currentColor'), LABEL),
    'sahoshi-mark-solid': lambda: svg(64, 64, mark_solid(INK, ACCENT), LABEL),
    'sahoshi-wordmark': lambda: wordmark(INK),
    'sahoshi-wordmark-day': lambda: wordmark(PAPER_INK),
    'sahoshi-lockup': lambda: lockup(INK, INK, ACCENT),
    'sahoshi-lockup-day': lambda: lockup(PAPER_INK, PAPER_INK, ACCENT),
    'sahoshi-lockup-mono': lambda: lockup('currentColor', 'currentColor', 'currentColor', True),
    'sahoshi-lockup-stacked': lambda: stacked(INK, INK, ACCENT),
    'sahoshi-lockup-stacked-day': lambda: stacked(PAPER_INK, PAPER_INK, ACCENT),
    'sahoshi-app-icon': app_icon,
    'favicon': favicon,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in FILES.items():
        with open(os.path.join(OUT, f'{name}.svg'), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(fn())
    print('ok', len(FILES), 'brand files →', OUT)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        OUT = os.path.abspath(sys.argv[1])
    main()
