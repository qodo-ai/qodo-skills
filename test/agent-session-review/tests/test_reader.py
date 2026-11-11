import json
import subprocess
import unittest

from cockpit import util
from cockpit.styles import NOTICE_BAR

SCRIPT = ("const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={};"
          "vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));")


def cut(source, start, end):
    return source[source.index(start):source.index(end)]


class ReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (util.ROOT / 'app/styles/package.js').read_text() + '\n' + (util.ROOT / 'app/styles/reader.js').read_text()

    def run_js(self, code):
        result = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': code}), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_reader_lists_every_widget_with_its_page_name_above_the_first(self):
        stubs = ("const esc=String,sico=()=>'',widgetHtml=(w)=>'<p>'+w+'</p>',wname=(w,p)=>((p&&p.names)||{})[w]||w.toUpperCase(),"
                 "BLOCKS={a:{},b:{sub:()=>'2 open'},c:{}},LAYOUT={pages:[{id:'one',label:'Overview',widgets:['a','b']},{id:'two',label:'Risk',names:{c:'Blast'},widgets:['c']}]},"
                 "GLASSES='<svg class=\"g24\"></svg>',svg=(p,c='')=>'<svg class=\"'+c+'\">'+p+'</svg>',WDONE='_done',wseq=()=>[['a','one'],['b','one'],['c','two']],wpos=(q)=>q.findIndex(([w])=>w===WFULL),store={get:(k,d)=>d,set(){}},document={documentElement:{style:{setProperty(){}}},querySelectorAll:()=>[]};let READER='scroll',RDAT=0,WFULL='b';")
        code = stubs + cut(self.source, 'const RDICON = ', 'function rdOpen(')
        html = self.run_js(code + "result=rdBody([['a','one'],['b','one'],['c','two']],(i)=>' data-rdfocus=\"'+i+'\"');")
        self.assertEqual(html.count('class="rd-pg"'), 2)
        self.assertLess(html.index('>Overview</p>'), html.index('>A</h2>'))
        self.assertLess(html.index('>B</h2>'), html.index('>Risk</p>'))
        self.assertIn('>Blast</h2>', html)   # a widget's name on its own page
        self.assertIn('data-rdfocus="2"', html)
        self.assertIn('<span class="ssub">2 open</span>', html)
        seg = self.run_js(code + 'result=rdSeg();')
        self.assertIn('data-rdmode="scroll" aria-pressed="true"', seg)
        self.assertIn('data-rdmode="step" aria-pressed="false"', seg)

    def test_one_header_for_both_modes_with_the_steps_in_the_middle(self):
        stubs = ("const esc=String,sico=()=>'',widgetHtml=()=>'',wname=(w)=>w.toUpperCase(),BLOCKS={a:{},b:{sub:()=>'2 open'},c:{}},LAYOUT={pages:[{id:'one',label:'O',widgets:['a','b','c']}]},"
                 "GLASSES='<svg class=\"g24\"></svg>',svg=(p,c='')=>'<svg class=\"'+c+'\">'+p+'</svg>',WDONE='_done',wseq=()=>[['a','one'],['b','one'],['c','one']],wpos=(q)=>q.findIndex(([w])=>w===WFULL),store={get:(k,d)=>d,set(){}},document={documentElement:{style:{setProperty(){}}},querySelectorAll:()=>[]};let READER='step',RDAT=2,WFULL='b';")
        code = stubs + cut(self.source, 'const RDICON = ', 'function rdOpen(')
        step = self.run_js(code + 'result=rdHead(true);')
        foot = self.run_js(code + 'result=rdFoot(true);')
        self.assertIn('<span class="rd-hc">', step)
        hc, hr = step.index('<span class="rd-hc">'), step.index('<span class="rd-hr">')
        self.assertTrue(hc < step.index('data-rdmode="scroll"') < step.index('data-rdfs="-1"') < hr)   # the mode and the text size in the middle
        self.assertTrue(hr < step.index('rd-find') < step.index('data-wfm-close'))   # Find and close on the right
        self.assertNotIn('data-wfstep', step)   # the steps are in the footer
        self.assertIn('class="rd-mi"', step)   # Scroll and Stepper carry icons
        self.assertTrue(foot.startswith('<div class="rd-ft">') and foot.index('data-rdend="first"') < foot.index('data-wfstep="-1"') < foot.index('data-wfstep="1"') < foot.index('data-rdend="last"'))   # « ‹ › », centred in the footer
        self.assertIn('title="Open in Reader">${GLASSES}</button>', self.source)   # every widget opens Reader with the glasses icon
        self.assertIn('data-wfstep="-1"', foot)
        self.assertIn('>2 of 3</span>', foot)
        self.assertIn('data-wfm-close', step)
        self.assertNotIn('<h2>', step)   # the widget's title is in the body, not the header
        self.assertIn('class="sico"', step)   # the glasses icon is drawn like a widget icon, not filled
        scroll = self.run_js(code + "READER='scroll';result=rdHead(false)+rdFoot(false);")
        self.assertIn('data-rdstep="1" aria-label="Next widget" title="Next widget (→)" disabled', scroll)   # the last widget is in focus
        self.assertIn('data-rdclose', scroll)
        self.assertIn('data-rdpg aria-pressed="true"', scroll)   # page boundaries: a toggle in Scroll
        self.assertNotIn('data-rdpg', step)   # one widget at a time has no pages to separate
        title = self.run_js(code + "result=rdTitle('b','one');")
        self.assertIn('<h2>B</h2><span class="ssub">2 open</span>', title)

    def test_find_suggests_widgets_by_name_page_and_text(self):
        stubs = ("const esc=String,sico=()=>'',widgetHtml=()=>'',wname=(w,p)=>({a:'Verdict',b:'Blast radius',c:'Hop by hop'})[w],WIDGETS={a:['Verdict','The bottom line'],b:['Blast radius','How far a fault reaches'],c:['Hop by hop','One request across systems']},"
                 "BLOCKS={a:{},b:{},c:{}},LAYOUT={pages:[{id:'o',label:'Overview',widgets:['a']},{id:'r',label:'Merge Risk',widgets:['b','c']}]},GLASSES='<svg></svg>',svg=(p)=>p,WDONE='_done',"
                 "wseq=()=>[['a','o'],['b','r'],['c','r']],wpos=()=>0,store={get:(k,d)=>d,set(){}},document={documentElement:{style:{setProperty(){}}},querySelectorAll:()=>[],querySelector:(q)=>q.includes('rdi=') && q.includes('2')?{textContent:'the engine reads dropped_findings here'}:null,addEventListener(){}};let READER='scroll',RDAT=0,WFULL=null;")
        code = stubs + self.source[self.source.index('const RDICON = '):self.source.index('function rdOpen(')] + self.source[self.source.index('function rdFind('):self.source.index('function rdFindDraw(')]
        hits = self.run_js(code + "result=[rdFind('blast').map(h=>h.name), rdFind('merge risk').map(h=>h.name), rdFind('dropped_findings').map(h=>[h.name,h.snip])];")
        self.assertEqual(hits[0], ['Blast radius'])
        self.assertEqual(hits[1], ['Blast radius', 'Hop by hop'])   # by page name
        self.assertEqual(hits[2][0][0], 'Hop by hop'); self.assertIn('dropped_findings', hits[2][0][1])   # by the widget's text, with a snippet
        self.assertTrue(self.source.index('rd-find') < self.source.index('function rdFoot('))   # Find is in the header; the steps are in the footer
        self.assertIn('!(e.target.matches && e.target.matches(".rd-q"))', self.source)   # Escape in Find doesn't close Reader

    def test_expand_opens_reader_in_stepper_and_scrolling_never_moves_the_focus(self):
        self.assertIn('READER = "step"; WFULL = b.dataset.wfull;', self.source)
        self.assertIn('${rdHead(true)}<div class="wfm-b sbody">${done ? wdoneHtml(seq) : rdTitle(WFULL, WFPAGE) + widgetHtml(WFULL)}', self.source)
        self.assertNotIn('addEventListener("scroll"', self.source[self.source.index('function rdDraw()'):])
        self.assertNotIn('class="wfm-b rd-b"', self.source)   # Scroll's body doesn't take the single-widget stepper's rules

    def test_header_has_reader_and_share_has_export(self):
        self.assertIn('data-reader aria-label="Reader', self.source)
        self.assertIn('${GLASSES}<span>Reader</span>', self.source)
        self.assertLess((util.ROOT / 'app/styles/package.js').stat().st_size, 524288)   # Reader lives in reader.js to keep package.js under the limit
        self.assertEqual(self.source.count('/*@READER@*/'), 1)
        self.assertIn("('/*@READER@*/', 'reader.js')", (util.ROOT / 'cockpit/styles.py').read_text())
        code = "const C={prs:[1,2]},COPYICON='';" + cut(self.source, 'function shareMenu()', 'function shareClose(') + 'result=shareMenu();'
        html = self.run_js(code)
        self.assertLess(html.index('data-share-copy'), html.index('data-share-export'))
        self.assertIn('Copy share prompt', html); self.assertNotIn('sh-cp', html)   # plain menu rows, not strong buttons
        self.assertIn('Export PDF', html)

    def test_export_prints_reader_layout_and_restores_the_page(self):
        body = self.source[self.source.index('function rdExport()'):]
        body = body[:body.index('\n}\n') + 3]
        for part in ('R.dataset.theme = "light"', 'd.open = true', '"afterprint", done, { once: true }', 'print()', 'el.remove()'):
            self.assertIn(part, body)

    def test_notice_is_a_toast_until_acknowledged(self):
        self.assertIn('hidden><span>{{NOTICE}}</span>', NOTICE_BAR)
        self.assertIn('>Got it</button>', NOTICE_BAR)
        self.assertIn('cockpit:notice-ack', NOTICE_BAR)
        self.assertNotIn('bottom:0;left', NOTICE_BAR)   # no longer a bar pinned to the bottom edge


if __name__ == '__main__':
    unittest.main()
