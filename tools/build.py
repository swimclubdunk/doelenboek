"""Build the standalone index.html from the app source, the design files and the goals.
Usage: build.py SRC.html OUT.html [FIREBASE_CONFIG.json]

- the stylesheets SRC links to (design/*.css, core.css) are inlined
- the animal drawings in design/animals/ become <symbol>s in the page
- the favicon comes from design/favicon.svg
- the built-in goals come from doelen/*.json"""
import sys, json, re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
DOELEN_DIR = ROOT / 'doelen'
GOAL_FIELDS = {'code', 'category', 'categoryEn', 'description', 'descriptionEn'}


class BuildError(Exception):
    """A mistake in one of the input files, with a message that says where."""


def fail(where, msg):
    raise BuildError(f'{where}: {msg}')


def load_goals(subject_keys):
    """Read every doelen/*.json file and return the goals in the shape the app expects.
    Stops with a readable message on the first mistake, so a hand edit can't break the app."""
    goals, seen_subjects = [], {}
    for path in sorted(DOELEN_DIR.glob('*.json')):
        where = path.relative_to(ROOT)
        try:
            doc = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            fail(where, f'not valid JSON (line {e.lineno}, column {e.colno}: {e.msg})')
        subject = doc.get('subject') if isinstance(doc, dict) else None
        if subject not in subject_keys:
            fail(where, f'"subject" must be one of {", ".join(subject_keys)}')
        if subject in seen_subjects:
            fail(where, f'subject {subject} is already used by {seen_subjects[subject]}')
        seen_subjects[subject] = path.name
        if not isinstance(doc.get('doelen'), list):
            fail(where, '"doelen" must be a list')
        codes = set()
        for n, g in enumerate(doc['doelen'], 1):
            goal = f'goal {n}' + (f' ({g.get("code")})' if isinstance(g, dict) and g.get('code') else '')
            if not isinstance(g, dict):
                fail(where, f'{goal} must be an object {{ ... }}')
            unknown = set(g) - GOAL_FIELDS
            if unknown:
                fail(where, f'{goal} has unknown field(s) {", ".join(sorted(unknown))}; allowed: {", ".join(sorted(GOAL_FIELDS))}')
            for k, v in g.items():
                if not isinstance(v, str):
                    fail(where, f'{goal}: "{k}" must be text in quotes')
            code = g.get('code', '').strip()
            if not code:
                fail(where, f'{goal} has no "code"')
            if not g.get('description', '').strip():
                fail(where, f'{goal} has no "description"')
            if code in codes:
                fail(where, f'code {code} appears twice')
            codes.add(code)
            goals.append({'id': f'b-{subject}-{code}', 'subject': subject, **{k: v.strip() if k == 'code' else v for k, v in g.items()}})
    return goals


def inline_styles(text, src_dir):
    """Replace each <link rel="stylesheet" href="local.css"> with a <style> holding that file."""
    def one(m):
        path = src_dir / m.group(1)
        if not path.is_file():
            fail(f'{m.group(0)}', 'stylesheet not found')
        css = path.read_text(encoding='utf-8').rstrip()
        if '</style' in css.lower():
            fail(path.relative_to(ROOT), 'a stylesheet may not contain "</style"')
        return f'<style>\n{css}\n</style>'
    return re.sub(r'<link rel="stylesheet" href="(?!https?:)([^"]+)">', one, text)


# attributes of a drawing's <svg> element that only describe the file, not how it looks
SVG_ROOT_SKIP = {'width', 'height', 'viewbox', 'version', 'id', 'x', 'y', 'class', 'xml:space'}


def svg_symbol(path, name):
    """One SVG file as a <symbol id="an-NAME">. Accepts files saved by design tools: drops the XML
    prolog, comments and metadata, keeps presentation attributes of the <svg> element (fill, stroke,
    ...), and prefixes ids so gradients in different files can't clash."""
    where = path.relative_to(ROOT)
    svg = path.read_text(encoding='utf-8')
    svg = re.sub(r'<\?xml.*?\?>|<!DOCTYPE.*?>|<!--.*?-->|<metadata\b.*?</metadata>', '', svg, flags=re.S | re.I)
    if re.search(r'<script|<foreignObject|\son\w+\s*=|javascript:', svg, re.I):
        fail(where, 'scripts, event handlers and embedded HTML are not allowed in a drawing')
    m = re.fullmatch(r'\s*<svg\b([^>]*)>(.*)</svg>\s*', svg, re.S)
    if not m:
        fail(where, 'must contain a single <svg> ... </svg> element')
    attrs = re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', m.group(1))
    box = next((v for k, v in attrs if k.lower() == 'viewbox'), None)
    if not box or len(box.replace(',', ' ').split()) != 4:
        fail(where, 'the <svg> element needs a viewBox="x y width height" that hugs the drawing')
    inner = m.group(2).strip()
    for i in sorted(set(re.findall(r'\bid="([^"]+)"', inner)), key=len, reverse=True):
        new = f'an-{name}-{i}'
        for a, b in ((f'id="{i}"', f'id="{new}"'), (f'url(#{i})', f'url(#{new})'), (f'href="#{i}"', f'href="#{new}"')):
            inner = inner.replace(a, b)
    keep = ' '.join(f'{k}="{v}"' for k, v in attrs if k.lower() not in SVG_ROOT_SKIP and not k.startswith('xmlns'))
    if keep:
        inner = f'<g {keep}>{inner}</g>'
    inner = re.sub(r'>\s+<', '><', inner)
    return f'<symbol id="an-{name}" viewBox="{box}">{inner}</symbol>'


def animal_symbols(animals_dir):
    """The drawings in design/animals/, in the order of animals.json.
    Returns ([[emoji, name], ...], sprite markup for the page)."""
    manifest_path = animals_dir / 'animals.json'
    where = manifest_path.relative_to(ROOT)
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        fail(where, f'not valid JSON (line {e.lineno}, column {e.colno}: {e.msg})')
    if not isinstance(manifest, list) or not manifest:
        fail(where, 'must be a list of {"animal": ..., "emoji": ...} entries')
    names, emojis, pairs, symbols = set(), set(), [], []
    for n, entry in enumerate(manifest, 1):
        name, emoji = (entry.get('animal'), entry.get('emoji')) if isinstance(entry, dict) else (None, None)
        if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9-]+', name):
            fail(where, f'entry {n}: "animal" must be the file name without .svg (lowercase letters, digits, -)')
        if not isinstance(emoji, str) or not emoji or len(emoji) > 16:
            fail(where, f'entry {n} ({name}): "emoji" must be a short text of at most 16 characters')
        if name in names or emoji in emojis:
            fail(where, f'entry {n} ({name}): this animal or emoji is listed twice')
        names.add(name)
        emojis.add(emoji)
        svg_path = animals_dir / f'{name}.svg'
        if not svg_path.is_file():
            fail(where, f'entry {n}: {svg_path.relative_to(ROOT)} not found')
        symbols.append(svg_symbol(svg_path, name))
        pairs.append([emoji, name])
    for extra in sorted({p.stem for p in animals_dir.glob('*.svg')} - names):
        print(f'note: design/animals/{extra}.svg is not listed in animals.json, so it is not used', file=sys.stderr)
    sprite = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">\n'
              + '\n'.join(symbols) + '\n</svg>')
    return pairs, sprite


def favicon_uri(path):
    svg = re.sub(r'\s*\n\s*', '', path.read_text(encoding='utf-8')).replace('"', "'")
    return 'data:image/svg+xml,' + quote(svg, safe=" '=/:;,.-()")


def fill(text, needle, value, what):
    if text.count(needle) != 1:
        raise BuildError(f'{what} placeholder not found exactly once in the source')
    return text.replace(needle, value)


def build(src, firebase_config=None):
    """The complete page as a string. Raises BuildError for a mistake in an input file."""
    src = Path(src).resolve()
    design = src.parent / 'design'
    text = src.read_text(encoding='utf-8')

    s = text.index('const SUBJECTS = [')
    subject_keys = re.findall(r"\{ key: '([A-Z]+)'", text[s:text.index('\n];', s)])
    goals = sorted(load_goals(subject_keys), key=lambda g: subject_keys.index(g["subject"]))  # stable: keeps file order within a subject
    goals_js = json.dumps(goals, ensure_ascii=False, indent=1).replace('</', '<\\/')
    text = fill(text, 'const BUILTIN_GOALS = [];', 'const BUILTIN_GOALS = ' + goals_js + ';', 'goals')

    pairs, sprite = animal_symbols(design / 'animals')
    text = fill(text, 'const ANIMAL_LIST = [];', 'const ANIMAL_LIST = ' + json.dumps(pairs, ensure_ascii=False) + ';', 'animal list')
    text = fill(text, '<!-- animal drawings: filled in by tools/build.py -->', sprite, 'animal drawings')

    if firebase_config:
        cfg = json.loads(Path(firebase_config).read_text(encoding='utf-8'))
        text = fill(text, 'const FIREBASE_CONFIG = null;', 'const FIREBASE_CONFIG = ' + json.dumps(cfg, ensure_ascii=False) + ';', 'Firebase config')

    text = inline_styles(text, src.parent)
    i = text.index('<header class="top">')
    head, body = text[:i].rstrip(), text[i:].rstrip()

    return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Doelenboek: houd per kind bij welke Vlaamse minimumdoelen aan bod kwamen in huisonderwijs.">
<meta name="color-scheme" content="light">
<link rel="icon" href="{favicon_uri(design / 'favicon.svg')}">
{head}
</head>
<body>
{body}
</body>
</html>
"""


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    try:
        page = build(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else None)
    except BuildError as e:
        sys.exit(str(e))
    out = sys.argv[2]
    open(out, 'w', encoding='utf-8', newline='\n').write(page)
    print(f'wrote {out} ({len(page.encode("utf-8")):,} bytes)')
