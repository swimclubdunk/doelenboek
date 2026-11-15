"""Direction 2: clean, round, stylised marks with a rounded wordmark."""
import math, os
import textlib as T

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2")
FRED = lambda w=600: T.font("fredoka", wght=w, wdth=100)
NUNI = lambda w=800: T.font("nunito", wght=w)

BROWN, DARK, CREAM, TAUPE, CORAL, SUN = "#725C4E", "#3B2F27", "#F4F0E4", "#C8BAAD", "#E07B53", "#F2B544"

def svg(inner, vb="0 0 120 120"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="Doelenboek">'
            f'<title>Doelenboek</title>{inner}</svg>')

# ---- round 1

def c1_cheer(fg=BROWN, ac=CORAL, bg=None):
    """An open book that is also a person with both arms up: a goal reached."""
    return (f'<circle cx="60" cy="33" r="14" fill="{ac}"/>'
            f'<path d="M60 96 C52 80 38 72 20 70 M60 96 C68 80 82 72 100 70" fill="none" stroke="{fg}" '
            f'stroke-width="17" stroke-linecap="round"/>')

def c2_tick(fg=BROWN, ac=CORAL, bg=CREAM):
    """A round badge with a fat tick: the stamp of approval, cleaned up."""
    return (f'<circle cx="60" cy="60" r="54" fill="{fg}"/>'
            f'<path d="M36 62 L52 78 L85 43" fill="none" stroke="{bg}" stroke-width="15" stroke-linecap="round" '
            f'stroke-linejoin="round"/><circle cx="85" cy="43" r="7.5" fill="{ac}"/>')

def c3_d(fg=BROWN, ac=CORAL, bg=CREAM):
    """Lowercase d whose bowl is a target."""
    return (f'<path d="M80 14 L80 90" stroke="{fg}" stroke-width="18" stroke-linecap="round"/>'
            f'<circle cx="52" cy="72" r="27" fill="none" stroke="{fg}" stroke-width="18"/>'
            f'<circle cx="52" cy="72" r="8" fill="{ac}"/>')

def c4_bookheart(fg=BROWN, ac=CORAL, bg=CREAM):
    """Two round pages that make a heart."""
    return (f'<path d="M60 102 L22 64 A21 21 0 0 1 60 34 A21 21 0 0 1 98 64 Z" fill="{fg}" stroke="{fg}" '
            f'stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M60 40 L60 92" stroke="{bg}" stroke-width="6" stroke-linecap="round"/>'
            f'<circle cx="60" cy="18" r="9" fill="{ac}"/>')

def lockup(mark, fg, text, ac, bg, name="doelenboek", font=None, size=58):
    d, w = T.text(name, 0, 0, size, font or FRED(600), anchor="start")
    W = 112 + w + 4
    return svg(f'<g transform="scale(.8333)">{mark(fg, ac, bg)}</g>'
               f'<path transform="translate(112 70)" d="{d}" fill="{text}"/>', f"0 0 {W:.1f} 100")

def write(key, fn):
    open(f"{OUT}/{key}.svg", "w").write(svg(fn()))
    open(f"{OUT}/{key}-dark.svg", "w").write(svg(fn(TAUPE, CORAL, "#2A221C")))
    open(f"{OUT}/{key}-chrome.svg", "w").write(svg(fn(CREAM, SUN, BROWN)))
    open(f"{OUT}/{key}-h.svg", "w").write(lockup(fn, BROWN, DARK, CORAL, CREAM))
    open(f"{OUT}/{key}-h-dark.svg", "w").write(lockup(fn, TAUPE, CREAM, CORAL, "#2A221C"))

for k, fn in {"c1-cheer": c1_cheer, "c2-tick": c2_tick, "c3-d": c3_d, "c4-bookheart": c4_bookheart}.items():
    write(k, fn)
print("clean ok")

# ---- round 2

def r2_cheer(fg=BROWN, ac=CORAL, bg=CREAM):
    """Round 1's cheering book, heavier: fat page-arms with a spine cut between them, a bigger head."""
    arms = (f'<path d="M58 94 C50 78 36 68 16 66" fill="none" stroke="{fg}" stroke-width="22" stroke-linecap="round"/>'
            f'<path d="M62 94 C70 78 84 68 104 66" fill="none" stroke="{fg}" stroke-width="22" stroke-linecap="round"/>')
    return f'<circle cx="60" cy="32" r="17" fill="{ac}"/>' + arms

def rosette(cx, cy, r, bumps, depth, n=240):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        rr = r - depth * (1 - math.cos(bumps * t)) / 2
        pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t)))
    return "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + " Z"

def r2_rosette(fg=BROWN, ac=CORAL, bg=CREAM):
    """The flower stamp of approval, cleaned up: a soft rosette with a fat tick."""
    return (f'<path d="{rosette(60, 60, 57, 12, 7)}" fill="{fg}" stroke="{fg}" stroke-width="2" stroke-linejoin="round"/>'
            f'<path d="M37 61 L53 77 L84 44" fill="none" stroke="{bg}" stroke-width="14" stroke-linecap="round" '
            f'stroke-linejoin="round"/>')

def r2_cheer_badge(fg=BROWN, ac=CORAL, bg=CREAM):
    """The cheering book inside a rosette badge: stamp of approval and person in one."""
    inner = (f'<circle cx="60" cy="40" r="11" fill="{ac}"/>'
             f'<path d="M58 84 C53 74 44 68 31 67 M62 84 C67 74 76 68 89 67" fill="none" stroke="{bg}" '
             f'stroke-width="14" stroke-linecap="round"/>')
    return f'<path d="{rosette(60, 60, 57, 12, 7)}" fill="{fg}" stroke="{fg}" stroke-width="2" stroke-linejoin="round"/>' + inner

def app_icon(fn, fg=CREAM, ac=SUN, bg=BROWN):
    return svg(f'<rect width="120" height="120" rx="28" fill="{bg}"/><g transform="translate(14 14) scale(.7667)">'
               f'{fn(fg, ac, bg)}</g>')

for k, fn in {"r2-cheer": r2_cheer, "r2-rosette": r2_rosette, "r2-cheer-badge": r2_cheer_badge, "c3-d": c3_d}.items():
    write(k, fn)
    open(f"{OUT}/{k}-app.svg", "w").write(app_icon(fn))
print("round 2 ok")
