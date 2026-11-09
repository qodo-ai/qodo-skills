"""V1 projection and snapshot-writer regressions from hosted review79170."""
import copy
import json
import os
from pathlib import Path
import subprocess
import threading
import unittest
from unittest import mock

from cockpit import enrich, impact, memory, product, reviewers, util, view
from cockpit.adapters import qodo_cli, qodo_comments, qodo_local
from cockpit.session_writer import SessionBusy
from tests import test_product_enrich_refresh as helpers
from tests import test_product_finding_scope as scope_tests
from tests.test_product import HEAD


class ProductHostedReviewTests(unittest.TestCase):
    def test_local_current_anchor_requires_known_side_collected_path_and_valid_line(self):
        pr=scope_tests.ProductFindingScopeTests().pr();pr['product']=True
        cases=[(None,'a.py',1,False),('LEFT','a.py',1,False),('RIGHT','a.py',1,True),
               ('RIGHT','absent.py',1,False),('RIGHT','a.py',-1,False),('RIGHT','a.py',True,False)]
        for side,path,line,current in cases:
            with self.subTest(side=side,path=path,line=line):
                raw={'id':'f','title':'Concern','location':{'file_path':path,'start_line':line,'side':side}}
                finding=qodo_local.to_finding(pr,{'local_review_id':'r','commit':HEAD},raw,None)
                self.assertEqual(finding['current_anchor'],current)
                self.assertEqual(finding.get('path'),path if current else None)
                self.assertEqual(finding['source_location']['path'],path)
                self.assertEqual(finding['source_location']['line'],line)
                public=view._pr_view({**pr,'findings':[finding]})['findings'][0]
                self.assertEqual(public['current_anchor'],current)
        saved={'id':'saved','source':'qodo-local','path':'a.py','line':1,'title':'Legacy','severity':'medium',
               'local':{'commit':HEAD,'review_id':'old','at':'2026-01-01'}}
        before=copy.deepcopy(saved)
        projected=view._pr_view({**pr,'findings':[saved]})['findings'][0]
        self.assertFalse(projected['current_anchor']);self.assertIsNone(projected['path'])
        self.assertEqual(projected['source_location']['line'],1);self.assertEqual(saved,before)

    def test_post_merge_findings_retain_terminal_reason_without_claiming_fix(self):
        pr=scope_tests.ProductFindingScopeTests().pr();pr['product']=True
        raw={'id':'late','title':'Late concern','attribution_status':'detected_after_merge','git_sha':HEAD,
             'location':{'file_path':'a.py','start_line':1,'side':'RIGHT'}}
        managed=qodo_cli.to_finding(pr,raw)
        local=qodo_local.to_finding(pr,{'local_review_id':'r','commit':HEAD},raw,None)
        for finding in (managed,local):
            public=view._pr_view({**pr,'findings':[finding]})['findings'][0]
            self.assertEqual(public['status'],'detected_after_merge')
            self.assertEqual(public['closed_as'],'detected_after_merge')
            self.assertIn('no fix was verified',public['status_why'])
            self.assertNotIn('confirmed the fix',public['status_why'])
        older={**managed,'status':'resolved'};before=copy.deepcopy(older)
        self.assertEqual(view._pr_view({**pr,'findings':[older]})['findings'][0]['status'],'detected_after_merge')
        self.assertEqual(older,before)
        kit=(util.ROOT/'app/styles/kit.js').read_text()
        code=kit[kit.index('  const localDone ='):kit.index('  /* render code lines')]
        script='const esc=String,md=String;'+code+';console.log(localDone('+json.dumps([local])+'));'
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('detected after merge; no fix verified',result.stdout)
        self.assertNotIn('<b>fixed</b>',result.stdout)

    def test_reviewers_command_cannot_overwrite_a_concurrent_enrichment(self):
        helper=helpers.ProductEnrichRefreshTests();entered=threading.Event();release=threading.Event();errors=[]
        with helper.session() as (root,sd,cfg,read):
            before=(sd/'review-data.json').read_bytes()
            def suggest(*args):
                entered.set()
                if not release.wait(4):raise RuntimeError('fixture lookup timeout')
                return {'suggested':[],'calls':0,'excluded':[]}
            def run():
                try:helper.run_cli(['reviewers','--session','s','--json'])
                except BaseException as error:errors.append(error)
            with mock.patch.object(reviewers,'suggest',side_effect=suggest):
                worker=threading.Thread(target=run);worker.start()
                try:
                    self.assertTrue(entered.wait(3))
                    with self.assertRaises(SessionBusy):enrich.enrich(sd,helper.authored())
                    self.assertEqual((sd/'review-data.json').read_bytes(),before)
                finally:release.set();worker.join(timeout=5)
            self.assertFalse(worker.is_alive());self.assertFalse(errors,errors)
            self.assertEqual(json.loads((sd/'review-data.json').read_text())['reviewers']['suggested'],[])

    def test_idless_bucket_objects_use_same_display_identity_as_their_details(self):
        pr=scope_tests.ProductFindingScopeTests().pr();pr['product']=True
        finding={'title':'No UUID','description':'Preserve these details','file_path':'a.py','start_line':1}
        for bucket,expected in [('resolved','resolved'),('dismissed','dismissed'),('still_open',None)]:
            rec={'local_review_id':'r','commit':HEAD,'result':{'findings':[finding],
                  'finding_state':{bucket:[finding]}}}
            with self.subTest(bucket=bucket),mock.patch.object(qodo_local,'fetch',return_value=[rec]):
                output=qodo_local.collect(pr,{})
                self.assertEqual(len(output),1)
                self.assertEqual(output[0].get('status'),expected)
                self.assertEqual(output[0]['body'],'Preserve these details')

    def test_duplicate_knowledge_titles_in_one_enrichment_make_one_draft_candidate(self):
        helper=helpers.ProductEnrichRefreshTests()
        with helper.session() as (root,sd,cfg,read):
            cfg['memory']={'enabled':True,'auto_commit':False,'amr':str(root/'amr'),'okf':str(root/'okf')}
            payload={'knowledge':[{'title':'Decision','body':'First intent','paths':['a.py']},
                                  {'title':' decision ','body':'Second copy','paths':['a.py']}]}
            with mock.patch.object(enrich,'session_config',return_value=cfg):
                enrich.enrich(sd,payload)
                data=json.loads((sd/'review-data.json').read_text())
                self.assertEqual(len(data['okf']['candidates']),1)
                self.assertEqual(len(memory.OKF(root/'okf').concepts()),1)
                enrich.enrich(sd,payload)
                self.assertEqual(len(json.loads((sd/'review-data.json').read_text())['okf']['candidates']),1)

    def test_closed_comment_severity_is_explicit_or_unknown_and_inline_restores_it(self):
        summary='Code Review by Qodo\n<h3>Resolved findings</h3>\n<details><summary>1. <s>Concern</s> <code>Resolved</code></summary></details>'
        rows,_,_=qodo_comments.parse_review(summary)
        self.assertEqual(rows[0]['severity'],'unknown')
        explicit=summary.replace('<code>Resolved</code>','<code>High</code> <code>Resolved</code>')
        self.assertEqual(qodo_comments.parse_review(explicit)[0][0]['severity'],'high')
        pr={'key':'o/r#1','repo':'o/r','number':1,'_raw_comments':[
            {'id':'summary','author':'qodo-code-review[bot]','body':summary},
            {'id':'inline','author':'qodo-code-review[bot]','path':'a.py','line':1,
             'body':'1. Concern\n<img src="https://img.shields.io/badge/High-ff0000">\nDetails'}]}
        findings=qodo_comments.collect(pr,{})
        self.assertEqual(len(findings),1)
        self.assertEqual(findings[0]['status'],'resolved')
        self.assertEqual(findings[0]['severity'],'high')

    def test_unassessed_impact_stays_unknown_through_enrichment_and_public_view(self):
        helper=helpers.ProductEnrichRefreshTests()
        with helper.session() as (root,sd,cfg,read):
            for value in (None,'severe'):
                result=enrich.enrich(sd,{'impact':[{'component':'Service','change':'Behavior','risk':value,
                           'affects':['caller'],'gaps':['Risk not assessed'],'prs':['org/repo#1']}]})
                self.assertTrue(any('risk must be' in w for w in result['warnings']))
                public=view.view_data(sd)
                self.assertEqual(public['impact'][0]['risk'],'unknown')
                self.assertEqual(public['risk']['level'],'unknown')
