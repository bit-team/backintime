# SPDX-FileCopyrightText: © 2026 Back In Time Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for user/group NSS name resolution and caching."""
import unittest
from unittest.mock import patch, MagicMock
import pwd
import grp
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import snapshots


class DummySnapshots:
    """Minimal wrapper exposing only user/group cache and resolution methods."""
    def __init__(self):
        self.userCache = {}
        self.groupCache = {}

    userName = snapshots.Snapshots.userName
    groupName = snapshots.Snapshots.groupName


class TestNSSNames(unittest.TestCase):
    def setUp(self):
        self.sn = DummySnapshots()

    @patch('pwd.getpwuid')
    def test_user_name_success_cached(self, mock_getpwuid):
        mock_entry = MagicMock()
        mock_entry.pw_name = 'alice'
        mock_getpwuid.return_value = mock_entry

        name = self.sn.userName(1001)
        self.assertEqual(name, 'alice')
        self.assertEqual(self.sn.userCache.get(1001), 'alice')
        self.assertEqual(mock_getpwuid.call_count, 1)

        # Second call should use cache directly
        name2 = self.sn.userName(1001)
        self.assertEqual(name2, 'alice')
        self.assertEqual(mock_getpwuid.call_count, 1)

    @patch('pwd.getpwuid')
    def test_user_name_keyerror_cached_as_dash(self, mock_getpwuid):
        mock_getpwuid.side_effect = KeyError('No such user')

        name = self.sn.userName(9999)
        self.assertEqual(name, '-')
        # KeyError is cached as '-' to prevent hammering NSS for missing UIDs across thousands of files
        self.assertEqual(self.sn.userCache.get(9999), '-')
        self.assertEqual(mock_getpwuid.call_count, 1)

        # Subsequent call should use cache directly
        name2 = self.sn.userName(9999)
        self.assertEqual(name2, '-')
        self.assertEqual(mock_getpwuid.call_count, 1)

    @patch('pwd.getpwuid')
    def test_user_name_transient_error_not_cached(self, mock_getpwuid):
        mock_getpwuid.side_effect = OSError('SSSD socket error')

        name = self.sn.userName(8888)
        self.assertEqual(name, '-')
        # Transient OSError must NOT be cached so it can recover
        self.assertNotIn(8888, self.sn.userCache)

    @patch('pwd.getpwuid')
    def test_user_name_transient_failure_then_success(self, mock_getpwuid):
        mock_entry = MagicMock()
        mock_entry.pw_name = 'bob'
        # First call fails with OSError (e.g. SSSD busy), second attempt in same call succeeds
        mock_getpwuid.side_effect = [OSError('SSSD socket timeout'), mock_entry]

        name = self.sn.userName(1002)
        self.assertEqual(name, 'bob')
        self.assertEqual(self.sn.userCache.get(1002), 'bob')
        self.assertEqual(mock_getpwuid.call_count, 2)

    @patch('grp.getgrgid')
    def test_group_name_success_cached(self, mock_getgrgid):
        mock_entry = MagicMock()
        mock_entry.gr_name = 'developers'
        mock_getgrgid.return_value = mock_entry

        name = self.sn.groupName(2001)
        self.assertEqual(name, 'developers')
        self.assertEqual(self.sn.groupCache.get(2001), 'developers')
        self.assertEqual(mock_getgrgid.call_count, 1)

        name2 = self.sn.groupName(2001)
        self.assertEqual(name2, 'developers')
        self.assertEqual(mock_getgrgid.call_count, 1)

    @patch('grp.getgrgid')
    def test_group_name_keyerror_cached_as_dash(self, mock_getgrgid):
        mock_getgrgid.side_effect = KeyError('No such group')

        name = self.sn.groupName(9999)
        self.assertEqual(name, '-')
        # KeyError is cached as '-' to prevent hammering NSS for missing GIDs across thousands of files
        self.assertEqual(self.sn.groupCache.get(9999), '-')
        self.assertEqual(mock_getgrgid.call_count, 1)

        # Subsequent call should use cache directly
        name2 = self.sn.groupName(9999)
        self.assertEqual(name2, '-')
        self.assertEqual(mock_getgrgid.call_count, 1)

    @patch('grp.getgrgid')
    def test_group_name_transient_error_not_cached(self, mock_getgrgid):
        mock_getgrgid.side_effect = OSError('LDAP socket error')

        name = self.sn.groupName(8888)
        self.assertEqual(name, '-')
        # Transient OSError must NOT be cached so it can recover
        self.assertNotIn(8888, self.sn.groupCache)

    @patch('grp.getgrgid')
    def test_group_name_transient_failure_then_success(self, mock_getgrgid):
        mock_entry = MagicMock()
        mock_entry.gr_name = 'staff'
        mock_getgrgid.side_effect = [OSError('LDAP busy'), mock_entry]

        name = self.sn.groupName(2002)
        self.assertEqual(name, 'staff')
        self.assertEqual(self.sn.groupCache.get(2002), 'staff')
        self.assertEqual(mock_getgrgid.call_count, 2)
