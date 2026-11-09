"""V1 projection and snapshot-writer regressions from hosted review79170."""
import copy
import json
import os
from pathlib import Path
import subprocess
import threading
import unittest
from unittest import mock

from cockpit import enrich, impact, memory, product, reviewers, util, view
from cockpit.adapters import qodo_cli, qodo_comments, qodo_local
from cockpit.session_writer import SessionBusy
from tests import test_product_enrich_refresh as helpers
from tests import test_product_finding_scope as scope_tests
from tests.test_product import HEAD


class ProductHostedReviewTests(unittest.TestCase):
    def node(self, script):
        return subprocess.run(['node'], input=script, capture_output=True, text=True)

    def test_local_current_anchor_requires_known_side_collected_path_and_valid_line(self):
        pr=scope_tests.ProductFindingScopeTests().pr();pr['product']=True
        cases=[(None,'a.py',1,False),('LEFT','a.py',1,False),('RIGHT','a.py',1,True),
               ('RIGHT','absent.py',1,False),('RIGHT','a.py',-1,False),('RIGHT','a.py',True,False),('RIGHT',['a.py'],1,False)]
        for side,path,line,current in cases:
            with self.subTest(side=side,path=path,line=line):
                raw={'id':'f','title':'Concern','location':{'file_path':path,'start_line':line,'side':side}}
                finding=qodo_local.to_finding(pr,{'local_review_id':'r','commit':HEAD},raw,None)
                self.assertEqual(finding['current_anchor'],current)
                self.assertEqual(finding.get('path'),path if current else None)
                self.assertEqual(finding['source_location']['path'],path)
                self.assertEqual(finding['source_location']['line'],line)
                public=view._pr_view({**pr,'findings':[finding]})['findings'][0]
                self.assertEqual(public['current_anchor'],current)
        saved={'id':'saved','source':'qodo-local','path':'a.py','line':1,'title':'Legacy','severity':'medium',
               'local':{'commit':HEAD,'review_id':'old','at':'2026-01-01'}}
        before=copy.deepcopy(saved)
        projected=view._pr_view({**pr,'findings':[saved]})['findings'][0]
        self.assertFalse(projected['current_anchor']);self.assertIsNone(projected['path'])
        self.assertEqual(projected['source_location']['line'],1);self.assertEqual(saved,before)

    def test_post_merge_findings_retain_terminal_reason_without_claiming_fix(self):
        pr=scope_tests.ProductFindingScopeTests().pr();pr['product']=True
        raw={'id':'late','title':'Late concern','attribution_status':'detected_after_merge','git_sha':HEAD,
             'location':{'file_path':'a.py','start_line':1,'side':'RIGHT'}}
        managed=qodo_cli.to_finding(pr,raw)
        local=qodo_local.to_finding(pr,{'local_review_id':'r','commit':HEAD},raw,None)
        for finding in (managed,local):
            public=view._pr_view({**pr,'findings':[finding]})['findings'][0]
            self.assertEqual(public['status'],'detected_after_merge')
            self.assertEqual(public['closed_as'],'detected_after_merge')
            self.assertIn('no fix was verified',public['status_why'])
            self.assertNotIn('confirmed the fix',public['status_why'])
        older={**managed,'status':'resolved'};before=copy.deepcopy(older)
        self.assertEqual(view._pr_view({**pr,'findings':[older]})['findings'][0]['status'],'detected_after_merge')
        self.assertEqual(older,before)
        kit=(util.ROOT/'app/styles/kit.js').read_text()
        code=kit[kit.index('  const localDone ='):kit.index('  /* render code lines')]
        script='const esc=String,md=String;'+code+';console.log(localDone('+json.dumps([local])+'));'
        result=self.node(script)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('detected after merge; no fix verified',result.stdout)
        self.assertNotIn('<b>fixed</b>',result.stdout)
        app=(util.ROOT/'app/app.js').read_text()
        start=app.index('function panelFindings(');panel=app[start:app.index('\n}',start)+2]
        setup='const esc=String,verdicts=()=>({}),sortedFindings=p=>p.findings||[],collapseRule=()=>false,findingView=f=>f.status_why,S={showCollapsed:{}};'
        result=self.node(setup+panel+';console.log(panelFindings('+json.dumps({'key':pr['key'],'findings':[],'outdated':[local]})+'))');
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('post-merge detections with no fix verified',result.stdout)
        self.assertNotIn('No findings from Qodo',result.stdout)

    def test_reviewers_command_cannot_overwrite_a_concurrent_enrichment(self):
        helper=helpers.ProductEnrichRefreshTests();entered=threading.Event();release=threading.Event();errors=[]
        with helper.session() as (root,sd,cfg,read):
            before=(sd/'review-data.json').read_bytes()
            def suggest(*args):
                entered.set()
                if not release.wait(4):raise RuntimeError('fixture lookup timeout')
                return {'suggested':[],'calls':0,'excluded':[]}
            def run():
                try:helper.run_cli(['reviewers','--session','s','--json'])
                except BaseException as error:errors.append(error)
            with mock.patch.object(reviewers,'suggest',side_effect=suggest):
                worker=threading.Thread(target=run);worker.start()
                try:
                    self.assertTrue(entered.wait(3))
                    with self.assertRaises(SessionBusy):enrich.enrich(sd,helper.authored())
                    self.assertEqual((sd/'review-data.json').read_bytes(),before)
                finally:release.set();worker.join(timeout=5)
            self.assertFalse(worker.is_alive());self.assertFalse(errors,errors)
            self.assertEqual(json.loads((sd/'review-data.json').read_text())['reviewers']['suggested'],[])
            def noncooperating(*args):
                data=json.loads((sd/'review-data.json').read_text());data['external_legacy_update']='retained'
                util.write_json(sd/'review-data.json',data)
                return {'suggested':[],'calls':0,'excluded':[],'basis':reviewers.basis(args[0])}
            with mock.patch.object(reviewers,'suggest',side_effect=noncooperating):
                helper.run_cli(['reviewers','--session','s','--json'])
            self.assertEqual(json.loads((sd/'review-data.json').read_text())['external_legacy_update'],'retained')
            self.assertTrue(json.loads((sd/'review-data.json').read_text())['reviewers']['stale'])

    def test_idless_bucket_objects_use_same_display_identity_as_their_details(self):
        pr=scope_tests.ProductFindingScopeTests().pr();pr['product']=True
        finding={'title':'No UUID','description':'Preserve these details','file_path':'a.py','start_line':1}
        for bucket,expected in [('resolved','resolved'),('dismissed','dismissed'),('still_open',None)]:
            rec={'local_review_id':'r','commit':HEAD,'result':{'findings':[finding],
                  'finding_state':{bucket:[finding]}}}
            with self.subTest(bucket=bucket),mock.patch.object(qodo_local,'fetch',return_value=[rec]):
                output=qodo_local.collect(pr,{})
                self.assertEqual(len(output),1)
                self.assertEqual(output[0].get('status'),expected)
                self.assertEqual(output[0]['body'],'Preserve these details')

    def test_duplicate_knowledge_titles_in_one_enrichment_make_one_draft_candidate(self):
        helper=helpers.ProductEnrichRefreshTests()
        with helper.session() as (root,sd,cfg,read):
            cfg['memory']={'enabled':True,'auto_commit':False,'amr':str(root/'amr'),'okf':str(root/'okf')}
            payload={'knowledge':[{'title':'Decision','body':'First intent','paths':['a.py']},
                                  {'title':' decision ','body':'Second copy','paths':['a.py']}]}
            with mock.patch.object(enrich,'session_config',return_value=cfg):
                enrich.enrich(sd,payload)
                data=json.loads((sd/'review-data.json').read_text())
                self.assertEqual(len(data['okf']['candidates']),1)
                self.assertEqual(len(memory.OKF(root/'okf').concepts()),1)
                enrich.enrich(sd,payload)
                self.assertEqual(len(json.loads((sd/'review-data.json').read_text())['okf']['candidates']),1)
                data=json.loads((sd/'review-data.json').read_text());data['okf']['candidates']=[]
                second=copy.deepcopy(data['prs'][0]);second.update(key='org/repo#2',number=2);data['prs'].append(second)
                (sd/'review-data.json').write_text(json.dumps(data))
                multi={'knowledge':[{'title':'Decision','pr':'org/repo#1'},
                                    {'title':'Decision','pr':'org/repo#2'},
                                    {'title':' decision ','pr':'org/repo#2'}]}
                enrich.enrich(sd,multi);enrich.enrich(sd,multi)
                candidates=json.loads((sd/'review-data.json').read_text())['okf']['candidates']
                self.assertEqual(len(candidates),2)
                self.assertEqual({c['pr'] for c in candidates},{'org/repo#1','org/repo#2'})
                self.assertEqual(len({c['path'] for c in candidates}),1)
                concept_path=candidates[0]['path']
                memory.OKF(root/'okf').confirm(concept_path,'fixture reviewer')
                saved=json.loads((sd/'review-data.json').read_text())
                self.assertTrue(all(concept_path in pr.get('concepts',[]) for pr in saved['prs']))
                concepts=[c.as_dict() for c in memory.OKF(root/'okf').concepts()]
                source=(util.ROOT/'app/app.js').read_text()
                def function(name):
                    start=source.index('function '+name+'(')
                    return source[start:source.index('\n}',start)+2]
                setup='const S='+json.dumps({'data':saved,'mem':{'enabled':True,'concepts':concepts}})+';'
                setup+='const esc=String,conceptByPath=p=>S.mem.concepts.find(c=>c.path===p),conceptView=c=>"<article>"+c.title+"</article>";'
                script=setup+function('knownFor')+function('draftsFor')+function('panelKnowledge')
                script+=';console.log(JSON.stringify(S.data.prs.map(p=>({html:panelKnowledge(p),drafts:draftsFor(p).length}))));'
                result=self.node(script)
                self.assertEqual(result.returncode,0,result.stderr)
                for rendered in json.loads(result.stdout):
                    self.assertIn('<article>Decision</article>',rendered['html'])
                    self.assertEqual(rendered['drafts'],0)
                memory.OKF(root/'okf').reject(concept_path,'fixture reviewer')
                concepts=[c.as_dict() for c in memory.OKF(root/'okf').concepts()]
                setup='const S='+json.dumps({'data':saved,'mem':{'enabled':True,'concepts':concepts}})+';'
                setup+='const esc=String,conceptByPath=p=>S.mem.concepts.find(c=>c.path===p),conceptView=c=>"<article>"+c.title+"</article>";'
                script=setup+function('knownFor')+function('draftsFor')+function('panelKnowledge')+';console.log(panelKnowledge(S.data.prs[0]));'
                result=self.node(script)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertNotIn('<article>Decision</article>',result.stdout)
                enrich.enrich(sd,{'knowledge':[{'title':'Decision','pr':'org/repo#2','body':'New proposal'}]})
                concepts=memory.OKF(root/'okf').concepts()
                self.assertEqual(sum(c.meta.get('status')=='deprecated' for c in concepts),1)
                self.assertEqual(sum(c.meta.get('status')=='draft' for c in concepts),1)
                saved=json.loads((sd/'review-data.json').read_text());saved['overlaps']={'files':[]}
                def render_stats(live):
                    setup='const S='+json.dumps({'data':saved,'mem':{'concepts':live},'panel':{}})+';'
                    setup+='const esc=String,conceptByPath=p=>S.mem.concepts.find(c=>c.path===p),checksSummary=()=>"",markbar=()=>"",liveNotes=()=>"",sessionBudget=()=>"",sessionStory=()=>"",contextBox=()=>"",renderPrefsBox=()=>"",panelOrder=()=>[["knowledge","Knowledge"]],renderPanel=()=>"";'
                    code=setup+function('knownFor')+function('draftsFor')+function('renderOverview')+function('crossMap')+function('renderPR')
                    code+=';console.log(JSON.stringify({overview:renderOverview(),pr:renderPR(S.data.prs[0]),map:crossMap()}));'
                    result=self.node(code);self.assertEqual(result.returncode,0,result.stderr)
                    return json.loads(result.stdout)
                retired=[c.as_dict() for c in memory.OKF(root/'okf').concepts() if c.meta.get('status')=='deprecated']
                stats=render_stats(retired)
                self.assertNotIn('1 known facts</span>',stats['overview'])
                self.assertNotIn('class="count"',stats['pr'])
                self.assertNotIn('data-node="c:',stats['map'])
                stable=[{**retired[0],'status':'stable'}]
                stats=render_stats(stable)
                self.assertIn('1 known facts</span>',stats['overview'])
                self.assertIn('data-node="c:',stats['map'])

    def test_closed_comment_severity_is_explicit_or_unknown_and_inline_restores_it(self):
        summary='Code Review by Qodo\n<h3>Resolved findings</h3>\n<details><summary>1. <s>Concern</s> <code>Resolved</code></summary></details>'
        rows,_,_=qodo_comments.parse_review(summary)
        self.assertEqual(rows[0]['severity'],'unknown')
        explicit=summary.replace('<code>Resolved</code>','<code>High</code> <code>Resolved</code>')
        self.assertEqual(qodo_comments.parse_review(explicit)[0][0]['severity'],'high')
        for label in ('🔴 High','⭐ Required'):
            decorated=summary.replace('<code>Resolved</code>','<code>'+label+'</code> <code>Resolved</code>')
            self.assertEqual(qodo_comments.parse_review(decorated)[0][0]['severity'],'high')
        pr={'key':'o/r#1','repo':'o/r','number':1,'_raw_comments':[
            {'id':'summary','author':'qodo-code-review[bot]','body':summary},
            {'id':'inline','author':'qodo-code-review[bot]','path':'a.py','line':1,
             'body':'1. Concern\n<img src="https://img.shields.io/badge/High-ff0000">\nDetails'}]}
        findings=qodo_comments.collect(pr,{})
        self.assertEqual(len(findings),1)
        self.assertEqual(findings[0]['status'],'resolved')
        self.assertEqual(findings[0]['severity'],'high')
        link='[View finding](https://portal.test/findings/finding-one)'
        for linked_summary in (False,True):
            pr['_raw_comments'][0]['body']=summary+(link if linked_summary else '')
            for badge,expected in ((None,'unknown'),('UnknownLabel','unknown'),('Required','high')):
                pr['_raw_comments'][1]['body']='1. Concern\n'+link+('\n<img src="https://img.shields.io/badge/'+badge+'-ff0000">' if badge else '')
                findings=qodo_comments.collect(pr,{})
                self.assertEqual(len(findings),1)
                self.assertEqual(findings[0]['severity'],expected,(linked_summary,badge))

    def test_unassessed_impact_stays_unknown_through_enrichment_and_public_view(self):
        helper=helpers.ProductEnrichRefreshTests()
        with helper.session() as (root,sd,cfg,read):
            for value in (None,'severe'):
                result=enrich.enrich(sd,{'impact':[{'component':'Service','change':'Behavior','risk':value,
                           'affects':['caller'],'gaps':['Risk not assessed'],'prs':['org/repo#1']}]})
                self.assertTrue(any('risk must be' in w for w in result['warnings']))
                public=view.view_data(sd)
                self.assertEqual(public['impact'][0]['risk'],'unknown')
                self.assertEqual(public['risk']['level'],'unknown')
                for relative in ('app/styles/package.js','app/styles/focus.html'):
                    source=(util.ROOT/relative).read_text()
                    def function(name):
                        start=source.index('function '+name+'(')
                        return source[start:source.index('\n}',start)+2]
                    constants='\n'.join(line for line in source.splitlines() if line.startswith(('const RISKS_ORDER =','const IMPACT =')))
                    row=source[source.index('const impactRow ='):source.index('function impactBody(')]
                    note_start=source.index('const impactNote =');note_end=min(i for token in ('\nconst ','\nfunction ','\nlet ') for i in [source.find(token,note_start+1)] if i>=0)
                    note=source[note_start:note_end]
                    render_data=copy.deepcopy(public);render_data['impact'][0]['gaps']=[];render_data['impact'][0]['evidence']=['Observed'];render_data['impact'][0]['workflows']=['flow']
                    setup='const C='+json.dumps(render_data)+';const S={bpin:null,open:{imp:true},iview:"parts"},EXPAND=false;const esc=String,md=String,silent=()=>false;'
                    setup+='const DEPLOY=[],setDoor=()=>({verdict:"two-way"}),doorChip=()=>"",checksLine=()=>"",toolsRow=()=>"",approvalLine=()=>"",contractsLine=()=>"",decisionsLine=()=>"";'
                    code=setup+constants+note+row+function('impactBody')+function('planBlast')+function('blastDetail')+function('bImpact')
                    code+=';const indicators=["unknown","high","medium","low"].map(risk=>{IMPACT[0].risk=risk;return {risk,html:bImpact()}});IMPACT[0].risk="unknown";const unknown=JSON.parse(JSON.stringify(IMPACT[0]));IMPACT.push({...unknown,risk:"medium"});const mixed=bImpact();IMPACT.pop();IMPACT[0].gaps=["Missing proof"];const gap=bImpact();console.log(JSON.stringify({parts:impactBody("parts"),workflows:impactBody("workflows"),blast:planBlast(false),indicators,mixed,gap}));'
                    result=self.node(code)
                    self.assertEqual(result.returncode,0,result.stderr)
                    rendered=json.loads(result.stdout);self.assertIn('Unknown',rendered['parts'])
                    self.assertNotIn('undefined',rendered['blast'])
                    import re
                    for item in rendered['indicators']:
                        button=re.search(r'<button[^>]+data-iview="blast"[^>]*>(.*?)</button>',item['html'],re.S).group(1)
                        expected={'unknown':'unknown','high':'bad','medium':'warn','low':'ok'}[item['risk']]
                        self.assertIn('vdot '+expected,button)
                        if item['risk']=='unknown':
                            self.assertNotIn('low risk only',item['html'])
                            self.assertIn('risk unassessed',item['html'])

                    for name in ('blast','workflows'):
                        button=re.search(r'<button[^>]+data-iview="'+name+r'"[^>]*>(.*?)</button>',rendered['mixed'],re.S).group(1)
                        self.assertIn('vdot warn',button,(relative,name))
                    button=re.search(r'<button[^>]+data-iview="parts"[^>]*>(.*?)</button>',rendered['gap'],re.S).group(1)
                    self.assertIn('vdot warn',button)
                    self.assertIn('1 gap; risk unassessed',button)


    def test_invalid_authored_coordinates_fail_before_snapshot_or_memory_changes(self):
        helper=helpers.ProductEnrichRefreshTests()
        with helper.session() as (root,sd,cfg,read):
            enrich.enrich(sd, {'prs':{'org/repo#1':{'summary':'Prior'}}})
            before={p.name:p.read_bytes() for p in (sd/'review-data.json',sd/'enrich.json')}
            invalid=[{'line':x,'path':'a.py'} for x in ('3',True,-1,0,{},[])]
            invalid += [{'line':1,'path':x} for x in ([],{},'',False)]
            for finding in invalid:
                payload={'prs':{'org/repo#1':{'findings':[dict(finding,title='Concern',severity='high')]}},
                         'knowledge':[{'title':'Never written','type':'Invariant','body':'No side effect'}]}
                with self.subTest(finding=finding), self.assertRaisesRegex(ValueError,'Agent finding'):
                    enrich.enrich(sd,payload)
                self.assertEqual({p.name:p.read_bytes() for p in (sd/'review-data.json',sd/'enrich.json')},before)
            enrich.enrich(sd,{'prs':{'org/repo#1':{'findings':[{'line':1,'path':'a.py','title':'Valid','severity':'high'}]}}})
            self.assertEqual(json.loads((sd/'review-data.json').read_text())['prs'][0]['findings'][-1]['line'],1)

    def test_interrupted_memory_file_replacements_preserve_prior_bytes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);okf=memory.OKF(root/'okf');okf.ensure()
            c=okf.propose(type_='Invariant',title='Atomic fact',body='Original',paths=['a.py'],by='test',sources=[])
            original=copy.deepcopy(c);c.body='Replacement'
            operations=[(okf.root/c.path,lambda:okf.write(c)),
                        (okf.root/'log.md',lambda:okf.log('Update',c.path,c.meta['title'],'new evidence')),
                        (okf.root/'index.md',okf.write_index)]
            amr=memory.AMR(root/'amr');amr.ensure('fixture')
            pref=amr.root/'preferences/general.md'
            operations.append((pref,lambda:amr.upsert(memory.Bullet('New preference',file='preferences/general.md'))))
            for target,write in operations:
                before=target.read_bytes()
                with self.subTest(target=target.name),mock.patch('os.replace',side_effect=OSError('interrupted')):
                    with self.assertRaisesRegex(OSError,'interrupted'):write()
                self.assertEqual(target.read_bytes(),before)
                self.assertEqual(list(target.parent.glob('.'+target.name+'.*.tmp')),[])
            self.assertEqual(okf.get(c.path).body.strip(),original.body)
            okf.write(c);self.assertEqual(okf.get(c.path).body.strip(),'Replacement')

            # Atomic replacement must retain existing file-symlink semantics.
            shared=root/'shared.md';shared.write_bytes(pref.read_bytes());pref.unlink();pref.symlink_to(shared)
            amr.upsert(memory.Bullet('Shared preference',file='preferences/general.md'))
            self.assertTrue(pref.is_symlink());self.assertIn('Shared preference',shared.read_text())
            # Direct callers keep their existing locale; the supported launcher enables UTF-8.
            original=os.fdopen
            def legacy_default(fd,mode,**kwargs):
                self.assertIsNone(kwargs.get('encoding'))
                return original(fd,mode,encoding='cp1252')
            locale_file=root/'locale.json'
            with mock.patch('os.fdopen',side_effect=legacy_default):
                util.write_json(locale_file,{'text':'café €'})
            self.assertEqual(json.loads(locale_file.read_bytes().decode('cp1252')),{'text':'café €'})

            import stat
            if os.name != 'nt':
                shared.chmod(0o640)
            before_mode=stat.S_IMODE(shared.stat().st_mode)
            amr.upsert(memory.Bullet('Another preference',file='preferences/general.md'))
            self.assertEqual(stat.S_IMODE(shared.stat().st_mode),before_mode)
            control=root/'normal.txt';control.write_text('ordinary creation')
            new=root/'memory-new.txt';memory.write_text(new,'atomic creation')
            self.assertEqual(stat.S_IMODE(new.stat().st_mode),stat.S_IMODE(control.stat().st_mode))

            if os.name != 'nt':
                private=root/'private.txt';private.write_text('prior');private.chmod(0o600)
                def private_temp(fd,mode,**kwargs):
                    self.assertEqual(stat.S_IMODE(os.fstat(fd).st_mode),0o600)
                    return original(fd,mode,**kwargs)
                with mock.patch('os.fdopen',side_effect=private_temp):
                    memory.write_text(private,'replacement')


    def test_deleted_file_full_patch_retains_old_lines_in_public_reading_plan(self):
        from cockpit import collect
        from cockpit.adapters.managed import Client
        from tests.test_product import fixture, page
        helper=helpers.ProductEnrichRefreshTests()
        hunk='@@ -1,2 +0,0 @@\n-def old():\n-    return 1\n'
        full='diff --git a/obsolete.py b/obsolete.py\n--- a/obsolete.py\n+++ /dev/null\n'+hunk
        for text in (hunk,full,'--- a/obsolete.py\n+++ /dev/null\n'+hunk):
            with self.subTest(full_header=text!=hunk),helper.session() as (root,sd,cfg,read):
                def deleted(group,tool,**args):
                    if tool=='read-review-data' and args['kind']=='files':
                        return page([{'filename':'obsolete.py','status':'removed','additions':0,'deletions':2,'patch_available':True}])
                    if tool=='read-review-data' and args['kind']=='patch':
                        self.assertEqual(args['path'],'obsolete.py')
                        return page([{'path':'obsolete.py','patch':text,'patch_complete':True}])
                    return fixture(group,tool,**args)
                with mock.patch.object(Client,'read',side_effect=deleted):
                    pr=Client().change('org/repo',1)
                self.assertEqual([line[:3] for line in pr['files'][0]['hunks'][0]['lines']],[['-',1,None],['-',2,None]])
                collect.build([pr],cfg,demo=True,session='s',dest=sd)
                public=view.view_data(sd)['prs'][0]
                self.assertTrue(public['product_evidence']['patches_complete'])
                ranges=[x for x in public['attention']['blocks'] if x['path']=='obsolete.py' and x['side']=='old']
                self.assertEqual(sum(x['lines'] for x in ranges),2,repr(public['attention']))
                self.assertTrue(all(x['tier']!='skip' for x in ranges))
        self.assertIn('(deleted)',collect.parse_diff(full))  # preserve the raw legacy parser default

    def test_contract_map_requests_are_local_in_product_copy_and_saved_events(self):
        source=(util.ROOT/'app/styles/contract-map.js').read_text()
        def function(name):
            start=source.index('  function '+name+'(')
            return source[start:source.index('\n  }',start)+4]
        code="""
const C={product:true},CON={c:{id:"c",name:"Contract",prs:["p"],touched_by:[]}};
const st={compose:"request",anchor:{pr:"p",path:"a.py",line:1},sel:{id:"c"}},S={notes:[]};
let sent=[],toasts=[];const KIT={served:true,host:{style:"package"},send:async e=>{sent.push(...e);return true}};
const esc=String,plain=String,short=String,anchorFor=()=>({path:"a.py",line:1}),agentPrompt=()=>"manual prompt",save=()=>{},renderAll=()=>{},toast=x=>toasts.push(x);
const $=selector=>({value:selector==="#cm-text"?"Fix the contract":"Expected result"}),$$=()=>[{dataset:{cmto:"p"},checked:true}];
"""
        code+=''.join(function(name) for name in ('composeHtml','draft','events','saveNote'))
        code+=''';(async()=>{const result=[];for(const product of [true,false]){C.product=product;st.compose="request";st.anchor={pr:"p",path:"a.py",line:1};sent=[];toasts=[];S.notes=[];const html=composeHtml(CON.c);saveNote();await Promise.resolve();result.push({product,html,sent,toasts})}console.log(JSON.stringify(result))})()'''
        result=self.node(code);self.assertEqual(result.returncode,0,result.stderr)
        local,legacy=json.loads(result.stdout)
        self.assertIn('Save change request',local['html']);self.assertIn('saved only in Cockpit',local['html'])
        self.assertNotIn('GitHub',local['html']);self.assertNotIn('Send back',local['html']);self.assertNotIn('Posts on',local['html'])
        self.assertEqual(local['toasts'],['Saved locally in Cockpit'])
        self.assertEqual(len(local['sent']),1);self.assertFalse(local['sent'][0]['post'])
        self.assertEqual(local['sent'][0]['pr'],'p');self.assertIn('Fix the contract',local['sent'][0]['text'])
        self.assertIn('queued for the GitHub review',legacy['html']);self.assertIn('Send back',legacy['html'])
        self.assertTrue(legacy['sent'][0]['post']);self.assertIn('queued for the GitHub review',legacy['toasts'][0])
