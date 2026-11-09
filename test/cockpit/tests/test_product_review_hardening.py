"""Integrated regressions for the final assembled review's supported defects."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from cockpit import collect, distill, export, memory, product, server, util, view
from cockpit.adapters import scanners
from cockpit.adapters.managed import Client
from tests import test_product_enrich_refresh as enrichment_tests
from tests import test_product_access_activity as http_tests
from tests.test_product import fixture, page


class ProductReviewHardeningTests(unittest.TestCase):
    def test_scanner_secret_is_redacted_in_saved_data_raw_evidence_code_and_export(self):
        marker = 'TEST-ONLY-SCANNER-VALUE'
        body = ('Upwind Secrets Scan\n<details><summary>High</summary>\n'
                '| File | Line | Type | Value |\n| --- | --- | --- | --- |\n'
                '| a.py | 1 | Token | `' + marker + '` |\n</details>')
        comment = {'body': body, 'author': 'scanner[bot]', 'url': 'https://forge.test/report'}
        helper = enrichment_tests.ProductEnrichRefreshTests()
        with helper.session() as (root, sd, cfg, read):
            pr = Client().change('org/repo', 1)
            pr['_raw_comments'] = [comment]
            pr['findings'] = scanners.upwind(pr, [comment], {})
            self.assertEqual(len(pr['findings']), 1)
            pr['read_evidence']['sections']['comments'] = {'items': [comment], 'pages': [page([comment])], 'complete': True}
            pr['files'][0]['hunks'][0]['lines'][0][3] = marker
            collect.build([pr], cfg, demo=True, session='s', dest=sd)
            stored = (sd / 'review-data.json').read_text()
            self.assertNotIn(marker, stored)
            saved = json.loads(stored)
            self.assertTrue(saved['source_redactions']['scanner_secret_values'])
            self.assertEqual(saved['prs'][0]['files'][0]['path'], 'a.py')
            with mock.patch.object(export, 'session_config', return_value=cfg):
                self.assertNotIn(marker, export.build(sd))
            legacy = copy.deepcopy(saved)
            legacy['prs'][0]['findings'][0]['body'] = 'Upwind flags a value of type Token ('+marker+'). A pushed secret stays in git history.'
            self.assertNotIn(marker, json.dumps(product.project_data(legacy)))
            (sd/'review-data.json').write_text(json.dumps(legacy))
            events=[{'type':'note','pr':'org/repo#1','text':'Observed '+marker},
                    {'type':'mark','pr':'org/repo#1','text':marker}]
            (sd/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
            before=(sd/'events.jsonl').read_bytes()
            with mock.patch.object(export, 'session_config', return_value=cfg):
                self.assertNotIn(marker, export.build(sd))
            # Styles may receive an already-redacted projection; consult the original snapshot too.
            self.assertNotIn(marker,json.dumps(view.view_data(sd,data=product.project_data(legacy))))
            self.assertEqual((sd/'events.jsonl').read_bytes(),before)
            server.append_events(sd,[{'type':'note','text':marker}],'s')
            self.assertNotIn(marker,(sd/'events.jsonl').read_text().splitlines()[-1])
            self.assertIn('[redacted]',(sd/'events.jsonl').read_text().splitlines()[-1])

    def test_body_limit_precedes_read_and_event_offsets_have_typed_errors(self):
        helper = http_tests.ProductAccessActivityTests()
        handler = object.__new__(server.Handler)
        handler.headers = {'Content-Length': str(server.MAX_BODY + 1)}
        handler.rfile = mock.Mock()
        with self.assertRaises(server.BodyError) as raised:
            handler._body()
        self.assertEqual(raised.exception.code, 413); handler.rfile.read.assert_not_called()
        with helper.local_server() as (root, httpd, cfg):
            sd=root/'sessions/a';data=json.loads((sd/'review-data.json').read_text())
            data['prs']=[{'findings':[{'source':'upwind','scanner':{'kind':'secret'},
                         'body':'Upwind flags a value of type Token (TEST-OLD-EVENT). A pushed secret stays.'}]}]
            (sd/'review-data.json').write_text(json.dumps(data))
            (sd/'events.jsonl').write_text(json.dumps({'type':'note','text':'TEST-OLD-EVENT'})+'\n')
            status,body,_=helper.request(httpd,'/api/events')
            self.assertEqual(status,200);self.assertNotIn(b'TEST-OLD-EVENT',body)
            self.assertEqual(json.loads(body)['events'][0]['text'],'[redacted]')
            for route, expected in [('/api/events?since=0&x=1', 200), ('/api/events?since=bad', 400),
                                    ('/api/events?since=-1', 400), ('/api/events?since=1&since=2', 400)]:
                self.assertEqual(helper.request(httpd, route)[0], expected)
            status, _, _ = helper.request(httpd, '/api/event', {}, **{'Content-Length': str(server.MAX_BODY+1)})
            self.assertEqual(status, 413)

    def test_verdicts_are_scoped_by_pr_in_browser_latest_state_and_memory(self):
        events = [{'type': 'finding_verdict', 'pr': 'org/repo#'+str(n),
                   'target': {'kind': 'finding', 'id': 'same'}, 'verdict': verdict}
                  for n, verdict in [(1, 'accept'), (2, 'dismiss')]]
        self.assertEqual(len(distill.latest_state(events)), 2)
        app = (util.ROOT / 'app/app.js').read_text()
        code = app[app.index('function verdicts('):app.index('function notes(')]
        script = 'const S='+json.dumps({'events': events})+';'+code+';console.log(JSON.stringify([verdicts("org/repo#1"),verdicts("org/repo#2")]));'
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [{'same': 'accept'}, {'same': 'dismiss'}])
        helper = enrichment_tests.ProductEnrichRefreshTests()
        with helper.session() as (root, sd, cfg, read):
            data = json.loads((sd / 'review-data.json').read_text())
            second = copy.deepcopy(data['prs'][0]); second['key'] = 'org/repo#2'
            data['prs'].append(second)
            for pr, category in zip(data['prs'], ['security', 'style']):
                pr['findings'] = [{'id': 'same', 'pr': pr['key'], 'category': category, 'title': category, 'path': 'a.py'}]
            (sd / 'review-data.json').write_text(json.dumps(data))
            (sd / 'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
            cfg['memory'] = {'enabled': True, 'amr': str(root/'amr'), 'okf': str(root/'okf'), 'auto_commit': False}
            result = distill.distill(sd, cfg)
            rules = {x['rule'] for x in result['amr'] if x.get('rule')}
            self.assertIn('prioritize category=security', rules)
            self.assertTrue(any(x.startswith('collapse category=style ') for x in rules))
            self.assertNotIn('prioritize category=style', rules)

    def test_two_process_memory_proposals_preserve_both_concepts_log_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); start = root/'start'; bundle = root/'okf'
            script = """import pathlib,sys,time
from cockpit.memory import OKF
root,start,label=pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]),sys.argv[3]
okf=OKF(root);okf.ensure();original=okf.write
def slow(c):
 time.sleep(.15)
 return original(c)
okf.write=slow
while not start.exists():time.sleep(.01)
okf.propose(type_='Invariant',title='Same title',body=label,paths=['a.py'],by='fixture',sources=[])
okf.write_index()
"""
            children = [subprocess.Popen([sys.executable, '-B', '-c', script, str(bundle), str(start), label],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for label in ('first', 'second')]
            start.write_text('go')
            for child in children:
                _, error = child.communicate(timeout=15)
                self.assertEqual(child.returncode, 0, error)
            concepts = memory.OKF(bundle).concepts()
            self.assertEqual({c.body.strip() for c in concepts}, {'first', 'second'})
            self.assertEqual((bundle/'log.md').read_text().count('**Creation**'), 2)
            for concept in concepts:
                self.assertIn(concept.path, (bundle/'index.md').read_text())

    def test_cli_session_rejects_paths_and_untrusted_latest_contents(self):
        from cockpit import __main__ as cli
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sessions = root/'sessions'; sessions.mkdir()
            outside = root/'outside'; outside.mkdir(); (outside/'review-data.json').write_text('{}')
            with mock.patch.object(cli, 'SESSIONS', sessions):
                for name in ('../outside', str(outside), 'a/../../outside', '..'):
                    with self.assertRaises(SystemExit): cli._session_dir(name)
                (sessions/'latest').write_text('../outside')
                with self.assertRaises(SystemExit): cli._session_dir('latest')
            self.assertEqual((outside/'review-data.json').read_text(), '{}')

    def test_launcher_finds_existing_user_bin_without_path_and_preserves_explicit_selection(self):
        path = Path(__file__).resolve().parents[3]/'skills/qodo-review-cockpit/scripts/launch.py'
        spec = importlib.util.spec_from_file_location('cockpit_launch_recovery_fixture', path)
        launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(launcher.shutil, 'which', return_value=None), \
             mock.patch.dict(os.environ, {'QODO_HOME': tmp, 'REVIEW_COCKPIT_QODO': ''}):
            binary = Path(tmp)/'bin'/('qodo.exe' if sys.platform == 'win32' else 'qodo')
            binary.parent.mkdir(); binary.write_text('fixture')
            self.assertEqual(launcher.resolve_cli(), str(binary))
            with mock.patch.dict(os.environ, {'REVIEW_COCKPIT_QODO': str(Path(tmp)/'missing')}):
                self.assertIsNone(launcher.resolve_cli())

    def test_windows_batch_fallback_preserves_metacharacters_without_a_shell(self):
        from cockpit import cli_process
        node = shutil.which('node'); self.assertTrue(node)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'A&B'; root.mkdir(); batch = root/'qodo.cmd'; batch.write_text('must not execute')
            (root/'qodo.mjs').write_text("import fs from 'node:fs';const a=process.argv.slice(2);console.log(JSON.stringify({args:JSON.parse(fs.readFileSync(a[a.indexOf('--args-file')+1],'utf8'))}));")
            for minimal_path in (False, True):
                batch.write_text('set "NODE='+node+'"' if minimal_path else 'must not execute')
                def which(name):
                    return node if name == 'node' and not minimal_path else str(batch) if str(name) == str(batch) else None
                with self.subTest(minimal_path=minimal_path), mock.patch.object(cli_process.sys, 'platform', 'win32'), \
                     mock.patch.object(cli_process.shutil, 'which', side_effect=which), mock.patch.object(tempfile, 'tempdir', str(root)):
                    result = Client(str(batch)).read('codebase', 'read-file', repo='org/repo', path='a&b%file-שלום.py')
                self.assertEqual(result['args'], {'repo': 'org/repo', 'path': 'a&b%file-שלום.py'})
