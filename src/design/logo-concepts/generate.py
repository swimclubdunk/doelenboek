"""Generate Doelenboek logo concepts as SVG (text outlined to paths, so no font is needed)."""
import io, math, sys, os
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import uharfbuzz as hb

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

BROWN, DARK, CREAM, TAUPE, WARM = "#725C4E", "#3B2F27", "#F4F0E4", "#C8BAAD", "#B07A52"

_fonts = {}
def font(**axes):
    key = tuple(sorted(axes.items()))
    if key not in _fonts:
        f = TTFont(os.path.join(HERE, "font", "fraunces.ttf"))
        f = instancer.instantiateVariableFont(f, axes)
        buf = io.BytesIO(); f.save(buf); data = buf.getvalue()
        _fonts[key] = (TTFont(io.BytesIO(data)), hb.Font(hb.Face(data)))
    return _fonts[key]

def shape(text, axes, tracking=0):
    tt, hbf = font(**axes)
    upem = tt["head"].unitsPerEm
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(hbf, buf, {"kern": True, "liga": True})
    order = tt.getGlyphOrder()
    out, x = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((order[info.codepoint], x + pos.x_offset, pos.y_offset, pos.x_advance))
        x += pos.x_advance + tracking * upem
    return tt, upem, out, x - tracking * upem

def glyph_d(tt, name, transform):
    pen = SVGPathPen(tt.getGlyphSet())
    tt.getGlyphSet()[name].draw(TransformPen(pen, transform))
    return pen.getCommands()

def text_path(text, x, y, size, axes, anchor="middle", tracking=0):
    """One path for a line of text; (x, y) is the baseline point at the anchor."""
    tt, upem, glyphs, width = shape(text, axes, tracking)
    s = size / upem
    x0 = x - (width * s / 2 if anchor == "middle" else 0)
    ds = [glyph_d(tt, n, (s, 0, 0, -s, x0 + gx * s, y - gy * s)) for n, gx, gy, _ in glyphs]
    return " ".join(d for d in ds if d), width * s

def arc_text(text, cx, cy, r, size, axes, top=True, tracking=0.08):
    """Text centred on the top (reads clockwise) or bottom (reads counter-clockwise) of a circle.
    r is the baseline radius."""
    tt, upem, glyphs, width = shape(text, axes, tracking)
    s = size / upem
    total = width * s / r  # radians
    ds = []
    for n, gx, gy, adv in glyphs:
        mid = (gx + adv / 2) * s / r - total / 2  # angle offset of the glyph centre
        if top:
            a = -math.pi / 2 + mid
            px, py = cx + r * math.cos(a), cy + r * math.sin(a)
            rot = a + math.pi / 2
        else:
            a = math.pi / 2 - mid
            px, py = cx + r * math.cos(a), cy + r * math.sin(a)
            rot = a - math.pi / 2
        c, si = math.cos(rot), math.sin(rot)
        # local glyph coords: x from -adv/2..adv/2, y up -> flip
        hx = adv * s / 2
        # transform: rotate(rot) then translate(px,py); local point (u,v) font units -> (u*s - hx, -v*s)
        a11, a12 = c * s, -si * -s   # x' = c*(u*s-hx) - si*(-v*s)
        a21, a22 = si * s, c * -s
        tx = px + c * (-hx) ; ty = py + si * (-hx)
        ds.append(glyph_d(tt, n, (a11, a21, a12, a22, tx, ty)))
    return " ".join(d for d in ds if d)

WORD = dict(wght=620, opsz=96, SOFT=100, WONK=1)
CAPS = dict(wght=640, opsz=12, SOFT=100, WONK=0)

# ---------------------------------------------------------------- marks (viewBox 0 0 120 120)

def book(cx, base, w, h, fill, gap=CREAM, lines=False):
    """Open book seen from the front: two gently curved pages meeting at a spine."""
    l, r = cx - w / 2, cx + w / 2
    top = base - h
    left = (f"M{cx} {top+4} C{cx-w*.18} {top-2} {l+w*.12} {top-1} {l} {top+3} "
            f"L{l} {base-3} C{l+w*.14} {base-7} {cx-w*.18} {base-6} {cx} {base} Z")
    right = (f"M{cx} {top+4} C{cx+w*.18} {top-2} {r-w*.12} {top-1} {r} {top+3} "
             f"L{r} {base-3} C{r-w*.14} {base-7} {cx+w*.18} {base-6} {cx} {base} Z")
    out = f'<path d="{left}" fill="{fill}"/><path d="{right}" fill="{fill}"/>'
    out += f'<path d="M{cx} {top+5} L{cx} {base-1}" stroke="{gap}" stroke-width="{max(1.6, w/40):.2f}" stroke-linecap="round"/>'
    if lines:
        for i in range(3):
            y = top + 9 + i * (h - 16) / 3
            out += (f'<path d="M{l+w*.08} {y+1} C{l+w*.2} {y-1.2} {cx-w*.14} {y-1.2} {cx-w*.06} {y+1}" '
                    f'stroke="{gap}" stroke-width="1.6" fill="none" stroke-linecap="round" opacity=".75"/>')
            out += (f'<path d="M{r-w*.08} {y+1} C{r-w*.2} {y-1.2} {cx+w*.14} {y-1.2} {cx+w*.06} {y+1}" '
                    f'stroke="{gap}" stroke-width="1.6" fill="none" stroke-linecap="round" opacity=".75"/>')
    return out

def sprout(cx, base, h, color):
    """A stem with two leaves, growing up from (cx, base)."""
    top = base - h
    return (f'<path d="M{cx} {base} C{cx} {base-h*.45} {cx+1} {top+h*.3} {cx} {top}" stroke="{color}" '
            f'stroke-width="3" fill="none" stroke-linecap="round"/>'
            f'<path d="M{cx} {top+h*.32} C{cx-4} {top+h*.05} {cx-14} {top-1} {cx-19} {top+h*.06} '
            f'C{cx-16} {top+h*.38} {cx-6} {top+h*.5} {cx} {top+h*.32} Z" fill="{color}"/>'
            f'<path d="M{cx} {top+h*.12} C{cx+4} {top-h*.18} {cx+14} {top-h*.24} {cx+19} {top-h*.14} '
            f'C{cx+16} {top+h*.16} {cx+6} {top+h*.28} {cx} {top+h*.12} Z" fill="{color}"/>')

def mark_bookplate(fg=BROWN, bg=CREAM, accent=WARM):
    """A: ex-libris arch with an open book and a sprout growing from its spine."""
    arch = "M22 112 L22 44 C22 22 40 8 60 8 C80 8 98 22 98 44 L98 112 Z"
    inner = "M28 106 L28 45 C28 27 43 14 60 14 C77 14 92 27 92 45 L92 106 Z"
    return (f'<path d="{arch}" fill="{fg}"/>'
            f'<path d="{inner}" fill="{bg}"/>'
            f'<path d="M32 102 L32 46 C32 30 45 18 60 18 C75 18 88 30 88 46 L88 102 Z" fill="none" '
            f'stroke="{fg}" stroke-width="1.2"/>'
            + sprout(60, 70, 32, accent)
            + book(60, 96, 50, 28, fg, gap=bg, lines=True))

def mark_together(fg=BROWN, bg=CREAM, accent=WARM):
    """B: a grown-up and a child, side by side, behind one open book."""
    parent = (f'<circle cx="46" cy="36" r="12" fill="{accent}"/>'
              f'<path d="M24 82 C24 62 33 54 46 54 C59 54 68 62 68 82 Z" fill="{accent}"/>')
    child = (f'<circle cx="78" cy="51" r="9" fill="{fg}"/>'
             f'<path d="M62 86 C62 72 69 65 78 65 C87 65 94 72 94 86 Z" fill="{fg}"/>')
    # gaps are cut with masks (not painted), so the mark sits on any background
    child_halo = ('<circle cx="78" cy="51" r="11.5" fill="#000"/>'
                  '<path d="M59.5 88 C59.5 70 68 62.5 78 62.5 C88 62.5 96.5 70 96.5 88 Z" fill="#000"/>')
    book_halo = '<path d="M15 76 C34 69 50 70 60 76 C70 70 86 69 105 76 L105 112 L15 112 Z" fill="#000"/>'
    uid = "t" + fg[1:] + bg[1:]
    defs = (f'<defs><mask id="{uid}p" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">'
            f'<rect width="120" height="120" fill="#fff"/>{child_halo}{book_halo}</mask>'
            f'<mask id="{uid}c" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">'
            f'<rect width="120" height="120" fill="#fff"/>{book_halo}</mask></defs>')
    b = book(60, 108, 84, 34, fg, gap=bg, lines=True)
    b = b.replace(f'stroke="{bg}"', 'stroke="#000"')  # page lines and spine are cut, too
    book_lines = b.split('<path d="M', 3)  # first two paths are the pages; the rest are cuts
    pages = '<path d="M' + book_lines[1] + '<path d="M' + book_lines[2]
    cuts = "".join('<path d="M' + p for p in book_lines[3].split('<path d="M')) if len(book_lines) > 3 else ""
    cuts = cuts.replace('<path d="M<path d="M', '<path d="M')
    defs += (f'<defs><mask id="{uid}b" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">'
             f'<rect width="120" height="120" fill="#fff"/>{cuts}</mask></defs>')
    return (defs + f'<g mask="url(#{uid}p)">{parent}</g><g mask="url(#{uid}c)">{child}</g>'
            f'<g mask="url(#{uid}b)">{pages}</g>')

def mark_seal(fg=BROWN, bg=CREAM, accent=WARM, words=("DOELENBOEK", "VLAANDEREN")):
    """C: a round stamp; target rings (doel) around an open book, the name lettered around the rim."""
    top = arc_text(words[0], 60, 60, 44.5, 10.5, CAPS, top=True, tracking=0.16)
    bot = arc_text(words[1], 60, 60, 52.2, 8.5, CAPS, top=False, tracking=0.22)
    stars = "".join(f'<circle cx="{60+48*math.cos(a):.2f}" cy="{60+48*math.sin(a):.2f}" r="1.6" fill="{bg}"/>'
                    for a in (math.radians(180 - 34), math.radians(34)))
    return (f'<circle cx="60" cy="60" r="58" fill="{fg}"/>'
            f'<circle cx="60" cy="60" r="40" fill="{bg}"/>'
            f'<circle cx="60" cy="60" r="35.5" fill="none" stroke="{fg}" stroke-width="1.2"/>'
            f'<circle cx="60" cy="60" r="55" fill="none" stroke="{bg}" stroke-width=".9"/>'
            f'<path d="{top}" fill="{bg}"/><path d="{bot}" fill="{bg}"/>' + stars
            + f'<circle cx="60" cy="56" r="24" fill="none" stroke="{TAUPE}" stroke-width="2"/>'
            + f'<circle cx="60" cy="56" r="14" fill="none" stroke="{TAUPE}" stroke-width="2"/>'
            + f'<circle cx="60" cy="44" r="4.2" fill="{accent}"/>'
            + book(60, 80, 44, 24, fg, gap=bg, lines=False))

def svg(inner, vb="0 0 120 120", w=None, h=None, title="Doelenboek"):
    size = f' width="{w}" height="{h}"' if w else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}"{size} role="img" aria-label="{title}">'
            f'<title>{title}</title>{inner}</svg>')

# ---------------------------------------------------------------- lockups

def lockup_h(mark_fn, fg=BROWN, text=DARK, bg=CREAM, accent=WARM):
    d, wpx = text_path("Doelenboek", 0, 0, 56, WORD, anchor="start")
    mark = f'<g transform="translate(0 0) scale(.8333)">{mark_fn(fg, bg, accent)}</g>'  # 100px tall
    word = f'<path transform="translate(118 70)" d="{d}" fill="{text}"/>'
    W = 118 + wpx + 4
    return svg(mark + word, vb=f"0 0 {W:.1f} 100"), W

def lockup_v(mark_fn, fg=BROWN, text=DARK, bg=CREAM, accent=WARM):
    d, wpx = text_path("Doelenboek", 0, 0, 44, WORD, anchor="middle")
    W = max(wpx + 8, 140)
    mark = f'<g transform="translate({W/2-60:.1f} 0)">{mark_fn(fg, bg, accent)}</g>'
    word = f'<path transform="translate({W/2:.1f} 168)" d="{d}" fill="{text}"/>'
    return svg(mark + word, vb=f"0 0 {W:.1f} 182"), W

DARK_BG = "#2A221C"
concepts = {
    "a-bookplate": ("A · Bookplate", mark_bookplate),
    "b-together": ("B · Reading together", mark_together),
    "c-seal": ("C · Seal", mark_seal),
}
for key, (_, fn) in concepts.items():
    open(f"{OUT}/{key}-mark.svg", "w").write(svg(fn()))
    open(f"{OUT}/{key}-mark-dark.svg", "w").write(svg(fn(fg=TAUPE, bg=DARK_BG, accent="#D19A6E")))
    open(f"{OUT}/{key}-horizontal.svg", "w").write(lockup_h(fn)[0])
    open(f"{OUT}/{key}-horizontal-dark.svg", "w").write(
        lockup_h(fn, fg=TAUPE, text=CREAM, bg=DARK_BG, accent="#D19A6E")[0])
    open(f"{OUT}/{key}-stacked.svg", "w").write(lockup_v(fn)[0])
print("ok", sorted(os.listdir(OUT)))
