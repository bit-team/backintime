# Back In Time
# Copyright (C) 2008-2017 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import sys
import tempfile
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import configfile
import snapshots


class TestSnapShots(unittest.TestCase):

    def test_valid_config(self):
        '''
        Test if the config file use by the snapshots is correctly
        initialized if the function is fed a valid ConfigFile object.
        '''
        cf = configfile.ConfigFile()
        sp = snapshots.Snapshots(cf)
        self.assertEqual(sp.config, cf)

    def test_None_as_config(self):
        '''
        Test if the config file use by the snapshots is correctly
        initialized if the function is fed None as the ConfigFile.
        '''
        sp = snapshots.Snapshots(None)
        self.assertIsInstance(sp.config, configfile.ConfigFile)

if __name__ == '__main__':
    unittest.main()
