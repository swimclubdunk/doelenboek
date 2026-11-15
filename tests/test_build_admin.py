"""Tests for the /admin/ build. Run: python -m unittest discover -s tests"""
import re, subprocess, sys, tempfile, unittest
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


if __name__ == '__main__':
    unittest.main()
