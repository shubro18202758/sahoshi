#!/usr/bin/env python3
"""Sahoshi identity: the mark, the wordmark, the lockups, the app icon and the favicon — generated from this one file.

Pure python3 stdlib, deterministic. Text is never set with a font at run time: the wordmark outlines come from
glyphs.json (Inter and Noto Sans Bengali, both SIL OFL 1.1, outlined once by outline_text.py).

THE MARK — Howrah Bridge folded into an S.
  One chamfered centreline draws a geometric S on the 64 grid; it is offset into a band of constant width. The band is
  the bridge, read from the top: the anchor arm (the top bar, a Warren truss), the first tower (the upper bend, solid),
  the suspended span (the middle bar, a truss), the second tower (the lower bend, solid), the far anchor arm (the bottom
  bar, a truss). Free ends close with an end post, as the bridge's do. At 32 px and below the solid S stands in.

COLOUR — Kolkata-taxi yellow (#FFC800) belongs to the mark (and the landing hero) only; it is never a UI meaning colour.
  Its hue (47°) sits far from the deck's decision orange (#FF9F43, 30°) and alert red. Paper (day) versions are black;
  the mono version is currentColor. No gradient, no filter, no image.

Run:  python3 build_brand.py [outdir]     (default: services/command-deck/static/brand)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'services', 'command-deck', 'static', 'brand')

TAXI = '#FFC800'        # Kolkata-taxi yellow: the mark and the landing hero only
INK = '#FFFFFF'         # night ink
PAPER_INK = '#000000'   # day ink
SUB = '#9A9A9A'         # the Bengali line on night
SUB_DAY = '#4D4D4D'     # the Bengali line on paper
TILE = '#000000'

with open(os.path.join(HERE, 'glyphs.json'), encoding='utf-8') as fh:
    GLYPHS = json.load(fh)


def f(v):
    s = f'{v:.2f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def pd(P, close=False):
    return 'M' + 'L'.join(f'{f(x)} {f(y)}' for x, y in P) + ('Z' if close else '')


# ── geometry ──────────────────────────────────────────────────────────────────────────────────────────────────
T, B, L, R, C = 14.0, 50.0, 15.0, 49.0, 7.5     # top and bottom bar, left and right side, chamfer
M = (T + B) / 2
H = 6.0          # half the band (chord centre to chord centre)
CW = 3.4         # chord weight
DW = 2.6         # diagonal weight
EXT = 1.5        # the free ends reach a little past the sides
HB = H + CW / 2  # the band's outer half width

CENTRE = [(R + EXT, T), (L + C, T), (L, T + C), (L, M - C), (L + C, M), (R - C, M), (R, M + C), (R, B - C), (R - C, B), (L - EXT, B)]


def offset(P, d):
    """An open polyline offset by d along its left normal, with mitred joins (keeps the band's width constant)."""
    def nrm(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        return (-dy / n, dx / n)
    out = []
    for i in range(len(P)):
        if i == 0:
            n = nrm(P[0], P[1])
        elif i == len(P) - 1:
            n = nrm(P[-2], P[-1])
        else:
            n1, n2 = nrm(P[i - 1], P[i]), nrm(P[i], P[i + 1])
            mx, my = n1[0] + n2[0], n1[1] + n2[1]
            k = math.hypot(mx, my)
            mx, my = mx / k, my / k
            s = 1 / (mx * n1[0] + my * n1[1])
            out.append((P[i][0] + mx * d * s, P[i][1] + my * d * s))
            continue
        out.append((P[i][0] + n[0] * d, P[i][1] + n[1] * d))
    return out


def band(i0, i1, half):
    """The band between centreline vertices i0..i1 as one closed polygon."""
    A, Bo = offset(CENTRE, half), offset(CENTRE, -half)
    return A[i0:i1 + 1] + list(reversed(Bo[i0:i1 + 1]))


def clip(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman: a polygon clipped to the rectangle [x0, x1] x [y0, y1]."""
    def cut(P, inside, cross):
        out = []
        for i in range(len(P)):
            a, b = P[i - 1], P[i]
            if inside(b):
                if not inside(a):
                    out.append(cross(a, b))
                out.append(b)
            elif inside(a):
                out.append(cross(a, b))
        return out

    def at_x(X):
        return lambda a, b: (X, a[1] + (b[1] - a[1]) * (X - a[0]) / (b[0] - a[0]))

    def at_y(Y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (Y - a[1]) / (b[1] - a[1]), Y)
    P = poly
    P = cut(P, lambda p: p[0] >= x0, at_x(x0))
    P = cut(P, lambda p: p[0] <= x1, at_x(x1))
    P = cut(P, lambda p: p[1] >= y0, at_y(y0))
    P = cut(P, lambda p: p[1] <= y1, at_y(y1))
    return P


def mark_truss(col):
    """Towers (the two bends) solid; spans (the three bars) as Warren trusses between two chords."""
    full = band(0, len(CENTRE) - 1, HB)
    towers = pd(clip(full, -99, T - HB - 1, L + C, M + HB + .5), True) + pd(clip(full, R - C, M - HB - .5, 99, B + HB + 1), True)
    spans = [(L + C, R + EXT, T, 4), (L + C, R - C, M, 3), (L - EXT, R - C, B, 4)]
    chords, web = '', ''
    for x0, x1, y, n in spans:
        chords += f'M{f(x0)} {f(y - H)}H{f(x1)}M{f(x0)} {f(y + H)}H{f(x1)}'
        web += pd([(x0 + (x1 - x0) * k / n, y + (H if k % 2 == 0 else -H)) for k in range(n + 1)])
    chords += f'M{f(R + EXT)} {f(T - H)}V{f(T + H)}M{f(L - EXT)} {f(B - H)}V{f(B + H)}'
    return (f'<path d="{towers}" fill="{col}"/>'
            f'<path d="{chords}" fill="none" stroke="{col}" stroke-width="{f(CW)}" stroke-linecap="square"/>'
            f'<path d="{web}" fill="none" stroke="{col}" stroke-width="{f(DW)}" stroke-linecap="round" stroke-linejoin="round"/>')


def mark_solid(col, half=5.5):
    """The small-size S (≤ 32 px): the same centreline, a slimmer band, so the counters stay open at 16 px."""
    return f'<path d="{pd(band(0, len(CENTRE) - 1, half), True)}" fill="{col}"/>'


# ── text ──────────────────────────────────────────────────────────────────────────────────────────────────────
def text(key, x, baseline, scale, col):
    g = GLYPHS[key]
    return f'<path transform="translate({f(x)} {f(baseline)}) scale({f(scale)})" d="{g["d"]}" fill="{col}"/>', g['advance'] * scale


def svg(w, h, body, label=None, extra=''):
    lab = f' role="img" aria-label="{label}"' if label else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" width="{f(w)}" height="{f(h)}"{lab}{extra}>'
            f'{body}</svg>\n')


LABEL = 'Sahoshi'
LABEL_BI = 'Sahoshi (সাহসী)'


def wordmark_parts(x, cap_top, cap, ink, sub, gap_ratio=.55):
    """'Sahoshi' with cap height `cap` from `cap_top`, a hairline, then 'সাহসী' on the same baseline."""
    la = GLYPHS['latin']
    k = cap / la['cap']
    base = cap_top + cap
    p1, w1 = text('latin', x - la['bbox'][0] * k, base, k, ink)
    gap = cap * gap_ratio
    rx = x + w1 + gap
    rule = f'<rect x="{f(rx)}" y="{f(cap_top - cap * .08)}" width="{f(max(1, cap * .055))}" height="{f(cap * 1.16)}" fill="{sub}" opacity=".55"/>'
    bn = GLYPHS['bengali']
    kb = cap * .9 / bn['xh']    # the Bengali headline sits just under the Latin cap height
    p2, w2 = text('bengali', rx + gap - bn['bbox'][0] * kb, base, kb, sub)
    return p1 + rule + p2, rx + gap + (bn['bbox'][2] - bn['bbox'][0]) * kb - x


def mark_g(inner, x, y, size):
    return f'<g transform="translate({f(x)} {f(y)}) scale({f(size / 64)})">{inner}</g>'


def lockup(ink, sub, mark_col, mono=False):
    h = 64
    body = mark_g(mark_truss(mark_col), 0, 0, 64)
    cap = 23.0
    words, w = wordmark_parts(76, (h - cap) / 2 + 1, cap, ink, sub)
    W = 76 + w + 2
    extra = ' fill="currentColor"' if mono else ''
    return svg(W, h, body + words, LABEL_BI, extra)


def stacked(ink, sub, mark_col):
    la, bn = GLYPHS['latin'], GLYPHS['bengali']
    cap = 26.0
    k = cap / la['cap']
    wl = (la['bbox'][2] - la['bbox'][0]) * k
    kb = cap * .78 / bn['xh']
    wb = (bn['bbox'][2] - bn['bbox'][0]) * kb
    W = max(wl, wb, 104) + 24
    msize = 104
    body = mark_g(mark_truss(mark_col), (W - msize) / 2, 0, msize)
    y1 = msize + 14 + cap
    p1, _ = text('latin', (W - wl) / 2 - la['bbox'][0] * k, y1, k, ink)
    y2 = y1 + 12 + la['bbox'][3] * k - bn['bbox'][1] * kb
    p2, _ = text('bengali', (W - wb) / 2 - bn['bbox'][0] * kb, y2, kb, sub)
    Hh = y2 + bn['bbox'][3] * kb + 4
    return svg(W, Hh, body + p1 + p2, LABEL_BI)


def wordmark(ink, sub):
    cap = 26.0
    words, w = wordmark_parts(2, 12, cap, ink, sub)
    return svg(w + 4, 50, words, LABEL_BI)


def app_icon():
    # black tile, the truss S in taxi yellow; a hairline keeps the tile's edge on a black home screen
    return svg(64, 64, f'<rect width="64" height="64" rx="15" fill="{TILE}"/>'
               f'<rect x=".75" y=".75" width="62.5" height="62.5" rx="14.25" fill="none" stroke="#FFFFFF" stroke-opacity=".14" stroke-width="1.5"/>'
               + mark_g(mark_truss(TAXI), 6.4, 6.4, 51.2), LABEL)


def favicon():
    # the tab icon: the solid S (the truss would close up at 16 px), taxi yellow on a black tile
    return svg(32, 32, f'<rect width="32" height="32" rx="7" fill="{TILE}"/>' + mark_g(mark_solid(TAXI), 1.6, 1.6, 28.8))


FILES = {
    'sahoshi-mark': lambda: svg(64, 64, mark_truss(TAXI), LABEL),
    'sahoshi-mark-day': lambda: svg(64, 64, mark_truss(PAPER_INK), LABEL),
    'sahoshi-mark-mono': lambda: svg(64, 64, mark_truss('currentColor'), LABEL),
    'sahoshi-mark-solid': lambda: svg(64, 64, mark_solid(TAXI), LABEL),
    'sahoshi-wordmark': lambda: wordmark(INK, SUB),
    'sahoshi-wordmark-day': lambda: wordmark(PAPER_INK, SUB_DAY),
    'sahoshi-lockup': lambda: lockup(INK, SUB, TAXI),
    'sahoshi-lockup-day': lambda: lockup(PAPER_INK, SUB_DAY, PAPER_INK),
    'sahoshi-lockup-mono': lambda: lockup('currentColor', 'currentColor', 'currentColor'),
    'sahoshi-lockup-stacked': lambda: stacked(INK, SUB, TAXI),
    'sahoshi-lockup-stacked-day': lambda: stacked(PAPER_INK, SUB_DAY, PAPER_INK),
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
