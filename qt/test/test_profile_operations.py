# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
# pylint: disable=C0115, C0116
"""Tests about ProfileOperations class"""
# pylint: disable=wrong-import-position
import unittest
from unittest.mock import Mock
# Workaround: gettext isn't initialized
import builtins
builtins._ = lambda txt: txt
from profile_operations import ProfileOperations  # noqa: E402


class AddInclude(unittest.TestCase):
    def test_no_duplicates(self):
        """Add dir and file"""
        mock_config = Mock()
        mock_config.include.return_value = [('A', 0), ('B', 1)]

        sut = ProfileOperations(1, mock_config)

        duplicates = sut.add_include(['C', 'D'])

        # return value
        self.assertEqual(duplicates, [])
        # first positional call argument
        self.assertEqual(
            [val for val, _ in mock_config.setInclude.call_args[0][0]],
            ['A', 'B', 'C', 'D']
        )

    def test_with_duplicates(self):
        """Add still existing dir/file"""
        mock_config = Mock()
        mock_config.include.return_value = [('A', 0), ('B', 1)]

        sut = ProfileOperations(1, mock_config)

        duplicates = sut.add_include(['C', 'B'])

        # return value
        self.assertEqual(duplicates, ['B'])
        # first positional call argument
        self.assertEqual(
            [val for val, _ in mock_config.setInclude.call_args[0][0]],
            ['A', 'B', 'C']
        )


class AddExclude(unittest.TestCase):
    def test_no_duplicates(self):
        mock_config = Mock()
        mock_config.exclude.return_value = ['A', 'B']

        sut = ProfileOperations(1, mock_config)

        duplicates = sut.add_exclude(['C', 'D'])

        # return value
        self.assertEqual(duplicates, [])
        # first positional call argument
        self.assertEqual(
            mock_config.setExclude.call_args[0][0],
            ['A', 'B', 'C', 'D']
        )

    def test_with_duplicates(self):
        mock_config = Mock()
        mock_config.exclude.return_value = ['A', 'B']

        sut = ProfileOperations(1, mock_config)

        duplicates = sut.add_exclude(['C', 'B'])

        # return value
        self.assertEqual(duplicates, ['B'])
        # first positional call argument
        self.assertEqual(
            mock_config.setExclude.call_args[0][0],
            ['A', 'B', 'C']
        )
