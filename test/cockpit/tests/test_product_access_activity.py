"""Real local HTTP admission and cross-process shared-state regressions."""
from contextlib import contextmanager, redirect_stdout
import http.client
from http.server import ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from cockpit import appstate, ask, server, util
from cockpit.session_writer import session_writer


class ProductAccessActivityTests(unittest.TestCase):
    @contextmanager
    def local_server(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT': '0'}):
            root = Path(tmp); sessions = root / 'sessions'
            for name in ('a', 'b'):
                sd = sessions / name; sd.mkdir(parents=True)
                (sd / 'review-data.json').write_text(json.dumps({'session': name, 'product': True, 'prs': []}))
                (sd / 'events.jsonl').write_text('')
            cfg = util.load_config(); cfg['memory']['enabled'] = False
            with mock.patch.object(server, 'SESSIONS', sessions), \
                 mock.patch.object(server.Handler, 'sdir', sessions / 'a', create=True), \
                 mock.patch.object(server.Handler, 'cfg', cfg, create=True), \
                 mock.patch.object(util, 'HOME', root), mock.patch.object(Path, 'home', return_value=root):
                httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
                httpd.product = True; httpd.access_key = 'fixture-only-browser-access'
                thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
                try:
                    yield root, httpd, cfg
                finally:
                    httpd.shutdown(); httpd.server_close(); thread.join(timeout=3)

    def request(self, httpd, path, body=None, *, authorized=True, session='a', **headers):
        headers = {'X-Cockpit-Session': session, **headers}
        if authorized:
            headers['Authorization'] = 'Bearer ' + httpd.access_key
        if body is not None:
            headers['Content-Type'] = 'application/json'
        connection = http.client.HTTPConnection('127.0.0.1', httpd.server_address[1], timeout=5)
        try:
            connection.request('GET' if body is None else 'POST', path,
                               body=None if body is None else json.dumps(body), headers=headers)
            response = connection.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            connection.close()

    def test_originless_requests_need_browser_admission_before_data_or_ask(self):
        with self.local_server() as (root, httpd, cfg), mock.patch.object(ask, 'ask', return_value={'answer': 'fixture'}) as agent:
            for route, body in [('/api/data', None), ('/api/events', None), ('/api/ask', {'prompt': 'Question'})]:
                with mock.patch.object(server.Handler, '_data', side_effect=AssertionError('private payload before admission')):
                    status, _, _ = self.request(httpd, route, body, authorized=False)
                self.assertEqual(status, 403)
            agent.assert_not_called()
            status, _, _ = self.request(httpd, '/api/ask', {'prompt': 'Question'})
            self.assertEqual(status, 200); agent.assert_called_once()
            port = httpd.server_address[1]
            status, _, _ = self.request(httpd, '/api/ask', {'prompt': 'Question'}, Origin='http://foreign.test:'+str(port))
            self.assertEqual(status, 403); self.assertEqual(agent.call_count, 1)
            status, _, _ = self.request(httpd, '/api/health', authorized=False)
            self.assertEqual(status, 200)

    def test_browser_bootstrap_cookie_and_restart_invalidation(self):
        with self.local_server() as (root, httpd, cfg):
            status, body, _ = self.request(httpd, '/_access', authorized=False)
            self.assertEqual(status, 200); self.assertNotIn(httpd.access_key.encode(), body)
            status, _, _ = self.request(httpd, '/api/access', {}, authorized=False)
            self.assertEqual(status, 403)
            status, _, headers = self.request(httpd, '/api/access', {})
            self.assertEqual(status, 200)
            cookie = headers['Set-Cookie']; self.assertIn('HttpOnly', cookie); self.assertIn('SameSite=Strict', cookie)
            status, _, _ = self.request(httpd, '/api/data', authorized=False, Cookie=cookie.split(';')[0])
            self.assertEqual(status, 200)
            httpd.access_key = 'replacement-fixture-access'
            status, _, _ = self.request(httpd, '/api/data', authorized=False, Cookie=cookie.split(';')[0])
            self.assertEqual(status, 403)

    def test_browser_asset_requests_can_run_concurrently(self):
        with self.local_server() as (root, httpd, cfg):
            barrier = threading.Barrier(2)
            original = server.Handler._get_selected
            def parallel(handler, route):
                if route == '/api/data':
                    barrier.wait(timeout=3)
                return original(handler, route)
            results = []
            with mock.patch.object(server.Handler, '_get_selected', new=parallel):
                threads = [threading.Thread(target=lambda: results.append(self.request(httpd, '/api/data')[0])) for _ in range(2)]
                for worker in threads:
                    worker.start()
                for worker in threads:
                    worker.join(timeout=5)
            self.assertEqual(results, [200, 200])

    def test_real_serve_delivers_access_only_to_browser_not_console(self):
        with self.local_server() as (root, unused, cfg):
            from urllib.parse import parse_qs, urlsplit
            instance = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
            def timer(delay, callback):
                return mock.Mock(start=callback)
            output = io.StringIO()
            with mock.patch.object(server, 'session_config', return_value=cfg), \
                 mock.patch.object(server, 'ThreadingHTTPServer', return_value=instance), \
                 mock.patch.object(instance, 'serve_forever'), mock.patch.object(server.threading, 'Timer', side_effect=timer), \
                 mock.patch('webbrowser.open') as browser, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT': '1'}), redirect_stdout(output):
                server.serve(root / 'sessions' / 'a', style='cockpit')
            url = urlsplit(browser.call_args.args[0])
            self.assertEqual(url.path, '/_access')
            self.assertEqual(parse_qs(url.fragment)['key'], [instance.access_key])
            self.assertNotIn(instance.access_key, output.getvalue())
            self.assertTrue(instance.product)

    def test_trash_refuses_another_tab_inflight_note_then_preserves_it_in_recoverable_trash(self):
        with self.local_server() as (root, httpd, cfg):
            entered, finish = threading.Event(), threading.Event()
            original = server.append_events
            def paused(*args, **kwargs):
                entered.set()
                if not finish.wait(4):
                    raise RuntimeError('fixture did not release note')
                return original(*args, **kwargs)
            outcome = []
            with mock.patch.object(server, 'append_events', side_effect=paused):
                writer = threading.Thread(target=lambda: outcome.append(self.request(httpd, '/api/event',
                    {'type': 'note', 'text': 'Keep this note'}, session='b')))
                writer.start()
                try:
                    self.assertTrue(entered.wait(3))
                    status, _, _ = self.request(httpd, '/api/session-delete', {'session': 'b'})
                    self.assertEqual(status, 409)
                    self.assertTrue((root / 'sessions/b/review-data.json').is_file())
                finally:
                    finish.set(); writer.join(timeout=5)
            self.assertEqual(outcome[0][0], 200)
            status, body, _ = self.request(httpd, '/api/session-delete', {'session': 'b'})
            self.assertEqual(status, 200)
            deleted = json.loads(body)
            moved = Path(deleted['trash'].replace('~', str(root), 1))
            self.assertIn('Keep this note', (moved / 'events.jsonl').read_text())
            self.assertFalse((root / 'sessions/b').exists())

    def test_trash_refuses_cross_process_refresh_writer(self):
        with self.local_server() as (root, httpd, cfg):
            sd = root / 'sessions/b'; signal = root / 'writer-ready'
            script = """import pathlib,sys,time
from cockpit.session_writer import session_writer
with session_writer(pathlib.Path(sys.argv[1])):
 pathlib.Path(sys.argv[2]).write_text('ready')
 while pathlib.Path(sys.argv[2]).exists(): time.sleep(.01)
"""
            child = subprocess.Popen([sys.executable, '-B', '-c', script, str(sd), str(signal)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                until = time.monotonic() + 5
                while not signal.exists() and time.monotonic() < until and child.poll() is None:
                    time.sleep(.01)
                self.assertTrue(signal.exists())
                status, _, _ = self.request(httpd, '/api/session-delete', {'session': 'b'})
                self.assertEqual(status, 409)
                self.assertTrue((sd / 'review-data.json').is_file())
            finally:
                signal.unlink(missing_ok=True)
                _, error = child.communicate(timeout=5)
            self.assertEqual(child.returncode, 0, error)

    def test_two_server_processes_preserve_independent_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); start = root / 'start'
            script = """import pathlib,sys,time
from cockpit import appstate
start=pathlib.Path(sys.argv[1]); key=sys.argv[2]
original=appstate.write_json
def slow_write(*args):
 time.sleep(.1)
 return original(*args)
appstate.write_json=slow_write
while not start.exists(): time.sleep(.01)
appstate.update({key:key})
"""
            env = {**os.environ, 'REVIEW_COCKPIT_HOME': str(root)}
            children = [subprocess.Popen([sys.executable, '-B', '-c', script, str(start), key], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for key in ('cockpit:theme', 'cockpit:page-view')]
            start.write_text('go')
            for child in children:
                _, error = child.communicate(timeout=15)
                self.assertEqual(child.returncode, 0, error)
            data = json.loads((root / 'app-state.json').read_text())
            self.assertEqual(data, {key: key for key in ('cockpit:theme', 'cockpit:page-view')})
