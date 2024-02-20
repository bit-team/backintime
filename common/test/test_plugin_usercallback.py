import sys
import pathlib
import unittest
import unittest.mock as mock
import json

# This workaround will become obsolet when migrating to src-layout
sys.path.append(str(pathlib.Path(__file__).parent))
sys.path.append(str(pathlib.Path(__file__).parent / 'plugins'))
import config
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
        sut.config = config.Config()
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
        sut.config = config.Config()
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
        sut.config = config.Config()
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
        sut.config = config.Config()
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
    """Full run backup and parsing the log output for the expected
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
        import pathlib
        print('I'*200)
        print(f'{pathlib.Path.cwd()=}')
        print(f'{sys.argv=}')
    '''
