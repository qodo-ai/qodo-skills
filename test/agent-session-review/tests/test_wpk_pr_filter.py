import json
import subprocess
import unittest

from cockpit import util

SCRIPT = ("const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={};"
          "vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));")
STUBS = ("const esc=String,strip=String,GHICON='',MICON={gear:''},KIT={host:{session:'s1'}},"
         "C={title:'Pkg',prs:[{key:'o/a#1',repo:'o/a',number:1,title:'One'},{key:'o/b#2',repo:'o/b',number:2,title:'Two'}]},"
         "pl1=(n,w)=>n+' '+w+(n===1?'':'s');let S={pr:'all'},BL=['verdict'];const curBlocks=()=>BL,"
         "prs=()=>S.pr==='all'?C.prs:C.prs.filter((p)=>S.pr.includes(p.key)),prOn=(k)=>S.pr==='all'||S.pr.includes(k);")


def cut(source, start, end):
    return source[source.index(start):source.index(end)]


class WorkPackagePrFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (util.ROOT / 'app/styles/package.js').read_text()
        cls.code = STUBS + cut(cls.source, 'function prddPanel()', 'const prddDraw') + cut(cls.source, 'let WPKS = [], WPKV', 'function wpkDraw()')
        cls.code += ("WPKS=[{id:'s1',title:'Pkg',prs:['o/a#1','o/b#2'],story:true},{id:'s2',title:'Other',prs:['o/c#3'],story:true}];")

    def menu(self, setup=''):
        result = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': self.code + setup + 'result=wpkMenu();'}), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_the_current_package_has_an_arrow_to_its_pr_filter(self):
        html = self.menu()
        self.assertIn('data-wpk-prs', html)
        self.assertIn('class="wpk-fw"', html)
        self.assertIn('data-wpk-go="s2"', html)
        self.assertNotIn('class="wpk-fn"', html)   # no count while every PR shows
        self.assertIn('<span class="wpk-fn">1 of 2 PRs</span>', self.menu("S.pr=['o/a#1'];"))

    def test_the_arrow_shows_the_pr_filter_with_a_way_back(self):
        html = self.menu("WPKV='prs';S.pr=['o/b#2'];")
        self.assertIn('data-wpk-back', html)
        self.assertIn('class="hsrow wpk-bk" data-wpk-back', html); self.assertIn('<span>Back</span>', html)   # one full-width Back row
        self.assertIn('data-prpick="o/a#1"', html)
        self.assertIn('data-prpick="o/b#2"', html)
        self.assertNotIn('data-wpk-go', html)
        self.assertNotIn('prdd-q', html)   # no search box
        self.assertNotIn('data-prpick="all"', html)   # no Select all: the PRs only

    def test_your_review_page_and_single_pr_packages_have_no_filter(self):
        self.assertNotIn('data-wpk-prs', self.menu("BL=['review'];"))
        self.assertNotIn('data-wpk-prs', self.menu("C.prs.length=1;"))

    def test_a_risk_pick_the_filter_hides_is_dropped(self):
        radar = self.source[self.source.index('function riskRadar()'):self.source.index('function rApply()')]
        drop = radar.index('RSEL = new Set([...RSEL].filter((k) => ser.some((x) => x.i === k)))')
        self.assertLess(drop, radar.index('const sel = RSEL ||'))   # reconciled before the chart picks its focus

    def test_failed_live_reads_are_not_up_to_date(self):
        tip = self.source[self.source.index('function freshTip()'):self.source.index('const SRV =')]
        self.assertIn('return v && !v.error && v.head;', tip)   # only a read that found the head counts
        self.assertIn('${gap} not checked', tip)

    def test_product_verdicts_date_from_a_complete_readiness_read(self):
        live = self.source[self.source.index('fetch("/api/live")'):]
        live = live[:live.index('\n')]
        self.assertIn('C.product ? v.readiness_complete === true && v.reviews_complete === true', live)   # product reads carry no unresolved count or checks

    def test_the_header_no_longer_holds_the_filter(self):
        html = (util.ROOT / 'app/styles/package.html').read_text()
        self.assertNotIn('id="prsel"', html)
        self.assertIn('id="wpkf" data-wpk-flt', html)
        self.assertNotIn('prddHtml', self.source)


if __name__ == '__main__':
    unittest.main()
