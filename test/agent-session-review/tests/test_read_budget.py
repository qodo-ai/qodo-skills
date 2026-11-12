import unittest

from cockpit.adapters import managed
from cockpit.adapters.managed import BudgetExceeded, ReadBudget


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


if __name__ == '__main__':
    unittest.main()
