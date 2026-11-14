"""Tests for the /admin/ build. Run: python -m unittest discover -s tests"""
import sys, tempfile, unittest
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

    def test_robots_keeps_crawlers_out_of_admin(self):
        self.assertIn('Disallow: /admin/', public.robots())


if __name__ == '__main__':
    unittest.main()
