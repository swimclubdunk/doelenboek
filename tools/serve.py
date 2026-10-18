"""Local preview for design work: rebuilds the app on every page load, so editing a file in
src/design/ (or anywhere else) and refreshing the browser is the whole loop.

Usage: python tools/serve.py [--live] [--port 8000]

  http://localhost:8000/          the app
  http://localhost:8000/animals   every animal drawing, with a check that each one fills its frame
  http://localhost:8000/over/     the public pages (also /minimumdoelen/, /en/about/, /llms.txt, ...)

By default the app keeps its data in this browser only, so you can add and delete test children
freely. --live builds with firebase-config.json, which logs into real accounts and real data."""
import argparse, html, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import ROOT, DOELEN_DIR, BuildError, build, animal_symbols, subject_keys_of  # noqa: E402
import public  # noqa: E402

SRC = ROOT / 'src' / 'doelenboek.html'
CONFIG = ROOT / 'firebase-config.json'
DESIGN = ROOT / 'src' / 'design'
FONTS = DESIGN / 'fonts'
TYPES = {'.html': 'text/html; charset=utf-8', '.txt': 'text/plain; charset=utf-8', '.xml': 'application/xml; charset=utf-8'}


def animals_page():
    pairs, sprite = animal_symbols(ROOT / 'src' / 'design' / 'animals')
    cells = ''.join(
        f'<figure><div class="frames">'
        f'<svg class="big" viewBox="0 0 64 64"><use href="#an-{n}"/></svg>'
        f'<svg class="big dark" viewBox="0 0 64 64"><use href="#an-{n}"/></svg></div>'
        f'<div class="sizes">' + ''.join(f'<svg style="width:{s}px;height:{s}px" viewBox="0 0 64 64"><use href="#an-{n}"/></svg>' for s in (52, 30, 24)) +
        f'</div><figcaption>{html.escape(e)} {n} <b data-check="{n}"></b></figcaption></figure>'
        for e, n in pairs)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Animals</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 24px; background: #F4F6F1; color: #1B2420; }}
p {{ max-width: 70ch; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 12px; }}
figure {{ margin: 0; padding: 10px; background: #fff; border-radius: 10px; display: grid; gap: 8px; }}
.frames {{ display: flex; gap: 8px; }}
.big {{ width: 90px; height: 90px; outline: 1px dashed #d55; background: #fff; }}
.big.dark {{ background: #192019; }}
.sizes {{ display: flex; gap: 8px; align-items: center; }}
figcaption {{ font-size: 13px; }}
b.ok {{ color: #2E7D4F; }} b.bad {{ color: #B3261E; }}
</style></head><body>
<h1>Animals</h1>
<p>Each drawing on white and on the dark-mode card colour; the dashed square is the avatar. A drawing should touch
two opposite sides of the square: its viewBox hugs the drawing. The order and emoji come from animals.json.</p>
<div class="grid">{cells}</div>
{sprite}
<script>
/* Render each drawing and check that it reaches the edges of its square. */
(async () => {{
  const N = 200;
  for (const el of document.querySelectorAll('[data-check]')) {{
    const sym = document.getElementById('an-' + el.dataset.check);
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${{N}}" height="${{N}}" viewBox="0 0 64 64"><defs>${{sym.outerHTML}}</defs><use href="#${{sym.id}}" width="64" height="64"/></svg>`;
    const img = new Image();
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    try {{ await img.decode(); }} catch (e) {{ el.textContent = '✗ does not render'; el.className = 'bad'; continue; }}
    const c = document.createElement('canvas'); c.width = c.height = N;
    const g = c.getContext('2d'); g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, N, N).data;
    let x0 = N, y0 = N, x1 = -1, y1 = -1;
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) if (d[(y * N + x) * 4 + 3] > 8) {{ x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }}
    const gap = Math.min(x0 + (N - 1 - x1), y0 + (N - 1 - y1));
    const ok = gap <= 2;
    el.textContent = ok ? '✓ fills the frame' : `✗ leaves ${{Math.round(100 * gap / N)}}% empty: fit the viewBox to the drawing`;
    el.className = ok ? 'ok' : 'bad';
  }}
}})();
</script></body></html>"""


def error_page(msg):
    return f"""<!doctype html><meta charset="utf-8"><title>Build error</title>
<body style="font-family: system-ui, sans-serif; margin: 40px; background: #FBF0D2; color: #5A4200">
<h1>The build stopped</h1><pre style="white-space: pre-wrap; font-size: 15px">{html.escape(msg)}</pre>
<p>Fix the file and refresh this page.</p></body>"""


class Handler(BaseHTTPRequestHandler):
    live = False

    def do_GET(self):
        path = self.path.split('?')[0].split('#')[0]
        try:
            if path in ('/', '/index.html'):
                body, status = build(SRC, CONFIG if self.live else None), 200
            elif path == '/animals':
                body, status = animals_page(), 200
            elif path.strip('/') in public.COPIED:
                return self.send_file(DESIGN / path.strip('/'))
            elif (page := self.public_file(path)) is not None:
                return self.send_text(*page)
            elif path.startswith('/fonts/') and (FONTS / path[7:]).is_file() and '/' not in path[7:]:
                return self.send_file(FONTS / path[7:])
            else:
                body, status = '<!doctype html><title>Not found</title>Not found. Try / or /animals.', 404
        except BuildError as e:
            body, status = error_page(str(e)), 500
        data = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')   # every refresh shows the current files
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def public_file(self, path):
        """(text, content type) of a public page or crawler file, rebuilt on every request; None if PATH is none of them."""
        rel = path.strip('/')
        files = public.site_files(DESIGN, DOELEN_DIR, subject_keys_of(SRC.read_text(encoding='utf-8')))
        for key in (rel, rel + '/index.html'):
            if key in files:
                return files[key], TYPES[Path(key).suffix]
        return None

    def send_text(self, body, ctype):
        data = body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, f):
        data = f.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', {'.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.png': 'image/png'}.get(f.suffix, 'text/plain; charset=utf-8'))
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--live', action='store_true', help='use firebase-config.json: real accounts and real data')
    ap.add_argument('--port', type=int, default=8000)
    args = ap.parse_args()
    Handler.live = args.live
    server = HTTPServer(('127.0.0.1', args.port), Handler)
    mode = 'LIVE data (Firebase)' if args.live else 'data kept in this browser only'
    print(f'Doelenboek preview, {mode}:\n  http://localhost:{args.port}/\n  http://localhost:{args.port}/animals\nCtrl+C to stop.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
