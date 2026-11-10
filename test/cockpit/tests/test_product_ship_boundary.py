"""V1 entrypoint and review-state regressions from the assembled review."""
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from cockpit import enrich, memory, reviewers, util
from cockpit.adapters import qodo_comments, qodo_local
from tests import test_product_enrich_refresh as helpers


class ProductShipBoundaryTests(unittest.TestCase):
    def test_critical_findings_cannot_collapse_and_count_and_sort_as_high_risk(self):
        source = (util.ROOT/'app/app.js').read_text()
        def function(name):
            start = source.index('function '+name+'(')
            return source[start:source.index('\nfunction ', start+1)]
        rank = next(line for line in source.splitlines() if line.startswith('const SEV_ORDER'))
        code = rank+function('conceptByPath')+function('knownFor')+function('collapseRule')+function('sortedFindings')+function('renderOverview')
        setup = '''const S={data:{prs:[{key:'o/r#1',number:1,title:'Change',files:[],findings:[
 {id:'low',severity:'low',category:'bug'}, {id:'critical',severity:'critical',category:'bug'},
 {id:'high',severity:'high',category:'bug'}]}]},mem:{concepts:[]}};
const rules=()=>[{action:'collapse',category:'bug'}],globRe=()=>/.*/,priority=()=>0,esc=String;
const checksSummary=()=>'',markbar=()=>'',liveNotes=()=>'',sessionBudget=()=>'',sessionStory=()=>'',contextBox=()=>'',renderPrefsBox=()=>'',crossMap=()=>'';
'''
        script=setup+code+';console.log(JSON.stringify({critical:collapseRule(S.data.prs[0].findings[1]),order:sortedFindings(S.data.prs[0]).map(x=>x.id),html:renderOverview()}));'
        result = subprocess.run(['node','-e',script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertIsNone(output['critical'])
        self.assertEqual(output['order'], ['critical','high','low'])
        self.assertIn('2 high/critical', output['html'])

    def test_agent_finding_identity_survives_insert_reorder_refresh_and_explicit_edits(self):
        helper = helpers.ProductEnrichRefreshTests()
        key='org/repo#1'
        with helper.session() as (root,sd,cfg,read):
            a={'title':'A','body':'first','path':'a.py'};b={'title':'B','body':'second','path':'a.py'}
            def apply(rows):
                enrich.enrich(sd, {'prs':{key:{'findings':rows}}})
                data=json.loads((sd/'review-data.json').read_text())
                return {f['title']:f['id'] for f in data['prs'][0]['findings'] if f['source']=='agent'}
            original=apply([a,b])
            note={'type':'note','pr':key,'note_id':'n','text':'Keep B','target':{'kind':'finding','id':original['B']}}
            (sd/'events.jsonl').write_text(json.dumps(note)+'\n')
            changed=apply([{'title':'C'},b,a])
            self.assertEqual(changed['A'],original['A']);self.assertEqual(changed['B'],original['B'])
            helper.run_cli(['refresh','--session','s'])
            saved=json.loads((sd/'review-data.json').read_text())
            current={f['title']:f['id'] for f in saved['prs'][0]['findings'] if f['source']=='agent'}
            self.assertEqual(current,changed)
            apply([]);new=apply([{'title':'New'}]);self.assertNotIn(new['New'],original.values())
            edited=apply([{**b,'id':original['B'],'body':'Edited rationale'}])
            self.assertEqual(edited['B'],original['B'])
            self.assertEqual(json.loads((sd/'events.jsonl').read_text())['target']['id'],original['B'])

    def test_interrupted_local_import_keeps_previous_record_until_atomic_publish(self):
        pr='org/repo#1';result={'local_review_id':'local-one','findings':[{'id':'f','title':'Concern'}]}
        with tempfile.TemporaryDirectory() as tmp,mock.patch.object(qodo_local,'STORE',Path(tmp)):
            qodo_local.add(result,pr=pr)
            original=next(Path(tmp).glob('*.json'));legacy=Path(tmp)/'legacy.json';original.rename(legacy)
            before=legacy.read_bytes()
            with mock.patch.object(qodo_local,'write_json',side_effect=OSError('interrupted fixture')):
                with self.assertRaises(OSError):qodo_local.add(result,pr=pr)
            self.assertEqual(legacy.read_bytes(),before)
            self.assertEqual(len(qodo_local.records()),1)
            qodo_local.add(result,pr=pr)
            self.assertEqual(len(qodo_local.records()),1);self.assertFalse(legacy.exists())

    def test_product_reviewers_never_use_gh_and_legacy_migration_is_unreachable(self):
        from cockpit import __main__ as cli, managed_work, home
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}),mock.patch('subprocess.run') as external:
            with self.assertRaisesRegex(RuntimeError,'managed Qodo'):reviewers.Budget(1).api('/fixture')
            external.assert_not_called()
            with mock.patch.object(managed_work,'reviewers',return_value={'candidates':[]}) as managed:
                self.assertEqual(reviewers.suggest({'product':True,'prs':[]}),{'candidates':[]})
                managed.assert_called_once()
            with mock.patch.object(home,'migrate') as migrate:
                with self.assertRaisesRegex(SystemExit,'outside this skill'):cli.main(['migrate','--to','unused'])
                migrate.assert_not_called()

    def test_encoded_non_uuid_finding_links_keep_identity_and_query(self):
        url='https://portal.example/review/findings/provider%3Aopaque%2FID?source=cli#details'
        finding=qodo_comments.parse_inline('1. A concrete finding\n\n[View finding]('+url+')')
        self.assertIsNotNone(finding)
        self.assertEqual(finding['qodo_id'],'provider:opaque/ID')
        self.assertEqual(finding['qodo_url'],url)
        action=url.replace('source=cli','action=dismiss&source=cli')
        finding=qodo_comments.parse_inline('1. A finding\n\n[Dismiss]('+action+')')
        self.assertNotIn('action=',finding['qodo_url'])
        self.assertIn('source=cli',finding['qodo_url'])

    def test_two_process_memory_finish_credits_one_session_only_once(self):
        helper=helpers.ProductEnrichRefreshTests()
        with helper.session() as (root,sd,cfg,read):
            data=json.loads((sd/'review-data.json').read_text())
            data['prs'][0]['findings']=[{'id':'f','pr':'org/repo#1','category':'security','title':'Concern','path':'a.py'}]
            (sd/'review-data.json').write_text(json.dumps(data))
            (sd/'events.jsonl').write_text(json.dumps({'type':'finding_verdict','pr':'org/repo#1','target':{'kind':'finding','id':'f'},'verdict':'accept'})+'\n')
            cfg['memory']={'enabled':True,'amr':str(root/'amr'),'okf':str(root/'okf'),'auto_commit':False}
            params=root/'cfg.json';params.write_text(json.dumps(cfg));start=root/'start'
            script="""import json,pathlib,sys,time
from cockpit.distill import distill
while not pathlib.Path(sys.argv[3]).exists():time.sleep(.01)
distill(pathlib.Path(sys.argv[1]),json.loads(pathlib.Path(sys.argv[2]).read_text()))
"""
            children=[subprocess.Popen([sys.executable,'-B','-c',script,str(sd),str(params),str(start)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
            start.write_text('go')
            for child in children:
                _,error=child.communicate(timeout=15);self.assertEqual(child.returncode,0,error)
            bullets=[b for b in memory.AMR(root/'amr').bullets() if b.meta.get('rule')=='prioritize category=security']
            self.assertEqual(len(bullets),1);self.assertEqual(int(bullets[0].meta['evidence']),1)
