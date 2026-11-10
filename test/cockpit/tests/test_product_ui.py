"""Execute the actual Work Package quality functions against observed incomplete evidence."""
import copy
import json
import subprocess
import unittest
from pathlib import Path

from cockpit.product import project_pr
from cockpit.util import ROOT


class ProductQualityTests(unittest.TestCase):
    def setUp(self):
        self.pr=json.loads((Path(__file__).resolve().parent/'fixtures/product/incomplete-source.json').read_text())
        self.source=(ROOT/'app/styles/package.js').read_text()

    def draw(self, pr, source=None):
        source=source or self.source
        start=source.index('function productEvidenceUnknown(') if 'function productEvidenceUnknown(' in source else source.index('function toolStatus(')
        end=source.index('function productToolsRow(') if 'function productToolsRow(' in source else source.index('function checksLine(')
        code=source[start:end]
        script=r'''
const vm = require('node:vm');
const x=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const ctx={prs:()=>[x.pr], isOpen:f=>!f.status||f.status==='open',srcName:f=>f.scanner?.name||f.source,
 shortPr:key=>'#'+key.split('#')[1],esc:s=>String(s??''),CI_BAD:['FAILURE','ERROR'],untestedFiles:()=>[],
 DECS:[],HEADSUP:[],flowFold:(id,title,chip,body)=>title+chip+body,testsRow:()=>'',
 KIT:{host:{styles:[]}},hasQuality:()=>false,strip:s=>s,md:s=>s};
vm.createContext(ctx); vm.runInContext(x.code+'\nresult={chip:issuesSub(),html:bIssues(),tools:toolStatus(prs())};',ctx);
process.stdout.write(JSON.stringify(ctx.result));
'''
        result=subprocess.run(['node','-e',script],input=json.dumps({'pr':pr,'code':code}),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_observed_comment_only_review_and_failed_sections_never_say_clean(self):
        pr=project_pr(self.pr)
        out=self.draw(pr)
        self.assertIn('Unknown',out['chip'])
        self.assertIn('no clean verdict',out['html'])
        self.assertIn('CI status is unknown',out['html'])
        self.assertNotIn('No CI checks ran',out['html'])
        self.assertNotIn('2 ran',out['html'])
        self.assertNotIn('>Clean<',out['html'])
        self.assertTrue(all(t['unknown'] for t in out['tools']))
        self.assertTrue(all(not t['ran'] for t in out['tools']))
        self.assertEqual(pr['scans'][0]['status'],'unknown')
        self.assertEqual(pr['scans'][0]['observed_status'],'passed')

    def test_complete_current_qodo_run_is_required_in_main_badge(self):
        pr=copy.deepcopy(self.pr); pr['scans']=[];pr['qodo_source']='cli';pr.pop('qodo_read_error',None)
        pr['qodo_review']={'status':'completed','commit':pr['head_sha'],'review_complete':True,'run_id':'run','bounded':False}
        for section in pr['read_evidence']['sections'].values():section.update(complete=True,status='observed',error=None)
        self.assertIn('Clean',self.draw(project_pr(pr))['chip'])
        for key,value in (('review_complete',False),('commit','old'),('run_id',None)):
            control=copy.deepcopy(pr);control['qodo_review'][key]=value
            self.assertIn('Unknown',self.draw(project_pr(control))['chip'])

    def test_standalone_quality_html_matches_before_product_mode(self):
        pr=copy.deepcopy(self.pr);pr.pop('product');pr.pop('read_evidence');pr.pop('qodo_read_error')
        original=json.loads((Path(__file__).resolve().parent/'fixtures/local/standalone-quality.json').read_text())
        current=self.draw(pr)
        self.assertEqual(current,original)
