"""Build the standalone index.html from the app source, the design files and the goals.
Usage: build.py SRC.html OUT.html [FIREBASE_CONFIG.json]

- the stylesheets SRC links to (design/*.css, core.css) are inlined
- the shared scripts messages.js, message-zoom.js and images.js are inlined (in the app and the admin page)
- the animal drawings in design/animals/ become <symbol>s in the page
- the favicon comes from design/favicon.svg
- the built-in goals come from doelen/*.json (kleuter), doelen-lager/*.json (lager onderwijs) and
  doelen-secundair/*.json (secundair, 1ste graad A- and B-stroom)
- the font files in design/fonts/ are copied to fonts/ next to OUT.html
- the public pages, robots.txt, sitemap.xml and llms.txt are written next to OUT.html (see public.py)
- the admin page src/admin.html is built to admin/index.html next to OUT.html (see build_admin)"""
import sys, json, re, shutil
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import public  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOELEN_DIR = ROOT / 'doelen'
LAGER_DIR = ROOT / 'doelen-lager'
SEC_DIR = ROOT / 'doelen-secundair'
# Each goal belongs to one tier: KO for kleuter, L4/L6 for the goals at the end of the 4th/6th leerjaar.
# The lager codes carry their tier as a prefix (L4-2.1.1); the app shows the code without it.
LAGER_TIERS = ('L4', 'L6')
GOAL_FIELDS = {'code', 'category', 'categoryEn', 'description', 'descriptionEn'}
# A secundair goal can belong to both streams: codes holds its official number per stream (S1A, S1B), and
# extension the streams in which it is an uitbreidingsdoel. See doelen-secundair/README.md.
SEC_TIERS = ('S1A', 'S1B')
SEC_FIELDS = {'codes', 'extension', 'category', 'categoryEn', 'description', 'descriptionEn'}
ADMIN_SRC = ROOT / 'src' / 'admin.html'
RULES = ROOT / 'firestore.rules'


class BuildError(Exception):
    """A mistake in one of the input files, with a message that says where."""


def fail(where, msg):
    raise BuildError(f'{where}: {msg}')


def load_goals(subject_keys):
    """Read every doelen/*.json and doelen-lager/*.json file and return the goals in the shape the app expects.
    Stops with a readable message on the first mistake, so a hand edit can't break the app."""
    return (load_goal_dir(DOELEN_DIR, subject_keys, lager=False) + load_goal_dir(LAGER_DIR, subject_keys, lager=True)
            + load_secundair_dir(SEC_DIR, subject_keys))


def goal_files(doelen_dir, subject_keys):
    """(where, subject, doelen) for every *.json in doelen_dir, after the checks every goal file shares."""
    seen_subjects = {}
    for path in sorted(doelen_dir.glob('*.json')):
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
        yield where, subject, doc['doelen']


def load_goal_dir(doelen_dir, subject_keys, lager):
    goals = []
    for where, subject, doelen in goal_files(doelen_dir, subject_keys):
        codes = set()
        for n, g in enumerate(doelen, 1):
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
            tier, shown = 'KO', code
            if lager:
                tier, _, shown = code.partition('-')
                if tier not in LAGER_TIERS or not shown:
                    fail(where, f'{goal}: a lager code must start with {" or ".join(t + "-" for t in LAGER_TIERS)}')
            goals.append({'id': f'b-{subject}-{code}', 'subject': subject, 'tier': tier, **g, 'code': shown})
    return goals


def load_secundair_dir(doelen_dir, subject_keys):
    """The secundair goals. A goal worded the same in both streams is one goal with a code per stream, so a
    tick carries over when a child changes stream. tier is its first stream, tiers all of them."""
    goals = []
    for where, subject, doelen in goal_files(doelen_dir, subject_keys):
        codes = {t: set() for t in SEC_TIERS}
        for n, g in enumerate(doelen, 1):
            if not isinstance(g, dict):
                fail(where, f'goal {n} must be an object {{ ... }}')
            cs = g.get('codes')
            goal = f'goal {n}' + (f' ({", ".join(f"{k} {v}" for k, v in cs.items())})' if isinstance(cs, dict) else '')
            unknown = set(g) - SEC_FIELDS
            if unknown:
                fail(where, f'{goal} has unknown field(s) {", ".join(sorted(unknown))}; allowed: {", ".join(sorted(SEC_FIELDS))}')
            if not isinstance(cs, dict) or not cs or set(cs) - set(SEC_TIERS) or not all(isinstance(v, str) and v.strip() for v in cs.values()):
                fail(where, f'{goal}: "codes" must map {" and/or ".join(SEC_TIERS)} to the official number, e.g. {{"S1A": "02.03"}}')
            ext = g.get('extension', [])
            if not isinstance(ext, list) or set(ext) - set(cs):
                fail(where, f'{goal}: "extension" must list streams of its own "codes"')
            for k in ('category', 'categoryEn', 'description', 'descriptionEn'):
                if k in g and not isinstance(g[k], str):
                    fail(where, f'{goal}: "{k}" must be text in quotes')
            if not g.get('description', '').strip():
                fail(where, f'{goal} has no "description"')
            for t, c in cs.items():
                if c in codes[t]:
                    fail(where, f'code {t} {c} appears twice')
                codes[t].add(c)
            tiers = [t for t in SEC_TIERS if t in cs]
            x = {'id': f'b-{subject}-{tiers[0]}-{cs[tiers[0]]}', 'subject': subject, 'tier': tiers[0], 'tiers': tiers,
                 'code': cs[tiers[0]], 'codes': {t: cs[t] for t in tiers}}
            if ext:
                x['ext'] = [t for t in tiers if t in ext]
            x['category'] = g.get('category', '')
            for k in ('categoryEn', 'description', 'descriptionEn'):
                if g.get(k):
                    x[k] = g[k]
            goals.append(x)
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


def copy_fonts(src, out_dir):
    """Copy design/fonts/ (the .woff2 files and their licences) to OUT_DIR/fonts/, where the
    stylesheet's url("fonts/...") finds them once it is inlined into the page."""
    fonts = Path(src).resolve().parent / 'design' / 'fonts'
    dest = Path(out_dir) / 'fonts'
    dest.mkdir(exist_ok=True)
    for f in fonts.iterdir():
        if f.suffix in ('.woff2', '.txt'):
            shutil.copyfile(f, dest / f.name)


def favicon_uri(path):
    svg = re.sub(r'\s*\n\s*', '', path.read_text(encoding='utf-8')).replace('"', "'")
    return 'data:image/svg+xml,' + quote(svg, safe=" '=/:;,.-()")


def fill(text, needle, value, what):
    if text.count(needle) != 1:
        raise BuildError(f'{what} placeholder not found exactly once in the source')
    return text.replace(needle, value)


def subject_keys_of(text):
    """The subject keys, in the order of the app's SUBJECTS list."""
    s = text.index('const SUBJECTS = [')
    return re.findall(r"\{ key: '([A-Z]+)'", text[s:text.index('\n];', s)])


def goals_js(subject_keys):
    """The built-in goals as a JavaScript array literal, in the order of the app's subjects."""
    goals = sorted(load_goals(subject_keys), key=lambda g: subject_keys.index(g["subject"]))  # stable: keeps file order within a subject
    return json.dumps(goals, ensure_ascii=False, indent=1).replace('</', '<\\/')


def js_block(text, name):
    """The `const NAME = [ ... ];` list from the app source, word for word, so the admin page shares it."""
    start = text.index(f'const {name} = [')
    return text[start:text.index('\n];', start) + 3]


def inline_script(text, src_dir, name):
    """Replace <script src="NAME"></script> with the contents of src_dir/NAME in a <script> block."""
    path = Path(src_dir) / name
    js = path.read_text(encoding='utf-8').rstrip()
    if '</script' in js.lower():
        fail(path.name, 'may not contain "</script"')
    return fill(text, f'<script src="{name}"></script>', f'<script>\n{js}\n</script>', name)


def admin_uid(rules):
    """The uid in isAdmin() of firestore.rules, or None while it still holds the OWNER_UID placeholder."""
    m = re.search(r"request\.auth\.uid == '([^']*)'", Path(rules).read_text(encoding='utf-8'))
    uid = m.group(1) if m else ''
    return uid if re.fullmatch(r'[A-Za-z0-9]{10,128}', uid) and uid != 'OWNER_UID' else None


def build_admin(src, app_src, firebase_config=None, rules=RULES):
    """The /admin/ page as a string: src/admin.html with the app's subjects, tiers, goals and styles,
    admin-stats.js and the Firebase config inlined. Raises BuildError for a mistake in an input file."""
    src, app_src = Path(src).resolve(), Path(app_src).resolve()
    app_text = app_src.read_text(encoding='utf-8')
    text = src.read_text(encoding='utf-8')

    text = fill(text, 'const SUBJECTS = [];', js_block(app_text, 'SUBJECTS'), 'subjects')
    text = fill(text, 'const TIERS = [];', js_block(app_text, 'TIERS'), 'tiers')
    text = fill(text, 'const BUILTIN_GOALS = [];', 'const BUILTIN_GOALS = ' + goals_js(subject_keys_of(app_text)) + ';', 'goals')
    uid = admin_uid(rules)
    if uid:
        text = fill(text, 'const ADMIN_UID = null;', 'const ADMIN_UID = ' + json.dumps(uid) + ';', 'admin uid')
    if firebase_config:
        cfg = json.loads(Path(firebase_config).read_text(encoding='utf-8'))
        text = fill(text, 'const FIREBASE_CONFIG = null;', 'const FIREBASE_CONFIG = ' + json.dumps(cfg, ensure_ascii=False) + ';', 'Firebase config')

    for name in ('admin-stats.js', 'messages.js', 'message-zoom.js', 'images.js'):
        text = inline_script(text, src.parent, name)

    # the page lives one folder down, at admin/index.html; the fonts are at fonts/ in the site root
    text = inline_styles(text, src.parent).replace('url("fonts/', 'url("../fonts/')
    i = text.index('<header class="top">')
    head, body = text[:i].rstrip(), text[i:].rstrip()

    return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="{favicon_uri(src.parent / 'design' / 'favicon.svg')}">
{head}
</head>
<body>
{body}
</body>
</html>
"""


def build(src, firebase_config=None, rules=RULES):
    """The complete page as a string. Raises BuildError for a mistake in an input file."""
    src = Path(src).resolve()
    design = src.parent / 'design'
    text = src.read_text(encoding='utf-8')

    subject_keys = subject_keys_of(text)
    text = fill(text, 'const BUILTIN_GOALS = [];', 'const BUILTIN_GOALS = ' + goals_js(subject_keys) + ';', 'goals')

    pairs, sprite = animal_symbols(design / 'animals')
    text = fill(text, 'const ANIMAL_LIST = [];', 'const ANIMAL_LIST = ' + json.dumps(pairs, ensure_ascii=False) + ';', 'animal list')
    text = fill(text, '<!-- animal drawings: filled in by tools/build.py -->', sprite, 'animal drawings')

    if firebase_config:
        cfg = json.loads(Path(firebase_config).read_text(encoding='utf-8'))
        text = fill(text, 'const FIREBASE_CONFIG = null;', 'const FIREBASE_CONFIG = ' + json.dumps(cfg, ensure_ascii=False) + ';', 'Firebase config')
    uid = admin_uid(rules)
    if uid:   # the owner's account gets an Admin button in the header
        text = fill(text, 'const ADMIN_UID = null;', 'const ADMIN_UID = ' + json.dumps(uid) + ';', 'admin uid')

    for name in ('messages.js', 'message-zoom.js', 'images.js'):   # shared with the admin page
        text = inline_script(text, src.parent, name)
    text = inline_styles(text, src.parent)
    text = fill(text, '<main id="main">', public.app_noscript() + '\n<main id="main">', 'main')
    i = text.index('<header class="top">')
    head, body = text[:i].rstrip(), text[i:].rstrip()

    return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light">
{public.app_head(public.load_subjects(DOELEN_DIR, subject_keys))}
<link rel="icon" href="{favicon_uri(design / 'favicon.svg')}">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
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
    config = sys.argv[3] if len(sys.argv) > 3 else None
    try:
        page = build(sys.argv[1], config)
        admin = build_admin(ADMIN_SRC, sys.argv[1], config)
    except BuildError as e:
        sys.exit(str(e))
    out = sys.argv[2]
    open(out, 'w', encoding='utf-8', newline='\n').write(page)
    out_dir = Path(out).resolve().parent
    copy_fonts(sys.argv[1], out_dir)
    print(f'wrote {out} ({len(page.encode("utf-8")):,} bytes)')
    (out_dir / 'admin').mkdir(exist_ok=True)
    (out_dir / 'admin' / 'index.html').write_text(admin, encoding='utf-8', newline='\n')
    print(f'wrote admin/index.html ({len(admin.encode("utf-8")):,} bytes)')
    if not admin_uid(RULES):
        print('note: firestore.rules has no admin uid yet (OWNER_UID), so /admin/ shows "Geen toegang" to everyone', file=sys.stderr)
    src = Path(sys.argv[1]).resolve()
    written = public.write_site(out_dir, src.parent / 'design', DOELEN_DIR, subject_keys_of(src.read_text(encoding='utf-8')))
    print(f'wrote {len(written)} public files (pages, robots.txt, sitemap.xml, llms.txt, ...)')
