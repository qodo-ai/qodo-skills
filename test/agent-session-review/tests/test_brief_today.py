import json
import subprocess
import unittest

from cockpit import util

SCRIPT = ("const vm=require('node:vm'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8')),c={};"
          "vm.createContext(c);vm.runInContext(x.code,c);process.stdout.write(JSON.stringify(c.result));")
PARAS = "[{label:'Today',text:'old'},{label:'Why',text:'because'},{label:'What',text:'new'},{label:'How',text:'mech'}]"


def cut(source, start, end):
    return source[source.index(start):source.index(end)]


class BriefTodayTests(unittest.TestCase):
    def run_js(self, code):
        result = subprocess.run(['node', '-e', SCRIPT], input=json.dumps({'code': code}), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_today_is_its_own_part_in_every_style(self):
        for name in ('package.js', 'focus.html'):
            with self.subTest(style=name):
                src = (util.ROOT / 'app/styles' / name).read_text()
                code = f"const BRIEF={{paragraphs:{PARAS}}};" + cut(src, 'const BKIND = ', 'const CLAUDE_RAYS' if name == 'package.js' else 'function heroHtml') + 'result=briefParts();'
                parts = self.run_js(code)
                self.assertEqual((parts['today'], parts['what']), (['old'], ['new']))   # pre-change behavior never reads as What
                self.assertIn('["today", "Today"]', src)   # and the hero has a Today tab

    def test_summary_has_three_sections_with_or_without_a_flow(self):
        src = (util.ROOT / 'app/styles/package.js').read_text()
        body = cut(src, 'function bSummary()', 'const flowOn = ')
        stubs = ("const md=String,C={blurb:'b'},heroHtml=()=>'HERO',assetsHtml=()=>'',briefCard=(t,b)=>b,"
                 f"BRIEF={{lede:'the change',paragraphs:{PARAS}}};let FLOWON=false;const flowOn=()=>FLOWON;")
        parts = cut(src, 'const BKIND = ', 'const CLAUDE_RAYS')
        for flow in (False, True):
            with self.subTest(flow=flow):
                html = self.run_js(stubs + parts + body.split('\nconst BEH6')[0] + f';FLOWON={str(flow).lower()};result=bSummary();')
                self.assertIn('bsec-today', html); self.assertIn('>Today<', html); self.assertIn('>The change<', html); self.assertIn('>Why<', html)


if __name__ == '__main__':
    unittest.main()
