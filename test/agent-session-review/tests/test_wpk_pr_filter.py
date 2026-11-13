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
        cls.code = STUBS + cut(cls.source, 'function prddPanel()', 'const prddDraw') + cut(cls.source, 'let WPKS = [], WPKT', 'function wpkDraw()')
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

    def test_the_pr_filter_flies_out_on_hover_with_no_back_row(self):
        self.assertNotIn('data-wpk-back', self.source); self.assertNotIn('WPKV', self.source)   # the menu keeps one view, the list
        self.assertNotIn('data-prpick', self.menu("S.pr=['o/b#2'];"))   # the PRs sit in the flyout, not the menu
        panel = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': self.code + 'result=prddPanel();'}), capture_output=True, text=True)
        html = json.loads(panel.stdout)
        self.assertIn('data-prpick="o/a#1"', html); self.assertIn('data-prpick="o/b#2"', html)
        self.assertNotIn('prdd-q', html); self.assertNotIn('data-prpick="all"', html)   # no search box, no Select all
        self.assertIn('class="wpk-fly"', self.source)
        self.assertIn('e.pointerType === "mouse" && e.target.closest && e.target.closest("#wpk .wpk-cur, #wpk .wpk-fly")) wpkFly(true)', self.source)   # hover opens it
        self.assertIn('e.target.closest(".wpk-m, .wpk-fly")', self.source)   # a click inside the flyout keeps the menu open
        self.assertIn('if (f && !f.hidden) { if (f.contains(document.activeElement)) $("#wpk .wpk-cur").focus(); return wpkFly(false); }', self.source)   # Escape closes a hover-opened flyout alone

    def test_picking_a_package_closes_the_menu(self):
        go = self.source[self.source.index('async function wpkGo(id)'):]
        self.assertTrue(go.split('\n')[1].lstrip().startswith('wpkClose(); try {'))
        self.assertNotIn('wpk-reopen', self.source)   # the menu no longer opens again after the reload
        self.assertIn('if (t.closest("[data-wpk-prs]")) { e.stopImmediatePropagation(); return wpkClose(); }', self.source)

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

    def test_product_verdicts_date_from_collection(self):
        live = self.source[self.source.index('fetch("/api/live")'):]
        live = live[:live.index('\n')]
        self.assertIn('C.live_at = !C.product &&', live)   # product CI and findings come from collection, so a live time would date them falsely

    def test_refresh_leads_the_header_and_more_sits_in_the_footer(self):
        head = self.source[self.source.index('function headActions()'):]
        head = head[:head.index('\n}\n')]
        self.assertTrue(head.rstrip().endswith('refreshHtml();   // Share, then Refresh, the primary action, on the far right'))
        self.assertNotIn('data-nvmore', head)
        foot = self.source[self.source.index('function freshHtml()'):self.source.index('function refreshHtml()')]
        self.assertLess(foot.index('snav-ago'), foot.index('data-nvmore')); self.assertLess(foot.index('data-nvmore'), foot.index('data-settings-open'))   # last refresh time, More, Settings
        self.assertNotIn('data-ck="refresh"', foot)
        tip = self.source[self.source.index('function freshTip()'):self.source.index('const SRV =')]
        self.assertIn('${folderBtn()}</div>', tip)   # Open in Finder beside when the data was fetched
        self.assertIn('class="hbtn hlbl hpri rf-btn ck-ricon', self.source)   # a primary button that still spins while refreshing

    def test_the_tour_points_at_refresh_and_more_stays_on_screen(self):
        welcome = (util.ROOT / 'app/styles/welcome.js').read_text()
        self.assertIn('document.querySelector(".rfw"), t: "Your data stays local"', welcome); self.assertNotIn('#snavfoot', welcome)
        more = self.source[self.source.index('function nvMore('):]
        more = more[:more.index('\n}\n')]
        self.assertIn('Math.max(8, Math.min(x, innerWidth - m.offsetWidth - 8))', more)   # both openings clamp the left edge
        self.assertIn('max-width:calc(100vw - 16px)', (util.ROOT / 'app/styles/package.html').read_text())

    def test_the_header_no_longer_holds_the_filter(self):
        html = (util.ROOT / 'app/styles/package.html').read_text()
        self.assertNotIn('id="prsel"', html)
        self.assertIn('id="wpkf" data-wpk-flt', html)
        self.assertNotIn('prddHtml', self.source)


if __name__ == '__main__':
    unittest.main()
