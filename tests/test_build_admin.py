"""Tests for the /admin/ build. Run: python -m unittest discover -s tests"""
import re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import build, public  # noqa: E402

APP = ROOT / 'src' / 'doelenboek.html'


def rules_with(uid):
    f = tempfile.NamedTemporaryFile('w', suffix='.rules', delete=False, encoding='utf-8')
    f.write(f"function isAdmin() {{ return request.auth != null && request.auth.uid == '{uid}'; }}\n")
    f.close()
    return Path(f.name)


class BuildAdmin(unittest.TestCase):
    def test_fills_every_placeholder_and_inlines_stats(self):
        page = build.build_admin(build.ADMIN_SRC, APP, None, rules_with('AbCdEf1234567890xyz'))
        self.assertIn('<meta name="robots" content="noindex, nofollow">', page)
        self.assertIn('const AdminStats = ', page)
        self.assertIn("{ key: 'NL'", page)
        self.assertIn("badge: { nl: 'Lager LJ 1-4'", page)
        self.assertIn('"id": "b-NL-', page)
        self.assertIn('const ADMIN_UID = "AbCdEf1234567890xyz";', page)
        for left in ('const SUBJECTS = [];', 'const TIERS = [];', 'const BUILTIN_GOALS = [];', '<script src="admin-stats.js">', '<link rel="stylesheet"'):
            self.assertNotIn(left, page)

    def test_tiers_find_every_name_they_use(self):
        # TIERS refers to other constants (subj: SEC_SUBJ); the admin page must define them too, or it stops loading
        page = build.build_admin(build.ADMIN_SRC, APP, None, rules_with('OWNER_UID'))
        tiers = build.js_block(page, 'TIERS')
        for name in set(re.findall(r'subj: ([A-Z_]+)', tiers)):
            self.assertIn(f'const {name} = ', page)

    def test_fonts_point_one_folder_up(self):
        page = build.build_admin(build.ADMIN_SRC, APP, None, rules_with('OWNER_UID'))
        self.assertIn('url("../fonts/', page)
        self.assertNotIn('url("fonts/', page)

    def test_placeholder_uid_means_no_admin(self):
        page = build.build_admin(build.ADMIN_SRC, APP, None, rules_with('OWNER_UID'))
        self.assertIn('const ADMIN_UID = null;', page)

    def test_firebase_config_is_filled_in(self):
        page = build.build_admin(build.ADMIN_SRC, APP, ROOT / 'firebase-config.json', rules_with('OWNER_UID'))
        self.assertIn('"projectId": "doelenboek-e78ca"', page)

    def test_app_gets_the_admin_uid_for_its_admin_button(self):
        page = build.build(APP, None, rules_with('AbCdEf1234567890xyz'))
        self.assertIn('const ADMIN_UID = "AbCdEf1234567890xyz";', page)
        self.assertIn('id="admin-link"', page)

    def test_robots_keeps_crawlers_out_of_admin(self):
        self.assertIn('Disallow: /admin/', public.robots())


class SharedScripts(unittest.TestCase):
    def test_both_pages_inline_messages_and_images(self):
        app = build.build(APP, None, rules_with('OWNER_UID'))
        admin = build.build_admin(build.ADMIN_SRC, APP, None, rules_with('OWNER_UID'))
        for page in (app, admin):
            self.assertIn('const Messages = ', page)
            self.assertIn('const Images = ', page)
            self.assertIn('const MessageZoom = ', page)   # image enlarging: the app popup and the admin preview
            self.assertNotIn('<script src="message-zoom.js">', page)
            self.assertNotIn('<script src="messages.js">', page)
            self.assertNotIn('<script src="images.js">', page)

    def test_script_with_closing_tag_is_refused(self):
        d = Path(tempfile.mkdtemp())
        (d / 'x.js').write_text('const a = "</script>";', encoding='utf-8')
        with self.assertRaises(build.BuildError):
            build.inline_script('<script src="x.js"></script>', d, 'x.js')


class BuiltPagesParse(unittest.TestCase):
    """Every inline <script> in the built app and admin page must be valid JavaScript (checked with node --check)."""
    def check(self, page):
        for i, js in enumerate(re.findall(r'<script>(.*?)</script>', page, re.S)):
            with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
                f.write(js)
            r = subprocess.run(['node', '--check', f.name], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f'script {i}: {r.stderr[:400]}')

    def test_app_scripts_parse(self):
        self.check(build.build(APP, ROOT / 'firebase-config.json'))

    def test_admin_scripts_parse(self):
        self.check(build.build_admin(build.ADMIN_SRC, APP, ROOT / 'firebase-config.json'))


class Vendor(unittest.TestCase):
    """vendor/ (pdfmake for the reports) is copied as-is next to the built page."""
    def test_copies_pdfmake(self):
        out = Path(tempfile.mkdtemp())
        build.copy_vendor(out)
        for name in ('pdfmake.min.js', 'vfs_fonts.js', 'LICENSE'):
            self.assertEqual((out / 'vendor' / 'pdfmake' / name).read_bytes(),
                             (ROOT / 'vendor' / 'pdfmake' / name).read_bytes())

    def test_copy_replaces_old_files(self):
        out = Path(tempfile.mkdtemp())
        (out / 'vendor' / 'old').mkdir(parents=True)
        build.copy_vendor(out)
        self.assertFalse((out / 'vendor' / 'old').exists())

if __name__ == '__main__':
    unittest.main()


class SecundairGoals(unittest.TestCase):
    """doelen-secundair/: a goal worded the same in both streams is one goal in both (its tick carries over)."""

    def goals(self):
        keys = build.subject_keys_of(APP.read_text(encoding='utf-8'))
        return [g for g in build.load_goals(keys) if g['tier'] in build.SEC_TIERS]

    def test_counts_per_stream(self):
        goals = self.goals()
        self.assertEqual(sum('S1A' in g['tiers'] for g in goals), 126)
        self.assertEqual(sum('S1B' in g['tiers'] for g in goals), 103)
        self.assertEqual(sum(len(g['tiers']) == 2 for g in goals), 66)
        self.assertTrue(all(g.get('descriptionEn') for g in goals))

    def test_shared_goal_has_a_code_per_stream(self):
        g = next(g for g in self.goals() if g['codes'] == {'S1A': '03.08', 'S1B': '03.07'})
        self.assertEqual((g['id'], g['tier'], g['tiers']), ('b-FR-S1A-03.08', 'S1A', ['S1A', 'S1B']))

    def test_extension_only_in_its_own_stream(self):
        g = next(g for g in self.goals() if g['codes'].get('S1B') == 'UD02.05')
        self.assertEqual((g['codes']['S1A'], g['ext']), ('02.05', ['S1B']))

    def test_rejects_extension_outside_its_codes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            Path(d, 'x.json').write_text('{"subject": "NL", "doelen": [{"codes": {"S1A": "01"}, "extension": ["S1B"], "description": "x"}]}', encoding='utf-8')
            with self.assertRaisesRegex(build.BuildError, 'extension'):
                build.load_secundair_dir(Path(d), ['NL'])


class PageScripts(unittest.TestCase):
    """Every inline script of the built app and admin page must parse (a stray quote in a text breaks the whole app)."""

    def test_inline_scripts_parse(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is not installed')
        for name, page in (('app', build.build(APP)), ('admin', build.build_admin(build.ADMIN_SRC, APP, None))):
            for n, code in enumerate(re.findall(r'<script>([\s\S]*?)</script>', page)):
                r = subprocess.run([node, '-e', 'new Function(require("fs").readFileSync(0, "utf8"))'], input=code, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(r.returncode, 0, f'{name} script {n}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "?"}')
