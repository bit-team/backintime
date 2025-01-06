# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about statefile module."""
import unittest
from pathlib import Path
from unittest import mock
import statedata
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut


class TestSingleton(unittest.TestCase):
    def setUp(self):
        # Clean up all instances
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def test_identity(self):
        """Identical identiy."""
        one = statedata.StateData()
        two = statedata.StateData()

        self.assertEqual(id(one), id(two))

    def test_content(self):
        """Identical values."""
        one = statedata.StateData()
        two = statedata.StateData()

        one['foobar'] = 7

        self.assertEqual(one, two)
