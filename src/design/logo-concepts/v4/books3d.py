"""A stack of three books seen in 3/4 from above, drawn for one ink colour.
Each book: cover on top (ink), long front face (spine or pages), short right face (pages).
Faces are separated by thin cuts; pages are cut out with ink page lines; books above cut a gap out of
the books below. Everything is built with masks, so it sits on any paper colour."""
import math, random
from stamp import wobble_fn

def jag(points, seed, amp=.22, step=1.2):
    """Closed polygon traced by hand: edges subdivided with a little sideways wobble."""
    wf = wobble_fn(seed, amp)
    out, s = [], 0.0
    n = len(points)
    for i in range(n):
        (x0, y0), (x1, y1) = points[i], points[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0); k = max(1, int(L / step))
        nx, ny = -(y1 - y0) / (L or 1), (x1 - x0) / (L or 1)
        for j in range(k):
            t = j / k; o = wf(s / 9.0)
            out.append((x0 + (x1 - x0) * t + nx * o, y0 + (y1 - y0) * t + ny * o)); s += L / k
    return "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in out) + " Z"

def line(p, q, seed, amp=.18):
    """An open hand-drawn line as a polyline (for strokes)."""
    wf = wobble_fn(seed, amp)
    L = math.hypot(q[0] - p[0], q[1] - p[1]); k = max(2, int(L / 1.2))
    nx, ny = -(q[1] - p[1]) / L, (q[0] - p[0]) / L
    pts = [(p[0] + (q[0] - p[0]) * j / k + nx * wf(j / 3), p[1] + (q[1] - p[1]) * j / k + ny * wf(j / 3)) for j in range(k + 1)]
    return "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts)

class Book:
    def __init__(self, x, y, W, H, ox, oy, rot, front, seed, label=False):
        """(x, y) = bottom-left corner of the front face. front: 'spine' or 'pages'."""
        self.x, self.y, self.W, self.H, self.ox, self.oy = x, y, W, H, ox, oy
        self.rot, self.front, self.seed, self.label = rot, front, seed, label
        self.cx, self.cy = x + (W + ox) / 2, y - (H + oy) / 2

    def P(self, u, v):
        """Point on the book: u along the width (0..W), v up (0 = bottom front edge); plus depth helpers."""
        return (self.x + u, self.y - v)

    def tf(self):
        return f'rotate({self.rot} {self.cx:.2f} {self.cy:.2f})'

    def silhouette(self):
        x, y, W, H, ox, oy = self.x, self.y, self.W, self.H, self.ox, self.oy
        return jag([(x, y), (x, y - H), (x + ox, y - H - oy), (x + W + ox, y - H - oy),
                    (x + W + ox, y - oy), (x + W, y)], self.seed)

    def cuts(self):
        """Mask content: black = cut away, white = ink back inside a cut."""
        x, y, W, H, ox, oy = self.x, self.y, self.W, self.H, self.ox, self.oy
        c = 1.7  # cover-board thickness seen on the page faces
        out = []
        B = lambda d: f'<path d="{d}" fill="#000"/>'
        Wl = lambda d, w=1.1: f'<path d="{d}" fill="none" stroke="#fff" stroke-width="{w}" stroke-linecap="round"/>'
        Bl = lambda d, w=1.1: f'<path d="{d}" fill="none" stroke="#000" stroke-width="{w}" stroke-linecap="round"/>'
        # edges between the faces
        out.append(Bl(line((x + .8, y - H), (x + W, y - H), self.seed + 1), 1.0))
        out.append(Bl(line((x + W, y - H), (x + W, y - .8), self.seed + 2), 1.0))
        # right face: the head of the page block
        rf = [(x + W + .9, y - H + .2 - c * .3), (x + W + ox - .2, y - H - oy + c + .6),
              (x + W + ox - .2, y - oy - c + .2), (x + W + .9, y - c)]
        out.append(B(jag(rf, self.seed + 3, .12)))
        mid = lambda f: ((x + W + .9) * (1 - f) + (x + W + ox - .2) * f)
        for k in (1, 2):
            t = k / 3
            out.append(Wl(line((x + W + 1.2, y - c - (H - 2 * c) * t), (x + W + ox - .5, y - oy - c - (H - 2 * c) * t),
                               self.seed + 4 + k), .7))
        if self.front == "pages":
            pf = [(x + 1.2, y - c), (x + 1.2, y - H + c), (x + W - .9, y - H + c), (x + W - .9, y - c)]
            out.append(B(jag(pf, self.seed + 7, .12)))
            for k in (1, 2):
                v = c + (H - 2 * c) * k / 3
                out.append(Wl(line((x + 2.4, y - v), (x + W - 2.2, y - v), self.seed + 8 + k), .7))
        else:  # spine: two bands near the ends and a title line
            for bx in (x + 4.2, x + W - 5.8):
                out.append(Bl(line((bx, y - 1.8), (bx, y - H + 1.8), self.seed + int(bx)), 1.3))
                out.append(Bl(line((bx + 1.7, y - 1.8), (bx + 1.7, y - H + 1.8), self.seed + int(bx) + 1), 1.3))
            out.append(Bl(line((x + W * .3, y - H / 2), (x + W * .62, y - H / 2), self.seed + 12), 1.5))
        if self.label:  # a title label on the cover
            lx, ly = x + W * .3, y - H - oy * .25
            lab = [(lx, ly), (lx + oy * .7 * ox / oy, ly - oy * .5), (lx + W * .42 + ox * .5, ly - oy * .5), (lx + W * .42, ly)]
            out.append(B(jag(lab, self.seed + 13, .1)))
        return "".join(out)

def stack(ink, uid):
    """The three books (bottom, middle, top) as SVG, with their masks."""
    books = [
        Book(38.5, 76, 38, 8.2, 6, 9.5, 1.2, "pages", 71),
        Book(40.5, 67.8, 34, 7.8, 6, 9.5, -3.2, "spine", 72),
        Book(43.5, 60, 30, 7.4, 6, 9.5, 2.6, "pages", 73, label=True),
    ]
    defs, body = [], []
    for i, b in enumerate(books):
        above = "".join(f'<path d="{u.silhouette()}" transform="{u.tf()}" fill="#000" stroke="#000" '
                        f'stroke-width="2.6" stroke-linejoin="round"/>' for u in books[i + 1:])
        defs.append(f'<mask id="{uid}{i}" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">'
                    f'<rect width="120" height="120" fill="#fff"/><g transform="{b.tf()}">{b.cuts()}</g>{above}</mask>')
        body.append(f'<g mask="url(#{uid}{i})"><path d="{b.silhouette()}" transform="{b.tf()}" fill="{ink}" '
                    f'stroke="{ink}" stroke-width=".8" stroke-linejoin="round"/></g>')
    return "<defs>" + "".join(defs) + "</defs>" + "".join(body)
