# Back In Time
# Copyright (C) 2016-2017 Taylor Raack, Germar Reitze
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
import sys
import subprocess
import stat
import shutil
import getpass
import unittest
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
        mnt.preMountCheck(mode = 'ssh', first_run = True, **self.mount_kwargs)

        try:
            hash_id = mnt.mount(mode = 'ssh', check = False, **self.mount_kwargs)
            full_path = os.path.join(self.sharePath,".local","share","backintime","mnt",hash_id,"mountpoint","testfile")

            # warning - don't use os.access for checking writability
            # https://github.com/bit-team/backintime/issues/490#issuecomment-156265196
            with open(full_path, 'wt') as f:
                f.write('foo')
        finally:
            mnt.umount(hash_id = hash_id)

    def test_unlockSshAgent(self):
        subprocess.Popen(['ssh-add', '-D'],
                         stdout = subprocess.DEVNULL,
                         stderr = subprocess.DEVNULL).communicate()
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.unlockSshAgent(force = True)

        out = subprocess.Popen(['ssh-add', '-l'],
                               stdout = subprocess.PIPE,
                               universal_newlines = True).communicate()[0]
        self.assertIn(ssh.private_key_fingerprint, out)

    def test_unlockSshAgent_fail(self):
        subprocess.Popen(['ssh-add', '-D'],
                         stdout = subprocess.DEVNULL,
                         stderr = subprocess.DEVNULL).communicate()
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.private_key_fingerprint = 'wrong fingerprint'
        with self.assertRaisesRegex(MountException, r"Could not unlock ssh private key\. Wrong password or password not available for cron\."):
            ssh.unlockSshAgent(force = True)

    def test_checkLogin(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.checkLogin()

    def test_checkLogin_fail_wrong_user(self):
        self.cfg.setSshUser('non_existing_user')
        ssh = sshtools.SSH(cfg = self.cfg)
        with self.assertRaisesRegex(MountException, r"Password-less authentication for .+ failed.+"):
            ssh.checkLogin()

    def test_checkCipher_default(self):
        ssh = sshtools.SSH(cfg = self.cfg, cipher = 'default')
        ssh.checkCipher()

    def test_checkCipher_specific(self):
        ssh = sshtools.SSH(cfg = self.cfg, cipher = 'aes128-ctr')
        ssh.checkCipher()

    def test_checkCipher_fail(self):
        # fix debug log
        self.cfg.SSH_CIPHERS['non_existing_cipher'] = 'non_existing_cipher'
        ssh = sshtools.SSH(cfg = self.cfg, cipher = 'non_existing_cipher')
        with self.assertRaisesRegex(MountException, r"Cipher .+ failed for.+"):
            ssh.checkCipher()

    @unittest.skip('Not yet implemented')
    def test_benchmarkCipher(self):
        pass

    def test_checkKnownHosts(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.checkKnownHosts()

    def test_checkKnownHosts_fail(self):
        self.cfg.setSshHost('non_existing_host')
        ssh = sshtools.SSH(cfg = self.cfg)
        with self.assertRaisesRegex(MountException, r".+ not found in ssh_known_hosts\."):
            ssh.checkKnownHosts()

    def test_checkRemoteFolder(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        #create new directories
        ssh.checkRemoteFolder()
        self.assertTrue(os.path.isdir(self.remotePath))

        #rerun check to test if it correctly recognize previous created folders
        ssh.checkRemoteFolder()

        #make folder read-only
        os.chmod(self.remotePath, stat.S_IRUSR | stat.S_IXUSR)
        with self.assertRaisesRegex(MountException, r"Remote path is not writable.+"):
            ssh.checkRemoteFolder()

        #make folder not executable
        os.chmod(self.remotePath, stat.S_IRUSR | stat.S_IWUSR)
        with self.assertRaisesRegex(MountException, r"Remote path is not executable.+"):
            ssh.checkRemoteFolder()

        #make it writable again otherwise cleanup will fail
        os.chmod(self.remotePath, stat.S_IRWXU)

    def test_checkRemoteFolder_fail_not_a_folder(self):
        with open(self.remotePath, 'wt') as f:
            f.write('foo')
        self.cfg.setSshSnapshotsPath(self.remotePath)
        ssh = sshtools.SSH(cfg = self.cfg)

        #path already exist but is not a folder
        with self.assertRaisesRegex(MountException, r"Remote path exists but is not a directory.+"):
            ssh.checkRemoteFolder()

    def test_checkRemoteFolder_fail_can_not_create(self):
        ssh = sshtools.SSH(cfg = self.cfg)

        #can not create path
        os.chmod(self.tmpDir.name, stat.S_IRUSR | stat.S_IXUSR)
        with self.assertRaisesRegex(MountException, r"Couldn't create remote path.+"):
            ssh.checkRemoteFolder()
        #make it writable again otherwise cleanup will fail
        os.chmod(self.tmpDir.name, stat.S_IRWXU)

    def test_checkRemoteFolder_with_spaces(self):
        self.remotePath = os.path.join(self.tmpDir.name, 'foo bar')
        self.cfg.setSshSnapshotsPath(self.remotePath)

        ssh = sshtools.SSH(cfg = self.cfg)
        #create new directories
        ssh.checkRemoteFolder()
        self.assertTrue(os.path.isdir(self.remotePath))

    def test_checkPingHost(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.checkPingHost()

    def test_checkPingHost_fail(self):
        self.cfg.setSshHost('non_existing_host')
        ssh = sshtools.SSH(cfg = self.cfg)
        with self.assertRaisesRegex(MountException, r'Ping .+ failed\. Host is down or wrong address\.'):
            ssh.checkPingHost()

    def test_check_remote_command(self):
        self.cfg.setNiceOnRemote(tools.checkCommand('nice'))
        self.cfg.setIoniceOnRemote(tools.checkCommand('ionice'))
        self.cfg.setNocacheOnRemote(tools.checkCommand('nocache'))
        self.cfg.setSmartRemoveRunRemoteInBackground(tools.checkCommand('screen') and tools.checkCommand('flock'))
        os.mkdir(self.remotePath)
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.checkRemoteCommands()

    def test_check_remote_command_fail(self):
        cmds = []
        if tools.checkCommand('nice'):
            cmds.append('nice')
            self.cfg.setNiceOnRemote(True)
        if tools.checkCommand('ionice'):
            cmds.append('ionice')
            self.cfg.setIoniceOnRemote(True)
        if tools.checkCommand('nocache'):
            cmds.append('nocache')
            self.cfg.setNocacheOnRemote(True)
        if tools.checkCommand('screen') and tools.checkCommand('flock'):
            cmds.extend(('screen', 'flock', 'rmdir', 'mktemp'))
            self.cfg.setSmartRemoveRunRemoteInBackground(True)

        # make one after an other command from 'cmds' fail by symlink them
        # to /bin/false
        false = tools.which('false')
        for cmd in cmds:
            msg = 'current trap: %s' %cmd
            with self.subTest(cmd = cmd):
                with TemporaryDirectory() as self.remotePath:
                    self.cfg.setSshSnapshotsPath(self.remotePath)

                    os.symlink(false, os.path.join(self.remotePath, cmd))
                    self.cfg.setSshPrefix(True, "export PATH=%s:$PATH; " %self.remotePath)
                    ssh = sshtools.SSH(cfg = self.cfg)
                    with self.assertRaisesRegex(MountException, r"Remote host .+ doesn't support '.*?%s.*'" %cmd, msg = msg):
                        ssh.checkRemoteCommands()

    def test_check_remote_command_hard_link_fail(self):
        # let hard-link check fail by manipulate one of the files
        os.mkdir(self.remotePath)
        self.cfg.setSshPrefix(True, 'TRAP=$(ls -1d %s/tmp_* | tail -n1)/a; rm $TRAP; echo bar > $TRAP; ' %self.remotePath)
        ssh = sshtools.SSH(cfg = self.cfg)
        with self.assertRaisesRegex(MountException, r"Remote host .+ doesn't support hardlinks"):
            ssh.checkRemoteCommands()

    def test_check_remote_command_with_spaces(self):
        self.cfg.setSmartRemoveRunRemoteInBackground(tools.checkCommand('screen') and tools.checkCommand('flock'))
        self.remotePath = os.path.join(self.tmpDir.name, 'foo bar')
        self.cfg.setSshSnapshotsPath(self.remotePath)
        os.mkdir(self.remotePath)
        ssh = sshtools.SSH(cfg = self.cfg)
        ssh.checkRemoteCommands()

    def test_randomId(self):
        ssh = sshtools.SSH(cfg = self.cfg)
        self.assertRegex(ssh.randomId(size = 6), r'[A-Z0-9]{6}')

class TestSshKey(generic.TestCaseCfg):
    def test_sshKeyGen(self):
        with TemporaryDirectory() as tmp:
            secKey = os.path.join(tmp, 'key')
            pubKey = secKey + '.pub'
            # create new key
            self.assertTrue(sshtools.sshKeyGen(secKey))
            self.assertTrue(os.path.isfile(secKey))
            self.assertTrue(os.path.isfile(pubKey))

            # do not overwrite existing keys
            self.assertFalse(sshtools.sshKeyGen(secKey))

    @unittest.skipIf(getpass.getuser() != 'germar', 'Password login does not work on Travis-ci.')
    @unittest.skipIf(not generic.LOCAL_SSH, 'Skip as this test requires a local ssh server, public and private keys installed')
    def test_sshCopyId(self):
        with TemporaryDirectory() as tmp:
            secKey = os.path.join(tmp, 'key')
            pubKey = secKey + '.pub'
            authKeys = os.path.expanduser('~/.ssh/authorized_keys')
            authKeysSic = os.path.join(tmp, 'sic')
            if os.path.exists(authKeys):
                shutil.copyfile(authKeys, authKeysSic)
                os.remove(authKeys)

            # create new key
            sshtools.sshKeyGen(secKey)
            self.assertTrue(os.path.isfile(pubKey))
            with open(pubKey, 'rt') as f:
                pubKeyValue = f.read()

            try:
                # test copy pubKey
                self.assertTrue(sshtools.sshCopyId(pubKey, self.cfg.user(), 'localhost',
                                                   askPass = 'test/mock_askpass'))

                self.assertTrue(os.path.exists(authKeys))
                with open(authKeys, 'rt') as f:
                    self.assertIn(pubKeyValue, f.readlines())
            finally:
                # restore original ~/.ssh/authorized_keys file without test pubKey
                if os.path.exists(authKeysSic):
                    shutil.copyfile(authKeysSic, authKeys)

    @unittest.skipIf(not tools.checkCommand('ssh-keygen'),
                     "'ssh-keygen' not found.")
    def test_sshKeyFingerprint(self):
        self.assertIsNone(sshtools.sshKeyFingerprint(os.path.abspath(__file__)))

        with TemporaryDirectory() as d:
            key = os.path.join(d, 'key')
            cmd = ['ssh-keygen', '-q', '-N', '', '-f', key]
            proc = subprocess.Popen(cmd)
            proc.communicate()

            fingerprint = sshtools.sshKeyFingerprint(key)
            self.assertIsInstance(fingerprint, str)
            if fingerprint.startswith('SHA256'):
                self.assertEqual(len(fingerprint), 50)
                self.assertRegex(fingerprint, r'^SHA256:[a-zA-Z0-9/+]+$')
            else:
                self.assertEqual(len(fingerprint), 47)
                self.assertRegex(fingerprint, r'^[a-fA-F0-9:]+$')

    @unittest.skipIf(not generic.LOCAL_SSH, 'Skip as this test requires a local ssh server, public and private keys installed')
    def test_sshHostKey(self):
        fingerprint, keyHash, keyType = sshtools.sshHostKey('localhost')
        self.assertIsInstance(fingerprint, str)
        self.assertIsInstance(keyHash, str)
        self.assertIsInstance(keyType, str)
        if fingerprint.startswith('SHA256'):
            self.assertEqual(len(fingerprint), 50)
            self.assertRegex(fingerprint, r'^SHA256:[a-zA-Z0-9/+]+$')
        else:
            self.assertEqual(len(fingerprint), 47)
            self.assertRegex(fingerprint, r'^[a-fA-F0-9:]+$')

        self.assertIn(keyType, ('ECDSA', 'RSA'))

        hostKey = '/etc/ssh/ssh_host_{}_key.pub'.format(keyType.lower())
        self.assertTrue(os.path.exists(hostKey))
        self.assertEqual(3, len(keyHash.split()))
        try:
            with open(hostKey, 'rt') as f:
                pubKey = f.read().split()[1]
            self.assertEqual(pubKey, keyHash.split()[2])
        except (IOError, IndexError):
            pass

    def test_writeKnownHostFile(self):
        KEY = '|1|abcdefghijklmnopqrstuvwxyz= ecdsa-sha2-nistp256 AAAAABCDEFGHIJKLMNOPQRSTUVWXYZ='
        with TemporaryDirectory() as tmp:
            knownHosts = os.path.expanduser('~/.ssh/known_hosts')
            knownHostsSic = os.path.join(tmp, 'known_hosts')
            if os.path.exists(knownHosts):
                shutil.copyfile(knownHosts, knownHostsSic)

            try:
                sshtools.writeKnownHostsFile(KEY)

                self.assertTrue(os.path.exists(knownHosts))
                with open(knownHosts, 'rt') as f:
                    self.assertIn(KEY, [x.strip() for x in f.readlines()])
            finally:
                # restore original known_hosts file
                if os.path.exists(knownHostsSic):
                    shutil.copyfile(knownHostsSic, knownHosts)
