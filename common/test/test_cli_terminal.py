# SPDX-FileCopyrightText: © 2026 Back In Time Team
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests for the terminal size used by the interactive snapshot selection.

Issue #2600: ``backintime restore`` without a (valid) snapshot ID asks the
user to choose one and crashed with ``SystemError: buffer overflow`` on
Python 3.14. The same code path crashed with ``OSError`` if stdin was not a
terminal (e.g. cron or a pipe) and with ``ZeroDivisionError`` if the terminal
reported a size of zero.
"""
import contextlib
import errno
import io
import os
import sys
import unittest
from unittest import mock
import tools
tools.initiate_translation(None)
import cli  # noqa: E402

try:
    import fcntl
    import pty
    import struct
    import termios
except ImportError:  # not POSIX
    fcntl = None

# No size information from the environment
NO_SIZE_ENV = {'COLUMNS': '', 'LINES': ''}


def _without_size_env():
    """The environment variables COLUMNS and LINES must not interfere."""
    env = {k: v for k, v in os.environ.items() if k not in NO_SIZE_ENV}

    return mock.patch.dict(os.environ, env, clear=True)


class TerminalSize(unittest.TestCase):
    """cli.terminalSize() returns ``[lines, columns]``."""

    def test_size_of_the_terminal(self):
        with _without_size_env(), \
                mock.patch('os.get_terminal_size',
                           return_value=os.terminal_size((100, 30))):
            self.assertEqual(cli.terminalSize(), [30, 100])

    def test_environment_is_respected(self):
        with mock.patch.dict(os.environ, {'COLUMNS': '120', 'LINES': '40'}):
            self.assertEqual(cli.terminalSize(), [40, 120])

    def test_stdin_is_not_a_terminal(self):
        """E.g. cron or a pipe: ENOTTY must not end in a crash."""
        with _without_size_env(), \
                mock.patch('os.get_terminal_size',
                           side_effect=OSError(errno.ENOTTY, 'not a tty')):
            self.assertEqual(cli.terminalSize(), [24, 80])

    def test_unknown_size_is_not_zero(self):
        """Terminals (e.g. in containers) may report a size of 0x0."""
        with _without_size_env(), \
                mock.patch('os.get_terminal_size',
                           return_value=os.terminal_size((0, 0))):
            self.assertEqual(cli.terminalSize(), [24, 80])

    @unittest.skipIf(fcntl is None, 'POSIX only')
    def test_reported_failure_2600(self):
        """Python 3.14 raises SystemError if the buffer of ioctl() is too
        small. The size must not depend on that call at all."""
        with _without_size_env(), \
                mock.patch.object(
                    fcntl, 'ioctl',
                    side_effect=SystemError('buffer overflow')):
            size = cli.terminalSize()

        self.assertEqual(len(size), 2)
        self.assertTrue(all(isinstance(x, int) and x > 0 for x in size))

    @unittest.skipIf(fcntl is None, 'POSIX only')
    def test_real_pseudo_terminal(self):
        """A real (pseudo) terminal of size 24 x 132 and one with size 0."""
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)

        class FakeStdout:
            @staticmethod
            def fileno():
                return slave

        with _without_size_env(), \
                mock.patch.object(sys, '__stdout__', FakeStdout()):
            fcntl.ioctl(slave, termios.TIOCSWINSZ,
                        struct.pack('hhhh', 24, 132, 0, 0))
            self.assertEqual(cli.terminalSize(), [24, 132])

            fcntl.ioctl(slave, termios.TIOCSWINSZ,
                        struct.pack('hhhh', 0, 0, 0, 0))
            self.assertEqual(cli.terminalSize(), [24, 80])


class SelectSnapshot(unittest.TestCase):
    """cli.selectSnapshot() with the terminal sizes of TerminalSize."""

    SNAPSHOTS = ('20260101-000000-123', '20260102-000000-123',
                 '20260103-000000-123')

    def select(self, snapshot_id=None, answers=('1',)):
        """Returns the selected snapshot and the printed output."""
        out = io.StringIO()
        cfg = mock.MagicMock()

        with contextlib.redirect_stdout(out), \
                mock.patch('builtins.input', side_effect=list(answers)):
            result = cli.selectSnapshot(
                list(self.SNAPSHOTS), cfg, snapshot_id=snapshot_id)

        return result, out.getvalue()

    def test_index_as_snapshot_id(self):
        """Valid existing usage: ``backintime restore 2``. No terminal
        size is needed."""
        with mock.patch.object(
                cli, 'terminalSize', side_effect=AssertionError('unused')):
            result, _out = self.select(snapshot_id='2')

        self.assertEqual(result, self.SNAPSHOTS[2])

    def test_choose_from_list(self):
        """Valid existing usage: No ID given, the user picks one."""
        with mock.patch.object(cli, 'terminalSize', return_value=[24, 80]):
            result, out = self.select()

        self.assertEqual(result, self.SNAPSHOTS[1])
        self.assertIn("SnapshotID's:", out)

        for snapshot in self.SNAPSHOTS:
            self.assertIn(snapshot, out)

    def test_wide_terminal_uses_several_columns(self):
        """Three entries (26 characters each) fit into one line of 80
        characters. No regression of the layout."""
        with mock.patch.object(cli, 'terminalSize', return_value=[24, 80]):
            _result, out = self.select()

        lines = [line for line in out.splitlines()
                 if self.SNAPSHOTS[0] in line]
        self.assertEqual(len(lines), 1)
        self.assertIn(self.SNAPSHOTS[2], lines[0])

    def test_narrow_terminal(self):
        """Less than 25 columns resulted in zero columns, and in a
        ZeroDivisionError."""
        for columns in (0, 1, 24, 25, 26):
            with self.subTest(columns=columns), \
                    mock.patch.object(
                        cli, 'terminalSize', return_value=[24, columns]):
                result, out = self.select()

                self.assertEqual(result, self.SNAPSHOTS[1])

                for snapshot in self.SNAPSHOTS:
                    self.assertIn(snapshot, out)

    @unittest.skipIf(fcntl is None, 'POSIX only')
    def test_reported_failure_2600(self):
        """``backintime restore`` without an ID on Python 3.14."""
        with _without_size_env(), \
                mock.patch.object(
                    fcntl, 'ioctl',
                    side_effect=SystemError('buffer overflow')):
            result, out = self.select()

        self.assertEqual(result, self.SNAPSHOTS[1])
        self.assertIn(self.SNAPSHOTS[0], out)

    def test_invalid_index_falls_back_to_the_list(self):
        """Invalid input is still answered with the list and a prompt."""
        with mock.patch.object(cli, 'terminalSize', return_value=[24, 80]):
            result, out = self.select(snapshot_id='99')

        self.assertEqual(result, self.SNAPSHOTS[1])
        self.assertIn('Invalid SnaphotID index: 99', out)


if __name__ == '__main__':
    unittest.main()
