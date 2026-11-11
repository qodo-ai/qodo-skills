"""Product citation identity, imported local notes and human-review coverage controls."""
import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cockpit import collect, managed_work, system, util, view
from cockpit.adapters import qodo_cli
from cockpit.adapters.managed import Client
from cockpit.enrich import enrich
from cockpit.styles import render
from tests.test_product import fixture, page, ID, HEAD


class SourceAndReaderTests(unittest.TestCase):
    def node(self, code, payload):
        script = "const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c=x.context||{};vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));"
        result = subprocess.run(['node', '-e', script], input=json.dumps({'code':code, **payload}), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_history_reviewers_share_canonical_bot_normalization(self):
        actors = [{'login':'human','type':'User'}, {'login':'typed-service','type':'Bot'},
                  {'login':'flagged-service','is_bot':True}, {'login':'named[bot]'}]
        def read(group, tool, **args):
            if tool == 'list-prs': return {'items':[{'number':2}]}
            if tool == 'read-review-data' and args['kind'] == 'reviews':
                return page([{'actor':actor, 'reviewed_revision':HEAD, 'state':'APPROVED'} for actor in actors])
            return fixture(group, tool, **args)
        with mock.patch.object(Client, 'read', side_effect=read):
            result = managed_work.reviewers({'prs':[{'key':'org/repo#1','repo':'org/repo','identity':ID}]}, {}, 3)
        self.assertEqual([r['login'] for r in result['suggested']], ['human'])

    def test_enrich_reobserves_edited_authored_citations_in_stored_contract_refs(self):
        requests = []
        other = {**ID, 'repo':'org/other', 'repository_url':'https://github.com/org/other'}
        def read(group, tool, **args):
            if tool == 'read-file':
                requests.append(args)
                return {'content':args['path']+' new source\nsecond new line', 'resolved_ref':args['ref'], 'truncated':False}
            return fixture(group, tool, **args)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'1'}), mock.patch.object(Client,'read',side_effect=read), mock.patch.object(qodo_cli,'fetch',return_value=None):
            sd = Path(tmp)/'s'; sd.mkdir()
            pr = Client().change('org/repo',1)
            cfg = util.load_config(); cfg['memory']['enabled'] = False
            collect.build([pr, {**copy.deepcopy(pr),'repo':'org/other','key':'org/other#2','number':2,'identity':other}], cfg, demo=True, session='s', dest=sd)
            old = {'repo':'org/repo','path':'old.py','from':1,'to':1,'excerpt':'OLD AUTHOR TEXT','excerpt_cut':0,
                   'source_evidence':{'complete':True,'requested_ref':'c'*40,'identity':ID,'path':'old.py','selection_from':1,'selection_to':1}}
            for changes in ({'path':'new.py'}, {'from':2,'to':3}, {'repo':'org/other'}):
                citation = {**copy.deepcopy(old), **changes}
                payload = {'system':{'contracts':[{'id':'c','name':'Contract','kind':'type','used':[citation]}]}}
                enrich(sd,payload)
                data = json.loads((sd/'review-data.json').read_text())
                stored = data['system']['contracts'][0]['used'][0]
                self.assertNotIn('OLD AUTHOR TEXT',stored['excerpt'])
                self.assertEqual(requests[-1]['path'],citation['path'])
                self.assertEqual(requests[-1]['start_line'],citation['from'])
                self.assertEqual(requests[-1]['repo'],other['repository_url'] if changes.get('repo') else ID['repository_url'])
                self.assertTrue(stored['source_evidence']['complete'])
                self.assertEqual(stored['source_evidence']['path'],citation['path'])
                self.assertEqual(system.resolve(data)['contracts'][0]['used'][0]['excerpt'],stored['excerpt'])
            with mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'0'}):
                legacy, _ = system.normalize({'contracts':[{'id':'c','name':'Contract','used':[old]}]}, {'prs':[pr]}, fetch=False)
                self.assertEqual(legacy['contracts'][0]['used'][0]['excerpt'],'OLD AUTHOR TEXT')

    def test_system_repository_case_matching_selects_exact_gitlab_identity_and_sha(self):
        prs = [{'key':repo+'#1','repo':repo,'identity':{'repo':repo,'provider':'gitlab','provider_host':'gitlab.test','repository_url':'https://gitlab.test/'+repo}, 'base':'main','base_sha':sha*40}
               for repo,sha in [('Org/Repo','c'),('org/repo','e')]]
        reads = []
        def read(group, tool, **args):
            self.assertEqual(tool,'read-file'); reads.append(args)
            return {'resolved_ref':args['ref'],'content':'correct source','truncated':False}
        raw = {'contracts':[{'id':'c','name':'C','used':[{'repo':'org/repo','path':'source.py','from':1,'to':1}]}]}
        with mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'1'}), mock.patch.object(Client,'read',side_effect=read):
            result, _ = system.normalize(raw, {'product':True,'prs':prs})
            stored = result['contracts'][0]['used'][0]
            self.assertEqual(reads[-1]['repo'],'https://gitlab.test/org/repo')
            self.assertEqual(reads[-1]['ref'],'e'*40); self.assertTrue(stored['source_evidence']['complete'])
            self.assertEqual(stored['source_evidence']['identity']['repo'],'org/repo')
            ambiguous = [prs[1], {**prs[1],'key':'org/repo#2','identity':{**prs[1]['identity'],'provider_host':'elsewhere.test'}}]
            reads.clear(); result, _ = system.normalize(raw, {'product':True,'prs':ambiguous})
            self.assertFalse(result['contracts'][0]['used'][0]['source_evidence']['complete']); self.assertFalse(reads)
            # Explicit hosts disambiguate two repositories even at the same SHA; the range cache must follow identity.
            other = {**prs[1], 'key':'org/repo#2', 'identity':{**prs[1]['identity'], 'provider_host':'elsewhere.test', 'repository_url':'https://elsewhere.test/org/repo'}}
            raw['contracts'][0]['used'] = [{**raw['contracts'][0]['used'][0], 'provider_host':host} for host in ('gitlab.test','elsewhere.test')]
            reads.clear(); result, _ = system.normalize(raw, {'product':True,'prs':[prs[1],other]})
            self.assertEqual([r['repo'] for r in reads], ['https://gitlab.test/org/repo','https://elsewhere.test/org/repo'])

    def test_actual_contract_source_link_builder_respects_identity_and_legacy(self):
        source = (util.ROOT/'app/styles/contract-map.js').read_text()
        code = source[source.index('  function ghBlob('):source.index('  function refHtml(')]
        def link(identity, native=None, product=True, diff=False):
            ref = {'repo':identity['repo'],'path':'source.py','ref':HEAD,'from':1,'to':2,'source_evidence':{'identity':identity,'source_url':native},'diff':diff,'pr':'p'}
            return self.node("const safeUrl=u=>/^https?:\\/\\//.test(String(u||''))?u:null;"+code+';result=ghBlob('+json.dumps(ref)+');', {'context':{'C':{'product':product},'PRS':{'p':{'identity':identity,'head_sha':HEAD,'repo':identity['repo']}}}})
        self.assertEqual(link(ID),f'https://github.com/org/repo/blob/{HEAD}/source.py#L1-L2')
        ghe = {**ID,'provider_host':'github.corp','repository_url':'https://github.corp/org/repo'}
        self.assertTrue(link(ghe).startswith('https://github.corp/'))
        for provider in ('gitlab','bitbucket','gerrit'):
            identity = {**ID,'provider':provider,'provider_host':'forge.test','repository_url':'https://forge.test/org/repo'}
            self.assertIsNone(link(identity)); self.assertIsNone(link(identity,diff=True))
            self.assertEqual(link(identity,'https://forge.test/native/source'),'https://forge.test/native/source')
            self.assertTrue(link(identity,product=False).startswith('https://github.com/'))

    def test_imported_note_events_render_hydrate_edit_undo_and_do_not_collide(self):
        hydrate_code = (util.ROOT/'app/styles/product-state.js').read_text()
        def hydrate(data, stored=None, mode='snapshot'):
            return self.node(hydrate_code+';result=PRODUCT_STATE.hydrate('+json.dumps(data)+','+json.dumps(stored)+','+json.dumps(mode)+');',{})
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'1'}), mock.patch.object(Client,'read',side_effect=fixture), mock.patch.object(qodo_cli,'fetch',return_value=None):
            sd = Path(tmp)/'s'; sd.mkdir(); pr = Client().change('org/repo',1)
            pr['_raw_comments'] = [{'id':7,'author':'reader','body':'imported comment','path':'a.py','line':1}]
            cfg = util.load_config(); cfg['memory']['enabled'] = False
            events = collect.import_own_comments(pr,'reader','s')
            collect.build([pr],cfg,demo=True,session='s',dest=sd)
            events += [{'type':'note','note_id':'existing','pr':pr['key'],'text':'local comment'},
                       {**events[0],'pr':'org/other#2'}]
            (sd/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
            data = json.loads((sd/'review-data.json').read_text()); data['prs'].append({**copy.deepcopy(pr),'key':'org/other#2','repo':'org/other'})
            for mode in ('snapshot','serve'):
                html = render('package',sd,data=data,mode=mode)
                self.assertIn('imported comment',html); self.assertIn('PRODUCT_STATE',html)
                seed = view.view_data(sd,data=data)
                state = hydrate(seed,mode=mode)
                self.assertEqual(len(state['notes']),3)
                ids = [n['sent'] for n in state['notes']]; self.assertEqual(len(set(ids)),3)
                note = next(n for n in state['notes'] if n['anchor']['pr']==pr['key'] and n['text']=='imported comment')
                self.assertEqual(note['anchor']['target'],events[0]['target']); self.assertEqual(note['anchor']['line'],1)
                edited = copy.deepcopy(state); edited['notes'][0]['text']='reader edited'
                self.assertEqual(hydrate(seed,edited)['notes'][0]['text'],'reader edited')
                edited['notes']=[]; self.assertFalse(hydrate(seed,edited)['notes'])
                seed['events'].append({'type':'note','note_id':note['sent'],'pr':pr['key'],'text':'canonical edit'})
                canonical = next(n for n in hydrate(seed,mode='serve')['notes'] if n['sent']==note['sent'])
                self.assertEqual(canonical['text'],'canonical edit'); self.assertEqual(canonical['anchor']['target'],events[0]['target'])
                seed['events'].append({'type':'note','note_id':note['sent'],'pr':pr['key'],'undo':True})
                self.assertNotIn(note['sent'],[n['sent'] for n in hydrate(seed,mode='serve')['notes']])

    def test_managed_live_state_and_actual_verdict_preserve_unknown_review_coverage(self):
        source = (util.ROOT/'app/styles/package.js').read_text()
        start = 'const reviewCoverageKnown =' if 'const reviewCoverageKnown =' in source else 'const awaitingReview ='
        code = source[source.index(start):source.index('function bVerdict()')]
        known = '[p].every(reviewCoverageKnown)' if start == 'const reviewCoverageKnown =' else 'true'
        code += source[source.index('const prState ='):source.index('\n',source.index('const prState ='))]
        code += source[source.index('const vdLink ='):source.index('function vdPrs(')]
        code += source[source.index('function vdPrs('):source.index('function vdThreads(')]
        reviews = []; complete = False
        def read(group, tool, **args):
            if tool == 'read-review-data' and args['kind']=='readiness': return page([{'state':'open','draft':False}])
            if tool == 'read-review-data' and args['kind']=='reviews': return page(reviews,complete=complete)
            return fixture(group, tool, **args)
        with mock.patch.object(Client,'read',side_effect=read):
            pr = Client().change('org/repo',1)
            def draw(live, snapshot=pr):
                return self.node('const esc=String,strip=String,store={get:(k,d)=>d,set(){}};'+code+';const p='+json.dumps(snapshot)+';result={state:prState(p),awaiting:awaitingReview(p),html:vdPrs("Human review",[p].filter(awaitingReview),'+known+')};',{'context':{'C':{'product':True},'LIVE':live}})
            live = managed_work.live_state([pr]); result = draw(live)
            self.assertEqual(result['state'],'open'); self.assertIsNone(result['awaiting']); self.assertIn('not checked yet',result['html'])
            self.assertEqual(live[pr['key']]['read_evidence']['readiness']['items'][0]['state'],'open')
            self.assertIsNone(draw({})['awaiting'])
            complete=True
            for actors,expected in [([],True),([{'login':'service','type':'Bot'}],True),([{'login':'human'}],False)]:
                reviews[:] = [{'actor':a,'state':'APPROVED','reviewed_revision':HEAD,'submitted_at':'2026-11-01T00:00:00Z'} for a in actors]
                current = Client().change('org/repo',1); live = managed_work.live_state([current])
                self.assertEqual(draw(live)['awaiting'],expected)
                if not expected:
                    self.assertEqual(live[pr['key']]['approved_by'],[])
                    self.assertEqual(managed_work.live_state([pr])[pr['key']]['approved_by'],['human'])

    def test_late_refresh_denial_restores_exact_snapshot_without_losing_reader_events(self):
        from cockpit.adapters.managed import PermissionDenied, current_budget
        from cockpit.server import Handler, append_events
        class ImmediateThread:
            def __init__(self, target, **kwargs): self.target = target
            def start(self): self.target()
        denied = True
        captured = {}
        def read(group, tool, **args):
            if tool == 'read-file':
                if denied:
                    self.assertNotEqual((sd/'review-data.json').read_bytes(), snapshot)
                    append_events(sd,[{'type':'note','note_id':'during-refresh','pr':'org/repo#1','text':'concurrent reader work'}],sd.name)
                    captured['events'] = (sd/'events.jsonl').read_bytes()
                    raise PermissionDenied('token_expired source read')
                return {'content':'new source', 'resolved_ref':args['ref'], 'truncated':False}
            result = fixture(group,tool,**args)
            if tool == 'get-change-context': result['head_sha'] = 'd'*40
            return result
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'1'}), mock.patch.object(qodo_cli,'fetch',return_value=None):
            sd = Path(tmp)/'s'; sd.mkdir()
            with mock.patch.object(Client,'read',side_effect=fixture): pr=Client().change('org/repo',1)
            cfg=util.load_config(); cfg['memory']['enabled']=False; cfg['notes']['enabled']=False; cfg['overlaps']['enabled']=False
            collect.build([pr],cfg,demo=True,session='s',dest=sd)
            (sd/'events.jsonl').write_text('{"type":"note","note_id":"existing","pr":"org/repo#1","text":"keep"}\n')
            # Distinct formatting verifies byte preservation, not just JSON equality.
            data=json.loads((sd/'review-data.json').read_text()); data['demo']=False
            (sd/'review-data.json').write_text(json.dumps(data,separators=(',', ':'))+'\n')
            snapshot=(sd/'review-data.json').read_bytes()
            (sd/'enrich.json').write_text(json.dumps({'system':{'contracts':[{'id':'c','name':'C','kind':'type','used':[{'repo':'org/repo','path':'source.py','from':1,'to':1}]}]}}))
            handler=object.__new__(Handler); handler.sdir=sd; handler.cfg=cfg
            with mock.patch.object(Client,'read',side_effect=read), mock.patch('threading.Thread',ImmediateThread), mock.patch.object(Handler,'_refreshing',{}):
                handler._refresh(data)
                self.assertEqual(Handler._refreshing['s']['state'],'error')
                self.assertIn('token_expired',Handler._refreshing['s']['error'])
                self.assertEqual((sd/'review-data.json').read_bytes(),snapshot)
                self.assertEqual((sd/'events.jsonl').read_bytes(),captured['events'])
                self.assertIsNone(current_budget())
                self.assertTrue(Handler._refresh_lock.acquire(blocking=False)); Handler._refresh_lock.release()
                denied=False
                handler._refresh(data)
                self.assertEqual(Handler._refreshing['s']['state'],'done')
                saved=json.loads((sd/'review-data.json').read_text())
                self.assertEqual(saved['prs'][0]['head_sha'],'d'*40)
                self.assertEqual(saved['system']['contracts'][0]['used'][0]['excerpt'],'new source')
                self.assertEqual((sd/'events.jsonl').read_bytes(),captured['events'])
                self.assertIsNone(current_budget())
                self.assertTrue(Handler._refresh_lock.acquire(blocking=False)); Handler._refresh_lock.release()

    def test_actual_verdict_qualifies_ci_and_review_counts_without_hiding_observed_failures(self):
        source=(util.ROOT/'app/styles/package.js').read_text()
        code=source[source.index('const vdLink ='):source.index('function crumb()')]
        code=source[source.index('function productCiUnknown('):source.index('\n',source.index('function productCiUnknown('))]+code
        def draw(pr, product=True):
            context={'C':{'product':product},'LIVE':{},'RK':None,'CI_BAD':['FAILURE','ERROR'],'CI_OK':['SUCCESS','NEUTRAL','SKIPPED'],'VDICON':{'unknown':''},'KIT':{}}
            setup='const esc=String,strip=String,RW=String; KIT.openFindings=()=>[];const store={get:(k,d)=>d,set(){}},document={addEventListener(){},querySelector:()=>null,getElementById:()=>null};KIT.allFindings=()=>[]; const prs=()=>['+json.dumps(pr)+'];'
            html=self.node(setup+code+';result=bVerdict();',{'context':context})
            def row(label):
                return html.split('<span class="vd-k">'+label+'</span>',1)[1].split('</div>',1)[0]
            return row('PRs failing CI'),row('PRs awaiting human review')
        complete=False; checks=[]
        def read(group,tool,**args):
            if tool=='read-review-data':
                if args['kind']=='checks':return page(checks,complete=complete)
                if args['kind']=='reviews':return page([],complete=complete)
            return fixture(group,tool,**args)
        with mock.patch.object(Client,'read',side_effect=read):
            pr=view._pr_view(Client().change('org/repo',1))
            for row in draw(pr):
                self.assertIn('coverage unknown',row); self.assertIn('—',row); self.assertNotIn('none',row)
            checks[:]=[{'name':'observed failure','state':'failure'}]
            ci,_=draw(view._pr_view(Client().change('org/repo',1)))
            self.assertIn('>1<small',ci); self.assertNotIn('at least',ci); self.assertIn('#1',ci); self.assertIn('coverage unknown',ci)   # a count like the other cards, marked coverage unknown
            complete=True
            ci,reviews=draw(view._pr_view(Client().change('org/repo',1)))
            self.assertIn('>1<small',ci); self.assertNotIn('coverage unknown',ci); self.assertIn('>1<small',reviews)
            checks[:]=[{'name':'passing','state':'success'}]
            ci,_=draw(view._pr_view(Client().change('org/repo',1)))
            self.assertIn('>0<small',ci); self.assertIn('none',ci)
            complete=False; checks.clear()
            legacy=view._pr_view(Client().change('org/repo',1)); legacy.pop('product',None)
            ci,_=draw(legacy,False)
            self.assertIn('>0<small',ci); self.assertNotIn('coverage unknown',ci)
