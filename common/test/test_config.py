# SPDX-FileCopyrightText: © 2016 Taylor Raack
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about config module.
"""
import os
import sys
import getpass
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


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
