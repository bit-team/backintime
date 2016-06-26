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
            self.assertTrue(self.cfg.set_snapshots_path(dirpath))

    def test_set_snapshots_path_fails_on_ro(self):
        with TemporaryDirectory() as dirpath:
            # set directory to read only
            os.chmod(dirpath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            self.assertFalse(self.cfg.set_snapshots_path(dirpath))

class TestSshCommand(generic.SSHTestCase):
    def test_full_command(self):
        cmd = self.cfg.ssh_command(cmd = ['echo', 'foo'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.get_user()),
                                   'echo', 'foo'])

    def test_custom_args(self):
        cmd = self.cfg.ssh_command(cmd = ['echo', 'foo'],
                                   custom_args = ['-o', 'PreferredAuthentications=publickey'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '-o', 'PreferredAuthentications=publickey',
                                   '{}@localhost'.format(self.cfg.get_user()),
                                   'echo', 'foo'])

    def test_cipher(self):
        self.cfg.set_ssh_cipher('aes256-cbc')
        cmd = self.cfg.ssh_command(cmd = ['echo', 'foo'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '-o', 'Ciphers=aes256-cbc',
                                   '{}@localhost'.format(self.cfg.get_user()),
                                   'echo', 'foo'])

        # disable cipher
        cmd = self.cfg.ssh_command(cmd = ['echo', 'foo'], cipher = False)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.get_user()),
                                   'echo', 'foo'])

    def test_without_command(self):
        cmd = self.cfg.ssh_command()
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.get_user())])

    def test_nice(self):
        self.cfg.set_run_nice_on_remote_enabled(True)
        self.cfg.set_run_ionice_on_remote_enabled(True)
        cmd = self.cfg.ssh_command(cmd = ['echo', 'foo'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.get_user()),
                                   'ionice', '-c2', '-n7',
                                   'nice', '-n 19',
                                   'echo', 'foo'])

        # without cmd no io-/nice
        cmd = self.cfg.ssh_command()
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.get_user())])

    def test_quote(self):
        cmd = self.cfg.ssh_command(cmd = ['echo', 'foo'], quote = True)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.get_user()),
                                   "'", 'echo', 'foo', "'"])

        # without cmd no quotes
        cmd = self.cfg.ssh_command(quote = True)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.get_user())])

    def test_prefix(self):
        self.cfg.set_ssh_prefix_enabled(True)
        self.cfg.set_ssh_prefix('echo bar')
        cmd = self.cfg.ssh_command(cmd = ['echo', 'foo'])
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.get_user()),
                                   'echo', 'bar',
                                   'echo', 'foo'])

        # disable prefix
        cmd = self.cfg.ssh_command(cmd = ['echo', 'foo'], prefix = False)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE),
                                   '-p', '22',
                                   '{}@localhost'.format(self.cfg.get_user()),
                                   'echo', 'foo'])

    def test_disable_args(self):
        cmd = self.cfg.ssh_command(port = False, user_host = False)
        self.assertListEqual(cmd, ['ssh',
                                   '-o', 'ServerAliveInterval=240',
                                   '-o', 'LogLevel=Error',
                                   '-o', 'IdentityFile={}'.format(generic.PRIV_KEY_FILE)])
