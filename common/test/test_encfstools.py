# Back In Time
# Copyright (C) 2016-2021 Taylor Raack, Germar Reitze
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TestEncFS_mount(generic.TestCase):

# encrypted filesystem verification seems quite complex to unit test at the moment, partially due to
# UI elements being created and expecting input, without tests for pre-prepared unit test fixture data

# TODO - perhaps pass encrypted fs class object which can be queried for passwords when necessary (so runtime
# can pass UI classes which can bring up actual UI elements and return credentials or unit tests can pass
# objects which can return hard coded passwords to prevent UI pop-ups in Travis)

# TODO - then - code actual tests and remove this one
    def setUp(self):
        super(TestEncFS_mount, self).setUp()

    def test_dummy(self):
        self.assertTrue(True)
