"""Text to SVG paths (outlined, so the logo needs no font), straight or along a circle, with optional
hand-set jitter per letter."""
import io, math, os, random
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import uharfbuzz as hb

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font")
_cache = {}

def font(name, **axes):
    key = (name, tuple(sorted(axes.items())))
    if key not in _cache:
        f = TTFont(os.path.join(FONTS, name + ".ttf"))
        if "fvar" in f:
            f = instancer.instantiateVariableFont(f, axes)
        buf = io.BytesIO(); f.save(buf); data = buf.getvalue()
        _cache[key] = (TTFont(io.BytesIO(data)), hb.Font(hb.Face(data)))
    return _cache[key]

def shape(text, fnt, tracking=0):
    tt, hbf = fnt
    upem = tt["head"].unitsPerEm
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(hbf, buf, {"kern": True, "liga": True})
    order = tt.getGlyphOrder()
    out, x = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((order[info.codepoint], x + pos.x_offset, pos.y_offset, pos.x_advance))
        x += pos.x_advance + tracking * upem
    return upem, out, x - tracking * upem

def _d(tt, name, t):
    pen = SVGPathPen(tt.getGlyphSet())
    tt.getGlyphSet()[name].draw(TransformPen(pen, t))
    return pen.getCommands()

def _place(tt, name, s, hx, rot, px, py):
    """Glyph with its advance centred on (px, py) baseline, rotated by rot radians."""
    c, si = math.cos(rot), math.sin(rot)
    return _d(tt, name, (c * s, si * s, si * s, -c * s, px - c * hx, py - si * hx))

def text(txt, x, y, size, fnt, anchor="middle", tracking=0, jitter=0, seed=1):
    """A line of text as one path d; (x, y) = baseline at the anchor. jitter (0..1) adds hand-set wobble."""
    tt = fnt[0]
    upem, glyphs, width = shape(txt, fnt, tracking)
    s = size / upem
    x0 = x - (width * s / 2 if anchor == "middle" else 0)
    rnd = random.Random(seed)
    ds = []
    for n, gx, gy, adv in glyphs:
        k = 1 + jitter * rnd.uniform(-.06, .06)
        rot = jitter * math.radians(rnd.uniform(-5, 5))
        dy = jitter * rnd.uniform(-.05, .05) * size
        ds.append(_place(tt, n, s * k, adv * s * k / 2, rot, x0 + (gx + adv / 2) * s, y - gy * s + dy))
    return " ".join(d for d in ds if d), width * s

def arc(txt, cx, cy, r, size, fnt, top=True, tracking=0.1, jitter=0, seed=1):
    """Text centred on the top (clockwise) or bottom (upright, counter-clockwise) of a circle;
    r is the baseline radius."""
    tt = fnt[0]
    upem, glyphs, width = shape(txt, fnt, tracking)
    s = size / upem
    total = width * s / r
    rnd = random.Random(seed)
    ds = []
    for n, gx, gy, adv in glyphs:
        mid = (gx + adv / 2) * s / r - total / 2
        a = -math.pi / 2 + mid if top else math.pi / 2 - mid
        rr = r + jitter * rnd.uniform(-.05, .05) * size
        k = 1 + jitter * rnd.uniform(-.06, .06)
        rot = (a + math.pi / 2 if top else a - math.pi / 2) + jitter * math.radians(rnd.uniform(-5, 5))
        ds.append(_place(tt, n, s * k, adv * s * k / 2, rot, cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return " ".join(d for d in ds if d)
