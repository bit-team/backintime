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
"""Tests about config module.
"""
import os
import stat
import sys
import getpass
import unittest
from unittest import mock
from test import generic
from tempfile import TemporaryDirectory
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config


class TestConfig(generic.TestCaseCfg):
    def test_set_snapshots_path_test_writes(self):
        with TemporaryDirectory() as dirpath:
            self.assertTrue(self.cfg.setSnapshotsPath(dirpath))

    def test_set_snapshots_path_fails_on_ro(self):
        with TemporaryDirectory() as dirpath:
            # set directory to read only
            with generic.mockPermissions(dirpath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH):
                self.assertFalse(self.cfg.setSnapshotsPath(dirpath))

    @mock.patch('os.chmod')
    def test_set_snapshots_path_permission_fail(self, mock_chmod):
        mock_chmod.side_effect = PermissionError()
        with TemporaryDirectory() as dirpath:
            self.assertTrue(self.cfg.setSnapshotsPath(dirpath))


class TestSshCommand(generic.SSHTestCase):
    @classmethod
    def setUpClass(cls):
        cls._user = getpass.getuser()

    def test_full_command(self):
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])
        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_custom_args(self):
        cmd = self.cfg.sshCommand(
            cmd=['echo', 'foo'],
            custom_args=['-o', 'PreferredAuthentications=publickey'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                '-o', 'PreferredAuthentications=publickey',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_cipher_aes256_cbc(self):
        self.cfg.setSshCipher('aes256-cbc')
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                '-o', 'Ciphers=aes256-cbc',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_cipher_disabled(self):
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'], cipher=False)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_without_command(self):
        cmd = self.cfg.sshCommand()
        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
            ]
        )

    def test_nice_and_ionice(self):
        self.cfg.setNiceOnRemote(True)
        self.cfg.setIoniceOnRemote(True)

        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'ionice', '-c2', '-n7',
                'nice', '-n19',
                'echo', 'foo'
            ]
        )

    def test_nice_and_ionice_without_command(self):
        self.cfg.setNiceOnRemote(True)
        self.cfg.setIoniceOnRemote(True)

        cmd = self.cfg.sshCommand()

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
            ]
        )

    def test_quote(self):
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'], quote=True)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                "'", 'echo', 'foo', "'"
            ]
        )

    def test_quote_without_command(self):
        cmd = self.cfg.sshCommand(quote=True)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
            ]
        )

    def test_prefix(self):
        self.cfg.setSshPrefix(True, 'echo bar')

        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'echo', 'bar',
                'echo', 'foo'
            ]
        )

    def test_prefix_false(self):
        # disable prefix
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'], prefix=False)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_disable_args(self):
        cmd = self.cfg.sshCommand(port=False, user_host=False)
        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
            ]
        )
