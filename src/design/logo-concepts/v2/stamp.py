"""Direction 1: a hand-cut rubber stamp of approval. Wobbly geometry is baked into the paths; an SVG
filter adds the rough edge and the uneven ink."""
import math, os, random
import textlib as T

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2")
os.makedirs(OUT, exist_ok=True)

SHAN = lambda w=700, b=0, i=0: T.font("shantell", wght=w, INFM=i, BNCE=b, SPAC=0)
FRAU = lambda: T.font("fraunces", wght=800, opsz=12, SOFT=100, WONK=0)

def wobble_fn(seed, amp):
    rnd = random.Random(seed)
    terms = [(k, amp * rnd.uniform(.3, 1) / (k ** .6), rnd.uniform(0, 6.3)) for k in range(2, 9)]
    return lambda t: sum(a * math.sin(k * t + p) for k, a, p in terms)

def blob(cx, cy, r, seed, amp=.8, n=160, ry=None):
    """A hand-drawn circle (closed path)."""
    w = wobble_fn(seed, amp); ry = ry or r
    pts = [(cx + (r + w(t)) * math.cos(t), cy + (ry + w(t)) * math.sin(t))
           for t in (2 * math.pi * i / n for i in range(n))]
    return "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + " Z"

def ring(cx, cy, r, width, seed, amp=.8):
    """A ring whose stroke width varies like a hand-cut line."""
    return blob(cx, cy, r + width / 2, seed, amp) + " " + blob(cx, cy, r - width / 2, seed + 50, amp)

def wobbly_rrect(x, y, w, h, rad, seed, amp=.6, n=220):
    """Rounded rectangle traced by hand."""
    wf = wobble_fn(seed, amp)
    pts = []
    # walk the perimeter parametrically
    straight = [(w - 2 * rad), (h - 2 * rad)]
    per = 2 * sum(straight) + 2 * math.pi * rad
    for i in range(n):
        d = per * i / n; t = 2 * math.pi * i / n
        segs = [("h", straight[0], (x + rad, y), 0), ("c", math.pi / 2 * rad, (x + w - rad, y + rad), -math.pi / 2),
                ("v", straight[1], (x + w, y + rad), 0), ("c", math.pi / 2 * rad, (x + w - rad, y + h - rad), 0),
                ("h-", straight[0], (x + w - rad, y + h), 0), ("c", math.pi / 2 * rad, (x + rad, y + h - rad), math.pi / 2),
                ("v-", straight[1], (x, y + h - rad), 0), ("c", math.pi / 2 * rad, (x + rad, y + rad), math.pi)]
        for kind, L, (ax, ay), a0 in segs:
            if d <= L:
                if kind == "h": px, py, nx, ny = ax + d, ay, 0, -1
                elif kind == "h-": px, py, nx, ny = ax - d, ay, 0, 1
                elif kind == "v": px, py, nx, ny = ax, ay + d, 1, 0
                elif kind == "v-": px, py, nx, ny = ax, ay - d, -1, 0
                else:
                    a = a0 + d / rad; px, py = ax + rad * math.cos(a), ay + rad * math.sin(a)
                    nx, ny = math.cos(a), math.sin(a)
                o = wf(t); pts.append((px + nx * o, py + ny * o)); break
            d -= L
    return "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + " Z"

def brush(points, w0, w1, seed=3, n=60):
    """A brush stroke along a Catmull-Rom spline through points, tapering from w0 to w1 with a fat middle."""
    rnd = random.Random(seed)
    def cr(p0, p1, p2, p3, t):
        return tuple(.5 * ((2 * p1[i]) + (-p0[i] + p2[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t * t
                           + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t ** 3) for i in range(2))
    P = [points[0]] + points + [points[-1]]
    line = []
    for s in range(1, len(P) - 2):
        for j in range(n):
            line.append(cr(P[s - 1], P[s], P[s + 1], P[s + 2], j / n))
    line.append(points[-1])
    L, R = [], []
    for i, (x, y) in enumerate(line):
        a, b = line[max(i - 1, 0)], line[min(i + 1, len(line) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; m = math.hypot(dx, dy) or 1
        f = i / (len(line) - 1)
        wdt = (w0 + (w1 - w0) * f) * (.55 + .45 * math.sin(math.pi * min(1, f * 1.15))) + rnd.uniform(-.15, .15)
        L.append((x - dy / m * wdt / 2, y + dx / m * wdt / 2)); R.append((x + dy / m * wdt / 2, y - dx / m * wdt / 2))
    pts = L + R[::-1]
    return "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + " Z"

def star(cx, cy, r, seed, rot=0):
    rnd = random.Random(seed); pts = []
    for i in range(10):
        a = rot - math.pi / 2 + i * math.pi / 5
        rr = (r if i % 2 == 0 else r * .45) * rnd.uniform(.9, 1.08)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + " Z"

def heart(cx, cy, s, seed):
    rnd = random.Random(seed); j = lambda: rnd.uniform(-.4, .4)
    return (f"M{cx} {cy+s*.9+j()} C{cx-s*.3} {cy+s*.6} {cx-s*1.05+j()} {cy+s*.15} {cx-s*1.0} {cy-s*.35+j()} "
            f"C{cx-s*.95} {cy-s*.95} {cx-s*.2+j()} {cy-s*1.0} {cx+j()*.3} {cy-s*.42} "
            f"C{cx+s*.25} {cy-s*1.02+j()} {cx+s*1.0} {cy-s*.9} {cx+s*1.02+j()} {cy-s*.32} "
            f"C{cx+s*1.05} {cy+s*.2} {cx+s*.3+j()} {cy+s*.6} {cx} {cy+s*.9} Z")

def ink_filter(fid, seed=4, rough=1.6, grain=1.0):
    """Rough edges (displacement) and uneven ink (two noise masks multiplied)."""
    return f'''<filter id="{fid}" x="-8%" y="-8%" width="116%" height="116%" color-interpolation-filters="sRGB">
<feTurbulence type="fractalNoise" baseFrequency=".09" numOctaves="2" seed="{seed}" result="w"/>
<feDisplacementMap in="SourceGraphic" in2="w" scale="{rough}" xChannelSelector="R" yChannelSelector="G" result="r"/>
<feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="2" seed="{seed+3}" result="g"/>
<feColorMatrix in="g" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 {5.5*grain:.2f} 0 0 0 {-1.25*grain+ (1-grain)*1:.2f}" result="ga"/>
<feTurbulence type="fractalNoise" baseFrequency=".022" numOctaves="3" seed="{seed+9}" result="b"/>
<feColorMatrix in="b" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 {2.6*grain:.2f} 0 0 0 {-.22*grain+(1-grain)*1:.2f}" result="ba"/>
<feComposite in="ga" in2="ba" operator="arithmetic" k1="1" result="m"/>
<feComposite in="r" in2="m" operator="in"/>
</filter>'''

def wrap(inner, fid, ink, vb, tilt=0, cx=60, cy=60, seed=4, grain=1.0, title="Doelenboek"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="{title}"><title>{title}</title>'
            f'<defs>{ink_filter(fid, seed, grain=grain)}</defs>'
            f'<g filter="url(#{fid})" fill="{ink}" fill-rule="evenodd" transform="rotate({tilt} {cx} {cy})">{inner}</g></svg>')

CHECK = [(38, 62), (52, 77), (84, 40)]

def s1_seal(ink, fid, grain=1.0):
    """Round seal: DOELENBOEK over the top, GOED GEDAAN under it, a brush tick in the middle."""
    top = T.arc("DOELENBOEK", 60, 60, 41.5, 12.5, SHAN(800), top=True, tracking=.07, jitter=1, seed=2)
    bot = T.arc("GOED GEDAAN", 60, 60, 49.5, 9.5, SHAN(750), top=False, tracking=.14, jitter=1, seed=5)
    inner = (f'<path d="{ring(60, 60, 55.5, 3.2, 11, .9)}"/>'
             f'<path d="{ring(60, 60, 36, 1.8, 17, .7)}"/>'
             f'<path d="{top}"/><path d="{bot}"/>'
             f'<path d="{star(14.5, 66, 3.2, 1, .2)}"/><path d="{star(105.5, 66, 3.2, 2, -.2)}"/>'
             f'<path d="{brush([(42, 60), (53, 73), (80, 43)], 9, 5.5, 9)}"/>')
    return wrap(inner, fid, ink, "0 0 120 120", tilt=-8, grain=grain)

def s2_label(ink, fid, grain=1.0):
    """Rectangular approval stamp: the name big, GOEDGEKEURD under it, a tick at the front."""
    name, w = T.text("Doelenboek", 0, 0, 30, SHAN(800, b=40), anchor="start", jitter=.6, seed=8)
    sub, w2 = T.text("GOEDGEKEURD", 0, 0, 10, SHAN(700), anchor="start", tracking=.32, jitter=.8, seed=3)
    W = 54 + w + 14; H = 68
    inner = (f'<path d="{wobbly_rrect(4, 4, W - 8, H - 8, 9, 21, .7)} {wobbly_rrect(7.8, 7.8, W - 15.6, H - 15.6, 6, 22, .6)}"/>'
             f'<path d="{wobbly_rrect(11.5, 11.5, W - 23, H - 23, 4, 23, .5)} {wobbly_rrect(12.9, 12.9, W - 25.8, H - 25.8, 3, 24, .5)}"/>'
             f'<path d="{brush([(19, 33), (28, 45), (47, 21)], 8, 5, 4)}"/>'
             f'<path transform="translate(54 41)" d="{name}"/>'
             f'<path transform="translate({54 + (w - w2) / 2:.1f} 54)" d="{sub}"/>')
    return wrap(inner, fid, ink, f"-6 -10 {W + 12:.1f} {H + 20}", tilt=-4, cx=W / 2, cy=H / 2, grain=grain)

def scallop(cx, cy, r, bumps, depth, seed, n=360):
    wf = wobble_fn(seed, .5)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        rr = r - depth * (1 - abs(math.cos(bumps * t / 2))) + wf(t)
        pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t)))
    return "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + " Z"

def s3_flower(ink, fid, grain=1.0):
    """Teacher-style scalloped stamp: a heart with a tick in it, the name around the top."""
    top = T.arc("Doelenboek", 60, 60, 37, 13, SHAN(800, b=60), top=True, tracking=.04, jitter=.8, seed=6)
    bot = T.arc("goed zo!", 60, 60, 44.5, 10, SHAN(700, b=80, i=100), top=False, tracking=.08, jitter=.8, seed=12)
    h = heart(60, 66, 17, 4)
    inner = (f'<path d="{scallop(60, 60, 58, 16, 4.5, 31)} {scallop(60, 60, 54.5, 16, 4, 32)}"/>'
             f'<path d="{top}"/><path d="{bot}"/>'
             f'<path d="{h} {brush([(49, 63), (57, 72), (73, 54)], 6.5, 4.2, 6)}"/>')
    return wrap(inner, fid, ink, "0 0 120 120", tilt=6, grain=grain)

BROWN, RED, CREAM = "#725C4E", "#B5462F", "#F4F0E4"
designs = {"s1-seal": s1_seal, "s2-label": s2_label, "s3-flower": s3_flower}
for k, fn in designs.items():
    open(f"{OUT}/{k}.svg", "w").write(fn(BROWN, k + "-i"))
    open(f"{OUT}/{k}-red.svg", "w").write(fn(RED, k + "-r"))
    open(f"{OUT}/{k}-cream.svg", "w").write(fn(CREAM, k + "-c"))
    open(f"{OUT}/{k}-clean.svg", "w").write(fn(BROWN, k + "-n", grain=0))
print("stamps ok")

def arm(pts, seed):
    """A fat brush stroke with round, slightly uneven ends."""
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    return (f'<path d="{brush(pts, 13, 11, seed)}"/><path d="{blob(x0, y0, 4.2, seed, .15)}"/>'
            f'<path d="{blob(x1, y1, 3.4, seed + 1, .15)}"/>')

def s4_cheer(ink, fid, grain=1.0):
    """The clean direction's cheering book, cut as a rubber stamp: scalloped rim, brushed arms, inked head."""
    bot = T.arc("doelenboek", 60, 60, 46.5, 12.5, SHAN(800, b=30), top=False, tracking=.05, jitter=.5, seed=14)
    inner = (f'<path d="{scallop(60, 60, 58, 14, 5, 41)} {scallop(60, 60, 54, 14, 4.5, 42)}"/>'
             f'<path d="{blob(60, 30, 11, 43, .22)}"/>'
             + arm([(58, 76), (51, 62), (39, 54), (21, 51)], 44)
             + arm([(62, 76), (69, 62), (81, 54), (99, 51)], 45) +
             f'<path d="{bot}"/>')
    return wrap(inner, fid, ink, "0 0 120 120", tilt=-5, grain=grain)

for c, ink in (("", BROWN), ("-red", RED), ("-cream", CREAM)):
    open(f"{OUT}/s4-cheer{c}.svg", "w").write(s4_cheer(ink, "s4" + c))
print("s4 ok")
