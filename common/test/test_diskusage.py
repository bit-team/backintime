# SPDX-FileCopyrightText: © 2026 arcsinhx
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests for diskusage module."""
import unittest
from unittest.mock import patch
import subprocess
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import diskusage


class FormatSizeHuman(unittest.TestCase):
    """Tests for format_size_human()."""

    def test_zero(self):
        self.assertEqual(diskusage.format_size_human(0), '0 Byte')

    def test_bytes(self):
        # 512 < 1024, stays as Byte
        self.assertEqual(diskusage.format_size_human(512), '512 Byte')

    def test_kib(self):
        self.assertEqual(diskusage.format_size_human(2048), '2.0 KiB')

    def test_mib(self):
        self.assertEqual(
            diskusage.format_size_human(1024 * 1024), '1.0 MiB')

    def test_gib(self):
        gib = 1024 * 1024 * 1024
        self.assertEqual(diskusage.format_size_human(gib), '1.0 GiB')


class LocalDiskUsage(unittest.TestCase):
    """Local backup disk usage: from low-level du to space savings."""

    def setUp(self):
        self.cfg = type('StubCfg', (), {
            'snapshotsMode': lambda self, profile_id=None: 'local',
        })()
        self.backups = [
            ('20260101-010000-001', '/tmp/snap1'),
            ('20260102-010000-002', '/tmp/snap2'),
        ]

    # --- _du_local_total ---

    @patch('diskusage.subprocess.run')
    def test_du_normal(self, mock_run):
        """Parse du output and extract grand total."""
        mock_run.return_value.stdout = '10\t/path\n20\t/path2\n30\ttotal\n'
        self.assertEqual(diskusage._du_local_total(['/a', '/b']), 30)

    @patch('diskusage.subprocess.run')
    def test_du_called_process_error(self, mock_run):
        """du fails → return -1 instead of raising."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'du', stderr='error')
        self.assertEqual(diskusage._du_local_total(['/a']), -1)

    @patch('diskusage.subprocess.run')
    def test_du_bad_output(self, mock_run):
        """du output is not parseable → return -1."""
        mock_run.return_value.stdout = 'not a number\n'
        self.assertEqual(diskusage._du_local_total(['/a']), -1)

    @patch('diskusage.subprocess.run')
    def test_du_empty_paths(self, mock_run):
        """Empty path list → 0 without calling du."""
        self.assertEqual(diskusage._du_local_total([]), 0)
        mock_run.assert_not_called()

    # --- compute_space_savings ---

    @patch('diskusage._du_local_total')
    def test_savings_basic(self, mock_du):
        """Two snapshots with shared hard links.

        Each has 100 individually, together 50.  Logical=200, physical=50.
        """
        mock_du.side_effect = [100, 100, 50]
        _, _, saved, percent = diskusage.compute_space_savings(
            self.cfg, self.backups)
        self.assertEqual(percent, 75.0)
        self.assertEqual(saved, 150)

    @patch('diskusage._du_local_total')
    def test_savings_no_sharing(self, mock_du):
        """No hard-link sharing between snapshots — 0 % saved."""
        mock_du.side_effect = [100, 100, 200]
        _, _, saved, percent = diskusage.compute_space_savings(
            self.cfg, self.backups)
        self.assertEqual(percent, 0.0)
        self.assertEqual(saved, 0)

    @patch('diskusage._du_local_total')
    def test_savings_error(self, mock_du):
        """du returns an error → graceful fallback."""
        mock_du.return_value = -1
        logical, physical, saved, percent = \
            diskusage.compute_space_savings(self.cfg, self.backups)
        self.assertEqual((logical, physical, saved, percent),
                         (-1, -1, -1, 0.0))

    @patch('diskusage._du_local_total')
    def test_savings_zero_logical(self, mock_du):
        """All backups are empty."""
        mock_du.return_value = 0
        logical, physical, saved, percent = \
            diskusage.compute_space_savings(self.cfg, self.backups)
        self.assertEqual((logical, physical, saved, percent),
                         (0, 0, 0, 0.0))


class SSHDiskUsage(unittest.TestCase):
    """SSH backup disk usage: from low-level du to space savings.

    Verifies that mounted_path is passed through to SID() and that the
    savings calculation works identically to the local path.
    """

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

    # --- _du_remote_total ---

    @patch('diskusage.subprocess.run')
    @patch('diskusage.snapshots.SID')
    def test_du_constructs_sid_with_mounted_path(self, mock_sid, mock_run):
        """mounted_path is forwarded to SID constructor for each backup."""
        mock_run.return_value.stdout = '42\ttotal\n'
        diskusage._du_remote_total(self.cfg, self.backups,
                                   mounted_path='/mnt')
        self.assertEqual(mock_sid.call_count, 2)
        mock_sid.assert_any_call(
            '20260101-010000-001', self.cfg, '/mnt')
        mock_sid.assert_any_call(
            '20260102-010000-002', self.cfg, '/mnt')

    @patch('diskusage.subprocess.run')
    @patch('diskusage.snapshots.SID')
    def test_du_called_process_error(self, mock_sid, mock_run):
        """SSH du fails → return -1."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'ssh', stderr='error')
        self.assertEqual(
            diskusage._du_remote_total(self.cfg, self.backups), -1)

    # --- compute_total_usage ---

    @patch('diskusage._du_remote_total')
    @patch('diskusage.snapshots.SID')
    def test_total_usage_routing(self, mock_sid, mock_du):
        """compute_total_usage routes to _du_remote_total in SSH mode."""
        mock_du.return_value = 42
        result = diskusage.compute_total_usage(
            self.cfg, self.backups, mounted_path='/mnt')
        self.assertEqual(result, 42)
        mock_du.assert_called_once()
        self.assertEqual(
            mock_du.call_args.kwargs.get('mounted_path'), '/mnt')

    # --- compute_space_savings ---

    @patch('diskusage._du_remote_total')
    @patch('diskusage.snapshots.SID')
    def test_savings_routing(self, mock_sid, mock_du):
        """SSH mode calls _du_remote_total, not _du_local_total."""
        mock_du.return_value = 100
        with patch('diskusage._du_local_total') as mock_local:
            diskusage.compute_space_savings(
                self.cfg, self.backups, mounted_path='/mnt')
            mock_local.assert_not_called()
        mock_du.assert_called()

    @patch('diskusage._du_remote_total')
    @patch('diskusage.snapshots.SID')
    def test_savings_mounted_path(self, mock_sid, mock_du):
        """mounted_path forwarded to every _du_remote_total call."""
        mock_du.return_value = 100
        diskusage.compute_space_savings(
            self.cfg, self.backups, mounted_path='/mnt')
        for call in mock_du.call_args_list:
            self.assertEqual(call.kwargs.get('mounted_path'), '/mnt')

    @patch('diskusage._du_remote_total')
    @patch('diskusage.snapshots.SID')
    def test_savings_calculation(self, mock_sid, mock_du):
        """SSH savings percentage: 2 backups, 100 each, 50 together.

        Logical = 200, physical = 50 → 75 % saved.
        """
        mock_du.side_effect = [100, 100, 50]
        _, _, saved, percent = diskusage.compute_space_savings(
            self.cfg, self.backups, mounted_path='/mnt')
        self.assertEqual(percent, 75.0)
        self.assertEqual(saved, 150)
