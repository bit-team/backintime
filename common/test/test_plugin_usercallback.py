import sys
import inspect
import tempfile
from pathlib import Path
import stat
import io
from datetime import datetime
import unittest
import unittest.mock as mock
import json
from contextlib import redirect_stdout, redirect_stderr

# This workaround will become obsolet when migrating to src-layout
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / 'plugins'))
import logger
from config import Config
from snapshots import Snapshots, SID
from usercallbackplugin import UserCallbackPlugin

# TODO
# Create a surrogate instance of config.Config
# I assume it is well usable for some other tests, too.
# But it will be always a workaround until the code is cleaner.


class UserCallback(unittest.TestCase):
    """Simple test related to to UserCallbackPlugin class.

    Dev note (buhtz, 2024-02-08): Test value is low because they depend on
    implementation and are not robust against refactoring the productive code.

    Some observations and suggestions:
     - Rename method UserCallbackPlugin.init()
     - Make UserCallbackPlugin.callback() private
     - UserCallbackPlugin.callback() : Encapsulating the Popen() part would
       improve the mocking.
     - Unit tests about logger output. But migrate "logger" to Python's
       inbuild "logging" module first.
    """
    def _generic_called_with(self, the_step, reason, *args):
        sut = UserCallbackPlugin()
        sut.config = Config()
        sut.script = ''

        mock_name = 'usercallbackplugin.UserCallbackPlugin.callback'
        with mock.patch(mock_name) as func_callback:
            the_step(sut, *args)
            func_callback.assert_called_once()
            func_callback.assert_called_with(reason, *args)

    def test_reason_processBegin(self):
        self._generic_called_with(UserCallbackPlugin.processBegin, '1')

    def test_reason_processEnd(self):
        self._generic_called_with(UserCallbackPlugin.processEnd, '2')

    def test_reason_processnewSnapshot(self):
        self._generic_called_with(UserCallbackPlugin.newSnapshot, '3', 'id1', 'path')

    def test_reason_error(self):
        sut = UserCallbackPlugin()
        sut.config = Config()
        sut.script = ''

        mock_name = 'usercallbackplugin.UserCallbackPlugin.callback'

        # with error message
        with mock.patch(mock_name) as func_callback:
            sut.error('code1', 'message')
            func_callback.assert_called_once()
            func_callback.assert_called_with('4', 'code1', 'message')

        # no error message
        with mock.patch(mock_name) as func_callback:
            sut.error('code2', None)
            func_callback.assert_called_once()
            func_callback.assert_called_with('4', 'code2')

    def test_reason_appStart(self):
        self._generic_called_with(UserCallbackPlugin.appStart, '5')

    def test_reason_appExit(self):
        self._generic_called_with(UserCallbackPlugin.appExit, '6')

    def test_reason_mount(self):
        sut = UserCallbackPlugin()
        sut.config = Config()
        sut.script = ''

        mock_name = 'usercallbackplugin.UserCallbackPlugin.callback'

        # No profileID
        with mock.patch(mock_name) as func_callback:
            sut.mount()
            func_callback.assert_called_once()
            func_callback.assert_called_with('7', profileID=None)

        # With profileID
        with mock.patch(mock_name) as func_callback:
            sut.mount('123')
            func_callback.assert_called_once()
            func_callback.assert_called_with('7', profileID='123')

    def test_reason_unmount(self):
        sut = UserCallbackPlugin()
        sut.config = Config()
        sut.script = ''

        mock_name = 'usercallbackplugin.UserCallbackPlugin.callback'

        # No profileID
        with mock.patch(mock_name) as func_callback:
            sut.unmount()
            func_callback.assert_called_once()
            func_callback.assert_called_with('8', profileID=None)

        # With profileID
        with mock.patch(mock_name) as func_callback:
            sut.unmount('987')
            func_callback.assert_called_once()
            func_callback.assert_called_with('8', profileID='987')


class SystemTest(unittest.TestCase):
    """Full backup run and parsing the log output for the expected
    user-callback returns in correct order.

    Create and use your own config file and take it over via `--config`
    option. Place your own user-callback script in the same folder as
    this config file.
    """

    # Use inspect.cleandoc() or textwrap.dedent() on it.
    # Credits: https://stackoverflow.com/a/48112903/4865723
    user_callback_content = '''
        #!/usr/bin/env python3
        import sys
        print(f'Profile: "{sys.argv[2]}" ({sys.argv[1]}) '
              f' Reason: {sys.argv[3]}')
        if len(sys.argv) > 4:
            print(f'{sys.argv[4:]=}')
    '''

    config_content = '''
        config.version=6
        profile1.snapshots.include.1.type=0
        profile1.snapshots.include.1.value={rootpath}/{source}
        profile1.snapshots.include.size=1
        profile1.snapshots.no_on_battery=false
        profile1.snapshots.notify.enabled=true
        profile1.snapshots.path={rootpath}/{destination}
        profile1.snapshots.path.host=test-host
        profile1.snapshots.path.profile=1
        profile1.snapshots.path.user=test-user
        profile1.snapshots.preserve_acl=false
        profile1.snapshots.preserve_xattr=false
        profile1.snapshots.remove_old_snapshots.enabled=true
        profile1.snapshots.remove_old_snapshots.unit=80
        profile1.snapshots.remove_old_snapshots.value=10
        profile1.snapshots.rsync_options.enabled=false
        profile1.snapshots.rsync_options.value=
        profiles.version=1
    '''

    # Name of folder with files to backup.
    NAME_SOURCE = 'snapshotsource'
    # Name of folder where snapshots (backups) are stored in.
    NAME_DESTINATION = 'snapshotdestination'

    def setUp(self):
        # cleanup() happens automatically
        self.temp_dir = tempfile.TemporaryDirectory(prefix='bit.')

        # Workaround: tempfile and pathlib not compatible yet
        temp_path = Path(self.temp_dir.name)

        # Create source and destination backup folders
        src_path = temp_path / self.NAME_SOURCE
        src_path.mkdir()
        (src_path / 'one').write_bytes(b'0123')
        (src_path / 'subfolder').mkdir()
        (src_path / 'subfolder' / 'two').write_bytes(b'4567')
        dest_path = temp_path / self.NAME_DESTINATION
        dest_path.mkdir()

        # Unclear what this is. Used in Config.__init__()
        self.data_path = temp_path / 'data_path'

        # folder for config file
        self.config_fp = Path(temp_path) / 'config_path' / 'config'
        self.config_fp.parent.mkdir()

        # create config file
        cfg_content = inspect.cleandoc(self.config_content).format(
            rootpath=self.temp_dir.name,
            source=self.NAME_SOURCE,
            destination=self.NAME_DESTINATION
        )
        self.config_fp.write_text(cfg_content, 'utf-8')

        # create user-callback script
        callback_content = inspect.cleandoc(self.user_callback_content)
        callback_fp = self.config_fp.parent / 'user-callback'
        callback_fp.write_text(callback_content, 'utf-8')
        callback_fp.chmod(stat.S_IRWXU)

        # # DEBUG
        # print(f'\n{self.temp_dir=}')
        # print(list(Path(self.temp_dir.name).rglob('*')))

    def test_foobar(self):
        """Try it..."""

        # Initialize logging
        # logger.APP_NAME = 'BIT_unittest'
        # logger.openlog()
        # # --- TestCase.setUp() ---
        # logger.DEBUG = True  # '-v' in sys.argv

        # # ?
        # self.run = False

        # --- TestCaseCfg.setUp() ---
        config = Config(
            config_path=str(self.config_fp),
            data_path=str(self.data_path)
        )

        # # mock notifyplugin to suppress notifications
        # patcher = patch('notifyplugin.NotifyPlugin.message')
        # self.mockNotifyPlugin = patcher.start()
        # config.PLUGIN_MANAGER.load(cfg=config)

        # The full snapshot path combines the backup destination root
        # directory with hostname, username and the profile (backupjob) ID.
        # e.g. /tmp/tmpf3mdnt8l/backintime/test-host/test-user/1
        full_snapshot_path = config.snapshotsFullPath()
        Path(full_snapshot_path).mkdir(parents=True)

        snapshot = Snapshots(config)

        # # use a tmp-file for flock because test_flockExclusive would deadlock
        # # otherwise if a regular snapshot is running in background
        # self.sn.GLOBAL_FLOCK = TMP_FLOCK.name

        # DevNote : Because BIT don't use Python's logging module there is
        # no way to use assertLogs(). Current solution is to capture
        # stdout/stderr.

        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):

            # result = snapshot.takeSnapshot(
            #     # Snapshot identifier for this snapshot to created
            #     sid=SID(datetime.now(), config),
            #     # Start time
            #     now=datetime.now(),
            #     # Folders to include
            #     include_folders=config.include()
            # )
            result = snapshot.backup()

        print(f'{result=}')

        print(f'---- redirected STDERR ---\n{stderr.getvalue()}')
        print(f'---- redirected STDOUT ---\n{stdout.getvalue()}')
