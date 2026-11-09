"""Session-local mode, source revision selection and partial reading-plan controls."""
import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from cockpit import attention, collect, managed_work, product, system, util, view
from cockpit.adapters import qodo_cli
from cockpit.adapters.managed import Client, ReadError
from tests.test_product import ID, HEAD, fixture, page


class ContextAndCoverageTests(unittest.TestCase):
    def test_session_config_and_operations_do_not_leak_mode_after_success_or_error(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'0'}):
            sd=Path(tmp); (sd/'review-data.json').write_text('{"product":true,"prs":[]}')
            self.assertFalse(product.enabled())
            cfg=util.session_config(sd)
            self.assertFalse(cfg['memory']['enabled']); self.assertFalse(product.enabled())
            self.assertEqual(os.environ['REVIEW_COCKPIT_PRODUCT'],'0')
            def source(*args, **kwargs):
                self.assertTrue(product.enabled())
                raise ReadError('controlled failure')
            raw={'contracts':[{'id':'c','name':'C','used':[{'repo':'org/repo','path':'source.py','from':1,'to':1,'ref':HEAD}]}]}
            with mock.patch.object(system,'_excerpt',side_effect=source):
                with self.assertRaises(ReadError):system.normalize(raw,{'product':True,'prs':[]})
            self.assertFalse(product.enabled())
            from cockpit import ask
            with mock.patch.object(ask,'pick',side_effect=RuntimeError('no agent')):
                with self.assertRaises(RuntimeError):ask.ask('question',sd)
            self.assertFalse(product.enabled())
            with product.scope({'product':True}):
                self.assertTrue(product.enabled())
                with self.assertRaisesRegex(RuntimeError,'gh is unavailable'):util.gh(['read'])
            with mock.patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,'legacy result','')):
                self.assertEqual(util.gh(['read']),'legacy result')

    def test_request_context_resets_and_product_server_blocks_legacy_preflight(self):
        from cockpit.server import Handler
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'0'}):
            sd=Path(tmp); (sd/'review-data.json').write_text('{"product":true,"prs":[]}')
            handler=object.__new__(Handler); handler.sdir=sd; handler.server=SimpleNamespace(product=False,access_key='fixture-access')
            handler.headers={'Host':'127.0.0.1:8765','Authorization':'Bearer fixture-access'}; handler.path='/api/data'; handler._pick_session=lambda:True
            def selected(route):
                self.assertTrue(product.enabled()); raise RuntimeError('request error')
            handler._get_selected=selected
            with self.assertRaises(RuntimeError):handler.do_GET()
            self.assertFalse(product.enabled())
            (sd/'review-data.json').write_text('{"prs":[]}')
            handler._get_selected=lambda route:product.enabled()
            self.assertFalse(handler.do_GET())
            handler.server.product=True
            self.assertTrue(handler.do_GET()); self.assertFalse(product.enabled())
            with mock.patch('cockpit.server.threads.fetch') as preflight, mock.patch('cockpit.server.build_review') as preview:
                result=handler._publish({'dry_run':True},{'prs':[]})
            self.assertFalse(result['provider_writes']); preflight.assert_not_called(); preview.assert_not_called()

    def test_same_repository_implicit_source_requires_consistent_base_or_explicit_sha(self):
        prs=[{'repo':'org/repo','key':'org/repo#'+str(n),'identity':ID,'base':'main','base_sha':sha*40,'head':'feature'+str(n),'head_sha':HEAD}
             for n,sha in [(1,'c'),(2,'d')]]
        citation={'repo':'org/repo','path':'source.py','from':1,'to':1}
        requests=[]
        def read(group,tool,**args):
            self.assertEqual(tool,'read-file'); requests.append(args)
            return {'content':'source','resolved_ref':args['ref'],'truncated':False}
        def normalize(ref):
            raw={'contracts':[{'id':'c','name':'C','used':[ref]}]}
            return system.normalize(raw,{'product':True,'prs':prs})[0]['contracts'][0]['used'][0]
        with mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'0'}), mock.patch.object(Client,'read',side_effect=read):
            for ref in (citation,{**citation,'ref':'HEAD'},{**citation,'ref':'main'}):
                out=normalize(ref); self.assertFalse(out['source_evidence']['complete']); self.assertIn('ambiguous',out['source_evidence']['reason']); self.assertFalse(requests)
            unknown_repo = {**citation,'repo':'org/not-in-package'}
            out=normalize(unknown_repo);self.assertFalse(out['source_evidence']['complete']);self.assertFalse(requests)
            out=normalize({**citation,'ref':HEAD}); self.assertTrue(out['source_evidence']['complete']); self.assertEqual(requests[-1]['ref'],HEAD)
            prs[1]['base_sha']='c'*40
            out=normalize(citation); self.assertTrue(out['source_evidence']['complete']); self.assertEqual(requests[-1]['ref'],'c'*40)

    def test_partial_managed_hunks_retain_reading_ranges_with_adjacent_subset_disclosure(self):
        from cockpit.styles import render
        def read(group,tool,**args):
            result=fixture(group,tool,**args)
            if tool=='read-review-data' and args['kind']=='patch':
                result.update(complete=False)
                for item in result['items']:item['patch_complete']=False
            return result
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'0'}), mock.patch.object(Client,'read',side_effect=read), mock.patch.object(qodo_cli,'fetch',return_value=None):
            sd=Path(tmp)/'s';sd.mkdir();pr=Client().change('org/repo',1)
            cfg=util.load_config();cfg['memory']['enabled']=False
            collect.build([pr],cfg,demo=True,session='s',dest=sd)
            data=json.loads((sd/'review-data.json').read_text());pr=data['prs'][0]
            self.assertTrue(pr['files'][0]['hunks']);self.assertTrue(pr['attention']['ranges'])
            plan=attention.plan(pr);self.assertFalse(plan['coverage']['complete']);self.assertEqual(plan['coverage']['scope'],'observed_subset')
            self.assertIn('observed patch subset',attention.plan_markdown(pr))
            public=view.view_data(sd,data=data)['prs'][0];self.assertFalse(public['attention']['coverage']['complete'])
            source=(util.ROOT/'app/styles/package.js').read_text();code=source[source.index('function planBar('):source.index('function segList(')]
            setup="const planFiles=()=>[{v:2,t:{deep:2},f:{path:'a.py'},p:{key:'p'},ty:'code'}],byType=()=>false,TIERS=['deep'],TIER_NAME={},esc=String,planViewTabs=()=>'',segList=()=>'',S={};let SEGS=[];"
            script="const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={};vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(c.result);"
            def draw(pr):
                result=subprocess.run(['node','-e',script],input=json.dumps({'code':setup+code+';result=planBar(['+json.dumps(pr)+'],{map:false});'}),capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr);return result.stdout
            html=draw(public);self.assertIn('Coverage incomplete',html);self.assertIn('observed changed lines',html);self.assertIn('100% of observed subset',html)
            self.assertIn('Coverage incomplete',render('package',sd,data=data))
            legacy=copy.deepcopy(pr);legacy.pop('product',None)
            with mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'0'}):
                self.assertNotIn('coverage',attention.plan(legacy))
                public.pop('product',None);self.assertNotIn('Coverage incomplete',draw(public));self.assertIn('2 changed lines',draw(public))

    def test_unmapped_legacy_native_rediscovery_failure_is_bounded_and_preserves_saved_snapshot(self):
        # This retained limitation is explicit: no identity/key migration is introduced.
        old={'collection':{'requested_refs':['https://dev.azure.test/org/project/_git/repo/pullrequest/7']},'prs':[{'repo':'project/repo','number':7,'key':'project/repo#7','identity':{**ID,'repo':'project/repo','provider':'azure','provider_host':'dev.azure.test'}}]}
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            sd=Path(tmp);p=sd/'review-data.json';p.write_text(json.dumps(old));before=p.read_bytes()
            with mock.patch.object(Client,'identity',side_effect=ReadError('registry unavailable')) as discover:
                with self.assertRaises(ReadError):managed_work.refresh(sd,old,{})
            self.assertEqual(discover.call_count,1);self.assertEqual(p.read_bytes(),before);self.assertFalse(product.enabled())

    def test_native_azure_collect_save_refresh_reuses_exact_saved_identity_without_discovery(self):
        identity={'repo':'org/project/repo','provider':'azure_devops','provider_host':'dev.azure.com','repository_url':'https://dev.azure.com/org/project/_git/repo'}
        url=identity['repository_url']+'/pullrequest/1';calls=[];refreshing=False
        def read(group,tool,**args):
            calls.append((tool,args))
            if tool=='search-repos':
                self.assertFalse(refreshing,'refresh must reuse the saved collection input identity')
                return {'repos':[{'full_name':identity['repo'],'provider':identity['provider'],'html_url':identity['repository_url']}],'truncated':False}
            if tool=='get-change-context':
                self.assertEqual(args['repo'],identity['repo']);self.assertEqual(args['provider_host'],identity['provider_host'])
                result=fixture(group,tool,**args);result['change']['url']=url
                if refreshing:result['head_sha']='d'*40
                return result
            return fixture(group,tool,**args)
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}),mock.patch.object(Client,'read',side_effect=read),mock.patch.object(qodo_cli,'fetch',return_value=None),mock.patch.object(collect,'SESSIONS',Path(tmp)):
            cfg=util.load_config();cfg['memory']['enabled']=False;cfg['notes']['enabled']=False;cfg['overlaps']['enabled']=False
            _,sd=managed_work.collect([url],None,cfg)
            old=json.loads((sd/'review-data.json').read_text());self.assertEqual(old['collection']['collected_refs'],[url]);self.assertEqual(old['prs'][0]['identity'],identity)
            refreshing=True;calls.clear();managed_work.refresh(sd,old,cfg)
            self.assertNotIn('search-repos',[tool for tool,args in calls])
            saved=json.loads((sd/'review-data.json').read_text());self.assertEqual(saved['prs'][0]['head_sha'],'d'*40);self.assertEqual(saved['prs'][0]['identity'],identity)
            # Older sessions with an exact returned native URL also have an unambiguous binding.
            old['collection'].pop('collected_refs');calls.clear();managed_work.refresh(sd,old,cfg)
            self.assertNotIn('search-repos',[tool for tool,args in calls])

    def test_canonical_managed_findings_preserve_origin_run_sha_and_neutral_before_pr_tag(self):
        from cockpit.risk import approval
        records=[{'id':str(i),'title':'Finding '+str(i),'description':'Useful evidence','review_source':origin,'git_sha':sha*40,'review_run_id':i,'created_at':'2026-11-01T00:00:00Z','finding_source':'IssueFinding','file_path':'a.py','start_line':1}
                 for i,origin,sha in [(1,'local_skill','e'),(2,'git_pr','b'),(3,'shift_left','f'),(4,None,'a')]]
        response={'review_session':None,'findings':records}
        def read(group,tool,**args):
            return copy.deepcopy(response) if tool=='findings' else fixture(group,tool,**args)
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}),mock.patch.object(Client,'read',side_effect=read),mock.patch.object(qodo_cli,'fetch',getattr(qodo_cli,'_real_fetch',qodo_cli.fetch)):
            sd=Path(tmp)/'s';sd.mkdir();pr=Client().change('org/repo',1)
            cfg=util.load_config();cfg['memory']['enabled']=False;cfg['notes']['enabled']=False;cfg['overlaps']['enabled']=False;cfg['adapters']=['qodo_comments']
            collect.build([pr],cfg,demo=True,session='s',dest=sd)
            data=json.loads((sd/'review-data.json').read_text());stored=data['prs'][0];public=view.view_data(sd,data=data)['prs'][0]
            self.assertEqual(len(stored['findings']),4);self.assertFalse(product.qodo_current(stored));self.assertFalse(public['product_evidence']['qodo_complete'])
            self.assertNotIn('Qodo reviewed every PR.',approval(data,'low')['reasons'])
            for raw,finding in zip(records,public['findings']):
                self.assertEqual(finding['review_source'],raw['review_source'] or 'unknown');self.assertEqual(finding['git_sha'],raw['git_sha']);self.assertEqual(finding['commit'],raw['git_sha']);self.assertEqual(finding['review_run_id'],raw['review_run_id']);self.assertTrue(finding['qodo_id'])
            self.assertEqual(public['findings'][0]['source'],'qodo-local');self.assertEqual(public['findings'][0]['local']['origin'],'managed')
            for finding in public['findings'][1:]:self.assertEqual(finding['source'],'qodo');self.assertIsNone(finding['local'])
            source=(util.ROOT/'app/styles/kit.js').read_text();tag=source[source.index('  const localTag ='):source.index('  /* a rule, convention')]
            done=source[source.index('  const localDone ='):source.index('  /* render code')]
            script="const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={esc:String,md:String};vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));"
            result=subprocess.run(['node','-e',script],input=json.dumps({'code':tag+done+';result={tags:'+json.dumps(public['findings'])+'.map(localTag),closed:localDone([{...'+json.dumps(public['findings'][0])+',status:"resolved"}])};'}),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);html=json.loads(result.stdout)
            self.assertIn('before the PR',html['tags'][0]);self.assertNotIn('author',html['tags'][0]);self.assertNotIn('fix',html['tags'][0]);self.assertEqual(html['tags'][1],'');self.assertIn('shift_left',html['tags'][2]);self.assertIn('origin unknown',html['tags'][3]);self.assertEqual(html['closed'],'')
            response['review_session']={'id':'completed-run','status':'completed','review_complete':True,'commit_sha':HEAD}
            current=Client().change('org/repo',1);qodo_cli.collect(current,cfg);current['qodo_source']='cli';self.assertTrue(product.qodo_current(current))
