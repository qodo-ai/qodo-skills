import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from cockpit import collect as c


def package(root, name, prs, requested=None, created='2026-11-01T00:00:00Z', **extra):
    d = root / name
    d.mkdir()
    data = {'created': created, 'prs': [{'repo': r, 'number': n, 'key': f'{r}#{n}', 'identity': {'provider_host': 'github.com'}} for r, n in prs], **extra}
    if requested is not None:
        data['collection'] = {'requested_refs': requested}
    (d / 'review-data.json').write_text(json.dumps(data))
    return d


class ReusePackageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        patch = mock.patch.object(c, 'SESSIONS', self.root)
        patch.start()
        self.addCleanup(patch.stop)
        env = mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT': '1'})
        env.start()
        self.addCleanup(env.stop)
        (self.root / 'latest').write_text('none')   # the pointer file is skipped, not read as a package
        package(self.root, 'old', [('o/a', 1), ('o/b', 2)], ['o/a#1', 'o/b#2'], created='2026-10-01T00:00:00Z')
        self.same = package(self.root, 'same', [('o/a', 1), ('o/b', 2)], ['o/a#1', 'o/b#2'])
        self.short = package(self.root, 'short', [('o/a', 1), ('o/b', 2)], ['o/a#1', 'o/b#2', 'o/c#3'])
        package(self.root, 'demo', [('o/a', 1), ('o/b', 2)], ['o/a#1', 'o/b#2'], created='2026-12-01T00:00:00Z', demo=True)

    def test_the_same_prs_in_any_order_find_the_newest_package(self):
        found, _ = c.existing_sessions(['https://github.com/O/B/pull/2', 'o/a#1'])
        self.assertEqual(found, self.same)   # not the older copy, not the demo

    def test_a_package_matches_by_what_it_was_asked_for(self):
        self.assertEqual(c.existing_sessions(['o/a#1', 'o/b#2', 'o/c#3'])[0], self.short)   # its collection stopped early
        self.assertNotEqual(c.existing_sessions(['o/a#1', 'o/b#2'])[0], self.short)   # two PRs never reuse the three-PR package

    def test_a_partial_overlap_is_reported_not_reused(self):
        found, partial = c.existing_sessions(['o/a#1'])
        self.assertIsNone(found)
        self.assertIn(('same', 1), partial)

    def run_review(self, *extra):
        from cockpit import __main__ as m
        out = io.StringIO()
        with mock.patch.object(c, 'refresh', return_value={'session': 'same', 'warnings': ['story drifted']}) as refresh, \
             mock.patch.object(c, 'collect', return_value=('fresh', self.root / 'fresh')) as collect, redirect_stdout(out):
            m.main(['review', 'o/b#2', 'o/a#1', '--collect-only', *extra])
        return refresh, collect, out.getvalue()

    def test_review_refreshes_the_existing_package_instead_of_duplicating_it(self):
        refresh, collect, out = self.run_review()
        refresh.assert_called_once_with(self.same)
        collect.assert_not_called()
        self.assertIn('Work package same already has these PRs', out)
        self.assertIn('warning: story drifted', out)
        self.assertIn('Collected session same ->', out)
        self.assertEqual((self.root / 'latest').read_text(), 'same')

    def test_new_collects_a_separate_package(self):
        refresh, collect, out = self.run_review('--new')
        refresh.assert_not_called()
        collect.assert_called_once()
        self.assertIn('Collected session fresh ->', out)


if __name__ == '__main__':
    unittest.main()
