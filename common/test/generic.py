# SPDX-FileCopyrightText: © 2016-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2023 Christian BUHTZ <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2024 David Wales (@daviewales)
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""This module offers some helpers and tools for unittesting.

Most of the content are `unittest.TestCase` derived classed doing basic setup
for the testing environment. They are dealing with snapshot path's, SSH,
config files and things like set.
"""
import os
import pathlib
import sys
import unittest
import socket
from unittest.mock import patch
from tempfile import TemporaryDirectory, NamedTemporaryFile
from contextlib import contextmanager

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logger
import tools
# Needed because backintime.startApp() is not invoked.
tools.initiate_translation(None)
import config
import snapshots

# mock notifyplugin to suppress notifications
tools.registerBackintimePath('qt', 'plugins')

TMP_FLOCK = NamedTemporaryFile(prefix='backintime', suffix='.flock')
SSH_PATH = pathlib.Path.home() / '.ssh'
AUTHORIZED_KEYS_FILE = SSH_PATH / 'authorized_keys'
DUMMY = 'dummy_test_process.sh'

public_keys = (
    # RSA key
    SSH_PATH / 'id_rsa.pub',
    # ed25519 key
    SSH_PATH / 'id_ed25519.pub',
)
existing_public_keys = tuple(filter(lambda k: k.exists(), public_keys))
authorised_public_keys = []

# Check if the existing keys are in authorized file
if AUTHORIZED_KEYS_FILE.exists():
    with AUTHORIZED_KEYS_FILE.open('rb') as auth:
        auth_keys = auth.readlines()

    for key in existing_public_keys:
        with key.open('rb') as pub:
            if pub.read() in auth_keys:
                authorised_public_keys.append(key)

if authorised_public_keys:
    KEY_IN_AUTH = True
    PUBLIC_KEY_FILE = authorised_public_keys[0]
    PRIV_KEY_FILE = PUBLIC_KEY_FILE.with_suffix('')
else:
    KEY_IN_AUTH = False
    try:
        PUBLIC_KEY_FILE = existing_public_keys[0]
        PRIV_KEY_FILE = PUBLIC_KEY_FILE.with_suffix('')
    except IndexError:
        PUBLIC_KEY_FILE = None
        PRIV_KEY_FILE = None

PRIV_KEY_IS_FILE = PRIV_KEY_FILE.is_file() if PRIV_KEY_FILE else False

# check if port 22 on localhost is available
# sshd should be there...
try:
    with socket.create_connection(('localhost', '22'), 2.0) as s:
        sshdPortAvailable = not bool(s.connect_ex(s.getpeername()))
except ConnectionRefusedError:
    sshdPortAvailable = False

ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'
ON_RTD = os.environ.get('READTHEDOCS', 'None').lower() == 'true'

SKIP_SSH_TEST_MESSAGE = 'Skip as this test requires a local ssh server, ' \
                        'public and private keys installed'
# # DEBUG
# print(f"{tools.processExists('sshd')=}")
# print(f'{PUBLIC_KEY_FILE=}')
# print(f'{PRIV_KEY_FILE=}')
# print(f'{PRIV_KEY_IS_FILE=}')
# print(f'{KEY_IN_AUTH=}')
# print(f'{sshdPortAvailable=}')

# If False all SSH related tests are skipped.
# On TravisCI that tests are enforced and never skipped.
LOCAL_SSH = True if ON_TRAVIS else all([
    # Server process running?
    tools.processExists('sshd'),
    # Privat keyfile
    PRIV_KEY_IS_FILE,
    # Key known (copied via "ssh-copy-id")
    KEY_IN_AUTH,
    # SSH port (22) available at the server
    sshdPortAvailable
])


# Temporary workaround (buhtz: 2023-09)
# Not all components of the code are able to handle Path objects
PRIV_KEY_FILE = str(PRIV_KEY_FILE)
PUBLIC_KEY_FILE = str(PUBLIC_KEY_FILE)
AUTHORIZED_KEYS_FILE = str(AUTHORIZED_KEYS_FILE)

class TestCase(unittest.TestCase):
    """Base class for Back In Time unit- and integration testing.

    In summary following is set via 'setUp()' and '__init__()':
       - Initialize logging.
       - Set path to config file (not open it).
       - Set path the "backup source" directory.
    """

    def __init__(self, methodName):
        """Initialize logging and set the path of the config file.

        The config file in the "test" folder is used.

        Args:
            methodName: Unknown.
        """

        # note by buhtz: This is not recommended. Unittest module handle
        # that itself. The default locale while unittesting is "C".
        # Need further investigation.
        os.environ['LANGUAGE'] = 'en_US.UTF-8'

        # Path to config file (in "common/test/config")
        self.cfgFile = os.path.abspath(
            os.path.join(__file__, os.pardir, 'config'))

        # Initialize logging
        logger.APP_NAME = 'BIT_unittest'
        logger.openlog()

        super(TestCase, self).__init__(methodName)

    def setUp(self):
        """
        """
        logger.DEBUG = '-v' in sys.argv

        # ?
        self.run = False

        # Not sure but this could be the "backup source" directory
        self.sharePathObj = TemporaryDirectory()
        self.sharePath = self.sharePathObj.name

    def tearDown(self):
        """
        """
        # BUHTZ 10/09/2022: In my understanding it is not needed and would be
        # done implicitly when the test class is destroyed.
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
    """Testing base class opening the config file, creating the config
    instance and starting the notify plugin.

    The path to the config file was set by the inherited class
    :py:class:`generic.TestCase`.
    """

    def setUp(self):
        super(TestCaseCfg, self).setUp()
        self.cfg = config.Config(self.cfgFile, self.sharePath)

        # mock notifyplugin to suppress notifications
        patcher = patch('notifyplugin.NotifyPlugin.message')
        self.mockNotifyPlugin = patcher.start()

        self.cfg.PLUGIN_MANAGER.load()


class TestCaseSnapshotPath(TestCaseCfg):
    """Testing base class for snapshot test cases.

    It setup a temporary directory as the root for all snapshots.
    """

    def setUp(self):
        """
        """
        super(TestCaseSnapshotPath, self).setUp()

        # The root of all snapshots. Like a "backup destination".
        # e.g. '/tmp/tmpf3mdnt8l'
        self.tmpDir = TemporaryDirectory()

        self.cfg.dict['profile1.snapshots.path'] = self.tmpDir.name

        # The full snapshot path combines the backup destination root
        # directory with hostname, username and the profile (backupjob) ID.
        # e.g. /tmp/tmpf3mdnt8l/backintime/test-host/test-user/1
        self.snapshotPath = self.cfg.snapshotsFullPath()

    def tearDown(self):
        """
        """
        super(TestCaseSnapshotPath, self).tearDown()

        self.tmpDir.cleanup()


class SnapshotsTestCase(TestCaseSnapshotPath):
    """Testing base class for snapshot testing unittest classes.

    Create the snapshot path and a :py:class:`Snapshot` instance of it.
    """

    def setUp(self):
        """
        """
        super(SnapshotsTestCase, self).setUp()

        # e.g. /tmp/tmpf3mdnt8l/backintime/test-host/test-user/1
        os.makedirs(self.snapshotPath)
        self.sn = snapshots.Snapshots(self.cfg)

        # use a tmp-file for flock because test_flockExclusive would deadlock
        # otherwise if a regular snapshot is running in background
        self.sn.GLOBAL_FLOCK = TMP_FLOCK.name


class SnapshotsWithSidTestCase(SnapshotsTestCase):
    """Testing base class creating a concrete SID object.

    Backup content (folder and file) is created in that snapshot like the
    snapshot was taken in the past.
    """

    def setUp(self):
        """
        """
        super(SnapshotsWithSidTestCase, self).setUp()

        # A snapthos "data object"
        self.sid = snapshots.SID('20151219-010324-123', self.cfg)

        # Create test files and folders
        # e.g. /tmp/tmp9rstvbsx/backintime/test-host/test-user/1/
        # 20151219-010324-123/backup/foo/bar
        # 20151219-010324-123/backup/foo/bar/baz

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
        # self.tmpDir = TemporaryDirectory(prefix='bit_test_', suffix=' with blank')
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
    """Testing base class for test cases using a snapshot and SSH.

    BUHTZ 2022-10-09: Seems exactly the same then `SnapshotsTestCase` except
    the inheriting class.
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
    """Testing base class for test cases using an existing snapshot (SID)
    and SSH.

    BUHTZ 2022-10-09: Seems exactly the same then `SnapshotsWithSidTestCase`
    except the inheriting class.
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
