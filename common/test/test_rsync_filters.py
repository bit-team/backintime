# SPDX-FileCopyrightText: © 2026 Back In Time Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later
"""Unit and integration tests for rsync include/exclude filter sequencing (issue #561)."""
import os
import sys
import unittest
from unittest.mock import MagicMock
import tempfile
import subprocess
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import snapshots
import encode


class DummyConfig:
    def __init__(self):
        self.ENCODE = encode.Bounce()
        self._LOCAL_DATA_FOLDER = '/tmp/bit_data'
        self._MOUNT_ROOT = '/tmp/bit_mount'

    def snapshotsPath(self):
        return '/tmp/bit_snapshots'

    def include(self):
        return [('/home/me', 0)]

    def exclude(self):
        return ['/home/me/Dropbox']


class DummySnapshots:
    def __init__(self):
        self.config = DummyConfig()

    rsyncSuffix = snapshots.Snapshots.rsyncSuffix
    rsyncExclude = snapshots.Snapshots.rsyncExclude
    rsyncInclude = snapshots.Snapshots.rsyncInclude


class TestRsyncFilters(unittest.TestCase):
    def setUp(self):
        self.sn = DummySnapshots()

    def test_rsync_suffix_standard_ordering(self):
        includes = [('/home/me', 0)]
        excludes = ['/home/me/.cache', '*.tmp']
        suffix = self.sn.rsyncSuffix(includeFolders=includes, excludeFolders=excludes)

        # Base directories
        self.assertIn('--chmod=Du+wx', suffix)
        self.assertIn('--include=/home/', suffix)
        self.assertIn('--include=/home/me/', suffix)

        # Excludes should come before top-level include
        idx_exclude_cache = suffix.index('--exclude=/home/me/.cache')
        idx_include_me = suffix.index('--include=/home/me/**')
        self.assertLess(idx_exclude_cache, idx_include_me)

        # Catch-all
        self.assertEqual(suffix[-2], '--exclude=*')
        self.assertEqual(suffix[-1], '/')

    def test_rsync_suffix_include_file_inside_excluded_dir_order(self):
        """Verify issue #561: including keep.txt inside excluded Dropbox folder."""
        includes = [
            ('/home/me', 0),
            ('/home/me/Dropbox/keep.txt', 1)
        ]
        excludes = ['/home/me/Dropbox', '*.tmp']
        suffix = self.sn.rsyncSuffix(includeFolders=includes, excludeFolders=excludes)

        # 1. Ancestor chain includes Dropbox directory so rsync can enter it
        self.assertIn('--include=/home/me/Dropbox/', suffix)

        # 2. Specific file include comes BEFORE Dropbox re-exclude
        idx_include_keep = suffix.index('--include=/home/me/Dropbox/keep.txt')
        idx_exclude_dropbox_tree = suffix.index('--exclude=/home/me/Dropbox/**')
        idx_exclude_dropbox_dir = suffix.index('--exclude=/home/me/Dropbox')
        self.assertLess(idx_include_keep, idx_exclude_dropbox_tree)
        self.assertLess(idx_include_keep, idx_exclude_dropbox_dir)

        # 3. Dropbox re-exclude comes BEFORE general /home/me/** include
        idx_include_me = suffix.index('--include=/home/me/**')
        self.assertLess(idx_exclude_dropbox_tree, idx_include_me)

    def test_rsync_suffix_include_folder_inside_excluded_dir_order(self):
        """Verify issue #561: including KeepFolder inside excluded Dropbox folder."""
        includes = [
            ('/home/me', 0),
            ('/home/me/Dropbox/KeepFolder', 0)
        ]
        excludes = ['/home/me/Dropbox']
        suffix = self.sn.rsyncSuffix(includeFolders=includes, excludeFolders=excludes)

        idx_include_sub = suffix.index('--include=/home/me/Dropbox/KeepFolder/**')
        idx_exclude_dropbox = suffix.index('--exclude=/home/me/Dropbox/**')
        idx_include_me = suffix.index('--include=/home/me/**')

        self.assertLess(idx_include_sub, idx_exclude_dropbox)
        self.assertLess(idx_exclude_dropbox, idx_include_me)

    def test_rsync_suffix_nested_overrides(self):
        """Verify multiple nested levels: Dropbox -> Keep -> Secret (excluded) -> special.txt (included)."""
        includes = [
            ('/home/me', 0),
            ('/home/me/Dropbox/Keep', 0),
            ('/home/me/Dropbox/Keep/Secret/special.txt', 1)
        ]
        excludes = [
            ('/home/me/Dropbox'),
            ('/home/me/Dropbox/Keep/Secret')
        ]
        suffix = self.sn.rsyncSuffix(includeFolders=includes, excludeFolders=excludes)

        idx_special = suffix.index('--include=/home/me/Dropbox/Keep/Secret/special.txt')
        idx_exc_secret = suffix.index('--exclude=/home/me/Dropbox/Keep/Secret/**')
        idx_keep = suffix.index('--include=/home/me/Dropbox/Keep/**')
        idx_exc_dropbox = suffix.index('--exclude=/home/me/Dropbox/**')

        self.assertLess(idx_special, idx_exc_secret)
        self.assertLess(idx_exc_secret, idx_keep)
        self.assertLess(idx_keep, idx_exc_dropbox)


@unittest.skipIf(os.name == 'nt', 'Rsync integration test requires POSIX environment')
class TestRsyncFiltersIntegration(unittest.TestCase):
    def setUp(self):
        self.sn = DummySnapshots()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.src_dir = Path(self.tmp_dir.name) / 'src'
        self.dst_dir = Path(self.tmp_dir.name) / 'dst'
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.dst_dir.mkdir(parents=True, exist_ok=True)

        # Create source tree
        dropbox = self.src_dir / 'home' / 'me' / 'Dropbox'
        dropbox.mkdir(parents=True, exist_ok=True)
        (self.src_dir / 'home' / 'me' / 'normal.txt').write_text('normal')
        (self.src_dir / 'home' / 'me' / 'normal.tmp').write_text('tmp')
        (dropbox / 'keep.txt').write_text('keep')
        (dropbox / 'ignored.txt').write_text('ignored')

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_rsync_execution_issue_561(self):
        """Execute rsync with filter sequence and verify only keep.txt is captured from Dropbox."""
        includes = [
            ('/home/me', 0),
            ('/home/me/Dropbox/keep.txt', 1)
        ]
        excludes = [
            '/home/me/Dropbox',
            '*.tmp'
        ]

        suffix = self.sn.rsyncSuffix(includeFolders=includes, excludeFolders=excludes)

        cmd = ['rsync', '-a', '--delete', '--delete-excluded']
        # Filter options from suffix (exclude chmod and chroot)
        filter_opts = [opt for opt in suffix if opt.startswith('--include=') or opt.startswith('--exclude=')]
        cmd.extend(filter_opts)
        cmd.extend([f'{self.src_dir}/', f'{self.dst_dir}/'])

        res = subprocess.run(cmd, capture_output=True, text=True, check=True)

        dst_keep = self.dst_dir / 'home' / 'me' / 'Dropbox' / 'keep.txt'
        dst_ignored = self.dst_dir / 'home' / 'me' / 'Dropbox' / 'ignored.txt'
        dst_normal = self.dst_dir / 'home' / 'me' / 'normal.txt'
        dst_tmp = self.dst_dir / 'home' / 'me' / 'normal.tmp'

        self.assertTrue(dst_keep.exists(), 'keep.txt inside Dropbox must be backed up')
        self.assertFalse(dst_ignored.exists(), 'ignored.txt inside Dropbox must be excluded')
        self.assertTrue(dst_normal.exists(), 'normal.txt in /home/me must be backed up')
        self.assertFalse(dst_tmp.exists(), '*.tmp file must be excluded')

    def test_rsync_execution_delete_excluded(self):
        """Verify that previously synced excluded files are pruned when --delete-excluded is used."""
        # Pre-populate destination with an excluded file and an included file
        dst_dropbox = self.dst_dir / 'home' / 'me' / 'Dropbox'
        dst_dropbox.mkdir(parents=True, exist_ok=True)
        old_file = dst_dropbox / 'old_excluded.txt'
        old_file.write_text('old')

        includes = [
            ('/home/me', 0),
            ('/home/me/Dropbox/keep.txt', 1)
        ]
        excludes = [
            '/home/me/Dropbox'
        ]

        suffix = self.sn.rsyncSuffix(includeFolders=includes, excludeFolders=excludes)

        cmd = ['rsync', '-a', '--delete', '--delete-excluded']
        filter_opts = [opt for opt in suffix if opt.startswith('--include=') or opt.startswith('--exclude=')]
        cmd.extend(filter_opts)
        cmd.extend([f'{self.src_dir}/', f'{self.dst_dir}/'])

        subprocess.run(cmd, capture_output=True, text=True, check=True)

        dst_keep = dst_dropbox / 'keep.txt'
        self.assertTrue(dst_keep.exists(), 'keep.txt must be preserved/transferred')
        self.assertFalse(old_file.exists(), 'old_excluded.txt must be deleted by --delete-excluded')
