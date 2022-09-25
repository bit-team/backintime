# Back In Time
# Copyright (C) 2016-2022 Germar Reitze
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

"""This module offers some helpers and tools for unittesting.

Most of the conent are `unittest.TestCase` derived classed doing basic setup
for the testing environment. They are dealing with snapshot path's, SSH,
config files and things like set.
"""

import os
import sys
import unittest
import socket
from unittest.mock import patch
from tempfile import TemporaryDirectory, NamedTemporaryFile
from contextlib import contextmanager

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logger
import config
import snapshots
import tools

# mock notifyplugin to suppress notifications
tools.registerBackintimePath('qt', 'plugins')

TMP_FLOCK = NamedTemporaryFile()
PRIV_KEY_FILE = os.path.expanduser(
    os.path.join("~", ".ssh", "id_rsa"))
AUTHORIZED_KEYS_FILE = os.path.expanduser(
    os.path.join("~", ".ssh", "authorized_keys"))
DUMMY = 'dummy_test_process.sh'

if os.path.exists(PRIV_KEY_FILE + '.pub') \
   and os.path.exists(AUTHORIZED_KEYS_FILE):

    with open(PRIV_KEY_FILE + '.pub', 'rb') as pub:

        with open(AUTHORIZED_KEYS_FILE, 'rb') as auth:
            KEY_IN_AUTH = pub.read() in auth.readlines()
else:
    KEY_IN_AUTH = False

# check if port 22 on localhost is available
# sshd should be there...
try:
    with socket.create_connection(('localhost', '22'), 2.0) as s:
        sshdPortAvailable = not bool(s.connect_ex(s.getpeername()))
except ConnectionRefusedError:
    sshdPortAvailable = False

LOCAL_SSH = all((tools.processExists('sshd'),
                 os.path.isfile(PRIV_KEY_FILE),
                 KEY_IN_AUTH,
                 sshdPortAvailable))

ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'
ON_RTD = os.environ.get('READTHEDOCS', 'None').lower() == 'true'


class TestCase(unittest.TestCase):
    """Base class for Back In Time unittesting.

    """

    def __init__(self, methodName):
        """Initialize.

        Args:
            methodName: Unkown.
        """

        # note by buhtz: This is not recommended. Unittest module handle
        # that itself. The default locale is "C". Need further investigation.
        os.environ['LANGUAGE'] = 'en_US.UTF-8'

        # config file path
        self.cfgFile = os.path.abspath(
            os.path.join(__file__, os.pardir, 'config'))

        logger.APP_NAME = 'BIT_unittest'
        logger.openlog()

        super(TestCase, self).__init__(methodName)

    def setUp(self):
        """
        """
        logger.DEBUG = '-v' in sys.argv
        self.run = False
        self.sharePathObj = TemporaryDirectory()
        self.sharePath = self.sharePathObj.name

    def tearDown(self):
        """
        """
        self.sharePathObj.cleanup()

    def callback(self, func, *args):
        """
        """
        func(*args)
        self.run = True

    # the next six assert methods are deprecated and can be replaced
    # by using Pythons in-build "pathlib.Path"

    def assertExists(self, *path):
        full_path = os.path.join(*path)
        if not os.path.exists(full_path):
            self.fail('File does not exist: {}'.format(full_path))

    def assertNotExists(self, *path):
        full_path = os.path.join(*path)
        if os.path.exists(full_path):
            self.fail('File does unexpected exist: {}'.format(full_path))

    def assertIsFile(self, *path):
        full_path = os.path.join(*path)
        if not os.path.isfile(full_path):
            self.fail('Not a File: {}'.format(full_path))

    def assertIsNoFile(self, *path):
        full_path = os.path.join(*path)
        if os.path.isfile(full_path):
            self.fail('Unexpected File: {}'.format(full_path))

    def assertIsDir(self, *path):
        full_path = os.path.join(*path)
        if not os.path.isdir(full_path):
            self.fail('Not a directory: {}'.format(full_path))

    def assertIsLink(self, *path):
        full_path = os.path.join(*path)
        if not os.path.islink(full_path):
            self.fail('Not a symlink: {}'.format(full_path))


class TestCaseCfg(TestCase):
    """Base class setting up config file.
    """

    def setUp(self):
        """
        """
        super(TestCaseCfg, self).setUp()

        # Testing explicitly instead of try-except
        # because we are doing unittesting here.
        if config.Config._instance:
            # Delete the config instance from the previous unittest
            config.Config._instance = None

        self.cfg = config.Config(self.cfgFile, self.sharePath)

        # mock notifyplugin to suppress notifications
        patcher = patch('notifyplugin.NotifyPlugin.message')
        self.mockNotifyPlugin = patcher.start()

        self.cfg.PLUGIN_MANAGER.load()

    def tearDown(self):
        """
        """
        config.Config._instance = None


class TestCaseSnapshotPath(TestCaseCfg):
    """Base class for snapshot test cases.

    It setup a temporary directory as snapshot paths for each test method.
    """

    def setUp(self):
        """
        """
        super(TestCaseSnapshotPath, self).setUp()

        # use a new TemporaryDirectory for snapshotPath to avoid
        # side effects on leftovers
        self.tmpDir = TemporaryDirectory()
        self.cfg.dict['profile1.snapshots.path'] = self.tmpDir.name
        self.snapshotPath = self.cfg.snapshotsFullPath()

    def tearDown(self):
        """
        """
        super(TestCaseSnapshotPath, self).tearDown()

        self.tmpDir.cleanup()


class SnapshotsTestCase(TestCaseSnapshotPath):
    """Base class for snapshot testing unittest classes.

    Unclear why this need to be separated from `TestCaseSnapshotPath`.
    """

    def setUp(self):
        """
        """
        super(SnapshotsTestCase, self).setUp()

        os.makedirs(self.snapshotPath)
        self.sn = snapshots.Snapshots(self.cfg)

        # use a tmp-file for flock because test_flockExclusive would deadlock
        # otherwise if a regular snapshot is running in background
        self.sn.GLOBAL_FLOCK = TMP_FLOCK.name


class SnapshotsWithSidTestCase(SnapshotsTestCase):
    """
    """

    def setUp(self):
        """
        """
        super(SnapshotsWithSidTestCase, self).setUp()

        self.sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.sid.makeDirs()
        self.testDir = 'foo/bar'
        self.testDirFullPath = self.sid.pathBackup(self.testDir)
        self.testFile = 'foo/bar/baz'
        self.testFileFullPath = self.sid.pathBackup(self.testFile)

        self.sid.makeDirs(self.testDir)
        with open(self.sid.pathBackup(self.testFile), 'wt'):
            pass


class SSHTestCase(TestCaseCfg):
    """Base class for test cases using the SSH features.

    Running this test requires that user has public / private key pair
    created and SSH server (at localhost) running.
    """

    def setUp(self):
        """
        """
        super(SSHTestCase, self).setUp()

        logger.DEBUG = '-v' in sys.argv

        self.cfg.setSnapshotsMode('ssh')
        self.cfg.setSshHost('localhost')
        self.cfg.setSshPrivateKeyFile(PRIV_KEY_FILE)

        # use a TemporaryDirectory for remote snapshot path
        self.tmpDir = TemporaryDirectory()
        self.remotePath = os.path.join(self.tmpDir.name, 'foo')
        self.remoteFullPath = os.path.join(
            self.remotePath, 'backintime', *self.cfg.hostUserProfile())
        self.cfg.setSshSnapshotsPath(self.remotePath)
        self.mount_kwargs = {}

    def tearDown(self):
        """
        """
        super(SSHTestCase, self).tearDown()
        self.tmpDir.cleanup()


class SSHSnapshotTestCase(SSHTestCase):
    """
    """

    def setUp(self):
        """
        """
        super(SSHSnapshotTestCase, self).setUp()

        self.snapshotPath = self.cfg.sshSnapshotsFullPath()
        os.makedirs(self.snapshotPath)

        self.sn = snapshots.Snapshots(self.cfg)

        # use a tmp-file for flock because test_flockExclusive would deadlock
        # otherwise if a regular snapshot is running in background
        self.sn.GLOBAL_FLOCK = TMP_FLOCK.name


class SSHSnapshotsWithSidTestCase(SSHSnapshotTestCase):
    """
    """

    def setUp(self):
        """
        """
        super(SSHSnapshotsWithSidTestCase, self).setUp()

        self.sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.remoteSIDBackupPath = os.path.join(
            self.snapshotPath, self.sid.sid, 'backup')

        os.makedirs(self.remoteSIDBackupPath)

        self.testDir = 'foo/bar'
        self.testDirFullPath = os.path.join(
            self.remoteSIDBackupPath, self.testDir)
        self.testFile = 'foo/bar/baz'
        self.testFileFullPath = os.path.join(
            self.remoteSIDBackupPath, self.testFile)

        os.makedirs(self.testDirFullPath)

        with open(self.testFileFullPath, 'wt'):
            pass


def create_test_files(path):
    """Create folders and files.

    Args:
        path: Destination folder.

    That is the resulting folder structure ::

        foo
        └── bar
            ├── baz
            ├── file with spaces
            └── test

    """
    os.makedirs(os.path.join(path, 'foo', 'bar'))

    with open(os.path.join(path, 'foo', 'bar', 'baz'), 'wt') as f:
        f.write('foo')

    with open(os.path.join(path, 'test'), 'wt') as f:
        f.write('bar')

    with open(os.path.join(path, 'file with spaces'), 'wt') as f:
        f.write('asdf')


@contextmanager
def mockPermissions(path, mode=0o000):
    """
    """

    st = os.stat(path)
    os.chmod(path, mode)
    yield

    # fix permissions so it can be removed
    os.chmod(path, st.st_mode)
