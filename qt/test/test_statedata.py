# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about statefile module."""
# pylint: disable=wrong-import-position,wrong-import-order
import unittest
from pathlib import Path
from qttools_path import register_backintime_path
register_backintime_path('common')
import statedata  # noqa: E402


class IsSingleton(unittest.TestCase):
    """StateData instance is a singleton."""

    @classmethod
    def tearDownClass(cls):
        # Delete existing StateData instance
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def setUp(self):
        # Clean up all instances
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def test_identity(self):
        """Identical identity."""
        one = statedata.StateData()
        two = statedata.StateData()

        self.assertEqual(id(one), id(two))

    def test_content(self):
        """Identical values."""
        one = statedata.StateData()
        two = statedata.StateData()

        one['foobar'] = 7

        self.assertEqual(one, two)


class Properties(unittest.TestCase):
    """Property access without errors."""

    @classmethod
    def tearDownClass(cls):
        # Delete existing StateData instance
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def setUp(self):
        # Delete existing StateData instance
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def test_read_empty_global(self):
        """Read properties from empty state data"""
        sut = statedata.StateData()

        self.assertEqual(sut.msg_release_candidate, None)
        self.assertEqual(sut.msg_encfs_global, False)
        self.assertEqual(sut.mainwindow_show_hidden, False)
        self.assertEqual(sut.files_view_sorting, (0, 0))
        self.assertEqual(sut.mainwindow_main_splitter_widths, (150, 450))
        self.assertEqual(sut.mainwindow_second_splitter_widths, (150, 300))

        with self.assertRaises(KeyError):
            # pylint: disable=pointless-statement
            _useless = sut.mainwindow_coords
            _useless = sut.mainwindow_dims
            _useless = sut.logview_dims
            _useless = sut.files_view_col_widths

    def test_last_path_default_is_root(self):
        """The last_path is / by default"""
        sut = statedata.StateData()
        profile = sut.profile(42)
        self.assertEqual(profile.last_path, Path('/'))

    def test_profile_not_exist(self):
        """Profile does not exists."""
        sut = statedata.StateData()
        profile = sut.profile(42)

        with self.assertRaises(KeyError):
            # pylint: disable=pointless-statement
            _useless = profile.include_sorting
