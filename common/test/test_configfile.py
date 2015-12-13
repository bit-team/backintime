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
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import configfile


class TestConfigFile(unittest.TestCase):
    '''Tests for the ConfigFile class in the configfile module'''
    def test_save(self):
        '''Saves the config file  in the tmp direcory '''
        filename = os.path.join(tempfile.gettempdir(), "test_save.cfg")
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
                self.assertEqual(original_cf.get_str_value(k), cf.get_str_value(k))

        os.remove(config_filename)

    def test_has_value(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'bar'}
        self.assertTrue(cfg.has_value('foo'))
        self.assertFalse(cfg.has_value('non_existend_key'))

    ############################################################################
    ###                               str_value                              ###
    ############################################################################

    def test_get_str_value(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'bar'}
        self.assertEqual(cfg.get_str_value('foo', 'default'), 'bar')

    def test_get_str_value_default(self):
        cfg = configfile.ConfigFile()
        self.assertEqual(cfg.get_str_value('non_existend_key', 'default'), 'default')

    def test_set_str_value(self):
        cfg = configfile.ConfigFile()
        cfg.set_str_value('foo', 'bar')
        self.assertEqual(cfg.dict, {'foo': 'bar'})

    ############################################################################
    ###                               int_value                              ###
    ############################################################################

    def test_get_int_value(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': '11'}
        self.assertEqual(cfg.get_int_value('foo', 22), 11)

    def test_get_int_value_default(self):
        cfg = configfile.ConfigFile()
        self.assertEqual(cfg.get_int_value('non_existend_key', 33), 33)

    def test_set_int_value(self):
        cfg = configfile.ConfigFile()
        cfg.set_int_value('foo', 44)
        self.assertEqual(cfg.dict, {'foo': '44'})

    ############################################################################
    ###                              bool_value                              ###
    ############################################################################

    def test_get_bool_value(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'true',
                    'bar': '1',
                    'baz': 'false',
                    'bla': '0'}
        self.assertEqual(cfg.get_bool_value('foo', False), True)
        self.assertEqual(cfg.get_bool_value('bar', False), True)
        self.assertEqual(cfg.get_bool_value('baz', True), False)
        self.assertEqual(cfg.get_bool_value('bla', True), False)

    def test_get_bool_value_default(self):
        cfg = configfile.ConfigFile()
        self.assertEqual(cfg.get_bool_value('non_existend_key', False), False)
        self.assertEqual(cfg.get_bool_value('non_existend_key', True), True)

    def test_set_bool_value(self):
        cfg = configfile.ConfigFile()
        cfg.set_bool_value('foo', True)
        cfg.set_bool_value('bar', False)
        self.assertEqual(cfg.dict, {'foo': 'true',
                                    'bar': 'false'})

    ############################################################################
    ###                           get_list_value                             ###
    ############################################################################

    def test_get_list_value_default(self):
        cfg = configfile.ConfigFile()
        self.assertEqual(cfg.get_list_value('test', 'str:value', ['asdf']), ['asdf'])

    def test_get_list_value_int(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'aaa.size': '3',
                    'aaa.1.bla': '55',
                    'aaa.2.bla': '66',
                    'aaa.3.bla': '77'}
        self.assertEqual(cfg.get_list_value('aaa', 'int:bla'), [55, 66, 77])

    def test_get_list_value_str(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'bbb.size': '3',
                    'bbb.1.value': 'foo',
                    'bbb.2.value': 'bar',
                    'bbb.3.value': 'baz'}
        self.assertEqual(cfg.get_list_value('bbb', 'str:value'), ['foo', 'bar', 'baz'])

    def test_get_list_value_bool(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'ccc.size': '2',
                    'ccc.1.foo': 'true',
                    'ccc.2.foo': 'false'}
        self.assertEqual(cfg.get_list_value('ccc', 'bool:foo'), [True, False])

    def test_get_list_value_tuple(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'ddd.size': '3',
                    'ddd.1.value': 'foo',
                    'ddd.1.type': '11',
                    'ddd.1.enabled': 'true',
                    'ddd.2.value': 'bar',
                    'ddd.2.type': '22',
                    'ddd.2.enabled': 'false',
                    'ddd.3.value': 'baz',
                    'ddd.3.type': '33',
                    'ddd.3.enabled': 'true'}
        self.assertEqual(cfg.get_list_value('ddd', ('str:value', 'int:type', 'bool:enabled')),
                         [('foo', 11, True), ('bar', 22, False), ('baz', 33, True)])

    def test_get_list_value_tuple_missing_values(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'eee.size': '3',
                    'eee.1.value': 'foo',
                    'eee.1.enabled': 'true',
                    'eee.2.type': '22',
                    'eee.2.enabled': 'false',
                    'eee.3.value': 'baz',
                    'eee.3.type': '33'}
        self.assertEqual(cfg.get_list_value('eee', ('str:value', 'int:type', 'bool:enabled')),
                         [('foo', 0, True), ('', 22, False), ('baz', 33, False)])

    def test_get_list_value_invalid_type(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'aaa.size': '3',
                    'aaa.1.bla': '55',
                    'aaa.2.bla': '66',
                    'aaa.3.bla': '77'}
        # cfg.get_list_value('aaa', 'non_existend_type:value')
        self.assertRaises(TypeError, cfg.get_list_value, 'aaa', 'non_existend_type:value')
        self.assertRaises(TypeError, cfg.get_list_value, 'aaa', {'dict:value'})
        self.assertRaises(TypeError, cfg.get_list_value, 'aaa', 1)

    ############################################################################
    ###                           set_list_value                             ###
    ############################################################################

    def test_set_list_value_int(self):
        cfg = configfile.ConfigFile()
        cfg.set_list_value('aaa', 'int:bla', [55, 66, 77])
        self.assertEqual(cfg.dict, {'aaa.size': '3',
                                    'aaa.1.bla': '55',
                                    'aaa.2.bla': '66',
                                    'aaa.3.bla': '77'})

    def test_set_list_value_str(self):
        cfg = configfile.ConfigFile()
        cfg.set_list_value('bbb', 'str:value', ['foo', 'bar', 'baz'])
        self.assertEqual(cfg.dict, {'bbb.size': '3',
                                    'bbb.1.value': 'foo',
                                    'bbb.2.value': 'bar',
                                    'bbb.3.value': 'baz'})

    def test_set_list_value_bool(self):
        cfg = configfile.ConfigFile()
        cfg.set_list_value('ccc', 'bool:foo', [True, False])
        self.assertEqual(cfg.dict, {'ccc.size': '2',
                                    'ccc.1.foo': 'true',
                                    'ccc.2.foo': 'false'})

    def test_set_list_value_tuple(self):
        cfg = configfile.ConfigFile()
        cfg.set_list_value('ddd', ('str:value', 'int:type', 'bool:enabled'),
                           [('foo', 11, True), ('bar', 22, False), ('baz', 33, True)])
        self.assertEqual(cfg.dict, {'ddd.size': '3',
                                    'ddd.1.value': 'foo',
                                    'ddd.1.type': '11',
                                    'ddd.1.enabled': 'true',
                                    'ddd.2.value': 'bar',
                                    'ddd.2.type': '22',
                                    'ddd.2.enabled': 'false',
                                    'ddd.3.value': 'baz',
                                    'ddd.3.type': '33',
                                    'ddd.3.enabled': 'true'})

    def test_set_list_value_tuple_missing_values(self):
        cfg = configfile.ConfigFile()
        cfg.set_list_value('ddd', ('str:value', 'int:type', 'bool:enabled'),
                           [('foo', 11, True), ('bar', 22), ('baz',)])
        self.assertEqual(cfg.dict, {'ddd.size': '3',
                                    'ddd.1.value': 'foo',
                                    'ddd.1.type': '11',
                                    'ddd.1.enabled': 'true',
                                    'ddd.2.value': 'bar',
                                    'ddd.2.type': '22',
                                    'ddd.3.value': 'baz'})

    def test_set_list_value_remove_leftovers(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'eee.size': '5',
                    'eee.1.bla': '55',
                    'eee.2.bla': '66',
                    'eee.3.bla': '77',
                    'eee.4.bla': '88',
                    'eee.5.bla': '99'}
        cfg.set_list_value('eee', 'int:bla', [55, 66, 77])
        self.assertEqual(cfg.dict, {'eee.size': '3',
                                    'eee.1.bla': '55',
                                    'eee.2.bla': '66',
                                    'eee.3.bla': '77'})

    def test_set_list_value_remove_leftovers(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'fff.size': '5',
                    'fff.1.value': 'foo',
                    'fff.1.type': '11',
                    'fff.1.enabled': 'true',
                    'fff.2.value': 'bar',
                    'fff.2.type': '22',
                    'fff.2.enabled': 'false',
                    'fff.3.value': 'baz',
                    'fff.3.type': '33',
                    'fff.3.enabled': 'true',
                    'fff.4.value': 'boom',
                    'fff.4.type': '44',
                    'fff.4.enabled': 'true',
                    'fff.5.value': 'bam',
                    'fff.5.type': '55',
                    'fff.5.enabled': 'true'}
        cfg.set_list_value('fff', ('str:value', 'int:type', 'bool:enabled'),
                           [('foo', 11, True), ('bar', 22), ('baz',)])
        self.assertEqual(cfg.dict, {'fff.size': '3',
                                    'fff.1.value': 'foo',
                                    'fff.1.type': '11',
                                    'fff.1.enabled': 'true',
                                    'fff.2.value': 'bar',
                                    'fff.2.type': '22',
                                    'fff.3.value': 'baz'})

    def test_set_list_value_invalid_type(self):
        cfg = configfile.ConfigFile()
        self.assertRaises(TypeError, cfg.set_list_value, 'aaa', 'non_existend_type:value', 'foo')
        self.assertRaises(TypeError, cfg.set_list_value, 'aaa', {'dict:value'}, 'foo')
        self.assertRaises(TypeError, cfg.set_list_value, 'aaa', 1, 'foo')

#TODO: add remove_key(s) test and tests for ConfigFileWithProfiles

if __name__ == '__main__':
    unittest.main()
