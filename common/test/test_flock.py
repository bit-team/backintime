# SPDX-FileCopyrightText: © 2026 Back In Time Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for GlobalFlock and _FlockContext."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import flock


class TestFlock(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.runtime_dir = Path(self.tmp_dir.name) / 'runtime'
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_flock_disabled(self):
        with flock.GlobalFlock(disable=True) as lock:
            self.assertIsNone(lock)

    def test_flock_acquires_and_releases(self):
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.runtime_dir)}):
            lock_ctx = flock.GlobalFlock(multi_user=False)
            self.assertEqual(lock_ctx._file_path, self.runtime_dir / 'backintime.lock')
            with lock_ctx:
                self.assertTrue(lock_ctx._file_path.exists())
                self.assertIsNotNone(lock_ctx._flock_handle)
            self.assertIsNone(lock_ctx._flock_handle)

    def test_flock_timeout_when_held(self):
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.runtime_dir)}):
            lock1 = flock.GlobalFlock(multi_user=False)
            with lock1:
                lock2 = flock.GlobalFlock(multi_user=False, timeout=1)
                with self.assertRaises(TimeoutError):
                    with lock2:
                        pass

    def test_flock_skips_unreadable_file(self):
        with patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.runtime_dir)}):
            # Create an unreadable lock file in runtime dir
            bad_file = self.runtime_dir / 'backintime.lock'
            bad_file.touch()

            # Mock os.access to report that bad_file is not readable
            original_access = os.access

            def mock_access(path, mode):
                if str(path) == str(bad_file):
                    return False
                return original_access(path, mode)

            with patch('os.access', side_effect=mock_access):
                cache_dir = Path(self.tmp_dir.name) / 'cache'
                with patch.dict(os.environ, {'XDG_CACHE_HOME': str(cache_dir)}):
                    lock_ctx = flock.GlobalFlock(multi_user=False)
                    # It should skip the unreadable bad_file and fall back to cache_dir
                    self.assertNotEqual(lock_ctx._file_path, bad_file)
                    self.assertTrue(str(lock_ctx._file_path).startswith(str(cache_dir)))
