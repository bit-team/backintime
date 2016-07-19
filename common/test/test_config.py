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
# You should have received a copy of the GNU General Public Licensealong
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import stat
import sys
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
            os.chmod(dirpath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            self.assertFalse(self.cfg.setSnapshotsPath(dirpath))

class TestSshCommand(generic.SSHTestCase):
    def test_full_command(self):
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.user()),
                                   'echo', 'foo'])

    def test_custom_args(self):
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'],
                                   custom_args = ['-o', 'PreferredAuthentications=publickey'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '-o', 'PreferredAuthentications=publickey',
                                   '{}@localhost'.format(self.cfg.user()),
                                   'echo', 'foo'])

    def test_cipher(self):
        self.cfg.setSshCipher('aes256-cbc')
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '-o', 'Ciphers=aes256-cbc',
                                   '{}@localhost'.format(self.cfg.user()),
                                   'echo', 'foo'])

        # disable cipher
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'], cipher = False)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.user()),
                                   'echo', 'foo'])

    def test_without_command(self):
        cmd = self.cfg.sshCommand()
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.user())])

    def test_nice(self):
        self.cfg.setNiceOnRemote(True)
        self.cfg.setIoniceOnRemote(True)
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.user()),
                                   'ionice', '-c2', '-n7',
                                   'nice', '-n 19',
                                   'echo', 'foo'])

        # without cmd no io-/nice
        cmd = self.cfg.sshCommand()
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.user())])

    def test_quote(self):
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'], quote = True)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.user()),
                                   "'", 'echo', 'foo', "'"])

        # without cmd no quotes
        cmd = self.cfg.sshCommand(quote = True)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.user())])

    def test_prefix(self):
        self.cfg.setSshPrefix(True, 'echo bar')
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.user()),
                                   'echo', 'bar',
                                   'echo', 'foo'])

        # disable prefix
        cmd = self.cfg.sshCommand(cmd = ['echo', 'foo'], prefix = False)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.user()),
                                   'echo', 'foo'])

    def test_disable_args(self):
        cmd = self.cfg.sshCommand(port = False, user_host = False)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE)])
