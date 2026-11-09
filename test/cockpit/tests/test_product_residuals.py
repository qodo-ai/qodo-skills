"""Integrated controls for managed source evidence, refresh budgets and local reader state."""
import copy
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cockpit import ask, collect, product, system, util
from cockpit.adapters import qodo_cli
from cockpit.adapters.managed import BudgetExceeded, Client, PermissionDenied
from tests.test_product import fixture, HEAD, ID, REV, read_tool


class ResidualProductTests(unittest.TestCase):
    def node(self,script,payload):
        result=subprocess.run(['node','-e',script],input=json.dumps(payload),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_all_primary_ci_aggregates_use_coverage_and_standalone_is_unchanged(self):
        source=(util.ROOT/'app/styles/package.js').read_text()
        prefix=source[source.index('function productEvidenceUnknown('):source.index('function productToolStatus(')]
        code=prefix+source[source.index('function pkCells('):source.index('document.addEventListener("click"',source.index('function pkCells('))]
        code+=source[source.index('function prChips('):source.index('const PKICON =')]
        script="""const vm=require('node:vm'), x=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const c={LIVE:{},CI_BAD:['FAILURE','ERROR'],CI_OK:['SUCCESS','SKIPPED','NEUTRAL'],isOpen:f=>!f.status||f.status==='open',prState:()=>'',esc:String,pl:(n,s)=>n+' '+s,S:{open:{}},pkgLines:()=>[0,0],GHICON:'',STATE_NAME:{},PRICON:{},strip:String};
vm.createContext(c);vm.runInContext(x.code+'; result={cells:pkCells('+JSON.stringify(x.pr)+'),chips:prChips('+JSON.stringify(x.pr)+'),table:pkTable([{repo:"org/repo",ps:['+JSON.stringify(x.pr)+'],rows:[]}])};',c);process.stdout.write(JSON.stringify(c.result));"""
        pr={'key':'org/repo#1','product':True,'findings':[],'checks':[{'state':'success'}],'product_evidence':{'ci_complete':False}}
        out=self.node(script,{'code':code,'pr':pr})
        self.assertEqual(out['cells']['ci'],['','Unknown']);self.assertIn('CI: Unknown',out['chips'])
        self.assertNotIn('All passed',out['table']);self.assertNotIn('1/1 passed',out['table']);self.assertIn('Unknown',out['table'])
        for control in ({**pr,'product_evidence':{'ci_complete':True}},{**pr,'product':False}):
            known=self.node(script,{'code':code,'pr':control});self.assertEqual(known['cells']['ci'],['ok','1/1 passed'])
            self.assertIn('CI passed 1/1',known['chips']);self.assertIn('All passed',known['table'])

    def test_patch_unavailability_cannot_make_local_quality_complete(self):
        with mock.patch.object(Client,'read',side_effect=fixture):pr=Client().change('org/repo',1)
        pr.update(qodo_source='cli',qodo_review={'status':'completed','review_complete':True,'commit':HEAD,'run_id':'run','bounded':False},scans=[])
        for proof in ({'items':[],'complete':False,'status':'unavailable'}, {'items':[{'patch_complete':None}],'complete':True,'status':'observed'}):
            pr['files'][0]['patch_evidence']=proof
            state=product.project_pr(pr)['product_evidence']
            self.assertTrue(state['qodo_complete']);self.assertFalse(state['patches_complete']);self.assertFalse(state['quality_complete'])
        pr['files'][0]['patch_evidence']={'items':[{'patch_complete':True}],'complete':True,'status':'observed'}
        self.assertTrue(product.project_pr(pr)['product_evidence']['quality_complete'])

    def hydrate(self,data,stored=None,mode='snapshot'):
        script="""const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={};vm.createContext(c);vm.runInContext(x.source+';result=PRODUCT_STATE.hydrate('+JSON.stringify(x.data)+','+JSON.stringify(x.stored)+','+JSON.stringify(x.mode)+');',c);process.stdout.write(JSON.stringify(c.result));"""
        return self.node(script,{'source':(util.ROOT/'app/styles/product-state.js').read_text(),'data':data,'stored':stored,'mode':mode})

    def test_snapshot_fresh_seed_then_note_edit_remove_verdict_read_reload(self):
        data={'session':'s','prs':[{'key':'org/repo#1'}],'events':[{'type':'note','note_id':'n1','pr':'org/repo#1','text':'original'}, {'type':'package_state','target':{'id':'s'},'state':{'verdict':{'org/repo#1':'comment'},'read':{'b1':True}}}, {'type':'finding_verdict','id':'f1','pr':'org/repo#1','verdict':'accept'}, {'type':'finding_verdict','id':'f2','pr':'org/repo#1','verdict':'dismiss'}]}
        fresh=self.hydrate(data)
        self.assertEqual(fresh['notes'][0]['text'],'original');self.assertEqual({m['id'] for m in fresh['marks']},{'f1','f2'})
        edited=copy.deepcopy(fresh);edited['notes'][0]['text']='reader edit';edited['verdict']['org/repo#1']='approve';edited['read']={'b2':True}
        reloaded=self.hydrate(data,edited)
        self.assertEqual(reloaded['notes'][0]['text'],'reader edit');self.assertEqual(reloaded['verdict'],edited['verdict']);self.assertEqual(reloaded['read'],{'b2':True})
        edited['notes']=[];self.assertEqual(self.hydrate(data,edited)['notes'],[])
        edited['marks']=[m for m in edited['marks'] if m['id']=='f2']
        self.assertEqual([m['id'] for m in self.hydrate(data,edited)['marks']],['f2'])
        # Live serving continues to use canonical server events rather than a stale browser cache.
        live=self.hydrate(data,edited,'serve');self.assertEqual(live['notes'][0]['text'],'original');self.assertEqual(live['read'],{'b1':True})

    def test_legacy_refresh_total_budget_and_completed_summary_preserve_saved_memory(self):
        def run(argv,**kwargs):
            group,tool=read_tool(argv)
            args=json.loads(Path(argv[argv.index('--args-file')+1]).read_text());calls.append(tool)
            return subprocess.CompletedProcess(argv,0,json.dumps(fixture(group,tool,**args)),'')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1','REVIEW_COCKPIT_QODO':'qodo'}):
            sd=Path(tmp)/'s';sd.mkdir();old={'session':'s','prs':[{'repo':'org/repo','number':n} for n in (1,2,3)],'memory':{'enabled':'False','auto_commit':'False','amr':'memory/amr','okf':'memory/okf'}}
            path=sd/'review-data.json';path.write_text(json.dumps(old));original=path.read_bytes()
            cfg=util.load_config();cfg['memory']['enabled']=False;cfg['notes']['enabled']=False;cfg['overlaps']['enabled']=False
            calls=[]
            with mock.patch('cockpit.adapters.managed.MAX_OPERATION_CALLS',18),mock.patch('subprocess.run',side_effect=run):
                with self.assertRaises(BudgetExceeded):collect.refresh(sd,cfg)
            self.assertLessEqual(len(calls),18);self.assertEqual(path.read_bytes(),original)
            calls=[]
            with mock.patch('cockpit.adapters.managed.MAX_OPERATION_CALLS',64),mock.patch('subprocess.run',side_effect=run),mock.patch.object(qodo_cli,'fetch',getattr(qodo_cli,'_real_fetch',qodo_cli.fetch)):
                collect.refresh(sd,cfg)
            data=json.loads(path.read_text());self.assertTrue(data['product'])
            self.assertEqual(data['managed_read_budget']['calls'],len(calls));self.assertLessEqual(len(calls),64)
            self.assertEqual(data['memory']['auto_commit'],'False')

    def test_enrich_contract_refs_pin_base_refuse_wrong_sha_and_carry_partial_metadata(self):
        from cockpit.enrich import enrich
        result={'content':'one line','resolved_ref':'c'*40,'truncated':True,'content_truncated_upstream':True,'next_start_line':2,'last_fetched_at':'2020-01-01'}
        requests=[]
        def read(group,tool,**args):
            if tool=='read-file':requests.append(args);return result.copy()
            return fixture(group,tool,**args)
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}),mock.patch.object(Client,'read',side_effect=read),mock.patch.object(qodo_cli,'fetch',return_value=None):
            sd=Path(tmp)/'s';sd.mkdir();pr=Client().change('org/repo',1)
            cfg=util.load_config();cfg['memory']['enabled']=False
            collect.build([pr],cfg,demo=True,session='s',dest=sd)
            payload={'system':{'components':[{'id':'a','name':'A','repo':'org/repo'},{'id':'b','name':'B'}],'contracts':[{'id':'c','name':'Contract','kind':'type','from':'a','to':['b'],'used':[{'repo':'org/repo','path':'source.py','from':1,'to':20}]}]}}
            enrich(sd,payload)
            ref=json.loads((sd/'review-data.json').read_text())['system']['contracts'][0]['used'][0]
            self.assertEqual(requests[-1]['ref'],'c'*40);self.assertIsNone(ref['excerpt_cut'])
            self.assertFalse(ref['source_evidence']['complete']);self.assertEqual(ref['source_evidence']['next_start_line'],2)
            self.assertEqual(ref['source_evidence']['last_fetched_at'],'2020-01-01');self.assertEqual(ref['source_evidence']['identity']['provider_host'],'github.com')
            mapped=system.resolve(json.loads((sd/'review-data.json').read_text()))['contracts'][0]['used'][0]
            self.assertEqual(mapped['source_evidence']['next_start_line'],2)
            result.update(resolved_ref='d'*40)
            enrich(sd,payload);ref=json.loads((sd/'review-data.json').read_text())['system']['contracts'][0]['used'][0]
            self.assertNotIn('excerpt',ref);self.assertIn('does not match',ref['source_evidence']['reason'])
            result.update(resolved_ref='c'*40,truncated=False,content_truncated_upstream=False,next_start_line=None,content='\n'.join(['line']*20))
            enrich(sd,payload);ref=json.loads((sd/'review-data.json').read_text())['system']['contracts'][0]['used'][0]
            self.assertTrue(ref['source_evidence']['complete']);self.assertEqual(ref['excerpt_cut'],0)
            legacy=json.loads((sd/'review-data.json').read_text());legacy['system']['contracts'][0]['used'][0].pop('source_evidence')
            mapped=system.resolve(legacy)['contracts'][0]['used'][0]
            self.assertIsNone(mapped['excerpt_cut']);self.assertEqual(mapped['source_evidence']['origin'],'legacy')
            data=json.loads((sd/'review-data.json').read_text());data['prs'][0]['base_sha']='e'*40;util.write_json(sd/'review-data.json',data)
            enrich(sd,payload);ref=json.loads((sd/'review-data.json').read_text())['system']['contracts'][0]['used'][0]
            self.assertEqual(requests[-1]['ref'],'e'*40);self.assertNotIn('excerpt',ref)

    def test_mutable_or_short_source_reads_never_claim_complete_or_zero_cut(self):
        for requested,resolved,content in [('main','c'*40,'one'),(HEAD,HEAD,'')]:
            def read(group,tool,**args):
                return {'content':content,'resolved_ref':resolved,'last_fetched_at':'2020-01-01'} if tool=='read-file' else fixture(group,tool,**args)
            with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}),mock.patch.object(Client,'read',side_effect=read):
                got=system._excerpt('org/repo','a.py',requested,1,20,{'n':0,'until':__import__('time').monotonic()+90})
            self.assertIsNone(got[1]);self.assertIsNone(got[2]['complete']);self.assertEqual(got[2]['resolved_ref'],resolved)

    def test_product_ask_global_denial_stops_agent_loop_and_uses_selected_client(self):
        cat={'codebase read-file':{'description':'Read source','params':['repo','path'],'required':['repo','path']}}
        response=subprocess.CompletedProcess([],1,'{"error":{"code":"invalid_token"}}','')
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1','REVIEW_COCKPIT_QODO':'selected-qodo'}):
            sd=Path(tmp);(sd/'review-data.json').write_text('{"product":true}')
            call={'tool':'codebase read-file','args':{'repo':'org/repo','path':'a.py'}}
            with mock.patch('subprocess.run',return_value=response) as process:
                with self.assertRaises(PermissionDenied):ask.run_read(call,cat,sd,10)
            self.assertEqual(process.call_count,1);self.assertEqual(process.call_args.args[0][0],'selected-qodo')
            with mock.patch.object(ask,'pick',return_value='codex'),mock.patch.object(ask,'catalog',return_value=cat),mock.patch.object(ask,'_turn',return_value=json.dumps({'calls':[call]})) as turn,mock.patch('subprocess.run',return_value=response) as process:
                with self.assertRaises(PermissionDenied):ask.ask('question',sd)
            self.assertEqual(turn.call_count,1);self.assertEqual(process.call_count,1)
            self.assertTrue(ask._ONE.acquire(blocking=False));ask._ONE.release()
            with mock.patch.object(ask,'_CATALOG',None),mock.patch.object(ask,'_MISSED',[None]),mock.patch('subprocess.run',return_value=response):
                with self.assertRaises(PermissionDenied):ask.catalog()
