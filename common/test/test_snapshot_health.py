# SPDX-FileCopyrightText: © 2026 Back In Time Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for rsync outcome classification and snapshot health states (issue #1587)."""
import os
import sys
import unittest
import tempfile
import json
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import tools
import snapshots


class TestClassifyRsyncOutcome(unittest.TestCase):
    def test_classify_success(self):
        outcome = tools.classify_rsync_outcome(exit_code=0, error_lines=[])
        self.assertEqual(outcome, tools.HEALTH_OK)

    def test_classify_exit_24_vanished_file(self):
        errors = ['file has vanished: /tmp/scratch.swp', 'some files vanished before they could be transferred']
        outcome = tools.classify_rsync_outcome(exit_code=24, error_lines=errors)
        self.assertEqual(outcome, tools.HEALTH_WARNING)

    def test_classify_exit_23_dead_symlink(self):
        errors = ['rsync: readlink_stat("/path/broken_symlink") failed: No such file or directory (2)']
        outcome = tools.classify_rsync_outcome(exit_code=23, error_lines=errors)
        self.assertEqual(outcome, tools.HEALTH_WARNING)

    def test_classify_exit_23_chown_warning(self):
        errors = ['rsync: chown "/dst/file" failed: Operation not permitted (1)']
        outcome = tools.classify_rsync_outcome(exit_code=23, error_lines=errors)
        self.assertEqual(outcome, tools.HEALTH_WARNING)

    def test_classify_fatal_io_error_fails(self):
        errors = ['rsync: write failed on "/backup/bigfile": No space left on device (28)']
        outcome = tools.classify_rsync_outcome(exit_code=11, error_lines=errors)
        self.assertEqual(outcome, tools.HEALTH_FAILED)

    def test_classify_continue_on_errors_overrides_to_warning(self):
        errors = ['rsync: generic non-benign failure on some file']
        outcome = tools.classify_rsync_outcome(exit_code=23, error_lines=errors, continue_on_errors=True)
        self.assertEqual(outcome, tools.HEALTH_WARNING)


class TestSIDHealthProperties(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.tmp_dir.name)
        self.snapshot_dir = self.base_path / '20260601-120000'
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        class MockConfig:
            def hostUserProfile(self, profile):
                return ('host', 'user', '1')
            def currentProfile(self):
                return '1'

        self.cfg = MockConfig()
        # Instantiate SID
        self.sid = snapshots.SID('20260601-120000', self.cfg, self.base_path)
        # Point sid._path to our temp snapshot directory
        self.sid._path = str(self.snapshot_dir)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_sid_default_healthy_ok(self):
        self.assertEqual(self.sid.health, tools.HEALTH_OK)
        self.assertTrue(self.sid.is_healthy)
        self.assertFalse(self.sid.failed)
        self.assertFalse(self.sid.warning)

    def test_sid_warning_state(self):
        self.sid.warning = True
        self.assertTrue(self.sid.warning)
        self.assertFalse(self.sid.failed)
        self.assertTrue(self.sid.is_healthy)
        self.assertEqual(self.sid.health, tools.HEALTH_WARNING)
        self.assertTrue((self.snapshot_dir / 'warning').exists())

        # Unset warning
        self.sid.warning = False
        self.assertFalse(self.sid.warning)
        self.assertEqual(self.sid.health, tools.HEALTH_OK)
        self.assertFalse((self.snapshot_dir / 'warning').exists())

    def test_sid_failed_state(self):
        self.sid.failed = True
        self.assertTrue(self.sid.failed)
        self.assertFalse(self.sid.is_healthy)
        self.assertEqual(self.sid.health, tools.HEALTH_FAILED)
        self.assertTrue((self.snapshot_dir / 'failed').exists())

        # Failed takes precedence over warning
        self.sid.warning = True
        self.assertEqual(self.sid.health, tools.HEALTH_FAILED)

    def test_sid_health_from_info_json(self):
        info_json = self.snapshot_dir / 'info.json'
        content = {
            'backup': {
                'date': '20260601-120000',
                'health': 'warning'
            }
        }
        info_json.write_text(json.dumps(content), encoding='utf-8')
        self.assertEqual(self.sid.health, tools.HEALTH_WARNING)
