"""Fixture-only Qodo process for installed-package contract tests; no network or credentials."""
import json
import os
from pathlib import Path
import sys

argv = sys.argv[1:]
with open(os.environ['PROBE_LOG'], 'a', encoding='utf-8') as log:
    log.write(json.dumps(argv) + '\n')
if '--version' in argv:
    print(os.environ.get('CLI_VERSION', '2.1.1'))
    sys.exit(0)
if 'whoami' in argv:
    print(os.environ.get('AUTH_PAYLOAD', '{}'))
    sys.exit(int(os.environ.get('AUTH_EXIT', '0')))
if argv[:2] == ['read', 'tools']:
    print(os.environ.get('CATALOG_PAYLOAD', '{}'))
    sys.exit(0)
if not os.environ.get('STUB_MANAGED'):
    print('{}')
    sys.exit(0)

args = {}
if '--args-file' in argv:
    args = json.loads(Path(argv[argv.index('--args-file') + 1]).read_text(encoding='utf-8'))
else:
    for index, flag in enumerate(argv):
        if flag.startswith('--') and index + 1 < len(argv) and not argv[index + 1].startswith('--'):
            args[flag[2:].replace('-', '_')] = argv[index + 1]
    # Match the real CLI boolean-flag contract rather than accepting the original transport bug.
    if '--extended' in argv and argv.index('--extended') + 1 < len(argv) and argv[argv.index('--extended') + 1] == 'true':
        print(json.dumps({'error': {'code': 'bad_boolean_flag'}}))
        sys.exit(1)

head, revision = 'b' * 40, 'a' * 64
identity = {'repo': 'demo/repo', 'provider': 'github', 'provider_host': 'github.com',
            'repository_url': 'https://github.com/demo/repo'}
kind, tool = args.get('kind'), argv[2] if len(argv) > 2 else ''
if tool == 'search-repos':
    answer = {'repos': [{'full_name': 'demo/repo', 'provider': 'github',
                         'html_url': identity['repository_url'], 'host': 'github.com'}], 'truncated': False}
elif tool == 'get-read-capabilities':
    answer = {'repository': identity, 'review_reads': {k: True for k in (
        'files', 'patch', 'comments', 'inline_comments', 'reviews', 'threads', 'checks', 'statuses',
        'annotations', 'readiness', 'history')}}
elif tool == 'get-change-context':
    answer = {'revision': revision, 'head_sha': head, 'base_sha': 'c' * 40,
              'change': {'title': 'A fixture change', 'url': 'https://github.com/demo/repo/pull/1',
                         'author': 'fixture-author', 'source_branch': 'feature', 'target_branch': 'main'}}
elif tool == 'read-review-data':
    rows = []
    if kind == 'files':
        rows = [{'filename': 'src/demo.py', 'additions': 1, 'deletions': 1, 'patch_available': True}]
    elif kind == 'patch':
        rows = [{'path': 'src/demo.py', 'patch': '@@ -1 +1 @@\n-before\n+after\n', 'patch_complete': True}]
    answer = {'revision': revision, 'items': rows, 'complete': True, 'next_cursor': None}
elif tool == 'list-prs':
    answer = {'pull_requests': []}
elif tool == 'findings':
    answer = {'review_session': {'id': 'fixture-review', 'status': 'completed', 'commit_sha': head,
                                 'review_complete': True}, 'findings': [], 'coverage': {'complete': True}}
elif tool == 'for-pr':
    answer = {'status': 'no_pr_notes', 'pr': None, 'track': None}
elif tool == 'read-file':
    answer = {'content': 'after\n', 'resolved_ref': head}
else:
    print(json.dumps({'error': {'code': 'fixture_unexpected_tool'}}))
    sys.exit(1)
print(json.dumps(answer))
