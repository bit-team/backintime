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
import tools
from exceptions import MountException

@unittest.skipIf(not generic.LOCAL_SSH, 'Skip as this test requires a local ssh server, public and private keys installed')
class TestSSH(generic.SSHTestCase):
    # running this test requires that user has public / private key pair created and ssh server running

    def test_can_mount_ssh_rw(self):
        mnt = mount.Mount(cfg = self.cfg, tmp_mount = True)
        mnt.pre_mount_check(mode = 'ssh', first_run = True, **self.mount_kwargs)

        try:
            hash_id = mnt.mount(mode = 'ssh', check = False, **self.mount_kwargs)
            full_path = os.path.join(self.sharePath,".local","share","backintime","mnt",hash_id,"mountpoint","testfile")

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
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.unlock_ssh_agent(force = True)

        out = subprocess.Popen(['ssh-add', '-l'],
                               stdout = subprocess.PIPE,
                               universal_newlines = True).communicate()[0]
        self.assertIn(ssh.private_key_fingerprint, out)

    def test_unlock_ssh_agent_fail(self):
        subprocess.Popen(['ssh-add', '-D'],
                         stdout = subprocess.DEVNULL,
                         stderr = subprocess.DEVNULL).communicate()
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.private_key_fingerprint = 'wrong fingerprint'
        with self.assertRaisesRegex(MountException, r"Could not unlock ssh private key\. Wrong password or password not available for cron\."):
            ssh.unlock_ssh_agent(force = True)

    def test_check_login(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.check_login()

    def test_check_login_fail_wrong_user(self):
        self.cfg.set_ssh_user('non_existing_user')
        ssh = sshtools.SSH(cfg = self.cfg)
        with self.assertRaisesRegex(MountException, r"Password-less authentication for .+ failed.+"):
            ssh.check_login()

    def test_check_cipher_default(self):
        ssh = sshtools.SSH(cfg = self.cfg, cipher = 'default')
        ssh.check_cipher()

    def test_check_cipher_specific(self):
        ssh = sshtools.SSH(cfg = self.cfg, cipher = 'aes128-ctr')
        ssh.check_cipher()

    def test_check_cipher_fail(self):
        # fix debug log
        self.cfg.SSH_CIPHERS['non_existing_cipher'] = 'non_existing_cipher'
        ssh = sshtools.SSH(cfg = self.cfg, cipher = 'non_existing_cipher')
        with self.assertRaisesRegex(MountException, r"Cipher .+ failed for.+"):
            ssh.check_cipher()

    @unittest.skip('Not yet implemented')
    def test_benchmark_cipher(self):
        pass

    def test_check_known_hosts(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.check_known_hosts()

    def test_check_known_hosts_fail(self):
        self.cfg.set_ssh_host('non_existing_host')
        ssh = sshtools.SSH(cfg = self.cfg)
        with self.assertRaisesRegex(MountException, r".+ not found in ssh_known_hosts\."):
            ssh.check_known_hosts()

    def test_check_remote_folder(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        #create new directories
        ssh.check_remote_folder()
        self.assertTrue(os.path.isdir(self.remotePath))

        #rerun check to test if it correctly recognize previous created folders
        ssh.check_remote_folder()

        #make folder read-only
        os.chmod(self.remotePath, stat.S_IRUSR | stat.S_IXUSR)
        with self.assertRaisesRegex(MountException, r"Remote path is not writeable.+"):
            ssh.check_remote_folder()

        #make folder not executable
        os.chmod(self.remotePath, stat.S_IRUSR | stat.S_IWUSR)
        with self.assertRaisesRegex(MountException, r"Remote path is not executable.+"):
            ssh.check_remote_folder()

        #make it writeable again otherwise cleanup will fail
        os.chmod(self.remotePath, stat.S_IRWXU)

    def test_check_remote_folder_fail_not_a_folder(self):
        with open(self.remotePath, 'wt') as f:
            f.write('foo')
        self.cfg.set_snapshots_path_ssh(self.remotePath)
        ssh = sshtools.SSH(cfg = self.cfg)

        #path already exist but is not a folder
        with self.assertRaisesRegex(MountException, r"Remote path exists but is not a directory.+"):
            ssh.check_remote_folder()

    def test_check_remote_folder_fail_can_not_create(self):
        ssh = sshtools.SSH(cfg = self.cfg)

        #can not create path
        os.chmod(self.tmpDir.name, stat.S_IRUSR | stat.S_IXUSR)
        with self.assertRaisesRegex(MountException, r"Couldn't create remote path.+"):
            ssh.check_remote_folder()
        #make it writeable again otherwise cleanup will fail
        os.chmod(self.tmpDir.name, stat.S_IRWXU)

    def test_check_ping_host(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.check_ping_host()

    def test_check_ping_host_fail(self):
        self.cfg.set_ssh_host('non_existing_host')
        ssh = sshtools.SSH(cfg = self.cfg)
        with self.assertRaisesRegex(MountException, r'Ping .+ failed\. Host is down or wrong address\.'):
            ssh.check_ping_host()

    def test_check_remote_command(self):
        self.cfg.set_run_nice_on_remote_enabled(tools.check_command('nice'))
        self.cfg.set_run_ionice_on_remote_enabled(tools.check_command('ionice'))
        self.cfg.set_run_nocache_on_remote_enabled(tools.check_command('nocache'))
        self.cfg.set_smart_remove_run_remote_in_background(tools.check_command('screen') and tools.check_command('flock'))
        with TemporaryDirectory() as self.remotePath:
            self.cfg.set_snapshots_path_ssh(self.remotePath)
            ssh = sshtools.SSH(cfg = self.cfg)
            ssh.check_remote_commands()

    def test_check_remote_command_fail(self):
        cmds = ['find']
        if tools.check_command('nice'):
            cmds.append('nice')
            self.cfg.set_run_nice_on_remote_enabled(True)
        if tools.check_command('ionice'):
            cmds.append('ionice')
            self.cfg.set_run_ionice_on_remote_enabled(True)
        if tools.check_command('nocache'):
            cmds.append('nocache')
            self.cfg.set_run_nocache_on_remote_enabled(True)
        if tools.check_command('screen') and tools.check_command('flock'):
            cmds.extend(('screen', 'flock', 'rmdir', 'mktemp'))
            self.cfg.set_smart_remove_run_remote_in_background(True)

        # make one after an other command from 'cmds' fail by symlink them
        # to /bin/false
        self.cfg.set_ssh_prefix_enabled(True)
        false = tools.which('false')
        for cmd in cmds:
            msg = 'current trap: %s' %cmd
            with self.subTest(cmd = cmd):
                with TemporaryDirectory() as self.remotePath:
                    self.cfg.set_snapshots_path_ssh(self.remotePath)

                    os.symlink(false, os.path.join(self.remotePath, cmd))
                    self.cfg.set_ssh_prefix("export PATH=%s:$PATH; " %self.remotePath)
                    ssh = sshtools.SSH(cfg = self.cfg)
                    with self.assertRaisesRegex(MountException, r"Remote host .+ doesn't support '.*?%s.*'" %cmd, msg = msg):
                        ssh.check_remote_commands()

    def test_check_remote_command_hard_link_fail(self):
        # let hard-link check fail by manipulate one of the files
        os.mkdir(self.remotePath)
        self.cfg.set_ssh_prefix_enabled(True)
        self.cfg.set_ssh_prefix('TRAP=$(ls -1d %s/tmp_* | tail -n1)/a; rm $TRAP; echo bar > $TRAP; ' %self.remotePath)
        ssh = sshtools.SSH(cfg = self.cfg)
        with self.assertRaisesRegex(MountException, r"Remote host .+ doesn't support hardlinks"):
            ssh.check_remote_commands()

    def test_random_id(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        self.assertRegex(ssh.random_id(size = 6), r'[A-Z0-9]{6}')
