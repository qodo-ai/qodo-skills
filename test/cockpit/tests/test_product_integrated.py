import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cockpit import criticality, managed_work, product
from cockpit.adapters import qodo_cli
from cockpit.adapters.managed import Client, PermissionDenied, ScopedPermissionDenied
from cockpit.risk import approval
from cockpit.util import ROOT
from tests.test_product import fixture, ID, HEAD, REV, page


class IntegratedProductTests(unittest.TestCase):
    def test_global_auth_stops_but_scoped_provider_denial_does_not_retry_or_fallback(self):
        for code in ('token_expired','invalid_token'):
            with mock.patch('subprocess.run',return_value=subprocess.CompletedProcess([],1,json.dumps({'error':{'code':code}}),'')) as run:
                with self.assertRaises(PermissionDenied):Client('qodo').read('codebase','get-change-context')
                self.assertEqual(run.call_count,1)
        out={'error':{'code':'MT-UPSTREAM-DOWN','metadata':{'upstream_status':403}}}
        with mock.patch('subprocess.run',return_value=subprocess.CompletedProcess([],1,json.dumps(out),'')) as run:
            result=Client('qodo').pages(ID,'statuses',1,REV)
        self.assertEqual(run.call_count,1);self.assertEqual(result['status'],'permission_limited');self.assertFalse(result['complete'])
        seen=[]
        def read(group,tool,**params):
            if tool=='read-review-data':
                seen.append(params['kind'])
                if params['kind']=='statuses':raise ScopedPermissionDenied('403')
            return fixture(group,tool,**params)
        with mock.patch.object(Client,'read',side_effect=read):pr=Client().change('org/repo',1)
        self.assertIn('history',seen);self.assertEqual(seen.count('statuses'),1)
        self.assertEqual(pr['read_evidence']['sections']['statuses']['status'],'permission_limited')

    def test_incomplete_paths_cannot_approve_and_unqualified_owners_remain_unchecked(self):
        def read(group,tool,**args):
            if tool=='read-review-data' and args['kind']=='files':return page([{'filename':'public.py'}],complete=None)
            return fixture(group,tool,**args)
        real_fetch=getattr(qodo_cli,'_real_fetch',qodo_cli.fetch)
        with mock.patch.object(Client,'read',side_effect=read),mock.patch.object(qodo_cli,'fetch',real_fetch):
            pr=Client().change('org/repo',1);qodo_cli.collect(pr,{})
        pr['qodo_source']='cli';data={'product':True,'prs':[pr]}
        cfg={'criticality':{'map':[{'repo':'*','paths':['secrets/**'],'approve':'never','reason':'secret files'}]}}
        self.assertIsNone(pr['files_complete'])
        gate=criticality.gate(criticality.resolve(data,cfg))
        self.assertEqual(approval(data,'low',gate=gate)['result'],'human review')
        self.assertTrue(approval(data,'low',gate=gate)['blocked_by_path'])
        pr['files_complete']=True
        with mock.patch.object(Client,'read',side_effect=fixture):rv=managed_work.reviewers(data,{},2)
        self.assertNotIn('owned',rv);data['reviewers']=rv
        gate=criticality.gate(criticality.resolve(data,{'criticality':{'codeowners':'protect'}}))
        self.assertTrue(gate['owners_unchecked'])
        self.assertEqual(approval(data,'low',gate=gate)['result'],'human review')

    def test_managed_reviewed_revision_preserves_current_human_approval(self):
        def read(group,tool,**args):
            if tool=='read-review-data' and args['kind']=='reviews':return page([{'actor':{'login':'alice'},'state':'APPROVED','reviewed_revision':HEAD,'submitted_at':'2026-11-01T00:00:00Z'}])
            return fixture(group,tool,**args)
        with mock.patch.object(Client,'read',side_effect=read):pr=Client().change('org/repo',1)
        self.assertEqual(pr['approvals'],['alice'])

    def test_colliding_repository_paths_are_rejected_before_association(self):
        from cockpit.adapters.managed import ReadError
        first={'key':'org/repo#1','repo':'org/repo','number':1,'identity':ID,'files':[]}
        second={**first,'key':'org/repo#2','number':2,'identity':{**ID,'provider_host':'github.corp','repository_url':'https://github.corp/org/repo'}}
        with self.assertRaisesRegex(ReadError,'separate sessions'):managed_work.validate_identities([first,second])
        self.assertEqual(first['key'],'org/repo#1');self.assertEqual(second['key'],'org/repo#2')

    def hydrate(self,data,stored=None):
        source=(ROOT/'app/styles/product-state.js').read_text()
        script="""const vm=require('node:vm'), x=JSON.parse(require('node:fs').readFileSync(0,'utf8'));const c={};vm.createContext(c);vm.runInContext(x.source+'; result=PRODUCT_STATE.hydrate('+JSON.stringify(x.data)+','+JSON.stringify(x.stored)+',"serve");',c);process.stdout.write(JSON.stringify(c.result));"""
        result=subprocess.run(['node','-e',script],input=json.dumps({'source':source,'data':data,'stored':stored or {}}),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_local_hydration_isolated_undo_edits_and_marks(self):
        data={'session':'s','prs':[{'key':'org/repo#1'}],'events':[
            {'type':'note','note_id':'n1','ui_id':'target','pr':'org/repo#1','text':'old'},
            {'type':'note','note_id':'n2','ui_id':'target','pr':'org/repo#1','text':'new'},
            {'type':'note','note_id':'unrelated','pr':'other/repo#1','text':'never show'},
            {'type':'note','session':'other','note_id':'cross','pr':'org/repo#1','text':'never show'},
            {'type':'mark','pr':'org/repo#1','target':{'kind':'pr','id':'org/repo#1'},'emoji':'👏'},
            {'type':'package_state','target':{'id':'s'},'state':{'picks':{'q':1},'verdict':{'org/repo#1':'approve','other/repo#1':'approve'}}}]}
        state=self.hydrate(data);self.assertEqual([n['text'] for n in state['notes']],['new'])
        self.assertEqual(len(state['marks']),1);self.assertEqual(state['picks'],{'q':1});self.assertNotIn('other/repo#1',state['verdict'])
        data['events'].append({'type':'note','note_id':'n2','pr':'org/repo#1','undo':True})
        self.assertEqual(self.hydrate(data,state)['notes'],[])

    def test_two_finding_verdict_ids_survive_and_replace_independently(self):
        data={'session':'s','prs':[{'key':'org/repo#1'}],'events':[
            {'type':'finding_verdict','pr':'org/repo#1','id':'f1','verdict':'accept'},
            {'type':'finding_verdict','pr':'org/repo#1','id':'f2','verdict':'accept'}]}
        self.assertEqual({e['id'] for e in self.hydrate(data)['marks']},{'f1','f2'})
        data['events'] += [{'type':'finding_verdict','pr':'org/repo#1','id':'f1','verdict':'dismiss'},
                           {'type':'finding_verdict','pr':'org/repo#1','id':'f2','verdict':None}]
        marks=self.hydrate(data)['marks'];self.assertEqual([(e['id'],e['verdict']) for e in marks],[('f1','dismiss')])

    def test_cli_note_refresh_default_export_hydrates_on_new_origin(self):
        from cockpit import collect as collection, __main__ as cli
        from cockpit.view import view_data
        from cockpit.util import write_json
        import contextlib,io
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);sessions=home/'sessions';sessions.mkdir()
            (home/'config.json').write_text(json.dumps({'sessions':str(sessions),'memory':{'enabled':False,'auto_commit':False},'overlaps':{'enabled':False},'notes':{'enabled':False}}))
            with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}),mock.patch.object(collection,'SESSIONS',sessions),mock.patch.object(Client,'read',side_effect=fixture),mock.patch.object(qodo_cli,'fetch',return_value=None):
                cfg=collection.load_config();cfg['memory']['enabled']=False
                _,sd=managed_work.collect(['org/repo#1'],None,cfg)
            env={**os.environ,'REVIEW_COCKPIT_HOME':str(home),'PYTHONDONTWRITEBYTECODE':'1'}
            result=subprocess.run([__import__('sys').executable,'-B','-m','cockpit','note','--session',sd.name,'--pr','org/repo#1','durable-note-control'],cwd=ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}),mock.patch.object(cli,'SESSIONS',sessions),mock.patch.object(Client,'read',side_effect=fixture),mock.patch.object(qodo_cli,'fetch',return_value=None),contextlib.redirect_stdout(io.StringIO()):
                cli.main(['refresh','--session',sd.name])
            result=subprocess.run([__import__('sys').executable,'-B','-m','cockpit','export','--session',sd.name,'--out',str(home/'out.html')],cwd=ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            html=(home/'out.html').read_text();self.assertIn('durable-note-control',html);self.assertIn('PRODUCT_STATE.hydrate',html)
            with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}):
                view=view_data(sd)
            state=self.hydrate(view,{})
            self.assertIn('durable-note-control',[n['text'] for n in state['notes']])
            self.assertFalse(any(e.get('post') for e in view['events'] if e.get('type')=='note'))
