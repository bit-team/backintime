# Back In Time
# Copyright (C) 2016 Taylor Raack
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
# You should have received a copy of the GNU General Public Licensealong
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import subprocess
import sys
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TestBackInTime(generic.TestCase):

# main tests for backintime

    def setUp(self):
        super(TestBackInTime, self).setUp()

    def test_quiet_mode(self):
        self.assertEquals("", subprocess.getoutput("python3 backintime.py --quiet"))
