"""Regression checks for finding provenance and shared export contents."""
import base64
import copy
import json
import os
from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

from cockpit import attention, collect, export, managed_work, util, view
from cockpit.adapters import qodo_cli, qodo_comments, qodo_local, scanners
from tests import test_product_finding_scope as scope_tests
from tests import test_product_enrich_refresh as refresh_tests
from tests.test_product import HEAD


class ProductQualityContractTests(unittest.TestCase):
    def setUp(self):
        self.scope = scope_tests.ProductFindingScopeTests()
        self.environment = mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT': '0'})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_managed_locations_require_current_revision_and_side_without_guessing_origin(self):
        cases = [(None, 'a' * 40, 'RIGHT', False), ('git_pr', 'a' * 40, 'LEFT', False),
                 (None, HEAD, None, False), (None, HEAD, 'LEFT', False), (None, None, 'RIGHT', False),
                 (None, HEAD, 'RIGHT', True), ('git_pr', HEAD, 'LEFT', True)]
        for origin, sha, side, current in cases:
            with self.subTest(origin=origin, sha=sha, side=side):
                pr = self.scope.pr()
                raw = {'id': 'f', 'title': 'Useful finding', 'description': 'Keep the evidence',
                       'git_sha': sha, 'review_source': origin,
                       'location': {'file_path': 'a.py', 'start_line': 1, 'side': side}}
                before = copy.deepcopy(raw)
                pr['findings'] = [qodo_cli.to_finding(pr, raw)]
                pr['attention'] = {'blocks': [{'id': 'b', 'path': 'a.py', 'side': 'old' if side == 'LEFT' else 'new',
                                               'from': 1, 'to': 1, 'lines': 1, 'tier': 'review'}]}
                public = view._pr_view(pr)
                finding = public['findings'][0]
                rendered = self.scope.render(public)
                self.assertEqual(raw, before)
                self.assertEqual(finding['review_source'], origin or 'unknown')
                self.assertEqual(finding['source'], 'qodo')
                self.assertIsNone(finding['local'])
                self.assertEqual(finding['current_anchor'], current)
                self.assertEqual(finding['source_location']['path'], 'a.py')
                self.assertEqual(finding['source_location']['git_sha'], sha)
                self.assertEqual(finding['body'], 'Keep the evidence')
                if current:
                    self.assertEqual(finding['path'], 'a.py')
                    self.assertIn('data-act="gofile"', rendered['app'])
                    self.assertEqual(rendered['anchors'][0]['side'], 'old' if side == 'LEFT' else 'new')
                    self.assertEqual(rendered['unitFindings'], [finding['id']])
                else:
                    self.assertIsNone(finding['path'])
                    self.assertNotIn('path', rendered['anchors'][0])
                    self.assertIn('Original source: a.py:1', rendered['primary'])
                    self.assertIn('Original source: a.py:1', rendered['app'])
                    self.assertNotIn('data-act="gofile"', rendered['app'])
                    self.assertFalse(rendered['unitFindings'])

    def test_saved_unknown_origin_snapshot_is_qualified_on_read_without_rewriting_it(self):
        pr = self.scope.pr()
        pr['findings'] = [{'id': 'saved', 'source': 'qodo', 'review_source': 'unknown',
                           'git_sha': 'a' * 40, 'side': 'RIGHT', 'path': 'a.py', 'line': 1,
                           'title': 'Saved finding', 'body': 'Preserved', 'severity': 'medium'}]
        pr['attention'] = {'blocks': [{'id': 'b', 'path': 'a.py', 'from': 1, 'to': 1, 'lines': 1, 'tier': 'review'}]}
        before = copy.deepcopy(pr)
        rendered = self.scope.render(view._pr_view(pr))
        self.assertEqual(pr, before)
        self.assertIn('Original source: a.py:1', rendered['primary'])
        self.assertNotIn('path', rendered['anchors'][0])
        self.assertNotIn('data-act="gofile"', rendered['app'])
        self.assertFalse(rendered['unitFindings'])

    def test_managed_reported_path_outside_collected_files_has_no_current_anchor(self):
        pr = self.scope.pr()
        finding = qodo_cli.to_finding(pr, {'id': 'f', 'git_sha': HEAD, 'review_source': 'git_pr',
                                            'file_path': 'not-collected.py', 'start_line': 1, 'side': 'RIGHT'})
        self.assertFalse(finding['current_anchor'])
        self.assertNotIn('path', finding)
        self.assertEqual(finding['source_location']['path'], 'not-collected.py')

    def test_saved_local_import_preserves_each_original_review_reference(self):
        pr = self.scope.pr()
        first = {'findings': [{'id': 'old', 'title': 'Earlier concern', 'file_path': 'a.py', 'start_line': 1}],
                 'meta': {'local_review_id': 'review-one', 'local_review_ids': {'old': 'review-one'},
                          'checkpoint': {'created_at': '2026-01-01T00:00:00Z'}}}
        second = {'findings': [{'id': 'old', 'title': 'Earlier concern', 'local_review_id': 'review-two'}, {'id': 'new', 'title': 'New concern'}],
                  'finding_state': {'complete': True, 'introduced': ['new'], 'still_open': ['old']},
                  'meta': {'local_review_id': 'review-two',
                           'local_review_ids': {'old': 'review-one', 'new': 'review-two'}}}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(qodo_local, 'STORE', Path(tmp)):
            qodo_local.add(first, pr=pr['key'], commit='a' * 40)
            qodo_local.add(second, pr=pr['key'], commit=HEAD)
            findings = {f['qodo_id']: f for f in qodo_local.collect(pr, {})}
        self.assertEqual(findings['old']['local']['review_id'], 'review-one')
        self.assertEqual(findings['new']['local']['review_id'], 'review-two')
        self.assertEqual(findings['old']['local']['commit'], 'a' * 40)
        self.assertEqual(findings['old']['local']['at'], '2026-01-01T00:00:00Z')
        self.assertIsNone(findings['old'].get('line'))
        self.assertEqual(findings['old']['local']['line'], 1)
        self.assertNotIn('status', findings['old'])
        self.assertEqual(findings['old']['title'], 'Earlier concern')

    def test_legacy_local_reference_fallback_is_preserved(self):
        pr = self.scope.pr()
        rec = {'local_review_id': 'record-review', 'commit': HEAD}
        for own, expected in [(None, 'record-review'), ('finding-review', 'finding-review')]:
            finding = qodo_local.to_finding(pr, rec, {'id': 'f', 'local_review_id': own}, None)
            self.assertEqual(finding['local']['review_id'], expected)

        carried = qodo_local.to_finding(pr, {'local_review_id': 'new-run', 'commit': HEAD, 'ran_at': '2026-01-02',
                    'result': {'meta': {'local_review_ids': {'f': 'old-run'}}}},
                    {'id': 'f', 'file_path': 'a.py', 'start_line': 1}, None)
        self.assertEqual(carried['local']['review_id'], 'old-run')
        self.assertIsNone(carried['local']['commit'])
        self.assertIsNone(carried['local']['at'])
        self.assertIsNone(carried.get('line'))
        self.assertEqual(carried['local']['line'], 1)

    def test_optional_badge_uses_the_existing_informational_severity(self):
        for badge in ('Optional', 'Informational', 'info'):
            parsed = qodo_comments._parse_item('1. Useful optional advice',
                     '<details><summary>Description</summary><pre>Helpful context</pre></details>', badge)
            self.assertEqual(parsed['severity'], 'low')
            self.assertEqual(qodo_cli._severity('informational'), 'low')
            self.assertEqual(parsed['body'], 'Helpful context')
        self.assertEqual(qodo_comments._parse_item('1. Required concern', '', 'High')['severity'], 'high')

    def test_refresh_preserves_latest_selection_on_success_and_late_failure(self):
        from cockpit import enrich
        from cockpit.server import append_events
        helper = refresh_tests.ProductEnrichRefreshTests()
        with helper.session() as (root, sd, cfg, read):
            latest = sd.parent / 'latest'
            self.assertEqual(latest.read_text(), 's')
            (sd.parent / 'other').mkdir()
            latest.write_text('other')
            enrich.enrich(sd, helper.authored())
            before = (sd / 'review-data.json').read_bytes()
            append_events(sd, [{'type': 'note', 'note_id': 'keep', 'text': 'Reader note'}], 's')
            events = (sd / 'events.jsonl').read_bytes()
            with mock.patch.object(enrich, 'enrich', side_effect=RuntimeError('controlled enrichment failure')):
                with self.assertRaisesRegex(RuntimeError, 'controlled enrichment failure'):
                    managed_work.refresh(sd, json.loads(before), cfg)
            self.assertEqual((sd / 'review-data.json').read_bytes(), before)
            self.assertEqual((sd / 'events.jsonl').read_bytes(), events)
            self.assertEqual(latest.read_text(), 'other')
            managed_work.refresh(sd, json.loads(before), cfg)
            self.assertEqual(latest.read_text(), 'other')
            self.assertEqual((sd / 'events.jsonl').read_bytes(), events)
            collect.build([self.scope.pr()], cfg, demo=True, session='new', dest=sd.parent / 'new')
            self.assertEqual(latest.read_text(), 'new')

    def test_scanner_annotations_retain_multiline_ranges_in_the_public_view(self):
        annotation = {'check': 'Scan', 'path': 'a.py', 'line': 2, 'end_line': 5,
                      'level': 'failure', 'title': 'Multiline concern', 'message': 'Inspect the whole range'}
        for parser in (scanners.sonar, scanners.check_annotations):
            for end in (5, None):
                with self.subTest(parser=parser.__name__, end=end):
                    pr = self.scope.pr()
                    pr['_annotations'] = [{**annotation, 'end_line': end}]
                    pr['findings'] = parser(pr, [], {'checks': ['Scan'], '_key': parser.__name__})
                    public = view._pr_view(pr)['findings'][0]
                    self.assertEqual(public['line'], 2)
                    self.assertEqual(public['end_line'], end or 2)
                    self.assertEqual(public['path'], 'a.py')

    def test_current_open_critical_findings_keep_generated_code_on_the_reading_list(self):
        for sha, status, guarded in ((HEAD, 'open', True), (HEAD, 'resolved', False), ('a' * 40, 'open', False)):
            with self.subTest(sha=sha, status=status):
                pr = self.scope.pr()
                pr['files'][0]['role'] = 'generated'
                pr['findings'] = [qodo_cli.to_finding(pr, {'id': 'critical', 'severity': 'critical',
                                  'review_source': 'git_pr', 'git_sha': sha,
                                  'attribution_status': 'full_implementation' if status == 'resolved' else None,
                                  'file_path': 'a.py', 'start_line': 1, 'side': 'RIGHT'})]
                pr['attention'], _ = attention.compute(pr)
                public = view._pr_view(pr)
                self.assertEqual(public['findings'][0]['severity'], 'critical')
                self.assertEqual(any(r['tier'] != 'skip' for r in pr['attention']['ranges']), guarded)
        scores = {}
        for severity in ('high', 'critical'):
            pr = self.scope.pr()
            pr['findings'] = [qodo_cli.to_finding(pr, {'id': severity, 'severity': severity, 'git_sha': HEAD,
                              'review_source': 'git_pr', 'file_path': 'a.py', 'start_line': 1, 'side': 'RIGHT'})]
            plan, _ = attention.compute(pr)
            scores[severity] = max(b['score'] for b in plan['blocks'])
        self.assertGreaterEqual(scores['critical'], scores['high'])

    def test_guided_screenshot_urls_cannot_create_html_attributes(self):
        source = (util.ROOT / 'app/styles/guided.html').read_text()
        renderer = source[source.index('function screenProduct()'):source.index('function codeBehind(')]
        kit = (util.ROOT / 'app/styles/kit.js').read_text()
        escape = next(line.strip() for line in kit.splitlines() if line.strip().startswith('const esc ='))
        url = 'https://example.test/image"onerror="marker()'
        html = self.scope.node(escape + '\nconst md=esc,codeBehind=()=>[];\n' + renderer + ';result=screenProduct();',
                               {'MEDIA': [{'src': url, 'title': 'Evidence', 'caption': ''}], 'S': {'shot': 0}})
        images = []
        class ParseImages(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == 'img':
                    images.append(dict(attrs))
        ParseImages().feed(html)
        self.assertEqual(len(images), 2)
        for image in images:
            self.assertEqual(set(image), {'src', 'alt'})
            self.assertEqual(image['src'], url)

    def test_full_app_export_embeds_only_referenced_contained_media_and_supports_nested_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sd = root / 'session'
            cfg = util.load_config()
            cfg['memory'] = {'enabled': False, 'auto_commit': False, 'amr': str(root / 'amr'), 'okf': str(root / 'okf')}
            cfg['notes']['enabled'] = False
            cfg['overlaps']['enabled'] = False
            cfg['adapters'] = []
            collect.build([self.scope.pr()], cfg, demo=True, session='shared', dest=sd)
            (sd / 'media' / 'shots').mkdir(parents=True)
            (sd / 'media' / 'shots' / 'after.png').write_bytes(b'image-content')
            (sd / 'media' / 'clip.mp4').write_bytes(b'video-content')
            (sd / 'media' / 'shots' / 'before.png').write_bytes(b'before-content')
            (sd / 'media' / 'unreferenced.txt').write_bytes(b'PRIVATE-UNREFERENCED')
            outside = root / 'outside.txt'
            outside.write_bytes(b'PRIVATE-OUTSIDE')
            data = json.loads((sd / 'review-data.json').read_text())
            sources = ['shots/after.png', 'clip.mp4', '../../outside.txt', str(outside), 'https://example.test/remote.png']
            if os.name != 'nt':
                (sd / 'media' / 'external.png').symlink_to(outside)
                sources.append('external.png')
            data['story'] = [{'kind': 'media', 'title': 'Evidence', 'src': src,
                              'type': 'video' if src.endswith('.mp4') else 'image'} for src in sources]
            data['prs'][0]['story'] = [{'kind': 'before_after', 'title': 'Change',
                                       'before': {'media': 'shots/before.png'}, 'after': {'media': 'shots/after.png'}}]
            (sd / 'review-data.json').write_text(json.dumps(data))
            with mock.patch.object(export, 'session_config', return_value=cfg):
                out = export.export(sd, root / 'shared.html', style='cockpit')
                written = []
                export.export(sd, root / 'all-styles.html', style='package', with_styles=True, written=written)
            app_copy = next(path for path in written if path.name.endswith('-cockpit.html'))
            html = out.read_text()
            copied = json.loads(re.search(r'window\.__COCKPIT__ = (.*?);</script>', app_copy.read_text(), re.S).group(1))
            self.assertEqual(set(copied['media']), {'shots/after.png', 'shots/before.png', 'clip.mp4'})
            payload = json.loads(re.search(r'window\.__COCKPIT__ = (.*?);</script>', html, re.S).group(1))
            self.assertEqual(set(payload['media']), {'shots/after.png', 'shots/before.png', 'clip.mp4'})
            self.assertEqual(base64.b64decode(payload['media']['shots/after.png'].split(',', 1)[1]), b'image-content')
            self.assertEqual(base64.b64decode(payload['media']['clip.mp4'].split(',', 1)[1]), b'video-content')
            self.assertEqual(base64.b64decode(payload['media']['shots/before.png'].split(',', 1)[1]), b'before-content')
            onepage = next(path for path in written if path.name.endswith('-onepage.html')).read_text()
            story = json.loads(re.search(r'<script[^>]*class="case-data"[^>]*>(.*?)</script>', onepage, re.S).group(1))
            self.assertEqual({m['file'] for m in story['media']}, {'shots/after.png', 'shots/before.png', 'clip.mp4',
                                                                  'https://example.test/remote.png'})
            for name in ('shots/after.png', 'shots/before.png', 'clip.mp4'):
                media = next(m for m in story['media'] if m['file'] == name)
                self.assertEqual(media['src'], payload['media'][name])
            for secret in (b'PRIVATE-UNREFERENCED', b'PRIVATE-OUTSIDE'):
                self.assertNotIn(base64.b64encode(secret).decode(), html)
                self.assertNotIn(secret.decode(), html)
                self.assertNotIn(base64.b64encode(secret).decode(), onepage)
