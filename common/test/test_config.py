# Back In Time
# Copyright (C) 2016 Taylor Raack
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import stat
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import config


class TestConfig(unittest.TestCase):
    """Regular tests for the `Config` class.

    Doing pre-setups via deriving from classes in `generic` should be avoided
    here.
    """

    def test_instance(self):
        """Singleton behaviour of `Config` class.

        Only one instance of `Config` is allowed. Otherwise Exceptions are
        raised.
        """

        # The whole enviornment especially the unitttest need be setup that
        # way that instances of `Config` used should be destroyed after each
        # test.

        # explicite check
        self.assertIsNone(config.Config._instance)

        # Because of that this should work without an Exception.
        config.Config()

        # again explicite check
        self.assertIsNotNone(config.Config._instance)

        # Now because have an instance this should raise an Exception because
        # only one instance is allowed.
        rex_pattern = r'.*still exists!.*Use.*to access it.*'
        with self.assertRaisesRegex(Exception, rex_pattern):
            config.Config()

        # no exception
        self.assertIsInstance(
            config.Config.instance(),
            config.Config
        )


class TestConfigSnapshots(generic.TestCaseCfg):
    """More high level tests for the `Config` class using pre-setups via
    deriving from classes in `generic` module.

    Development note: It is not clear for me (buhtz) why this is related
     to the `Config` class.
    """

    def test_set_snapshots_path_test_writes(self):
        """
        """
        with TemporaryDirectory() as dirpath:
            self.assertTrue(self.cfg.setSnapshotsPath(dirpath))

    def test_set_snapshots_path_fails_on_ro(self):
        """
        """
        with TemporaryDirectory() as dirpath:
            # set directory to read only
            perms_to_mock = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
            with generic.mockPermissions(dirpath, perms_to_mock):
                self.assertFalse(self.cfg.setSnapshotsPath(dirpath))

    @patch('os.chmod')
    def test_set_snapshots_path_permission_fail(self, mock_chmod):
        """
        """
        mock_chmod.side_effect = PermissionError()
        with TemporaryDirectory() as dirpath:
            self.assertTrue(self.cfg.setSnapshotsPath(dirpath))


class TestSshCommand(generic.SSHTestCase):
    """High level tests for the `Config` class and its SSH related methods.

    Development note: It is obvious that this functionality should be
    separated from the `Config` class.
    """
    def test_full_command(self):
        """
        """
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'])
        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '{}@localhost'.format(self.cfg.user()),
                'echo', 'foo'
            ]
        )

    def test_custom_args(self):
        """
        """
        cmd = self.cfg.sshCommand(
            cmd=['echo', 'foo'],
            custom_args=['-o', 'PreferredAuthentications=publickey']
        )

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '-o', 'PreferredAuthentications=publickey',
                '{}@localhost'.format(self.cfg.user()),
                'echo', 'foo'
            ]
        )

    def test_cipher(self):
        """
        """
        self.cfg.setSshCipher('aes256-cbc')
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '-o', 'Ciphers=aes256-cbc',
                '{}@localhost'.format(self.cfg.user()),
                'echo', 'foo'
            ]
        )

        # disable cipher
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'], cipher=False)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '{}@localhost'.format(self.cfg.user()),
                'echo', 'foo'
            ]
        )

    def test_without_command(self):
        """
        """
        cmd = self.cfg.sshCommand()

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '{}@localhost'.format(self.cfg.user())
            ]
        )

    def test_nice(self):
        """
        """
        self.cfg.setNiceOnRemote(True)
        self.cfg.setIoniceOnRemote(True)

        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '{}@localhost'.format(self.cfg.user()),
                'ionice', '-c2', '-n7',
                'nice', '-n19',
                'echo', 'foo'
            ]
        )

        # without cmd no io-/nice
        cmd = self.cfg.sshCommand()

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '{}@localhost'.format(self.cfg.user())
            ]
        )

    def test_quote(self):
        """
        """
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'], quote=True)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '{}@localhost'.format(self.cfg.user()),
                "'", 'echo', 'foo', "'"
            ]
        )

        # without cmd no quotes
        cmd = self.cfg.sshCommand(quote=True)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '{}@localhost'.format(self.cfg.user())
            ]
        )

    def test_prefix(self):
        """
        """
        self.cfg.setSshPrefix(True, 'echo bar')

        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '{}@localhost'.format(self.cfg.user()),
                'echo', 'bar',
                'echo', 'foo'
            ]
        )

        # disable prefix
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'], prefix=False)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                '-p', '22',
                '{}@localhost'.format(self.cfg.user()),
                'echo', 'foo'
            ]
        )

    def test_disable_args(self):
        """
        """
        cmd = self.cfg.sshCommand(port=False, user_host=False)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE)
            ]
        )
