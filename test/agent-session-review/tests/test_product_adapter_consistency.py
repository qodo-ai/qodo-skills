"""Shared local patch proof, truncated authored notes and non-advancing page controls."""
import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cockpit import attention, collect, notes, product, util, view
from cockpit.adapters import qodo_cli
from cockpit.adapters.managed import Client, ReadError
from cockpit.risk import approval
from tests.test_product import fixture, page, ID, HEAD, REV


class AdapterConsistencyTests(unittest.TestCase):
    def verdict(self, pr, decision):
        source=(util.ROOT/'app/styles/package.js').read_text()
        code=source[source.index('const vdLink ='):source.index('function crumb()')]
        code=source[source.index('function productCiUnknown('):source.index('\n',source.index('function productCiUnknown('))]+code
        script="const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={C:{product:true},LIVE:{},RK:{approval:x.decision,level:'low'},CI_BAD:[],VDICON:{ok:'',no:'',unknown:''},KIT:{}};vm.createContext(c);vm.runInContext('const esc=String,strip=String,RW=String;KIT.openFindings=()=>[];const store={get:(k,d)=>d,set(){}},document={addEventListener(){},querySelector:()=>null,getElementById:()=>null};KIT.allFindings=()=>[];const prs=()=>['+JSON.stringify(x.pr)+'];'+x.code+';html=bVerdict();',c);process.stdout.write(c.html);"
        result=subprocess.run(['node','-e',script],input=json.dumps({'pr':pr,'decision':decision,'code':code}),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);return result.stdout

    def test_managed_change_build_projection_plan_approval_and_default_verdict_share_patch_proof(self):
        cases=[('incomplete-file-list',False,'Changed-file list'),('missing-item-proof',False,'Patch evidence'),('truncated',False,'Patch evidence'),('unavailable',False,'Patch evidence'),('no-patch-read',False,'Patch evidence'),('empty-with-missing',False,'known changed files'),('populated-with-missing',False,'known changed files'),('complete',True,None),('genuinely-empty',True,None)]
        for case,complete,reason in cases:
            with self.subTest(case=case):
                def read(group,tool,**args):
                    result=fixture(group,tool,**args)
                    if tool=='get-change-context':
                        result['change']['changed_files']=2 if case in ('empty-with-missing','populated-with-missing') else 0 if case=='genuinely-empty' else 1
                    if tool=='read-review-data':
                        if args['kind']=='files':
                            if case=='incomplete-file-list':result['complete']=False
                            if case in ('empty-with-missing','genuinely-empty'):return page([])
                            if case=='no-patch-read':result['items'][0]['patch_available']=False
                        if args['kind']=='patch':
                            if case=='unavailable':raise ReadError('patch unavailable')
                            for item in result['items']:item['patch_complete']=None if case=='missing-item-proof' else True
                            if case=='truncated':result['complete']=False
                    return result
                with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}),mock.patch.object(Client,'read',side_effect=read),mock.patch.object(qodo_cli,'fetch',getattr(qodo_cli,'_real_fetch',qodo_cli.fetch)):
                    sd=Path(tmp)/'s';sd.mkdir();pr=Client().change('org/repo',1)
                    cfg=util.load_config();cfg['memory']['enabled']=False;cfg['notes']['enabled']=False;cfg['overlaps']['enabled']=False;cfg['adapters']=['qodo_comments']
                    collect.build([pr],cfg,demo=True,session='s',dest=sd)
                    data=json.loads((sd/'review-data.json').read_text());stored=data['prs'][0];projected=product.project_pr(stored)
                    self.assertTrue(product.qodo_current(stored));self.assertTrue(projected['product_evidence']['qodo_complete'])
                    self.assertEqual(projected['product_evidence']['patches_complete'],complete)
                    self.assertEqual(projected['product_evidence']['quality_complete'],complete)
                    self.assertEqual(attention.plan(stored)['coverage']['complete'],complete)
                    decision=approval(data,'low');self.assertEqual(decision['result'],'approve' if complete else 'human review')
                    html=self.verdict(view._pr_view(stored),decision)
                    self.assertIn('Risk review checks pass' if complete else 'Risk review needs attention',html)
                    if reason:
                        self.assertIn(reason,' '.join(decision['reasons']));self.assertIn(reason,html)
                    if case=='truncated':self.assertTrue(stored['files'][0]['hunks'])
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            self.assertEqual(approval({'prs':[{'key':'legacy#1','qodo_source':'comments','findings':[]}]},'low')['result'],'approve')

    def test_for_pr_rejects_truncated_parseable_page_fragments_on_every_page(self):
        pr={'repo':'org/repo','provider':'github','provider_host':'github.com','number':1,'head_sha':HEAD}
        answer={'lookupStatus':'found','prContext':{'id':'note','document':{'contentMarkdown':'intent','commitShaAtUpdate':HEAD}}}
        text=json.dumps(answer)
        for truncated in (0,1,None):
            calls=[]
            def read(group,tool,**args):
                if tool=='resolve-repository':return {'repo_ref':'opaque'}
                index=1 if args.get('read_cursor') else 0;calls.append(index)
                return {'result_is_page':True,'text':text[:-1] if index==0 else text[-1:], 'next_read_cursor':'opaque.next' if index==0 else None,'qar_operation_result_truncated':index==truncated}
            with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}),mock.patch.object(Client,'read',side_effect=read):
                result=notes.for_pr(pr,{}, {})
            if truncated is not None:
                self.assertEqual(result['status'],'unavailable');self.assertIn('truncated',result['why']);self.assertNotIn('pr',result)
                self.assertEqual(calls,[0] if truncated==0 else [0,1])
            else:self.assertEqual(result['pr']['markdown'],'intent');self.assertTrue(result['pr']['head_matches'])

    def test_nonadvancing_cursor_retains_raw_envelope_but_not_rejected_items(self):
        repeated=page([{'id':'one'}],next_cursor='opaque.#signed',complete=False)
        with mock.patch.object(Client,'read',side_effect=[copy.deepcopy(repeated),copy.deepcopy(repeated)]):
            result=Client().pages(ID,'comments',1,REV)
        self.assertEqual(result['items'],[{'id':'one'}]);self.assertFalse(result['complete']);self.assertEqual(result['status'],'bounded');self.assertIn('did not advance',result['error'])
        self.assertEqual(result['rejected_page'],repeated);self.assertEqual(len(result['pages']),1)
        advancing=[page([{'id':'one'}],next_cursor='opaque.1#',complete=False),page([{'id':'two'}],next_cursor='opaque.2?',complete=False),page([{'id':'three'}])]
        with mock.patch.object(Client,'read',side_effect=advancing) as read:
            result=Client().pages(ID,'comments',1,REV)
        self.assertEqual([item['id'] for item in result['items']],['one','two','three']);self.assertTrue(result['complete'])
        self.assertEqual([call.kwargs['cursor'] for call in read.call_args_list],[None,'opaque.1#','opaque.2?'])
        def read(group,tool,**args):
            result=fixture(group,tool,**args)
            if tool=='read-review-data' and args['kind']=='files':result.update(next_cursor='same.cursor',complete=False)
            return result
        with mock.patch.object(Client,'read',side_effect=read):pr=Client().change('org/repo',1)
        self.assertEqual(len(pr['files']),1);self.assertFalse(pr['files_complete'])
        self.assertIn('rejected_page',pr['read_evidence']['sections']['files'])
