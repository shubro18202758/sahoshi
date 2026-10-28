#!/usr/bin/env python3
"""Sahoshi artwork — vehicle product shots, event key art and Kolkata scenes, generated from this one file.

Pure python3 stdlib, deterministic (seeded), writes plain SVG (gradients, highlights, shadows, SVG filters).

  vehicles/<class>.svg   480 x 300  studio product shots, 3/4 front view, one camera and one key light for the set
  events/<kind>.svg      640 x 360  16:9 key art: a graded, near-monochrome Kolkata scene with depth and ONE accent,
                                    the kind's meaning colour (route teal for corridor work, clear green for the 108
                                    corridor, alert red for a stolen / watchlisted vehicle, a white key light for
                                    reported situations that no one has verified)
  scenes/<name>.svg      960 x 320  wide city scenes for the Home greeting (dawn, day, dusk, night, all-clear): the Hooghly,
                                    Howrah Bridge across it, Vidyasagar Setu downstream, the Victoria Memorial on the far bank

Rules: vehicles and places only — people appear only as distant, abstract crowd masses, never a face or an individual;
no text or numerals inside an image; no camera frames; no navy or purple; every file labelled (role="img" + aria-label).

Run:  python3 build_artwork.py [outdir]     (default: services/command-deck/static/artwork)
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'services', 'command-deck', 'static', 'artwork')

# ── meaning accents (the deck's frozen roles) ───────────────────────────────────────────────────────────────
TEAL = '#2DD4BF'
GREEN = '#3CCB7F'
RED = '#FF5C61'
WHITE = '#FFFFFF'


# ── number + colour helpers ─────────────────────────────────────────────────────────────────────────────────
def f1(v):
    s = f'{v:.1f}'
    if s.endswith('.0'):
        s = s[:-2]
    return '0' if s in ('-0', '-0.0') else s


def hx(c):
    c = c.lstrip('#')
    if len(c) == 3:
        c = ''.join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    return '#' + ''.join(f'{max(0, min(255, int(round(v)))):02X}' for v in rgb)


def mix(a, b, t):
    A, B = hx(a), hx(b)
    return to_hex(tuple(A[i] + (B[i] - A[i]) * t for i in range(3)))


def scale(c, k):
    return to_hex(tuple(v * k for v in hx(c)))


def pts(ps):
    return ' '.join(f'{f1(x)},{f1(y)}' for x, y in ps)


# ── SVG document ────────────────────────────────────────────────────────────────────────────────────────────
class Svg:
    def __init__(self, w, h, label):
        self.w, self.h, self.label = w, h, label
        self.defs, self.body, self.n, self._blur, self._memo = [], [], 0, {}, {}

    def uid(self, p):
        self.n += 1
        return f'{p}{self.n}'

    def _stops(self, stops):
        out = []
        for s in stops:
            o, c = s[0], s[1]
            a = s[2] if len(s) > 2 else 1
            out.append(f'<stop offset="{f1(o * 100)}%" stop-color="{c}"' + (f' stop-opacity="{a:g}"' if a != 1 else '') + '/>')
        return ''.join(out)

    def lin(self, stops, x1=0, y1=0, x2=0, y2=1, user=False):
        key = ('l', tuple(map(tuple, stops)), x1, y1, x2, y2, user)
        if key in self._memo:
            return self._memo[key]
        i = self.uid('g')
        self._memo[key] = f'url(#{i})'
        u = ' gradientUnits="userSpaceOnUse"' if user else ''
        co = (f1(x1), f1(y1), f1(x2), f1(y2)) if user else (f'{x1:g}', f'{y1:g}', f'{x2:g}', f'{y2:g}')
        self.defs.append(f'<linearGradient id="{i}" x1="{co[0]}" y1="{co[1]}" x2="{co[2]}" y2="{co[3]}"{u}>{self._stops(stops)}</linearGradient>')
        return f'url(#{i})'

    def rad(self, stops, cx=.5, cy=.5, r=.5, user=False, fx=None, fy=None):
        key = ('r', tuple(map(tuple, stops)), cx, cy, r, user, fx, fy)
        if key in self._memo:
            return self._memo[key]
        i = self.uid('r')
        self._memo[key] = f'url(#{i})'
        u = ' gradientUnits="userSpaceOnUse"' if user else ''
        fmt = f1 if user else (lambda v: f'{v:g}')
        foc = (f' fx="{fmt(fx)}" fy="{fmt(fy)}"' if fx is not None else '')
        self.defs.append(f'<radialGradient id="{i}" cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}"{foc}{u}>{self._stops(stops)}</radialGradient>')
        return f'url(#{i})'

    def blur(self, sd):
        key = round(sd, 1)
        if key not in self._blur:
            i = self.uid('b')
            self.defs.append(f'<filter id="{i}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{f1(key)}"/></filter>')
            self._blur[key] = f'url(#{i})'
        return self._blur[key]

    def raw_def(self, s):
        self.defs.append(s)

    def add(self, s):
        self.body.append(s)

    def render(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
                f'role="img" aria-label="{self.label}"><defs>{"".join(self.defs)}</defs>{"".join(self.body)}</svg>\n')


# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
#  VEHICLES — a tiny 3D studio: extruded, rounded profiles, one camera, one key light, flat-shaded strips.
# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def vnorm(a):
    m = math.sqrt(vdot(a, a)) or 1
    return (a[0] / m, a[1] / m, a[2] / m)


LIGHT = vnorm((0.55, 0.5, 0.85))      # key light: above, front, near side — the same for every vehicle
LOD = {'smooth': 2, 'circle': 28}                   # corner-cutting passes; a multi-vehicle composition draws one pass less


class Cam:
    """x = vehicle forward, y = vehicle left (the near side), z = up. The camera sits front-left, a little high."""

    def __init__(self, az=34, el=12, dist=26, target=(0, 0, 0.9), f=1.0):
        a, e = math.radians(az), math.radians(el)
        self.eye = (target[0] + dist * math.cos(a) * math.cos(e), target[1] + dist * math.sin(a) * math.cos(e), target[2] + dist * math.sin(e))
        self.fwd = vnorm(vsub(target, self.eye))
        self.right = vnorm(vcross(self.fwd, (0, 0, 1)))
        self.up = vcross(self.right, self.fwd)
        self.f = f * dist
        self.half = vnorm(vsub(LIGHT, self.fwd))   # Blinn half vector (light + view)

    def p(self, P):
        d = vsub(P, self.eye)
        z = vdot(d, self.fwd)
        return (self.f * vdot(d, self.right) / z, -self.f * vdot(d, self.up) / z)

    def depth(self, P):
        return vdot(vsub(P, self.eye), self.fwd)

    def facing(self, n, P):
        return vdot(n, vsub(self.eye, P)) > 0


def shade(base, n, cam, amb=0.34, dif=0.5, sky=0.3, spec=0.55, shin=28):
    d = max(0.0, vdot(n, LIGHT))
    s = (0.5 + 0.5 * n[2])
    h = max(0.0, vdot(n, cam.half)) ** shin
    B = hx(base)
    k = amb + dif * d + sky * s
    return to_hex(tuple(B[i] * k + 255 * spec * h for i in range(3)))


def chaikin(poly, n=2, keep=()):
    """Corner-cutting on a closed polygon of (x, z, tag); indexes in `keep` stay sharp."""
    pts_ = [(p[0], p[1], p[2], i in keep) for i, p in enumerate(poly)]
    for _ in range(n):
        out = []
        L = len(pts_)
        for i in range(L):
            a, b = pts_[i], pts_[(i + 1) % L]
            if a[3]:
                out.append(a)
            else:
                out.append((a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25, a[2], False))
            if b[3]:
                out.append((a[0] * .5 + b[0] * .5, a[1] * .5 + b[1] * .5, a[2], False))
            else:
                out.append((a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75, a[2], False))
        pts_ = out
    return [(p[0], p[1], p[2]) for p in pts_]


class Studio:
    """Collects 2D draw ops in camera space; fits them into the frame on render."""

    def __init__(self, label, w=480, h=300, cam=None):
        self.svg = Svg(w, h, label)
        self.cam = cam or Cam()
        self.ops = []     # (layer, depth, kind, payload)
        self.bounds = []

    # payload helpers store camera-space 2D points; the fit transform is applied in render()
    def poly(self, P3, fill, layer=5, depth=None, extra='', bound=True, stroke=None):
        P2 = [self.cam.p(p) for p in P3]
        if bound:
            self.bounds.extend(P2)
        d = depth if depth is not None else sum(self.cam.depth(p) for p in P3) / len(P3)
        self.ops.append((layer, -d, 'poly', (P2, fill, extra, stroke)))

    def line(self, P3, stroke, width, layer=7, extra='', depth=0):
        P2 = [self.cam.p(p) for p in P3]
        self.ops.append((layer, depth, 'line', (P2, stroke, width, extra)))



def circle3(c, r, axis='y', n=None, start=0, end=2 * math.pi):
    """A circle in the x-z plane (wheel) at y = c[1]; or in the x-y plane (axis='z')."""
    n = n or LOD['circle']
    out = []
    for i in range(n + 1 if end - start < 2 * math.pi - 1e-6 else n):
        a = start + (end - start) * i / (n if end - start < 2 * math.pi - 1e-6 else n)
        if axis == 'y':
            out.append((c[0] + r * math.cos(a), c[1], c[2] + r * math.sin(a)))
        else:
            out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2]))
    return out


def hull(points):
    P = sorted(set((round(x, 3), round(y, 3)) for x, y in points))
    if len(P) < 3:
        return P

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


class Vehicle:
    """Builders for one vehicle in a Studio. All lengths in metres."""

    def __init__(self, st, origin=(0, 0, 0)):
        self.st, self.cam, self.o = st, st.cam, origin

    def P(self, x, y, z):
        return (x + self.o[0], y + self.o[1], z + self.o[2])

    # ── an extruded, rounded body ─────────────────────────────────────────────
    def body(self, prof, hw, paint, *, glass=(), smooth=2, keep=(), side=None, layer=5, matte=False, sidepaint=None, edge=True):
        """prof: [(x, z, tag)] closed outline seen from the near side; hw(x, z) half width; tags in `glass` draw as glass."""
        cam = self.cam
        P = chaikin(prof, min(smooth, LOD['smooth']), keep)
        area = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))
        sgn = 1 if area > 0 else -1
        sheen = []
        for i in range(len(P)):
            a, b = P[i], P[(i + 1) % len(P)]
            dx, dz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dz) or 1
            n = (sgn * dz / L, 0, -sgn * dx / L)
            ha, hb = hw(a[0], a[1]), hw(b[0], b[1])
            q = [self.P(a[0], ha, a[1]), self.P(b[0], hb, b[1]), self.P(b[0], -hb, b[1]), self.P(a[0], -ha, a[1])]
            c = tuple(sum(v[k] for v in q) / 4 for k in range(3))
            if not cam.facing(n, c):
                continue
            if a[2] in glass:
                col = shade('#262B30', n, cam, amb=.42, dif=.12, sky=.5, spec=.7, shin=40)
                sheen.extend(cam.p(v_) for v_ in q)
            elif matte:
                col = shade(paint, n, cam, spec=.08)
            else:
                col = shade(paint, n, cam)
            self.st.poly(q, col, layer=layer, stroke=col)
        if sheen:
            sv_ = self.st.svg
            g = sv_.lin([(0, WHITE, 0), (.34, WHITE, 0), (.36, WHITE, .28), (.5, WHITE, .1), (.52, WHITE, 0), (.62, WHITE, 0), (.64, WHITE, .12), (.7, WHITE, 0)], 0, 0, 1, .5)
            self.st.ops.append((layer, 500, 'poly', (hull(sheen), g, '', None)))
        # the near side panel: car-paint reflection — sky above the shoulder, a sharp horizon, darker ground below
        sp = sidepaint or paint
        side3 = [self.P(p[0], hw(p[0], p[1]), p[1]) for p in P]
        zs = [p[1] for p in P]
        if side is None:
            g = self.st.svg.lin([(0, mix(sp, WHITE, .35)), (.34, mix(sp, WHITE, .12)), (.52, sp), (.55, scale(sp, .78)),
                                 (.86, scale(sp, .5)), (1, scale(sp, .36))])
        else:
            g = side
        self.st.poly(side3, g, layer=layer + 1, depth=-1e3)
        if edge:
            # the shoulder catch-light along the top of the side panel
            top = [p for p in P if p[1] > min(zs) + (max(zs) - min(zs)) * .45]
            if len(top) > 2:
                self.st.line([self.P(p[0], hw(p[0], p[1]) + .004, p[1]) for p in top], WHITE, 1.1, layer=layer + 2, extra=' stroke-opacity=".38"')
        return P

    def side_poly(self, xz, hw, fill, layer=8, dy=.006):
        self.st.poly([self.P(x, hw(x, z) + dy, z) for x, z in xz], fill, layer=layer, depth=-1e3)

    def glass_side(self, xz, hw, layer=8):
        sv = self.st.svg
        g = sv.lin([(0, '#5E6872'), (.28, '#2B3138'), (.3, '#3A424A'), (.62, '#1B1F24'), (1, '#121519')], 0, 0, .35, 1)
        self.side_poly(xz, hw, g, layer=layer)
        self.side_poly(xz, hw, sv.lin([(0, WHITE, 0), (.42, WHITE, 0), (.44, WHITE, .2), (.58, WHITE, .05), (.6, WHITE, 0)], 0, 0, 1, .4), layer=layer, dy=.007)
        # trim: the black window surround
        self.st.ops.append((layer, -1e3, 'poly', ([self.cam.p(self.P(x, hw(x, z) + .005, z)) for x, z in xz], 'none',
                                                   ' stroke="#0B0C0E" stroke-width="1.6" stroke-linejoin="round"', None)))

    def front_face(self, x, yz, fill, layer=9):
        """A feature on the vehicle's front plane at x: yz = [(y, z)]."""
        self.st.poly([self.P(x, y, z) for y, z in yz], fill, layer=layer, depth=-1e3)

    def wheel(self, x, y, r, z=None, width=.24, near=True, rim='#C9CDD2', spokes=5, layer=None):
        """A wheel on the near (y>0, outer face at y) or far side."""
        z = r if z is None else z
        st, sv = self.st, self.st.svg
        sgn = 1 if near else -1
        outer = circle3(self.P(x, y, z), r)
        inner = circle3(self.P(x, y - sgn * width, z), r)
        L = (layer if layer is not None else (12 if near else 2))
        h2 = hull([self.cam.p(p) for p in outer + inner])
        st.ops.append((L, 0, 'poly', (h2, '#0D0D0E', '', None)))
        st.bounds.extend(h2)
        if not near:
            return
        st.poly(outer, sv.rad([(0, '#2A2A2C'), (.8, '#1C1C1E'), (1, '#111112')]), layer=L, depth=-1)
        # the rim: a brushed-metal dish and dark gaps between the spokes
        rr = r * .64
        st.poly(circle3(self.P(x, y + .01, z), rr), sv.lin([(0, mix(rim, WHITE, .5)), (.5, rim), (1, scale(rim, .55))], 0, 0, .6, 1), layer=L, depth=-2)
        for k in range(spokes):
            a0 = 2 * math.pi * k / spokes + .35
            a1 = a0 + 2 * math.pi / spokes * .58
            gap = [(x + rr * .88 * math.cos(a0 + t * (a1 - a0)), y + .012, z + rr * .88 * math.sin(a0 + t * (a1 - a0))) for t in (0, .5, 1)]
            gap += [(x + rr * .3 * math.cos(a1), y + .012, z + rr * .3 * math.sin(a1)), (x + rr * .3 * math.cos(a0), y + .012, z + rr * .3 * math.sin(a0))]
            st.poly([self.P(*p) for p in gap], '#17181A', layer=L, depth=-3)
        st.poly(circle3(self.P(x, y + .014, z), rr * .2, n=12), scale(rim, .7), layer=L, depth=-4)

    def arch(self, x, y, r, z):
        pts3 = [self.P(x + r * math.cos(a), y + .003, max(z + r * math.sin(a), .12)) for a in [i * math.pi / 14 for i in range(15)]]
        self.st.poly(pts3, '#0A0A0B', layer=9, depth=-1e3)

    def lamp(self, x, yz, glow=WHITE, layer=10, lit=True, color=None):
        sv = self.st.svg
        fill = color or sv.lin([(0, '#FFFFFF'), (.6, '#E6EBF0'), (1, '#9AA3AC')], 0, 0, 1, 1)
        self.front_face(x, yz, fill, layer=layer)
        if lit:
            cy_ = sum(z for _, z in yz) / len(yz)
            cyy = sum(y for y, _ in yz) / len(yz)
            c = self.cam.p(self.P(x + .05, cyy, cy_))
            self.st.ops.append((layer + 1, 0, 'glow', (c, glow)))

    def shadow(self, x0, x1, hw, extra=.28):
        P = [self.P(x1 + extra, hw + extra, 0), self.P(x0 - extra, hw + extra, 0), self.P(x0 - extra, -hw - extra, 0), self.P(x1 + extra, -hw - extra, 0)]
        P2 = [self.cam.p(p) for p in P]
        self.st.ops.append((0, 0, 'shadow', (P2,)))


def studio_render(st, **kw):
    sv = st.svg
    xs = [p[0] for p in st.bounds]
    ys = [p[1] for p in st.bounds]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W, H = sv.w, sv.h
    pad = kw.get('pad', (24, 26, 24, 40))
    aw, ah = W - pad[0] - pad[2], H - pad[1] - pad[3]
    s = min(aw / (x1 - x0), ah / (y1 - y0))
    tx = pad[0] + (aw - (x1 - x0) * s) / 2 - x0 * s
    ty = H - pad[3] - y1 * s

    def T(p):
        return (p[0] * s + tx, p[1] * s + ty)
    cx = (x0 + x1) / 2 * s + tx
    gy = H - pad[3]
    # the studio floor: a soft pool of light (reads on a dark ground, invisible on paper)
    sv.add(f'<ellipse cx="{f1(cx)}" cy="{f1(gy - 4)}" rx="{f1(W * .47)}" ry="{f1(H * .17)}" '
           f'fill="{sv.rad([(0, WHITE, .12), (.5, WHITE, .045), (1, WHITE, 0)])}"/>')
    sv.add('<g stroke-width=".7" stroke-linejoin="round">')
    for layer, _d, kind, pl in sorted(st.ops, key=lambda o: (o[0], o[1])):
        if kind == 'poly':
            P2, fill, extra, stroke = pl
            stv = f' stroke="{stroke}"' if stroke else ''
            sv.add(f'<polygon points="{pts(T(p) for p in P2)}" fill="{fill}"{stv}{extra}/>')
        elif kind == 'line':
            P2, stroke, width, extra = pl
            sv.add(f'<polyline points="{pts(T(p) for p in P2)}" fill="none" stroke="{stroke}" stroke-width="{f1(width)}" '
                   f'stroke-linecap="round" stroke-linejoin="round"{extra}/>')
        elif kind == 'shadow':
            P2 = [T(p) for p in pl[0]]
            sv.add(f'<polygon points="{pts(P2)}" fill="#000" opacity=".5" filter="{sv.blur(9)}"/>')
            # contact shadow: tighter and darker, hugging the footprint
            c = (sum(p[0] for p in P2) / 4, sum(p[1] for p in P2) / 4)
            P3 = [(c[0] + (p[0] - c[0]) * .86, c[1] + (p[1] - c[1]) * .7) for p in P2]
            sv.add(f'<polygon points="{pts(P3)}" fill="#000" opacity=".62" filter="{sv.blur(3.5)}"/>')
        elif kind == 'glow':
            c, col = pl
            p = T(c)
            sv.add(f'<circle cx="{f1(p[0])}" cy="{f1(p[1])}" r="{f1(s * .16)}" fill="{col}" opacity=".34" filter="{sv.blur(s * .09)}"/>')
        elif kind == 'beam':
            c, col, r = pl
            p = T(c)
            sv.add(f'<circle cx="{f1(p[0])}" cy="{f1(p[1])}" r="{f1(s * r * .7)}" fill="{col}" opacity=".6" filter="{sv.blur(s * r * .4)}"/>')
    sv.add('</g>')
    return sv.render()


# ── profiles ────────────────────────────────────────────────────────────────────────────────────────────────
def hw_car(base=.87, belt=1.0, tumble=.38, nose=1.85, nose_in=.06):
    def f(x, z):
        w = base
        if z > belt:
            w -= (z - belt) * tumble
        if x > nose:
            w -= (x - nose) * nose_in * 4
        return w
    return f


def sedan(v, paint, x=0.0, plate_dark=False):
    hw = hw_car()
    prof = [(2.02, .3, 'b'), (2.13, .46, 'b'), (2.1, .68, 'b'), (1.9, .82, 'b'), (1.0, .97, 'g'),
            (.2, 1.44, 'b'), (-.02, 1.5, 'b'), (-.95, 1.48, 'g'), (-1.6, 1.08, 'b'), (-1.96, 1.04, 'b'), (-2.1, .95, 'b'),
            (-2.15, .56, 'b'), (-2.05, .3, 'b')]
    v.body(prof, hw, paint, glass=('g',))
    _car_common(v, hw, wheel_x=(1.3, -1.32), r=.33, dlo=[(.9, 1.02), (.18, 1.4), (-.92, 1.42), (-1.5, 1.05), (-1.1, 1.02)],
                bpillar=-.3, doors=(.94, -.3, -1.45), handle_z=.9)
    _car_front(v, hw, xf=2.1, lz=(.68, .78), gz=(.44, .62))
    v.shadow(-2.15, 2.13, .87)


def _car_common(v, hw, wheel_x, r, dlo, bpillar, doors, handle_z, track=.8, rim='#C9CDD2', lower=.34):
    sv = v.st.svg
    for wx in wheel_x:
        v.wheel(wx, -track, r, near=False)
    for wx in wheel_x:
        v.arch(wx, hw(wx, .5), r * 1.2, r)
        v.wheel(wx, track + .07, r, rim=rim)
    v.glass_side(dlo, hw)
    # B-pillar
    zt = max(z for _, z in dlo) - .02
    v.side_poly([(bpillar + .06, .99), (bpillar + .1, zt), (bpillar - .04, zt), (bpillar - .08, .99)], hw, '#0B0C0E', layer=9)
    for dx in doors:
        v.st.line([v.P(dx, hw(dx, .5) + .006, lower), v.P(dx - .02, hw(dx, .9) + .006, .98)], '#000', .9, layer=9, extra=' stroke-opacity=".45"')
    for hx_ in (doors[0] - .5, doors[1] - .5):
        v.side_poly([(hx_, handle_z), (hx_ - .2, handle_z), (hx_ - .2, handle_z - .04), (hx_, handle_z - .04)], hw, '#E9ECEF', layer=9, dy=.01)
    # the character line: a crisp highlight crease just under the windows
    v.st.line([v.P(wheel_x[0] + r * 1.6, hw(wheel_x[0], .9) + .007, .9 - .02), v.P(wheel_x[1] - r * 1.4, hw(wheel_x[1], .9) + .007, .9 + .02)], WHITE, 1, layer=9, extra=' stroke-opacity=".5"')
    # rocker shadow
    v.side_poly([(wheel_x[0] - r * 1.25, lower + .02), (wheel_x[1] + r * 1.25, lower + .02), (wheel_x[1] + r * 1.25, lower - .06), (wheel_x[0] - r * 1.25, lower - .06)], hw,
                sv.lin([(0, '#000', .0), (1, '#000', .55)]), layer=9)


def _car_front(v, hw, xf, lz=(.66, .76), gz=(.42, .6), lamp_y=(.52, .84), grille_w=.42):
    sv = v.st.svg
    # grille (dark, with a soft gloss) and lower intake
    v.front_face(xf + .02, [(grille_w, gz[1]), (-grille_w, gz[1]), (-grille_w + .04, gz[0]), (grille_w - .04, gz[0])],
                 sv.lin([(0, '#3A3D41'), (1, '#0E0F11')]))
    v.front_face(xf + .03, [(.36, .4), (-.36, .4), (-.32, .33), (.32, .33)], '#0E0F11')
    # headlamps — slim LED units, lit
    v.lamp(xf - .1, [(lamp_y[1], lz[1]), (lamp_y[0], lz[1] - .01), (lamp_y[0] + .02, lz[0]), (lamp_y[1] - .04, lz[0] + .02)])
    v.lamp(xf - .1, [(-lamp_y[0], lz[1] - .01), (-lamp_y[1], lz[1]), (-lamp_y[1] + .04, lz[0] + .02), (-lamp_y[0] - .02, lz[0])])
    # mirror on the near side
    v.st.poly([v.P(.66, .86, 1.0), v.P(.5, 1.06, 1.04), v.P(.42, 1.06, .95), v.P(.58, .86, .93)], '#141518', layer=11, depth=-1e3)


def suv(v, paint, sidepaint=None, livery=None):
    hw = hw_car(base=.95, belt=1.12, tumble=.3)
    prof = [(2.25, .42, 'b'), (2.36, .6, 'b'), (2.34, .9, 'b'), (2.14, 1.08, 'b'), (1.2, 1.18, 'b'), (.82, 1.22, 'g'),
            (.12, 1.74, 'b'), (-.1, 1.8, 'b'), (-2.05, 1.78, 'b'), (-2.25, 1.62, 'g'), (-2.36, 1.18, 'b'), (-2.38, .7, 'b'), (-2.28, .42, 'b')]
    v.body(prof, hw, paint, glass=('g',), sidepaint=sidepaint)
    if livery:
        livery(v, hw)
    _car_common(v, hw, wheel_x=(1.45, -1.48), r=.38, dlo=[(.76, 1.24), (.08, 1.68), (-2.05, 1.7), (-2.18, 1.26)],
                bpillar=-.42, doors=(.78, -.42, -1.55), handle_z=1.08, track=.84, lower=.5)
    v.side_poly([(-1.62, 1.25), (-1.66, 1.68), (-1.76, 1.68), (-1.72, 1.25)], hw, '#0B0C0E', layer=9)
    _car_front(v, hw, xf=2.34, lz=(.86, .98), gz=(.58, .84), lamp_y=(.5, .86), grille_w=.46)
    # roof rails
    for yy in (.66, -.66):
        v.st.line([v.P(.0, yy, 1.83), v.P(-1.95, yy, 1.82)], '#2A2C2F', 2.2, layer=6 if yy < 0 else 12)
    v.shadow(-2.38, 2.36, .95)


def car(v):
    sedan(v, '#C4C9CE')


def lightbar(v, x, z, hw_, colors=('#E8EEF4', '#E8EEF4')):
    sv = v.st.svg
    prof = [(x + .22, z, 'b'), (x + .2, z + .12, 'b'), (x - .2, z + .12, 'b'), (x - .22, z, 'b')]
    v.body(prof, lambda X, Z: hw_, '#1E2024', smooth=1, layer=13, edge=False,
           side=sv.lin([(0, '#3A3F46'), (1, '#16181B')]))
    # the lens segments (glowing)
    for i, c in enumerate(colors):
        y0 = hw_ - .02 - i * hw_
        v.st.poly([v.P(x + .23, y0, z + .02), v.P(x + .23, y0 - hw_ + .06, z + .02), v.P(x + .23, y0 - hw_ + .06, z + .1), v.P(x + .23, y0, z + .1)],
                  c, layer=14, depth=-1e3)
        v.st.ops.append((15, 0, 'beam', (v.cam.p(v.P(x + .25, y0 - hw_ / 2, z + .07)), c, .3)))


def patrol(v):
    sv = v.st.svg

    def liv(v_, hw):
        # a generic patrol livery: a deep band along the waist, a thin bright pinstripe (no insignia, no words)
        v_.side_poly([(2.28, .88), (-2.36, .88), (-2.36, .7), (2.3, .7)], hw, sv.lin([(0, '#33373D'), (1, '#1C1F23')]), layer=8)
        v_.side_poly([(2.28, .93), (-2.36, .93), (-2.36, .9), (2.29, .9)], hw, '#276EF1', layer=8)
    suv(v, '#E9ECEF', livery=liv)
    lightbar(v, -.55, 1.82, .5, colors=('#3B82F6', '#EF4444'))


def ambulance(v):
    sv = v.st.svg
    hw = hw_car(base=1.0, belt=1.25, tumble=.08, nose=2.3)
    # a high-roof van (the familiar 108 shape): short bonnet, tall box
    prof = [(2.55, .4, 'b'), (2.68, .6, 'b'), (2.66, .95, 'b'), (2.4, 1.12, 'b'), (1.75, 1.26, 'g'), (1.2, 2.2, 'b'), (.9, 2.42, 'b'),
            (-2.6, 2.44, 'b'), (-2.72, 2.32, 'b'), (-2.75, .5, 'b'), (-2.62, .4, 'b')]
    v.body(prof, hw, '#F1F3F5', glass=('g',), keep=(7, 8, 9))
    # livery: a red waist band, a chequered yellow band beneath (generic emergency livery; no words, no emblem)
    v.side_poly([(2.62, 1.12), (-2.74, 1.12), (-2.74, .96), (2.66, .96)], hw, sv.lin([(0, '#E2353B'), (1, '#B5242A')]), layer=8)
    for i in range(14):
        x0 = 2.4 - i * .37
        col = '#F2C230' if i % 2 == 0 else '#F7F7F7'
        v.side_poly([(x0, .94), (x0 - .37, .94), (x0 - .37, .8), (x0, .8)], hw, col, layer=8)
    for wx in (1.75, -1.8):
        v.wheel(wx, -.86, .36, near=False)
    for wx in (1.75, -1.8):
        v.arch(wx, hw(wx, .5), .44, .36)
        v.wheel(wx, .93, .36)
    v.glass_side([(1.6, 1.3), (1.12, 2.08), (.55, 2.1), (.5, 1.32)], hw)
    v.glass_side([(-.2, 1.5), (-.2, 2.04), (-1.6, 2.04), (-1.6, 1.5)], hw)
    v.side_poly([(-.32, 1.06), (-.32, 2.26), (-.36, 2.26), (-.36, 1.06)], hw, '#000', layer=9)
    v.lamp(2.62, [(.8, 1.0), (.5, 1.0), (.5, .9), (.8, .9)])
    v.lamp(2.62, [(-.5, 1.0), (-.8, 1.0), (-.8, .9), (-.5, .9)])
    v.front_face(2.7, [(.42, .86), (-.42, .86), (-.4, .66), (.4, .66)], sv.lin([(0, '#3A3D41'), (1, '#0E0F11')]))
    v.front_face(2.72, [(.6, .58), (-.6, .58), (-.56, .46), (.56, .46)], '#1A1B1E')
    lightbar(v, 1.0, 2.43, .55, colors=('#EF4444', '#3B82F6'))
    v.st.poly([v.P(1.7, .98, 1.3), v.P(1.5, 1.16, 1.36), v.P(1.42, 1.16, 1.2), v.P(1.62, .98, 1.18)], '#141518', layer=11, depth=-1e3)
    v.shadow(-2.75, 2.68, 1.0)


def fire_tender(v):
    sv = v.st.svg
    hw = lambda x, z: 1.18
    red = '#C9252B'
    # cab
    cab = [(3.7, .55, 'b'), (3.82, .8, 'b'), (3.8, 1.5, 'b'), (3.62, 1.6, 'g'), (3.5, 2.6, 'b'), (3.3, 2.75, 'b'), (2.0, 2.78, 'b'), (1.9, .55, 'b')]
    v.body(cab, hw, red, glass=('g',), keep=(6, 7))
    # body box with lockers
    box = [(1.85, .6, 'b'), (1.85, 2.5, 'b'), (-3.6, 2.5, 'b'), (-3.7, .6, 'b')]
    v.body(box, lambda x, z: 1.2, red, smooth=1, keep=(0, 1, 2, 3))
    for i in range(4):
        x0 = 1.6 - i * 1.3
        v.side_poly([(x0, 2.3), (x0 - 1.15, 2.3), (x0 - 1.15, 1.0), (x0, 1.0)], lambda x, z: 1.2,
                    sv.lin([(0, '#D8DDE2'), (.5, '#A9B0B7'), (1, '#7E868E')], 0, 0, 0, 1), layer=8)
        for k in range(6):
            zz = 1.08 + k * .2
            v.side_poly([(x0 - .04, zz + .06), (x0 - 1.11, zz + .06), (x0 - 1.11, zz + .03), (x0 - .04, zz + .03)], lambda x, z: 1.2, '#5E666E', layer=9)
    # a reflective white waist stripe
    v.side_poly([(3.8, 1.02), (-3.68, 1.02), (-3.68, .9), (3.8, .9)], lambda x, z: 1.2, '#F2F4F6', layer=10)
    # the ladder on the roof
    for yy in (.62, -.62):
        v.st.line([v.P(2.6, yy, 2.98), v.P(-3.4, yy, 2.72)], '#D7DCE1', 3, layer=6 if yy < 0 else 14)
    for i in range(13):
        xx = 2.5 - i * .46
        zz = 2.98 - (2.98 - 2.72) * (2.6 - xx) / 6.0
        v.st.line([v.P(xx, .62, zz), v.P(xx, -.62, zz)], '#AEB5BC', 1.4, layer=13)
    v.st.line([v.P(2.6, .62, 2.98), v.P(2.6, .62, 2.78)], '#AEB5BC', 2, layer=14)
    for wx in (2.6, -1.9, -2.9):
        v.wheel(wx, -1.06, .52, near=False)
    for wx in (2.6, -1.9, -2.9):
        v.arch(wx, 1.18, .6, .52)
        v.wheel(wx, 1.14, .52, rim='#B9BFC5', spokes=8)
    v.glass_side([(3.66, 1.68), (3.48, 2.5), (2.2, 2.52), (2.2, 1.68)], hw)
    v.front_face(3.84, [(.86, 1.25), (-.86, 1.25), (-.86, .9), (.86, .9)], sv.lin([(0, '#D5DADF'), (1, '#6A727A')]))
    v.lamp(3.84, [(1.1, 1.2), (.9, 1.2), (.9, .98), (1.1, .98)])
    v.lamp(3.84, [(-.9, 1.2), (-1.1, 1.2), (-1.1, .98), (-.9, .98)])
    v.front_face(3.86, [(1.18, .72), (-1.18, .72), (-1.18, .55), (1.18, .55)], '#C7CDD3')
    lightbar(v, 2.7, 2.78, .7, colors=('#EF4444', '#EF4444'))
    v.shadow(-3.7, 3.82, 1.2)


def bus(v):
    sv = v.st.svg
    hw = lambda x, z: 1.27 - max(0, z - 2.6) * .2
    prof = [(5.95, .42, 'b'), (6.05, .7, 'b'), (6.05, 1.3, 'g'), (5.98, 2.75, 'b'), (5.8, 3.05, 'b'), (-5.8, 3.05, 'b'), (-6.0, 2.85, 'b'),
            (-6.05, .5, 'b'), (-5.9, .38, 'b')]
    v.body(prof, hw, '#E7EAED', glass=('g',), keep=())
    # a continuous glazing band (dark glass), a slim waist band, the door
    v.glass_side([(5.7, 1.4), (5.7, 2.62), (-5.75, 2.62), (-5.75, 1.4)], hw)
    for i in range(8):
        x0 = 4.3 - i * 1.32
        v.side_poly([(x0, 1.38), (x0, 2.64), (x0 - .07, 2.64), (x0 - .07, 1.38)], hw, '#0B0C0E', layer=9)
    v.side_poly([(5.9, 1.22), (-6.0, 1.22), (-6.0, 1.1), (5.95, 1.1)], hw, '#2F5F8F', layer=8)
    v.side_poly([(5.92, 1.06), (-6.02, 1.06), (-6.02, .5), (5.92, .5)], hw, sv.lin([(0, '#6FA3D2'), (1, '#3F77AD')]), layer=8)
    v.side_poly([(5.4, .52), (5.4, 2.6), (4.5, 2.6), (4.5, .52)], hw, sv.lin([(0, '#3A424A'), (1, '#15181B')]), layer=10)
    v.side_poly([(4.97, .52), (4.97, 2.6), (4.93, 2.6), (4.93, .52)], hw, '#0B0C0E', layer=11)
    for wx in (4.1, -3.4):
        v.wheel(wx, -1.12, .5, near=False)
    for wx in (4.1, -3.4):
        v.arch(wx, 1.27, .6, .5)
        v.wheel(wx, 1.2, .5, rim='#B9BFC5', spokes=8)
    v.lamp(6.05, [(1.12, .9), (.82, .9), (.82, .76), (1.12, .76)])
    v.lamp(6.05, [(-.82, .9), (-1.12, .9), (-1.12, .76), (-.82, .76)])
    v.shadow(-6.05, 6.05, 1.27)


def truck(v):
    sv = v.st.svg
    hw = lambda x, z: 1.2 - max(0, z - 2.2) * .12
    # a cab-over truck: flat-faced cab, cargo body with ribbed sides
    cab = [(2.7, .62, 'b'), (2.86, .9, 'b'), (2.86, 1.55, 'g'), (2.74, 2.55, 'b'), (2.55, 2.72, 'b'), (1.0, 2.75, 'b'), (.96, .62, 'b')]
    v.body(cab, hw, '#E4E7EA', glass=('g',), keep=(5, 6))
    box = [(.82, .9, 'b'), (.82, 3.05, 'b'), (-4.6, 3.05, 'b'), (-4.6, .9, 'b')]
    v.body(box, lambda x, z: 1.25, '#8D959C', smooth=1, keep=(0, 1, 2, 3),
           side=sv.lin([(0, '#B9C0C6'), (.5, '#9AA2A9'), (1, '#6C747B')]))
    for i in range(15):
        x0 = .6 - i * .35
        v.side_poly([(x0, 2.95), (x0 - .05, 2.95), (x0 - .05, 1.0), (x0, 1.0)], lambda x, z: 1.25, '#7A828A', layer=9)
    v.side_poly([(.82, .9), (-4.6, .9), (-4.6, .72), (.82, .72)], lambda x, z: 1.25, '#2A2D31', layer=9)
    v.glass_side([(2.8, 1.62), (2.66, 2.48), (1.25, 2.5), (1.25, 1.62)], hw)
    v.front_face(2.88, [(.82, 1.35), (-.82, 1.35), (-.82, .98), (.82, .98)], sv.lin([(0, '#4A4E53'), (1, '#16181B')]))
    v.lamp(2.88, [(1.12, 1.3), (.9, 1.3), (.9, 1.08), (1.12, 1.08)])
    v.lamp(2.88, [(-.9, 1.3), (-1.12, 1.3), (-1.12, 1.08), (-.9, 1.08)])
    v.front_face(2.9, [(1.2, .82), (-1.2, .82), (-1.2, .64), (1.2, .64)], '#2B2E32')
    for wx in (1.95, -2.6, -3.6):
        v.wheel(wx, -1.02, .5, near=False)
    for wx in (1.95, -2.6, -3.6):
        v.arch(wx, 1.2, .58, .5)
        v.wheel(wx, 1.1, .5, rim='#B9BFC5', spokes=8)
    v.st.poly([v.P(2.7, 1.2, 2.1), v.P(2.6, 1.42, 2.15), v.P(2.6, 1.42, 1.7), v.P(2.7, 1.2, 1.68)], '#141518', layer=13, depth=-1e3)
    v.shadow(-4.6, 2.9, 1.25)


def tempo(v):
    sv = v.st.svg
    hw = lambda x, z: .82 - max(0, z - 1.5) * .1
    # a small goods carrier: short cab, open deck with a tarp canopy
    cab = [(1.6, .5, 'b'), (1.72, .72, 'b'), (1.7, 1.08, 'g'), (1.4, 1.86, 'b'), (1.2, 1.92, 'b'), (.4, 1.92, 'b'), (.36, .5, 'b')]
    v.body(cab, hw, '#E6E9EC', glass=('g',), keep=(5, 6))
    deck = [(.3, .62, 'b'), (.3, 2.05, 'b'), (-2.4, 2.05, 'b'), (-2.45, .62, 'b')]
    v.body(deck, lambda x, z: .86, '#7E878F', smooth=1, keep=(0, 1, 2, 3), matte=True,
           side=sv.lin([(0, '#9AA2AA'), (.15, '#8A939B'), (1, '#5D656C')]))
    # tarp ropes
    for i in range(5):
        x0 = .05 - i * .55
        v.st.line([v.P(x0, .866, 2.0), v.P(x0 - .1, .866, .9)], '#4B535A', 1, layer=9)
    v.side_poly([(.3, .9), (-2.45, .9), (-2.45, .62), (.3, .62)], lambda x, z: .86, '#2A2D31', layer=9)
    v.glass_side([(1.62, 1.12), (1.36, 1.78), (.62, 1.78), (.62, 1.12)], hw)
    v.lamp(1.72, [(.74, .98), (.52, .98), (.52, .84), (.74, .84)])
    v.lamp(1.72, [(-.52, .98), (-.74, .98), (-.74, .84), (-.52, .84)])
    v.front_face(1.74, [(.4, .9), (-.4, .9), (-.4, .74), (.4, .74)], sv.lin([(0, '#3A3D41'), (1, '#0E0F11')]))
    for wx in (1.05, -1.75):
        v.wheel(wx, -.7, .3, near=False)
    for wx in (1.05, -1.75):
        v.arch(wx, .84, .36, .3)
        v.wheel(wx, .78, .3)
    v.st.poly([v.P(1.5, .82, 1.2), v.P(1.36, .98, 1.24), v.P(1.3, .98, 1.1), v.P(1.44, .82, 1.08)], '#141518', layer=11, depth=-1e3)
    v.shadow(-2.45, 1.74, .86)


def auto_rickshaw(v):
    sv = v.st.svg
    yellow = '#E9B92E'
    # the canopy: a rounded hood over an open cabin; dark inside
    hwc = lambda x, z: .66
    canopy = [(.95, 1.32, 'b'), (.9, 1.62, 'b'), (.62, 1.78, 'b'), (-1.02, 1.78, 'b'), (-1.22, 1.6, 'b'), (-1.25, .72, 'b'), (-.6, .72, 'b'), (-.55, 1.32, 'b')]
    v.body(canopy, hwc, yellow, smooth=2, keep=(5, 6, 7), matte=True,
           side=sv.lin([(0, mix(yellow, WHITE, .25)), (.25, yellow), (.6, scale(yellow, .8)), (1, scale(yellow, .62))]))
    # the open side: interior shadow inside the canopy frame
    v.side_poly([(.82, 1.36), (.76, 1.58), (.55, 1.68), (-.5, 1.68), (-.5, .9), (.82, .9)], hwc, sv.lin([(0, '#141414'), (1, '#050505')]), layer=8)
    # the lower body: black tub with a narrow front cowl
    hwb = lambda x, z: .66 if x < .3 else max(.24, .66 - (x - .3) * .5)
    tub = [(1.55, .3, 'b'), (1.62, .55, 'b'), (1.48, 1.0, 'g'), (1.3, 1.32, 'b'), (.95, 1.32, 'b'), (.82, .92, 'b'), (-1.28, .92, 'b'), (-1.3, .5, 'b'), (-1.2, .36, 'b')]
    v.body(tub, hwb, '#3B7D49', glass=('g',), smooth=2, keep=(3, 4, 5, 6))
    v.side_poly([(.82, .9), (-1.28, .9), (-1.28, .84), (.82, .84)], hwb, yellow, layer=9)
    v.side_poly([(.82, .5), (-1.28, .5), (-1.28, .44), (.82, .44)], hwb, '#F2F2F2', layer=9)
    for wx, wy in ((-.95, -.62),):
        v.wheel(wx, wy, .24, near=False)
    v.arch(-.95, .66, .3, .24)
    v.wheel(-.95, .7, .24, rim='#AEB5BC')
    v.wheel(1.42, .1, .23, rim='#AEB5BC')
    v.lamp(1.6, [(.12, .78), (-.12, .78), (-.12, .62), (.12, .62)])
    v.st.line([v.P(1.32, .3, 1.32), v.P(1.38, .5, 1.38)], '#1A1A1A', 2, layer=13)
    v.shadow(-1.3, 1.62, .66)


def two_wheeler(v):
    sv = v.st.svg
    # a parked scooter on its side stand: leg shield, floorboard, rear body under the seat, handlebar cowl
    paint = '#CDD2D7'
    for wx in (.74, -.6):
        v.wheel(wx, -.05, .24, near=False, width=.1)
    # rear body (bulbous, under the seat)
    rear = [(-.08, .34, 'b'), (-.1, .6, 'b'), (-.24, .78, 'b'), (-.98, .84, 'b'), (-1.04, .66, 'b'), (-.86, .44, 'b'), (-.4, .3, 'b')]
    v.body(rear, lambda x, z: .19, paint, smooth=2, layer=10)
    # floorboard
    v.body([(.42, .3, 'b'), (.42, .38, 'b'), (-.12, .38, 'b'), (-.12, .3, 'b')], lambda x, z: .15, '#2A2D31', smooth=1, edge=False, layer=11, matte=True)
    # seat
    v.body([(-.14, .8, 'b'), (-.18, .9, 'b'), (-.94, .94, 'b'), (-1.02, .85, 'b')], lambda x, z: .17, '#1C1E21', smooth=2, matte=True, edge=False, layer=12)
    # rear wheel, then the leg shield in front of it
    v.wheel(-.6, .12, .24, width=.1, rim='#AEB5BC', layer=13)
    # front fork and fender
    v.st.line([v.P(.74, .02, .24), v.P(.58, .02, .98)], '#1E2023', 3.2, layer=13)
    v.body([(.98, .42, 'b'), (.9, .5, 'b'), (.6, .5, 'b'), (.52, .42, 'b')], lambda x, z: .07, paint, smooth=1, layer=16, edge=False)
    shield = [(.66, .38, 'b'), (.74, .56, 'b'), (.7, .96, 'b'), (.58, 1.04, 'b'), (.44, 1.0, 'b'), (.4, .36, 'b')]
    v.body(shield, lambda x, z: .23 if z < .9 else .2, paint, smooth=2, layer=14)
    # the handlebar cowl with the headlamp
    cowl = [(.66, .98, 'b'), (.7, 1.08, 'b'), (.6, 1.16, 'b'), (.42, 1.14, 'b'), (.4, 1.0, 'b')]
    v.body(cowl, lambda x, z: .16, paint, smooth=2, layer=17)
    v.lamp(.7, [(.1, 1.1), (-.1, 1.1), (-.1, 1.02), (.1, 1.02)], layer=18)
    v.st.line([v.P(.5, -.38, 1.12), v.P(.5, .38, 1.12)], '#17181A', 3, layer=16)
    for yy in (.3, -.3):
        v.st.line([v.P(.5, yy, 1.12), v.P(.44, yy * 1.08, 1.34)], '#17181A', 1.2, layer=16)
        v.st.poly(circle3(v.P(.44, yy * 1.08, 1.36), .045, n=10), '#2A2D31', layer=16)
    v.wheel(.74, .06, .24, width=.1, rim='#AEB5BC', layer=15)
    v.st.line([v.P(-.3, .16, .3), v.P(-.2, .32, .02)], '#1E2023', 1.6, layer=14)
    v.shadow(-1.04, .98, .26, extra=.16)


def _round_lamp(v, x, y, z, r, n=12):
    v.lamp(x, [(y + r * math.cos(2 * math.pi * k / n), z + r * math.sin(2 * math.pi * k / n)) for k in range(n)])


def taxi(v):
    """The Kolkata yellow taxi: the Ambassador's rounded 1950s body — tall chrome grille, round lamps on the wings,
    an upright glasshouse, a domed roof, a full boot; chrome bumpers and hubcaps. No plate, no sign, no words."""
    sv = v.st.svg
    paint = '#F2B705'
    hw = hw_car(base=.83, belt=1.08, tumble=.34, nose=1.95, nose_in=.05)
    prof = [(2.1, .3, 'b'), (2.2, .48, 'b'), (2.2, .8, 'b'), (2.04, .94, 'b'), (1.2, 1.03, 'b'), (.66, 1.08, 'g'),
            (.26, 1.52, 'b'), (-.1, 1.62, 'b'), (-.92, 1.6, 'b'), (-1.3, 1.5, 'g'), (-1.68, 1.1, 'b'), (-2.06, 1.02, 'b'),
            (-2.22, .84, 'b'), (-2.24, .5, 'b'), (-2.12, .3, 'b')]
    v.body(prof, hw, paint, glass=('g',))
    _car_common(v, hw, wheel_x=(1.36, -1.4), r=.33, dlo=[(.64, 1.1), (.26, 1.48), (-.9, 1.54), (-1.26, 1.46), (-1.58, 1.12)],
                bpillar=-.34, doors=(.66, -.34, -1.42), handle_z=.96, rim='#E4E7EA', lower=.36)
    chrome = sv.lin([(0, '#FFFFFF'), (.45, '#C9CED3'), (.55, '#7E868E'), (1, '#D8DCE0')])
    # the grille: a tall chrome surround with vertical slats
    v.front_face(2.22, [(.4, .82), (-.4, .82), (-.4, .46), (.4, .46)], chrome)
    v.front_face(2.23, [(.34, .78), (-.34, .78), (-.34, .5), (.34, .5)], '#15171A')
    for k in range(9):
        y = -.3 + k * .075
        v.front_face(2.235, [(y + .018, .78), (y - .018, .78), (y - .018, .5), (y + .018, .5)], '#C9CED3', layer=10)
    _round_lamp(v, 2.16, .6, .76, .12)
    _round_lamp(v, 2.16, -.6, .76, .12)
    # chrome bumpers, front and rear, and the chrome waist strip
    v.front_face(2.26, [(.86, .42), (-.86, .42), (-.86, .3), (.86, .3)], chrome, layer=11)
    v.side_poly([(2.24, .42), (1.95, .42), (1.95, .3), (2.24, .3)], hw, chrome, layer=10)
    v.side_poly([(-1.95, .44), (-2.26, .44), (-2.26, .32), (-1.95, .32)], hw, chrome, layer=10)
    v.st.line([v.P(1.9, hw(1.9, .82) + .008, .82), v.P(-2.1, hw(-2.1, .82) + .008, .82)], '#E9ECEF', 1.2, layer=10, extra=' stroke-opacity=".8"')
    v.st.poly([v.P(.66, .84, 1.06), v.P(.5, 1.02, 1.1), v.P(.42, 1.02, 1.01), v.P(.58, .84, .99)], '#C9CED3', layer=11, depth=-1e3)
    v.shadow(-2.24, 2.22, .84)


def toto(v):
    """A toto (battery e-rickshaw): one front wheel under a narrow nose, a light body with a coloured skirt, a flat
    roof on slim posts over the open benches."""
    sv = v.st.svg
    body, skirt, roof = '#E3E8EC', '#5E8F6C', '#2C3034'
    hwb = lambda x, z: .5 if x < .7 else max(.2, .5 - (x - .7) * .55)
    tub = [(1.3, .3, 'b'), (1.36, .55, 'b'), (1.24, 1.02, 'g'), (1.08, 1.16, 'b'), (.7, 1.16, 'b'), (.62, .74, 'b'), (-1.3, .74, 'b'), (-1.34, .42, 'b'), (-1.22, .3, 'b')]
    v.body(tub, hwb, body, glass=('g',), smooth=2, keep=(3, 4, 5, 6))
    v.side_poly([(.62, .72), (-1.3, .72), (-1.32, .44), (.62, .44)], hwb, skirt, layer=9)
    v.side_poly([(1.3, .62), (.66, .62), (.66, .5), (1.32, .5)], hwb, skirt, layer=9)
    # the roof on four slim posts
    hwr = lambda x, z: .56
    v.body([(1.16, 1.9, 'b'), (1.16, 2.0, 'b'), (-1.42, 2.0, 'b'), (-1.42, 1.9, 'b')], hwr, roof, smooth=1, edge=False, matte=True, layer=13,
           side=sv.lin([(0, '#41464C'), (1, '#1E2125')]))
    for x in (1.0, -1.32):
        for y in (.5, -.5):
            v.st.line([v.P(x, y, .74 if x < 0 else 1.14), v.P(x, y, 1.9)], '#2A2D31', 1.8, layer=12 if y > 0 else 4)
    # the benches inside, in shadow
    v.side_poly([(.5, 1.16), (-1.2, 1.16), (-1.2, .76), (.5, .76)], hwb, sv.lin([(0, '#2A2C30'), (1, '#0F1012')]), layer=8)
    v.wheel(-.9, -.46, .22, near=False)
    v.arch(-.9, .5, .27, .22)
    v.wheel(-.9, .52, .22, rim='#AEB5BC')
    v.wheel(1.2, .06, .21, rim='#AEB5BC')
    v.lamp(1.37, [(.1, .82), (-.1, .82), (-.1, .66), (.1, .66)])
    v.st.line([v.P(1.12, .34, 1.18), v.P(1.18, .5, 1.26)], '#1A1A1A', 2, layer=13)
    v.shadow(-1.42, 1.36, .56)


def protected_car(v):
    suv(v, '#26282C')


def convoy(st, order=('patrol', 'protected', 'patrol')):
    """A protected movement as one composition on a teal route lane, lead vehicle first."""
    sv = st.svg
    gap = 6.2
    xs = [gap * (len(order) - 1) / 2 - i * gap for i in range(len(order))]
    half = gap * (len(order) - 1) / 2 + 3.4
    lane = lambda w: [st.cam.p((half, w, 0)), st.cam.p((-half, w, 0)), st.cam.p((-half, -w, 0)), st.cam.p((half, -w, 0))]
    fade = sv.lin([(0, TEAL, 0), (.25, TEAL, 1), (.75, TEAL, 1), (1, TEAL, 0)], 0, 0, 1, 0)
    st.ops.append((0, 1, 'poly', (lane(1.25), fade, f' opacity=".22" filter="{sv.blur(5)}"', None)))
    st.ops.append((0, 2, 'poly', (lane(.05), fade, '', None)))
    build = {'patrol': patrol, 'protected': protected_car, 'ambulance': ambulance}
    for i, (x, kind) in enumerate(reversed(list(zip(xs, order)))):
        v = Vehicle(st, (x, 0, 0))
        base = len(st.ops)
        build[kind](v)
        # each vehicle on its own depth band so the painter draws far to near
        st.ops[base:] = [(o[0] + 20 * (i + 1), o[1], o[2], o[3]) for o in st.ops[base:]]


VEHICLES = {
    'taxi': ('Yellow taxi (Ambassador)', taxi),
    'car': ('Car', car),
    'suv': ('SUV', lambda v: suv(v, '#B8BEC4')),
    'two_wheeler': ('Two-wheeler', two_wheeler),
    'auto_rickshaw': ('Auto-rickshaw', auto_rickshaw),
    'toto': ('E-rickshaw (toto)', toto),
    'bus': ('City bus', bus),
    'truck': ('Truck', truck),
    'tempo': ('Tempo', tempo),
    'ambulance': ('Ambulance', ambulance),
    'patrol': ('Patrol vehicle', patrol),
    'fire_tender': ('Fire tender', fire_tender),
}


def build_vehicle(name):
    label, fn = VEHICLES[name]
    st = Studio(f'Studio shot: {label}')
    fn(Vehicle(st))
    return studio_render(st)


CONVOYS = {
    # the protection classes as compositions (the deck's protocol table: Z+ / Z / Y / X)
    # class Z is the standard convoy (convoy.svg)
    'convoy': ('Convoy: lead vehicle, protected car, tail vehicle', ('patrol', 'protected', 'patrol')),
    'convoy_zplus': ('Convoy, class Z plus: lead vehicle, protected car, tail vehicle, ambulance', ('patrol', 'protected', 'patrol', 'ambulance')),
    'convoy_y': ('Convoy, class Y: lead vehicle and protected car', ('patrol', 'protected')),
    'convoy_x': ('Convoy, class X: the protected car on its route', ('protected',)),
}


def build_convoy(name='convoy'):
    label, order = CONVOYS[name]
    LOD['smooth'] = 2 if len(order) == 1 else 1
    LOD['circle'] = 28 if len(order) == 1 else 18 if len(order) < 4 else 14
    try:
        st = Studio(label, cam=Cam(az=26, el=12, dist=34 + 6 * max(0, len(order) - 3)))
        convoy(st, order)
        return studio_render(st, pad=(18, 30, 18, 44))
    finally:
        LOD['smooth'], LOD['circle'] = 2, 28


# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
#  SCENES — graded, near-monochrome Kolkata with depth; one accent per picture.
# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
# time-of-day grades (desaturated: warm-grey dusk and dawn, steel-grey day, charcoal night — never navy or purple)
TOD = {
    'night': dict(sky=('#030304', '#0C0C0D', '#26252A'), sun=None, glow='#4A4540', far='#1F2022', mid='#131415', near='#070708',
                  ground='#0E0E0F', road='#18181A', line='#5C5C5C', haze='#3E3A35', lamp='#FFF3DF', win='#F2E6D0', star=True),
    'dusk': dict(sky=('#0E0E0F', '#33302E', '#8E8074'), sun='#E6D3BE', glow='#B59F8B', far='#423E3B', mid='#252424', near='#111112',
                 ground='#1A1A1A', road='#242424', line='#8A8580', haze='#6A5F57', lamp='#FFF3DF', win='#F6E7CF', star=False),
    'dawn': dict(sky=('#3A3B3D', '#86827E', '#CFC6BC'), sun='#FFF6EA', glow='#E9DED1', far='#8E8A86', mid='#5A5856', near='#262626',
                 ground='#3E3D3C', road='#4A4948', line='#C9C3BC', haze='#D2C8BD', lamp='#FFF6EA', win='#FFF6EA', star=False),
    'day': dict(sky=('#7F878F', '#B9BEC3', '#EDEEEF'), sun='#FFFFFF', glow='#FFFFFF', far='#AEB1B4', mid='#7B7F83', near='#383A3C',
                ground='#5F6265', road='#45474A', line='#E8E8E8', haze='#DCDDDE', lamp='#FFFFFF', win='#F4F5F6', star=False),
    'storm': dict(sky=('#0E0F10', '#26292B', '#4B4F52'), sun=None, glow='#7E8487', far='#3A3D40', mid='#222426', near='#0E0F10',
                  ground='#18191A', road='#202123', line='#7D8184', haze='#4E5356', lamp='#F4F6F8', win='#E4E8EA', star=False),
}


class Ground:
    """A pinhole camera over a flat city: horizon at hy, vanishing point vx; z metres ahead, X metres to the right."""

    def __init__(self, W, H, hy, vx, h=2.4, znear=3.4):
        self.W, self.H, self.hy, self.vx, self.h = W, H, hy, vx, h
        self.F = (H - hy) * znear / h

    def y(self, z, Y=0.0):
        return self.hy + self.F * (self.h - Y) / z

    def x(self, X, z):
        return self.vx + self.F * X / z

    def s(self, z):
        return self.F / z

    def pt(self, X, z, Y=0.0):
        return (self.x(X, z), self.y(z, Y))


class Scene:
    def __init__(self, label, tod, W=640, H=360, seed=1):
        self.svg = Svg(W, H, label)
        self.W, self.H = W, H
        self.t = TOD[tod]
        self.tod = tod
        self.rng = random.Random(seed)

    def add(self, s):
        self.svg.add(s)

    # ── atmosphere ────────────────────────────────────────────────────────────
    def sky(self, hy, sun=None, sun_r=60):
        sv, t = self.svg, self.t
        s0, s1, s2 = t['sky']
        self.add(f'<rect width="{self.W}" height="{f1(hy + 2)}" fill="{sv.lin([(0, s0), (.62, s1), (1, s2)], 0, 0, 0, hy, user=True)}"/>')
        if t['star']:
            r = random.Random(7)
            d = ''.join(f'M{f1(r.uniform(0, self.W))} {f1(r.uniform(0, hy * .55))}h.8' for _ in range(46))
            self.add(f'<path d="{d}" stroke="#FFF" stroke-opacity=".5" stroke-width=".8" stroke-linecap="round"/>')
        if sun and t['sun']:
            sx, sy = sun
            self.add(f'<circle cx="{f1(sx)}" cy="{f1(sy)}" r="{f1(sun_r * 3.2)}" fill="{sv.rad([(0, t["glow"], .55), (.4, t["glow"], .16), (1, t["glow"], 0)])}"/>')
            self.add(f'<circle cx="{f1(sx)}" cy="{f1(sy)}" r="{f1(sun_r * .2)}" fill="{t["sun"]}" opacity=".9" filter="{sv.blur(sun_r * .05)}"/>')
        # the horizon glow of the city itself
        self.add(f'<rect y="{f1(hy - 70)}" width="{self.W}" height="72" fill="{sv.lin([(0, t["haze"], 0), (1, t["haze"], .55)])}"/>')

    def clouds(self, n, y0, y1, col=None, op=.35, seed=3, rx=(60, 160), ry=(6, 16)):
        r = random.Random(seed)
        col = col or mix(self.t['sky'][1], WHITE, .12)
        b = self.svg.blur(7)
        d = ''.join(f'<ellipse cx="{f1(r.uniform(-40, self.W + 40))}" cy="{f1(r.uniform(y0, y1))}" rx="{f1(r.uniform(*rx))}" ry="{f1(r.uniform(*ry))}"/>' for _ in range(n))
        self.add(f'<g fill="{col}" opacity="{op}" filter="{b}">{d}</g>')

    def haze(self, y, h, op=.6, col=None):
        col = col or self.t['haze']
        self.add(f'<rect y="{f1(y - h)}" width="{self.W}" height="{f1(h)}" fill="{self.svg.lin([(0, col, 0), (1, col, op)])}"/>')

    def finish(self, vign=.75, grain=True):
        sv = self.svg
        self.add(f'<rect width="{self.W}" height="{self.H}" fill="{sv.rad([(0, "#000", 0), (.62, "#000", 0), (1, "#000", vign)], .5, .46, .78)}"/>')
        if grain:
            i = sv.uid('n')
            sv.raw_def(f'<filter id="{i}" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="4" stitchTiles="stitch"/>'
                       f'<feColorMatrix type="matrix" values="0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 .55 0"/></filter>')
            self.add(f'<rect width="{self.W}" height="{self.H}" filter="url(#{i})" opacity=".09"/>')
        return sv.render()

    # ── city ──────────────────────────────────────────────────────────────────
    def windows(self, lit=.5, col=None, cell=(5, 7), seed=11):
        """A window-light pattern (lit cells at random) to lay over building silhouettes."""
        col = col or self.t['win']
        r = random.Random(seed)
        w, h = cell
        tw, th = w * 9, h * 7
        rects = ''.join(f'<rect x="{i * w + 1}" y="{j * h + 2}" width="{w - 3}" height="{h - 4}"/>' for i in range(9) for j in range(7) if r.random() < lit)
        i = self.svg.uid('p')
        self.svg.raw_def(f'<pattern id="{i}" width="{tw}" height="{th}" patternUnits="userSpaceOnUse"><g fill="{col}">{rects}</g></pattern>')
        return f'url(#{i})'

    def skyline(self, base, hmin, hmax, col, x0=-10, x1=None, wmin=10, wmax=30, seed=5, win=None, win_op=.5, spires=.15, gap=.15):
        r = random.Random(seed)
        x1 = self.W + 10 if x1 is None else x1
        d, x = [], x0
        while x < x1:
            w = r.uniform(wmin, wmax)
            if r.random() < gap:
                x += w * .5
                continue
            h = r.uniform(hmin, hmax) * (1.0 if r.random() > .2 else 1.5)
            top = base - h
            seg = f'M{f1(x)} {f1(base)}V{f1(top)}'
            if r.random() < .3:   # a setback
                seg += f'H{f1(x + w * .2)}V{f1(top - h * .12)}H{f1(x + w * .8)}V{f1(top)}'
            seg += f'H{f1(x + w)}V{f1(base)}Z'
            if r.random() < spires:
                seg += f'M{f1(x + w * .5 - .6)} {f1(top)}v{f1(-h * .25)}h1.2v{f1(h * .25)}z'
            d.append(seg)
            x += w + r.uniform(-w * .35, w * .1)
        path = ''.join(d)
        self.add(f'<path d="{path}" fill="{col}"/>')
        if win:
            self.add(f'<path d="{path}" fill="{win}" opacity="{win_op}"/>')

    def stadium(self, cx, base, w, col, rim=None, lights=None, op_l=.9):
        """A vast cricket bowl: a low wide drum with a ring roof and floodlight masts."""
        h = w * .16
        sv = self.svg
        d = (f'M{f1(cx - w / 2)} {f1(base)}L{f1(cx - w * .47)} {f1(base - h * .78)}Q{f1(cx)} {f1(base - h * 1.25)} {f1(cx + w * .47)} {f1(base - h * .78)}'
             f'L{f1(cx + w / 2)} {f1(base)}Z')
        self.add(f'<path d="{d}" fill="{col}"/>')
        # the roof ring catching the light
        rim = rim or mix(col, WHITE, .25)
        self.add(f'<path d="M{f1(cx - w * .47)} {f1(base - h * .78)}Q{f1(cx)} {f1(base - h * 1.25)} {f1(cx + w * .47)} {f1(base - h * .78)}" fill="none" stroke="{rim}" stroke-width="{f1(max(1, w * .008))}"/>')
        # facade ribs
        ribs = ''.join(f'M{f1(cx - w * .45 + i * w * .9 / 24)} {f1(base - h * .1)}V{f1(base - h * (.62 + .2 * math.sin(math.pi * i / 24)))}' for i in range(25))
        self.add(f'<path d="{ribs}" stroke="{mix(col, WHITE, .1)}" stroke-width="{f1(max(.6, w * .003))}"/>')
        if lights:
            for k in (-.38, -.13, .13, .38):
                lx = cx + w * k
                ly = base - h * (1.15 + .05 * (1 - abs(k)))
                self.add(f'<circle cx="{f1(lx)}" cy="{f1(ly)}" r="{f1(w * .07)}" fill="{lights}" opacity="{op_l * .5}" filter="{sv.blur(w * .03)}"/>'
                         f'<rect x="{f1(lx - w * .012)}" y="{f1(ly - w * .006)}" width="{f1(w * .024)}" height="{f1(w * .012)}" fill="{lights}"/>')

    def river(self, y0, y1, refl=None):
        sv, t = self.svg, self.t
        top = mix(t['sky'][2], '#000', .35)
        self.add(f'<rect y="{f1(y0)}" width="{self.W}" height="{f1(y1 - y0)}" fill="{sv.lin([(0, top), (1, mix(t["sky"][1], "#000", .65))])}"/>')
        r = random.Random(21)
        d = ''.join(f'M{f1(r.uniform(-20, self.W))} {f1(y0 + (y1 - y0) * (r.random() ** 1.6))}h{f1(r.uniform(8, 50))}' for _ in range(70))
        self.add(f'<path d="{d}" stroke="{mix(t["sky"][2], WHITE, .2)}" stroke-opacity=".28" stroke-width=".8"/>')

    def reflection(self, x, y0, length, col, w=3, op=.5):
        """A vertical shimmer on the water below a light."""
        r = random.Random(int(x * 13) % 997)
        d = ''.join(f'M{f1(x - w * r.uniform(.4, 1.2))} {f1(y0 + i * 2.2)}h{f1(w * r.uniform(.8, 2.4))}' for i in range(int(length / 2.2)))
        self.add(f'<path d="{d}" stroke="{col}" stroke-opacity="{op}" stroke-width="1.1"/>')

    def trees(self, x0, x1, base, hmin, hmax, col, seed=9, n=None):
        r = random.Random(seed)
        n = n or int((x1 - x0) / (hmax * .6))
        d = ''
        for _ in range(n):
            x, h = r.uniform(x0, x1), r.uniform(hmin, hmax)
            for k in range(3):
                d += f'<ellipse cx="{f1(x + r.uniform(-h * .3, h * .3))}" cy="{f1(base - h * r.uniform(.45, .8))}" rx="{f1(h * r.uniform(.3, .5))}" ry="{f1(h * r.uniform(.25, .38))}"/>'
        self.add(f'<g fill="{col}">{d}</g>')

    def road(self, g, half, col=None, far=900, near=2.5, edge=None, shoulder=None):
        col = col or self.t['road']
        sv = self.svg
        P = [g.pt(-half, near), g.pt(-half, far), g.pt(half, far), g.pt(half, near)]
        self.add(f'<polygon points="{pts(P)}" fill="{sv.lin([(0, mix(col, self.t["haze"], .55)), (.3, col), (1, scale(col, .8))], 0, g.hy, 0, self.H, user=True)}"/>')
        if edge:
            for X in (-half + .3, half - .3):
                self.add(f'<polygon points="{pts([g.pt(X - .12, near), g.pt(X - .12, far), g.pt(X + .12, far), g.pt(X + .12, near)])}" fill="{edge}" opacity=".7"/>')

    def dashes(self, g, X, col, z0=3, z1=400, every=12, length=4, w=.14, op=.85):
        d = ''
        z = z0
        while z < z1:
            a, b = z, z + length
            P = [g.pt(X - w, a), g.pt(X - w, b), g.pt(X + w, b), g.pt(X + w, a)]
            d += 'M' + 'L'.join(f'{f1(x)} {f1(y)}' for x, y in P) + 'Z'
            z += every
        self.add(f'<path d="{d}" fill="{col}" opacity="{op}"/>')

    def ribbon(self, g, pts_xz, col, w=.5, op=1, glow=True, fade_far=True):
        """A glowing line on the ground (an accent route), from near to far: [(X, z)]."""
        sv = self.svg
        left = [g.pt(X - w, z) for X, z in pts_xz]
        right = [g.pt(X + w, z) for X, z in reversed(pts_xz)]
        poly = pts(left + right)
        y0, y1 = g.y(pts_xz[-1][1]), g.y(pts_xz[0][1])
        grad = sv.lin([(0, col, 0 if fade_far else 1), (.25, col, 1), (1, col, 1)], 0, y0, 0, y1, user=True)
        if glow:
            self.add(f'<polygon points="{poly}" fill="{grad}" opacity="{op * .8}" filter="{sv.blur(4)}"/>')
            wide = [g.pt(X - w * 5, z) for X, z in pts_xz] + [g.pt(X + w * 5, z) for X, z in reversed(pts_xz)]
            self.add(f'<polygon points="{pts(wide)}" fill="{grad}" opacity="{op * .14}" filter="{sv.blur(8)}"/>')
        self.add(f'<polygon points="{poly}" fill="{grad}" opacity="{op}"/>')

    def streetlights(self, g, X, zs, col=None, pole=None, h=9, arm=1.6, pool=True):
        col = col or self.t['lamp']
        pole = pole or scale(self.t['near'], 1.6)
        sv = self.svg
        out, glow, heads, pools = '', '', '', ''
        sgn = -1 if X > 0 else 1
        pg = sv.rad([(0, col, .22), (.5, col, .07), (1, col, 0)]) if pool else None
        for z in zs:
            x0, yb = g.pt(X, z)
            _, yt = g.pt(X, z, h)
            xa, ya = g.pt(X + sgn * arm, z, h)
            s = g.s(z)
            out += f'M{f1(x0)} {f1(yb)}V{f1(yt)}L{f1(xa)} {f1(ya)}'
            heads += f'M{f1(xa - s * .32)} {f1(ya)}h{f1(s * .64)}v{f1(max(.6, s * .1))}h{f1(-s * .64)}z'
            glow += f'<circle cx="{f1(xa)}" cy="{f1(ya + s * .12)}" r="{f1(max(1.4, s * .55))}"/>'
            if pool:
                px, py = g.pt(X + sgn * arm, z)
                pools += f'<ellipse cx="{f1(px)}" cy="{f1(py)}" rx="{f1(s * 5)}" ry="{f1(s * 1.1)}"/>'
        if pools:
            self.add(f'<g fill="{pg}">{pools}</g>')
        self.add(f'<path d="{out}" stroke="{pole}" stroke-width="1" fill="none"/>')
        self.add(f'<g fill="{col}" opacity=".45" filter="{sv.blur(1.8)}">{glow}</g><path d="{heads}" fill="{col}"/>')

    def car(self, g, X, z, kind='car', facing='front', body=None, lamps=None, tail=None, w=None, h=None, beacon=None, glow=True):
        """A vehicle in perspective, seen from the front or the rear: graded body, glass with a sheen, lamps."""
        sv = self.svg
        s = g.s(z)
        dims = {'car': (1.8, 1.45), 'taxi': (1.72, 1.6), 'suv': (1.9, 1.75), 'bus': (2.5, 3.1), 'van': (2.0, 2.4), 'truck': (2.4, 3.0), 'auto': (1.3, 1.7)}[kind]
        W_, H_ = (w or dims[0]) * s, (h or dims[1]) * s
        cx, yb = g.pt(X, z)
        body = body or ('#C9CDD2' if facing == 'front' else '#2A2C2F')
        gb = sv.lin([(0, mix(body, WHITE, .25)), (.5, body), (1, scale(body, .62))])
        out = f'<ellipse cx="{f1(cx)}" cy="{f1(yb)}" rx="{f1(W_ * .64)}" ry="{f1(max(1, s * .2))}" fill="#000" opacity=".6"/>'
        r_ = W_ * .12
        lower = H_ * (.52 if kind in ('car', 'suv', 'taxi') else .88)
        y_low = yb - lower - s * .22
        out += f'<rect x="{f1(cx - W_ * .44)}" y="{f1(yb - s * .42)}" width="{f1(W_ * .2)}" height="{f1(s * .42)}" rx="{f1(s * .06)}" fill="#0A0A0A"/>'
        out += f'<rect x="{f1(cx + W_ * .24)}" y="{f1(yb - s * .42)}" width="{f1(W_ * .2)}" height="{f1(s * .42)}" rx="{f1(s * .06)}" fill="#0A0A0A"/>'
        out += f'<rect x="{f1(cx - W_ / 2)}" y="{f1(y_low)}" width="{f1(W_)}" height="{f1(lower)}" rx="{f1(r_)}" fill="{gb}"/>'
        out += f'<rect x="{f1(cx - W_ * .47)}" y="{f1(y_low + lower * .72)}" width="{f1(W_ * .94)}" height="{f1(lower * .2)}" rx="{f1(r_ * .4)}" fill="#141516" opacity=".75"/>'
        glass = sv.lin([(0, '#4A5056'), (.45, '#1A1D20'), (1, '#0E1012')])
        if kind in ('car', 'suv', 'taxi'):
            cw = W_ * (.7 if kind == 'taxi' else .76)
            ct = yb - H_ - s * .2
            out += (f'<path d="M{f1(cx - W_ * .46)} {f1(y_low + s * .04)}L{f1(cx - cw / 2)} {f1(ct)}Q{f1(cx)} {f1(ct - s * .08)} {f1(cx + cw / 2)} {f1(ct)}L{f1(cx + W_ * .46)} {f1(y_low + s * .04)}Z" fill="{mix(body, WHITE, .12)}"/>'
                    f'<path d="M{f1(cx - W_ * .4)} {f1(y_low)}L{f1(cx - cw * .45)} {f1(ct + s * .1)}H{f1(cx + cw * .45)}L{f1(cx + W_ * .4)} {f1(y_low)}Z" fill="{glass}"/>'
                    f'<path d="M{f1(cx - cw * .1)} {f1(ct + s * .12)}L{f1(cx - W_ * .3)} {f1(y_low - s * .02)}H{f1(cx - W_ * .18)}L{f1(cx + cw * .06)} {f1(ct + s * .12)}Z" fill="#FFF" opacity=".12"/>')
        else:
            out += f'<rect x="{f1(cx - W_ * .45)}" y="{f1(yb - H_ - s * .12)}" width="{f1(W_ * .9)}" height="{f1(H_ * .34)}" rx="{f1(r_ * .5)}" fill="{glass}"/>'
            out += f'<rect x="{f1(cx - W_ / 2)}" y="{f1(yb - H_ - s * .26)}" width="{f1(W_)}" height="{f1(s * .16)}" rx="{f1(s * .05)}" fill="{mix(body, WHITE, .2)}"/>'
        ly = y_low + lower * .3
        lw, lh = W_ * .2, max(.8, s * .12)
        if facing == 'front':
            lc = lamps or self.t['lamp']
            out += ''.join(f'<rect x="{f1(cx + k * W_ * .36 - lw / 2)}" y="{f1(ly)}" width="{f1(lw)}" height="{f1(lh)}" rx="{f1(lh / 2)}" fill="{lc}"/>' for k in (-1, 1))
            out += f'<rect x="{f1(cx - W_ * .18)}" y="{f1(ly + lh * .2)}" width="{f1(W_ * .36)}" height="{f1(lower * .2)}" rx="{f1(s * .04)}" fill="#0F1011"/>'
            if glow:
                out += ''.join(f'<circle cx="{f1(cx + k * W_ * .36)}" cy="{f1(ly)}" r="{f1(W_ * .26)}" fill="{lc}" opacity=".3" filter="{sv.blur(max(1, W_ * .1))}"/>' for k in (-1, 1))
        else:
            tc = tail or '#B9B4AE'
            out += ''.join(f'<rect x="{f1(cx + k * W_ * .36 - lw / 2)}" y="{f1(ly)}" width="{f1(lw)}" height="{f1(lh)}" rx="{f1(lh / 2)}" fill="{tc}"/>' for k in (-1, 1))
            if glow and tail:
                out += ''.join(f'<circle cx="{f1(cx + k * W_ * .36)}" cy="{f1(ly)}" r="{f1(W_ * .3)}" fill="{tc}" opacity=".45" filter="{sv.blur(max(1, W_ * .12))}"/>' for k in (-1, 1))
        if beacon:
            by = yb - H_ - s * .26
            out += (f'<rect x="{f1(cx - W_ * .22)}" y="{f1(by - s * .14)}" width="{f1(W_ * .44)}" height="{f1(s * .14)}" rx="{f1(s * .05)}" fill="{beacon}"/>'
                    f'<circle cx="{f1(cx)}" cy="{f1(by)}" r="{f1(W_ * .6)}" fill="{beacon}" opacity=".3" filter="{sv.blur(max(1.5, W_ * .22))}"/>')
        self.add(out)

    def streaks(self, g, lanes, col, z0=6, z1=600, w=.16, op=.6, n=1):
        """Long-exposure light trails along lanes."""
        sv = self.svg
        for X in lanes:
            P = [g.pt(X - w, z0), g.pt(X - w * .5, z1), g.pt(X + w * .5, z1), g.pt(X + w, z0)]
            y0, y1 = g.y(z1), g.y(z0)
            grad = sv.lin([(0, col, 0), (.4, col, op * .6), (1, col, op)], 0, y0, 0, y1, user=True)
            self.add(f'<polygon points="{pts(P)}" fill="{grad}" filter="{sv.blur(.7)}"/>')

    def crowd(self, g, X0, X1, z0, z1, col, n=180, seed=31, hmin=1.5, hmax=1.85, blur=.35):
        """A distant crowd as one abstract mass: rounded heads-and-shoulders bumps, never an individual."""
        r = random.Random(seed)
        items = []
        for _ in range(n):
            z = z0 + (z1 - z0) * r.random() ** .8
            items.append((z, r.uniform(X0, X1), r.uniform(hmin, hmax)))
        items.sort(key=lambda t: -t[0])
        d = ''
        for z, X, hh in items:
            s = g.s(z)
            x, y = g.pt(X, z)
            w = .5 * s
            top = y - hh * s
            d += f'M{f1(x - w * .5)} {f1(y)}V{f1(top + w * .55)}a{f1(w * .5)} {f1(w * .55)} 0 0 1 {f1(w)} 0V{f1(y)}Z'
        self.add(f'<path d="{d}" fill="{col}" filter="{self.svg.blur(blur)}"/>')

    def barrier(self, g, X, z0, z1, col, h=1.0, stripe=None, every=2.4):
        """A run of barrier panels along the kerb: one continuous strip, the joints drawn only where they read."""
        P = [g.pt(X, z0), g.pt(X, z1), g.pt(X, z1, h), g.pt(X, z0, h)]
        self.add(f'<polygon points="{pts(P)}" fill="{col}"/>')
        if stripe:
            Q = [g.pt(X, z0, h * .55), g.pt(X, z1, h * .55), g.pt(X, z1, h * .75), g.pt(X, z0, h * .75)]
            self.add(f'<polygon points="{pts(Q)}" fill="{stripe}"/>')
        d, z = '', z0 + every
        while z < min(z1, 60):
            a_, b_ = g.pt(X, z), g.pt(X, z, h)
            d += f'M{f1(a_[0])} {f1(a_[1])}L{f1(b_[0])} {f1(b_[1])}'
            z += every
        if d:
            self.add(f'<path d="{d}" stroke="#000" stroke-opacity=".45" stroke-width=".9"/>')

    def signal(self, g, X, z, state_col, dark='#1B1C1E', h=4.2, pole=None, glow=True, lit=1):
        """A traffic signal head on a pole; `lit` is the lamp index (0 top .. 2 bottom) or None when dark."""
        sv = self.svg
        pole = pole or scale(self.t['near'], 1.6)
        x, yb = g.pt(X, z)
        s = g.s(z)
        _, yt = g.pt(X, z, h)
        out = f'<path d="M{f1(x)} {f1(yb)}V{f1(yt)}" stroke="{pole}" stroke-width="{f1(max(.8, s * .12))}"/>'
        bw, bh = s * .38, s * 1.1
        out += f'<rect x="{f1(x - bw / 2)}" y="{f1(yt - bh)}" width="{f1(bw)}" height="{f1(bh)}" rx="{f1(bw * .25)}" fill="{dark}"/>'
        for i in range(3):
            cy = yt - bh + bh * (i + .5) / 3
            on = lit is not None and i == lit
            out += f'<circle cx="{f1(x)}" cy="{f1(cy)}" r="{f1(bw * .3)}" fill="{state_col if on else "#2C2D30"}"/>'
            if on and glow:
                out += f'<circle cx="{f1(x)}" cy="{f1(cy)}" r="{f1(max(2.5, s * .9))}" fill="{state_col}" opacity=".45" filter="{sv.blur(max(1.5, s * .45))}"/>'
        self.add(out)

    def bunting(self, g, z, X0, X1, Y, col, sag=.8, n=14):
        P = [g.pt(X0 + (X1 - X0) * i / n, z, Y - sag * math.sin(math.pi * i / n)) for i in range(n + 1)]
        line = 'M' + 'L'.join(f'{f1(x)} {f1(y)}' for x, y in P)
        s = g.s(z)
        flags = ''.join(f'M{f1(x - s * .18)} {f1(y)}l{f1(s * .18)} {f1(s * .42)}l{f1(s * .18)} {f1(-s * .42)}Z' for x, y in P[1:-1])
        self.add(f'<path d="{line}" stroke="{col}" stroke-width=".6" fill="none"/><path d="{flags}" fill="{col}"/>')

    def viaduct(self, g, X, z0, z1, deck_h, col, every=30, under=None):
        """An elevated metro viaduct on T-piers, running away from the viewer."""
        d = ''
        z = z0
        while z < z1:
            x, yb = g.pt(X, z)
            _, yt = g.pt(X, z, deck_h - .8)
            s = g.s(z)
            d += f'M{f1(x - s * .7)} {f1(yb)}V{f1(yt)}H{f1(x - s * 2.4)}V{f1(yt - s * .6)}H{f1(x + s * 2.4)}V{f1(yt)}H{f1(x + s * .7)}V{f1(yb)}Z'
            z += every
        deck = [g.pt(X - 3, z0, deck_h), g.pt(X - 3, z1, deck_h), g.pt(X + 3, z1, deck_h), g.pt(X + 3, z0, deck_h),
                g.pt(X + 3, z0, deck_h - 1.6), g.pt(X + 3, z1, deck_h - 1.6), g.pt(X - 3, z1, deck_h - 1.6), g.pt(X - 3, z0, deck_h - 1.6)]
        side = [g.pt(X - 3, z0, deck_h), g.pt(X - 3, z1, deck_h), g.pt(X - 3, z1, deck_h - 1.6), g.pt(X - 3, z0, deck_h - 1.6)]
        self.add(f'<path d="{d}" fill="{col}"/><polygon points="{pts(side)}" fill="{mix(col, WHITE, .12)}"/>')

    def crane(self, x, base, h, col, jib=1.0):
        s = h / 100
        d = (f'M{f1(x - 3 * s)} {f1(base)}V{f1(base - h)}h{f1(6 * s)}V{f1(base)}Z'
             f'M{f1(x - 30 * s * jib)} {f1(base - h)}h{f1(110 * s * jib)}v{f1(-4 * s)}h{f1(-110 * s * jib)}Z'
             f'M{f1(x - 2 * s)} {f1(base - h - 4 * s)}l{f1(2 * s)} {f1(-14 * s)}l{f1(2 * s)} {f1(14 * s)}Z')
        lines = ''.join(f'M{f1(x - 3 * s)} {f1(base - k * 8 * s)}L{f1(x + 3 * s)} {f1(base - (k + 1) * 8 * s)}' for k in range(int(h / (8 * s))))
        cable = f'M{f1(x + 60 * s * jib)} {f1(base - h)}V{f1(base - h * .45)}'
        tie = f'M{f1(x)} {f1(base - h - 18 * s)}L{f1(x + 78 * s * jib)} {f1(base - h - 4 * s)}M{f1(x)} {f1(base - h - 18 * s)}L{f1(x - 28 * s * jib)} {f1(base - h - 4 * s)}'
        self.add(f'<path d="{d}" fill="{col}"/><path d="{lines}{cable}{tie}" stroke="{col}" stroke-width=".7" fill="none"/>')

    def gantry(self, g, z, half, h, col, depth=.8, signs=None):
        """An overhead gantry across the road (an ANPR or a sign gantry); `signs`: [(X, width, height, fill)]."""
        out = ''
        for X in (-half, half):
            x, yb = g.pt(X, z)
            _, yt = g.pt(X, z, h)
            s = g.s(z)
            out += f'<rect x="{f1(x - s * .18)}" y="{f1(yt)}" width="{f1(s * .36)}" height="{f1(yb - yt)}" fill="{col}"/>'
        xl, yl = g.pt(-half, z, h)
        xr, _ = g.pt(half, z, h)
        s = g.s(z)
        out += f'<rect x="{f1(xl)}" y="{f1(yl - s * depth)}" width="{f1(xr - xl)}" height="{f1(s * depth)}" fill="{col}"/>'
        out += f'<path d="' + ''.join(f'M{f1(xl + (xr - xl) * i / 16)} {f1(yl)}l{f1((xr - xl) / 32)} {f1(-s * depth)}l{f1((xr - xl) / 32)} {f1(s * depth)}' for i in range(16)) + f'" stroke="{mix(col, WHITE, .15)}" stroke-width=".6" fill="none"/>'
        self.add(out)
        if signs:
            for X, w, hh, fill in signs:
                x0, y0 = g.pt(X - w / 2, z, h - .2)
                x1, y1 = g.pt(X + w / 2, z, h - .2 - hh)
                self.add(f'<rect x="{f1(x0)}" y="{f1(y1)}" width="{f1(x1 - x0)}" height="{f1(y0 - y1)}" rx="{f1(s * .1)}" fill="{fill}"/>')

    def beam(self, x, y, x1, y1, x2, y2, col, op=.22):
        """A soft cone of light from (x, y) spreading to the segment (x1, y1)–(x2, y2)."""
        sv = self.svg
        g = sv.lin([(0, col, op), (1, col, 0)], x, y, (x1 + x2) / 2, (y1 + y2) / 2, user=True)
        self.add(f'<polygon points="{pts([(x, y), (x1, y1), (x2, y2)])}" fill="{g}" filter="{sv.blur(2)}"/>')

    def brackets(self, x, y, w, h, col, k=.28, sw=1.6):
        a, b = w * k, h * k
        d = (f'M{f1(x)} {f1(y + b)}V{f1(y)}H{f1(x + a)}M{f1(x + w - a)} {f1(y)}H{f1(x + w)}V{f1(y + b)}'
             f'M{f1(x + w)} {f1(y + h - b)}V{f1(y + h)}H{f1(x + w - a)}M{f1(x + a)} {f1(y + h)}H{f1(x)}V{f1(y + h - b)}')
        self.add(f'<path d="{d}" stroke="{col}" stroke-width="{f1(sw)}" fill="none" stroke-linecap="round"/>')

    def glow(self, x, y, r, col, op=.5):
        self.add(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{f1(r)}" fill="{col}" opacity="{op}" filter="{self.svg.blur(r * .45)}"/>')

    def rain(self, n, col, op=.22, seed=17, ang=-.18, ln=(8, 18)):
        r = random.Random(seed)
        d = ''
        for _ in range(n):
            x, y, L = r.uniform(-20, self.W + 20), r.uniform(-10, self.H), r.uniform(*ln)
            d += f'M{f1(x)} {f1(y)}l{f1(L * ang)} {f1(L)}'
        self.add(f'<path d="{d}" stroke="{col}" stroke-opacity="{op}" stroke-width=".7"/>')


def facades(sc, g, X, z0, z1, col, side, seed=61, hmin=14, hmax=40, floors=None, floor_op=.35):
    """Modern blocks along a boulevard: facades receding to the vanishing point, floor lines converging."""
    r = random.Random(seed)
    z = z0
    faces, lines = '', ''
    while z < z1:
        dz = r.uniform(14, 34)
        hh = r.uniform(hmin, hmax)
        a, b = z, z + dz
        P = [g.pt(X, a), g.pt(X, b), g.pt(X, b, hh), g.pt(X, a, hh)]
        faces += 'M' + 'L'.join(f'{f1(x)} {f1(y)}' for x, y in P) + 'Z'
        if floors:
            Y = 3.4
            while Y < hh - 1:
                p0, p1 = g.pt(X, a + .6, Y), g.pt(X, b - .6, Y)
                lines += f'M{f1(p0[0])} {f1(p0[1])}L{f1(p1[0])} {f1(p1[1])}'
                Y += 4.2
            zz = a + 4
            while zz < b - 2:
                p0, p1 = g.pt(X, zz, 0), g.pt(X, zz, hh)
                lines += f'M{f1(p0[0])} {f1(p0[1])}L{f1(p1[0])} {f1(p1[1])}'
                zz += 7
        z = b + r.uniform(0, 4)
    sc.add(f'<path d="{faces}" fill="{col}"/>')
    if floors:
        sc.add(f'<path d="{lines}" stroke="{floors}" stroke-opacity="{floor_op}" stroke-width=".8"/>')


def ground_plane(sc, hy, col=None):
    t = sc.t
    col = col or t['ground']
    sc.add(f'<rect y="{f1(hy)}" width="{sc.W}" height="{f1(sc.H - hy)}" fill="{sc.svg.lin([(0, mix(col, t["haze"], .5)), (.25, col), (1, scale(col, .7))])}"/>')


# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
#  KOLKATA — the landmarks and the street, drawn as graded silhouettes (never a photo, never a person).
# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
def _qpts(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / n for i in range(n + 1))]


def howrah_profile(u):
    """The top chord of Howrah Bridge as a fraction of the tower height above the deck, along the bridge (u = 0..1):
    anchor arm rising to the tower, the cantilever arm falling away in a long concave sweep, the suspended span."""
    v = u if u <= .5 else 1 - u
    if v <= .145:                                   # anchor arm: rises to the tower top
        t = v / .145
        return .2 + .8 * (t ** 1.35)
    if v <= .36:                                    # cantilever arm: concave fall from the tower
        t = (v - .145) / (.36 - .145)
        return 1 - .66 * (1 - (1 - t) ** 2.1)
    t = (v - .36) / (.5 - .36)                      # suspended span: a shallow rise to midspan
    return .34 + .06 * math.sin(t * math.pi / 2)


def howrah_bridge(sc, x0, x1, deck, H, col, lit=None, op=1.0, web=.55, piers_to=None, detail=1.0):
    """Howrah Bridge in elevation: the cantilever truss with its two towers, posts and cross-bracing, deck below."""
    sv = sc.svg
    W = x1 - x0
    n = max(24, int(56 * detail))
    us = [i / n for i in range(n + 1)]
    top = [(x0 + W * u, deck - H * howrah_profile(u)) for u in us]
    # the truss web: posts at every panel point and an X in every panel
    d = ''
    for i in range(n + 1):
        x, y = top[i]
        d += f'M{f1(x)} {f1(deck)}V{f1(y)}'
        if i < n:
            xa, ya = top[i + 1]
            d += f'M{f1(x)} {f1(deck)}L{f1(xa)} {f1(ya)}M{f1(x)} {f1(y)}L{f1(xa)} {f1(deck)}'
    sw = max(.45, W / 900)
    mass = f'M{f1(x0)} {f1(deck)}L' + pts(top) + f'L{f1(x1)} {f1(deck)}Z'
    out = (f'<g opacity="{op:g}"><path d="{mass}" fill="{col}" opacity="{min(.6, web * .62):.2f}"/>'
           f'<path d="{d}" stroke="{col}" stroke-width="{f1(sw * 1.25)}" stroke-opacity="{min(1, web + .35):.2f}" fill="none"/>')
    # the chords: top chord heavy, the deck girder below
    out += f'<path d="M{pts(top)}" fill="none" stroke="{col}" stroke-width="{f1(sw * 3.2)}" stroke-linejoin="round"/>'
    out += f'<rect x="{f1(x0)}" y="{f1(deck - sw)}" width="{f1(W)}" height="{f1(max(1.6, H * .06))}" fill="{col}"/>'
    # the towers: slim lattice legs rising just above the chord, and the piers into the river
    for u in (.145, .855):
        x = x0 + W * u
        yt = deck - H * 1.05
        tw = max(1.2, W * .0045)
        pier = piers_to if piers_to is not None else deck + H * .2
        out += f'<path d="M{f1(x - tw)} {f1(pier)}V{f1(yt + tw)}L{f1(x)} {f1(yt - tw)}L{f1(x + tw)} {f1(yt + tw)}V{f1(pier)}Z" fill="{col}"/>'
        out += f'<rect x="{f1(x - tw * 2.4)}" y="{f1(deck)}" width="{f1(tw * 4.8)}" height="{f1(pier - deck)}" fill="{col}"/>'
    out += '</g>'
    sc.add(out)
    if lit:
        # the bridge's evening lights: points along the top chord and the deck
        line = f'M{pts(top)}M{f1(x0)} {f1(deck)}H{f1(x1)}'
        dot = f'stroke-width="{f1(max(1.2, sw * 1.8))}" stroke-linecap="round" stroke-dasharray="0 {f1(W / 48)}" fill="none"'
        sc.add(f'<path d="{line}" stroke="{lit}" {dot}/><path d="{line}" stroke="{lit}" {dot} opacity=".35" filter="{sv.blur(max(1.2, W / 260))}"/>')
    return top


def vidyasagar_setu(sc, x0, x1, deck, H, col, op=1.0, lit=None, cables=11):
    """Vidyasagar Setu in elevation: two tall H-pylons, a fan of stay cables on each side, the long thin deck."""
    W = x1 - x0
    sw = max(.55, W / 800)
    out = f'<g opacity="{op:g}">'
    # the deck: a gentle crest over the main span
    dk = [(x0 + W * i / 40, deck - H * .05 * math.sin(math.pi * i / 40)) for i in range(41)]
    out += f'<path d="M{pts(dk)}" stroke="{col}" stroke-width="{f1(max(1.2, H * .035))}" fill="none"/>'
    cab = ''
    for u in (.22, .78):
        px = x0 + W * u
        yd = deck - H * .05 * math.sin(math.pi * u)
        ytop = yd - H
        lw = max(1.2, W * .007)
        # the H-pylon: two legs (seen a little from the side) and two portal beams
        for dx in (-lw * 1.1, lw * 1.1):
            out += f'<path d="M{f1(px + dx - lw / 2)} {f1(yd + H * .14)}L{f1(px + dx * .6 - lw / 2)} {f1(ytop)}h{f1(lw)}L{f1(px + dx + lw / 2)} {f1(yd + H * .14)}Z" fill="{col}"/>'
        for k in (.42, .9):
            out += f'<rect x="{f1(px - lw * 1.8)}" y="{f1(yd - H * k)}" width="{f1(lw * 3.6)}" height="{f1(max(.8, lw * .6))}" fill="{col}"/>'
        # semi-fan stays: anchored along the top quarter of the pylon, spread along the deck
        for side in (-1, 1):
            reach = W * (.2 if (side < 0 and u < .5) or (side > 0 and u > .5) else .27)
            for k in range(cables):
                t = (k + 1) / cables
                ay = ytop + H * .04 + H * .22 * (1 - t)
                dx_ = side * reach * (.12 + .88 * t)
                xx = px + dx_
                yy = deck - H * .05 * math.sin(math.pi * min(1, max(0, (xx - x0) / W)))
                cab += f'M{f1(px)} {f1(ay)}L{f1(xx)} {f1(yy)}'
    out += f'<path d="{cab}" stroke="{col}" stroke-width="{f1(sw)}" stroke-opacity=".8" fill="none"/></g>'
    sc.add(out)
    if lit:
        sc.add(f'<path d="M{pts(dk)}" stroke="{lit}" stroke-width="{f1(max(1, sw * 2))}" stroke-linecap="round" stroke-dasharray="0 {f1(W / 20)}" fill="none"/>')


def victoria_memorial(sc, cx, base, s, col, light=None, win=None):
    """The Victoria Memorial: a long marble hall on a plinth, corner pavilions with cupolas, the drum and the great
    dome with its lantern and finial (the statue on top reads only as a slender finial at this size)."""
    c2 = mix(col, '#000', .18)
    d = f'M{f1(cx - 84 * s)} {f1(base)}V{f1(base - 5 * s)}H{f1(cx + 84 * s)}V{f1(base)}Z'                      # plinth
    d += f'M{f1(cx - 76 * s)} {f1(base - 5 * s)}V{f1(base - 27 * s)}H{f1(cx + 76 * s)}V{f1(base - 5 * s)}Z'     # hall
    d += f'M{f1(cx - 20 * s)} {f1(base - 27 * s)}V{f1(base - 36 * s)}H{f1(cx + 20 * s)}V{f1(base - 27 * s)}Z'   # portico attic
    for k in (-1, 1):                                                                                               # corner pavilions
        x = cx + k * 68 * s
        d += f'M{f1(x - 9 * s)} {f1(base - 27 * s)}V{f1(base - 38 * s)}H{f1(x + 9 * s)}V{f1(base - 27 * s)}Z'
        d += f'M{f1(x - 7 * s)} {f1(base - 38 * s)}Q{f1(x - 7 * s)} {f1(base - 49 * s)} {f1(x)} {f1(base - 50 * s)}Q{f1(x + 7 * s)} {f1(base - 49 * s)} {f1(x + 7 * s)} {f1(base - 38 * s)}Z'
        d += f'M{f1(x - .8 * s)} {f1(base - 50 * s)}V{f1(base - 55 * s)}h{f1(1.6 * s)}V{f1(base - 50 * s)}Z'
        xi = cx + k * 30 * s                                                                                       # inner domes
        d += f'M{f1(xi - 6 * s)} {f1(base - 36 * s)}V{f1(base - 42 * s)}Q{f1(xi - 6 * s)} {f1(base - 51 * s)} {f1(xi)} {f1(base - 52 * s)}Q{f1(xi + 6 * s)} {f1(base - 51 * s)} {f1(xi + 6 * s)} {f1(base - 42 * s)}V{f1(base - 36 * s)}Z'
    d += f'M{f1(cx - 23 * s)} {f1(base - 36 * s)}V{f1(base - 52 * s)}H{f1(cx + 23 * s)}V{f1(base - 36 * s)}Z'    # drum
    d += (f'M{f1(cx - 24 * s)} {f1(base - 52 * s)}C{f1(cx - 25 * s)} {f1(base - 74 * s)} {f1(cx - 9 * s)} {f1(base - 85 * s)} {f1(cx)} {f1(base - 87 * s)}'
          f'C{f1(cx + 9 * s)} {f1(base - 85 * s)} {f1(cx + 25 * s)} {f1(base - 74 * s)} {f1(cx + 24 * s)} {f1(base - 52 * s)}Z')   # dome
    d += f'M{f1(cx - 4.5 * s)} {f1(base - 86 * s)}V{f1(base - 94 * s)}H{f1(cx + 4.5 * s)}V{f1(base - 86 * s)}Z'  # lantern
    d += f'M{f1(cx - 3.5 * s)} {f1(base - 94 * s)}Q{f1(cx)} {f1(base - 99 * s)} {f1(cx + 3.5 * s)} {f1(base - 94 * s)}Z'
    d += f'M{f1(cx - .9 * s)} {f1(base - 98 * s)}L{f1(cx)} {f1(base - 107 * s)}L{f1(cx + .9 * s)} {f1(base - 98 * s)}Z'  # finial
    sc.add(f'<path d="{d}" fill="{col}"/>')
    # the dome's light side and the arcade
    sc.add(f'<path d="M{f1(cx - 24 * s)} {f1(base - 52 * s)}C{f1(cx - 25 * s)} {f1(base - 74 * s)} {f1(cx - 9 * s)} {f1(base - 85 * s)} {f1(cx)} {f1(base - 87 * s)}" '
           f'fill="none" stroke="{light or mix(col, WHITE, .35)}" stroke-opacity=".55" stroke-width="{f1(max(.6, 1.1 * s))}"/>')
    arc = ''
    for i in range(-11, 12):
        if abs(i) < 3:
            continue
        x = cx + i * 6 * s
        arc += f'M{f1(x - 1.8 * s)} {f1(base - 9 * s)}V{f1(base - 19 * s)}Q{f1(x)} {f1(base - 22 * s)} {f1(x + 1.8 * s)} {f1(base - 19 * s)}V{f1(base - 9 * s)}Z'
    sc.add(f'<path d="{arc}" fill="{win or c2}"' + (' opacity=".7"' if win else '') + '/>')
    cols_ = ''.join(f'M{f1(cx + i * 4 * s - .7 * s)} {f1(base - 9 * s)}V{f1(base - 33 * s)}h{f1(1.4 * s)}V{f1(base - 9 * s)}Z' for i in range(-4, 5))
    sc.add(f'<path d="{cols_}" fill="{mix(col, WHITE, .2)}" opacity=".7"/>')


def shaheed_minar(sc, x, base, h, col):
    """The Shaheed Minar at the Esplanade: a slender fluted column on a broad base, two balconies, a small cupola."""
    w = h * .045
    d = (f'M{f1(x - w * 2.2)} {f1(base)}L{f1(x - w * 1.4)} {f1(base - h * .1)}L{f1(x - w)} {f1(base - h * .82)}'
         f'H{f1(x - w * 1.5)}V{f1(base - h * .84)}H{f1(x - w * .8)}L{f1(x - w * .7)} {f1(base - h * .93)}H{f1(x - w * 1.1)}V{f1(base - h * .945)}'
         f'H{f1(x - w * .6)}Q{f1(x)} {f1(base - h * 1.02)} {f1(x + w * .6)} {f1(base - h * .945)}H{f1(x + w * 1.1)}V{f1(base - h * .93)}H{f1(x + w * .7)}'
         f'L{f1(x + w * .8)} {f1(base - h * .84)}H{f1(x + w * 1.5)}V{f1(base - h * .82)}H{f1(x + w)}L{f1(x + w * 1.4)} {f1(base - h * .1)}L{f1(x + w * 2.2)} {f1(base)}Z'
         f'M{f1(x - .4)} {f1(base - h * 1.0)}V{f1(base - h * 1.06)}h.8V{f1(base - h)}Z')
    sc.add(f'<path d="{d}" fill="{col}"/>')


def tall_tower(sc, x, base, w, h, col, lit=None):
    """The city's tallest residential tower near Chowringhee: a slim slab with a crown."""
    d = f'M{f1(x)} {f1(base)}V{f1(base - h)}l{f1(w * .2)} {f1(-h * .03)}h{f1(w * .6)}l{f1(w * .2)} {f1(h * .03)}V{f1(base)}Z'
    sc.add(f'<path d="{d}" fill="{col}"/>')
    if lit:
        fl = ''.join(f'M{f1(x + w * .15)} {f1(base - k * h / 40)}h{f1(w * .7)}' for k in range(3, 39, 2))
        sc.add(f'<path d="{fl}" stroke="{lit}" stroke-opacity=".35" stroke-width=".7"/>')


def kol_skyline(sc, hy, seed, col, lit=None, landmarks=(), far=True, lit_frac=.25):
    """The far bank: a low city with its markers (Victoria Memorial, Shaheed Minar, the tall tower, the bridges)."""
    t = sc.t
    win = sc.windows(lit=lit_frac, seed=seed + 3) if lit else None
    for kind, x, k in landmarks:
        if kind == 'victoria':
            victoria_memorial(sc, x, hy + 1, k, mix(col, t['sky'][2], .1), win=t['win'] if lit else None)
        elif kind == 'minar':
            shaheed_minar(sc, x, hy + 1, k, mix(col, t['sky'][2], .08))
        elif kind == 'tower':
            tall_tower(sc, x, hy + 1, 9 * k, 120 * k, mix(col, t['sky'][2], .14), lit=t['win'] if lit else None)
    if far:
        sc.skyline(hy + 1, 4, 16, mix(col, t['sky'][2], .25), seed=seed, wmin=7, wmax=20, win=win, win_op=.2, spires=.05)
        sc.haze(hy + 1, 16, .4)


def bari_row(sc, g, X, z0, z1, col, side=1, seed=41, lit=None, hmin=9, hmax=15, lit_frac=.35, shutters=None):
    """Old north-Kolkata houses along a lane: three and four storeys, a parapet on the roof, long cast-iron verandas,
    tall louvred shutters."""
    r = random.Random(seed)
    sv = sc.svg
    z = z0
    faces, trims, rails, dark, glow = '', '', '', '', ''
    shutters = shutters or scale(col, .55)
    while z < z1:
        dz = r.uniform(6, 11)
        hh = r.uniform(hmin, hmax)
        a, b = z, z + dz
        P = [g.pt(X, a), g.pt(X, b), g.pt(X, b, hh), g.pt(X, a, hh)]
        faces += 'M' + 'L'.join(f'{f1(x)} {f1(y)}' for x, y in P) + 'Z'
        # the parapet and the veranda slabs, projecting into the lane
        for Y in [hh] + ([hh * k for k in (.36, .64) if r.random() < .8] if g.s(b) > 1.2 else []):
            e = [g.pt(X, a, Y), g.pt(X, b, Y), g.pt(X - side * .9, b, Y - .18), g.pt(X - side * .9, a, Y - .18)]
            trims += 'M' + 'L'.join(f'{f1(x)} {f1(y)}' for x, y in e) + 'Z'
            if Y < hh:
                q0, q1 = g.pt(X - side * .9, a, Y + .9), g.pt(X - side * .9, b, Y + .9)
                rails += f'M{f1(q0[0])} {f1(q0[1])}L{f1(q1[0])} {f1(q1[1])}'
        # tall shuttered windows (only where a window is more than a pixel or two)
        storeys = max(2, int(hh / 3.4)) if g.s(b) > 2.2 else 0
        for s_ in range(storeys):
            Y0 = .9 + s_ * hh / storeys
            n_ = max(2, int(dz / 2.6))
            for k in range(n_):
                za = a + dz * (k + .28) / n_
                zb = za + dz * .44 / n_
                w_ = [g.pt(X, za, Y0), g.pt(X, zb, Y0), g.pt(X, zb, Y0 + 2.0), g.pt(X, za, Y0 + 2.0)]
                p_ = 'M' + 'L'.join(f'{f1(x)} {f1(y)}' for x, y in w_) + 'Z'
                if lit and r.random() < lit_frac:
                    glow += p_
                else:
                    dark += p_
        z = b
    sc.add(f'<path d="{faces}" fill="{col}"/>')
    sc.add(f'<path d="{dark}" fill="{shutters}"/><path d="{trims}" fill="{scale(col, .62)}"/>')
    if rails:
        sc.add(f'<path d="{rails}" stroke="{scale(col, .45)}" stroke-width=".8" fill="none"/>')
    if glow:
        sc.add(f'<path d="{glow}" fill="{lit}" opacity=".55"/><path d="{glow}" fill="{lit}" opacity=".3" filter="{sv.blur(2.2)}"/>')


def tram_lines(sc, g, X, z0, z1, h=6.2, col=None, every=14, rails=True, op=.8):
    """Tram tracks set in the road and the overhead wire on its span poles."""
    col = col or scale(sc.t['near'], 1.9)
    d = ''
    if rails:
        for dx in (-.72, .72):
            a, b = g.pt(X + dx, z0), g.pt(X + dx, z1)
            d += f'M{f1(a[0])} {f1(a[1])}L{f1(b[0])} {f1(b[1])}'
        sc.add(f'<path d="{d}" stroke="{mix(sc.t["road"], WHITE, .28)}" stroke-width=".9" opacity=".7"/>')
    a, b = g.pt(X, z0, h), g.pt(X, z1, h)
    w = f'M{f1(a[0])} {f1(a[1])}L{f1(b[0])} {f1(b[1])}'
    z = z0 + 2
    while z < min(z1, 160):
        p, q = g.pt(X - 7, z, h + .4), g.pt(X + 7, z, h + .4)
        w += f'M{f1(p[0])} {f1(p[1])}L{f1(q[0])} {f1(q[1])}'
        z += every
    sc.add(f'<path d="{w}" stroke="{col}" stroke-width=".7" fill="none" opacity="{op:g}"/>')


def light_gate(sc, g, z, half, h, col, dots=26, op=1.0):
    """A Puja light gate over the road: an arch of small lamps on two posts."""
    sv = sc.svg
    pts_ = []
    for i in range(dots + 1):
        a = math.pi * i / dots
        X = -half * math.cos(a)
        Y = h + (h * .38) * math.sin(a)
        pts_.append(g.pt(X, z, Y))
    s = g.s(z)
    r = max(.5, s * .09)
    inner = [g.pt(-half * .82 * math.cos(math.pi * i / dots), z, h * .92 + h * .3 * math.sin(math.pi * i / dots)) for i in range(dots + 1)]
    gap = math.hypot(pts_[1][0] - pts_[0][0], pts_[1][1] - pts_[0][1])
    arcs = f'M{pts(pts_)}M{pts(inner)}'
    dot = f'stroke-width="{f1(r * 2)}" stroke-linecap="round" stroke-dasharray="0 {f1(gap)}" fill="none"'
    posts = ''
    for X in (-half, half):
        a_, b_ = g.pt(X, z), g.pt(X, z, h)
        posts += f'M{f1(a_[0])} {f1(a_[1])}L{f1(b_[0])} {f1(b_[1])}'
    sc.add(f'<g opacity="{op:g}"><path d="{posts}" stroke="{scale(sc.t["near"], 1.6)}" stroke-width="{f1(max(.6, s * .12))}"/>'
           f'<path d="{arcs}" stroke="{col}" {dot}/><path d="{arcs}" stroke="{col}" {dot} opacity=".5" filter="{sv.blur(max(1, s * .2))}"/></g>')


def pandal(sc, cx, base, w, col, lit=None, glow=None):
    """A Durga Puja pandal seen down the street: a tall temple-like facade of bamboo and cloth, a deep entrance arch,
    side towers; outlined in strings of small lamps at night."""
    sv = sc.svg
    h = w * .78
    d = (f'M{f1(cx - w / 2)} {f1(base)}V{f1(base - h * .5)}L{f1(cx - w * .36)} {f1(base - h * .62)}V{f1(base - h * .5)}'
         f'L{f1(cx - w * .2)} {f1(base - h * .7)}L{f1(cx)} {f1(base - h)}L{f1(cx + w * .2)} {f1(base - h * .7)}'
         f'L{f1(cx + w * .36)} {f1(base - h * .5)}V{f1(base - h * .62)}L{f1(cx + w / 2)} {f1(base - h * .5)}V{f1(base)}Z')
    sc.add(f'<path d="{d}" fill="{col}"/>')
    # the spires on the side towers and the crown
    sp = ''.join(f'M{f1(x - w * .03)} {f1(base - h * hh)}L{f1(x)} {f1(base - h * (hh + .12))}L{f1(x + w * .03)} {f1(base - h * hh)}Z'
                 for x, hh in ((cx - w * .43, .56), (cx + w * .43, .56), (cx, .98)))
    sc.add(f'<path d="{sp}" fill="{col}"/>')
    # the entrance: a tall pointed arch, glowing inside
    aw, ah = w * .24, h * .58
    arch = f'M{f1(cx - aw / 2)} {f1(base)}V{f1(base - ah * .6)}Q{f1(cx - aw / 2)} {f1(base - ah)} {f1(cx)} {f1(base - ah * 1.05)}Q{f1(cx + aw / 2)} {f1(base - ah)} {f1(cx + aw / 2)} {f1(base - ah * .6)}V{f1(base)}Z'
    inner = glow or mix(col, WHITE, .4)
    sc.add(f'<path d="{arch}" fill="{inner}"/>')
    if glow:
        sc.glow(cx, base - ah * .4, w * .2, glow, .5)
    # side openings and relief bands
    bands = ''.join(f'M{f1(cx - w * .48)} {f1(base - h * k)}H{f1(cx + w * .48)}' for k in (.16, .32, .46))
    sc.add(f'<path d="{bands}" stroke="{mix(col, WHITE, .14)}" stroke-width="{f1(max(.6, w * .006))}"/>')
    if lit:
        # strings of lamps along the outline and the relief bands
        outline = [(cx - w / 2, base - h * .5), (cx - w * .36, base - h * .62), (cx - w * .36, base - h * .5), (cx - w * .2, base - h * .7),
                   (cx, base - h), (cx + w * .2, base - h * .7), (cx + w * .36, base - h * .5), (cx + w * .36, base - h * .62), (cx + w / 2, base - h * .5)]
        strings = f'M{pts(outline)}' + ''.join(f'M{f1(cx - w * .46)} {f1(base - h * k)}H{f1(cx + w * .46)}' for k in (.16, .32, .46))
        dot = f'stroke-width="{f1(max(1, w * .012))}" stroke-linecap="round" stroke-dasharray="0 {f1(max(2.2, w * .022))}" fill="none"'
        sc.add(f'<path d="{strings}" stroke="{lit}" {dot}/><path d="{strings}" stroke="{lit}" {dot} opacity=".45" filter="{sv.blur(max(1, w * .01))}"/>')


def colonnade(sc, cx, base, w, h, col, n=8, pediment=True, light=None):
    """A Greek-revival riverside pavilion (the ghats' colonnades): steps, a row of columns, an entablature, a pediment."""
    c2 = mix(col, '#000', .35)
    d = f'M{f1(cx - w * .56)} {f1(base)}V{f1(base - h * .06)}H{f1(cx + w * .56)}V{f1(base)}Z'
    d += f'M{f1(cx - w * .52)} {f1(base - h * .06)}V{f1(base - h * .12)}H{f1(cx + w * .52)}V{f1(base - h * .06)}Z'
    cw = w / (n * 2 - 1)
    for i in range(n):
        x = cx - w / 2 + i * 2 * cw
        d += f'M{f1(x)} {f1(base - h * .12)}V{f1(base - h * .78)}h{f1(cw)}V{f1(base - h * .12)}Z'
    d += f'M{f1(cx - w * .54)} {f1(base - h * .78)}V{f1(base - h * .92)}H{f1(cx + w * .54)}V{f1(base - h * .78)}Z'
    if pediment:
        d += f'M{f1(cx - w * .56)} {f1(base - h * .92)}L{f1(cx)} {f1(base - h * 1.18)}L{f1(cx + w * .56)} {f1(base - h * .92)}Z'
    sc.add(f'<path d="{d}" fill="{col}"/>')
    # the shadowed interior between the columns, the lit edge of each column
    inner = ''.join(f'M{f1(cx - w / 2 + (2 * i + 1) * cw)} {f1(base - h * .12)}V{f1(base - h * .76)}h{f1(cw)}V{f1(base - h * .12)}Z' for i in range(n - 1))
    sc.add(f'<path d="{inner}" fill="{c2}" opacity=".75"/>')
    if light:
        lit = ''.join(f'M{f1(cx - w / 2 + i * 2 * cw)} {f1(base - h * .12)}V{f1(base - h * .78)}' for i in range(n))
        sc.add(f'<path d="{lit}" stroke="{light}" stroke-opacity=".5" stroke-width="{f1(max(.6, cw * .25))}"/>')


def ghat_steps(sc, x0, x1, y0, y1, col, n=7):
    """Steps going down into the river."""
    out = ''
    for i in range(n):
        y = y0 + (y1 - y0) * i / n
        hgt = (y1 - y0) / n
        out += f'<rect x="{f1(x0 - i * 2)}" y="{f1(y)}" width="{f1(x1 - x0 + i * 4)}" height="{f1(hgt)}" fill="{mix(col, WHITE, .06 * (i % 2))}"/>'
        out += f'<rect x="{f1(x0 - i * 2)}" y="{f1(y)}" width="{f1(x1 - x0 + i * 4)}" height=".8" fill="{mix(col, WHITE, .25)}"/>'
    sc.add(out)


def country_boat(sc, x, y, L, col, canopy=None, flip=False):
    """A Hooghly country boat (nouka): a long low hull sweeping up at both ends, a low hooped canopy amidships."""
    k = -1 if flip else 1
    h = L * .06
    hull = (f'M{f1(x - L / 2)} {f1(y - h * 2.2)}Q{f1(x - L * .36)} {f1(y + h * .4)} {f1(x)} {f1(y + h * .5)}'
            f'Q{f1(x + L * .36)} {f1(y + h * .4)} {f1(x + L / 2)} {f1(y - h * 2.6)}L{f1(x + L * .44)} {f1(y - h * .9)}Q{f1(x)} {f1(y - h * .5)} {f1(x - L * .44)} {f1(y - h * .8)}Z')
    cx = x + k * L * .06
    can = f'M{f1(cx - L * .2)} {f1(y - h * .6)}C{f1(cx - L * .19)} {f1(y - h * 2.6)} {f1(cx + L * .19)} {f1(y - h * 2.6)} {f1(cx + L * .2)} {f1(y - h * .6)}Z'
    ribs = ''.join(f'M{f1(cx + L * .2 * u)} {f1(y - h * .6)}V{f1(y - h * (2.05 - 1.2 * u * u))}' for u in (-.6, -.2, .2, .6))
    sc.add(f'<path d="{hull}" fill="{col}"/><path d="{can}" fill="{canopy or mix(col, WHITE, .16)}"/>'
           f'<path d="{ribs}" stroke="{col}" stroke-width="{f1(max(.5, L * .006))}" opacity=".6"/>'
           f'<path d="M{f1(x + k * L * .34)} {f1(y - h * .8)}L{f1(x + k * L * .52)} {f1(y + h * 1.4)}" stroke="{col}" stroke-width="{f1(max(.6, L * .01))}"/>')


def ferry_launch(sc, x, y, L, col, lit=None):
    """A Hooghly ferry launch: a long low hull and a two-tier cabin."""
    h = L * .16
    d = (f'M{f1(x - L / 2)} {f1(y - h * .5)}L{f1(x - L * .44)} {f1(y)}H{f1(x + L * .4)}L{f1(x + L / 2)} {f1(y - h * .6)}Z'
         f'M{f1(x - L * .4)} {f1(y - h * .5)}V{f1(y - h * 1.15)}H{f1(x + L * .36)}V{f1(y - h * .5)}Z'
         f'M{f1(x - L * .3)} {f1(y - h * 1.15)}V{f1(y - h * 1.65)}H{f1(x + L * .2)}V{f1(y - h * 1.15)}Z')
    sc.add(f'<path d="{d}" fill="{col}"/>')
    win = ''.join(f'<rect x="{f1(x - L * .37 + i * L * .07)}" y="{f1(y - h * 1.0)}" width="{f1(L * .045)}" height="{f1(h * .3)}"/>' for i in range(10))
    sc.add(f'<g fill="{lit or mix(col, WHITE, .3)}" opacity="{.8 if lit else .5}">{win}</g>')


def floodlight_mast(sc, x, base, h, col, light, op=.9):
    """A stadium floodlight mast: a tall tapering lattice tower and a tilted bank of lamps that floods the night."""
    sv = sc.svg
    w = h * .05
    d = f'M{f1(x - w)} {f1(base)}L{f1(x - w * .35)} {f1(base - h)}H{f1(x + w * .35)}L{f1(x + w)} {f1(base)}Z'
    lat = ''.join(f'M{f1(x - w + (w * .65) * k / 10)} {f1(base - h * k / 10)}L{f1(x + w - (w * .65) * (k + 1) / 10)} {f1(base - h * (k + 1) / 10)}' for k in range(10))
    sc.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{f1(max(.6, w * .22))}"/><path d="{lat}" stroke="{col}" stroke-width="{f1(max(.4, w * .14))}"/>')
    bw, bh = h * .16, h * .11
    bank = f'<rect x="{f1(x - bw / 2)}" y="{f1(base - h - bh)}" width="{f1(bw)}" height="{f1(bh)}" fill="{col}"/>'
    cells = ''.join(f'<rect x="{f1(x - bw / 2 + bw * (i + .12) / 5)}" y="{f1(base - h - bh + bh * (j + .14) / 4)}" width="{f1(bw * .76 / 5)}" height="{f1(bh * .72 / 4)}"/>' for i in range(5) for j in range(4))
    sc.add(bank + f'<g fill="{light}">{cells}</g>')
    sc.add(f'<circle cx="{f1(x)}" cy="{f1(base - h - bh / 2)}" r="{f1(bw * 1.6)}" fill="{light}" opacity="{op * .45:.2f}" filter="{sv.blur(bw * .7)}"/>')


def bowl(sc, cx, base, w, col, rim=None):
    """A cricket ground's stands: a long low bowl with tiered stands and a cantilevered roof line."""
    h = w * .13
    d = f'M{f1(cx - w / 2)} {f1(base)}L{f1(cx - w * .48)} {f1(base - h)}H{f1(cx + w * .48)}L{f1(cx + w / 2)} {f1(base)}Z'
    sc.add(f'<path d="{d}" fill="{col}"/>')
    tiers = ''.join(f'M{f1(cx - w * .47)} {f1(base - h * k)}H{f1(cx + w * .47)}' for k in (.3, .55, .8))
    sc.add(f'<path d="{tiers}" stroke="{rim or mix(col, WHITE, .2)}" stroke-width="{f1(max(.6, w * .003))}" opacity=".7"/>')
    sc.add(f'<path d="M{f1(cx - w * .5)} {f1(base - h * 1.05)}H{f1(cx + w * .5)}" stroke="{rim or mix(col, WHITE, .3)}" stroke-width="{f1(max(1, w * .006))}"/>')


def howrah_station(sc, cx, base, w, col, lit=None):
    """Howrah Station from the river: a long brick front with eight square towers under pyramid roofs, arched bays."""
    h = w * .14
    d = f'M{f1(cx - w / 2)} {f1(base)}V{f1(base - h)}H{f1(cx + w / 2)}V{f1(base)}Z'
    xs = [cx - w / 2 + w * k / 7 for k in range(8)]
    for i, x in enumerate(xs):
        tw = w * .045
        th = h * (1.9 if i in (3, 4) else 1.55)
        d += f'M{f1(x - tw / 2)} {f1(base - h + 1)}V{f1(base - th)}L{f1(x)} {f1(base - th - tw * .9)}L{f1(x + tw / 2)} {f1(base - th)}V{f1(base - h + 1)}Z'
    sc.add(f'<path d="{d}" fill="{col}"/>')
    arches = ''
    for i in range(28):
        x = cx - w * .48 + w * .96 * i / 27
        arches += f'M{f1(x - w * .008)} {f1(base - h * .1)}V{f1(base - h * .55)}Q{f1(x)} {f1(base - h * .66)} {f1(x + w * .008)} {f1(base - h * .55)}V{f1(base - h * .1)}Z'
    sc.add(f'<path d="{arches}" fill="{lit or mix(col, "#000", .35)}"' + (' opacity=".75"' if lit else '') + '/>')


def fallen_tree(sc, g, X0, X1, z, col, leaf, seed=12, light=None):
    """A cyclone-felled tree lying across the road: the root plate torn up on its edge at the kerb, the trunk on the
    tarmac, the crown heaped over the far lanes."""
    r = random.Random(seed)
    sv = sc.svg
    light = light or mix(col, WHITE, .35)
    # the root plate: a disc of earth and roots standing on its edge
    rx, ry = g.pt(X0, z, 1.5)
    s = g.s(z)
    sc.add(f'<ellipse cx="{f1(rx)}" cy="{f1(ry)}" rx="{f1(s * .55)}" ry="{f1(s * 1.6)}" fill="{scale(col, .75)}"/>')
    roots = ''.join(f'M{f1(rx)} {f1(ry)}l{f1(r.uniform(-.9, .9) * s)} {f1(r.uniform(-1.9, 1.9) * s)}' for _ in range(9))
    sc.add(f'<path d="{roots}" stroke="{scale(col, .55)}" stroke-width="{f1(max(.7, s * .07))}" fill="none"/>')
    # the trunk: a tapered log lying across the lanes, lit along its top
    top, bot = [], []
    n = 12
    for i in range(n + 1):
        u = i / n
        X = X0 + (X1 - X0) * u
        rad = .5 - .32 * u
        top.append(g.pt(X, z + u * 1.5, .5 + rad))
        bot.append(g.pt(X, z + u * 1.5, .5 - rad))
    sc.add(f'<polygon points="{pts(top + list(reversed(bot)))}" fill="{col}"/>')
    sc.add(f'<polyline points="{pts(top)}" fill="none" stroke="{light}" stroke-width="{f1(max(.8, s * .07))}" stroke-opacity=".7"/>')
    # broken branches and the crown, heaped on the far lanes
    br, lv = '', []
    cx_, cy_ = g.pt(X1, z + 1.5, 1.2)
    for _ in range(14):
        a = r.uniform(-math.pi * .95, -math.pi * .05)
        L_ = s * r.uniform(1.2, 3.2)
        sx_, sy_ = g.pt(X0 + (X1 - X0) * r.uniform(.45, 1), z + 1, r.uniform(.4, 1.1))
        ex, ey = sx_ + L_ * math.cos(a), sy_ + L_ * math.sin(a) * .6
        br += f'M{f1(sx_)} {f1(sy_)}L{f1(ex)} {f1(ey)}'
        for _ in range(3):
            lv.append(f'<ellipse cx="{f1(ex + r.uniform(-1, 1) * s * .7)}" cy="{f1(ey + r.uniform(-1, 1) * s * .35)}" rx="{f1(s * r.uniform(.6, 1.2))}" ry="{f1(s * r.uniform(.35, .7))}"/>')
    for _ in range(26):
        lv.append(f'<ellipse cx="{f1(cx_ + r.uniform(-3.2, 3.5) * s)}" cy="{f1(cy_ + r.uniform(-1.6, .8) * s)}" rx="{f1(s * r.uniform(.7, 1.5))}" ry="{f1(s * r.uniform(.4, .8))}"/>')
    sc.add(f'<path d="{br}" stroke="{col}" stroke-width="{f1(max(.9, s * .1))}" stroke-linecap="round" fill="none"/>')
    sc.add(f'<g fill="{leaf}">{"".join(lv)}</g><g fill="{mix(leaf, WHITE, .12)}" opacity=".5" transform="translate(0 {f1(-s * .15)})">{"".join(lv[::3])}</g>')


def palms(sc, xs, base, h, col, bend=0.0, seed=4):
    """Palms along a promenade, bending with the wind (bend > 0 leans them right)."""
    r = random.Random(seed)
    out = ''
    for x in xs:
        hh = h * r.uniform(.8, 1.1)
        tx, ty = x + bend * hh * .35, base - hh
        out += f'<path d="M{f1(x)} {f1(base)}Q{f1(x + bend * hh * .05)} {f1(base - hh * .6)} {f1(tx)} {f1(ty)}" stroke="{col}" stroke-width="{f1(max(.8, hh * .035))}" fill="none"/>'
        for k in range(7):
            a = -math.pi * (.08 + .84 * k / 6) + bend * .5
            L = hh * r.uniform(.28, .36)
            ex, ey = tx + L * math.cos(a), ty + L * math.sin(a) * .7 + L * .2
            out += f'<path d="M{f1(tx)} {f1(ty)}Q{f1((tx + ex) / 2)} {f1(ty - L * .25)} {f1(ex)} {f1(ey)}" stroke="{col}" stroke-width="{f1(max(.6, hh * .028))}" fill="none"/>'
    sc.add(out)


def tide_gauge(sc, x, top, bottom, col, mark):
    """A tide gauge post on the kerb: ruled marks, the water standing high on it."""
    d = f'M{f1(x)} {f1(top)}V{f1(bottom)}'
    ticks = ''.join(f'M{f1(x)} {f1(top + (bottom - top) * k / 10)}h{f1(7 if k % 2 == 0 else 4)}' for k in range(11))
    sc.add(f'<path d="{d}" stroke="{col}" stroke-width="4"/><path d="{ticks}" stroke="{col}" stroke-width="1.6"/>'
           f'<path d="M{f1(x - 9)} {f1(mark)}h18" stroke="{TEAL}" stroke-width="3" stroke-linecap="round"/>'
           f'<rect x="{f1(x - 12)}" y="{f1(mark)}" width="24" height="{f1(bottom - mark)}" fill="{TEAL}" opacity=".16"/>')


def port_cranes(sc, xs, base, h, col):
    """Ship-to-shore cranes at the docks."""
    out = ''
    for x in xs:
        s = h / 100
        out += (f'M{f1(x - 14 * s)} {f1(base)}L{f1(x - 10 * s)} {f1(base - 70 * s)}H{f1(x - 8 * s)}L{f1(x - 11 * s)} {f1(base)}Z'
                f'M{f1(x + 14 * s)} {f1(base)}L{f1(x + 10 * s)} {f1(base - 70 * s)}H{f1(x + 8 * s)}L{f1(x + 11 * s)} {f1(base)}Z'
                f'M{f1(x - 40 * s)} {f1(base - 70 * s)}H{f1(x + 70 * s)}v{f1(-6 * s)}H{f1(x - 40 * s)}Z'
                f'M{f1(x - 4 * s)} {f1(base - 76 * s)}L{f1(x)} {f1(base - 100 * s)}L{f1(x + 4 * s)} {f1(base - 76 * s)}Z')
    sc.add(f'<path d="{out}" fill="{col}"/>')


TAXI_PAINT = '#E9B32A'      # the Ambassador's yellow, graded into each scene (never a UI meaning colour)


def taxi_tone(sc, k=.38):
    return mix(TAXI_PAINT, sc.t['mid'], k)


def kol_backdrop(sc, hy, seed=5, landmarks=(), lit=.3, mid=True, far_h=(6, 22)):
    t = sc.t
    kol_skyline(sc, hy, seed, t['far'], lit=bool(lit), landmarks=landmarks, lit_frac=lit or .2)
    if mid:
        win = sc.windows(lit=lit) if lit else None
        sc.skyline(hy + 3, far_h[0] * .6, far_h[1] * .6, t['mid'], seed=seed + 1, wmin=12, wmax=30, win=win, win_op=.3, spires=0)


def ev_protected_movement():
    sc = Scene('Protected movement: a convoy on a cleared road towards Vidyasagar Setu at dusk', 'dusk', seed=101)
    t = sc.t
    hy, g = 196, Ground(640, 360, 196, 300, h=2.6)
    sc.sky(hy, sun=(470, hy - 18), sun_r=56)
    sc.clouds(9, 50, 150)
    vidyasagar_setu(sc, 40, 640, hy - 4, 118, mix(t['mid'], t['far'], .55), op=1)
    kol_backdrop(sc, hy, seed=5, mid=False, lit=.15)
    ground_plane(sc, hy)
    facades(sc, g, -22, 40, 700, mix(t['mid'], t['far'], .3), 1, seed=61, floors=t['win'], floor_op=.16)
    facades(sc, g, 22, 36, 700, mix(t['mid'], t['far'], .2), -1, seed=62, floors=t['win'], floor_op=.16)
    sc.road(g, 10.5)
    for X in (-3.5, 3.5):
        sc.dashes(g, X, t['line'], op=.55)
    sc.barrier(g, -10.2, 6, 160, '#4A4846', h=.9, stripe='#A9A39C')
    sc.barrier(g, 10.2, 6, 160, '#4A4846', h=.9, stripe='#A9A39C')
    sc.streetlights(g, -12, [12, 20, 32, 52, 85, 140, 230])
    sc.streetlights(g, 12, [16, 26, 42, 68, 110, 180])
    sc.ribbon(g, [(0, 3), (0, 14), (0, 240)], TEAL, w=.2)
    for z, kind, body, bc in ((30, 'suv', '#E9ECEF', WHITE), (21.5, 'suv', '#1E2023', None), (15, 'suv', '#E9ECEF', WHITE)):
        sc.car(g, 0, z, kind=kind, body=body, beacon=bc)
    sc.haze(hy + 40, 40, .18)
    return sc.finish()


def ev_procession():
    sc = Scene('Procession: a Puja route through a north Kolkata lane under light gates, towards a glowing pandal', 'dusk', seed=102)
    t = sc.t
    hy, g = 206, Ground(640, 360, 206, 320, h=1.9)
    sc.sky(hy, sun=(330, hy - 52), sun_r=60)
    sc.clouds(7, 40, 130)
    kol_backdrop(sc, hy, seed=8, mid=False, lit=.2)
    ground_plane(sc, hy)
    end_z = 80
    pandal(sc, 320, g.y(end_z), 150, mix(t['mid'], t['far'], .3), lit=t['lamp'], glow=mix(t['lamp'], t['glow'], .3))
    sc.road(g, 6, col=mix(t['road'], t['haze'], .1))
    bari_row(sc, g, -6, 8, end_z - 4, mix(t['mid'], '#000', .1), side=1, seed=41, lit=t['win'], hmin=9, hmax=14, lit_frac=.3)
    bari_row(sc, g, 6, 8, end_z - 4, mix(t['mid'], '#000', .2), side=-1, seed=42, lit=t['win'], hmin=9, hmax=14, lit_frac=.3)
    for z in (14, 26, 46):
        light_gate(sc, g, z, 5.4, 6.4, t['lamp'], dots=20)
    sc.ribbon(g, [(0, 3), (0, 20), (0, end_z)], TEAL, w=.18)
    sc.crowd(g, -4.6, 4.6, 26, end_z - 6, mix(t['near'], t['mid'], .4), n=120, seed=33)
    sc.haze(g.y(30), 50, .22)
    return sc.finish()


def ev_mass_gathering():
    sc = Scene('Durga Puja crowd: a great pandal lit at night, the crowd one distant mass under the light gates', 'night', seed=103)
    t = sc.t
    hy, g = 206, Ground(640, 360, 206, 320, h=2.2)
    sc.sky(hy)
    sc.add(f'<ellipse cx="320" cy="{hy - 40}" rx="330" ry="90" fill="#FFF3DF" opacity=".16" filter="{sc.svg.blur(22)}"/>')
    kol_backdrop(sc, hy, seed=12, mid=False, lit=.2)
    ground_plane(sc, hy, col='#151516')
    pandal(sc, 320, g.y(70), 300, '#2A2725', lit='#FFE9C4', glow='#F7E2C0')
    sc.add(f'<ellipse cx="320" cy="{f1(g.y(40))}" rx="420" ry="54" fill="{sc.svg.rad([(0, "#8A8279", .7), (.55, "#4A4540", .3), (1, "#000", 0)])}"/>')
    for z in (12, 20, 32):
        light_gate(sc, g, z, 9, 7.5, '#FFE9C4', dots=24)
    for X0, X1 in ((-14, -5), (0, 0), (14, 5)):
        sc.ribbon(g, [(X0, 3), ((X0 + X1) / 2, 25), (X1, 66)], TEAL, w=.22, op=.85)
    sc.crowd(g, -22, -3, 10, 64, '#060607', n=120, seed=35, blur=.35)
    sc.crowd(g, 3, 22, 10, 64, '#060607', n=120, seed=36, blur=.35)
    return sc.finish()


def ev_race():
    sc = Scene('Race: the marathon course on Red Road at dawn, Victoria Memorial beyond the trees', 'dawn', seed=104)
    t = sc.t
    hy, g = 204, Ground(640, 360, 204, 300, h=2.2)
    sc.sky(hy, sun=(160, hy - 30), sun_r=70)
    sc.clouds(8, 40, 140, op=.3)
    victoria_memorial(sc, 470, hy + 2, .95, mix(t['far'], t['sky'][2], .15))
    sc.trees(0, 640, hy + 3, 10, 22, mix(t['mid'], t['far'], .35), seed=14, n=60)
    ground_plane(sc, hy)
    sc.road(g, 9)
    sc.barrier(g, -8.8, 4, 140, '#8E8882', h=1.0, stripe='#E2DCD5', every=2.2)
    sc.barrier(g, 8.8, 4, 140, '#8E8882', h=1.0, stripe='#E2DCD5', every=2.2)
    sc.ribbon(g, [(-1.2, 3), (-1.2, 40), (-1.2, 400)], TEAL, w=.16)
    sc.gantry(g, 30, 9.4, 6.4, '#2D2C2B', depth=1.6, signs=[(0, 10, 1.2, '#E9E4DE')])
    sc.streetlights(g, -11, [14, 26, 48, 90, 160], col='#FFF6EA')
    sc.streetlights(g, 11, [18, 34, 64, 120], col='#FFF6EA')
    sc.crowd(g, -5, 5, 120, 200, mix(t['mid'], t['haze'], .3), n=46, seed=39, blur=.5)
    return sc.finish(vign=.55)


def ev_ceremonial():
    sc = Scene('Ceremonial: a flag-lined Red Road parade route, Victoria Memorial at the end of the avenue', 'day', seed=105)
    t = sc.t
    hy, g = 210, Ground(640, 360, 210, 320, h=1.8)
    sc.sky(hy, sun=(160, 60), sun_r=50)
    sc.clouds(10, 30, 150, col='#FFFFFF', op=.45)
    kol_skyline(sc, hy, 16, t['far'], landmarks=(('victoria', 320, 1.25),), far=True)
    ground_plane(sc, hy, col='#8C8F92')
    sc.road(g, 6, col='#6E7174')
    sc.trees(0, 170, g.y(60), 18, 34, mix(t['near'], t['mid'], .3), seed=9)
    sc.trees(470, 640, g.y(60), 18, 34, mix(t['near'], t['mid'], .3), seed=10)
    d, fl = '', ''
    for X in (-7.5, 7.5):
        for z in (14, 19, 27, 38, 54, 76, 104):
            x, yb = g.pt(X, z)
            _, yt = g.pt(X, z, 7.5)
            s = g.s(z)
            d += f'M{f1(x)} {f1(yb)}V{f1(yt)}'
            fl += f'M{f1(x)} {f1(yt)}q{f1(s * .3)} {f1(-s * .1)} {f1(s * .7)} 0v{f1(s * .45)}q{f1(-s * .4)} {f1(s * .1)} {f1(-s * .7)} 0Z'
    sc.add(f'<path d="{d}" stroke="{t["near"]}" stroke-width=".8"/><path d="{fl}" fill="#F4F5F6"/>')
    sc.ribbon(g, [(0, 3), (0, 30), (0, 118)], TEAL, w=.26, glow=True, op=.9)
    return sc.finish(vign=.45)


def ev_egress_surge():
    sc = Scene('Stadium egress: crowds stream out of Eden Gardens under its floodlights at night', 'night', seed=106)
    t = sc.t
    hy, g = 168, Ground(640, 360, 168, 360, h=6)
    sc.sky(hy)
    sc.add(f'<ellipse cx="250" cy="{hy - 40}" rx="300" ry="80" fill="#FFF3DF" opacity=".16" filter="{sc.svg.blur(18)}"/>')
    kol_backdrop(sc, hy, seed=18, mid=False, lit=.12)
    ground_plane(sc, hy, col='#1A1A1B')
    sc.add(f'<ellipse cx="300" cy="{hy + 50}" rx="380" ry="80" fill="{sc.svg.rad([(0, "#5E5952", .6), (1, "#000", 0)])}"/>')
    bowl(sc, 250, hy + 40, 460, '#1C1C1E', rim='#8A847C')
    for x, hgt in ((40, 120), (150, 142), (350, 142), (460, 120)):
        floodlight_mast(sc, x, hy + 30, hgt, '#2C2C2E', '#FFF6E6')
    sc.road(g, 7)
    for X in (-2.3, 2.3):
        sc.dashes(g, X, '#5C5C5C', op=.5)
    for X in (-10.5, 10.5):
        P = [g.pt(X - 2.6, 4), g.pt(X - 2.6, 200), g.pt(X + 2.6, 200), g.pt(X + 2.6, 4)]
        sc.add(f'<polygon points="{pts(P)}" fill="#6A645D" opacity=".5"/>')
    sc.crowd(g, -13, -8, 7, 90, '#030303', n=180, seed=37, blur=.3)
    sc.crowd(g, 8, 13, 7, 90, '#030303', n=160, seed=38, blur=.3)
    d = ''
    for z in (12, 18, 27, 40, 60, 90):
        for X in (-4.6, 0, 4.6):
            a, b, c = g.pt(X - 1.2, z + 1.4), g.pt(X, z), g.pt(X + 1.2, z + 1.4)
            d += f'M{f1(a[0])} {f1(a[1])}L{f1(b[0])} {f1(b[1])}L{f1(c[0])} {f1(c[1])}'
    sc.add(f'<path d="{d}" stroke="{TEAL}" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round" filter="{sc.svg.blur(2)}" opacity=".7"/>')
    sc.add(f'<path d="{d}" stroke="{TEAL}" stroke-width="1.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    sc.streetlights(g, -14.5, [12, 20, 34, 56, 92], h=10)
    sc.streetlights(g, 14.5, [14, 24, 40, 66, 110], h=10)
    for z in (16, 24):
        sc.car(g, 10.5, z, kind='bus', body='#D9DCDF')
    return sc.finish()


def ev_emergency_evacuation():
    sc = Scene('Cyclone evacuation: buses on a cleared route under a storm sky, palms bending in the wind', 'storm', seed=107)
    t = sc.t
    hy, g = 192, Ground(640, 360, 192, 380, h=2.6)
    sc.sky(hy)
    sc.clouds(16, 10, 150, col='#2B2F32', op=.8, rx=(90, 220), ry=(16, 36), seed=6)
    kol_backdrop(sc, hy, seed=20, lit=.1)
    ground_plane(sc, hy)
    palms(sc, (30, 70, 118, 520, 566, 610), hy + 12, 70, mix(t['near'], t['mid'], .2), bend=.6)
    facades(sc, g, -16, 22, 500, mix(t['mid'], t['far'], .2), 1, seed=63, hmin=8, hmax=16, floors=t['win'], floor_op=.14)
    sc.road(g, 8)
    sc.dashes(g, 0, t['line'], op=.5)
    for z in (36, 25, 17, 11.5):
        sc.car(g, 3.8, z, kind='bus', body='#E4E6E8')
    sc.ribbon(g, [(-3.6, 3), (-3.6, 60), (-3.6, 400)], TEAL, w=.2)
    x, y = g.pt(-9.5, 16, 3.2)
    sc.add(f'<path d="M{f1(x)} {f1(g.y(16))}V{f1(y)}" stroke="{t["near"]}" stroke-width="1.6"/>')
    sc.glow(x, y, 16, TEAL, .6)
    sc.add(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="3.2" fill="{TEAL}"/>')
    sc.streetlights(g, 9.6, [14, 24, 40, 66, 110])
    sc.rain(220, '#DDE2E5', op=.16, seed=23, ang=-.32)
    return sc.finish()


def ev_flooding():
    sc = Scene('Waterlogging at high tide: a north Kolkata street under water, tram wires overhead, a bus wading, the tide gauge high', 'storm', seed=108)
    t = sc.t
    hy, g = 196, Ground(640, 360, 196, 300, h=1.8)
    sc.sky(hy)
    sc.clouds(14, 20, 160, col='#3B3F42', op=.7, rx=(80, 200), ry=(14, 30))
    kol_backdrop(sc, hy, seed=22, lit=.1, mid=False)
    ground_plane(sc, hy)
    bari_row(sc, g, -10, 6, 110, t['mid'], side=1, seed=64, lit=t['win'], hmin=10, hmax=16, lit_frac=.12)
    bari_row(sc, g, 10, 6, 110, mix(t['mid'], '#000', .2), side=-1, seed=65, lit=t['win'], hmin=10, hmax=16, lit_frac=.1)
    water = [g.pt(-10, 2.5), g.pt(-10, 900), g.pt(10, 900), g.pt(10, 2.5)]
    sc.add(f'<polygon points="{pts(water)}" fill="{sc.svg.lin([(0, mix(t["sky"][2], WHITE, .1)), (.3, t["sky"][1]), (1, mix(t["sky"][0], "#000", .2))], 0, hy, 0, 360, user=True)}"/>')
    r = random.Random(3)
    d = ''.join(f'M{f1(x)} {f1(y)}h{f1(r.uniform(6, 30) * (y - hy) / 160)}' for x, y in ((r.uniform(0, 640), hy + (360 - hy) * r.random() ** 1.5) for _ in range(70)))
    sc.add(f'<path d="{d}" stroke="#FFFFFF" stroke-opacity=".18" stroke-width=".8"/>')
    tram_lines(sc, g, -1.5, 4, 600, h=6.4, rails=False)
    for X, zs in ((-9, (14, 24, 40, 70)), (9, (18, 30, 52))):
        sc.streetlights(g, X, zs, pool=False, h=8)
        for z in zs:
            sc.reflection(g.pt(X + (1.6 if X < 0 else -1.6), z)[0], g.y(z), 40 * g.s(z) / 10 + 10, t['lamp'], w=2.4 * g.s(z) / 8 + 1, op=.4)
    sc.car(g, 1.5, 21, kind='bus', body='#D6D9DC')
    bx = g.pt(1.5, 21)[0]
    sc.add(f'<rect x="{f1(bx - 28)}" y="{f1(g.y(21) - 7)}" width="56" height="9" fill="{t["sky"][1]}" opacity=".85"/>')
    sc.reflection(bx - 12, g.y(21) + 2, 40, t['lamp'], w=4, op=.5)
    sc.reflection(bx + 12, g.y(21) + 2, 40, t['lamp'], w=4, op=.5)
    # the taxi stalled in the water, half under
    tx_ = g.pt(-5, 13)
    sc.car(g, -5, 13, kind='taxi', body=taxi_tone(sc, .5))
    sc.add(f'<rect x="{f1(tx_[0] - 34)}" y="{f1(tx_[1] - 10)}" width="68" height="12" fill="{t["sky"][1]}" opacity=".88"/>')
    # the tide gauge on the right kerb: the water stands high on it
    tide_gauge(sc, 596, 196, 340, '#D9DCDF', 292)
    x0, y0 = g.pt(-3.4, 7, 0)
    x1, y1 = g.pt(-.4, 7, .9)
    sc.add(f'<rect x="{f1(x0)}" y="{f1(y1)}" width="{f1(x1 - x0)}" height="{f1(y0 - y1)}" rx="3" fill="#D9DCDF"/>')
    sc.add(f'<path d="M{f1(x0 + 8)} {f1((y0 + y1) / 2)}h{f1(x1 - x0 - 22)}m-7 -6l7 6l-7 6" stroke="{TEAL}" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    sc.rain(150, '#E4E8EA', op=.2)
    return sc.finish()


def ev_work_zone():
    sc = Scene('Work zone: metro viaduct works narrow the road; traffic diverted', 'dusk', seed=109)
    t = sc.t
    hy, g = 198, Ground(640, 360, 198, 330, h=2.4)
    sc.sky(hy, sun=(120, hy - 24), sun_r=54)
    sc.clouds(8, 40, 140)
    kol_backdrop(sc, hy, seed=24, lit=.2, landmarks=(('tower', 520, .9),))
    sc.crane(430, hy + 1, 120, mix(t['far'], t['sky'][2], .25), jib=1.1)
    ground_plane(sc, hy)
    sc.road(g, 10)
    sc.viaduct(g, 0, 24, 500, 11, mix(t['far'], t['sky'][2], .2), every=30)
    sc.barrier(g, -2.4, 6, 300, '#3C3A38', h=2.2, stripe='#A9A39C', every=3.0)
    sc.barrier(g, 2.4, 6, 300, '#353331', h=2.2, stripe='#A9A39C', every=3.0)
    d = ''
    for z in (7, 10, 14, 19, 26, 36, 50):
        for X in (-3.4, 3.4):
            x, yb = g.pt(X, z)
            s = g.s(z)
            d += f'M{f1(x - s * .14)} {f1(yb)}L{f1(x - s * .05)} {f1(yb - s * .9)}H{f1(x + s * .05)}L{f1(x + s * .14)} {f1(yb)}Z'
    sc.add(f'<path d="{d}" fill="#EDEBE8"/>')
    for X in (-6.5, 6.5):
        sc.dashes(g, X, t['line'], op=.5)
    sc.ribbon(g, [(5, 3), (5, 30), (5, 300)], TEAL, w=.2)
    sc.streetlights(g, -11, [14, 24, 40, 66, 110])
    sc.streetlights(g, 11, [12, 20, 34, 56, 94])
    sc.car(g, 6.2, 26, kind='taxi', body=taxi_tone(sc))
    sc.car(g, 6.2, 13, kind='car', body='#CFD3D7')
    return sc.finish()


def ev_green_corridor():
    sc = Scene('Ambulance (108) green corridor: an ambulance on a cleared road at night, every signal ahead green', 'night', seed=110)
    t = sc.t
    hy, g = 196, Ground(640, 360, 196, 320, h=2.4)
    sc.sky(hy)
    kol_backdrop(sc, hy, seed=26, lit=.3, landmarks=(('tower', 450, 1.0),))
    ground_plane(sc, hy)
    facades(sc, g, -20, 34, 600, '#18191A', 1, seed=66, floors=t['win'], floor_op=.16)
    facades(sc, g, 20, 30, 600, '#151617', -1, seed=67, floors=t['win'], floor_op=.16)
    sc.road(g, 11)
    for X in (-3.7, 3.7):
        sc.dashes(g, X, '#5C5C5C', op=.5)
    sc.ribbon(g, [(0, 3), (0, 40), (0, 500)], GREEN, w=.24)
    for z in (9, 18, 34, 64, 120):
        sc.signal(g, -11.6, z, GREEN, lit=2)
        sc.signal(g, 11.6, z, GREEN, lit=2)
    sc.streetlights(g, -13.5, [20, 40, 80, 150], pool=False)
    sc.streetlights(g, 13.5, [24, 48, 96], pool=False)
    for z, X, kind in ((16, -8.2, 'taxi'), (26, -8.2, 'car'), (40, 8.2, 'car'), (20, 8.2, 'taxi')):
        sc.car(g, X, z, kind=kind, facing='rear', body=taxi_tone(sc, .55) if kind == 'taxi' else '#2A2B2D', tail='#8D8984', glow=False)
    sc.car(g, 0, 15, kind='van', body='#F2F3F4', beacon='#F4F8FF')
    return sc.finish()


def ev_vehicle_pursuit():
    sc = Scene('Vehicle pursuit: a watchlisted car under a camera gantry on a night flyover, Howrah Bridge lit beyond', 'night', seed=111)
    t = sc.t
    hy, g = 190, Ground(640, 360, 190, 330, h=2.2)
    sc.sky(hy)
    howrah_bridge(sc, 150, 560, hy - 2, 70, '#3A3B3D', lit='#F2E6D0', web=.5)
    kol_backdrop(sc, hy, seed=28, lit=.2, mid=False)
    ground_plane(sc, hy)
    sc.road(g, 12)
    for X in (-4, 0, 4):
        sc.dashes(g, X, '#5C5C5C', op=.5)
    sc.streaks(g, [-6, -9.6], '#F4EEE4', z0=4, z1=500, op=.55)
    sc.barrier(g, -12, 4, 300, '#3A3A3B', h=.8, stripe='#7C7C7C')
    sc.barrier(g, 12, 4, 300, '#3A3A3B', h=.8, stripe='#7C7C7C')
    sc.gantry(g, 62, 12, 6.2, '#232425', depth=.7)
    for X in (-6, -2, 2, 6):
        x, y = g.pt(X, 62, 5.6)
        s = g.s(62)
        sc.add(f'<rect x="{f1(x - s * .3)}" y="{f1(y)}" width="{f1(s * .6)}" height="{f1(s * .35)}" rx="1" fill="#3A3B3D"/><circle cx="{f1(x)}" cy="{f1(y + s * .5)}" r=".9" fill="#F4EEE4"/>')
    z, X = 17, 2.0
    x, yb = g.pt(X, z)
    s = g.s(z)
    sc.add(f'<ellipse cx="{f1(x)}" cy="{f1(yb)}" rx="{f1(s * 2.2)}" ry="{f1(s * .5)}" fill="{RED}" opacity=".28" filter="{sc.svg.blur(4)}"/>')
    sc.car(g, X, z, kind='car', facing='rear', body='#303235', tail=RED)
    sc.brackets(x - s * 1.6, yb - s * 2.1, s * 3.2, s * 2.4, RED, sw=1.8)
    sc.car(g, -2.4, 8.2, kind='suv', facing='rear', body='#E3E5E7', tail='#BDB8B2', beacon='#F4F8FF', glow=False)
    sc.streetlights(g, -14, [16, 30, 56, 100], pool=False)
    sc.streetlights(g, 14, [20, 38, 70], pool=False)
    return sc.finish()


def ev_crime_incident():
    sc = Scene('Watchlisted vehicle: a roadside number-plate camera reads a passing car on an old Kolkata street at night', 'night', seed=112)
    t = sc.t
    hy, g = 200, Ground(640, 360, 200, 270, h=2.6)
    sc.sky(hy)
    kol_backdrop(sc, hy, seed=30, lit=.3, landmarks=(('tower', 120, .9),))
    ground_plane(sc, hy)
    bari_row(sc, g, -9, 10, 160, '#161718', side=1, seed=68, lit=t['win'], hmin=10, hmax=15, lit_frac=.2)
    sc.road(g, 8)
    sc.dashes(g, 0, '#5C5C5C', op=.5)
    sc.streetlights(g, -9.6, [18, 32, 56, 100])
    z, X = 11, 1.3
    x, yb = g.pt(X, z)
    s = g.s(z)
    sc.beam(520, 108, x - s * 1.4, yb - s * .6, x + s * 1.4, yb - s * .2, '#F4EEE4', op=.18)
    sc.car(g, X, z, kind='car', body='#2E3033')
    sc.add(f'<rect x="{f1(x - s * .45)}" y="{f1(yb - s * .62)}" width="{f1(s * .9)}" height="{f1(s * .22)}" rx="1" fill="#CFCFCF"/>'
           f'<rect x="{f1(x - s * .38)}" y="{f1(yb - s * .56)}" width="{f1(s * .76)}" height="{f1(s * .1)}" fill="#7A7A7A"/>')
    sc.brackets(x - s * 1.5, yb - s * 1.9, s * 3, s * 2.1, RED, sw=1.8)
    sc.add(f'<ellipse cx="{f1(x)}" cy="{f1(yb)}" rx="{f1(s * 2)}" ry="{f1(s * .45)}" fill="{RED}" opacity=".22" filter="{sc.svg.blur(4)}"/>')
    sc.add(f'<path d="M600 360V96H520" stroke="#1F2022" stroke-width="7" fill="none"/>'
           f'<rect x="498" y="96" width="44" height="22" rx="4" fill="#2C2D30"/><rect x="494" y="100" width="8" height="14" rx="2" fill="#141516"/>'
           f'<circle cx="536" cy="104" r="2" fill="#F4EEE4"/>')
    sc.glow(498, 107, 10, '#F4EEE4', .35)
    return sc.finish()


def ev_road_accident():
    sc = Scene('Road accident: two cars stopped askew on the bridge approach at night, Vidyasagar Setu lit ahead', 'night', seed=113)
    t = sc.t
    hy, g = 196, Ground(640, 360, 196, 300, h=2.4)
    sc.sky(hy)
    vidyasagar_setu(sc, 40, 600, hy - 3, 92, '#3A3B3D', lit='#F2E6D0')
    kol_backdrop(sc, hy, seed=32, lit=.2, mid=False)
    ground_plane(sc, hy)
    sc.road(g, 11)
    for X in (-3.7, 3.7):
        sc.dashes(g, X, '#5C5C5C', op=.5)
    sc.streaks(g, [-7.4], '#F4EEE4', z0=8, z1=400, op=.4)
    sc.streetlights(g, -13, [16, 30, 56, 100])
    sc.streetlights(g, 13, [20, 38, 70])
    for X, z, rot, facing in ((3.2, 10.5, -12, 'rear'), (5.8, 12.5, 16, 'front')):
        x, yb = g.pt(X, z)
        sc.add(f'<g transform="rotate({rot} {f1(x)} {f1(yb)})">')
        sc.car(g, X, z, kind='car', facing=facing, body='#C3C7CB' if facing == 'front' else '#2B2D30', tail='#A9A49E', glow=facing == 'front')
        sc.add('</g>')
    x, yb = g.pt(1.4, 8.5)
    s = g.s(8.5)
    sc.add(f'<path d="M{f1(x)} {f1(yb - s * .9)}L{f1(x + s * .5)} {f1(yb)}H{f1(x - s * .5)}Z" fill="none" stroke="#F4F4F4" stroke-width="2" stroke-linejoin="round"/>')
    sc.glow(x, yb - s * .4, 10, '#FFFFFF', .25)
    sc.car(g, 5.2, 30, kind='suv', body='#E3E5E7', beacon='#F4F8FF')
    return sc.finish()


def ev_public_disorder():
    sc = Scene('Reported disturbance: a gathering at the Esplanade by the Shaheed Minar, seen from afar', 'dusk', seed=114)
    t = sc.t
    hy, g = 204, Ground(640, 360, 204, 320, h=2.2)
    sc.sky(hy, sun=(450, hy - 40), sun_r=50)
    sc.clouds(8, 40, 130)
    kol_skyline(sc, hy, 34, t['far'], landmarks=(('minar', 330, 150),), lit=True, lit_frac=.15)
    ground_plane(sc, hy)
    bari_row(sc, g, -14, 16, 90, mix(t['mid'], '#000', .15), side=1, seed=43, lit=t['win'], hmin=10, hmax=15, lit_frac=.3)
    bari_row(sc, g, 14, 16, 90, mix(t['mid'], '#000', .25), side=-1, seed=44, lit=t['win'], hmin=10, hmax=15, lit_frac=.3)
    sc.add(f'<ellipse cx="320" cy="{f1(g.y(48))}" rx="300" ry="34" fill="{sc.svg.rad([(0, t["glow"], .55), (1, t["glow"], 0)])}"/>')
    sc.crowd(g, -11, 11, 26, 80, '#0B0B0C', n=240, seed=45, blur=.45)
    sc.add(f'<g fill="{t["haze"]}" opacity=".45" filter="{sc.svg.blur(10)}"><ellipse cx="320" cy="{f1(g.y(40))}" rx="260" ry="22"/></g>')
    for X0 in (-9, -5, -1, 3, 7):
        a, b = g.pt(X0, 11), g.pt(X0 + 3.2, 11)
        _, top = g.pt(X0, 11, 1.1)
        sc.add(f'<rect x="{f1(a[0])}" y="{f1(top)}" width="{f1(b[0] - a[0])}" height="{f1(a[1] - top)}" rx="2" fill="#2C2C2D"/>'
               f'<rect x="{f1(a[0])}" y="{f1(top + (a[1] - top) * .25)}" width="{f1(b[0] - a[0])}" height="{f1((a[1] - top) * .18)}" fill="#D9D9D9"/>')
    return sc.finish()


def ev_reported_crime():
    sc = Scene('Reported crime: a quiet north Kolkata lane at night under one street lamp, cables overhead', 'night', seed=115)
    t = sc.t
    hy, g = 210, Ground(640, 360, 210, 360, h=1.7)
    sc.sky(hy)
    sc.skyline(hy + 1, 4, 12, '#121213', seed=36)
    ground_plane(sc, hy, col='#0D0D0E')
    sc.road(g, 3.4, col='#161617')
    bari_row(sc, g, -3.4, 2.6, 80, '#18181A', side=1, seed=46, lit='#FFF3DF', hmin=9, hmax=13, lit_frac=.06)
    bari_row(sc, g, 3.4, 2.6, 80, '#141415', side=-1, seed=47, lit='#FFF3DF', hmin=9, hmax=13, lit_frac=.05)
    # the overhead cables that criss-cross every old lane
    r = random.Random(8)
    cab = ''
    for _ in range(9):
        za, zb = r.uniform(4, 30), r.uniform(4, 30)
        a, b = g.pt(-3.4, za, r.uniform(5, 8)), g.pt(3.4, zb, r.uniform(5, 8))
        mx_, my_ = (a[0] + b[0]) / 2, max(a[1], b[1]) + r.uniform(4, 16)
        cab += f'M{f1(a[0])} {f1(a[1])}Q{f1(mx_)} {f1(my_)} {f1(b[0])} {f1(b[1])}'
    sc.add(f'<path d="{cab}" stroke="#050505" stroke-width="1" fill="none"/>')
    x, y = g.pt(-3.1, 12, 4.4)
    px, py = g.pt(-1.2, 12)
    sc.beam(x, y, px - 80, py + 10, px + 70, py + 6, '#FFF3DF', op=.24)
    sc.add(f'<ellipse cx="{f1(px)}" cy="{f1(py)}" rx="90" ry="16" fill="#FFF3DF" opacity=".16" filter="{sc.svg.blur(6)}"/>')
    sc.glow(x, y, 12, '#FFF3DF', .7)
    sc.add(f'<rect x="{f1(x - 3)}" y="{f1(y - 2)}" width="6" height="4" rx="1.5" fill="#FFF8EC"/>')
    sx, sy = g.pt(-.8, 14)
    sc.add(f'<g fill="#050505"><circle cx="{f1(sx - 12)}" cy="{f1(sy - 4)}" r="4.5"/><circle cx="{f1(sx + 12)}" cy="{f1(sy - 4)}" r="4.5"/>'
           f'<path d="M{f1(sx - 16)} {f1(sy - 8)}q4 -9 14 -9h6l4 -10h3l-3 12q4 3 4 7z"/></g>')
    fx, fy = g.pt(0, 80, 2.6)
    sc.glow(fx, fy, 30, '#FFF3DF', .5)
    return sc.finish(vign=.85)


def ev_hazard():
    sc = Scene('Hazard: a smoke plume over the docks on the Hooghly', 'storm', seed=116)
    t = sc.t
    hy, g = 214, Ground(640, 360, 214, 300, h=2.4)
    sc.sky(hy)
    r = random.Random(4)
    pl = ''
    for i in range(16):
        k = i / 15
        pl += f'<ellipse cx="{f1(400 - k * 150 + r.uniform(-10, 10))}" cy="{f1(hy - 24 - k * 170)}" rx="{f1(22 + k * 80)}" ry="{f1(14 + k * 30)}"/>'
    sc.add(f'<g fill="#8E9295" opacity=".55" filter="{sc.svg.blur(9)}">{pl}</g>')
    sc.add(f'<g fill="#C9CCCE" opacity=".35" filter="{sc.svg.blur(5)}">{pl[:900]}</g>')
    sc.glow(400, hy - 10, 30, '#F4F6F8', .4)
    c = mix(t['mid'], t['far'], .3)
    port_cranes(sc, (90, 180, 520), hy + 2, 110, c)
    d = ''.join(f'M{x} {hy + 2}V{hy - h}l{w / 2} -6l{w / 2} 6V{hy + 2}Z' for x, w, h in ((230, 70, 18), (330, 90, 22), (440, 60, 16), (590, 80, 14)))
    d += ''.join(f'M{x} {hy + 2}V{hy - 22}a{w / 2} 5 0 0 1 {w} 0V{hy + 2}Z' for x, w in ((300, 30), (334, 26)))
    sc.add(f'<path d="{d}" fill="{c}"/>')
    sc.skyline(hy + 4, 4, 10, t['mid'], seed=38, spires=0)
    ground_plane(sc, hy)
    sc.road(g, 8)
    sc.dashes(g, 0, t['line'], op=.6)
    x, yb = g.pt(-9, 12)
    _, yt = g.pt(-9, 12, 2.8)
    s = g.s(12)
    sc.add(f'<path d="M{f1(x)} {f1(yb)}V{f1(yt)}" stroke="#2A2B2D" stroke-width="2.5"/>'
           f'<path d="M{f1(x)} {f1(yt - s * 1.1)}L{f1(x + s * .62)} {f1(yt)}H{f1(x - s * .62)}Z" fill="#F4F4F4" stroke="#2A2B2D" stroke-width="1.5" stroke-linejoin="round"/>'
           f'<path d="M{f1(x)} {f1(yt - s * .72)}L{f1(x + s * .34)} {f1(yt - s * .1)}H{f1(x - s * .34)}Z" fill="#2A2B2D"/>')
    sc.car(g, 2.2, 30, kind='car', body='#CFD3D7')
    sc.car(g, -2.2, 46, kind='truck', facing='rear', body='#3A3C3E', glow=False)
    return sc.finish(vign=.6)


def ev_infra_failure():
    sc = Scene('Infrastructure failure: a tram junction in a power cut, signals dark, one work light on', 'night', seed=117)
    t = sc.t
    hy, g = 200, Ground(640, 360, 200, 320, h=2.6)
    sc.sky(hy)
    win = sc.windows(lit=.06, seed=13)
    sc.skyline(hy + 1, 8, 30, '#161718', seed=40, wmin=10, wmax=26, win=win, win_op=.5)
    ground_plane(sc, hy)
    sc.road(g, 9)
    cr = [g.pt(-400, 18), g.pt(400, 18), g.pt(400, 26), g.pt(-400, 26)]
    sc.add(f'<polygon points="{pts(cr)}" fill="{t["road"]}"/>')
    tram_lines(sc, g, 0, 3, 400, h=6.8, col='#2E2F31')
    for X, z in ((-9.6, 16), (9.6, 16), (-9.6, 28), (9.6, 28)):
        sc.signal(g, X, z, '#2C2D30', dark='#3A3B3E', lit=None, h=4.6, pole='#3A3B3E')
    x, yb = g.pt(-12, 18)
    s = g.s(18)
    sc.add(f'<path d="M{f1(x)} {f1(yb)}l{f1(s * 2.6)} {f1(-s * 7)}l{f1(s * 1.4)} {f1(s * .5)}" stroke="#2A2B2D" stroke-width="2.4" fill="none"/>')
    wx, wy = g.pt(6, 16, 3.4)
    sc.add(f'<path d="M{f1(wx)} {f1(wy)}L{f1(wx - 9)} {f1(g.y(16))}M{f1(wx)} {f1(wy)}L{f1(wx + 9)} {f1(g.y(16))}M{f1(wx)} {f1(wy)}V{f1(g.y(16))}" stroke="#2A2B2D" stroke-width="1.6"/>')
    sc.beam(wx, wy, wx - 170, g.y(16) + 30, wx + 40, g.y(16) + 40, '#F4F6F8', op=.22)
    sc.glow(wx, wy, 26, '#F4F6F8', .55)
    sc.add(f'<rect x="{f1(wx - 7)}" y="{f1(wy - 5)}" width="14" height="9" rx="2" fill="#F8F9FA"/>')
    for X, z, kind in ((-3.2, 12, 'taxi'), (-3.2, 34, 'car'), (3.2, 46, 'car')):
        sc.car(g, X, z, kind=kind, body=taxi_tone(sc, .55) if kind == 'taxi' else '#BFC3C7')
    return sc.finish(vign=.8)


def ev_weather():
    sc = Scene('Weather warning: a monsoon storm over the Hooghly and Howrah Bridge', 'storm', seed=118)
    t = sc.t
    hy = 196
    sc.sky(hy)
    sc.clouds(18, 0, 150, col='#1A1C1E', op=.85, rx=(90, 220), ry=(18, 40), seed=8)
    bolt = 'M452 30L440 74L452 78L432 128L446 132L424 180'
    sc.add(f'<path d="{bolt}" stroke="#F4F8FF" stroke-width="5" fill="none" opacity=".5" filter="{sc.svg.blur(4)}"/><path d="{bolt}" stroke="#FFFFFF" stroke-width="1.6" fill="none"/>')
    sc.glow(440, 80, 90, '#E8EEF4', .22)
    kol_backdrop(sc, hy, seed=42, lit=.1, mid=False)
    sc.river(hy + 2, 360)
    howrah_bridge(sc, -60, 700, hy + 30, 120, '#4A4E52', web=.6, piers_to=hy + 46)
    sc.add(f'<path d="M424 {hy + 30}L436 {hy + 70}L428 {hy + 74}L440 {hy + 130}" stroke="#FFFFFF" stroke-opacity=".3" stroke-width="2" fill="none" filter="{sc.svg.blur(2)}"/>')
    country_boat(sc, 160, 292, 90, '#141516')
    sc.add(f'<rect y="318" width="640" height="42" fill="#121314"/><rect y="316" width="640" height="3" fill="#2C2F32"/>')
    d = ''.join(f'M{x} 318V262h10' for x in (40, 200, 360, 520))
    sc.add(f'<path d="{d}" stroke="#2A2C2E" stroke-width="2.4" fill="none"/>' + ''.join(f'<circle cx="{x + 10}" cy="264" r="2.2" fill="#F4F6F8"/>' for x in (40, 200, 360, 520)))
    for x in (50, 210, 370, 530):
        sc.reflection(x, 270, 44, '#F4F6F8', w=3, op=.25)
    sc.rain(320, '#DDE2E5', op=.2, seed=19)
    return sc.finish(vign=.7)


def ev_advisory():
    sc = Scene('Advisory: an overhead message sign on the evening approach to Vidyasagar Setu', 'dusk', seed=119)
    t = sc.t
    hy, g = 200, Ground(640, 360, 200, 330, h=2.4)
    sc.sky(hy, sun=(200, hy - 20), sun_r=56)
    sc.clouds(9, 40, 140)
    vidyasagar_setu(sc, -20, 660, hy - 2, 132, mix(t['near'], t['mid'], .35), lit=t['lamp'])
    kol_backdrop(sc, hy, seed=44, lit=.25, mid=False)
    ground_plane(sc, hy)
    sc.road(g, 10)
    for X in (-3.4, 3.4):
        sc.dashes(g, X, t['line'], op=.5)
    sc.streaks(g, [-6.8, 6.8], '#F4EEE4', z0=6, z1=400, op=.35)
    sc.streetlights(g, -12, [14, 26, 46, 80, 140])
    sc.streetlights(g, 12, [18, 32, 58, 100])
    z = 14
    sc.gantry(g, z, 10.4, 6.6, '#1E1F20', depth=.5)
    x0, y0 = g.pt(-6, z, 6.4)
    x1, y1 = g.pt(6, z, 3.8)
    sc.add(f'<rect x="{f1(x0)}" y="{f1(y0)}" width="{f1(x1 - x0)}" height="{f1(y1 - y0)}" rx="3" fill="#0B0B0C" stroke="#3A3B3D" stroke-width="1.5"/>')
    bars = ''
    for k, frac in enumerate((.82, .64, .74)):
        yy = y0 + (y1 - y0) * (.25 + k * .25)
        bars += f'M{f1(x0 + 12)} {f1(yy)}H{f1(x0 + 12 + (x1 - x0 - 24) * frac)}'
    sc.add(f'<path d="{bars}" stroke="#FFF6E8" stroke-width="4" stroke-dasharray="2.2 1.6" opacity=".9"/>'
           f'<path d="{bars}" stroke="#FFF6E8" stroke-width="7" opacity=".25" filter="{sc.svg.blur(3)}"/>')
    for X, z_, kind in ((-1.8, 40, 'taxi'), (1.8, 52, 'car'), (-5, 70, 'taxi')):
        sc.car(g, X, z_, kind=kind, body=taxi_tone(sc) if kind == 'taxi' else '#C8CCD0')
    return sc.finish()


def ev_cyclone():
    sc = Scene('Cyclone: a tree felled across the road after the storm; traffic led round it', 'storm', seed=120)
    t = sc.t
    hy, g = 200, Ground(640, 360, 200, 320, h=2.2)
    sc.sky(hy)
    sc.clouds(16, 10, 160, col='#2F3336', op=.8, rx=(90, 220), ry=(16, 36), seed=9)
    kol_backdrop(sc, hy, seed=46, lit=.08, mid=False)
    ground_plane(sc, hy)
    bari_row(sc, g, -11, 14, 160, t['mid'], side=1, seed=48, lit=t['win'], hmin=10, hmax=15, lit_frac=.08)
    sc.road(g, 9)
    sc.dashes(g, 0, t['line'], op=.5)
    # wet road sheen
    sc.add(f'<polygon points="{pts([g.pt(-9, 3), g.pt(-9, 600), g.pt(9, 600), g.pt(9, 3)])}" fill="{t["sky"][2]}" opacity=".12"/>')
    fallen_tree(sc, g, -9, 3.2, 10, '#5A554E', '#47504B', seed=12, light='#D8D2C8')
    sc.glow(*g.pt(-6.5, 9, 2.2), 26, '#F4F8FF', .28)
    d = ''
    for z, X in ((7.5, 3.6), (8.6, 5.2), (9.8, 6.6), (11.2, 7.6)):
        x, yb = g.pt(X, z)
        s = g.s(z)
        d += f'M{f1(x - s * .14)} {f1(yb)}L{f1(x - s * .05)} {f1(yb - s * .7)}H{f1(x + s * .05)}L{f1(x + s * .14)} {f1(yb)}Z'
    sc.add(f'<path d="{d}" fill="#EDEBE8"/>')
    sc.ribbon(g, [(-2, 3), (4, 6.5), (7.4, 10), (7.4, 15), (3, 24), (0, 200)], TEAL, w=.2)
    sc.streetlights(g, 10.5, [14, 26, 46, 80], pool=False)
    sc.rain(260, '#DDE2E5', op=.18, seed=29, ang=-.36)
    return sc.finish(vign=.7)


def ev_station_surge():
    sc = Scene('Station surge: Howrah Station across the river at dusk, its forecourt full, ferries at the jetty', 'dusk', seed=121)
    t = sc.t
    hy = 206
    sc.sky(hy, sun=(140, hy - 40), sun_r=60)
    sc.clouds(9, 40, 140)
    kol_skyline(sc, hy - 4, 50, t['far'], lit=True, lit_frac=.15)
    howrah_station(sc, 300, hy + 2, 470, mix(t['mid'], t['far'], .15), lit=t['win'])
    howrah_bridge(sc, 470, 1100, hy - 6, 96, mix(t['mid'], t['far'], .35), web=.45, lit=t['lamp'])
    # the forecourt: a band of crowd as one mass, lit from above
    sc.add(f'<rect y="{hy + 2}" width="640" height="10" fill="{mix(t["ground"], t["haze"], .25)}"/>')
    r = random.Random(7)
    d = ''.join(f'M{f1(x)} {hy + 11}v{f1(-r.uniform(3, 5.5))}a1.6 1.8 0 0 1 3.2 0v{f1(r.uniform(3, 5.5))}z' for x in (r.uniform(80, 530) for _ in range(260)))
    sc.add(f'<path d="{d}" fill="{t["near"]}" filter="{sc.svg.blur(.3)}"/>')
    sc.river(hy + 12, 360)
    for x in (120, 300, 470):
        sc.reflection(x, hy + 16, 70, t['win'], w=6, op=.3)
    ferry_launch(sc, 420, 268, 140, '#1B1C1D', lit=t['win'])
    ferry_launch(sc, 160, 248, 90, '#262728', lit=t['win'])
    # the teal flow: the ferry route across to the city side
    sc.add(f'<path d="M80 340Q260 290 400 278" stroke="{TEAL}" stroke-width="3" fill="none" stroke-dasharray="1 9" stroke-linecap="round"/>')
    sc.add(f'<rect y="336" width="640" height="24" fill="{t["near"]}"/>')
    return sc.finish(vign=.55)


def ev_ghat_transit():
    sc = Scene('Ghat transit: Babughat at dawn, its colonnade over the steps, boats waiting on the Hooghly', 'dawn', seed=122)
    t = sc.t
    hy = 196
    sc.sky(hy, sun=(520, hy - 30), sun_r=70)
    sc.clouds(8, 30, 140, op=.3)
    vidyasagar_setu(sc, 300, 760, hy - 2, 60, mix(t['far'], t['sky'][2], .3), op=.9)
    sc.add(f'<rect y="{hy}" width="640" height="{360 - hy}" fill="{t["haze"]}" opacity=".2"/>')
    sc.river(hy + 2, 360)
    sc.reflection(520, hy + 4, 120, t['sun'], w=12, op=.45)
    # the near bank on the left: the pavilion over the ghat steps
    bank = mix(t['near'], '#000', .2)
    sc.add(f'<path d="M0 214H300L330 236V360H0Z" fill="{bank}"/>')
    sc.trees(-20, 120, 214, 30, 60, mix(t['near'], t['mid'], .4), seed=21)
    colonnade(sc, 190, 214, 170, 92, mix(t['mid'], WHITE, .28), n=8, light=t['sun'])
    ghat_steps(sc, 60, 330, 236, 300, mix(t['near'], t['mid'], .45), n=8)
    r = random.Random(3)
    d = ''.join(f'M{f1(x)} 236v{f1(-r.uniform(4, 6))}a1.7 2 0 0 1 3.4 0v{f1(r.uniform(4, 6))}z' for x in (r.uniform(110, 300) for _ in range(90)))
    sc.add(f'<path d="{d}" fill="{t["near"]}" opacity=".85" filter="{sc.svg.blur(.35)}"/>')
    sc.add(f'<path d="M300 300Q420 280 600 240" stroke="{TEAL}" stroke-width="3" fill="none" stroke-dasharray="1 9" stroke-linecap="round"/>')
    country_boat(sc, 430, 318, 120, '#2A2928')
    country_boat(sc, 560, 282, 84, '#3A3836', flip=True)
    ferry_launch(sc, 380, 258, 110, '#3F3E3C')
    return sc.finish(vign=.5)


EVENTS = {
    'protected_movement': ev_protected_movement,
    'procession': ev_procession,
    'mass_gathering': ev_mass_gathering,
    'race': ev_race,
    'ceremonial': ev_ceremonial,
    'egress_surge': ev_egress_surge,
    'emergency_evacuation': ev_emergency_evacuation,
    'flooding': ev_flooding,
    'work_zone': ev_work_zone,
    'green_corridor': ev_green_corridor,
    'vehicle_pursuit': ev_vehicle_pursuit,
    'crime_incident': ev_crime_incident,
    'road_accident': ev_road_accident,
    'public_disorder': ev_public_disorder,
    'reported_crime': ev_reported_crime,
    'hazard': ev_hazard,
    'infra_failure': ev_infra_failure,
    'weather': ev_weather,
    'advisory': ev_advisory,
    'cyclone': ev_cyclone,
    'station_surge': ev_station_surge,
    'ghat_transit': ev_ghat_transit,
}


# ── city scenes for the Home greeting (960 x 320): the Hooghly, Howrah Bridge across it, the city on the far bank ─
def panorama(tod, label, seed, green=False, lights=False, boats=True):
    W, H = 960, 320
    sc = Scene(label, tod, W=W, H=H, seed=seed)
    t, sv = sc.t, sc.svg
    hy = 206
    night = tod in ('night', 'dusk')
    sun = {'dawn': (720, hy - 40), 'day': (240, 64), 'dusk': (300, hy - 30)}.get(tod)
    sc.sky(hy, sun=sun, sun_r=76 if tod != 'day' else 46)
    if tod == 'night':
        sc.add(f'<circle cx="790" cy="58" r="10" fill="#F2EEE8"/><circle cx="790" cy="58" r="46" fill="#F2EEE8" opacity=".14" filter="{sv.blur(14)}"/>')
    sc.clouds(12, 24, 140, op=.3 if tod != 'day' else .55, col=WHITE if tod == 'day' else None, rx=(70, 190))
    start = len(sv.body)
    far = mix(t['far'], t['sky'][2], .3)
    win = sc.windows(lit=.4 if night else .5, seed=15, col=t['win'] if night else scale(t['mid'], .62))
    # the far bank: Vidyasagar Setu far downstream (right), the city, the Victoria Memorial, the Shaheed Minar
    vidyasagar_setu(sc, 600, 1100, hy - 2, 74, mix(far, t['sky'][2], .2), lit=t['lamp'] if lights else None)
    sc.skyline(hy, 5, 18, far, seed=seed, wmin=7, wmax=18, spires=.05)
    victoria_memorial(sc, 790, hy + 1, .9, mix(t['far'], t['mid'], .3), win=t['win'] if night else None)
    shaheed_minar(sc, 905, hy + 1, 100, mix(t['far'], t['mid'], .3))
    tall_tower(sc, 688, hy + 1, 10, 116, mix(t['far'], t['mid'], .35), lit=t['win'] if night else None)
    sc.haze(hy, 22, .45)
    sc.skyline(hy, 8, 30, t['mid'], x0=420, x1=980, seed=seed + 1, wmin=12, wmax=26, win=win, win_op=.5 if night else .3, spires=.05, gap=.3)
    sc.skyline(hy, 6, 20, mix(t['mid'], t['far'], .4), x0=-10, x1=430, seed=seed + 2, wmin=10, wmax=24, win=win, win_op=.3, spires=0)
    sc.add(f'<rect y="{hy - 1}" width="{W}" height="5" fill="{mix(t["ground"], t["haze"], .3)}"/>')
    sc.trees(0, W, hy - 1, 6, 11, mix(t['near'], t['mid'], .5), seed=seed + 7, n=40)
    lamps = ''.join(f'<circle cx="{x}" cy="{hy - 7}" r="1.1"/>' for x in range(14, W, 38))
    sc.add(f'<g fill="{t["lamp"] if night else mix(t["mid"], WHITE, .5)}">{lamps}</g>')
    if green:
        sc.add(''.join(f'<circle cx="{x}" cy="{hy - 9}" r="1.8" fill="{GREEN}"/><circle cx="{x}" cy="{hy - 9}" r="6" fill="{GREEN}" opacity=".35" filter="{sv.blur(2.5)}"/>' for x in (96, 402, 708)))
    city = ''.join(sv.body[start:])
    del sv.body[start:]
    sv.add(f'<g id="city">{city}</g>')
    sc.add(f'<rect y="{hy + 3}" width="{W}" height="{H - hy}" fill="{sv.lin([(0, mix(t["sky"][2], "#000", .25)), (.5, mix(t["sky"][1], "#000", .45)), (1, mix(t["sky"][0], "#000", .55))])}"/>')
    sc.add(f'<use href="#city" transform="matrix(1 0 0 -.62 0 {f1(hy * 1.62 + 6)})" opacity=".3" filter="{sv.blur(1.6)}"/>')
    r = random.Random(seed + 3)
    d = ''.join(f'M{f1(r.uniform(-10, W))} {f1(hy + 6 + (H - hy) * r.random() ** 1.4)}h{f1(r.uniform(8, 46))}' for _ in range(120))
    sc.add(f'<path d="{d}" stroke="{mix(t["sky"][2], WHITE, .35)}" stroke-opacity=".22" stroke-width=".8"/>')
    if sun and tod != 'day':
        sc.reflection(sun[0], hy + 6, 100, t['sun'], w=14, op=.42)
    # Howrah Bridge across the river: the anchor arm, the towers, the long cantilevers, the suspended span
    bc = mix(t['near'], t['mid'], .45) if tod != 'night' else '#3F4042'
    howrah_bridge(sc, -170, 700, hy + 40, 150, bc, lit=t['lamp'] if lights else None, web=.55, piers_to=hy + 64, detail=.78)
    if lights:
        for x in (-12, 120, 250, 380, 520, 640):
            sc.reflection(x, hy + 66, 46, t['lamp'], w=5, op=.3)
    if boats:
        country_boat(sc, 700, H - 40, 110, t['near'])
        country_boat(sc, 860, H - 66, 70, mix(t['near'], t['mid'], .4), flip=True)
    sc.add(f'<rect y="{H - 18}" width="{W}" height="18" fill="{t["near"]}"/>'
           f'<path d="M0 {H - 30}H{W}M0 {H - 24}H{W}" stroke="{t["near"]}" stroke-width="1.6"/>'
           + f'<path d="' + ''.join(f'M{x} {H - 18}V{H - 30}' for x in range(6, W, 22)) + f'" stroke="{t["near"]}" stroke-width="1.4"/>')
    for x in (90, 520, 900):
        sc.add(f'<path d="M{x} {H - 18}V{H - 108}q0 -8 9 -8h8" stroke="{t["near"]}" stroke-width="3" fill="none"/>'
               f'<rect x="{x + 13}" y="{H - 118}" width="12" height="4" rx="2" fill="{t["lamp"] if night else t["near"]}"/>')
        if night:
            sc.glow(x + 19, H - 114, 16, t['lamp'], .45)
            sc.reflection(x + 19, H - 60, 30, t['lamp'], w=4, op=.25)
    return sc.finish(vign=.5)


SCENES = {
    'dawn': lambda: panorama('dawn', 'Kolkata at dawn: Howrah Bridge across the Hooghly, the city waking on the far bank', 201),
    'day': lambda: panorama('day', 'Kolkata by day: the Hooghly under a bright sky, Howrah Bridge and the Victoria Memorial', 202),
    'dusk': lambda: panorama('dusk', 'Kolkata at dusk: Howrah Bridge and Vidyasagar Setu, the first lights on the river', 203, lights=True),
    'night': lambda: panorama('night', 'Kolkata at night: Howrah Bridge lit over the Hooghly, the city glowing beyond', 204, lights=True),
    'all-clear': lambda: panorama('dawn', 'All clear: a calm morning on the Hooghly, the riverfront signals green', 205, green=True),
}


# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
#  OUTPUT
# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
def write(sub, name, text):
    d = os.path.join(OUT, sub)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f'{name}.svg'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)


def main():
    for name in VEHICLES:
        write('vehicles', name, build_vehicle(name))
    for name in CONVOYS:
        write('vehicles', name, build_convoy(name))
    for name, fn in EVENTS.items():
        write('events', name, fn())
    for name, fn in SCENES.items():
        write('scenes', name, fn())


if __name__ == '__main__':
    if len(sys.argv) > 1:
        OUT = os.path.abspath(sys.argv[1])
    main()
