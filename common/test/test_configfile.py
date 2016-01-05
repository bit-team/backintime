# Back In Time
# Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
from tempfile import NamedTemporaryFile
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import configfile
import logger


class TestConfigFile(unittest.TestCase):
    '''Tests for the ConfigFile class in the configfile module'''
    def setUp(self):
        logger.DEBUG = '-v' in sys.argv

    def test_save(self):
        '''Saves the config file  in the tmp direcory '''
        with NamedTemporaryFile() as cfgFile:
            cf = configfile.ConfigFile()
            self.assertTrue(cf.save(cfgFile.name))
            self.assertTrue(os.path.exists(cfgFile.name))

        self.assertFalse(cf.save('/foo'))

    def test_load(self):
        '''
        ConfigFile should be able to load its content from a previously
        saved ConfigFile object.
        '''
        with NamedTemporaryFile() as cfgFile:
            original_cf = configfile.ConfigFile()
            key = "config_key"
            value = "config_value"
            original_cf.set_str_value(key, value)
            original_cf.save(cfgFile.name)

            cf = configfile.ConfigFile()
            cf.load(cfgFile.name)

            self.assertEqual(len(cf.get_keys()), len(original_cf.get_keys()))
            for k in original_cf.get_keys():
                with self.subTest(k = k):
                    #workaround for py.test3 2.5.1 doesn't support subTest
                    msg = 'k = %s' %k
                    self.assertTrue(cf.has_value(k), msg)
                    self.assertEqual(original_cf.get_str_value(k), cf.get_str_value(k))

    def test_remap_key(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': '123',
                    'bar': '456'}
        #old key not in dict
        cfg.remap_key('notExistedKey', 'baz')
        self.assertEqual(cfg.get_str_value('foo'), '123')
        self.assertEqual(cfg.get_str_value('bar'), '456')

        #valid remap
        cfg.remap_key('foo', 'baz')
        self.assertEqual(cfg.get_str_value('foo'), '')
        self.assertEqual(cfg.get_str_value('baz'), '123')
        self.assertEqual(cfg.get_str_value('bar'), '456')

        #do not overwrite existing keys
        cfg.remap_key('baz', 'bar')
        self.assertEqual(cfg.get_str_value('baz'), '')
        self.assertEqual(cfg.get_str_value('bar'), '456')

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
        self.assertDictEqual(cfg.dict, {'foo': 'bar'})

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
        self.assertDictEqual(cfg.dict, {'foo': '44'})

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
        self.assertDictEqual(cfg.dict, {'foo': 'true',
                                        'bar': 'false'})

    ############################################################################
    ###                           get_list_value                             ###
    ############################################################################

    def test_get_list_value_default(self):
        cfg = configfile.ConfigFile()
        self.assertListEqual(cfg.get_list_value('test', 'str:value', ['asdf']), ['asdf'])

    def test_get_list_value_int(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'aaa.size': '3',
                    'aaa.1.bla': '55',
                    'aaa.2.bla': '66',
                    'aaa.3.bla': '77'}
        self.assertListEqual(cfg.get_list_value('aaa', 'int:bla'), [55, 66, 77])

    def test_get_list_value_str(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'bbb.size': '3',
                    'bbb.1.value': 'foo',
                    'bbb.2.value': 'bar',
                    'bbb.3.value': 'baz'}
        self.assertListEqual(cfg.get_list_value('bbb', 'str:value'), ['foo', 'bar', 'baz'])

    def test_get_list_value_bool(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'ccc.size': '2',
                    'ccc.1.foo': 'true',
                    'ccc.2.foo': 'false'}
        self.assertListEqual(cfg.get_list_value('ccc', 'bool:foo'), [True, False])

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
        self.assertListEqual(cfg.get_list_value('ddd', ('str:value', 'int:type', 'bool:enabled')),
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
        self.assertListEqual(cfg.get_list_value('eee', ('str:value', 'int:type', 'bool:enabled')),
                             [('foo', 0, True), ('', 22, False), ('baz', 33, False)])

    def test_get_list_value_invalid_type(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'aaa.size': '3',
                    'aaa.1.bla': '55',
                    'aaa.2.bla': '66',
                    'aaa.3.bla': '77'}
        # cfg.get_list_value('aaa', 'non_existend_type:value')
        with self.assertRaises(TypeError):
            cfg.get_list_value('aaa', 'non_existend_type:value')
        with self.assertRaises(TypeError):
            cfg.get_list_value('aaa', {'dict:value'})
        with self.assertRaises(TypeError):
            cfg.get_list_value('aaa', 1)

    ############################################################################
    ###                           set_list_value                             ###
    ############################################################################

    def test_set_list_value_int(self):
        cfg = configfile.ConfigFile()
        cfg.set_list_value('aaa', 'int:bla', [55, 66, 77])
        self.assertDictEqual(cfg.dict, {'aaa.size': '3',
                                        'aaa.1.bla': '55',
                                        'aaa.2.bla': '66',
                                        'aaa.3.bla': '77'})

    def test_set_list_value_str(self):
        cfg = configfile.ConfigFile()
        cfg.set_list_value('bbb', 'str:value', ['foo', 'bar', 'baz'])
        self.assertDictEqual(cfg.dict, {'bbb.size': '3',
                                        'bbb.1.value': 'foo',
                                        'bbb.2.value': 'bar',
                                        'bbb.3.value': 'baz'})

    def test_set_list_value_bool(self):
        cfg = configfile.ConfigFile()
        cfg.set_list_value('ccc', 'bool:foo', [True, False])
        self.assertDictEqual(cfg.dict, {'ccc.size': '2',
                                        'ccc.1.foo': 'true',
                                        'ccc.2.foo': 'false'})

    def test_set_list_value_tuple(self):
        cfg = configfile.ConfigFile()
        cfg.set_list_value('ddd', ('str:value', 'int:type', 'bool:enabled'),
                           [('foo', 11, True), ('bar', 22, False), ('baz', 33, True)])
        self.assertDictEqual(cfg.dict, {'ddd.size': '3',
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
        self.assertDictEqual(cfg.dict, {'ddd.size': '3',
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
        self.assertDictEqual(cfg.dict, {'eee.size': '3',
                                        'eee.1.bla': '55',
                                        'eee.2.bla': '66',
                                        'eee.3.bla': '77'})

    def test_set_list_value_remove_leftovers_tuple(self):
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
        self.assertDictEqual(cfg.dict, {'fff.size': '3',
                                        'fff.1.value': 'foo',
                                        'fff.1.type': '11',
                                        'fff.1.enabled': 'true',
                                        'fff.2.value': 'bar',
                                        'fff.2.type': '22',
                                        'fff.3.value': 'baz'})

    def test_set_list_value_invalid_type_for_type_key(self):
        cfg = configfile.ConfigFile()
        with self.assertRaises(TypeError):
            cfg.set_list_value('aaa', 'non_existend_type:value', ['foo',])
        with self.assertRaises(TypeError):
            cfg.set_list_value('aaa', {'dict:value'}, ['foo',])
        with self.assertRaises(TypeError):
            cfg.set_list_value('aaa', 1, ['foo',])

    def test_set_list_value_invalid_type_for_value(self):
        cfg = configfile.ConfigFile()
        with self.assertRaises(TypeError):
            cfg.set_list_value('bbb', 'str:value', 'foo')
        with self.assertRaises(TypeError):
            cfg.set_list_value('bbb', 'str:value', {'foo': 'bar'})

    ############################################################################
    ###                            remove keys                               ###
    ############################################################################

    def test_remove_key(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'true',
                    'bar': '1',
                    'baz': 'false',
                    'bla': '0'}
        cfg.remove_key('bla')
        self.assertDictEqual(cfg.dict, {'foo': 'true',
                                        'bar': '1',
                                        'baz': 'false'})

    def test_remove_keys_start_with(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'true',
                    'bar': '1',
                    'baz': 'false',
                    'bla': '0'}
        cfg.remove_keys_starts_with('ba')
        self.assertDictEqual(cfg.dict, {'foo': 'true',
                                        'bla': '0'})

    def test_remove_keys_start_with_not_matching_prefix(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'true',
                    'bar': '1',
                    'baz': 'false',
                    'bla': '0'}
        cfg.remove_keys_starts_with('not_matching')
        self.assertDictEqual(cfg.dict, {'foo': 'true',
                                        'bar': '1',
                                        'baz': 'false',
                                        'bla': '0'})

class TestConfigFileWithProfiles(unittest.TestCase):
    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.cfg = configfile.ConfigFileWithProfiles('DefaultProfileName')
        self.cfg.add_profile('foo')
        self.cfg.add_profile('bar')
        self.cfg.add_profile('baz')

    def test_load(self):
        '''
        ConfigFile should be able to load its content from a previously
        saved ConfigFile object.
        '''
        with NamedTemporaryFile() as cfgFile:
            origCfg = configfile.ConfigFileWithProfiles()
            origCfg.set_int_value('profiles.version', 1)
            key = "config_key"
            value = "config_value"
            origCfg.set_profile_str_value(key, value)
            origCfg.set_profile_str_value(key, value, profile_id = '2')
            origCfg.save(cfgFile.name)

            self.cfg.load(cfgFile.name)

            self.assertEqual(len(self.cfg.get_keys()), len(origCfg.get_keys()))
            for k in origCfg.get_keys():
                with self.subTest(k = k):
                    #workaround for py.test3 2.5.1 doesn't support subTest
                    msg = 'k = %s' %k
                    self.assertTrue(self.cfg.has_value(k), msg)
                    self.assertEqual(origCfg.get_str_value(k), self.cfg.get_str_value(k))

    def test_get_profiles(self):
        emptyCfg = configfile.ConfigFileWithProfiles()
        self.assertListEqual(emptyCfg.get_profiles(), ['1',])

        self.assertListEqual(self.cfg.get_profiles(), ['1', '2', '3', '4'])

        self.cfg.remove_profile('3')
        self.assertListEqual(self.cfg.get_profiles(), ['1', '2', '4'])

    def test_get_profiles_sorted_by_name(self):
        self.assertListEqual(self.cfg.get_profiles_sorted_by_name(), ['3', '4', '1', '2'])

    def test_current_profile(self):
        self.assertEqual(self.cfg.get_current_profile(), '1')

        self.assertTrue(self.cfg.set_current_profile(4))
        self.assertEqual(self.cfg.get_current_profile(), '4')

        self.assertTrue(self.cfg.set_current_profile('3'))
        self.assertEqual(self.cfg.get_current_profile(), '3')

        self.assertFalse(self.cfg.set_current_profile('9'))
        self.assertEqual(self.cfg.get_current_profile(), '3')

    def test_current_profile_by_name(self):
        self.assertEqual(self.cfg.get_current_profile(), '1')

        self.assertTrue(self.cfg.set_current_profile_by_name('bar'))
        self.assertEqual(self.cfg.get_current_profile(), '3')

        self.assertFalse(self.cfg.set_current_profile_by_name('NotExistingProfile'))
        self.assertEqual(self.cfg.get_current_profile(), '3')

    def test_profile_exists(self):
        self.assertTrue(self.cfg.profile_exists('2'))
        self.assertTrue(self.cfg.profile_exists(3))
        self.assertFalse(self.cfg.profile_exists('9'))
        self.assertFalse(self.cfg.profile_exists(10))

    def test_profile_exists_by_name(self):
        self.assertTrue(self.cfg.profile_exists_by_name('foo'))
        self.assertFalse(self.cfg.profile_exists_by_name('NotExistingProfile'))

    def test_get_profile_name(self):
        self.assertEqual(self.cfg.get_profile_name('1'), 'DefaultProfileName')
        self.assertEqual(self.cfg.get_profile_name('2'), 'foo')
        self.assertEqual(self.cfg.get_profile_name(3), 'bar')

        self.assertEqual(self.cfg.get_profile_name(), 'DefaultProfileName')
        self.cfg.set_current_profile('3')
        self.assertEqual(self.cfg.get_profile_name(), 'bar')

        self.assertEqual(self.cfg.get_profile_name('4'), 'baz')
        del self.cfg.dict['profile4.name']
        self.assertEqual(self.cfg.get_profile_name('4'), 'Profile 4')

    def test_add_profile(self):
        #add already existing profile
        self.assertIsNone(self.cfg.add_profile('foo'))

        #new valid profile
        self.assertEqual(self.cfg.add_profile('asdf'), '5')

        #new valid profile fill an old profile ID
        self.cfg.remove_profile('3')
        self.assertEqual(self.cfg.add_profile('qwertz'), '3')

    def test_remove_profile(self):
        for profile in self.cfg.get_profiles():
            self.cfg.set_profile_str_value('foo', 'bar', profile)

        self.assertFalse(self.cfg.remove_profile('9'))

        self.assertTrue(self.cfg.remove_profile('3'))
        self.assertNotIn('3', self.cfg.get_profiles())
        self.assertNotIn('profile3.foo', self.cfg.dict)

        self.cfg.set_current_profile('4')
        self.assertTrue(self.cfg.remove_profile())
        self.assertNotIn('4', self.cfg.get_profiles())
        self.assertNotIn('profile4.foo', self.cfg.dict)
        self.assertEqual(self.cfg.get_current_profile(), '1')

        self.assertTrue(self.cfg.remove_profile(2))
        self.assertNotIn('2', self.cfg.get_profiles())
        self.assertNotIn('profile2.foo', self.cfg.dict)

        self.assertFalse(self.cfg.remove_profile())

    def test_set_profile_name(self):
        self.assertFalse(self.cfg.set_profile_name('foo', '3'))
        self.assertEqual(self.cfg.get_profile_name('3'), 'bar')

        self.assertTrue(self.cfg.set_profile_name('newName', '4'))
        self.assertEqual(self.cfg.get_profile_name('4'), 'newName')

        self.assertTrue(self.cfg.set_profile_name('otherName', 3))
        self.assertEqual(self.cfg.get_profile_name('3'), 'otherName')

        self.assertTrue(self.cfg.set_profile_name('thirdName'))
        self.assertEqual(self.cfg.get_profile_name('1'), 'thirdName')

    def test_get_profile_key(self):
        self.assertEqual(self.cfg._get_profile_key_('foo'), 'profile1.foo')
        self.assertEqual(self.cfg._get_profile_key_('foo', '2'), 'profile2.foo')
        self.assertEqual(self.cfg._get_profile_key_('foo', 3), 'profile3.foo')

    def test_remove_profile_key(self):
        for profile in self.cfg.get_profiles():
            self.cfg.set_profile_str_value('foo', 'bar', profile)

        self.assertIn('profile1.foo', self.cfg.dict)
        self.cfg.remove_profile_key('foo')
        self.assertNotIn('profile1.foo', self.cfg.dict)

        self.assertIn('profile3.foo', self.cfg.dict)
        self.cfg.remove_profile_key('foo', '3')
        self.assertNotIn('profile3.foo', self.cfg.dict)

    def test_remove_profile_keys_starts_with(self):
        for profile in self.cfg.get_profiles():
            self.cfg.set_profile_str_value('foo', 'bar', profile)

        self.assertIn('profile1.foo', self.cfg.dict)
        self.cfg.remove_profile_keys_starts_with('f')
        self.assertNotIn('profile1.foo', self.cfg.dict)

        self.assertIn('profile3.foo', self.cfg.dict)
        self.cfg.remove_profile_keys_starts_with('f', '3')
        self.assertNotIn('profile3.foo', self.cfg.dict)

    def test_has_profile_value(self):
        for profile in self.cfg.get_profiles():
            self.cfg.set_profile_str_value('foo', 'bar', profile)

        self.assertTrue(self.cfg.has_profile_value('foo'))
        self.assertFalse(self.cfg.has_profile_value('baz'))

        self.assertTrue(self.cfg.has_profile_value('foo', '3'))
        self.assertFalse(self.cfg.has_profile_value('baz', '3'))

    def test_set_profile_value(self):
        methods =  {'str':  ('foo', 'FOO'),
                    'int':  ('bar', 123),
                    'bool': ('baz', True)}

        for profile in (None, '3'):
            for t in methods:
                with self.subTest(profile = profile, t = t):
                    #workaround for py.test3 2.5.1 doesn't support subTest
                    msg = 'profile = {}, t = {}'.format(profile, t)
                    key, value = methods[t]
                    setFunc = getattr(self.cfg, 'set_profile_{}_value'.format(t))
                    getFunc = getattr(self.cfg, 'get_profile_{}_value'.format(t))
                    setFunc(key, value, profile_id = profile)
                    self.assertEqual(getFunc(key, profile_id = profile), value, msg)
            with self.subTest(profile = profile):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'profile = {}'.format(profile)
                self.cfg.set_profile_list_value('bla',
                                                'str:value',
                                                ['ASDF', 'QWERTZ'],
                                                profile_id = profile)
                result = self.cfg.get_profile_list_value('bla',
                                                         'str:value',
                                                         profile_id = profile)
                self.assertListEqual(result, ['ASDF', 'QWERTZ'], msg)

if __name__ == '__main__':
    unittest.main()
