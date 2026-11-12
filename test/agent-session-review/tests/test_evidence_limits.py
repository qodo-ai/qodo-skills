import json
import subprocess
import unittest

from cockpit import util
from cockpit.styles import evidence_limits

SCRIPT = ("const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={};"
          "vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));")
DONE = {'complete': True, 'items': [{'patch_complete': True}]}


class EvidenceLimitsTests(unittest.TestCase):
    def test_limits_say_not_recorded_once_and_list_real_gaps(self):
        data = {'prs': [
            {'key': 'o/a#1', 'title': 'Old', 'files': [{'path': 'a.py'}, {'path': 'b.py'}]},
            {'key': 'o/b#2', 'title': 'New', 'read_evidence': {'sections': {'checks': {'status': 'truncated', 'complete': False}, 'reviews': {'status': 'exhausted', 'complete': True}, 'files': {'status': 'exhausted', 'complete': True}}},
             'files': [{'path': 'c.py', 'patch_evidence': DONE}, {'path': 'd.py', 'patch_evidence': {'complete': False, 'items': []}}], 'qodo_read_error': 'Qodo unavailable'},
            {'key': 'o/c#3', 'title': 'Clean', 'read_evidence': {'sections': {'checks': {'status': 'exhausted', 'complete': True}, 'files': {'status': 'exhausted', 'complete': True}}}, 'files': [{'path': 'e.py', 'patch_evidence': DONE}]}]}
        old, new, clean = evidence_limits(data)['prs']
        self.assertFalse(old['recorded'])
        self.assertEqual(old['files_unrecorded'], 2)
        self.assertTrue(new['recorded'])
        self.assertEqual(new['files_open'], ['d.py'])
        self.assertEqual([s['name'] for s in new['sections'] if not s['complete']], ['checks'])
        self.assertEqual(new['qodo_error'], 'Qodo unavailable')
        self.assertEqual((clean['files_open'], clean['files_unrecorded']), ([], 0))
        source = (util.ROOT / 'app/styles/evidence.js').read_text()
        stubs = "const KIT={host:{limits:" + json.dumps(evidence_limits(data)) + "}},esc=String,strip=String,pl=(n,w)=>n+' '+w+(n===1?'':'s');"
        out = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': stubs + source.split('document.addEventListener')[0]
                             + 'result=[evSummary(),EVL.prs.map(evState),evPr(EVL.prs[0]),evPr(EVL.prs[1]),evTip()];'}), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        summary, states, old_html, new_html, tip = json.loads(out.stdout)
        self.assertEqual(summary[:2], ['warn', 'Gaps on 2 of 3 PRs'])
        self.assertEqual(states, [['none', 'Not recorded'], ['warn', '3 gaps'], ['ok', 'Complete']])
        self.assertIn('No completeness was recorded for this PR', old_html)
        self.assertNotIn('a.py', old_html)   # not one line per file
        self.assertIn('Patches confirmed complete: 1 of 2', new_html)
        self.assertIn('<code>d.py</code>', new_html)
        self.assertIn('<b>checks</b>', new_html)
        self.assertIn('data-ev-open', tip)

    def test_missing_changed_files_and_an_unconfirmed_file_list_are_gaps(self):
        data = {'prs': [{'key': 'o/a#1', 'title': 'A', 'read_evidence': {'sections': {'files': {'status': 'exhausted', 'complete': True}}}, 'files_complete': False, 'files_missing': 3,
                         'files': [{'path': 'a.py', 'patch_evidence': {'complete': True, 'items': []}}]}]}
        pr = evidence_limits(data)['prs'][0]
        self.assertFalse(pr['files_list_complete'])
        self.assertEqual(pr['files_missing'], 3)
        self.assertEqual(pr['files_open'], ['a.py'])   # a patch with no items isn't confirmed
        source = (util.ROOT / 'app/styles/evidence.js').read_text()
        stubs = "const KIT={host:{limits:" + json.dumps(evidence_limits(data)) + "}},esc=String,strip=String,pl=(n,w)=>n+' '+w+(n===1?'':'s');"
        out = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': stubs + source.split('document.addEventListener')[0] + 'result=[evState(EVL.prs[0]),evPr(EVL.prs[0])];'}), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        state, html = json.loads(out.stdout)
        self.assertEqual(state, ['warn', '3 gaps'])
        self.assertIn('Changed-file list', html); self.assertIn("3 changed files the PR reports aren't in the review", html)

    def test_an_incomplete_files_section_counts_once(self):
        data = {'prs': [{'key': 'o/a#1', 'title': 'A', 'read_evidence': {'sections': {'files': {'status': 'truncated', 'complete': False}}}, 'files_complete': False,
                         'files': [{'path': 'a.py', 'patch_evidence': {'complete': True, 'items': [{'patch_complete': True}]}}]}]}
        source = (util.ROOT / 'app/styles/evidence.js').read_text()
        stubs = "const KIT={host:{limits:" + json.dumps(evidence_limits(data)) + "}},esc=String,strip=String,pl=(n,w)=>n+' '+w+(n===1?'':'s');"
        out = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': stubs + source.split('document.addEventListener')[0] + 'result=evState(EVL.prs[0]);'}), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), ['warn', '1 gap'])   # the files section and the file list are one failed read

    def test_session_auth_link_is_for_served_pages_only(self):
        styles = (util.ROOT / 'cockpit/styles.py').read_text()
        self.assertIn('if mode == "serve" and access_url:', styles)   # a snapshot never carries the key
        server = (util.ROOT / 'cockpit/server.py').read_text()
        self.assertIn('render(name, self.sdir, mode="serve", access_url=access)', server)
        source = (util.ROOT / 'app/styles/evidence.js').read_text()
        fn = source[source.index('function authTip()'):source.index('function evPr(')]
        out = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': "const esc=String,KIT={host:{access_url:'http://127.0.0.1:1/_access#key=k'}};" + fn + "result=[authTip(),(KIT.host={},authTip())];"}), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        html, none = json.loads(out.stdout)
        self.assertIn('Session auth', html); self.assertIn('data-copy-access', html); self.assertNotIn('href=', html)   # just Copy link
        self.assertEqual(none, '')

    def test_the_page_no_longer_appends_the_limits_block(self):
        styles = (util.ROOT / 'cockpit/styles.py').read_text()
        self.assertNotIn('Managed source evidence and limits', styles)
        self.assertIn("host['limits'] = evidence_limits(data)", styles)
        package = (util.ROOT / 'app/styles/package.js').read_text()
        tip = package[package.index('function freshTip()'):package.index('const SRV =')]
        self.assertTrue(tip.index('ft-ago') < tip.index('data-srv') < tip.index('data-commits-open') < tip.index('evTip()'))   # fetch time, server, commits link, then the limits
        self.assertNotIn('<ul>${rows}</ul>', tip)   # the PR list moved into its dialog
        self.assertIn('function evCommits()', (util.ROOT / 'app/styles/evidence.js').read_text())


if __name__ == '__main__':
    unittest.main()
