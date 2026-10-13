"""Wrap the artifact page (head-less fragment) into a complete standalone index.html,
filling in the built-in goals from doelen/*.json.
Usage: build.py SRC.html OUT.html [FIREBASE_CONFIG.json]"""
import sys, json, re
from pathlib import Path

DOELEN_DIR = Path(__file__).resolve().parent.parent / 'doelen'
GOAL_FIELDS = {'code', 'category', 'categoryEn', 'description', 'descriptionEn'}


def load_goals(subject_keys):
    """Read every doelen/*.json file and return the goals in the shape the app expects.
    Stops with a readable message on the first mistake, so a hand edit can't break the app."""
    goals, seen_subjects = [], {}
    for path in sorted(DOELEN_DIR.glob('*.json')):
        def fail(msg):
            sys.exit(f'{path.relative_to(DOELEN_DIR.parent)}: {msg}')
        try:
            doc = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            fail(f'not valid JSON (line {e.lineno}, column {e.colno}: {e.msg})')
        subject = doc.get('subject') if isinstance(doc, dict) else None
        if subject not in subject_keys:
            fail(f'"subject" must be one of {", ".join(subject_keys)}')
        if subject in seen_subjects:
            fail(f'subject {subject} is already used by {seen_subjects[subject]}')
        seen_subjects[subject] = path.name
        if not isinstance(doc.get('doelen'), list):
            fail('"doelen" must be a list')
        codes = set()
        for n, g in enumerate(doc['doelen'], 1):
            where = f'goal {n}' + (f' ({g.get("code")})' if isinstance(g, dict) and g.get('code') else '')
            if not isinstance(g, dict):
                fail(f'{where} must be an object {{ ... }}')
            unknown = set(g) - GOAL_FIELDS
            if unknown:
                fail(f'{where} has unknown field(s) {", ".join(sorted(unknown))}; allowed: {", ".join(sorted(GOAL_FIELDS))}')
            for k, v in g.items():
                if not isinstance(v, str):
                    fail(f'{where}: "{k}" must be text in quotes')
            code = g.get('code', '').strip()
            if not code:
                fail(f'{where} has no "code"')
            if not g.get('description', '').strip():
                fail(f'{where} has no "description"')
            if code in codes:
                fail(f'code {code} appears twice')
            codes.add(code)
            goals.append({'id': f'b-{subject}-{code}', 'subject': subject, **{k: v.strip() if k == 'code' else v for k, v in g.items()}})
    return goals


src, out = sys.argv[1], sys.argv[2]
text = open(src, encoding='utf-8').read()

s = text.index('const SUBJECTS = [')
subject_keys = re.findall(r"\{ key: '([A-Z]+)'", text[s:text.index('\n];', s)])
goals = sorted(load_goals(subject_keys), key=lambda g: subject_keys.index(g["subject"]))  # stable: keeps file order within a subject
needle = 'const BUILTIN_GOALS = [];'
assert text.count(needle) == 1, 'goals placeholder not found exactly once'
goals_js = json.dumps(goals, ensure_ascii=False, indent=1).replace('</', '<\\/')
text = text.replace(needle, 'const BUILTIN_GOALS = ' + goals_js + ';')

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
