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
    data = {'created': created, 'prs': [{'repo': r, 'number': n, 'key': f'{r}#{n}', 'title': f'PR {n}', 'identity': {'provider_host': 'github.com'}} for r, n in prs], **extra}
    if requested is not None:
        data['collection'] = {'requested_refs': requested}
    (d / 'review-data.json').write_text(json.dumps(data))
    return d


class ReusePackageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'sessions'
        self.root.mkdir()
        patch = mock.patch.object(c, 'SESSIONS', self.root)
        patch.start()
        self.addCleanup(patch.stop)
        env = mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT': '1'})
        env.start()
        self.addCleanup(env.stop)
        (self.root / 'latest').write_text('none')   # the pointer file is skipped, not read as a package
        package(self.root, '20261001-000000-aaaa', [('o/a', 1), ('o/b', 2)], ['o/a#1', 'o/b#2'], created='2026-10-01T00:00:00Z')
        self.same = package(self.root, '20261101-000000-bbbb', [('O/A', 1), ('o/b', 2)], ['O/A#1', 'o/b#2'])
        self.short = package(self.root, '20261102-000000-cccc', [('o/a', 1), ('o/b', 2)], ['o/a#1', 'o/b#2', 'o/c#3'])   # asked for 3, holds 2
        self.wider = package(self.root, '20261103-000000-dddd', [('o/a', 1), ('o/d', 4)], ['o/a#1', 'o/d#4'])
        package(self.root, 'demo-20261201', [('o/a', 1), ('o/b', 2)], ['o/a#1', 'o/b#2'], created='2026-12-01T00:00:00Z', demo=True)

    def test_the_same_prs_in_any_order_find_the_newest_package(self):
        found, _ = c.existing_sessions(['https://github.com/o/b/pull/2', 'o/a#1'])
        self.assertEqual(found, self.same)   # not the older copy, not the demo

    def test_a_package_matches_by_what_it_was_asked_for(self):
        self.assertEqual(c.existing_sessions(['o/a#1', 'o/b#2', 'o/c#3'])[0], self.short)   # its collection stopped early
        self.assertNotEqual(c.existing_sessions(['o/a#1', 'o/b#2'])[0], self.short)   # two PRs never reuse the three-PR package

    def test_similar_packages_say_what_they_hold_lack_and_add(self):
        found, similar = c.existing_sessions(['o/a#1', 'o/c#3'])
        self.assertIsNone(found)
        by = {s['id']: s for s in similar}
        self.assertEqual(by['20261103-000000-dddd']['held'], ['o/a#1'])
        self.assertEqual(by['20261103-000000-dddd']['missing'], ['o/c#3'])
        self.assertEqual(by['20261103-000000-dddd']['extra'], ['o/d#4'])
        self.assertEqual(by['20261102-000000-cccc']['held'], ['o/a#1'])   # o/c#3 was only asked for, never saved
        self.assertIn('o/c#3', by['20261102-000000-cccc']['missing'])
        self.assertEqual(by['20261103-000000-dddd']['extra'], ['o/d#4']); self.assertEqual(by['20261101-000000-bbbb']['held'], ['o/a#1'])   # shown as the request spells it

    def test_links_and_odd_names_are_never_matched(self):
        outside = Path(self.root.parent) / 'outside'
        package(outside.parent, 'outside', [('o/x', 9)], ['o/x#9'])
        (self.root / '20261104-000000-eeee').symlink_to(outside, target_is_directory=True)
        package(self.root, 'not a session', [('o/x', 9)], ['o/x#9'])
        self.assertEqual(c.existing_sessions(['o/x#9']), (None, []))

    def run_review(self, *extra, refresh_result=None, refresh_error=None):
        from cockpit import __main__ as m
        out = io.StringIO()
        refresh = mock.patch.object(c, 'refresh', return_value=refresh_result or {'session': self.same.name, 'warnings': ['story drifted']}, side_effect=refresh_error)
        collect = mock.patch.object(c, 'collect', return_value=('fresh', self.root / 'fresh'))
        with refresh as r, collect as k, mock.patch.object(m, 'SESSIONS', self.root), redirect_stdout(out):
            try:
                m.main(['review', *extra, '--collect-only'])
                code = 0
            except SystemExit as e:
                code = e.code
        return r, k, out.getvalue(), code

    def test_review_refreshes_the_exact_package_and_names_the_similar_ones(self):
        refresh, collect, out, code = self.run_review('o/b#2', 'O/A#1')
        self.assertEqual(code, 0)
        refresh.assert_called_once_with(self.same, refs=None, default_repo=None)
        collect.assert_not_called()
        self.assertIn(f'Updating work package {self.same.name}', out)
        self.assertIn('Note: work package 20261103-000000-dddd', out)   # a partial package is still named
        self.assertIn('warning: story drifted', out)
        self.assertEqual((self.root / 'latest').read_text(), self.same.name)

    def test_similar_packages_stop_the_review_until_the_user_decides(self):
        refresh, collect, out, code = self.run_review('o/a#1', 'o/c#3')
        self.assertEqual(code, 3)
        refresh.assert_not_called(); collect.assert_not_called()   # nothing collected
        self.assertIn('Similar work packages already exist', out)
        self.assertIn('20261103-000000-dddd', out); self.assertIn('lacks: o/c#3', out); self.assertIn('also has: o/d#4', out)
        self.assertIn('--into <id>', out); self.assertIn('--new', out)

    def test_into_changes_that_packages_scope(self):
        refresh, collect, out, code = self.run_review('o/a#1', 'o/c#3', '--into', '20261103-000000-dddd', refresh_result={'session': '20261103-000000-dddd', 'warnings': []})
        self.assertEqual(code, 0)
        refresh.assert_called_once_with(self.wider, refs=['o/a#1', 'o/c#3'], default_repo=None)
        collect.assert_not_called()
        self.assertIn('(new scope)', out)

    def test_new_collects_a_separate_package(self):
        refresh, collect, out, code = self.run_review('o/a#1', 'o/c#3', '--new')
        self.assertEqual(code, 0)
        refresh.assert_not_called()
        collect.assert_called_once()
        self.assertIn('Collected session fresh ->', out)

    def test_a_refresh_out_of_read_budget_leaves_the_package_as_it_was(self):
        from cockpit.adapters.managed import BudgetExceeded
        _, collect, _, code = self.run_review('o/b#2', 'o/a#1', refresh_error=BudgetExceeded('Managed read operation budget exhausted'))
        self.assertIn('was left as it was', str(code)); self.assertIn('--new', str(code))
        collect.assert_not_called()

    def test_packages_lists_saved_work_packages(self):
        from cockpit import __main__ as m, server
        out = io.StringIO()
        with mock.patch.object(server, 'SESSIONS', self.root), redirect_stdout(out):
            m.main(['packages'])
        ids = [p['id'] for p in json.loads(out.getvalue())]
        self.assertIn(self.same.name, ids); self.assertNotIn('demo-20261201', ids)


class ReapplyTests(unittest.TestCase):
    def test_a_refresh_turns_stale_decisions_into_warnings(self):
        from cockpit import enrich
        source = Path(enrich.__file__).read_text()
        self.assertIn('if enabled() and w and not reapply:', source)   # a fresh enrich still rejects them
        self.assertIn('"stale after refresh: {x}"', source)
        for name in ('managed_work.py', 'collect.py'):
            self.assertIn('reapply=True', (Path(enrich.__file__).parent / name).read_text())


if __name__ == '__main__':
    unittest.main()
