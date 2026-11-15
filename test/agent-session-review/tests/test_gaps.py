import json
import tempfile
import unittest
from pathlib import Path

from cockpit.gaps import gaps


def session(root, data, builder=None, triage=()):
    d = Path(root) / '20261115-000000-abcd'
    d.mkdir()
    (d / 'review-data.json').write_text(json.dumps(data))
    if builder is not None:
        (d / 'builder.json').write_text(json.dumps(builder))
    if triage:
        (d / 'triage').mkdir()
        for n in triage:
            (d / 'triage' / f'triage-{n}.json').write_text('{}')
    return d


PRS = [{'key': 'o/a#1', 'number': 1}, {'key': 'o/b#2', 'number': 2}]


class GapsTests(unittest.TestCase):
    def test_a_fresh_collection_lists_every_empty_widget(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = gaps(session(tmp, {'prs': PRS}))
        names = [r['widget'] for r in rows]
        for w in ('Product summary', 'Primary behaviors', 'Human decisions', 'Contract changes', 'System', 'Qodo risk assessment',
                  'Execution paths', 'Code changes', 'Agent decisions (o/a#1)', 'Guided reading (o/b#2)', 'Findings review (o/b#2)'):
            self.assertIn(w, names)
        self.assertTrue(next(r for r in rows if r['widget'] == 'Product assets')['optional'])   # only if the sources have links
        self.assertEqual(next(r for r in rows if r['widget'] == 'Execution paths')['via'], 'walkthrough --builder')

    def test_a_filled_review_has_no_gaps(self):
        prs = [{**p, 'decisions': [{'text': 'x'}], 'layers': [{'title': 'x'}]} for p in PRS]
        data = {'prs': prs, 'system': {'contracts': [{}]}, 'impact': [{'factors': {'radius': {'level': 'low'}}}],
                'story': [{'kind': 'brief', 'assets': [{'kind': 'prd', 'url': 'https://x'}]},
                          {'kind': 'flow', 'answers': [{'q': 'q', 'a': 'a'}], 'decisions': [{}], 'contracts': [{}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(gaps(session(tmp, data, builder={'files': [{}], 'flows': [{}]}, triage=(1, 2))), [])

    def test_a_flow_skip_settles_the_flow_widgets(self):
        with tempfile.TemporaryDirectory() as tmp:
            names = [r['widget'] for r in gaps(session(tmp, {'prs': [], 'story': [{'kind': 'flow', 'skip': 'config only'}]}))]
        self.assertNotIn('Primary behaviors', names); self.assertNotIn('Contract changes', names)

    def test_the_skill_fills_gaps_instead_of_asking(self):
        root = Path(__file__).resolve().parents[3] / 'skills/qodo-agent-session-review'
        skill = (root / 'SKILL.md').read_text()
        self.assertIn('gaps --session <id>', skill); self.assertIn('Repeat until `gaps` exits 0', skill)
        self.assertIn('never ask the user to supply missing information', skill)
        for f in ('runtime/app/styles/package.js', 'runtime/app/styles/walkthrough.js'):
            text = (root / f).read_text()
            self.assertNotIn('code-review-master', text); self.assertNotIn('qodo-findings-triage', text)   # personal skills customers don't have


if __name__ == '__main__':
    unittest.main()
