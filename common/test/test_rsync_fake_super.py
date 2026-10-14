# SPDX-FileCopyrightText: © 2026 Back In Time Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for non-root fake-super ownership handling and hardlink preservation (issues #988, #994, #1437)."""

import builtins
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import subprocess
from io import StringIO

builtins._ = lambda s: s

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import tools
import snapshots
from konfig import Konfig, Profile
from config import Config
from singleton import Singleton


class DummyProfileConfig:
    def __init__(self, mode='auto', snapshots_path='/tmp'):
        self._mode = mode
        self._snapshots_path = snapshots_path

    def ownerGroupMode(self, profile_id=None):
        return self._mode

    def snapshotsPath(self):
        return self._snapshots_path

    def nocacheOnLocal(self):
        return False

    def useChecksum(self):
        return False

    def copyUnsafeLinks(self):
        return False

    def copyLinks(self):
        return False

    def oneFileSystem(self):
        return False

    def preserveAcl(self):
        return False

    def preserveXattr(self):
        return False

    def bwlimitEnabled(self):
        return False

    def rsyncOptionsEnabled(self):
        return False

    def snapshotsMode(self):
        return 'local'


class TestXattrSupportProbe(unittest.TestCase):
    def test_check_xattr_support_live(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # On Linux ext4/tmpfs, xattr support should be detectable
            has_xattr = tools.check_xattr_support(tmpdir)
            self.assertIsInstance(has_xattr, bool)

    def test_check_xattr_support_nonexistent(self):
        self.assertFalse(tools.check_xattr_support('/path/does/not/exist/987654321'))

    @patch('os.setxattr')
    def test_check_xattr_support_os_error(self, mock_setxattr):
        mock_setxattr.side_effect = OSError("Operation not supported")
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertFalse(tools.check_xattr_support(tmpdir))


class TestEffectiveOwnerGroupMode(unittest.TestCase):
    def test_explicit_modes(self):
        cfg = DummyProfileConfig(mode='real')
        self.assertEqual(tools.get_effective_owner_group_mode(cfg), 'real')

        cfg = DummyProfileConfig(mode='off')
        self.assertEqual(tools.get_effective_owner_group_mode(cfg), 'off')

        cfg = DummyProfileConfig(mode='fake-super')
        self.assertEqual(tools.get_effective_owner_group_mode(cfg), 'fake-super')

    @patch('os.geteuid', return_value=0)
    def test_auto_mode_as_root(self, _mock_geteuid):
        cfg = DummyProfileConfig(mode='auto')
        self.assertEqual(tools.get_effective_owner_group_mode(cfg), 'real')

    @patch('os.geteuid', return_value=1000)
    @patch('tools.rsyncCaps', return_value=['xattrs', 'progress2'])
    @patch('tools.check_xattr_support', return_value=True)
    def test_auto_mode_as_nonroot_with_xattr(self, _mock_xattr, _mock_caps, _mock_geteuid):
        cfg = DummyProfileConfig(mode='auto')
        self.assertEqual(tools.get_effective_owner_group_mode(cfg), 'fake-super')

    @patch('os.geteuid', return_value=1000)
    @patch('tools.rsyncCaps', return_value=['xattrs', 'progress2'])
    @patch('tools.check_xattr_support', return_value=False)
    def test_auto_mode_as_nonroot_without_xattr(self, _mock_xattr, _mock_caps, _mock_geteuid):
        cfg = DummyProfileConfig(mode='auto')
        self.assertEqual(tools.get_effective_owner_group_mode(cfg), 'off')

    @patch('os.geteuid', return_value=1000)
    @patch('tools.rsyncCaps', return_value=['progress2'])  # missing xattrs
    def test_auto_mode_rsync_lacks_xattr(self, _mock_caps, _mock_geteuid):
        cfg = DummyProfileConfig(mode='auto')
        self.assertEqual(tools.get_effective_owner_group_mode(cfg), 'off')


class TestRsyncPrefixFakeSuper(unittest.TestCase):
    @patch('tools.get_effective_owner_group_mode', return_value='fake-super')
    def test_rsync_prefix_injects_fake_super(self, _mock_mode):
        cfg = DummyProfileConfig()
        cmd = tools.rsyncPrefix(cfg, no_perms=False)
        self.assertIn('--fake-super', cmd)
        self.assertIn('--numeric-ids', cmd)
        self.assertIn('--perms', cmd)
        self.assertIn('--group', cmd)
        self.assertIn('--owner', cmd)

    @patch('tools.get_effective_owner_group_mode', return_value='real')
    def test_rsync_prefix_real_mode(self, _mock_mode):
        cfg = DummyProfileConfig()
        cmd = tools.rsyncPrefix(cfg, no_perms=False)
        self.assertNotIn('--fake-super', cmd)
        self.assertIn('--perms', cmd)
        self.assertIn('--group', cmd)
        self.assertIn('--owner', cmd)

    def test_rsync_prefix_no_perms_flag(self):
        cfg = DummyProfileConfig()
        cmd = tools.rsyncPrefix(cfg, no_perms=True)
        self.assertNotIn('--fake-super', cmd)
        self.assertIn('--no-perms', cmd)
        self.assertIn('--no-group', cmd)
        self.assertIn('--no-owner', cmd)

    @patch('tools.get_effective_owner_group_mode', return_value='off')
    def test_rsync_prefix_off_mode(self, _mock_mode):
        cfg = DummyProfileConfig()
        cmd = tools.rsyncPrefix(cfg, no_perms=False)
        self.assertNotIn('--fake-super', cmd)
        self.assertIn('--no-perms', cmd)
        self.assertIn('--no-group', cmd)
        self.assertIn('--no-owner', cmd)


class TestRsyncCallbackMetadataWarnings(unittest.TestCase):
    def test_chown_warning_surfaced(self):
        class MockSnapshotLog:
            def __init__(self):
                self.entries = []

            def append(self, msg, level=1):
                self.entries.append((msg, level))

        class MockSnapshots:
            def __init__(self):
                self.messages = []
                self.snapshotLog = MockSnapshotLog()

            def setTakeSnapshotMessage(self, level, msg):
                self.messages.append((level, msg))

            rsyncCallback = snapshots.Snapshots.rsyncCallback

        sn = MockSnapshots()
        params = [False, False, []]
        line = 'rsync: chown "/path/to/file" failed: Operation not permitted (1)'
        sn.rsyncCallback(line, params)

        # Fatal error flag should NOT be prematurely set
        self.assertFalse(params[0])
        # Warning line MUST be captured in error_lines list for classification
        self.assertIn(line, params[2])
        # Snapshot log must record warning
        self.assertTrue(any(line in entry[0] for entry in sn.snapshotLog.entries))


class TestKonfigProfileOwnerGroupMode(unittest.TestCase):
    def setUp(self):
        Singleton.remove_all_instances()

    def test_konfig_default_and_set(self):
        conf = Konfig()
        conf.load(StringIO(''))
        profile = conf.profile(1)
        self.assertEqual(profile.owner_group_mode, 'auto')

        profile.owner_group_mode = 'fake-super'
        self.assertEqual(profile.owner_group_mode, 'fake-super')

        profile.owner_group_mode = 'real'
        self.assertEqual(profile.owner_group_mode, 'real')

        profile.owner_group_mode = 'off'
        self.assertEqual(profile.owner_group_mode, 'off')

        with self.assertRaises(ValueError):
            profile.owner_group_mode = 'invalid_mode'


class TestFakeSuperHardlinkFunctional(unittest.TestCase):
    """Functional test verifying that --fake-super preserves hardlinks across snapshots."""

    def test_fake_super_hardlink_preservation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            if not tools.check_xattr_support(tmpdir):
                self.skipTest(f"Temp directory '{tmpdir}' does not support xattrs")

            src = os.path.join(tmpdir, 'src')
            s1 = os.path.join(tmpdir, 's1')
            s2 = os.path.join(tmpdir, 's2')
            os.makedirs(src)
            os.makedirs(s1)
            os.makedirs(s2)

            # Create read-only file (issue #994)
            f_ro = os.path.join(src, 'readonly.txt')
            with open(f_ro, 'w') as fh:
                fh.write('immutable content')
            os.chmod(f_ro, 0o444)

            # Create directory with 0o555 mode
            sub = os.path.join(src, 'sub')
            os.makedirs(sub)
            f_sub = os.path.join(sub, 'inner.txt')
            with open(f_sub, 'w') as fh:
                fh.write('inner data')
            os.chmod(sub, 0o555)

            # Snapshot 1 with fake-super
            cmd1 = ['rsync', '-a', '--fake-super', '--numeric-ids', src + '/', s1 + '/']
            res1 = subprocess.run(cmd1, capture_output=True, text=True)
            self.assertEqual(res1.returncode, 0, f"rsync s1 failed: {res1.stderr}")

            # Snapshot 2 with fake-super and link-dest
            cmd2 = [
                'rsync', '-a', '--fake-super', '--numeric-ids',
                '--link-dest=' + s1,
                src + '/', s2 + '/'
            ]
            res2 = subprocess.run(cmd2, capture_output=True, text=True)
            self.assertEqual(res2.returncode, 0, f"rsync s2 failed: {res2.stderr}")

            # Verify hardlinks: s1 and s2 files must share the exact same inode!
            s1_ro = os.path.join(s1, 'readonly.txt')
            s2_ro = os.path.join(s2, 'readonly.txt')
            self.assertEqual(os.stat(s1_ro).st_ino, os.stat(s2_ro).st_ino)
            self.assertGreaterEqual(os.stat(s2_ro).st_nlink, 2)

            s1_inner = os.path.join(s1, 'sub', 'inner.txt')
            s2_inner = os.path.join(s2, 'sub', 'inner.txt')
            self.assertEqual(os.stat(s1_inner).st_ino, os.stat(s2_inner).st_ino)
            self.assertGreaterEqual(os.stat(s2_inner).st_nlink, 2)


if __name__ == '__main__':
    unittest.main()
