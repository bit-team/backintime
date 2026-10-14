# SPDX-FileCopyrightText: © 2026 Back In Time Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later
"""Unit tests for SSHSetupValidator diagnostics and pre-flight checks."""
import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sshsetupvalidator
from sshsetupvalidator import SSHSetupValidator, SSHSetupError


class DummyHost:
    def __init__(self):
        self.host = 'remote.example.com'
        self.port = 22
        self.user_host = 'user@remote.example.com'
        self.path = '/home/user/backup'
        self.user_host_path = 'user@remote.example.com:/home/user/backup'
        self.priv_key_file = None
        self.proxy = None


class DummyConfig:
    def __init__(self):
        self._nice = True
        self._ionice = True
        self._nocache = True
        self._smart_remove_bg = False
        self._ssh_check_commands = True

    def niceOnRemote(self):
        return self._nice

    def setNiceOnRemote(self, val):
        self._nice = val

    def ioniceOnRemote(self):
        return self._ionice

    def setIoniceOnRemote(self, val):
        self._ionice = val

    def nocacheOnRemote(self):
        return self._nocache

    def setNocacheOnRemote(self, val):
        self._nocache = val

    def smartRemoveRunRemoteInBackground(self):
        return self._smart_remove_bg

    def sshCheckCommands(self):
        return self._ssh_check_commands


class DummyMountManager:
    def __init__(self):
        self.backend = MagicMock()
        self.backend.host = DummyHost()
        self.cfg = DummyConfig()


class TestSSHSetupValidator(unittest.TestCase):
    def setUp(self):
        self.mnt = DummyMountManager()
        self.validator = SSHSetupValidator(self.mnt)

    def test_check_remote_shell_success(self):
        self.validator._ssh = MagicMock(return_value=(0, 'BIT_OK\n', ''))
        # Should not raise
        self.validator._check_remote_shell()
        self.validator._ssh.assert_called_once_with(['echo', 'BIT_OK'])

    def test_check_remote_shell_restricted_sftp(self):
        self.validator._ssh = MagicMock(return_value=(1, '', 'This service allows sftp connections only.\n'))
        with self.assertRaises(SSHSetupError) as ctx:
            self.validator._check_remote_shell()
        self.assertIn('restricted shell', ctx.exception.gui_msg.lower())
        self.assertIn('sftp', ctx.exception.gui_msg.lower())

    def test_check_remote_shell_rssh(self):
        self.validator._ssh = MagicMock(return_value=(1, '', 'rssh: command not permitted\n'))
        with self.assertRaises(SSHSetupError) as ctx:
            self.validator._check_remote_shell()
        self.assertIn('restricted shell', ctx.exception.gui_msg.lower())

    def test_check_remote_tools_nice_fallback(self):
        def mock_ssh(cmd):
            if cmd == ['bash', '-c', 'true']:
                return (0, '', '')
            if cmd == ['nice', '-n', '19', 'true']:
                return (127, '', 'nice: command not found\n')
            if cmd == ['ionice', '-c2', '-n7', 'true']:
                return (0, '', '')
            if cmd == ['nocache', 'true']:
                return (0, '', '')
            return (0, '', '')

        self.validator._ssh = MagicMock(side_effect=mock_ssh)
        self.assertTrue(self.validator.cfg.niceOnRemote())
        # Should not raise SSHSetupError; instead, niceOnRemote should be automatically disabled
        self.validator._check_remote_tools()
        self.assertFalse(self.validator.cfg.niceOnRemote())
        self.assertTrue(self.validator.cfg.ioniceOnRemote())

    def test_ensure_remote_directory_restricted_shell_error(self):
        self.validator._ssh = MagicMock(return_value=(1, '', 'This service allows sftp connections only.\n'))
        with self.assertRaises(SSHSetupError) as ctx:
            self.validator._ensure_remote_directory()
        self.assertIn('restricted shell', ctx.exception.gui_msg.lower())

    def test_check_direct_hardlinks_success(self):
        self.validator._ssh = MagicMock(return_value=(0, '88888 88888\n', ''))
        self.assertTrue(self.validator._check_direct_hardlinks())

    def test_check_direct_hardlinks_failure(self):
        self.validator._ssh = MagicMock(return_value=(1, '', 'ln: failed to create hard link: Operation not permitted\n'))
        self.assertFalse(self.validator._check_direct_hardlinks())

    def test_check_rsync_hardlinks_direct_failure_raises(self):
        self.validator._check_direct_hardlinks = MagicMock(return_value=False)
        with self.assertRaises(SSHSetupError) as ctx:
            self.validator._check_rsync_hardlinks()
        self.assertIn('does not support hardlinks', ctx.exception.gui_msg.lower())

    @patch('subprocess.Popen')
    def test_check_rsync_hardlinks_direct_success_rsync_diff_warns_not_raises(self, mock_popen):
        self.validator._check_direct_hardlinks = MagicMock(return_value=True)

        # Mock Popen for rsync commands and stat inode commands
        proc_rsync = MagicMock()
        proc_rsync.communicate.return_value = ('', '')
        proc_rsync.returncode = 0

        proc_stat1 = MagicMock()
        proc_stat1.communicate.return_value = ('1001\n', '')
        proc_stat1.returncode = 0

        proc_stat2 = MagicMock()
        proc_stat2.communicate.return_value = ('1002\n', '')
        proc_stat2.returncode = 0

        mock_popen.side_effect = [proc_rsync, proc_rsync, proc_stat1, proc_stat2]

        # Inodes differ (1001 != 1002), but direct hardlinks succeeded:
        # must NOT raise SSHSetupError!
        self.validator._check_rsync_hardlinks()

