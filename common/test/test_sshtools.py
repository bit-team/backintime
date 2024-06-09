# Back In Time
# Copyright (C) 2016-2022 Taylor Raack, Germar Reitze
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
import random
import subprocess
import stat
import shutil
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import mount
import sshtools
import tools
from exceptions import MountException

SKIP_MESSAGE_SSH = 'Skip as this test requires a local ssh server, public ' \
                   'and private keys installed'

@unittest.skipIf(not generic.LOCAL_SSH, SKIP_MESSAGE_SSH)
class TestSSH(generic.SSHTestCase):
    def test_can_mount_ssh_rw(self):
        mnt = mount.Mount(cfg = self.cfg, tmp_mount = True)
        mnt.preMountCheck(mode = 'ssh', first_run = True, **self.mount_kwargs)

        try:
            hash_id = mnt.mount(mode = 'ssh', check = False, **self.mount_kwargs)
            full_path = os.path.join(
                    self.sharePath, ".local", "share", "backintime", "mnt", hash_id, "mountpoint", "testfile")

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
        self.assertIsDir(self.remotePath)

        #rerun check to test if it correctly recognize previous created folders
        ssh.checkRemoteFolder()

        #make folder read-only
        with generic.mockPermissions(self.remotePath, stat.S_IRUSR | stat.S_IXUSR):
            with self.assertRaisesRegex(MountException, r"Remote path is not writable.+"):
                ssh.checkRemoteFolder()

        #make folder not executable
        with generic.mockPermissions(self.remotePath, stat.S_IRUSR | stat.S_IWUSR):
            with self.assertRaisesRegex(MountException, r"Remote path is not executable.+"):
                ssh.checkRemoteFolder()

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
        with generic.mockPermissions(self.tmpDir.name, stat.S_IRUSR | stat.S_IXUSR):
            with self.assertRaisesRegex(MountException, r"Couldn't create remote path.+"):
                ssh.checkRemoteFolder()

    def test_checkRemoteFolder_with_spaces(self):
        self.remotePath = os.path.join(self.tmpDir.name, 'foo bar')
        self.cfg.setSshSnapshotsPath(self.remotePath)

        ssh = sshtools.SSH(cfg = self.cfg)
        #create new directories
        ssh.checkRemoteFolder()
        self.assertIsDir(self.remotePath)

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
            self.assertIsFile(secKey)
            self.assertIsFile(pubKey)

            # do not overwrite existing keys
            self.assertFalse(sshtools.sshKeyGen(secKey))

    @unittest.skipIf(not tools.checkCommand('ssh-keygen'),
                     "'ssh-keygen' not found.")
    def test_sshKeyFingerprint(self):
        self.assertIsNone(
            sshtools.sshKeyFingerprint(os.path.abspath(__file__)))

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
        self.assertExists(hostKey)
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

                self.assertExists(knownHosts)
                with open(knownHosts, 'rt') as f:
                    self.assertIn(KEY, [x.strip() for x in f.readlines()])
            finally:
                # restore original known_hosts file
                if os.path.exists(knownHostsSic):
                    shutil.copyfile(knownHostsSic, knownHosts)

@unittest.skipIf(not generic.LOCAL_SSH, SKIP_MESSAGE_SSH)
class TestStartSshAgent(generic.SSHTestCase):
    # running this test requires that user has public / private key pair created and ssh server running
    SOCK = 'SSH_AUTH_SOCK'
    PID =  'SSH_AGENT_PID'

    def setUp(self):
        super(TestStartSshAgent, self).setUp()
        self.ssh = sshtools.SSH(cfg = self.cfg)
        self.currentSock = os.environ.pop(self.SOCK, '')
        self.currentPid  = os.environ.pop(self.PID, '')

    def tearDown(self):
        os.environ[self.SOCK] = self.currentSock
        os.environ[self.PID]  = self.currentPid

    def test_startSshAgent(self):
        self.ssh.startSshAgent()
        self.assertTrue(self.SOCK in os.environ)
        self.assertTrue(self.PID  in os.environ)

    @patch('tools.which')
    @patch('os.kill')
    def test_startSshAgentEqualSign(self, mockKill, mockWhich):
        mockWhich.return_value = ['echo', 'setenv SSH_AUTH_SOCK=/tmp/ssh-zWg8uTdgh1QJ/agent.9070;\n',
                                  'setenv SSH_AGENT_PID=9071;\n'
                                  'echo Agent pid 9071;']
        self.ssh.startSshAgent()
        self.assertTrue(self.SOCK in os.environ)
        self.assertTrue(self.PID  in os.environ)

    @patch('tools.which')
    @patch('os.kill')
    def test_startSshAgentSpace(self, mockKill, mockWhich):
        mockWhich.return_value = ['echo', 'setenv SSH_AUTH_SOCK /tmp/ssh-zWg8uTdgh1QJ/agent.9070;\n',
                                  'setenv SSH_AGENT_PID 9071;\n'
                                  'echo Agent pid 9071;']
        self.ssh.startSshAgent()
        self.assertTrue(self.SOCK in os.environ)
        self.assertTrue(self.PID  in os.environ)

    @patch('tools.which')
    @patch('os.kill')
    def test_startSshAgentExport(self, mockKill, mockWhich):
        mockWhich.return_value = ['echo', 'SSH_AUTH_SOCK=/tmp/ssh-zWg8uTdgh1QJ/agent.9070; export SSH_AUTH_SOCK;\n',
                                  'SSH_AGENT_PID=9071; export SSH_AGENT_PID;\n'
                                  'echo Agent pid 9071;']
        self.ssh.startSshAgent()
        self.assertTrue(self.SOCK in os.environ)
        self.assertTrue(self.PID  in os.environ)

    @patch('tools.which')
    def test_startSshAgentError(self, mockWhich):
        mockWhich.return_value = '/bin/false'
        with self.assertRaises(MountException):
            self.ssh.startSshAgent()

    @patch('tools.which')
    def test_startSshAgentMissing(self, mockWhich):
        mockWhich.return_value = ''
        with self.assertRaises(MountException):
            self.ssh.startSshAgent()

class SSHCopyID(unittest.TestCase):
    def test_complete_command(self):
        """Complete generated command"""
        command = sshtools.sshCopyIdCommand(
            generic.PRIV_KEY_FILE,
            'user',
            'non_existing_host',
        )
        self.assertEqual(
            command,
            [
                'ssh-copy-id',
                '-i',
                generic.PRIV_KEY_FILE,
                '-p',
                '22',
                'user@non_existing_host'
            ]
        )

    def test_default_port(self):
        """Default port"""
        sut = sshtools.sshCopyIdCommand(
            generic.PRIV_KEY_FILE,
            'user',
            'non_existing_host',
        )
        self.assertEqual(len(sut), 6, sut)
        # no port explicit specified
        self.assertEqual(sut[4], '22')

    def test_custom_port(self):
        """Custom (random) port"""
        custom_port = str(random.randint(23, 128))

        sut = sshtools.sshCopyIdCommand(
            generic.PRIV_KEY_FILE,
            'user',
            'non_existing_host',
            port=custom_port
        )
        self.assertEqual(sut[3], '-p')
        self.assertEqual(sut[4], custom_port)

    def test_proxy_with_default_port(self):
        """Used proxy and default port"""
        proxy_user = 'non_existing_proxy_user'
        proxy_host = 'non_existing_proxy_host'

        sut = sshtools.sshCopyIdCommand(
            generic.PRIV_KEY_FILE,
            'user',
            'non_existing_host',
            proxy_user=proxy_user,
            proxy_host=proxy_host
        )

        self.assertIn(
            'ProxyJump=non_existing_proxy_user@non_existing_proxy_host:22',
            sut)

    def test_proxy_with_custom_port(self):
        """Used proxy and custom port"""
        proxy_user = 'non_existing_proxy_user'
        proxy_host = 'non_existing_proxy_host'
        proxy_port = str(random.randint(23, 128))

        sut = sshtools.sshCopyIdCommand(
            generic.PRIV_KEY_FILE,
            'user',
            'non_existing_host',
            proxy_user=proxy_user,
            proxy_host=proxy_host,
            proxy_port=proxy_port
        )

        self.assertIn(
            'ProxyJump=non_existing_proxy_user@non_existing_proxy_host'
            f':{proxy_port}',
            sut)
