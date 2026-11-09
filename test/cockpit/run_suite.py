"""Discover all maintained behavior tests; explicitly account for restricted-worker exclusions."""
import argparse
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
SOCKET_CASES = (
    'tests.test_cockpit.StoryTests.test_media_route_serves_only_session_media',
    'tests.test_cockpit.StyleTests.test_refresh_from_the_page_runs_in_the_background',
    'tests.test_cockpit.StyleTests.test_reveal_opens_only_the_session_folder',
    'tests.test_cockpit.StyleTests.test_manage_work_packages',
    'tests.test_cockpit.StyleTests.test_app_state_shared_by_every_session',
    'tests.test_cockpit.StyleTests.test_server_routes',
    'tests.test_cockpit.RecipeTests.test_served_page_saves_recipes_and_sends_requests',
    'tests.test_product_session_http.ProductSessionHTTPTests.test_multi_session_notes_and_publish_preserve_explicit_server_boundary',
    'tests.test_product_session_http.ProductSessionHTTPTests.test_product_get_origin_guard_precedes_payload_and_resource_routes',
)
GIT_CASES = (
    'tests.test_cockpit.FormatTests.test_memory_gets_its_own_repo_outside_any',
    'tests.test_cockpit.FormatTests.test_memory_commits_in_each_repo_and_never_inits_a_broad_folder',
)


def cases(suite):
    for entry in suite:
        if isinstance(entry, unittest.TestSuite):
            yield from cases(entry)
        else:
            yield entry


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocked = []

    def addError(self, test, err):
        message = str(err[1])
        if isinstance(err[1], PermissionError) or 'Cockpit suite ' in message:
            self.blocked.append({'id': test.id(), 'reason': message})
        super().addError(test, err)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Account for known denied socket/Git cases without attempting them')
    parser.add_argument('--list', action='store_true')
    args = parser.parse_args()
    discovered = list(cases(unittest.defaultTestLoader.discover(str(ROOT / 'tests'), top_level_dir=str(ROOT))))
    ids = [test.id() for test in discovered]
    if len(ids) != len(set(ids)):
        raise RuntimeError('Duplicate maintained test identities')
    excluded = []
    restricted = set(SOCKET_CASES + GIT_CASES) if args.offline else set()
    if args.offline:
        missing = restricted - set(ids)
        if missing:
            raise RuntimeError('Offline accounting references missing tests: ' + ', '.join(sorted(missing)))
        excluded = [{'id': test.id(), 'reason': 'prior denied socket path' if test.id() in SOCKET_CASES
                     else 'parent-owned real Git fixture path'} for test in discovered if test.id() in restricted]
    selected = [test for test in discovered if test.id() not in restricted]
    report = {'discovered': len(discovered), 'selected': len(selected), 'excluded': excluded,
              'mode': 'offline' if args.offline else 'full', 'ids': ids}
    for item in excluded:
        print('NOT RUN (parent full suite): ' + item['id'] + ' — ' + item['reason'], flush=True)
    if not args.list:
        result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(unittest.TestSuite(selected))
        report.update(testsRun=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                      skipped=len(result.skipped), blocked=result.blocked, successful=result.wasSuccessful())
    else:
        print(json.dumps(report, indent=2))
    Path(os.environ['COCKPIT_TEST_SUMMARY']).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if args.list or report['successful'] else 1


if __name__ == '__main__':
    sys.exit(main())
