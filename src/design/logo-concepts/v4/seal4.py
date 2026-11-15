"""Seal, round 3: books in 3/4 view from above; blue ink on beige paper."""
import os
from seal import ink_filter, ring, star, SHAN, OUT
import textlib as T
from books3d import stack

BLUE, NAVY, BEIGE = "#2352C8", "#1A3B96", "#F3ECDF"

def seal(ink, fid, speck=1.0, blot=.3):
    top = T.arc("DOELENBOEK", 60, 60, 37, 17.5, SHAN(800), top=True, tracking=.24, jitter=.8, seed=2)
    inner = (f'<path d="{ring(60, 60, 54.5, 6.5, 11, .8)}"/>'
             f'<path d="{ring(60, 60, 33.5, 3.6, 17, .6)}"/>'
             f'<path d="{top}" stroke="{ink}" stroke-width=".9" stroke-linejoin="round"/>'
             f'<path d="{star(60, 102.5, 5.4, 3, .1)}" stroke="{ink}" stroke-width="1.2" stroke-linejoin="round"/>'
             f'<path d="{star(36.5, 96.5, 3.4, 1, .3)}" stroke="{ink}" stroke-width="1" stroke-linejoin="round"/>'
             f'<path d="{star(83.5, 96.5, 3.4, 2, -.3)}" stroke="{ink}" stroke-width="1" stroke-linejoin="round"/>'
             + f'<g transform="translate(60 59) scale(1.1) translate(-60 -58)">' + stack(ink, fid + "m") + "</g>")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="Doelenboek">'
            f'<title>Doelenboek</title><defs>{ink_filter(fid, speck=speck, blot=blot)}</defs>'
            f'<g filter="url(#{fid})" fill="{ink}" fill-rule="evenodd" transform="rotate(-8 60 60)">{inner}</g></svg>')

def books_only(ink, fid):
    """The book stack alone, for the favicon."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="33 40 54 42" role="img" aria-label="Doelenboek">'
            f'<title>Doelenboek</title><defs>{ink_filter(fid, speck=.5, blot=0)}</defs>'
            f'<g filter="url(#{fid})">{stack(ink, fid + "m")}</g></svg>')

for name, ink in (("blue", BLUE), ("navy", NAVY), ("beige", BEIGE)):
    open(f"{OUT}/seal4-{name}.svg", "w").write(seal(ink, "s4" + name))
open(f"{OUT}/seal4-blue-solid.svg", "w").write(seal(BLUE, "s4bs", speck=0, blot=0))
open(f"{OUT}/books4-blue.svg", "w").write(books_only(BLUE, "b4b"))
open(f"{OUT}/books4-beige.svg", "w").write(books_only(BEIGE, "b4w"))
print("seal4 ok")
