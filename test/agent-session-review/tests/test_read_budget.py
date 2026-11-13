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
