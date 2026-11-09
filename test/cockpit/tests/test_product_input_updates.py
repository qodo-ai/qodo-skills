"""Public regressions for saved enrichment, line targets and incomplete evidence."""
import contextlib
import copy
import io
import json
import subprocess
import unittest
from unittest import mock

from cockpit import enrich, util, view
from cockpit.adapters import qodo_cli, qodo_findings
from cockpit.adapters.managed import Client
from tests import test_product_enrich_refresh as helpers
from tests.test_product import HEAD, fixture, page

KEY = helpers.KEY


class ProductInputUpdateTests(unittest.TestCase):
    def test_invalid_rollback_preserves_saved_plan_and_authored_input(self):
        helper = helpers.ProductEnrichRefreshTests()
        with helper.session() as (root, sd, cfg, read):
            cfg['memory'].update(enabled=True, auto_commit=False, amr=str(root/'amr'), okf=str(root/'okf'))
            initial = {'rollback': {'steps': ['Revert the change'], 'verify': ['Run checks']}}
            with mock.patch.object(enrich, 'session_config', return_value=cfg):
                enrich.enrich(sd, initial)
                before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
                for invalid in ('bad', [], {'steps': 'bad'}, {'steps': [False]}, {'one_way': ['bad']}):
                    with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'Invalid rollback'):
                        enrich.enrich(sd, {'rollback': invalid, 'knowledge': [{'title': 'Must not be written'}]})
                    self.assertEqual({p: p.read_bytes() for p in root.rglob('*') if p.is_file()}, before)
                helper.run_cli(['refresh', '--session', 's'])
                self.assertEqual(json.loads((sd/'review-data.json').read_text())['rollback']['steps'][0]['text'], 'Revert the change')

    def test_invalid_decisions_preserve_choices_but_explicit_empty_list_clears(self):
        helper = helpers.ProductEnrichRefreshTests()
        with helper.session() as (root, sd, cfg, read):
            enrich.enrich(sd, helper.authored())
            before = {p: p.read_bytes() for p in (sd/'review-data.json', sd/'enrich.json')}
            for invalid in ('bad', {}, [False], [{'text': 'Missing plan', 'status': 'missing'}]):
                with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, 'Invalid decisions'):
                    enrich.enrich(sd, {'prs': {KEY: {'decisions': invalid}}})
                self.assertEqual({p: p.read_bytes() for p in before}, before)
            helper.run_cli(['refresh', '--session', 's'])
            self.assertEqual(json.loads((sd/'review-data.json').read_text())['prs'][0]['decisions'][0]['id'], 'd')
            enrich.enrich(sd, {'prs': {KEY: {'decisions': []}}})
            self.assertEqual(json.loads((sd/'review-data.json').read_text())['prs'][0]['decisions'], [])

    def test_note_and_mark_reject_invalid_line_targets_without_appending_events(self):
        helper = helpers.ProductEnrichRefreshTests()
        with helper.session() as (root, sd, cfg, read):
            events_file = sd/'events.jsonl'
            original = events_file.read_bytes() if events_file.exists() else b''
            for command in ('note', 'mark'):
                for flags in (['--path', 'a.py', '--line', '0'], ['--path', 'a.py', '--line', '-1'], ['--line', '1']):
                    with self.subTest(command=command, flags=flags), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                        helper.run_cli([command, 'Review', '--session', 's', '--pr', KEY, *flags])
                    self.assertEqual(error.exception.code, 2)
                    self.assertEqual(events_file.read_bytes() if events_file.exists() else b'', original)
                helper.run_cli([command, 'Review', '--session', 's', '--pr', KEY, '--path', 'a.py', '--line', '1'])
                events = [json.loads(x) for x in (sd/'events.jsonl').read_text().splitlines()]
                self.assertEqual(events[-1]['target']['kind'], 'line')
                self.assertEqual(events[-1]['target']['id'], 'a.py:1')
                events_file.write_bytes(original)

    def test_unobserved_story_range_warns_and_renders_explicit_gap(self):
        helper = helpers.ProductEnrichRefreshTests()
        with helper.session() as (root, sd, cfg, read):
            story = [{'id': 'unseen', 'kind': 'code', 'title': 'Unseen', 'path': 'a.py', 'from': 999, 'to': 1000},
                     {'id': 'seen', 'kind': 'code', 'title': 'Seen', 'path': 'a.py', 'from': 1, 'to': 1}]
            result = enrich.enrich(sd, {'prs': {KEY: {'story': story}}})
            self.assertTrue(any('no observed code in this range' in w for w in result['warnings']))
            data = json.loads((sd/'review-data.json').read_text());pr = view._pr_view(data['prs'][0])
            self.assertEqual(data['prs'][0]['story'][0]['from'], 999)
            kit = (util.ROOT/'app/styles/kit.js').read_text()
            code = kit[kit.index('  const codeHtml ='):kit.index('  /* mermaid:')]
            setup = 'const esc=String,langOf=()=>"",hlText=String;'
            blocks = [pr['code']['beat:unseen'], pr['code']['beat:seen']]
            output = subprocess.run(['node'], input=setup+code+';console.log(JSON.stringify('+json.dumps(blocks)+'.map(b=>codeHtml(b))));', text=True, capture_output=True)
            self.assertEqual(output.returncode, 0, output.stderr)
            gap, observed = json.loads(output.stdout)
            self.assertIn('No observed code in this range.', gap)
            self.assertIn('hello', observed)
            self.assertNotIn('No observed code', observed)

    def test_native_old_comment_coordinate_is_not_a_current_anchor(self):
        helper = helpers.ProductEnrichRefreshTests()
        uid = 'd69d7061-b8c7-403f-92aa-d55b2a6f30f7'
        comment = {'id': 77, 'actor': {'login': 'qodo-code-review[bot]'}, 'path': 'a.py', 'line': None,
                   'original_line': 1, 'side': 'RIGHT', 'original_commit_id': HEAD,
                   'url': 'https://github.com/org/repo/pull/1#discussion_r77',
                   'body': '1. Concern\n[View finding](https://portal.test/findings/'+uid+')\n<img src="https://img.shields.io/badge/High-ff0000">\nDetails'}
        def read(group, tool, **args):
            if tool == 'read-review-data' and args['kind'] == 'inline_comments':
                return page([copy.deepcopy(comment)])
            return fixture(group, tool, **args)
        with helper.session() as (root, sd, cfg, default):
            with mock.patch.object(Client, 'read', side_effect=read):
                pr = Client().change('org/repo', 1)
            self.assertIsNone(pr['_raw_comments'][0]['line'])
            with mock.patch.object(qodo_cli, 'fetch', return_value=None):
                findings = qodo_findings(pr, cfg)
            self.assertEqual(len(findings), 1)
            public = view._pr_view({**pr, 'findings': findings})['findings'][0]
            self.assertFalse(public['current_anchor']);self.assertIsNone(public['line']);self.assertIsNone(public['path'])
            self.assertEqual(public['source_location']['line'], 1)
            self.assertNotIn(public.get('status'), ('outdated', 'resolved'))
            authoritative = qodo_cli.to_finding(pr, {'id': uid, 'title': 'Concern', 'git_sha': HEAD,
                                                    'location': {'file_path': 'a.py', 'start_line': 1, 'side': 'RIGHT'}})
            with mock.patch.object(qodo_cli, 'collect', return_value=[authoritative]):
                structured = qodo_findings(pr, cfg)
            self.assertTrue(structured[0]['current_anchor']);self.assertEqual(structured[0]['line'], 1)
            self.assertEqual(structured[0]['url'], comment['url'])
