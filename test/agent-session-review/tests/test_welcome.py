import json
import subprocess
import unittest

from cockpit import util
from cockpit.appstate import APP_KEYS

SCRIPT = ("const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={};"
          "vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));")


class WelcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (util.ROOT / 'app/styles/welcome.js').read_text()
        cls.package = (util.ROOT / 'app/styles/package.js').read_text()

    def auto(self, saved):
        head = self.source[:self.source.index('const WCART')]
        code = ("let opened=0;const KIT={host:{session:'s1'}},C={title:'Pkg',reviewed_at:'2026-11-10T13:00:00Z'},DB={};"
                + (f"DB['cockpit:welcome']={json.dumps(saved)};" if saved is not None else "")
                + "const store={get:(k,d)=>k in DB?DB[k]:d,set:(k,v)=>{DB[k]=v;}},wcOpen=()=>{opened++;};" + head + "wcAuto();result=opened;")
        out = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': code}), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_welcome_opens_first_and_on_a_regenerated_review_unless_switched_off(self):
        self.assertEqual(self.auto(None), 1)   # the first open ever
        self.assertEqual(self.auto({'hide': True, 'last': 'old'}), 0)   # Don't show again
        self.assertEqual(self.auto({'hide': False, 'last': 's1@2026-11-10T13:00:00Z'}), 0)   # already shown for this review
        self.assertEqual(self.auto({'hide': False, 'last': 's1@2026-11-09T09:00:00Z'}), 1)   # the skill regenerated it

    def test_state_lives_in_the_app_settings_file(self):
        self.assertIn('cockpit:welcome', APP_KEYS)
        self.assertIn('cockpit:layout-dividers', APP_KEYS)

    def test_welcome_page_has_both_ways_in_and_dont_show_again_checked(self):
        for part in ('Agent Session Review', 'data-wc-tour>Start the tour', 'data-wc-hide checked', "Don't show again", 'Change it later in Settings'):
            self.assertIn(part, self.source)
        self.assertNotIn('data-wc-build', self.source); self.assertNotIn('wc-pk', self.source)   # no layout button, no feature name or package counts
        self.assertEqual(self.source.count('t: "'), 6)   # the tour: pages, the work package, where to start, Reader, the layout, the data
        self.assertIn('Qodo toolbox', self.source)
        self.assertIn('document.querySelector(".snav-wp")', self.source); self.assertIn('document.querySelector(".ptl-w")', self.source)   # the header's name when the side menu is collapsed
        self.assertIn('class="wa-diff"', self.source)   # the hero's diff turns into the dashboard
        self.assertNotIn('data-wc-back', self.package)
        self.assertIn('data-ly="tpl"><b>${LYICON.tpl}Help me build a layout</b>', self.package)   # the wizard is at the foot of the Customize nav
        self.assertIn('enter: () =>', self.source); self.assertIn('nvMore(b)', self.source)   # the layout step opens the ⋮ menu

    def test_the_wizard_moved_from_the_more_menu_to_the_welcome_page(self):
        self.assertNotIn('<span>Layout wizard</span>', self.package)
        self.assertIn('setTimeout(wcAuto, 0)', self.package)
        self.assertNotIn('WZFIRST', self.package)
        self.assertNotIn('kind: "tpl", first: true', self.source)
        self.assertIn('+ wcSetRow();', self.package)   # Settings › General has the switch
        self.assertIn('"wpk-fwd" : "wpk-back"', self.package)   # the menu's two views slide


class HeaderSwitcherTests(unittest.TestCase):
    def test_the_header_name_switches_packages_only_with_the_side_menu_collapsed(self):
        nav = (util.ROOT / 'app/styles/nav.js').read_text()
        code = ("const esc=String,HICON={chev:''},KIT={host:{session:'s1'}},document={getElementById:()=>null};let WPKS=[{id:'s1',title:'A'}];" + nav[:nav.index('function ptlClose')] + "const one=ptlWp('A');WPKS.push({id:'s2',title:'B'});result=[one,ptlWp('A')];")
        out = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': code}), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        one, two = json.loads(out.stdout)
        self.assertNotIn('data-ptlwp', one); self.assertIn('data-ptlwp', two)   # a menu only when there's another package
        self.assertNotIn('prdd', nav); self.assertIn('wpkGo(g.dataset.ptlgo, true)', nav)   # switching only, no PR filter, no reopened menu
        package = (util.ROOT / 'app/styles/package.js').read_text()
        self.assertIn('${nm ? `${ptlWp(nm)}', package)
        self.assertIn('m.className = "ptl-mm hmenu"', nav); self.assertNotIn('"nv-mm', nav)   # never reused as the ⋮ menu
        for key in ('ArrowDown', 'ArrowUp', 'Home', 'End'):
            self.assertIn(key, nav)   # a keyboard menu
        self.assertLess(nav.index('if (!m.contains(document.activeElement)) return;'), nav.index('ArrowDown:'))   # only while focus is in the menu
        self.assertIn('if (!nm) ptlClose();', package)   # a redraw without the switcher closes its menu
        check = subprocess.run(['node', '--check', str(util.ROOT / 'app/styles/nav.js')], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)   # the whole file parses, not just the slice above


if __name__ == '__main__':
    unittest.main()
