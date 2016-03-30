# Back In Time
# Copyright (C) 2016 Taylor Raack, Germar Reitze
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
import sys
import unittest
import subprocess
import stat
from tempfile import TemporaryDirectory
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import config
import logger
import mount
import sshtools
from exceptions import MountException

ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'

@unittest.skipIf(not ON_TRAVIS, 'Skip as this test requires a local ssh server, public and private keys installed')
class TestSSH(generic.TestCase):
    # running this test requires that user has public / private key pair created and ssh server running

    def setUp(self):
        super(TestSSH, self).setUp()
        logger.DEBUG = '-v' in sys.argv
        self.config = config.Config()
        self.config.set_snapshots_mode('ssh')
        self.config.set_ssh_host('localhost')
        self.config.set_ssh_private_key_file(os.path.expanduser(os.path.join("~",".ssh","id_rsa")))
        self.mount_kwargs = {}

    def test_can_mount_ssh_rw(self):
        with TemporaryDirectory() as dirpath:
            self.config.set_snapshots_path_ssh(dirpath)

            mnt = mount.Mount(cfg = self.config, tmp_mount = True)
            mnt.pre_mount_check(mode = 'ssh', first_run = True, **self.mount_kwargs)

            try:
                hash_id = mnt.mount(mode = 'ssh', check = False, **self.mount_kwargs)
                full_path = os.path.expanduser(os.path.join("~",".local","share","backintime","mnt",hash_id,"mountpoint","testfile"))

                # warning - don't use os.access for checking writability
                # https://github.com/bit-team/backintime/issues/490#issuecomment-156265196
                with open(full_path, 'wt') as f:
                    f.write('foo')
            finally:
                mnt.umount(hash_id = hash_id)

    def test_unlock_ssh_agent(self):
        subprocess.Popen(['ssh-add', '-D'],
                         stdout = subprocess.DEVNULL,
                         stderr = subprocess.DEVNULL).communicate()
        ssh1 = sshtools.SSH(cfg = self.config)
        try:
            ssh1.unlock_ssh_agent(force = True)
        except MountException as e:
            self.fail('unlock_ssh_agent failed unexpected with: %s' %str(e))
        out = subprocess.Popen(['ssh-add', '-l'],
                               stdout = subprocess.PIPE,
                               universal_newlines = True).communicate()[0]
        self.assertIn(ssh1.private_key_fingerprint, out)

        subprocess.Popen(['ssh-add', '-D'],
                         stdout = subprocess.DEVNULL,
                         stderr = subprocess.DEVNULL).communicate()
        ssh2 = sshtools.SSH(cfg = self.config)
        ssh2.private_key_fingerprint = 'wrong fingerprint'
        with self.assertRaises(MountException):
            ssh2.unlock_ssh_agent(force = True)

    def test_check_login(self):
        ssh1 = sshtools.SSH(cfg = self.config)
        try:
            ssh1.check_login()
        except MountException as e:
            self.fail('check_login failed unexpected with: %s' %str(e))

        self.config.set_ssh_user('non_existing_user')
        ssh2 = sshtools.SSH(cfg = self.config)
        with self.assertRaises(MountException):
            ssh2.check_login()

    @unittest.skip('Not yet implemented')
    def test_check_cipher(self):
        pass

    @unittest.skip('Not yet implemented')
    def test_benchmark_cipher(self):
        pass

    def test_check_known_hosts(self):
        ssh1 = sshtools.SSH(cfg = self.config)
        try:
            ssh1.check_known_hosts()
        except MountException as e:
            self.fail('check_known_hosts failed unexpected with: %s' %str(e))

        self.config.set_ssh_host('non_existing_host')
        ssh2 = sshtools.SSH(cfg = self.config)
        with self.assertRaises(MountException):
            ssh2.check_known_hosts()

    def test_check_remote_folder(self):
        with TemporaryDirectory() as tmp:
            remotePath = os.path.join(tmp, 'foo')
            self.config.set_snapshots_path_ssh(remotePath)
            ssh1 = sshtools.SSH(cfg = self.config)
            #create new directories
            try:
                ssh1.check_remote_folder()
            except MountException as e:
                self.fail('check_remote_folder failed unexpected with: %s' %str(e))
            self.assertTrue(os.path.isdir(remotePath))

            #rerun check to test if it correctly recognize previous created folders
            try:
                ssh1.check_remote_folder()
            except MountException as e:
                self.fail('check_remote_folder second test failed unexpected with: %s' %str(e))

            #make folder read-only
            os.chmod(remotePath, stat.S_IRUSR | stat.S_IXUSR)
            with self.assertRaises(MountException):
                ssh1.check_remote_folder()

            #make folder not executable
            os.chmod(remotePath, stat.S_IRUSR | stat.S_IWUSR)
            with self.assertRaises(MountException):
                ssh1.check_remote_folder()

            #make it writeable again otherwise cleanup will fail
            os.chmod(remotePath, stat.S_IRWXU)

        with TemporaryDirectory() as tmp:
            remotePath = os.path.join(tmp, 'foo')
            with open(remotePath, 'wt') as f:
                f.write('foo')
            self.config.set_snapshots_path_ssh(remotePath)
            ssh2 = sshtools.SSH(cfg = self.config)

            #path already exist but is not a folder
            with self.assertRaises(MountException):
                ssh2.check_remote_folder()

        with TemporaryDirectory() as tmp:
            remotePath = os.path.join(tmp, 'foo')
            self.config.set_snapshots_path_ssh(remotePath)
            ssh3 = sshtools.SSH(cfg = self.config)

            #can not create path
            os.chmod(tmp, stat.S_IRUSR | stat.S_IXUSR)
            with self.assertRaises(MountException):
                ssh2.check_remote_folder()
            #make it writeable again otherwise cleanup will fail
            os.chmod(tmp, stat.S_IRWXU)

    def test_check_ping_host(self):
        ssh1 = sshtools.SSH(cfg = self.config)
        try:
            ssh1.check_ping_host()
        except MountException as e:
            self.fail('check_ping_host failed unexpected with: %s' %str(e))

        self.config.set_ssh_host('non_existing_host')
        ssh2 = sshtools.SSH(cfg = self.config)
        with self.assertRaises(MountException):
            ssh2.check_ping_host()

    @unittest.skip('Not yet implemented')
    def test_check_remote_command(self):
        pass

    def test_random_id(self):
        ssh = sshtools.SSH(cfg = self.config)
        self.assertRegex(ssh.random_id(size = 6), r'[A-Z0-9]{6}')
