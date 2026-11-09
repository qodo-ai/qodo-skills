"""Managed page truncation, partial live evidence and explicit citation-host controls."""
import base64
import copy
import json
import os
import subprocess
import unittest
from unittest import mock

from cockpit import collect, managed_work, system, util
from cockpit.adapters.managed import Client, ScopedPermissionDenied, PermissionDenied
from tests.test_product import fixture, page, ID, HEAD, REV


class ReadQualificationTests(unittest.TestCase):
    def test_cli_pages_reject_truncation_before_items_on_first_and_terminal_pages(self):
        for bad_index in (0,1):
            records=[page([{'id':'accepted','filename':'a.py'}],complete=False,next_cursor='opaque.next'),page([{'id':'rejected','filename':'b.py'}],complete=True)]
            records[bad_index]['qar_operation_result_truncated']=True
            calls=[]
            def run(argv,**kwargs):
                from pathlib import Path
                args=json.loads(Path(argv[argv.index('--args-file')+1]).read_text());calls.append(args)
                return subprocess.CompletedProcess(argv,0,json.dumps(records[len(calls)-1]),'')
            with mock.patch('subprocess.run',side_effect=run):result=Client('fixture-qodo').pages(ID,'files',1,REV)
            self.assertFalse(result['complete']);self.assertEqual(result['status'],'bounded');self.assertIn('truncated',result['error'])
            self.assertEqual(result['items'],[] if bad_index==0 else [{'id':'accepted','filename':'a.py'}]);self.assertEqual(result['rejected_page'],records[bad_index])
            self.assertEqual(len(result['pages']),bad_index);self.assertEqual(result['next_cursor'],None if bad_index==0 else 'opaque.next')
        with mock.patch.object(Client,'read',side_effect=[page([{'id':'one','filename':'a.py'}],complete=False,next_cursor='opaque.next'),page([{'id':'two','filename':'b.py'}],qar_operation_result_truncated=False)]):
            result=Client().pages(ID,'files',1,REV)
        self.assertTrue(result['complete']);self.assertEqual([x['id'] for x in result['items']],['one','two'])

    def test_raw_change_never_normalizes_truncated_file_or_patch_proof(self):
        for kind in ('files','patch'):
            def read(group,tool,**args):
                result=fixture(group,tool,**args)
                if tool=='read-review-data' and args['kind']=='patch':
                    for item in result['items']:item['patch_complete']=True
                if tool=='read-review-data' and args['kind']==kind:result['qar_operation_result_truncated']=True
                return result
            with mock.patch.object(Client,'read',side_effect=read):pr=Client().change('org/repo',1)
            if kind=='files':self.assertFalse(pr['files_complete']);self.assertFalse(pr['files'])
            else:
                patch=pr['files'][0]['patch_evidence'];self.assertFalse(patch['complete']);self.assertFalse(pr['files'][0]['hunks']);self.assertFalse(patch['items']);self.assertTrue(patch['rejected_page']['qar_operation_result_truncated'])

    def test_live_partial_readiness_and_comments_remain_unknown_with_observed_lower_bound(self):
        pr={'repo':'org/repo','number':1,'key':'org/repo#1','identity':ID,'head_sha':HEAD,'collected_at':'2026-11-01'}
        for mode in ('partial-empty','partial-observed','denied','complete-empty','complete-observed'):
            def read(group,tool,**args):
                if tool=='read-review-data' and args['kind'] in ('readiness','comments'):
                    if mode=='denied':raise ScopedPermissionDenied('scope denied')
                    complete=mode.startswith('complete')
                    if args['kind']=='readiness':return page([{'state':'closed' if not complete else 'open','native_state':'DIRTY','draft':True}],complete=complete)
                    items=[{'created_at':'2026-11-02','body':'observed comment'}] if mode.endswith('observed') else []
                    return page(items,complete=complete)
                return fixture(group,tool,**args)
            with mock.patch.object(Client,'read',side_effect=read):result=managed_work.live_state([pr])[pr['key']]
            complete=mode.startswith('complete');observed=1 if mode.endswith('observed') else 0
            self.assertEqual(result['comments_complete'],complete);self.assertEqual(result['readiness_complete'],complete);self.assertEqual(result['new_comments_observed'],observed)
            self.assertEqual(result['new_comments'],observed if complete else None)
            self.assertEqual(result['state'],'OPEN' if complete else None);self.assertEqual(result['merge_state'],'DIRTY' if complete else None);self.assertEqual(result['draft'],True if complete else None)
            if mode.startswith('partial'):self.assertEqual(result['observed_readiness']['state'],'closed')
            # Execute the actual KIT live flags: incomplete observations cannot announce zero comments/closed/conflicts.
            if not complete:
                source=(util.ROOT/'app/styles/kit.js').read_text();code=source[source.index('        const f = {'):source.index('        if (f.commits)')]
                script="const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={v:x.v};vm.createContext(c);vm.runInContext(x.code+';result=f;',c);process.stdout.write(JSON.stringify(c.result));"
                run=subprocess.run(['node','-e',script],input=json.dumps({'v':result,'code':code}),capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr);flags=json.loads(run.stdout);self.assertFalse(flags['comments']);self.assertFalse(flags['closed']);self.assertFalse(flags['conflicts'])
        legacy={**pr};native={'headRefOid':HEAD,'state':'OPEN','comments':[],'reviews':[]}
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}),mock.patch.object(collect,'gh_json',return_value=native) as gh,mock.patch.object(collect.threads,'fetch',return_value={}):
            result=collect.live_state([legacy])[pr['key']]
        self.assertEqual(result['new_comments'],0);self.assertEqual(result['state'],'OPEN');gh.assert_called_once();self.assertNotIn('comments_complete',result)

    def test_live_truncated_terminal_comments_only_counts_accepted_observations(self):
        def read(group,tool,**args):
            if tool=='read-review-data' and args['kind']=='comments':
                return page([{'created_at':'2026-11-02'}],complete=False,next_cursor='next') if not args.get('cursor') else page([{'created_at':'2026-11-03'}],qar_operation_result_truncated=True)
            return fixture(group,tool,**args)
        pr={'repo':'org/repo','number':1,'key':'org/repo#1','identity':ID,'head_sha':HEAD,'collected_at':'2026-11-01'}
        with mock.patch.object(Client,'read',side_effect=read):result=managed_work.live_state([pr])[pr['key']]
        self.assertIsNone(result['new_comments']);self.assertFalse(result['comments_complete']);self.assertEqual(result['new_comments_observed'],1)
        self.assertTrue(result['read_evidence']['comments']['rejected_page']['qar_operation_result_truncated'])

    def test_external_citations_pass_host_to_discovery_and_never_share_cross_host_cache(self):
        repo='org/external';rows=[{'full_name':repo,'provider':'github','html_url':'https://'+host+'/'+repo} for host in ('forge-a.test','forge-b.test')];reads=[];search=[]
        def read(group,tool,**args):
            if tool=='search-repos':search.append(args);return {'repos':copy.deepcopy(rows),'truncated':False}
            if tool=='read-file':reads.append(args);return {'content':args['repo'],'resolved_ref':args['ref'],'truncated':False}
            self.fail('unexpected managed tool '+tool)
        def citation(host):return {'repo':repo,'provider_host':host,'path':'source.py','from':1,'to':1,'ref':HEAD}
        raw={'contracts':[{'id':'c','name':'C','used':[citation(host) for host in ('forge-a.test','forge-b.test','forge-a.test','missing.test')]}]}
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}),mock.patch.object(Client,'read',side_effect=read):result,warnings=system.normalize(raw,{'product':True,'prs':[]})
        refs=result['contracts'][0]['used'];self.assertEqual([r['repo'] for r in reads],['https://forge-a.test/'+repo,'https://forge-b.test/'+repo])
        for ref,host in zip(refs[:3],('forge-a.test','forge-b.test','forge-a.test')):
            self.assertEqual(ref['provider_host'],host);self.assertEqual(ref['source_evidence']['identity']['provider_host'],host);self.assertTrue(ref['source_evidence']['complete']);self.assertEqual(ref['excerpt'],'https://'+host+'/'+repo)
        self.assertTrue(refs[2]['source_evidence']['cache_hit']);self.assertFalse(refs[3]['source_evidence']['complete']);self.assertNotIn('excerpt',refs[3]);self.assertEqual(refs[3]['provider_host'],'missing.test')
        self.assertEqual(len(search),3)
        # Registered only elsewhere must not cause any read-file request for the supplied host.
        rows[:]=[rows[1]];reads.clear()
        with mock.patch.object(Client,'read',side_effect=read):result,_=system.normalize({'contracts':[{'id':'c','name':'C','used':[citation('forge-a.test')]}]},{'product':True,'prs':[]})
        self.assertFalse(reads);self.assertFalse(result['contracts'][0]['used'][0]['source_evidence']['complete'])
        legacy=citation('ignored-host.test');legacy['path']='legacy-host-proof.py'
        encoded=base64.b64encode(b'legacy text').decode()
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}),mock.patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,json.dumps({'content':encoded}),'')) as process:
            result,_=system.normalize({'contracts':[{'id':'c','name':'C','used':[legacy]}]},{'prs':[]})
        self.assertEqual(result['contracts'][0]['used'][0]['excerpt'],'legacy text');self.assertEqual(process.call_args.args[0][0],'gh')

    def test_nullable_comment_dates_keep_live_counts_unknown_without_losing_observations(self):
        pr={'repo':'org/repo','number':1,'key':'org/repo#1','identity':ID,'head_sha':HEAD,'collected_at':'2026-11-01'}
        for date in (None, '', 7):
            def read(group,tool,**args):
                if tool=='read-review-data' and args['kind']=='comments':
                    return page([{'created_at':date,'body':'date unavailable'}, {'created_at':'2026-11-02','body':'dated observation'}])
                return fixture(group,tool,**args)
            with mock.patch.object(Client,'read',side_effect=read):result=managed_work.live_state([pr])[pr['key']]
            self.assertFalse(result['comments_complete']);self.assertIsNone(result['new_comments'])
            self.assertEqual(result['new_comments_observed'],1);self.assertTrue(result['read_evidence']['comments']['complete'])
            self.assertEqual(len(result['read_evidence']['comments']['items']),2);self.assertTrue(result['readiness_complete']);self.assertIsNone(result['state'])

    def test_product_attention_does_not_skip_tests_on_partial_green_ci(self):
        from cockpit import attention
        from cockpit.semantic import annotate
        def test_pr(**kwargs):
            diff='+++ b/tests/test_new.py\n@@ -0,0 +1,2 @@\n+def test_added():\n+    assert True\n'
            files=[{'path':path,'hunks':hunks,'additions':2,'deletions':0} for path,hunks in collect.parse_diff(diff).items()]
            annotate(files)
            return {'key':'org/repo#1','files':files,'findings':[],**kwargs}
        for complete,state,tier in [(True,'SUCCESS','skip'),(False,'SUCCESS','skim'),(False,'FAILURE','review')]:
            pr=test_pr(product=True,checks=[{'name':'ci','state':state}])
            pr['read_evidence']={'sections':{'checks':{'complete':True},'statuses':{'complete':complete}}}
            result,_=attention.compute(pr)
            rows=[r for r in result['ranges'] if r['path']=='tests/test_new.py']
            self.assertTrue(rows);self.assertEqual({'review' if r['tier']=='deep' else r['tier'] for r in rows},{tier})
            if not complete and state=='SUCCESS':self.assertTrue(all('CI passed' not in r['evidence'] for r in rows))
        pr.pop('product');result,_=attention.compute(pr)
        self.assertTrue(any(r['tier'] in ('review','deep') for r in result['ranges'] if r['path']=='tests/test_new.py'))
        pr['checks']=[{'name':'ci','state':'SUCCESS'}];result,_=attention.compute(pr)
        self.assertEqual({r['tier'] for r in result['ranges'] if r['path']=='tests/test_new.py'},{'skip'})

    def test_missing_head_never_projects_prior_human_approval(self):
        for head in (None,HEAD,'b'*40):
            def read(group,tool,**args):
                result=fixture(group,tool,**args)
                if tool=='get-change-context':result['head_sha']=head
                if tool=='read-review-data' and args['kind']=='reviews':
                    result['items']=[{'actor':{'login':'human','type':'User'},'state':'APPROVED','reviewed_revision':HEAD,'submitted_at':'2026-11-02'}]
                return result
            with mock.patch.object(Client,'read',side_effect=read):pr=Client().change('org/repo',1)
            self.assertEqual(pr['approvals'],['human'] if head==HEAD else [])
            self.assertEqual(len(pr['read_evidence']['sections']['reviews']['items']),1)

    def test_undated_decisive_reviews_keep_collection_and_live_decisions_unknown(self):
        for date in (None, '', 7, '2026-11-03'):
            def read(group,tool,**args):
                result=fixture(group,tool,**args)
                if tool=='read-review-data' and args['kind']=='reviews':
                    result['items']=[{'actor':{'login':'human','type':'User'},'state':'APPROVED','reviewed_revision':HEAD,'submitted_at':'2026-11-02'}, {'actor':{'login':'human','type':'User'},'state':'CHANGES_REQUESTED','reviewed_revision':HEAD,'submitted_at':date}]
                return result
            with mock.patch.object(Client,'read',side_effect=read):
                pr=Client().change('org/repo',1)
                live=managed_work.live_state([pr])[pr['key']]
            known=isinstance(date,str) and bool(date)
            self.assertEqual(pr['review_decision_complete'],known);self.assertEqual(live['reviews_complete'],known)
            self.assertEqual(pr['approvals'],[]);self.assertEqual(live['review_decision'],'CHANGES_REQUESTED' if known else None)
            self.assertEqual(live['current_approved_by'],[] if known else None)
            self.assertTrue(pr['read_evidence']['sections']['reviews']['complete']);self.assertEqual(len(pr['read_evidence']['sections']['reviews']['items']),2)

    def test_dated_human_review_and_undated_bot_preserve_positive_decision(self):
        def read(group,tool,**args):
            result=fixture(group,tool,**args)
            if tool=='read-review-data' and args['kind']=='reviews':result['items']=[{'actor':{'login':'human','type':'User'},'state':'APPROVED','reviewed_revision':HEAD,'submitted_at':'2026-11-02'}, {'actor':{'login':'qodo[bot]','type':'Bot'},'state':'CHANGES_REQUESTED','submitted_at':None}]
            return result
        with mock.patch.object(Client,'read',side_effect=read):
            pr=Client().change('org/repo',1);live=managed_work.live_state([pr])[pr['key']]
        self.assertTrue(pr['review_decision_complete']);self.assertEqual(pr['approvals'],['human']);self.assertEqual(live['review_decision'],'APPROVED')

    def test_cli_auth_family_stops_before_partial_page_and_provider_limit_stays_scoped(self):
        for code in ('MT-AUTH-MISSING','MT-AUTH-EXPIRED','MT-AUTH-INVALID'):
            for metadata in ({},{'upstream_status':403}):
                error={'error':{'code':code,'metadata':metadata}}
                with mock.patch('subprocess.run',return_value=subprocess.CompletedProcess([],1,json.dumps(error),'')) as run:
                    with self.assertRaises(PermissionDenied):Client('fixture-qodo').pages(ID,'files',1,REV)
                self.assertEqual(run.call_count,1)
        error={'error':{'code':'MT-UPSTREAM-ERROR','metadata':{'upstream_status':403}}}
        with mock.patch('subprocess.run',return_value=subprocess.CompletedProcess([],1,json.dumps(error),'')) as run:
            partial=Client('fixture-qodo').pages(ID,'comments',1,REV)
        self.assertEqual(run.call_count,1);self.assertEqual(partial['status'],'permission_limited');self.assertFalse(partial['complete']);self.assertFalse(partial['items'])
