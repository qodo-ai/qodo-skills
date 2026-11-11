"""Product-only request-origin and normalized presentation-link boundaries."""
import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from cockpit import product, util, view
from cockpit.adapters import qodo_cli
from cockpit.adapters.managed import Client
from cockpit.server import Handler
from tests.test_product import fixture, page


class ProductWebTests(unittest.TestCase):
    def test_product_get_rejects_foreign_requests_before_payload_routes(self):
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            sd=Path(tmp);path=sd/'review-data.json';path.write_text('{"product":true}')
            handler=object.__new__(Handler);handler.sdir=sd;handler.server=SimpleNamespace(product=True,access_key='fixture-access')
            handler._json=lambda obj,code=200:(obj,code)
            for explicit in (True,False):
                handler.server.product=explicit
                for headers in ({'Host':'foreign.test:8765'},{'Host':'127.0.0.1:8765','Origin':'http://foreign.test:8765'}):
                    handler.headers=headers
                    for route in ('/api/data','/api/events','/api/memory','/api/app-state','/media/private.png','/app.js'):
                        handler.path=route
                        with mock.patch.object(handler,'_pick_session',return_value=True) as pick,mock.patch.object(handler,'_data') as data,mock.patch.object(handler,'_get_selected') as selected,mock.patch.object(Client,'read') as read:
                            self.assertEqual(handler.do_GET()[1],403);data.assert_not_called();selected.assert_not_called();read.assert_not_called()
                            if explicit:pick.assert_not_called()
            handler.server.product=False
            for host in ('127.0.0.1','localhost','[::1]'):
                handler.headers={'Host':host+':8765','Origin':'http://'+host+':8765','Authorization':'Bearer fixture-access'};handler.path='/api/data'
                with mock.patch.object(handler,'_pick_session',return_value=True),mock.patch.object(handler,'_data',return_value={'product':True}),mock.patch.object(handler,'_get_selected',return_value='allowed'):
                    self.assertEqual(handler.do_GET(),'allowed')
            path.write_text('{"product":false}')
            handler.headers={'Host':'foreign.test:8765','Origin':'http://foreign.test:8765'}
            with mock.patch.object(handler,'_pick_session',return_value=True),mock.patch.object(handler,'_data',return_value={}),mock.patch.object(handler,'_get_selected',return_value='legacy'):
                self.assertEqual(handler.do_GET(),'legacy')

    def render_links(self, pr):
        package=(util.ROOT/'app/styles/package.js').read_text();kit=(util.ROOT/'app/styles/kit.js').read_text();app=(util.ROOT/'app/app.js').read_text()
        code=kit[kit.index('  const esc ='):kit.index('  const cases =')]
        code+=kit[kit.index('  const localTag ='):kit.index('  /* a rule, convention')]
        code+='const KIT={localTag,localDone:()=>"",isConvention:()=>false};'
        code+=package[package.index('function pkTable('):package.index('document.addEventListener("click"',package.index('function pkTable('))]
        code+=package[package.index('function bPrs('):package.index('/* ---------- header actions:')]
        code+=package[package.index('function vFindings('):package.index('/* ---------- notes:')]
        for name in ('conceptByPath','knownFor'):
            start=app.index('function '+name+'(');code+=app[start:app.index('\nfunction ',start+1)]
        code+=app[app.index('function renderPR('):app.index('function renderPanel(')]
        code+=app[app.index('function findingView('):app.index('\nfunction ',app.index('function findingView(')+1)]
        setup="""const strip=String,pl=(n,s)=>n+' '+s,prs=()=>C.prs,prState=()=>'',STATE_NAME={},PRICON={},GHICON='',linesChip=()=>'',prChips=()=>'',pkgLines=()=>[0,0],shortPr=String;
const pkCells=()=>({merge:['',''],ci:['',''],open:0,bad:0,wait:0,passed:0,checks:0,add:0,del:0}),pkDot=()=>'',pkNum=()=>'';
const isOpen=f=>!f.status||f.status==='open',sevRank={},scansHtml=()=>'',productEvidenceUnknown=()=>false,noteHtml=()=>'';
const panelOrder=()=>[['findings','Findings']],draftsFor=()=>[],checksSummary=()=>'',liveNotes=()=>'',markbar=()=>'',renderPanel=()=>'',collapseRule=()=>null,sevPill=()=>'',localPill=()=>'',notes=()=>[],noteView=()=>'',mdi=md;
"""
        script="const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={C:{prs:[x.pr]},S:{open:{'pkt:org/repo':true},panel:{},showCollapsed:{},mem:{concepts:[]}},EXPAND:true};vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));"
        result=subprocess.run(['node','-e',script],input=json.dumps({'pr':pr,'code':code+setup+';result={cards:bPrs(),table:bPrs(true),findings:vFindings(),app:renderPR(C.prs[0])+C.prs[0].findings.map(f=>findingView(f,C.prs[0])).join("")};'}),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);return json.loads(result.stdout)

    def test_managed_unsafe_links_are_projected_without_mutating_evidence_or_stored_data(self):
        unsafe='javascript:alert(1)';valid='https://forge.test/org/repo/pull/1'
        raw={'review_session':None,'findings':[{'id':'f','title':'Finding','description':'Evidence','url':unsafe,'portal_url':'data:text/html,unsafe','file_path':'a.py','start_line':1}]}
        def read(group,tool,**args):
            if tool=='findings':return copy.deepcopy(raw)
            result=fixture(group,tool,**args)
            if tool=='get-change-context':result['change']['url']=valid
            if tool=='read-review-data' and args['kind']=='checks':return page([{'name':'observed','state':'success','url':unsafe}])
            return result
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}),mock.patch.object(Client,'read',side_effect=read),mock.patch.object(qodo_cli,'fetch',getattr(qodo_cli,'_real_fetch',qodo_cli.fetch)):
            pr=Client().change('org/repo',1);pr['findings']=qodo_cli.collect(pr,{});pr['scans']=[{'name':'scanner','url':unsafe}];pr['qodo']={'url':unsafe}
            # A separate contract-valid context can also contain an unsafe primary change URL.
            context=fixture('codebase','get-change-context');context['change']['url']=unsafe
            with mock.patch.object(Client,'read',side_effect=lambda g,t,**a:copy.deepcopy(context) if t=='get-change-context' else read(g,t,**a)):
                unsafe_pr=Client().change('org/repo',1)
            pr['url']=unsafe_pr['url'];pr['read_evidence']['context']=context
            sd=Path(tmp);stored={'session':'s','product':True,'prs':[pr]};path=sd/'review-data.json';path.write_text(json.dumps(stored));before=path.read_bytes()
            handler=object.__new__(Handler);handler.sdir=sd;handler.server=SimpleNamespace(product=False)
            projected=handler._data()['prs'][0]
            self.assertIsNone(projected['url']);self.assertIsNone(projected['findings'][0]['url']);self.assertIsNone(projected['findings'][0]['qodo_url']);self.assertIsNone(projected['checks'][0]['url']);self.assertIsNone(projected['scans'][0]['url']);self.assertIsNone(projected['qodo']['url'])
            self.assertEqual(json.dumps(projected['read_evidence']),json.dumps(pr['read_evidence']));self.assertEqual(projected['qodo_review_evidence'],pr['qodo_review_evidence']);self.assertEqual(path.read_bytes(),before)
            public=view._pr_view(projected)
            for name,html in self.render_links(public).items():self.assertNotRegex(html,r'href=["\']\s*(?:javascript:|data:)',name)
            stored['prs'][0]['url']=valid;stored['prs'][0]['findings'][0]['url']=valid;stored['prs'][0]['findings'][0]['qodo_url']=valid;path.write_text(json.dumps(stored))
            for name,html in self.render_links(view._pr_view(handler._data()['prs'][0])).items():self.assertIn('href="'+valid,html,name)
            stored['product']=False;stored['prs'][0].pop('product',None);stored['prs'][0]['url']=unsafe;stored['prs'][0]['findings'][0]['url']=unsafe;path.write_text(json.dumps(stored))
            for html in self.render_links(view._pr_view(handler._data()['prs'][0])).values():self.assertIn('href="'+unsafe,html)
            for value in ('javascript:alert(1)','java\nscript:alert(1)','data:text/html,hi','//foreign.test','https://',' http://example.test','https://example.test/\tbad'):
                self.assertIsNone(product.safe_http_url(value))
            self.assertEqual(product.safe_http_url(valid),valid)
