# SPDX-FileCopyrightText: © 2026 arcsinhx
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests for diskusage module."""
# pylint: disable=missing-function-docstring,missing-class-docstring
import unittest
from unittest.mock import patch
import diskusage


class LocalSpaceSavings(unittest.TestCase):
    def setUp(self):
        self.cfg = type('StubCfg', (), {
            'snapshotsMode': lambda self, profile_id=None: 'local',
        })()
        self.backups = [
            ('20260101-010000-001', '/tmp/snap1'),
            ('20260102-010000-002', '/tmp/snap2'),
        ]

    @patch('diskusage._du_local_total')
    def test_savings_basic(self, mock_du):
        """Two snapshots with shared hard links.

        Each has 100 individually, together 50.  Logical=200, physical=50.
        """
        mock_du.side_effect = [100, 100, 50]
        _logical, _physical, saved, percent = diskusage.compute_space_savings(
            self.cfg, self.backups
        )
        self.assertEqual(percent, 75.0)
        self.assertEqual(saved, 150)

    @patch('diskusage._du_local_total')
    def test_savings_no_sharing(self, mock_du):
        """No hard-link sharing between snapshots — 0 % saved."""
        mock_du.side_effect = [100, 100, 200]
        _logical, _physical, saved, percent = diskusage.compute_space_savings(
            self.cfg, self.backups)
        self.assertEqual(percent, 0.0)
        self.assertEqual(saved, 0)

    @patch('diskusage._du_local_total')
    def test_savings_error(self, mock_du):
        """du returns an error → graceful fallback."""
        mock_du.return_value = -1
        logical, physical, saved, percent = \
            diskusage.compute_space_savings(self.cfg, self.backups)
        self.assertEqual(
            (logical, physical, saved, percent),
            (-1, -1, -1, 0.0)
        )

    @patch('diskusage._du_local_total')
    def test_savings_zero_logical(self, mock_du):
        """All backups are empty."""
        mock_du.return_value = 0
        logical, physical, saved, percent = \
            diskusage.compute_space_savings(self.cfg, self.backups)
        self.assertEqual(
            (logical, physical, saved, percent),
            (0, 0, 0, 0.0)
        )


class SSHComputeSpaceSavings(unittest.TestCase):
    def setUp(self):
        self.cfg = type('StubCfg', (), {
            'snapshotsMode': lambda s, profile_id=None: 'ssh',
            'sshCommand': lambda s, cmd=None, nice=False, ionice=False: (
                ['ssh', 'localhost'] + (cmd or [])
            ),
        })()
        self.backups = [
            ('20260101-010000-001', '/mnt/remote/snap1'),
            ('20260102-010000-002', '/mnt/remote/snap2'),
        ]

    @patch('diskusage._du_remote_total')
    def test_savings_calculation(self, mock_du):
        """SSH savings percentage: 2 backups, 100 each, 50 together.

        Logical = 200, physical = 50 → 75 % saved.
        """
        mock_du.side_effect = [100, 100, 50]
        _logical, _physical, saved, percent = diskusage.compute_space_savings(
            self.cfg, self.backups
        )
        self.assertEqual(percent, 75.0)
        self.assertEqual(saved, 150)
