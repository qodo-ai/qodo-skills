"""Controls for provider identity, human review coverage and incomplete collections."""
import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cockpit import collect, managed_work, product
from cockpit.adapters import qodo_local
from cockpit.adapters.managed import BudgetExceeded, Client, ReadError
from cockpit.risk import approval
from tests.test_product import fixture, HEAD, ID, page


class PendingAcceptanceTests(unittest.TestCase):
    def test_mixed_host_same_path_rejected_before_build_even_different_numbers(self):
        def change(repo,number,host=None,**args):
            return {'repo':repo,'number':number,'key':f'{repo}#{number}','identity':{**ID,'provider_host':host}}
        refs=['https://github.com/org/repo/pull/1','https://github.corp/org/repo/pull/2']
        with mock.patch.object(Client,'change',side_effect=change),mock.patch.object(collect,'build') as build:
            with self.assertRaisesRegex(ReadError,'separate sessions'):managed_work.collect(refs,None,{})
        build.assert_not_called()
        pr={'repo':'org/repo','key':'org/repo#1','number':1,'identity':ID}
        self.assertEqual(managed_work.validate_identities([pr])[0]['key'],'org/repo#1')
        record={'pr':'org/repo#1','result':{'findings':[]}}
        with mock.patch.object(qodo_local,'records',return_value=[record]):self.assertEqual(qodo_local.fetch(pr,{}),[record])

    def test_github_casefold_is_provider_scoped_and_ambiguity_checked(self):
        registered={'full_name':'Org/Repo','provider':'github','html_url':'https://github.com/Org/Repo'}
        with mock.patch.object(Client,'read',return_value={'repos':[registered]}):
            self.assertEqual(Client().identity('ORG/REPO','github.com')['repo'],'Org/Repo')
        with mock.patch.object(Client,'read',return_value={'repos':[registered,{**registered,'full_name':'org/repo'}]}):
            with self.assertRaises(ReadError):Client().identity('ORG/REPO','github.com')
        with mock.patch.object(Client,'read',return_value={'repos':[{**registered,'provider':'gitlab','html_url':'https://gitlab.test/Org/Repo'}]}):
            with self.assertRaises(ReadError):Client().identity('ORG/REPO','gitlab.test')
            self.assertEqual(Client().identity('Org/Repo','gitlab.test')['repo'],'Org/Repo')

    def test_bot_actor_never_becomes_human_approval_or_change_request_in_collect_or_live(self):
        reviews=[{'actor':{'login':'alice','is_bot':False},'state':'APPROVED','reviewed_revision':HEAD,'submitted_at':'2026-11-01T00:00:00Z'},
                 {'actor':{'login':'build-service','is_bot':True},'state':'APPROVED','reviewed_revision':HEAD},
                 {'actor':{'login':'gate-service','is_bot':True},'state':'CHANGES_REQUESTED','reviewed_revision':HEAD}]
        def read(group,tool,**args):
            if tool=='read-review-data' and args['kind']=='reviews':return page(reviews)
            return fixture(group,tool,**args)
        with mock.patch.object(Client,'read',side_effect=read):
            pr=Client().change('org/repo',1)
            snapshot={**pr,'approvals':[]}
            live=managed_work.live_state([snapshot])[pr['key']]
        self.assertEqual(pr['approvals'],['alice']);self.assertEqual(pr['changes_requested'],[])
        self.assertEqual(live['approved_by'],['alice']);self.assertEqual(live['current_approved_by'],['alice']);self.assertEqual(live['review_decision'],'APPROVED')
        with mock.patch.object(Client,'read',side_effect=read):known=managed_work.live_state([pr])[pr['key']]
        self.assertEqual(known['approved_by'],[]);self.assertEqual(known['current_approved_by'],['alice'])
        reviews[0]['reviewed_revision']='old'
        with mock.patch.object(Client,'read',side_effect=read):live=managed_work.live_state([pr])[pr['key']]
        self.assertEqual(live['approved_by'],[]);self.assertIsNone(live['review_decision'])
        reviews[0].update(reviewed_revision=HEAD,state='CHANGES_REQUESTED')
        with mock.patch.object(Client,'read',side_effect=read):live=managed_work.live_state([pr])[pr['key']]
        self.assertEqual(live['review_decision'],'CHANGES_REQUESTED')

    def test_partial_review_coverage_remains_unknown_in_live_status(self):
        def read(group,tool,**args):
            if tool=='read-review-data' and args['kind']=='reviews':return page([{'actor':{'login':'alice'},'state':'APPROVED','reviewed_revision':HEAD}],complete=False)
            return fixture(group,tool,**args)
        pr={'key':'org/repo#1','repo':'org/repo','number':1,'identity':ID}
        with mock.patch.object(Client,'read',side_effect=read):live=managed_work.live_state([pr])[pr['key']]
        self.assertIsNone(live['approved_by']);self.assertIsNone(live['review_decision']);self.assertFalse(live['reviews_complete'])

    def test_new_partial_collection_saves_evidence_and_can_retry_omitted_refs_without_losing_notes(self):
        def run(argv,**kwargs):
            args=json.loads(Path(argv[argv.index('--args-file')+1]).read_text());calls.append((argv[3],args))
            return subprocess.CompletedProcess(argv,0,json.dumps(fixture(argv[2],argv[3],**args)),'')
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1','REVIEW_COCKPIT_QODO':'qodo'}),mock.patch.object(collect,'SESSIONS',Path(tmp)):
            cfg=collect.load_config();cfg['memory']['enabled']=False;cfg['notes']['enabled']=False;cfg['overlaps']['enabled']=False;cfg['adapters']=['qodo_comments']
            requested=['org/repo#1','org/repo#2','org/repo#3'];calls=[]
            with mock.patch('cockpit.adapters.managed.MAX_OPERATION_CALLS',18),mock.patch('subprocess.run',side_effect=run):
                _,sd=managed_work.collect(requested,None,cfg)
            data=json.loads((sd/'review-data.json').read_text());self.assertLessEqual(len(calls),18)
            self.assertGreaterEqual(len(data['prs']),1);self.assertEqual(data['prs'][0]['head_sha'],HEAD)
            self.assertFalse(data['collection']['complete']);self.assertEqual(data['collection']['requested_refs'],requested)
            self.assertIn('org/repo#3',data['collection']['omitted_refs'])
            verdict=approval(data,'low');self.assertEqual(verdict['result'],'human review');self.assertNotIn('Qodo reviewed every PR.',verdict['reasons'])
            self.assertTrue(all(not p['product_evidence']['quality_complete'] for p in product.project_data(data)['prs']))
            from cockpit.styles import render
            self.assertIn('Work package collection incomplete',render('package',sd,data=data))
            original=(sd/'review-data.json').read_bytes();(sd/'events.jsonl').write_text('{"type":"note","note_id":"n","pr":"org/repo#1","text":"keep"}\n')
            calls=[]
            with mock.patch('cockpit.adapters.managed.MAX_OPERATION_CALLS',18),mock.patch('subprocess.run',side_effect=run):
                with self.assertRaises(BudgetExceeded):managed_work.refresh(sd,data,cfg)
            self.assertEqual((sd/'review-data.json').read_bytes(),original);self.assertLessEqual(len(calls),18)
            calls=[]
            with mock.patch('cockpit.adapters.managed.MAX_OPERATION_CALLS',96),mock.patch('subprocess.run',side_effect=run):managed_work.refresh(sd,data,cfg)
            recovered=json.loads((sd/'review-data.json').read_text());self.assertEqual(len(recovered['prs']),3)
            self.assertTrue(recovered['collection']['complete']);self.assertEqual(recovered['collection']['omitted_refs'],[])
            self.assertTrue(any(args.get('change_number')==3 for tool,args in calls if tool=='get-change-context'))
            self.assertIn('"text":"keep"',(sd/'events.jsonl').read_text())

    def test_full_app_ci_uses_handler_product_projection_and_preserves_standalone(self):
        from cockpit.server import Handler
        from types import SimpleNamespace
        from cockpit.util import ROOT
        source=(ROOT/'app/app.js').read_text()
        code=source[source.index('function checksSummary('):source.index('// A local finding:')]
        old=(Path(__file__).resolve().parent/'fixtures/local/standalone-checks.js').read_text()
        script="const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={esc:String};vm.createContext(c);vm.runInContext(x.code+';result=checksSummary('+JSON.stringify(x.pr)+');',c);process.stdout.write(JSON.stringify(c.result));"
        def draw(pr,code=code):
            r=subprocess.run(['node','-e',script],input=json.dumps({'code':code,'pr':pr}),capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            sd=Path(tmp);data={'prs':[{'key':'org/repo#1','checks':[{'name':'observed','state':'success'}],'read_evidence':{'sections':{'checks':{'complete':True},'statuses':{'complete':False}}}}]}
            (sd/'review-data.json').write_text(json.dumps(data))
            handler=object.__new__(Handler);handler.sdir=sd;handler.server=SimpleNamespace(product=True)
            pr=handler._data()['prs'][0];html=draw(pr)
            self.assertIn('CI: Unknown',html);self.assertIn('success (reported)',html);self.assertNotIn('1/1 checks passed',html)
            data['prs'][0]['read_evidence']['sections']['statuses']['complete']=True
            (sd/'review-data.json').write_text(json.dumps(data));self.assertIn('1/1 checks passed',draw(handler._data()['prs'][0]))
            handler.server.product=False;pr=handler._data()['prs'][0];self.assertEqual(draw(pr),draw(pr,old))

    def test_standalone_comment_only_preview_matches_original_before_after(self):
        pr={'key':'org/repo#1','qodo_source':'comments','findings':[]}
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            expected=json.loads((Path(__file__).resolve().parent/'fixtures/local/standalone-approval.json').read_text())
            self.assertEqual(approval({'prs':[pr]},'low')['result'],expected['standalone'])
            self.assertEqual(approval({'product':True,'prs':[pr]},'low')['result'],expected['product'])
