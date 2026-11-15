"""S1 seal, round 2: a stack of books instead of the tick, no bottom text, DOELENBOEK spread wide,
everything heavier and inked more solidly."""
import math, os, random, sys
from stamp import blob, ring, star, wobble_fn, SHAN, OUT, BROWN, RED, CREAM
import textlib as T

def ink_filter(fid, seed=4, rough=1.4, speck=1.0, blot=.3):
    """Rough edges; a few specks and a gentle unevenness, so the ink stays dense (high contrast)."""
    return f'''<filter id="{fid}" x="-8%" y="-8%" width="116%" height="116%" color-interpolation-filters="sRGB">
<feTurbulence type="fractalNoise" baseFrequency=".09" numOctaves="2" seed="{seed}" result="w"/>
<feDisplacementMap in="SourceGraphic" in2="w" scale="{rough}" xChannelSelector="R" yChannelSelector="G" result="r"/>
<feTurbulence type="fractalNoise" baseFrequency=".7" numOctaves="2" seed="{seed+3}" result="g"/>
<feColorMatrix in="g" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 {6*speck:.2f} 0 0 0 {1-1.3*speck:.2f}" result="ga"/>
<feTurbulence type="fractalNoise" baseFrequency=".03" numOctaves="3" seed="{seed+9}" result="b"/>
<feColorMatrix in="b" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 {1.4*blot:.2f} 0 0 0 {1-.45*blot:.2f}" result="ba"/>
<feComposite in="ga" in2="ba" operator="arithmetic" k1="1" result="m"/>
<feComposite in="r" in2="m" operator="in"/>
</filter>'''

def wobbly_box(x, y, w, h, rad, seed, amp=.35, n=120):
    """A hand-cut rounded rectangle (centre-based wobble, so it stays a clean closed shape)."""
    wf = wobble_fn(seed, amp)
    pts = []
    cx, cy = x + w / 2, y + h / 2
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        # superellipse-ish rounded rect: exponent gives the corner radius feel
        p = 2 + 10 * (1 - rad / min(w, h))
        px = cx + (w / 2) * math.copysign(abs(c) ** (2 / p), c)
        py = cy + (h / 2) * math.copysign(abs(s) ** (2 / p), s)
        o = wf(t)
        pts.append((px + c * o, py + s * o))
    return "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + " Z"

def book(cx, cy, w, h, rot, seed, spine_left=True):
    """One book lying flat, seen from the side: a solid cover with the page block and two spine bands cut out.
    Returns path data (evenodd: the holes are inner shapes)."""
    x, y = cx - w / 2, cy - h / 2
    d = wobbly_box(x, y, w, h, 3, seed)
    rnd = random.Random(seed)
    if spine_left:
        pages = wobbly_box(x + w - 10, y + 3, 7.4, h - 6, 1.5, seed + 1, .15)
        bands = [x + 6]
    else:
        pages = wobbly_box(x + 2.6, y + 3, 7.4, h - 6, 1.5, seed + 1, .15)
        bands = [x + w - 8.6]
    d += " " + pages
    for bx in bands:
        d += " " + wobbly_box(bx, y + 2.6, 2.6, h - 5.2, 1, seed + int(bx), .1)
    return f'<path d="{d}" transform="rotate({rot} {cx} {cy})"/>'

def books():
    return (book(60, 72.5, 46, 13, 1.5, 61, True)
            + book(58.6, 59.5, 41, 12.5, -3, 62, False)
            + book(61, 47, 35, 12, 4, 63, True))

def seal(ink, fid, speck=1.0, blot=.3):
    top = T.arc("DOELENBOEK", 60, 60, 37, 17.5, SHAN(800), top=True, tracking=.24, jitter=.8, seed=2)
    inner = (f'<path d="{ring(60, 60, 54.5, 6.5, 11, .8)}"/>'
             f'<path d="{ring(60, 60, 33.5, 3.6, 17, .6)}"/>'
             f'<path d="{top}" stroke="{ink}" stroke-width=".9" stroke-linejoin="round"/>'
             f'<path d="{star(60, 102.5, 5.4, 3, .1)}" stroke="{ink}" stroke-width="1.2" stroke-linejoin="round"/>'
             f'<path d="{star(36.5, 96.5, 3.4, 1, .3)}" stroke="{ink}" stroke-width="1" stroke-linejoin="round"/>'
             f'<path d="{star(83.5, 96.5, 3.4, 2, -.3)}" stroke="{ink}" stroke-width="1" stroke-linejoin="round"/>'
             + books())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="Doelenboek">'
            f'<title>Doelenboek</title><defs>{ink_filter(fid, speck=speck, blot=blot)}</defs>'
            f'<g filter="url(#{fid})" fill="{ink}" fill-rule="evenodd" transform="rotate(-8 60 60)">{inner}</g></svg>')

for c, ink in (("", BROWN), ("-red", RED), ("-cream", CREAM)):
    open(f"{OUT}/seal{c}.svg", "w").write(seal(ink, "seal" + c))
open(f"{OUT}/seal-solid.svg", "w").write(seal(BROWN, "seal-solid", speck=0, blot=0))
print("seal ok")
