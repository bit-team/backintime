import sys
import inspect
import io
import unittest
import unittest.mock as mock
import tempfile
import stat
from contextlib import redirect_stdout, redirect_stderr
from ast import literal_eval
from pathlib import Path

# This workaround will become obsolet when migrating to src-layout
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / 'plugins'))

import pluginmanager
from config import Config
from snapshots import Snapshots
from usercallbackplugin import UserCallbackPlugin


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

    @classmethod
    def _create_user_callback_file(cls, parent_path):
        content = inspect.cleandoc('''
            #!/usr/bin/env python3
            import sys
            print(sys.argv[1:])
        ''')

        callback_fp = parent_path / 'user-callback'
        callback_fp.write_text(content, 'utf-8')
        callback_fp.chmod(stat.S_IRWXU)

    # Name of folder with files to backup.
    NAME_SOURCE = 'src'
    # Name of folder where snapshots (backups) are stored in.
    NAME_DESTINATION = 'dest'

    @classmethod
    def _extract_callback_responses(cls, output):
        """Extract response of user-callback script out of log output.

        See https://github.com/bit-team/user-callback for documentation about
        user-callback and the response codes.

        Example ::
            # Raw output
            INFO: user-callback returned '['1', 'Main profile', '2']'
            INFO: Something else
            INFO: user-callback returned '['1', 'Main profile', '8']'

            # Result in a two entry list
            [
                ['1', 'Main profile', '2']
                ['1', 'Main profile', '8']
            ]

        Returns:
            A list of response values as lists. First entry is profile, second
            is profile id, third is reason code. If available further entries
            could be contained.
        """

        if isinstance(output, str):
            output = output.splitlines()

        # only log lines related to user-callback
        response_lines = filter(
            lambda line: 'user-callback returned' in line, output)

        callback_responses = []

        for line in response_lines:

            callback_responses.append(
                literal_eval(line[line.index("'")+1:line.rindex("'")])
            )

        # Workaround: Cast profile-id and response-code to integers
        for idx in range(len(callback_responses)):
            callback_responses[idx][0] = int(callback_responses[idx][0])
            callback_responses[idx][2] = int(callback_responses[idx][2])

        return callback_responses

    @classmethod
    def _create_source_and_destination_folders(cls, parent_path):
        # Folder to backup
        src_path = parent_path / cls.NAME_SOURCE
        src_path.mkdir()

        # Files and folders as backup content
        (src_path / 'one').write_bytes(b'0123')
        (src_path / 'subfolder').mkdir()
        (src_path / 'subfolder' / 'two').write_bytes(b'4567')

        # Folder to store backup
        dest_path = parent_path / cls.NAME_DESTINATION
        dest_path.mkdir()

    @classmethod
    def _create_config_file(cls, parent_path):
        """Minimal config file"""
        # pylint: disable-next=R0801
        cfg_content = inspect.cleandoc('''
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
        ''')

        cfg_content = cfg_content.format(
            rootpath=parent_path,
            source=cls.NAME_SOURCE,
            destination=cls.NAME_DESTINATION
        )

        # config file location
        config_fp = parent_path / 'config_path' / 'config'
        config_fp.parent.mkdir()
        config_fp.write_text(cfg_content, 'utf-8')

        return config_fp

    def setUp(self):
        """Setup a local snapshot profile including a user-callback"""
        # cleanup() happens automatically
        self._temp_dir = tempfile.TemporaryDirectory(prefix='bit.')
        # Workaround: tempfile and pathlib not compatible yet
        self.temp_path = Path(self._temp_dir.name)

        self._create_source_and_destination_folders(self.temp_path)
        self.config_fp = self._create_config_file(self.temp_path)
        self._create_user_callback_file(self.config_fp.parent)

        # Reset this instance because it is not isolated between tests.
        Config.PLUGIN_MANAGER = pluginmanager.PluginManager()

    def test_local_snapshot(self):
        """User-callback response while doing a local snapshot"""

        config = Config(
            config_path=str(self.config_fp),
            data_path=str(self.temp_path / '.local' / 'share')
        )

        full_snapshot_path = config.snapshotsFullPath()
        Path(full_snapshot_path).mkdir(parents=True)

        snapshot = Snapshots(config)

        # DevNote : Because BIT don't use Python's logging module there is
        # no way to use assertLogs(). Current solution is to capture
        # stdout/stderr.
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            # Result is inverted. 'True' means there was an error.
            self.assertFalse(snapshot.backup())

        # Empty STDOUT output
        self.assertFalse(stdout.getvalue())

        responses = self._extract_callback_responses(stderr.getvalue())

        # Number of responses
        self.assertEqual(5, len(responses))

        # Test Name and ID
        self.assertEqual(
            {(1, 'Main profile')},
            # de-duplicate (using set() )by first two elements in each entry
            {(entry[0], entry[1]) for entry in responses}
        )

        # Order of response codes
        self.assertEqual(
            [
                7,  # Mount
                1,  # Backup begins
                3,  # New snapshot was taken
                2,  # Backup ends
                8,  # Unmount
            ],
            [entry[2] for entry in responses]
        )
