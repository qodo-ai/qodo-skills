"""Managed product contract controls. All subprocess calls are fixture-backed."""
import copy
import json
import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cockpit.adapters.managed import Client, ReadError, PermissionDenied, parse_ref
from cockpit import product
from cockpit.adapters import qodo_cli
from cockpit.risk import approval

REV = 'a' * 64
HEAD = 'b' * 40
ID = {'repo': 'org/repo', 'provider': 'github', 'provider_host': 'github.com', 'repository_url': 'https://github.com/org/repo'}


def page(items=(), **extra):
    return {'revision': REV, 'items': list(items), 'complete': True, 'next_cursor': None, **extra}


def fixture(group, tool, **args):
    if tool == 'search-repos':
        return {'repos': [{'full_name': ID['repo'], 'provider': ID['provider'], 'html_url': ID['repository_url']}], 'truncated': False}
    if tool == 'get-read-capabilities':
        return {'repository': ID, 'review_reads': {k: True for k in ('files', 'patch', 'comments', 'inline_comments', 'reviews', 'threads', 'checks', 'statuses', 'annotations', 'readiness', 'history')}}
    if tool == 'get-change-context':
        return {'revision': REV, 'head_sha': HEAD, 'base_sha': 'c'*40, 'change': {'title': 'Change', 'url': 'https://github.com/org/repo/pull/1', 'author': 'author', 'source_branch': 'feature', 'target_branch': 'main'}}
    if tool == 'read-review-data':
        if args['kind'] == 'files':
            return page([{'filename': 'a.py', 'additions': 1, 'patch_available': True}])
        if args['kind'] == 'patch':
            return page([{'path': 'a.py', 'patch': '@@ -0,0 +1 @@\n+hello\n', 'patch_complete': None}])
        return page()
    if tool == 'list-prs':
        return {'pull_requests': []}
    if tool == 'findings':
        return {'review_session': {'id': 'run', 'status': 'completed', 'commit_sha': HEAD, 'review_complete': True}, 'findings': []}
    if tool == 'read-file':
        return {'content': 'hello', 'resolved_ref': HEAD}
    raise AssertionError((group, tool, args))


class AdapterTests(unittest.TestCase):
    def test_six_provider_identities_and_url_forms(self):
        identities = [('github','github.corp','org/repo','pull/1'), ('gitlab','gitlab.corp','group/sub/repo','-/merge_requests/1'),
                      ('bitbucket','bitbucket.org','org/repo','pull-requests/1'), ('bitbucket_server','bb.corp','projects/A/repos/repo','pull-requests/1'),
                      ('azure_devops','dev.azure.com','org/project/_git/repo','pullrequest/1'), ('gerrit','review.corp','org/repo','')]
        for provider, host, repo, suffix in identities:
            url = f'https://{host}/{repo}'
            with mock.patch.object(Client, 'read', return_value={'repos': [{'full_name': repo, 'provider': provider, 'html_url': url}]}):
                self.assertEqual(Client().identity(repo, host)['provider_host'], host)
            if suffix:
                self.assertEqual(parse_ref(url+'/'+suffix), (repo, 1, host))
        self.assertEqual(parse_ref('https://review.corp/c/org/repo/+/1'), ('org/repo',1,'review.corp'))
        for provider, repo, url in [('azure_devops','org/project/repo','https://dev.azure.com/org/project/_git/repo'), ('bitbucket_server','PROJ/repo','https://bb.corp/projects/PROJ/repos/repo')]:
            parsed, _, host = parse_ref(url + ('/pullrequest/1' if provider == 'azure_devops' else '/pull-requests/1'))
            with mock.patch.object(Client,'read',return_value={'repos':[{'full_name':repo,'provider':provider,'html_url':url}]}):
                self.assertEqual(Client().identity(parsed,host)['repo'],repo)
        with mock.patch.object(Client, 'read', return_value={'repos': [], 'truncated': True}):
            with self.assertRaises(ReadError):
                Client().identity('org/repo')

    def test_cursor_is_opaque_and_unknown_is_preserved(self):
        pages = [page([{'id': 1}], next_cursor='opaque.#signed', complete=False), page([{'id': 2}], complete=None)]
        with mock.patch.object(Client, 'read', side_effect=pages) as read:
            result = Client().pages(ID, 'comments', 1, REV)
        self.assertIsNone(result['complete'])
        self.assertEqual(read.call_args.kwargs['cursor'], 'opaque.#signed')
        self.assertEqual(result['items'], [{'id':1},{'id':2}])
        self.assertEqual(result['pages'], pages)

    def test_process_permission_denial_is_not_optional_unavailable(self):
        with mock.patch('subprocess.run',side_effect=PermissionError('blocked')):
            with self.assertRaises(PermissionDenied): Client('qodo').read('codebase','search-repos')
        with mock.patch('subprocess.run',return_value=subprocess.CompletedProcess([],1,'','not_logged_in')):
            with self.assertRaises(PermissionDenied): Client('qodo').read('codebase','search-repos')

    def test_changed_revision_aborts_and_bound_retains_cursor(self):
        with mock.patch.object(Client,'read',return_value={'revision':REV,'complete':True}):
            with self.assertRaises(ReadError): Client().pages(ID,'files',1,REV)
        with mock.patch.object(Client,'read',return_value=page(revision='z'*64)):
            with self.assertRaises(ReadError): Client().pages(ID,'files',1,REV)
        with mock.patch('cockpit.adapters.managed.MAX_PAGES',1), mock.patch.object(Client,'read',return_value=page(next_cursor='next')):
            r=Client().pages(ID,'files',1,REV)
            self.assertFalse(r['complete']); self.assertEqual(r['next_cursor'],'next')

    def test_error_never_falls_back_and_permission_is_structural(self):
        for code, error in [('MT-FORBIDDEN',PermissionDenied),('MT-REPO-NOT-IN-SCOPE',PermissionDenied),('MT-UNAVAILABLE',ReadError),('not_logged_in',PermissionDenied)]:
            with mock.patch('subprocess.run',return_value=subprocess.CompletedProcess([],1,json.dumps({'error':{'code':code}}),'')) as run:
                with self.assertRaises(error): Client('qodo').read('codebase','get-change-context',repo='org/repo')
                self.assertEqual(run.call_count,1)
                self.assertEqual(run.call_args.args[0][0],'qodo')

    def test_adapter_through_approval_requires_authoritative_completion(self):
        raw = fixture('pr-review-session','findings')
        # Existing test_cockpit replaces fetch globally; explicitly use original implementation.
        real_fetch = getattr(qodo_cli,'_real_fetch',qodo_cli.fetch)
        def complete_local_patch(group, tool, **args):
            result = fixture(group, tool, **args)
            if tool == 'read-review-data' and args['kind'] == 'patch':
                for item in result['items']:
                    item['patch_complete'] = True
            return result
        # This matrix varies Qodo authority; local patch proof must independently be complete.
        with mock.patch.object(Client,'read',side_effect=complete_local_patch):
            pr=Client().change('org/repo',1)
        for mutation, allowed in [({},True),({'review_complete':False},False),({'id':None},False),({'commit_sha':'old'},False),({'status':'running'},False)]:
            response=copy.deepcopy(raw); response['review_session'].update(mutation)
            with mock.patch.object(Client,'read',return_value=response), mock.patch.object(qodo_cli,'fetch',real_fetch):
                qodo_cli.collect(pr,{})
            pr['qodo_source']='cli'
            self.assertEqual(approval({'prs':[pr]},'low')['result']=='approve',allowed)
        for bounded in ('qar_operation_result_truncated','result_is_page','truncated'):
            response={**raw,bounded:True}
            with mock.patch.object(Client,'read',return_value=response), mock.patch.object(qodo_cli,'fetch',real_fetch): qodo_cli.collect(pr,{})
            self.assertEqual(approval({'prs':[pr]},'low')['result'],'human review')
        pr['qodo_source']='comments'
        self.assertEqual(approval({'prs':[pr]},'low')['result'],'human review')
        pr['head_sha']=None
        self.assertEqual(approval({'prs':[pr]},'low')['result'],'human review')

    def test_notes_canonical_identity_paging_and_permission_stop(self):
        from cockpit import notes
        pr={'repo':'group/sub/repo','provider':'gitlab','provider_host':'gitlab.corp','number':1,'head_sha':HEAD}
        answer={'lookupStatus':'found','prContext':{'id':'note','publishedRevision':3,'digest':'hash','document':{'contentMarkdown':'intent','commitShaAtUpdate':HEAD}}}
        seen=[]
        def read(group,tool,**args):
            seen.append((tool,args))
            if tool=='resolve-repository': return {'repo_ref':'opaque'}
            text=json.dumps(answer)
            if args.get('read_cursor')=='cursor': return {'result_is_page':True,'text':text[20:],'next_read_cursor':None}
            return {'result_is_page':True,'text':text[:20],'next_read_cursor':'cursor'}
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}), mock.patch.object(Client,'read',side_effect=read):
            result=notes.for_pr(pr,{}, {})
        self.assertEqual(result['pr']['revision'],3); self.assertEqual(result['pr']['digest'],'hash')
        self.assertEqual(seen[0][1]['provider'],'gitlab'); self.assertEqual(seen[-1][1]['read_cursor'],'cursor')
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}), mock.patch.object(Client,'read',side_effect=PermissionDenied('stop')):
            with self.assertRaises(PermissionDenied): notes.collect([pr],{})

    def test_lossless_patch_chunks_and_comments_actor(self):
        def read(group,tool,**args):
            if tool=='read-review-data' and args['kind']=='patch':
                return page([{'patch':'@@ -0,0 +1 @@\n+hel'},{'patch':'lo\n'}])
            if tool=='read-review-data' and args['kind']=='comments':
                return page([{'id':'c','actor':{'login':'bot'},'body':'text'}])
            return fixture(group,tool,**args)
        with mock.patch.object(Client,'read',side_effect=read): pr=Client().change('org/repo',1)
        self.assertEqual(pr['files'][0]['hunks'][0]['lines'][0][-1],'hello')
        self.assertEqual(pr['_raw_comments'][0]['author'],'bot')


class ProductTests(unittest.TestCase):
    def test_product_server_marks_legacy_session_ui_and_empty_package_cannot_approve(self):
        from cockpit.server import Handler
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            sd=Path(tmp); (sd/'review-data.json').write_text('{"session":"old","prs":[]}')
            handler=object.__new__(Handler); handler.sdir=sd; handler.server=SimpleNamespace(product=True)
            self.assertTrue(handler._data()['product'])
            self.assertFalse(handler._data()['provider_writes'])
        self.assertEqual(approval({'product':True,'prs':[]},'low')['result'],'human review')

    def test_refresh_saved_product_restores_memory_off_without_flag(self):
        from cockpit import collect, util
        with tempfile.TemporaryDirectory() as tmp:
            sd=Path(tmp); (sd/'review-data.json').write_text(json.dumps({'product':True,'prs':[],'memory':{'enabled':'False','auto_commit':'False','amr':'memory/amr','okf':'memory/okf'}}))
            with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}), mock.patch('cockpit.managed_work.refresh',return_value={}) as refresh:
                collect.refresh(sd)
                cfg=refresh.call_args.args[2]
                self.assertFalse(util.memory_on(cfg)); self.assertFalse(cfg['memory']['auto_commit'])

    def test_write_gate_before_all_preflight_even_dry_run(self):
        from cockpit.server import Handler
        handler=object.__new__(Handler)
        with mock.patch('subprocess.run',side_effect=AssertionError('no subprocess')):
            for dry in (True,False):
                r=handler._publish({'dry_run':dry},{'product':True})
                self.assertFalse(r['ok']); self.assertFalse(r['provider_writes'])

    def test_no_gh_sentinel_across_product_collection_refresh_and_source(self):
        from cockpit import collect as c, managed_work, system
        from cockpit.util import load_config
        real_fetch=getattr(qodo_cli,'_real_fetch',qodo_cli.fetch)
        calls=[]
        def run(argv,**kw):
            self.assertNotEqual(Path(argv[0]).name,'gh')
            self.assertEqual(argv[1],'read')
            group,tool=argv[2:4];args={}
            args=json.loads(Path(argv[argv.index('--args-file')+1]).read_text())
            calls.append(tool)
            return subprocess.CompletedProcess(argv,0,json.dumps(fixture(group,tool,**args)),'')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}), mock.patch('subprocess.run',side_effect=run), mock.patch.object(qodo_cli,'fetch',real_fetch), mock.patch('cockpit.notes.collect'):
            cfg=load_config(); cfg['memory']['enabled']=False
            with mock.patch.object(c,'SESSIONS',Path(tmp)):
                _,sd=c.collect(['org/repo#1'])
                data=json.loads((sd/'review-data.json').read_text())
                (sd/'events.jsonl').write_text('{"type":"note","text":"keep"}\n')
                c.refresh(sd,cfg)
                self.assertEqual((sd/'events.jsonl').read_text(),'{"type":"note","text":"keep"}\n')
                c.live_state(data['prs'])
                managed_work.reviewers(data,cfg,4)
                system._excerpt('org/repo','a.py',HEAD,1,1,{'n':0,'until':__import__('time').monotonic()+10})
                self.assertTrue(json.loads((sd/'review-data.json').read_text())['product'])
        self.assertIn('get-change-context',calls); self.assertIn('list-prs',calls); self.assertIn('read-file',calls)

    def test_template_resources_export_and_product_notice(self):
        from cockpit import styles
        from cockpit.util import ROOT
        text=(ROOT/'app/styles/package.html').read_text().replace('{{PACKAGE_SCRIPT}}',(ROOT/'app/styles/package.js').read_text())
        # The maintained local shell baseline needs no separate Git repository or historical commit.
        shell=json.loads((Path(__file__).resolve().parent/'fixtures/local/package-shell.json').read_text())
        self.assertEqual(hashlib.sha256(text[:text.rfind('<script>')].encode()).hexdigest(),shell['prefix_sha256'])
        self.assertEqual(hashlib.sha256(text[text.rfind('</script>'):].encode()).hexdigest(),shell['suffix_sha256'])
        for name in ('package.html','package.js'): self.assertLess((ROOT/'app/styles'/name).stat().st_size,524288)

    def test_readonly_installed_resources_demo_export_and_alias(self):
        import shutil
        from cockpit.util import ROOT
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); package=root/'package'; package.mkdir(); home=root/'data'
            for name in ('cockpit','app','fixtures'):
                shutil.copytree(ROOT/name,package/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            shutil.copy2(ROOT/'config.json',package/'config.json')
            before={str(p.relative_to(package)):p.read_bytes() for p in package.rglob('*') if p.is_file()}
            try:
                for p in package.rglob('*'): p.chmod(0o555 if p.is_dir() else 0o444)
                package.chmod(0o555)
                env={**os.environ,'PR_COCKPIT_HOME':str(home),'PYTHONPATH':str(package),'PYTHONDONTWRITEBYTECODE':'1'}
                env.pop('REVIEW_COCKPIT_HOME',None)
                for args in (['review','--demo','--collect-only'],['export','--session','latest','--out',str(root/'export.html')]):
                    result=subprocess.run([__import__('sys').executable,'-B','-m','cockpit','--product',*args],cwd=root,env=env,capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                text=(root/'export.html').read_text()
                self.assertIn('Local review and export only',text)
                self.assertNotIn('{{PACKAGE_SCRIPT}}',text)
                self.assertTrue((home/'sessions/latest').is_file())
                self.assertEqual(before,{str(p.relative_to(package)):p.read_bytes() for p in package.rglob('*') if p.is_file()})
            finally:
                package.chmod(0o755)
                for p in package.rglob('*'): p.chmod(0o755 if p.is_dir() else 0o644)

    def test_fresh_defaults_keep_user_memory_configuration(self):
        from cockpit import util
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(util,'HOME',Path(tmp)), mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}):
            self.assertFalse(util.load_config()['memory']['enabled'])
            self.assertFalse(util.load_config()['memory']['auto_commit'])
            (Path(tmp)/'config.json').write_text('{"memory":{"enabled":true,"auto_commit":false}}')
            self.assertTrue(util.load_config()['memory']['enabled'])
            self.assertFalse(util.load_config()['memory']['auto_commit'])


class CheckpointFixTests(unittest.TestCase):
    def test_shared_operation_budget_bounds_complete_collect_and_secondary_reads(self):
        from cockpit import collect as c
        from cockpit import managed_work
        from cockpit.adapters.managed import ReadBudget, read_operation
        real_fetch=getattr(qodo_cli,'_real_fetch',qodo_cli.fetch)
        calls=[]
        def run(argv,**kwargs):
            self.assertEqual(Path(argv[0]).name,'qodo')
            group, tool=argv[2:4]
            params=json.loads(Path(argv[argv.index('--args-file')+1]).read_text())
            calls.append(tool)
            if tool=='resolve-repository': out={'repo_ref':'opaque'}
            elif tool=='for-pr': out={'lookupStatus':'no_pr_notes'}
            else: out=fixture(group,tool,**params)
            return subprocess.CompletedProcess(argv,0,json.dumps(out),'')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1','REVIEW_COCKPIT_QODO':'qodo'}), mock.patch.object(c,'SESSIONS',Path(tmp)), mock.patch('subprocess.run',side_effect=run), mock.patch.object(qodo_cli,'fetch',real_fetch):
            budget=ReadBudget(max_calls=18,seconds=180)
            with read_operation(budget):
                _,sd=managed_work.collect(['org/repo#1'],None,c.load_config())
            data=json.loads((sd/'review-data.json').read_text())
            self.assertLessEqual(len(calls),18)
            self.assertEqual(len(calls),budget.calls)
            self.assertIn('findings',calls); self.assertIn('for-pr',calls); self.assertIn('list-prs',calls)
            self.assertTrue(data['managed_read_budget']['exhausted'])
            self.assertEqual(data['prs'][0]['notes']['status'],'no_pr_notes')
            self.assertTrue(any('budget exhausted' in w for w in data['prs'][0]['overlap_read_warnings']))

    def test_cli_args_file_preserves_types_and_is_removed_after_process(self):
        seen=[]
        def run(argv,**kwargs):
            path=Path(argv[argv.index('--args-file')+1]); seen.append(path)
            self.assertEqual(json.loads(path.read_text()),{'pr_url':'https://example.test/repo/pull/1','extended':True,'count':3,'cursor':'opaque cursor'})
            self.assertNotIn('true',argv)
            return subprocess.CompletedProcess(argv,0,'{}','')
        with mock.patch('subprocess.run',side_effect=run):
            Client('qodo').read('pr-review-session','findings',pr_url='https://example.test/repo/pull/1',extended=True,count=3,cursor='opaque cursor',missing=None)
        self.assertFalse(seen[0].exists())

    def test_deadline_caps_each_process_and_no_process_after_exhaustion(self):
        from cockpit.adapters.managed import ReadBudget, BudgetExceeded
        clock=[0]
        def run(argv,**kwargs):
            clock[0]+=9
            return subprocess.CompletedProcess(argv,0,'{}','')
        with mock.patch('cockpit.adapters.managed.time.monotonic',side_effect=lambda:clock[0]):
            client=Client('qodo',budget=ReadBudget(max_calls=10,seconds=10))
            with mock.patch('subprocess.run',side_effect=run) as process:
                client.read('codebase','search-repos'); client.read('codebase','search-repos')
                with self.assertRaises(BudgetExceeded): client.read('codebase','search-repos')
            self.assertEqual([call.kwargs['timeout'] for call in process.call_args_list],[10,1])

    def test_patch_budget_retains_unconsumed_cursor_and_incomplete_state(self):
        from cockpit.adapters.managed import ReadBudget
        count=[0]
        def run(argv,**kwargs):
            count[0]+=1
            return subprocess.CompletedProcess(argv,0,json.dumps(page([{'patch':'text'}],next_cursor='opaque'+str(count[0]),complete=False)),'')
        with mock.patch('subprocess.run',side_effect=run):
            result=Client('qodo',budget=ReadBudget(max_calls=2)).pages(ID,'patch',1,REV,path='a.py')
        self.assertEqual(count[0],2); self.assertFalse(result['complete'])
        self.assertEqual(result['status'],'bounded'); self.assertEqual(result['next_cursor'],'opaque2')

    def test_missing_findings_url_is_explicit_and_never_dispatches(self):
        fetch=getattr(qodo_cli,'_real_fetch',qodo_cli.fetch)
        for url in (None,'','not-a-url'):
            pr={'product':True,'url':url}
            with mock.patch.object(Client,'read',side_effect=AssertionError('must not read')):
                self.assertIsNone(fetch(pr,{}))
            self.assertIn('valid PR URL',pr['qodo_read_error'])

    def test_missing_revision_is_per_pr_live_error_and_permission_stops_loop(self):
        from cockpit.managed_work import live_state
        prs=[{'key':'org/repo#'+str(n),'repo':'org/repo','number':n,'identity':ID} for n in (1,2)]
        def read(group,tool,**args):
            if tool=='get-change-context' and args['change_number']==1:return {'head_sha':HEAD}
            return fixture(group,tool,**args)
        with mock.patch.object(Client,'read',side_effect=read): result=live_state(prs)
        self.assertIn('revision',result[prs[0]['key']]['error']); self.assertNotIn('error',result[prs[1]['key']])
        with mock.patch.object(Client,'read',side_effect=PermissionDenied('stop')) as read:
            with self.assertRaises(PermissionDenied):live_state(prs)
        self.assertEqual(read.call_count,1)

    def test_standalone_preview_and_optional_notes_keep_previous_behavior(self):
        from cockpit import notes
        data={'prs':[{'key':'org/repo#1','qodo_source':'comments','findings':[]}]}
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            self.assertEqual(approval(data,'low')['result'],'approve')
            with mock.patch('subprocess.run',side_effect=PermissionError('blocked binary')):
                result,error=notes._read('qodo','for-pr',[])
                self.assertIsNone(result);self.assertIn('PermissionError',error)
            with mock.patch.object(notes,'for_pr',side_effect=PermissionError('blocked binary')):
                notes.collect(data['prs'],{})
            self.assertEqual(data['prs'][0]['notes']['status'],'unavailable')
        data['product']=True
        self.assertEqual(approval(data,'low')['result'],'human review')

    def test_source_cache_reuses_identity_and_returned_file_range_in_same_run(self):
        from cockpit.system import _excerpt
        import time
        budget={'n':0,'until':time.monotonic()+90}
        def read(group,tool,**args):
            if tool=='read-file':return {'content':'one\ntwo\nthree','resolved_ref':HEAD}
            return fixture(group,tool,**args)
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}), mock.patch.object(Client,'read',side_effect=read) as reads:
            self.assertEqual(_excerpt('org/repo','a.py',HEAD,1,3,budget)[0],'one\ntwo\nthree')
            self.assertEqual(_excerpt('org/repo','a.py',HEAD,2,3,budget)[0],'two\nthree')
            self.assertEqual(reads.call_count,2)
            _excerpt('org/repo','other.py',HEAD,1,3,budget)
            self.assertEqual(reads.call_count,3) # same repository discovery, another source read
        other_budget={'n':0,'until':time.monotonic()+90}
        with mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'1'}), mock.patch.object(Client,'read',side_effect=read) as reads:
            _excerpt('org/repo','a.py',HEAD,1,3,other_budget)
            self.assertEqual(reads.call_count,2) # a new run reobserves identity and source

    def test_browser_evidence_summarizes_raw_pages_but_keeps_provenance(self):
        from cockpit.view import _read_summary
        raw={'context':{'revision':REV},'capabilities':{'review_reads':{'comments':True}},'sections':{'comments':{'items':[{'body':'large body'}],'pages':[page([{'body':'large body'}],consistency='change_observed',observed_at='now')],'complete':True,'next_cursor':None,'status':'observed'}}}
        compact=_read_summary(raw)
        self.assertNotIn('items',compact['sections']['comments']); self.assertNotIn('pages',compact['sections']['comments'])
        self.assertEqual(compact['sections']['comments']['item_count'],1)
        self.assertEqual(compact['sections']['comments']['observations'][0]['revision'],REV)
        self.assertEqual(raw['sections']['comments']['items'][0]['body'],'large body')
