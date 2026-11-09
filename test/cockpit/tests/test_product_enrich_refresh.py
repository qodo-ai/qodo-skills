"""Authored enrichment survives refresh while product snapshot writers exclude each other."""
import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from cockpit import collect, managed_work, util
from cockpit import enrich as enrichment
from cockpit import __main__ as cli
from cockpit.adapters import qodo_cli
from cockpit.adapters.managed import Client, PermissionDenied
from cockpit.server import append_events
from cockpit.session_writer import LOCK_NAME, SessionBusy, session_writer
from tests.test_product import fixture

KEY='org/repo#1'


class ProductEnrichRefreshTests(unittest.TestCase):
    @contextlib.contextmanager
    def session(self):
        def read(group,tool,**args):
            if tool=='read-file':return {'content':'observed source','resolved_ref':args['ref'],'truncated':False}
            return fixture(group,tool,**args)
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}),mock.patch.object(Client,'read',side_effect=read),mock.patch.object(qodo_cli,'fetch',return_value=None):
            root=Path(tmp);sd=root/'sessions'/'s';sd.mkdir(parents=True)
            cfg=util.load_config();cfg['memory']['enabled']=False;cfg['notes']['enabled']=False;cfg['overlaps']['enabled']=False;cfg['adapters']=['qodo_comments']
            pr=Client().change('org/repo',1);collect.build([pr],cfg,demo=True,session='s',dest=sd)
            with mock.patch.object(cli,'SESSIONS',root/'sessions'),mock.patch.object(util,'load_config',return_value=cfg):
                yield root,sd,cfg,read

    def authored(self, text='Narrative'):
        return {'story':[{'kind':'callout','title':'Context','lede':'Read this first','text':text}],
                'prs':{KEY:{'summary':'Initial summary','layers':[{'id':'impl','title':'Implementation','ranges':[{'path':'a.py','from':1,'to':1}]}],
                            'decisions':[{'id':'d','text':'Retain the narrative','status':'missing','plan':'Refresh preserves context','source':'session'}]}},
                'system':{'contracts':[{'id':'c','name':'Contract','used':[{'repo':'org/repo','path':'source.py','from':1,'to':1,'ref':'main'}]}]}}

    def run_cli(self,args):
        with contextlib.redirect_stdout(io.StringIO()):cli.main(args)

    def test_cli_external_authored_input_incremental_merge_clear_and_refresh_preserve_local_work(self):
        with self.session() as (root,sd,cfg,read):
            outside=root/'external-input.json';payload=self.authored();outside.write_text(json.dumps(payload));original=outside.read_bytes()
            self.run_cli(['--product','enrich',str(outside),'--session','s'])
            self.assertEqual(json.loads((sd/'enrich.json').read_text()),payload);self.assertEqual(outside.read_bytes(),original)
            stored=json.loads((sd/'review-data.json').read_text());ref=stored['system']['contracts'][0]['used'][0]
            self.assertEqual(ref['ref'],'c'*40);self.assertEqual(ref['excerpt'],'observed source')
            self.assertNotIn('excerpt',json.loads((sd/'enrich.json').read_text())['system']['contracts'][0]['used'][0])
            second=root/'summary-only.json';second.write_text(json.dumps({'prs':{KEY:{'summary':'New summary'}}}))
            self.run_cli(['--product','enrich',str(second),'--session','s'])
            append_events(sd,[{'type':'note','note_id':'reader','pr':KEY,'text':'keep reader note'}],'s');events=(sd/'events.jsonl').read_bytes()
            self.run_cli(['--product','refresh','--session','s'])
            stored=json.loads((sd/'review-data.json').read_text());pr=stored['prs'][0]
            self.assertEqual(stored['story'][0]['text'],'Narrative');self.assertEqual(pr['summary'],'New summary');self.assertEqual(pr['layers'][0]['id'],'impl');self.assertEqual(pr['decisions'][0]['id'],'d')
            self.assertEqual((sd/'events.jsonl').read_bytes(),events)
            authored=json.loads((sd/'enrich.json').read_text());self.assertEqual(authored['system'],payload['system']);self.assertEqual(authored['prs'][KEY]['layers'],payload['prs'][KEY]['layers'])
            self.assertEqual(outside.read_bytes(),original)
            enrichment.enrich(sd,{'story':[],'prs':{KEY:{'decisions':[]}}})
            self.run_cli(['--product','refresh','--session','s'])
            stored=json.loads((sd/'review-data.json').read_text());self.assertEqual(stored['story'],[]);self.assertEqual(stored['prs'][0]['decisions'],[]);self.assertTrue(stored['prs'][0]['layers'])
            self.assertFalse((sd/LOCK_NAME).exists())

    def test_active_enrich_rejects_refresh_and_refresh_reads_new_snapshot_under_guard(self):
        with self.session() as (root,sd,cfg,read):
            stale=json.loads((sd/'review-data.json').read_text());entered=threading.Event();finish=threading.Event();errors=[];real=enrichment._enrich
            def paused(*args,**kwargs):
                result=real(*args,**kwargs);entered.set()
                if not finish.wait(3):raise RuntimeError('test writer did not resume')
                return result
            def work():
                try:enrichment.enrich(sd,self.authored('Accepted newer narrative'))
                except BaseException as error:errors.append(error)
            with mock.patch.object(enrichment,'_enrich',side_effect=paused):
                thread=threading.Thread(target=work);thread.start()
                try:
                    self.assertTrue(entered.wait(3));snapshot=(sd/'review-data.json').read_bytes()
                    with mock.patch.object(Client,'read') as reads:
                        with self.assertRaisesRegex(SessionBusy,'busy'):managed_work.refresh(sd,stale,cfg)
                        reads.assert_not_called()
                    self.assertEqual((sd/'review-data.json').read_bytes(),snapshot)
                    append_events(sd,[{'type':'note','note_id':'during','pr':KEY,'text':'reader during enrich'}],'s')
                finally:finish.set();thread.join(timeout=3)
            self.assertFalse(errors);self.assertFalse(thread.is_alive())
            real_refresh=managed_work._refresh
            def verify_current(sdir,current,config):
                self.assertEqual(current['story'][0]['text'],'Accepted newer narrative')
                return real_refresh(sdir,current,config)
            with mock.patch.object(managed_work,'_refresh',side_effect=verify_current):managed_work.refresh(sd,stale,cfg)
            self.assertEqual(json.loads((sd/'review-data.json').read_text())['story'][0]['text'],'Accepted newer narrative')
            self.assertIn('reader during enrich',(sd/'events.jsonl').read_text());self.assertFalse((sd/LOCK_NAME).exists())

    def test_refresh_late_failure_rejects_concurrent_enrich_preserves_newer_intent_and_retry(self):
        with self.session() as (root,sd,cfg,read):
            stale=json.loads((sd/'review-data.json').read_text());enrichment.enrich(sd,self.authored('Accepted intent'))
            snapshot=(sd/'review-data.json').read_bytes();authored=(sd/'enrich.json').read_bytes()
            outside=root/'competing.json';outside.write_text(json.dumps({'story':[{'kind':'callout','text':'Retry intent','lede':'Updated'}]}));input_bytes=outside.read_bytes()
            entered=threading.Event();finish=threading.Event();errors=[]
            def paused(group,tool,**args):
                if tool=='get-change-context':
                    entered.set()
                    if not finish.wait(3):raise RuntimeError('test refresh did not resume')
                if tool=='read-file':raise PermissionDenied('controlled late source denial')
                result=read(group,tool,**args)
                if tool=='get-change-context':result['head_sha']='d'*40
                return result
            def work():
                try:managed_work.refresh(sd,stale,cfg)
                except BaseException as error:errors.append(error)
            with mock.patch.object(Client,'read',side_effect=paused):
                thread=threading.Thread(target=work);thread.start()
                try:
                    self.assertTrue(entered.wait(3))
                    with self.assertRaisesRegex(SessionBusy,'busy'):self.run_cli(['--product','enrich',str(outside),'--session','s'])
                    self.assertEqual(outside.read_bytes(),input_bytes);self.assertEqual((sd/'enrich.json').read_bytes(),authored)
                    append_events(sd,[{'type':'note','note_id':'refresh-note','pr':KEY,'text':'concurrent local note'}],'s');events=(sd/'events.jsonl').read_bytes()
                finally:finish.set();thread.join(timeout=3)
            self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],PermissionDenied);self.assertFalse(thread.is_alive())
            self.assertEqual((sd/'review-data.json').read_bytes(),snapshot);self.assertEqual((sd/'enrich.json').read_bytes(),authored);self.assertEqual((sd/'events.jsonl').read_bytes(),events);self.assertFalse((sd/LOCK_NAME).exists())
            self.run_cli(['--product','enrich',str(outside),'--session','s']);managed_work.refresh(sd,stale,cfg)
            self.assertEqual(json.loads((sd/'review-data.json').read_text())['story'][0]['text'],'Retry intent');self.assertEqual((sd/'events.jsonl').read_bytes(),events)

    def test_cross_process_writer_busy_then_cli_retry_and_same_owner_reentrancy(self):
        with self.session() as (root,sd,cfg,read):
            outside=root/'input.json';outside.write_text(json.dumps({'story':[{'kind':'callout','text':'Child narrative','lede':'Context'}]}));before=outside.read_bytes();snapshot=(sd/'review-data.json').read_bytes()
            (root/'config.json').write_text(json.dumps(cfg))
            argv=[sys.executable,'-B','-m','cockpit','--product','enrich',str(outside),'--session','s']
            env={**os.environ,'PYTHONPATH':str(util.ROOT),'REVIEW_COCKPIT_HOME':str(root)}
            with session_writer(sd):
                with session_writer(sd):self.assertTrue((sd/LOCK_NAME).is_dir())
                result=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=10)
                self.assertNotEqual(result.returncode,0);self.assertIn('Work package busy',result.stderr)
                self.assertEqual((sd/'review-data.json').read_bytes(),snapshot);self.assertEqual(outside.read_bytes(),before)
            self.assertFalse((sd/LOCK_NAME).exists())
            result=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads((sd/'review-data.json').read_text())['story'][0]['text'],'Child narrative');self.assertEqual(outside.read_bytes(),before);self.assertFalse((sd/LOCK_NAME).exists())

    def test_standalone_enrich_keeps_legacy_persistence_and_guard_behavior(self):
        with self.session() as (root,sd,cfg,read):
            data=json.loads((sd/'review-data.json').read_text());data.pop('product',None)
            for pr in data['prs']:pr.pop('product',None)
            (sd/'review-data.json').write_text(json.dumps(data))
            with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}),session_writer(sd):
                enrichment.enrich(sd,{'story':[{'kind':'callout','text':'Legacy','lede':'Context'}]})
            self.assertFalse((sd/'enrich.json').exists());self.assertEqual(json.loads((sd/'review-data.json').read_text())['story'][0]['text'],'Legacy')
