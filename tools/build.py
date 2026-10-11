"""Wrap the artifact page (head-less fragment) into a complete standalone index.html.
Usage: build_standalone.py SRC.html OUT.html [FIREBASE_CONFIG.json]"""
import sys, json

src, out = sys.argv[1], sys.argv[2]
text = open(src, encoding='utf-8').read()
if len(sys.argv) > 3:
    cfg = json.load(open(sys.argv[3], encoding='utf-8'))
    needle = 'const FIREBASE_CONFIG = null;'
    assert text.count(needle) == 1, 'config placeholder not found exactly once'
    text = text.replace(needle, 'const FIREBASE_CONFIG = ' + json.dumps(cfg, ensure_ascii=False) + ';')
marker = '<header class="top">'
i = text.index(marker)
head, body = text[:i].rstrip(), text[i:].rstrip()

favicon = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
           "%3Crect width='64' height='64' rx='14' fill='%231F6F78'/%3E"
           "%3Cpath d='M18 16h14a16 16 0 0 1 0 32H18z' fill='none' stroke='white' stroke-width='6'/%3E"
           "%3Ccircle cx='31' cy='32' r='4' fill='%23E9C46A'/%3E%3C/svg%3E")

page = f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Doelenboek: houd per kind bij welke Vlaamse minimumdoelen aan bod kwamen in huisonderwijs.">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="{favicon}">
{head}
</head>
<body>
{body}
</body>
</html>
"""
open(out, 'w', encoding='utf-8', newline='\n').write(page)
print(f'wrote {out} ({len(page.encode("utf-8")):,} bytes)')
