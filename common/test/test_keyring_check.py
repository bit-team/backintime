# SPDX-FileCopyrightText: © 2026 Back In Time Team
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests for the keyring check done while importing the module "tools".

Issue #2438: A keyring backend forced in ``keyringrc.cfg`` that can not be
loaded (e.g. KWallet without a D-Bus session as it is the case when started
via cron) raised an exception while ``tools`` was imported. The application
ended before anything was logged.
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import tools
tools.initiate_translation(None)

try:
    import keyring
    import keyring.backends.chainer
    import keyring.backends.fail
except ImportError:
    keyring = None

COMMON_DIR = pathlib.Path(__file__).resolve().parent.parent

# The module tools imports keyring only if it is not running as root
KEYRING_USABLE = keyring is not None and tools.is_keyring_available
SKIP_REASON = 'Package "keyring" is not available (or running as root)'


@unittest.skipUnless(KEYRING_USABLE, SKIP_REASON)
class KeyringCheck(unittest.TestCase):
    """tools._check_if_keyring_is_supported() with mocked backends."""

    def check(self, **kwargs):
        with mock.patch.object(tools.keyring, 'get_keyring', **kwargs):
            return tools._check_if_keyring_is_supported()

    def test_backend_fails_to_load(self):
        """The reported failure: forced backend can not be loaded."""
        with mock.patch.object(tools.logger, 'warning') as warn:
            result = self.check(side_effect=RuntimeError(
                'Unable to autolaunch a dbus-daemon without a $DISPLAY'))

        self.assertIs(result, False)
        warn.assert_called_once()
        self.assertIn('dbus-daemon', warn.call_args[0][0])

    def test_any_error_type_is_handled(self):
        """The backend can raise whatever it wants."""
        for error in (RuntimeError('x'), ImportError('x'), OSError('x'),
                      ValueError('x'), KeyError('x'), AttributeError('x')):
            with self.subTest(error=type(error).__name__):
                self.assertIs(self.check(side_effect=error), False)

    def test_supported_backend(self):
        """No regression: A supported backend is still detected."""
        chainer = keyring.backends.chainer.ChainerBackend()

        self.assertIs(self.check(return_value=chainer), True)

    def test_unsupported_backend(self):
        """No regression: An unsupported backend is still not usable."""
        self.assertIs(
            self.check(return_value=keyring.backends.fail.Keyring()), False)

    def test_keyring_not_installed(self):
        """No regression: Package is missing."""
        with mock.patch.object(tools, 'is_keyring_available', False):
            self.assertIs(tools._check_if_keyring_is_supported(), False)


@unittest.skipUnless(KEYRING_USABLE, SKIP_REASON)
class ImportWithForcedBackend(unittest.TestCase):
    """The reported failure end to end: ``import tools`` in a new process
    like cron does it. No display and no D-Bus session. The user config
    forces the KWallet backend."""

    CONFIG = (
        '[backend]\n'
        'default-keyring=keyring.backends.kwallet.DBusKeyring\n'
    )

    def run_import(self, home: pathlib.Path) -> subprocess.CompletedProcess:
        env = {
            'HOME': str(home),
            'XDG_CONFIG_HOME': str(home / '.config'),
            'PATH': os.environ.get('PATH', ''),
            'PYTHONDONTWRITEBYTECODE': '1',
            'LANG': 'C',
        }
        code = (
            'import tools\n'
            'print("KEYRING_SUPPORTED=%s" % tools.KEYRING_SUPPORTED)\n'
        )

        return subprocess.run(
            [sys.executable, '-c', code],
            env=env, cwd=str(COMMON_DIR), capture_output=True, text=True,
            timeout=120, check=False)

    def test_forced_backend_does_not_stop_the_application(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            config = home / '.config' / 'python_keyring' / 'keyringrc.cfg'
            config.parent.mkdir(parents=True)
            config.write_text(self.CONFIG, encoding='utf-8')

            proc = self.run_import(home)

        self.assertEqual(proc.returncode, 0, proc.stderr[-1500:])
        self.assertIn('KEYRING_SUPPORTED=False', proc.stdout)

    def test_without_config_file(self):
        """Valid existing usage: No keyringrc.cfg at all."""
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_import(pathlib.Path(tmp))

        self.assertEqual(proc.returncode, 0, proc.stderr[-1500:])
        self.assertRegex(proc.stdout, r'KEYRING_SUPPORTED=(True|False)')


if __name__ == '__main__':
    unittest.main()
