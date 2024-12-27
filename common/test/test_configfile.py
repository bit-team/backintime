# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
from tempfile import NamedTemporaryFile
import unittest
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import configfile


class TestConfigFile(generic.TestCase):
    """
    Tests for the ConfigFile class in the configfile module
    """

    def test_save(self):
        """
        Saves the config file in the tmp directory
        """
        with NamedTemporaryFile() as cfgFile:
            cf = configfile.ConfigFile()
            self.assertTrue(cf.save(cfgFile.name))
            self.assertExists(cfgFile.name)

        #test fail routine in ConfigFile.save
        with NamedTemporaryFile() as fakeDir:
            self.assertFalse(cf.save(os.path.join(fakeDir.name, 'foo')))

    def test_load(self):
        """
        ConfigFile should be able to load its content from a previously
        saved ConfigFile object.
        """
        with NamedTemporaryFile() as cfgFile:
            original_cf = configfile.ConfigFile()
            key = "config_key"
            value = "config_value"
            original_cf.setStrValue(key, value)
            original_cf.save(cfgFile.name)

            cf = configfile.ConfigFile()
            cf.load(cfgFile.name)

            self.assertEqual(len(cf.keys()), len(original_cf.keys()))
            for k in original_cf.keys():
                with self.subTest(k = k):
                    #workaround for py.test3 2.5.1 doesn't support subTest
                    msg = 'k = %s' %k
                    self.assertTrue(cf.hasKey(k), msg)
                    self.assertEqual(original_cf.strValue(k), cf.strValue(k))

    def test_remapKey(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': '123',
                    'bar': '456'}
        #old key not in dict
        cfg.remapKey('notExistedKey', 'baz')
        self.assertEqual(cfg.strValue('foo'), '123')
        self.assertEqual(cfg.strValue('bar'), '456')

        #valid remap
        cfg.remapKey('foo', 'baz')
        self.assertEqual(cfg.strValue('foo'), '')
        self.assertEqual(cfg.strValue('baz'), '123')
        self.assertEqual(cfg.strValue('bar'), '456')

        #do not overwrite existing keys
        cfg.remapKey('baz', 'bar')
        self.assertEqual(cfg.strValue('baz'), '')
        self.assertEqual(cfg.strValue('bar'), '456')

    def test_remapKeyRegex(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'asdf.foo.qwertz': '123',
                    'foo.qwertz': '456',
                    'asdf.foo': '789',
                    'yxcv': 'jkl'}

        cfg.remapKeyRegex('foo', 'bar')
        self.assertEqual(cfg.strValue('asdf.bar.qwertz', 'WrongValue'), '123')
        self.assertEqual(cfg.strValue('bar.qwertz', 'WrongValue'), '456')
        self.assertEqual(cfg.strValue('asdf.bar', 'WrongValue'), '789')
        self.assertEqual(cfg.strValue('asdf.foo.qwertz', ''), '')
        self.assertEqual(cfg.strValue('foo.qwertz', ''), '')
        self.assertEqual(cfg.strValue('asdf.foo', ''), '')
        self.assertEqual(cfg.strValue('yxcv', 'WrongValue'), 'jkl')

    def test_hasKey(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'bar'}
        self.assertTrue(cfg.hasKey('foo'))
        self.assertFalse(cfg.hasKey('non_existend_key'))

    ############################################################################
    ###                               str_value                              ###
    ############################################################################

    def test_strValue(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'bar'}
        self.assertEqual(cfg.strValue('foo', 'default'), 'bar')

    def test_strValue_default(self):
        cfg = configfile.ConfigFile()
        self.assertEqual(cfg.strValue('non_existend_key', 'default'), 'default')

    def test_setStrValue(self):
        cfg = configfile.ConfigFile()
        cfg.setStrValue('foo', 'bar')
        self.assertDictEqual(cfg.dict, {'foo': 'bar'})

    ############################################################################
    ###                               int_value                              ###
    ############################################################################

    def test_intValue(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': '11'}
        self.assertEqual(cfg.intValue('foo', 22), 11)

    def test_intValue_default(self):
        cfg = configfile.ConfigFile()
        self.assertEqual(cfg.intValue('non_existend_key', 33), 33)

    def test_setIntValue(self):
        cfg = configfile.ConfigFile()
        cfg.setIntValue('foo', 44)
        self.assertDictEqual(cfg.dict, {'foo': '44'})

    ############################################################################
    ###                              bool_value                              ###
    ############################################################################

    def test_boolValue(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'true',
                    'bar': '1',
                    'baz': 'false',
                    'bla': '0'}
        self.assertEqual(cfg.boolValue('foo', False), True)
        self.assertEqual(cfg.boolValue('bar', False), True)
        self.assertEqual(cfg.boolValue('baz', True), False)
        self.assertEqual(cfg.boolValue('bla', True), False)

    def test_boolValue_default(self):
        cfg = configfile.ConfigFile()
        self.assertEqual(cfg.boolValue('non_existend_key', False), False)
        self.assertEqual(cfg.boolValue('non_existend_key', True), True)

    def test_setBoolValue(self):
        cfg = configfile.ConfigFile()
        cfg.setBoolValue('foo', True)
        cfg.setBoolValue('bar', False)
        self.assertDictEqual(cfg.dict, {'foo': 'true',
                                        'bar': 'false'})

    ############################################################################
    ###                           listValue                             ###
    ############################################################################

    def test_listValue_default(self):
        cfg = configfile.ConfigFile()
        self.assertListEqual(cfg.listValue('test', 'str:value', ['asdf']), ['asdf'])

    def test_listValue_int(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'aaa.size': '3',
                    'aaa.1.bla': '55',
                    'aaa.2.bla': '66',
                    'aaa.3.bla': '77'}
        self.assertListEqual(cfg.listValue('aaa', 'int:bla'), [55, 66, 77])

    def test_listValue_str(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'bbb.size': '3',
                    'bbb.1.value': 'foo',
                    'bbb.2.value': 'bar',
                    'bbb.3.value': 'baz'}
        self.assertListEqual(cfg.listValue('bbb', 'str:value'), ['foo', 'bar', 'baz'])

    def test_listValue_bool(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'ccc.size': '2',
                    'ccc.1.foo': 'true',
                    'ccc.2.foo': 'false'}
        self.assertListEqual(cfg.listValue('ccc', 'bool:foo'), [True, False])

    def test_listValue_tuple(self):
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
        self.assertListEqual(cfg.listValue('ddd', ('str:value', 'int:type', 'bool:enabled')),
                             [('foo', 11, True), ('bar', 22, False), ('baz', 33, True)])

    def test_listValue_tuple_missing_values(self):
        """
        Don't include missing values. Bug #521
        https://github.com/bit-team/backintime/issues/521
        """
        cfg = configfile.ConfigFile()
        cfg.dict = {'eee.size': '3',
                    'eee.1.value': 'foo',
                    'eee.1.enabled': 'true',
                    'eee.2.type': '22',
                    'eee.2.enabled': 'false',
                    'eee.3.value': 'baz',
                    'eee.3.type': '33'}
        self.assertListEqual(cfg.listValue('eee', ('str:value', 'int:type', 'bool:enabled')),
                             [('foo', 0, True), ('baz', 33, False)])

    def test_listValue_invalid_type(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'aaa.size': '3',
                    'aaa.1.value': '55',
                    'aaa.2.value': '66',
                    'aaa.3.value': '77'}
        with self.assertRaises(TypeError):
            cfg.listValue('aaa', 'non_existend_type:value')
        with self.assertRaises(TypeError):
            cfg.listValue('aaa', {'dict:value'})
        with self.assertRaises(TypeError):
            cfg.listValue('aaa', 1)

    def test_listValue_wrong_size(self):
        """
        Don't include empty values if size is wrong. Bug #521
        https://github.com/bit-team/backintime/issues/521
        """
        cfg = configfile.ConfigFile()
        cfg.dict = {'bbb.size': '4',
                    'bbb.1.value': 'foo',
                    'bbb.2.value': 'bar',
                    'bbb.3.value': 'baz'}
        self.assertListEqual(cfg.listValue('bbb', 'str:value'), ['foo', 'bar', 'baz'])

    def test_listValue_zero_count(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'ccc.size': '2',
                    'ccc.0.value': 'foo',
                    'ccc.1.value': 'bar',
                    'ccc.2.value': 'baz'}
        self.assertListEqual(cfg.listValue('ccc', 'str:value'), ['bar', 'baz'])

    def test_listValue_missing_values(self):
        """
        Don't include missing values. Bug #521
        https://github.com/bit-team/backintime/issues/521
        """
        cfg = configfile.ConfigFile()
        cfg.dict = {'ddd.size': '4',
                    'ddd.1.value': 'foo',
                    'ddd.2.value': 'bar',
                    'ddd.4.value': 'baz'}
        self.assertListEqual(cfg.listValue('ddd', 'str:value'),
                             ['foo', 'bar', 'baz'])

    def test_listValue_empty_list(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'eee.size': '0'}
        self.assertListEqual(cfg.listValue('eee', 'str:value',
                                           default = ['foo', 'bar']),
                             [])

    ############################################################################
    ###                           setListValue                             ###
    ############################################################################

    def test_setListValue_int(self):
        cfg = configfile.ConfigFile()
        cfg.setListValue('aaa', 'int:bla', [55, 66, 77])
        self.assertDictEqual(cfg.dict, {'aaa.size': '3',
                                        'aaa.1.bla': '55',
                                        'aaa.2.bla': '66',
                                        'aaa.3.bla': '77'})

    def test_setListValue_str(self):
        cfg = configfile.ConfigFile()
        cfg.setListValue('bbb', 'str:value', ['foo', 'bar', 'baz'])
        self.assertDictEqual(cfg.dict, {'bbb.size': '3',
                                        'bbb.1.value': 'foo',
                                        'bbb.2.value': 'bar',
                                        'bbb.3.value': 'baz'})

    def test_setListValue_bool(self):
        cfg = configfile.ConfigFile()
        cfg.setListValue('ccc', 'bool:foo', [True, False])
        self.assertDictEqual(cfg.dict, {'ccc.size': '2',
                                        'ccc.1.foo': 'true',
                                        'ccc.2.foo': 'false'})

    def test_setListValue_tuple(self):
        cfg = configfile.ConfigFile()
        cfg.setListValue('ddd', ('str:value', 'int:type', 'bool:enabled'),
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

    def test_setListValue_tuple_missing_values(self):
        cfg = configfile.ConfigFile()
        cfg.setListValue('ddd', ('str:value', 'int:type', 'bool:enabled'),
                           [('foo', 11, True), ('bar', 22), ('baz',)])
        self.assertDictEqual(cfg.dict, {'ddd.size': '3',
                                        'ddd.1.value': 'foo',
                                        'ddd.1.type': '11',
                                        'ddd.1.enabled': 'true',
                                        'ddd.2.value': 'bar',
                                        'ddd.2.type': '22',
                                        'ddd.3.value': 'baz'})

    def test_setListValue_remove_leftovers(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'eee.size': '5',
                    'eee.1.bla': '55',
                    'eee.2.bla': '66',
                    'eee.3.bla': '77',
                    'eee.4.bla': '88',
                    'eee.5.bla': '99'}
        cfg.setListValue('eee', 'int:bla', [55, 66, 77])
        self.assertDictEqual(cfg.dict, {'eee.size': '3',
                                        'eee.1.bla': '55',
                                        'eee.2.bla': '66',
                                        'eee.3.bla': '77'})

    def test_setListValue_remove_leftovers_tuple(self):
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
        cfg.setListValue('fff', ('str:value', 'int:type', 'bool:enabled'),
                           [('foo', 11, True), ('bar', 22), ('baz',)])
        self.assertDictEqual(cfg.dict, {'fff.size': '3',
                                        'fff.1.value': 'foo',
                                        'fff.1.type': '11',
                                        'fff.1.enabled': 'true',
                                        'fff.2.value': 'bar',
                                        'fff.2.type': '22',
                                        'fff.3.value': 'baz'})

    def test_setListValue_invalid_type_for_type_key(self):
        cfg = configfile.ConfigFile()
        with self.assertRaises(TypeError):
            cfg.setListValue('aaa', 'non_existend_type:value', ['foo',])
        with self.assertRaises(TypeError):
            cfg.setListValue('aaa', {'dict:value'}, ['foo',])
        with self.assertRaises(TypeError):
            cfg.setListValue('aaa', 1, ['foo',])

    def test_setListValue_invalid_type_for_value(self):
        cfg = configfile.ConfigFile()
        with self.assertRaises(TypeError):
            cfg.setListValue('bbb', 'str:value', 'foo')
        with self.assertRaises(TypeError):
            cfg.setListValue('bbb', 'str:value', {'foo': 'bar'})

    ############################################################################
    ###                            remove keys                               ###
    ############################################################################

    def test_remove_key(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'true',
                    'bar': '1',
                    'baz': 'false',
                    'bla': '0'}
        cfg.removeKey('bla')
        self.assertDictEqual(cfg.dict, {'foo': 'true',
                                        'bar': '1',
                                        'baz': 'false'})

    def test_remove_keys_start_with(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'true',
                    'bar': '1',
                    'baz': 'false',
                    'bla': '0'}
        cfg.removeKeysStartsWith('ba')
        self.assertDictEqual(cfg.dict, {'foo': 'true',
                                        'bla': '0'})

    def test_remove_keys_start_with_not_matching_prefix(self):
        cfg = configfile.ConfigFile()
        cfg.dict = {'foo': 'true',
                    'bar': '1',
                    'baz': 'false',
                    'bla': '0'}
        cfg.removeKeysStartsWith('not_matching')
        self.assertDictEqual(cfg.dict, {'foo': 'true',
                                        'bar': '1',
                                        'baz': 'false',
                                        'bla': '0'})


class TestConfigFileWithProfiles(generic.TestCase):
    def setUp(self):
        super(TestConfigFileWithProfiles, self).setUp()
        self.cfg = configfile.ConfigFileWithProfiles('DefaultProfileName')
        self.cfg.addProfile('foo')
        self.cfg.addProfile('bar')
        self.cfg.addProfile('baz')

    def test_load(self):
        """
        ConfigFile should be able to load its content from a previously
        saved ConfigFile object.
        """
        with NamedTemporaryFile() as cfgFile:
            origCfg = configfile.ConfigFileWithProfiles()
            origCfg.setIntValue('profiles.version', 1)
            key = "config_key"
            value = "config_value"
            origCfg.setProfileStrValue(key, value)
            origCfg.setProfileStrValue(key, value, profile_id = '2')
            origCfg.save(cfgFile.name)

            self.cfg.load(cfgFile.name)

            self.assertEqual(len(self.cfg.keys()), len(origCfg.keys()))
            for k in origCfg.keys():
                with self.subTest(k = k):
                    #workaround for py.test3 2.5.1 doesn't support subTest
                    msg = 'k = %s' %k
                    self.assertTrue(self.cfg.hasKey(k), msg)
                    self.assertEqual(origCfg.strValue(k), self.cfg.strValue(k))

    def test_profiles(self):
        emptyCfg = configfile.ConfigFileWithProfiles()
        self.assertListEqual(emptyCfg.profiles(), ['1',])

        self.assertListEqual(self.cfg.profiles(), ['1', '2', '3', '4'])

        self.cfg.removeProfile('3')
        self.assertListEqual(self.cfg.profiles(), ['1', '2', '4'])

    def test_profilesSortedByName(self):
        self.assertListEqual(self.cfg.profilesSortedByName(), ['3', '4', '1', '2'])

    def test_current_profile(self):
        self.assertEqual(self.cfg.currentProfile(), '1')

        self.assertTrue(self.cfg.setCurrentProfile(4))
        self.assertEqual(self.cfg.currentProfile(), '4')

        self.assertTrue(self.cfg.setCurrentProfile('3'))
        self.assertEqual(self.cfg.currentProfile(), '3')

        self.assertFalse(self.cfg.setCurrentProfile('9'))
        self.assertEqual(self.cfg.currentProfile(), '3')

    def test_current_profile_by_name(self):
        self.assertEqual(self.cfg.currentProfile(), '1')

        self.assertTrue(self.cfg.setCurrentProfileByName('bar'))
        self.assertEqual(self.cfg.currentProfile(), '3')

        self.assertFalse(self.cfg.setCurrentProfileByName('NotExistingProfile'))
        self.assertEqual(self.cfg.currentProfile(), '3')

    def test_profileExists(self):
        self.assertTrue(self.cfg.profileExists('2'))
        self.assertTrue(self.cfg.profileExists(3))
        self.assertFalse(self.cfg.profileExists('9'))
        self.assertFalse(self.cfg.profileExists(10))

    def test_profileExistsByName(self):
        self.assertTrue(self.cfg.profileExistsByName('foo'))
        self.assertFalse(self.cfg.profileExistsByName('NotExistingProfile'))

    def test_profileName(self):
        self.assertEqual(self.cfg.profileName('1'), 'DefaultProfileName')
        self.assertEqual(self.cfg.profileName('2'), 'foo')
        self.assertEqual(self.cfg.profileName(3), 'bar')

        self.assertEqual(self.cfg.profileName(), 'DefaultProfileName')
        self.cfg.setCurrentProfile('3')
        self.assertEqual(self.cfg.profileName(), 'bar')

        self.assertEqual(self.cfg.profileName('4'), 'baz')
        del self.cfg.dict['profile4.name']
        self.assertEqual(self.cfg.profileName('4'), 'Profile 4')

    def test_addProfile(self):
        #add already existing profile
        self.assertIsNone(self.cfg.addProfile('foo'))

        #new valid profile
        self.assertEqual(self.cfg.addProfile('asdf'), '5')

        #new valid profile fill an old profile ID
        self.cfg.removeProfile('3')
        self.assertEqual(self.cfg.addProfile('qwertz'), '3')

    def test_removeProfile(self):
        for profile in self.cfg.profiles():
            self.cfg.setProfileStrValue('foo', 'bar', profile)

        self.assertFalse(self.cfg.removeProfile('9'))

        self.assertTrue(self.cfg.removeProfile('3'))
        self.assertNotIn('3', self.cfg.profiles())
        self.assertNotIn('profile3.foo', self.cfg.dict)

        self.cfg.setCurrentProfile('4')
        self.assertTrue(self.cfg.removeProfile())
        self.assertNotIn('4', self.cfg.profiles())
        self.assertNotIn('profile4.foo', self.cfg.dict)
        self.assertEqual(self.cfg.currentProfile(), '1')

        self.assertTrue(self.cfg.removeProfile(2))
        self.assertNotIn('2', self.cfg.profiles())
        self.assertNotIn('profile2.foo', self.cfg.dict)

        self.assertFalse(self.cfg.removeProfile())

    def test_setProfileName(self):
        self.assertFalse(self.cfg.setProfileName('foo', '3'))
        self.assertEqual(self.cfg.profileName('3'), 'bar')

        self.assertTrue(self.cfg.setProfileName('newName', '4'))
        self.assertEqual(self.cfg.profileName('4'), 'newName')

        self.assertTrue(self.cfg.setProfileName('otherName', 3))
        self.assertEqual(self.cfg.profileName('3'), 'otherName')

        self.assertTrue(self.cfg.setProfileName('thirdName'))
        self.assertEqual(self.cfg.profileName('1'), 'thirdName')

    def test_get_profile_key(self):
        self.assertEqual(self.cfg.profileKey('foo'), 'profile1.foo')
        self.assertEqual(self.cfg.profileKey('foo', '2'), 'profile2.foo')
        self.assertEqual(self.cfg.profileKey('foo', 3), 'profile3.foo')

    def test_removeProfileKey(self):
        for profile in self.cfg.profiles():
            self.cfg.setProfileStrValue('foo', 'bar', profile)

        self.assertIn('profile1.foo', self.cfg.dict)
        self.cfg.removeProfileKey('foo')
        self.assertNotIn('profile1.foo', self.cfg.dict)

        self.assertIn('profile3.foo', self.cfg.dict)
        self.cfg.removeProfileKey('foo', '3')
        self.assertNotIn('profile3.foo', self.cfg.dict)

    def test_removeProfileKeysStartsWith(self):
        for profile in self.cfg.profiles():
            self.cfg.setProfileStrValue('foo', 'bar', profile)

        self.assertIn('profile1.foo', self.cfg.dict)
        self.cfg.removeProfileKeysStartsWith('f')
        self.assertNotIn('profile1.foo', self.cfg.dict)

        self.assertIn('profile3.foo', self.cfg.dict)
        self.cfg.removeProfileKeysStartsWith('f', '3')
        self.assertNotIn('profile3.foo', self.cfg.dict)

    def test_remapProfileKey(self):
        for profile in self.cfg.profiles():
            self.cfg.setProfileStrValue('foo', '123', profile)
            self.cfg.setProfileStrValue('bar', '456', profile)

        # old key not in cfg
        self.cfg.remapProfileKey('notExistedKey', 'baz', 1)
        self.assertEqual(self.cfg.profileStrValue('foo', '', 1), '123')
        self.assertEqual(self.cfg.profileStrValue('bar', '', 1), '456')


        # valid remap
        self.cfg.remapProfileKey('foo', 'baz', 1)
        self.assertEqual(self.cfg.profileStrValue('foo', '', 1), '')
        self.assertEqual(self.cfg.profileStrValue('baz', '', 1), '123')
        self.assertEqual(self.cfg.profileStrValue('foo', '', 2), '123')
        self.assertEqual(self.cfg.profileStrValue('foo', '', 3), '123')

        # do not overwrite existing keys
        self.cfg.remapProfileKey('foo', 'bar', 1)
        self.assertEqual(self.cfg.profileStrValue('foo', '', 2), '123')
        self.assertEqual(self.cfg.profileStrValue('baz', '', 2), '')
        self.assertEqual(self.cfg.profileStrValue('bar', '', 2), '456')

    def test_hasProfileKey(self):
        for profile in self.cfg.profiles():
            self.cfg.setProfileStrValue('foo', 'bar', profile)

        self.assertTrue(self.cfg.hasProfileKey('foo'))
        self.assertFalse(self.cfg.hasProfileKey('baz'))

        self.assertTrue(self.cfg.hasProfileKey('foo', '3'))
        self.assertFalse(self.cfg.hasProfileKey('baz', '3'))

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
                    setFunc = getattr(self.cfg, 'setProfile{}Value'.format(t.capitalize()))
                    getFunc = getattr(self.cfg, 'profile{}Value'.format(t.capitalize()))
                    setFunc(key, value, profile_id = profile)
                    self.assertEqual(getFunc(key, profile_id = profile), value, msg)
            with self.subTest(profile = profile):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'profile = {}'.format(profile)
                self.cfg.setProfileListValue('bla',
                                                'str:value',
                                                ['ASDF', 'QWERTZ'],
                                                profile_id = profile)
                result = self.cfg.profileListValue('bla',
                                                         'str:value',
                                                         profile_id = profile)
                self.assertListEqual(result, ['ASDF', 'QWERTZ'], msg)


if __name__ == '__main__':
    unittest.main()
