# Back In Time
# Copyright (C) 2016 Germar Reitze
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
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys
import unittest
from tempfile import TemporaryDirectory, NamedTemporaryFile

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logger
import config
import snapshots
import tools

TMP_FLOCK = NamedTemporaryFile()
PRIV_KEY_FILE = os.path.expanduser(os.path.join("~",".ssh","id_rsa"))
AUTHORIZED_KEYS_FILE = os.path.expanduser(os.path.join("~",".ssh","authorized_keys"))
DUMMY = 'dummy_test_process.sh'

if os.path.exists(PRIV_KEY_FILE + '.pub') and os.path.exists(AUTHORIZED_KEYS_FILE):
    with open(PRIV_KEY_FILE + '.pub', 'rb') as pub:
        with open(AUTHORIZED_KEYS_FILE, 'rb') as auth:
            KEY_IN_AUTH = pub.read() in auth.readlines()
else:
    KEY_IN_AUTH = False

LOCAL_SSH = all((tools.process_exists('sshd'),
                 os.path.isfile(PRIV_KEY_FILE),
                 KEY_IN_AUTH))

ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'
ON_RTD = os.environ.get('READTHEDOCS', 'None').lower() == 'true'

class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        os.environ['LANGUAGE'] = 'en_US.UTF-8'
        self.cfgFile = os.path.abspath(os.path.join(__file__, os.pardir, 'config'))
        self.sharePath = '/tmp/bit'
        logger.APP_NAME = 'BIT_unittest'
        logger.openlog()
        super(TestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.run = False

    def callback(self, func, *args):
        func(*args)
        self.run = True

class TestCaseCfg(TestCase):
    def setUp(self):
        super(TestCaseCfg, self).setUp()
        self.cfg = config.Config(self.cfgFile, self.sharePath)

class SnapshotsTestCase(TestCaseCfg):
    def setUp(self):
        super(SnapshotsTestCase, self).setUp()
        #use a new TemporaryDirectory for snapshotPath to avoid
        #side effects on leftovers
        self.tmpDir = TemporaryDirectory()
        self.cfg.dict['profile1.snapshots.path'] = self.tmpDir.name
        self.snapshotPath = self.cfg.get_snapshots_full_path()
        os.makedirs(self.snapshotPath)

        self.sn = snapshots.Snapshots(self.cfg)
        #use a tmp-file for flock because test_flockExclusive would deadlock
        #otherwise if a regular snapshot is running in background
        self.sn.GLOBAL_FLOCK = TMP_FLOCK.name

    def tearDown(self):
        self.tmpDir.cleanup()

class SnapshotsWithSidTestCase(SnapshotsTestCase):
    def setUp(self):
        super(SnapshotsWithSidTestCase, self).setUp()
        self.sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.sid.makeDirs()
        self.testDir = 'foo/bar'
        self.testDirFullPath = self.sid.pathBackup(self.testDir)
        self.testFile = 'foo/bar/baz'
        self.testFileFullPath = self.sid.pathBackup(self.testFile)

        self.sid.makeDirs(self.testDir)
        with open(self.sid.pathBackup(self.testFile), 'wt') as f:
            pass

class SSHTestCase(TestCaseCfg):
    # running this test requires that user has public / private key pair created and ssh server running

    def setUp(self):
        super(SSHTestCase, self).setUp()
        logger.DEBUG = '-v' in sys.argv
        self.cfg.set_snapshots_mode('ssh')
        self.cfg.set_ssh_host('localhost')
        self.cfg.set_ssh_private_key_file(PRIV_KEY_FILE)
        # use a TemporaryDirectory for remote snapshot path
        self.tmpDir = TemporaryDirectory()
        self.remotePath = os.path.join(self.tmpDir.name, 'foo')
        self.cfg.set_snapshots_path_ssh(self.remotePath)
        self.mount_kwargs = {}

    def tearDown(self):
        self.tmpDir.cleanup()

class SSHSnapshotTestCase(SSHTestCase):
    def setUp(self):
        super(SSHSnapshotTestCase, self).setUp()
        self.snapshotPath = self.cfg.get_snapshots_full_path_ssh()
        os.makedirs(self.snapshotPath)

        self.sn = snapshots.Snapshots(self.cfg)
        #use a tmp-file for flock because test_flockExclusive would deadlock
        #otherwise if a regular snapshot is running in background
        self.sn.GLOBAL_FLOCK = TMP_FLOCK.name

class SSHSnapshotsWithSidTestCase(SSHSnapshotTestCase):
    def setUp(self):
        super(SSHSnapshotsWithSidTestCase, self).setUp()
        self.sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.remoteSIDBackupPath = os.path.join(self.snapshotPath, self.sid.sid, 'backup')
        os.makedirs(self.remoteSIDBackupPath)
        self.testDir = 'foo/bar'
        self.testDirFullPath = os.path.join(self.remoteSIDBackupPath, self.testDir)
        self.testFile = 'foo/bar/baz'
        self.testFileFullPath = os.path.join(self.remoteSIDBackupPath, self.testFile)

        os.makedirs(self.testDirFullPath)
        with open(self.testFileFullPath, 'wt') as f:
            pass

def create_test_files(path):
    os.makedirs(os.path.join(path, 'foo', 'bar'))
    with open(os.path.join(path, 'foo', 'bar', 'baz'), 'wt') as f:
        f.write('foo')
    with open(os.path.join(path, 'test'), 'wt') as f:
        f.write('bar')
    with open(os.path.join(path, 'file with spaces'), 'wt') as f:
        f.write('asdf')
