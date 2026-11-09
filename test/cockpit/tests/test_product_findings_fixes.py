"""Current product regressions reported by Qodo, through collection, enrichment and export."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from cockpit import enrich, export, risk
from cockpit.adapters import qodo_local
from cockpit.adapters.managed import Client
from tests.test_product import HEAD, ID, REV, fixture, page
from tests import test_product_enrich_refresh as refresh_tests


class ProductFindingFixTests(unittest.TestCase):
    def test_malformed_provider_rows_preserve_prior_pages_and_report_visible_gaps(self):
        for kind in ('files', 'comments', 'reviews', 'checks', 'annotations', 'history'):
            for bad in (None, [], 'bad', 42):
                with self.subTest(kind=kind, bad=bad):
                    first = {'filename': 'a.py', 'id': 1}
                    pages = [page([first], complete=False, next_cursor='signed-next'), page([bad])]
                    with mock.patch.object(Client, 'read', side_effect=pages):
                        result = Client().pages(ID, kind, 1, REV)
                    self.assertEqual(result['items'], [first])
                    self.assertFalse(result['complete'])
                    self.assertEqual(result['status'], 'malformed')
                    self.assertEqual(result['rejected_page'], pages[1])
                    self.assertEqual(result['next_cursor'], 'signed-next')

    def test_missing_file_path_cannot_be_presented_as_complete(self):
        for row in ({'additions': 1}, {'path': ''}, {'filename': 3}, None):
            with self.subTest(row=row):
                def read(group, tool, **args):
                    if tool == 'read-review-data' and args['kind'] == 'files':
                        return page([row])
                    return fixture(group, tool, **args)
                with mock.patch.object(Client, 'read', side_effect=read):
                    pr = Client().change('org/repo', 1)
                self.assertEqual(pr['files'], [])
                self.assertFalse(pr['files_complete'])
                evidence = pr['read_evidence']['sections']['files']
                self.assertEqual(evidence['status'], 'malformed')
                self.assertEqual(evidence['rejected_page']['items'], [row])

    def test_reopened_id_only_bucket_overrides_old_implementation_status_without_rewriting_source(self):
        pr = {'key': 'org/repo#1', 'repo': 'org/repo', 'head': 'feature', 'head_sha': HEAD, 'files': []}
        for bucket in ('still_open', 'introduced'):
            first = {'local_review_id': 'original', 'commit': HEAD, 'result': {
                'findings': [{'id': 'f', 'title': 'Concern', 'attribution_status': 'full_implementation'}],
                'finding_state': {'complete': True, 'resolved': ['f']}}}
            second = {'local_review_id': 'next', 'commit': HEAD, 'result': {
                'findings': [], 'finding_state': {'complete': True, bucket: ['f']}}}
            before = json.dumps([first, second], sort_keys=True)
            with self.subTest(bucket=bucket), mock.patch.object(qodo_local, 'fetch', return_value=[first, second]):
                finding = qodo_local.collect(pr, {})[0]
            self.assertEqual(finding.get('status', 'open'), 'open')
            self.assertEqual(finding['title'], 'Concern')
            self.assertEqual(json.dumps([first, second], sort_keys=True), before)

    def test_titleless_story_and_inline_agent_assessment_survive_cli_refresh_and_full_export(self):
        helper = refresh_tests.ProductEnrichRefreshTests()
        with helper.session() as (root, sd, cfg, read):
            payload = {'story': [
                {'kind': 'notice', 'items': [{'title': 'Gap', 'text': 'Evidence unavailable', 'tone': 'gap'}]},
                {'kind': 'callout', 'lede': 'Context', 'text': 'Valid beat without a title'}],
                'prs': {'org/repo#1': {'findings': [{'title': 'Agent concern', 'body': 'Keep rationale',
                    'severity': 'low', 'stance': 'partial', 'why': 'Specific assessment'}]}}}
            source = root / 'authored.json'; source.write_text(json.dumps(payload))
            helper.run_cli(['enrich', str(source), '--session', sd.name])
            helper.run_cli(['refresh', '--session', sd.name])
            saved = json.loads((sd / 'review-data.json').read_text())
            finding = next(f for f in saved['prs'][0]['findings'] if f['source'] == 'agent')
            self.assertEqual((finding['stance'], finding['stance_why']), ('partial', 'Specific assessment'))
            with mock.patch.object(export, 'session_config', return_value=cfg):
                html = export.build(sd)
            self.assertIn('<title>PR review · PR review</title>', html)
            self.assertIn('Specific assessment', html)
            self.assertIn('Valid beat without a title', html)

    def test_risk_citations_reject_invalid_ranges_and_disclose_unverified_line_numbers(self):
        for lines in ('not-a-line', '-1', '0', '3-1', '1:2', [], True):
            raw = {'radius': {'level': 'small', 'why': 'Authored evidence', 'ev': [{'path': 'a.py', 'lines': lines}]}}
            factors, warnings = risk.normalize_factors(raw, {'a.py'})
            self.assertNotIn('lines', factors['radius']['ev'][0])
            if lines:
                self.assertTrue(any('invalid line reference' in w for w in warnings))
        raw = {'radius': {'level': 'small', 'why': 'Authored evidence', 'ev': [{'path': 'a.py', 'lines': '2-5'}]}}
        factors, warnings = risk.normalize_factors(raw, {'a.py'})
        self.assertEqual(factors['radius']['ev'][0]['lines'], '2-5')
        self.assertFalse(factors['radius']['ev'][0]['lines_verified'])
        self.assertTrue(any('not source-verified' in w for w in warnings))

    def test_direct_packaged_cli_cannot_omit_the_managed_local_only_profile(self):
        from contextlib import redirect_stdout
        import io
        from cockpit import __main__ as cli, collect, product, server, util
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT': '0'}):
            def collected(*args):
                self.assertTrue(product.enabled())
                with self.assertRaisesRegex(RuntimeError, 'gh is unavailable'):
                    util.gh(['api', 'fixture'])
                return 's', Path(tmp)
            with mock.patch.object(collect, 'collect', side_effect=collected) as read, redirect_stdout(io.StringIO()):
                cli.main(['review', 'org/repo#1', '--collect-only'])
                read.assert_called_once()

    def test_launcher_preserves_external_legacy_pointer_and_explicit_home_aliases(self):
        import importlib.util
        script = Path(__file__).resolve().parents[3] / 'skills/qodo-review-cockpit/scripts/launch.py'
        spec = importlib.util.spec_from_file_location('cockpit_launch_fixture', script)
        launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_HOME': '', 'PR_COCKPIT_HOME': ''}):
            root = Path(tmp); runtime = root / 'runtime'; runtime.mkdir()
            external = root / 'existing-reviews'
            (runtime / 'config.local.json').write_text(json.dumps({'home': str(external)}))
            with mock.patch.object(launcher, 'RUNTIME', runtime):
                self.assertEqual(launcher.state_home(), external.resolve())
                with mock.patch.dict(os.environ, {'PR_COCKPIT_HOME': str(root / 'alias')}):
                    self.assertEqual(launcher.state_home(), (root / 'alias').resolve())
                (runtime / 'config.local.json').write_text('{malformed')
                with self.assertRaisesRegex(SystemExit, 'inspect the existing'):
                    launcher.state_home()
