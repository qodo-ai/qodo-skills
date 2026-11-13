import json
import subprocess
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from cockpit.adapters import managed
from cockpit.adapters.managed import BudgetExceeded, Client, RateLimited, ReadBudget, ReadError, read_operation


class ReadBudgetTests(unittest.TestCase):
    def test_an_operation_has_no_default_cap_on_reads_or_time(self):
        budget = ReadBudget()
        for _ in range(500):   # far past the old 96-read cap
            self.assertEqual(budget.reserve(), managed.READ_TIMEOUT_SECONDS)   # each read keeps its own timeout
        summary = budget.summary()
        self.assertEqual((summary['calls'], summary['max_calls'], summary['remaining_seconds'], summary['exhausted']), (500, None, None, False))

    def test_a_caller_can_still_set_its_own_limit(self):
        budget = ReadBudget(max_calls=2)
        budget.reserve(); budget.reserve()
        with self.assertRaises(BudgetExceeded):
            budget.reserve()
        self.assertTrue(budget.summary()['exhausted'])
        timed = ReadBudget(seconds=5)
        self.assertLessEqual(timed.reserve(), 5)   # the read timeout never outlasts the caller's limit
        self.assertIsNotNone(timed.summary()['remaining_seconds'])


    def test_reads_that_keep_timing_out_stop_the_operation(self):
        budget = ReadBudget()
        client = Client('qodo', budget=budget)
        with mock.patch('subprocess.run', side_effect=subprocess.TimeoutExpired('qodo', 1)):
            for _ in range(managed.MAX_TIMEOUTS_IN_A_ROW):
                with self.assertRaises(ReadError):
                    client.read('codebase', 'search-repos')
            with self.assertRaises(BudgetExceeded):
                client.read('codebase', 'search-repos')   # a stalled service: the rest is marked unavailable, not waited for
        self.assertTrue(budget.summary()['exhausted'])
        budget.timeouts = 1
        ok = SimpleNamespace(stdout=json.dumps({'repos': []}), stderr='', returncode=0)
        with mock.patch('subprocess.run', return_value=ok):
            Client('qodo', budget=budget).read('codebase', 'search-repos')
        self.assertEqual(budget.timeouts, 0)   # a read that answers resets the count

    def test_a_rate_limited_read_waits_for_the_reset_and_retries(self):
        limited = SimpleNamespace(stdout=json.dumps({'error': {'code': 'MT-RATE-LIMITED', 'metadata': {'retry_after': 7}}}), stderr='', returncode=1)
        ok = SimpleNamespace(stdout=json.dumps({'repos': []}), stderr='', returncode=0)
        with mock.patch('subprocess.run', side_effect=[limited, ok]), mock.patch('time.sleep') as slept:
            self.assertEqual(Client('qodo', budget=ReadBudget()).read('codebase', 'search-repos'), {'repos': []})
        slept.assert_called_once_with(7)
        with mock.patch('subprocess.run', return_value=limited), mock.patch('time.sleep'):
            with self.assertRaises(RateLimited):
                Client('qodo', budget=ReadBudget()).read('codebase', 'search-repos')   # gives up after RATE_LIMIT_RETRIES
        with mock.patch('subprocess.run', return_value=limited), mock.patch('time.sleep') as slept:
            with self.assertRaises(RateLimited):
                Client('qodo', budget=ReadBudget(seconds=3)).read('codebase', 'search-repos')   # never waits past the caller's limit
        slept.assert_not_called()

    def test_a_read_can_carry_its_own_deadline(self):
        ok = SimpleNamespace(stdout=json.dumps({'repos': []}), stderr='', returncode=0)
        with read_operation() as op, mock.patch('subprocess.run', return_value=ok) as run:
            Client('qodo').read('codebase', 'search-repos', max_seconds=4)
            self.assertAlmostEqual(run.call_args.kwargs['timeout'], 4, places=2)   # the notes step's time left, not the full 120 s
            self.assertEqual(op.calls, 1)   # and it still counts toward the operation
        from cockpit import notes
        src = (notes.__file__ and open(notes.__file__).read())
        self.assertIn("read('review-notes', leaf, max_seconds=left", src)
        self.assertIn("_END.reset(token)", src)

    def test_rate_limit_retries_count_as_calls_and_stay_in_time(self):
        limited = SimpleNamespace(stdout=json.dumps({'error': {'code': 'MT-RATE-LIMITED', 'metadata': {'retry_after': 1}}}), stderr='', returncode=1)
        with mock.patch('subprocess.run', return_value=limited) as run, mock.patch('time.sleep'):
            with self.assertRaises(BudgetExceeded):
                Client('qodo', budget=ReadBudget(max_calls=2)).read('codebase', 'search-repos')
        self.assertEqual(run.call_count, 2)   # a call cap holds across retries
        clock = [100.0]
        with mock.patch('subprocess.run', return_value=limited) as run, mock.patch('time.sleep', side_effect=lambda s: clock.__setitem__(0, clock[0] + s)), \
                mock.patch('time.monotonic', side_effect=lambda: clock[0]):
            with self.assertRaises((RateLimited, BudgetExceeded)):
                Client('qodo', budget=ReadBudget()).read('codebase', 'search-repos', max_seconds=2.5)
        timeouts = [c.kwargs['timeout'] for c in run.call_args_list]
        self.assertEqual(timeouts[0], 2.5); self.assertTrue(all(b < a for a, b in zip(timeouts, timeouts[1:])))   # each retry gets only the time still left

    def test_persistent_throttling_stops_the_operation_instead_of_waiting_per_read(self):
        limited = SimpleNamespace(stdout=json.dumps({'error': {'code': 'MT-RATE-LIMITED', 'metadata': {'retry_after': 60}}}), stderr='', returncode=1)
        budget = ReadBudget()
        with mock.patch('subprocess.run', return_value=limited), mock.patch('time.sleep') as slept:
            for _ in range(managed.MAX_THROTTLED_IN_A_ROW):
                with self.assertRaises(RateLimited):
                    Client('qodo', budget=budget).read('codebase', 'search-repos')
            with self.assertRaises(BudgetExceeded):
                Client('qodo', budget=budget).read('codebase', 'search-repos')   # throttled read after read: the rest is marked unavailable
        self.assertLessEqual(sum(c.args[0] for c in slept.call_args_list), managed.RATE_LIMIT_TOTAL_WAIT)   # waiting is capped per operation
        self.assertTrue(budget.summary()['exhausted'])

    def test_reset_time_comes_from_the_service_and_is_never_negative(self):
        now = time.time()
        self.assertEqual(managed.reset_wait({'retry_after': -5}), 0.0)   # a stale reset: try again now, never a crash
        self.assertAlmostEqual(managed.reset_wait({'reset_at': now + 30}), 30, delta=1)   # epoch seconds
        self.assertAlmostEqual(managed.reset_wait({'reset_at': (now + 30) * 1000}), 30, delta=1)   # epoch milliseconds
        from datetime import datetime, timezone
        iso = datetime.fromtimestamp(now + 45, timezone.utc).isoformat().replace('+00:00', 'Z')
        self.assertAlmostEqual(managed.reset_wait({'reset_at': iso}), 45, delta=1)
        self.assertIsNone(managed.reset_wait({'reset_at': 'soon'}))
        stale = SimpleNamespace(stdout=json.dumps({'error': {'code': 'MT-RATE-LIMITED', 'metadata': {'retry_after': -3}}}), stderr='', returncode=1)
        ok = SimpleNamespace(stdout=json.dumps({'repos': []}), stderr='', returncode=0)
        with mock.patch('subprocess.run', side_effect=[stale, ok]), mock.patch('time.sleep') as slept:
            Client('qodo', budget=ReadBudget()).read('codebase', 'search-repos')
        self.assertEqual(slept.call_args.args[0], 1.0)
        none = SimpleNamespace(stdout=json.dumps({'error': {'code': 'MT-RATE-LIMITED'}}), stderr='', returncode=1)
        with mock.patch('subprocess.run', side_effect=[none, ok]), mock.patch('time.sleep') as slept:
            Client('qodo', budget=ReadBudget()).read('codebase', 'search-repos')
        self.assertEqual(slept.call_args.args[0], managed.RATE_LIMIT_BACKOFF[0])   # no reset given: long enough to clear a one-minute window

    def test_a_callers_own_budget_holds_inside_an_operation(self):
        ok = SimpleNamespace(stdout=json.dumps({'repos': []}), stderr='', returncode=0)
        with read_operation() as op, mock.patch('subprocess.run', return_value=ok) as run:
            own = ReadBudget(max_calls=1, seconds=5)
            Client('qodo', budget=own).read('codebase', 'search-repos')
            self.assertLessEqual(run.call_args.kwargs['timeout'], 5)   # the system map's deadline, not the full 120 s
            with self.assertRaises(BudgetExceeded):
                Client('qodo', budget=own).read('codebase', 'search-repos')   # and its call cap
            self.assertEqual(op.calls, 2)   # both attempts still count toward the operation

    def test_the_fallback_link_is_fresh_and_always_available(self):
        from cockpit import util
        server = (util.ROOT / 'cockpit/server.py').read_text()
        self.assertIn("if not want_link and open_browser_briefly(link()):", server)
        self.assertIn("return self._json({'opened': False, 'url': link()})", server)   # a new invite, not the one handed to the launcher
        js = (util.ROOT / 'app/styles/evidence.js').read_text()
        self.assertIn("data-access-fallback", js); self.assertIn("JSON.stringify({ link: true })", js)   # Didn't open? Get a link

    def test_parallel_notes_collections_keep_their_own_deadlines(self):
        import threading
        from cockpit import notes
        seen = {}
        def run(name, secs):
            token = notes._END.set(secs)
            threading.Event().wait(0.05)
            seen[name] = notes._END.get()
            notes._END.reset(token)
        a = threading.Thread(target=run, args=('a', 1.0)); b = threading.Thread(target=run, args=('b', 2.0))
        a.start(); b.start(); a.join(); b.join()
        self.assertEqual(seen, {'a': 1.0, 'b': 2.0}); self.assertIsNone(notes._END.get())

    def test_opening_the_browser_never_holds_the_reply(self):
        from cockpit import server
        with mock.patch('webbrowser.open', side_effect=lambda url: time.sleep(2) or True):
            start = time.monotonic()
            self.assertFalse(server.open_browser_briefly('http://127.0.0.1:1/_access#key=k', wait=0.2))   # too slow: the page gets the link instead
            self.assertLess(time.monotonic() - start, 1)
        with mock.patch('webbrowser.open', return_value=True):
            self.assertTrue(server.open_browser_briefly('http://127.0.0.1:1/_access#key=k', wait=1))

if __name__ == '__main__':
    unittest.main()
