# SPDX-FileCopyrightText: © 2026 goingforstudying-ctrl
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about the cli module."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from cli import _fix_enum_values
from bitbase import TimeUnit


class FixEnumValues(unittest.TestCase):
    """_fix_enum_values() rewrites legacy enum names in the config file."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / 'config'

    def test_missing_file_is_ignored(self):
        """A not existing config file is ignored."""
        _fix_enum_values(self.path, TimeUnit)

        self.assertFalse(self.path.exists())

    def test_legacy_enum_values_are_fixed(self):
        """Legacy enum names are replaced by their integer values."""
        self.path.write_text(
            'profile1.name=Main\n'
            'profile1.schedule.time=TimeUnit.YEAR\n',
            encoding='utf-8')

        _fix_enum_values(self.path, TimeUnit)

        self.assertEqual(
            self.path.read_text(encoding='utf-8'),
            'profile1.name=Main\n'
            'profile1.schedule.time=80\n')

    def test_clean_file_is_not_rewritten(self):
        """A config without legacy enum values is left on disk untouched.

        Regression test for #2638: an unconditional write truncates the
        file first and races with concurrent readers.
        """
        self.path.write_text(
            'profile1.name=Main\n'
            'profile1.schedule.time=20\n',
            encoding='utf-8')

        with mock.patch('tools.atomic_write_text') as mock_write:
            _fix_enum_values(self.path, TimeUnit)

        mock_write.assert_not_called()
        self.assertEqual(
            self.path.read_text(encoding='utf-8'),
            'profile1.name=Main\n'
            'profile1.schedule.time=20\n')
