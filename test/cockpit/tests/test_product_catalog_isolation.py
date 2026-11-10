"""Product Ask catalogs never reuse a standalone or differently configured CLI result."""
import json
import os
import subprocess
import unittest
from unittest import mock

from cockpit import ask, managed_work
from cockpit.adapters.managed import Client, PermissionDenied


class CatalogIsolationTests(unittest.TestCase):
    def test_profile_and_command_changes_do_not_share_catalogs(self):
        def run(argv, **kwargs):
            payload = {'tools': [{'group': 'codebase', 'leaf': argv[0], 'access': 'read'}]}
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload), '')
        legacy = {'legacy tool': {}}
        with mock.patch.object(ask, '_CATALOG', legacy), mock.patch.object(ask, '_PRODUCT_CATALOG', {}), \
                mock.patch('subprocess.run', side_effect=run) as calls, \
                mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT': '1', 'REVIEW_COCKPIT_QODO': 'first-cli'}):
            self.assertEqual(list(ask.catalog()), ['codebase first-cli'])
            with mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT': '0'}):
                self.assertEqual(ask.catalog(), legacy)
            with mock.patch.dict(os.environ, {'REVIEW_COCKPIT_QODO': 'second-cli'}):
                self.assertEqual(list(ask.catalog()), ['codebase second-cli'])
            self.assertEqual(list(ask.catalog()), ['codebase first-cli'])
            self.assertEqual(calls.call_count, 2)

    def test_legacy_cache_cannot_hide_product_auth_denial(self):
        response = subprocess.CompletedProcess([], 1, json.dumps({'error': {'code': 'MT-AUTH-MISSING'}}), '')
        with mock.patch.object(ask, '_CATALOG', {'legacy tool': {}}), \
                mock.patch.object(ask, '_PRODUCT_CATALOG', {}), \
                mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT': '1'}), \
                mock.patch('subprocess.run', return_value=response):
            with self.assertRaises(PermissionDenied):
                ask.catalog()

    def test_github_reviewer_exclusion_uses_case_insensitive_accounts(self):
        identity = {'provider': 'github', 'repo': 'org/repo'}
        data = {'reviewer_login': 'Current', 'prs': [{'identity': identity, 'repo': 'org/repo',
                'number': 1, 'key': 'org/repo#1', 'author': 'Author', 'files': []}]}
        reviews = {'items': [{'user': {'login': name}, 'state': 'APPROVED'}
                             for name in ('author', 'CURRENT', 'Other')], 'complete': True}
        def read(group, tool, **kwargs):
            return {'items': [{'number': 2}]} if tool == 'list-prs' else {'revision': 'observed'}
        with mock.patch.object(Client, 'read', side_effect=read), mock.patch.object(Client, 'pages', return_value=reviews):
            result = managed_work.reviewers(data, {}, 4)
        self.assertEqual([row['login'] for row in result['suggested']], ['Other'])
