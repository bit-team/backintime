# Back In Time
# Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common/'))

import configfile


class TestConfigFile(unittest.TestCase):
    '''Tests for the ConfigFile class in the configfile module'''
    def test_save(self):
        '''Saves the config file  in the tmp direcory '''
        filename = os.path.join(tempfile.gettempdir(), "test_save.cfg")
        print(filename)
        cf = configfile.ConfigFile()
        cf.save(filename)
        self.assertTrue(os.path.exists(filename))
        os.remove(filename)

    def test_load(self):
        '''
        ConfigFile should be able to load its content from a previously
        saved ConfigFile object.
        '''
        config_filename = os.path.join(
            tempfile.gettempdir(),
            "test_load.cfg")
        original_cf = configfile.ConfigFile()
        key = "config_key"
        value = "config_value"
        original_cf.set_str_value(key, value)
        original_cf.save(config_filename)

        cf = configfile.ConfigFile()
        cf.load(config_filename)

        self.assertEqual(len(cf.get_keys()), len(original_cf.get_keys()))
        for k in original_cf.get_keys():
            with self.subTest(k = k):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'k = %s' %k
                self.assertTrue(cf.has_value(k), msg)

        os.remove(config_filename)

if __name__ == '__main__':
    unittest.main()
