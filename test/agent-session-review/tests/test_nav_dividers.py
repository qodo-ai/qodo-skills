import json
import subprocess
import unittest

from cockpit import util

SCRIPT = ("const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={};"
          "vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));")
STUBS = ("const esc=(s)=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;'),sico=()=>'',NVICON={},GRIP='',LYICON={page:'',bin:'',pen:'',div:''},"
         "S={tab:'a'},SECS=false,SUBON=false,NVOPEN=false,MINI=false,BEH6=[],RISK5=[],BRIEF3=['brief'],"
         "WIDGETS={w:1,brief:1,decisions:1},PICONS=['ovw','brief'],SICON={w:'',brief:''},rslug=(s)=>String(s).toLowerCase().replace(/[^a-z0-9]+/g,'-');")


def cut(source, start, end):
    return source[source.index(start):source.index(end)]


class NavDividerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (util.ROOT / 'app/styles/package.js').read_text()

    def run_js(self, code):
        result = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': STUBS + code}), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def nav(self, edit, layout):
        tabs = [[p['id'], p['label'], [], 'ovw', [d['label'] for d in layout['dividers'] if d['at'] == p['id']]] for p in layout['pages']]
        code = f'let EDIT={json.dumps(edit)},LAYOUT={json.dumps(layout)},TABS={json.dumps(tabs)},RECIPE={{id:"package-layout"}};'
        code += cut(self.source, 'const navItems = ', 'let LAYOUT = cleanLayout') + cut(self.source, 'const navPage = ', 'const LYICON')
        return self.run_js(code + 'result=navHtml({},[]);')

    LAYOUT = {'pages': [{'id': 'a', 'label': 'Overview', 'widgets': ['w']}, {'id': 'b', 'label': 'Requirements', 'widgets': ['w']},
                        {'id': 'c', 'label': 'Risk', 'widgets': ['w']}],
              'dividers': [{'id': 'd-intent', 'label': 'Intent', 'at': 'b'}, {'id': 'd-end', 'label': 'Later', 'at': None}]}

    def test_reading_the_nav_shows_each_divider_above_its_page(self):
        html = self.nav(False, self.LAYOUT)
        self.assertLess(html.index('>Overview<'), html.index('>Intent</p>'))
        self.assertLess(html.index('>Intent</p>'), html.index('>Requirements<'))
        self.assertGreater(html.index('>Later</p>'), html.index('>Requirements<'))   # a divider below the last page still shows, at the bottom
        self.assertNotIn('Add divider', html)

    def test_customize_lists_dividers_with_pages_to_drag_rename_and_delete(self):
        html = self.nav(True, self.LAYOUT)
        self.assertIn('data-grip="p:1" aria-label="Drag the Intent divider', html)   # one list: the divider is row 1, its page row 2
        self.assertIn('data-grip="p:2" aria-label="Drag the Requirements page', html)
        self.assertIn('data-grip="p:4" aria-label="Drag the Later divider', html)
        self.assertIn('data-ly="div-edit" data-lyv="d-intent"', html)
        self.assertIn('data-ly="div-rm" data-lyv="d-intent"', html)
        self.assertIn('data-ly="div-new"', html)

    def test_reordering_the_nav_moves_dividers_with_their_new_neighbours(self):
        code = f'let LAYOUT={json.dumps(self.LAYOUT)};' + cut(self.source, 'const navItems = ', 'let LAYOUT = cleanLayout')
        out = self.run_js(code + 'const xs=navItems();xs.splice(2,0,xs.splice(1,1)[0]);navSet(xs);result=LAYOUT;')   # Intent dragged below Requirements
        self.assertEqual([p['id'] for p in out['pages']], ['a', 'b', 'c'])
        self.assertEqual({d['id']: d['at'] for d in out['dividers']}, {'d-intent': 'c', 'd-end': None})

    def test_stored_dividers_are_cleaned(self):
        layout = {'pages': [{'id': 'a', 'label': 'A', 'widgets': ['w']}],
                  'dividers': [{'id': 'd-x', 'label': '  Intent  ', 'at': 'a'}, {'id': 'd-x', 'label': 'x' * 40, 'at': 'gone'}, {'label': '  ', 'at': 'a'}]}
        out = self.run_js(cut(self.source, 'function cleanLayout(', 'const RTXT') + f'result=cleanLayout({json.dumps(layout)});')
        self.assertEqual(out['dividers'][0], {'id': 'd-x', 'label': 'Intent', 'at': 'a'})
        self.assertEqual((out['dividers'][1]['id'], len(out['dividers'][1]['label']), out['dividers'][1]['at']), ('d-x-2', 24, None))
        self.assertEqual(len(out['dividers']), 2)   # an empty name is dropped

    def test_pages_without_an_icon_take_their_first_widgets(self):
        layout = {'pages': [{'id': 'o', 'label': 'Overview', 'icon': 'ovw', 'widgets': ['w']}, {'id': 's', 'label': 'System', 'icon': 'ovw', 'widgets': ['w']},
                            {'id': 'c', 'label': 'Complexity', 'widgets': ['w']}, {'id': 'b', 'label': 'Mine', 'icon': 'brief', 'widgets': ['w']}, {'id': 'd', 'label': 'Plain', 'widgets': ['decisions']}]}
        out = self.run_js(cut(self.source, 'function cleanLayout(', 'const RTXT') + f'result=cleanLayout({json.dumps(layout)}).pages.map((p)=>p.icon);')
        self.assertEqual(out, ['ovw', 'ovw', 'w', 'brief', 'ovw'])   # a chosen icon stays, Overview's included; a missing one takes the first widget's
        store = ("const DB={'L':{pages:[{id:'o',label:'Overview',icon:'ovw',widgets:['w']},{id:'s',label:'System',icon:'ovw',widgets:['w']}]}},"
                 "LKEY='L',store={get:(k,d)=>k in DB?DB[k]:d,set:(k,v)=>{DB[k]=v;}};")
        mig = self.run_js(store + cut(self.source, 'const PGICONS = ', 'const navItems = ') + "result=[DB.L.pages.map((p)=>p.icon),DB['cockpit:layout-icons']];")
        self.assertEqual(mig, [['ovw', 'w'], True])   # the old shared default, once, on stored layouts

    def test_risk_summary_text_moves_into_risk_assessment(self):
        out = self.run_js(cut(self.source, 'const LDEF = ', 'const VIEWDEF') + 'result=LDEF().pages.flatMap((p)=>p.widgets);')
        self.assertNotIn('rtext', out); self.assertIn('rsum', out)   # the default shows the summary inside Risk assessment
        store = ("const DB={'L':{pages:[{id:'r',label:'Risk',widgets:['rtext','rsum','rblast']},{id:'t',label:'Text',widgets:['rtext']}]}},"
                 "LKEY='L',store={get:(k,d)=>k in DB?DB[k]:d,set:(k,v)=>{DB[k]=v;}};")
        mig = self.run_js(store + cut(self.source, 'const RTXTIN = ', 'const PGICONS = ') + "result=DB.L.pages.map((p)=>p.widgets);")
        self.assertEqual(mig, [['rsum', 'rblast'], ['rtext']])   # dropped beside Risk assessment, kept where it stands alone
        body = self.source[self.source.index('function bRiskSum()'):self.source.index('const bRiskText')]
        self.assertLess(body.index('class="rtop"'), body.index('riskRadar()'))   # the text across the top, then the chart

    def test_default_layout_is_adams_2026_11_12_layout(self):
        out = self.run_js(cut(self.source, 'const LDEF = ', 'const VIEWDEF') + 'result=LDEF();')
        self.assertEqual([(d['label'], d['at']) for d in out['dividers']], [('Session review', 'brief'), ('Code review', 'triage')])
        self.assertEqual([p['id'] for p in out['pages']], ['prs', 'brief', 'coding-agent-decisions', 'system', 'triage', 'plan', 'review-walkthrough', 'builder', 'contract-changes', 'code-changes'])
        self.assertEqual(out['pages'][0]['widgets'], ['summary', 'verdict', 'prstable', 'rsum']); self.assertEqual(out['home'], 'prs')
        views = self.run_js(cut(self.source, 'const VIEWDEF = ', '// more page icons') + 'result=VIEWDEF;')
        self.assertEqual(set(views), {p['id'] for p in out['pages']})   # a Page view for every default page, none for pages it no longer has
        self.assertFalse(any('group' in p for p in out['pages']))

    def test_a_stored_layout_without_dividers_gets_the_defaults_once(self):
        store = ("const DB={'cockpit:package-layout:4':{pages:[{id:'brief',label:'Mine',group:'Old',widgets:['w']},{id:'own',label:'Own',widgets:['w']}]}},"
                 "LKEY='cockpit:package-layout:4',store={get:(k,d)=>k in DB?DB[k]:d,set:(k,v)=>{DB[k]=v;}};")
        code = store + cut(self.source, 'const LDEF = ', 'const VIEWDEF') + cut(self.source, 'const DIVS', 'const navItems')
        out = self.run_js(code + 'result=DB;')
        layout = out['cockpit:package-layout:4']
        self.assertEqual(layout['dividers'], [{'id': 'd-review', 'label': 'Session review', 'at': 'brief'}])   # only above pages it still has
        self.assertNotIn('group', layout['pages'][0])
        self.assertTrue(out['cockpit:layout-dividers'])
        kept = self.run_js(store.replace("{pages:[", "{dividers:[],pages:[") + cut(self.source, 'const LDEF = ', 'const VIEWDEF') + cut(self.source, 'const DIVS', 'const navItems') + 'result=DB;')
        self.assertEqual(kept['cockpit:package-layout:4']['dividers'], [])   # a layout that already has its own dividers (even none) is left alone


if __name__ == '__main__':
    unittest.main()
