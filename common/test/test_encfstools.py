# SPDX-FileCopyrightText: © 2016-2022 Taylor Raack
# SPDX-FileCopyrightText: © 2016-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


class TestEncFS_mount(generic.TestCase):

    # encrypted filesystem verification seems quite complex to unit test at the
    # moment, partially due to UI elements being created and expecting input,
    # without tests for pre-prepared unit test fixture data

    # TODO - perhaps pass encrypted fs class object which can be queried for
    # passwords when necessary (so runtime can pass UI classes which can bring
    # up actual UI elements and return credentials or unit tests can pass
    # objects which can return hard coded passwords to prevent UI pop-ups in
    # Travis)

    # TODO - then - code actual tests and remove this one
    def setUp(self):
        super(TestEncFS_mount, self).setUp()

    def test_dummy(self):
        self.assertTrue(True)
