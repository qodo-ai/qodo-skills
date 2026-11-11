"""Scoped product risk labels and original pre-PR finding coordinates."""
import copy
import json
import os
import subprocess
import unittest
from unittest import mock

from cockpit import product, util, view
from cockpit.adapters import qodo_cli
from cockpit.adapters.managed import Client
from cockpit.risk import approval
from tests.test_product import fixture, HEAD


class ProductFindingScopeTests(unittest.TestCase):
    def node(self, code, context):
        script="const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c=x.context;vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));"
        result=subprocess.run(['node','-e',script],input=json.dumps({'code':code,'context':context}),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def pr(self):
        def read(group,tool,**args):
            result=fixture(group,tool,**args)
            if tool=='read-review-data' and args['kind']=='patch':
                for item in result['items']:item['patch_complete']=True
            return result
        with mock.patch.object(Client,'read',side_effect=read):p=Client().change('org/repo',1)
        p.update(qodo_source='cli',qodo_review={'status':'completed','review_complete':True,'commit':HEAD,'run_id':'run','bounded':False},findings=[])
        return p

    def test_product_risk_recommendation_does_not_claim_merge_readiness(self):
        source=(util.ROOT/'app/styles/package.js').read_text()
        code=source[source.index('const vdLink ='):source.index('function crumb()')]
        code=source[source.index('function productCiUnknown('):source.index('\n',source.index('function productCiUnknown('))]+code
        for case in ('passing','failing','partial-ci','partial-comments'):
            with self.subTest(case=case),mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
                p=self.pr();p['checks']=[{'name':'build','state':'FAILURE' if case=='failing' else 'SUCCESS'}]
                if case=='partial-ci':p['read_evidence']['sections']['checks']['complete']=False
                if case=='partial-comments':p['read_evidence']['sections']['comments']['complete']=False
                data={'product':True,'prs':[p]};decision=approval(data,'low');self.assertEqual(decision['result'],'approve')
                public=view._pr_view(p)
                context={'p':public,'C':{'product':True},'LIVE':{},'RK':{'approval':decision,'level':'low'},'CI_BAD':['FAILURE'],'CI_OK':['SUCCESS','NEUTRAL','SKIPPED'],'VDICON':{'ok':'','no':'','unknown':''},'KIT':{}}
                setup='const esc=String,strip=String,RW=String;KIT.openFindings=()=>[];const store={get:(k,d)=>d,set(){}},document={addEventListener(){},querySelector:()=>null,getElementById:()=>null};KIT.allFindings=()=>[];const prs=()=>[p];'
                html=self.node(setup+code+';result=bVerdict();',context)
                self.assertIn('Risk review checks pass',html);self.assertIn('not merge readiness',html);self.assertNotIn('Ready to merge',html)
                if case=='failing':self.assertIn('#1',html);self.assertIn('PRs failing CI',html)
                if case=='partial-ci':self.assertIn('coverage unknown',html)
                context['C']['product']=False
                legacy=self.node(setup+code+';result=bVerdict();',context)   # standalone, nothing read live: conflicts are unknown
                self.assertIn('Not ready to merge',legacy);self.assertIn('merge conflicts',legacy);self.assertNotIn('Risk review checks pass',legacy)
                context['LIVE']={p['key']:{'state':'OPEN','merge_state':'CLEAN','review_decision':'APPROVED','unresolved':0,'checks':p['checks']}}
                legacy=self.node(setup+code+';result=bVerdict();',context)   # every threshold read
                if case=='failing':self.assertIn('Not ready to merge',legacy);self.assertIn('CI failing on 1 PR',legacy)
                else:self.assertIn('Ready to merge',legacy);self.assertNotIn('Not ready to merge',legacy)

    def test_product_verdict_has_no_merge_thresholds_or_merge_risk_row(self):
        source=(util.ROOT/'app/styles/package.js').read_text()
        code=source[source.index('function productCiUnknown('):source.index('\n',source.index('function productCiUnknown('))]
        code+=source[source.index('const vdLink ='):source.index('function crumb()')]
        self.assertIn('w === "verdict" && !C.product',source)   # no Verdict settings wrench in product mode
        p=self.pr();p['checks']=[{'name':'build','state':'SUCCESS'}]
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            decision=approval({'product':True,'prs':[p]},'low');public=view._pr_view(p)
        rules={'sev':[],'ci':False,'conflicts':False,'review':False,'comments':False}   # every threshold switched off
        setup='const esc=String,strip=String,RW=String;KIT.openFindings=()=>[];KIT.allFindings=()=>[];const prs=()=>[p];'
        setup+='const store={get:()=>('+json.dumps(rules)+'),set(){}},document={addEventListener(){},querySelector:()=>null,getElementById:()=>null};'
        for product in (True,False):
            with self.subTest(product=product):
                context={'p':public,'C':{'product':product},'LIVE':{},'RK':{'approval':decision,'level':'low'},'CI_BAD':['FAILURE'],'CI_OK':['SUCCESS','NEUTRAL','SKIPPED'],'VDICON':{'ok':'','no':'','unknown':''},'KIT':{}}
                html=self.node(setup+code+';result=bVerdict();',context)
                self.assertNotIn('>Merge Risk<',html)
                if product:self.assertNotIn('vd-t off',html);self.assertIn('not merge readiness',html)
                else:self.assertIn('vd-t off',html)

    def test_standalone_verdict_blocks_running_or_missing_ci_and_product_never_dims_severities(self):
        source=(util.ROOT/'app/styles/package.js').read_text()
        code=source[source.index('function productCiUnknown('):source.index('\n',source.index('function productCiUnknown('))]
        code+=source[source.index('const vdLink ='):source.index('function crumb()')]
        p=self.pr()
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):public=view._pr_view(p)
        rules={'sev':['high'],'ci':True,'conflicts':True,'review':True,'comments':True}
        setup='const esc=String,strip=String,RW=String;KIT.openFindings=()=>[{severity:"low"}];KIT.allFindings=()=>[{severity:"low"}];const prs=()=>[p];'
        setup+='const store={get:()=>('+json.dumps(rules)+'),set(){}},document={addEventListener(){},querySelector:()=>null,getElementById:()=>null};'
        for checks,want in (([{'state':'IN_PROGRESS'}],'CI still running on 1 PR'),([],'no passing CI checks on 1 PR'),([{'state':'SKIPPED'},{'state':'NEUTRAL'}],'no passing CI checks on 1 PR'),([{'state':'SUCCESS'}],'Ready to merge')):
            with self.subTest(checks=checks):
                live={p['key']:{'state':'OPEN','merge_state':'CLEAN','review_decision':'APPROVED','unresolved':0,'checks':checks}}
                context={'p':public,'C':{'product':False},'LIVE':live,'RK':None,'CI_BAD':['FAILURE'],'CI_OK':['SUCCESS','NEUTRAL','SKIPPED'],'VDICON':{'ok':'','no':'','unknown':''},'KIT':{}}
                html=self.node(setup+code+';result=bVerdict();',context);self.assertIn(want,html)
                if want=='Ready to merge':self.assertNotIn('Not ready',html);self.assertIn('vd-s low off',html)   # a Low finding below the High threshold
        context['C']={'product':True}
        self.assertNotIn(' off"',self.node(setup+code+';result=bVerdict();',context))   # product mode has no thresholds to dim by

    def render(self,p):
        package=(util.ROOT/'app/styles/package.js').read_text();app=(util.ROOT/'app/app.js').read_text()
        code=package[package.index('const findingOnCurrentCode ='):package.index('\n',package.index('const findingOnCurrentCode ='))]+'\n'
        code+=package[package.index('function vFindings('):package.index('/* ---------- notes:')]
        code+=package[package.index('function unitsOf('):package.index('const UNITS =')]
        code+=app[app.index('function findingView('):app.index('function sortedFindings(')]
        setup="""const esc=s=>String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c])),md=esc,mdi=esc,isOpen=f=>!f.status||f.status==='open',srcName=()=> 'Qodo',shortPr=String,scansHtml=()=>'',productEvidenceUnknown=()=>false;
const anchors=[],noteHtml=(id,anchor)=>{anchors.push(anchor);return '';};KIT.localTag=()=> 'before the PR';KIT.localDone=()=>'';KIT.isConvention=()=>false;const prs=()=>C.prs;
const collapseRule=()=>null,sevPill=()=>'',localPill=()=>'',markbar=()=>'',notes=()=>[],noteView=()=>'',DST={};
"""
        context={'C':{'product':True,'prs':[p]},'S':{'open':{},'showCollapsed':{}},'EXPAND':False,'sevRank':{},'KIT':{}}
        return self.node(setup+code+';result={primary:vFindings(),anchors,app:findingView(C.prs[0].findings[0],C.prs[0],null),unitFindings:unitsOf(C.prs[0]).flatMap(u=>u.findings).map(f=>f.id)};',context)

    def test_original_prepr_location_is_preserved_without_unverified_current_anchor(self):
        cases=[('old', 'a'*40,'RIGHT',False),('removed',HEAD,'LEFT',False),('unknown-commit',None,'RIGHT',False),('unknown-side',HEAD,None,False),('current',HEAD,'RIGHT',True)]
        for name,sha,side,current in cases:
            with self.subTest(case=name),mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
                p=self.pr();raw={'id':'f','title':'Useful finding','description':'Original evidence','review_source':'local_skill','git_sha':sha,'review_run_id':7,'file_path':'a.py','start_line':1,'end_line':2,'side':side}
                original=copy.deepcopy(raw);finding=qodo_cli.to_finding(p,raw);p['findings']=[finding]
                p['attention']={'blocks':[{'id':'b','path':'a.py','from':1,'to':1,'lines':1,'tier':'review'}]}
                public=view._pr_view(p);f=public['findings'][0];location=f['local']['source_location']
                self.assertEqual(raw,original);self.assertEqual(location,{'path':'a.py','line':1,'end_line':2,'side':side,'git_sha':sha,'review_run_id':7})
                self.assertEqual(f['side'],side);self.assertEqual(f['local']['current_anchor'],current)
                rendered=self.render(public)
                if current:
                    self.assertEqual(f['path'],'a.py');self.assertEqual(f['line'],1);self.assertEqual(rendered['anchors'][0]['side'],'new')
                    self.assertIn('data-act="gofile"',rendered['app']);self.assertTrue(rendered['unitFindings'])
                else:
                    self.assertIsNone(f['path']);self.assertIsNone(f['line']);self.assertIsNone(f['end_line'])
                    self.assertNotIn('path',rendered['anchors'][0]);self.assertNotIn('line',rendered['anchors'][0]);self.assertNotIn('side',rendered['anchors'][0])
                    self.assertIn('Original source: a.py:1',rendered['primary']);self.assertIn('Original source: a.py:1',rendered['app']);self.assertNotIn('data-act="gofile"',rendered['app']);self.assertFalse(rendered['unitFindings'])
                self.assertEqual(f['title'],'Useful finding');self.assertEqual(f['body'],'Original evidence');self.assertEqual(f['review_run_id'],7);self.assertEqual(f['git_sha'],sha)

    def test_saved_managed_findings_without_anchor_metadata_stay_source_scoped(self):
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            p=self.pr();p['findings']=[{'id':'old-saved','source':'qodo-local','severity':'medium','title':'Kept finding','body':'Kept evidence','path':'a.py','line':1,'git_sha':'a'*40,'local':{'origin':'managed','commit':'a'*40}}]
            p['attention']={'blocks':[{'id':'b','path':'a.py','from':1,'to':1,'lines':1,'tier':'review'}]}
            rendered=self.render(view._pr_view(p))
            self.assertIn('Original source: a.py:1',rendered['primary']);self.assertIn('Original source: a.py:1',rendered['app'])
            self.assertNotIn('line',rendered['anchors'][0]);self.assertNotIn('data-act="gofile"',rendered['app']);self.assertFalse(rendered['unitFindings'])

    def test_general_hosted_and_standalone_locations_retain_existing_semantics(self):
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            p=self.pr();hosted={'id':'f','review_source':'git_pr','git_sha':HEAD,'file_path':'a.py','start_line':1,'side':'LEFT'}
            finding=qodo_cli.to_finding(p,hosted);self.assertEqual(finding['path'],'a.py');self.assertEqual(finding['line'],1);self.assertNotIn('local',finding)
            p.pop('product',None);legacy={**hosted,'review_source':'local_skill'}
            finding=qodo_cli.to_finding(p,legacy);self.assertEqual(finding['path'],'a.py');self.assertEqual(finding['line'],1);self.assertNotIn('local',finding)

    def test_managed_pr_left_side_keeps_old_diff_note_and_block_coordinates(self):
        from cockpit import attention, collect
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            p=self.pr()
            p['files'][0]['hunks']=collect.parse_diff('+++ b/a.py\n@@ -1 +1 @@\n-old value\n+new value\n')['a.py']
            finding=qodo_cli.to_finding(p,{'id':'hosted-left','title':'Removed-side issue','description':'Old-line evidence','review_source':'git_pr','git_sha':HEAD,'file_path':'a.py','start_line':1,'side':'LEFT','action_level':'action_required'})
            self.assertEqual(finding['side'],'LEFT');self.assertNotIn('local',finding)
            p['findings']=[finding];computed,_=attention.compute(p)
            self.assertTrue(any(row['side']=='old' and row['tier'] in ('review','deep') for row in computed['ranges']))
            p['attention']={'blocks':[{'id':'old','path':'a.py','side':'old','from':1,'to':1,'lines':1,'tier':'review'}, {'id':'new','path':'a.py','side':'new','from':1,'to':1,'lines':1,'tier':'review'}]}
            rendered=self.render(view._pr_view(p))
            self.assertEqual(rendered['anchors'][0]['side'],'old')
            self.assertEqual(rendered['unitFindings'].count(finding['id']),1)
