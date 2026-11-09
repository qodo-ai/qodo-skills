# Maintained Cockpit behavior tests

These tests exercise `skills/qodo-review-cockpit/runtime` directly. They need Python
3.9+ and Node.js, with Python standard-library dependencies only. They do not need
an upstream checkout, historical Git objects, credentials, or a provider connection.
The tests retain the component's original terms in [LICENSE](LICENSE).

From the qodo-skills repository, run:

```sh
node scripts/test-cockpit-runtime.mjs
node scripts/test-cockpit-runtime.mjs --list
node scripts/test-cockpit-runtime.mjs --offline --report /tmp/cockpit-results.json
```

The default command discovers and runs all 337 behavior tests. The runner uses
`python -X utf8 -B`, an explicit runtime/test PYTHONPATH, the maintained runtime as
cwd, and temporary HOME, TMPDIR and REVIEW_COCKPIT_HOME. Product mode defaults to
zero for raw-library comparison cases; packaged CLI commands always select product mode.
Product tests also select their explicit profile. No installed application is changed.
Provider subprocesses resolve to unavailable test fixtures; test-process auditing
rejects real provider clients and external network addresses. Full execution allows
loopback HTTP servers and temporary Git repositories used by behavior tests.

`--offline` is an explicitly accounted restricted-worker subset: 318 tests. It
excludes seventeen socket cases and two real Git fixture cases, listed individually in
`run_suite.py` and in every offline report. These are not unittest skips or passes.
The parent must run the default command to qualify all behavior. `--list` performs
full discovery without executing tests. `--python PATH` selects the interpreter.

## Fixtures and migration

All 16 original behavior modules and the tests package marker are retained; the maintained
quality-contract module adds eleven regression tests. The findings and access/activity
modules add fourteen regressions, including concurrent browser requests and cross-process
settings/Trash coordination. Seven final-review regressions cover scanner-secret redaction,
bounded requests, PR-scoped verdicts, shared memory writes, session paths and CLI recovery.
Six V1 boundary tests cover critical severity, stable authored findings, atomic local imports,
provider/migration guards, opaque portal links and cross-process memory credit.
Two handoff regressions cover request-to-refresh-worker activity and distillation versus direct memory edits.
Seven hosted-review regressions cover local-coordinate proof, post-merge closure reasons, reviewer snapshot exclusion, ID-less bucket objects, duplicate knowledge, closed-comment severity and unknown impact risk.
The original impact assertion now expects Unknown for invalid risk, rather than inventing Medium.
The six source
fixture assets are copied unchanged. Paths to Qodo comment/product test fixtures
are relative to this suite; runtime demo fixtures remain under the runtime tree.
Module imports such as `tests.test_product` retain one consistent identity.

Four historical `git show` dependencies became local regression baselines:

- `package-shell.json` fixes SHA256 hashes of the expanded template's surrounding
  shell; the behavior test also bounds each maintained template resource.
- `standalone-quality.json` records the standalone quality rendering, checked
  during migration against the preserved original template rendering.
- `standalone-checks.js` contains only the original standalone checks renderer;
  tests execute it and compare the current standalone renderer on the same input.
- `standalone-approval.json` records standalone/product comment-only decisions;
  tests still execute the maintained approval implementation in both modes.

These fixtures are regression expectations, not an import or update mechanism.
The test suite and runtime are now maintained together in this repository.

## Retired standalone release-builder tests

The old `ReleaseTests` class contained 14 tests exclusively for the retired
`release/build.py` pipeline. It is not copied, silently skipped, or counted in the
original 290 behavior tests. Distribution checks belong to the qodo-skills Node component
validator and packaging tests. Migration responsibilities are:

| Retired test methods | Replacement responsibility |
| --- | --- |
| `test_globs`, `test_internal_markers`, `test_worktree_builds_take_no_ref`, `test_a_git_build_uses_its_own_commits_rules` | Retired builder implementation semantics; no equivalent builder exists. Maintained resource selection and validation replace its input pipeline. |
| `test_scan_and_reasoned_exceptions`, `test_case_and_bare_paths_are_caught`, `test_an_exception_covers_only_the_hit_it_spans`, `test_demo_session_ids_are_allowed_by_name` | Maintained component privacy scanning, narrow exceptions and public fixture checks. |
| `test_contributors_never_ship`, `test_contributors_come_from_the_release_commit` | Resource privacy/exclusion validation; no generated upstream contributors file. |
| `test_never_wins_and_binaries_need_a_review`, `test_documents_need_a_review_even_when_they_decode_as_text` | Resource bounds/type validation and exact reviewed binary policy. |
| `test_this_checkout_ships_clean`, `test_package_is_reproducible_and_runs_alone` | Component integrity and generated-host/install/resource tests, plus retained read-only installed demo/export behavior test. |

The parent owns replacement component-validator and packaging checks, their full
execution, and final review. This migration alone does not establish those gates.
