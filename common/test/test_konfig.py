# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
import unittest
import configparser
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
from pathlib import Path
from io import StringIO
from konfig import Konfig, Profile
from singleton import Singleton


class General(unittest.TestCase):
    """Konfig class"""

    def setUp(self):
        Singleton.remove_all_instances()

    def test_empty(self):
        """Empty config file"""
        sut = Konfig()
        sut.load(StringIO(''))

        self.assertEqual(
            dict(sut._conf.items()),
            {'profile1.name': 'Main profile'}
        )

    def test_default_values(self):
        """Default values and their types of fields if not present."""
        sut = Konfig()
        sut.load(StringIO(''))

        self.assertEqual(sut.global_flock, False)
        self.assertIsInstance(sut.global_flock, bool)
        self.assertEqual(sut.language, '')
        self.assertIsInstance(sut.language, str)

    def test_no_interpolation(self):
        """Interpolation should be turned off"""
        try:
            sut = Konfig()
            sut.load(StringIO('qt.diff.params=%6 %1 %2'))
        except configparser.InterpolationSyntaxError as exc:
            self.fail(f'InterpolationSyntaxError was raised. {exc}')

    def test_new_instance_has_clean_state(self):
        """A new Konfig instance does not inherit old values."""
        sut = Konfig()
        sut['test.value'] = 'foobar'

        Singleton.remove_all_instances()

        sut = Konfig()

        with self.assertRaises(KeyError):
            sut['test.value']


class Read(unittest.TestCase):
    """Read a config file/object"""

    def setUp(self):
        Singleton.remove_all_instances()

    def test_from_memory_via_load(self):
        """Config in memory"""
        sut = Konfig()
        self.assertEqual(sut.language, '')

        buffer = StringIO('global.language=ab')
        sut.load(buffer)
        self.assertEqual(sut.language, 'ab')

    @pyfakefs_ut.patchfs
    def test_from_file_via_load(self, fake_fs):
        """Config in from file"""
        sut = Konfig()
        self.assertEqual(sut.language, '')

        fp = Path.cwd() / 'filezwei'
        with fp.open('w', encoding='utf-8') as handle:
            handle.write('global.language=wq\n')

        with fp.open('r', encoding='utf-8') as handle:
            sut.load(handle)
        self.assertEqual(sut.language, 'wq')


class ProfilesBasics(unittest.TestCase):
    """Konfig.Profile class"""

    def setUp(self):
        Singleton.remove_all_instances()

    def test_empty(self):
        """Profile child objects"""
        konf = Konfig()
        konf.load(StringIO(''))
        sut = konf.profile(1)
        self.assertEqual(sut['name'], 'Main profile')

    def test_default_values(self):
        """Default values and their types of fields if not present."""
        sut = Konfig()
        sut.load(StringIO('profile0.name=Zero'))
        sut = sut.profile(0)

        self.assertEqual(sut.ssh_check_commands, True)
        self.assertIsInstance(sut.ssh_check_commands, bool)
        self.assertEqual(sut.ssh_port, 22)
        self.assertIsInstance(sut.ssh_port, int)


class ProfilesExistance(unittest.TestCase):
    def setUp(self):
        Singleton.remove_all_instances()
        konfig = Konfig()
        konfig.load(StringIO('\n'.join([
            'profile1.name=One',
            'profile3.name=Misc',
            'profile42.name=TheAnswer',
            'profile7.name=Magic',
        ])))

    def test_to_id(self):
        self.assertEqual(Konfig().to_profile_id(42), 42)
        self.assertEqual(Konfig().to_profile_id('Magic'), 7)
        self.assertEqual(Konfig().to_profile_id('One'), 1)
        self.assertEqual(Konfig().to_profile_id('TheAnswer'), 42)

        # existence is irrelevant
        self.assertEqual(Konfig().to_profile_id(4), 4)

    def test_exists(self):
        self.assertIsInstance(Konfig().profile(42), Profile)
        self.assertIsInstance(Konfig().profile('One'), Profile)

    def test_unexisting(self):
        with self.assertRaises(KeyError):
            Konfig().profile(123)

    def test_has(self):
        self.assertTrue(Konfig().has_profile(42))
        self.assertTrue(Konfig().has_profile('One'))

    def test_dont_has(self):
        for arg in [321, 'IamNotHere']:
            self.assertFalse(Konfig().has_profile(arg))


class IncExc(unittest.TestCase):
    """About include and exclude fields"""

    def setUp(self):
        Singleton.remove_all_instances()

    def test_exclude_write(self):
        """Write exclude fields"""
        config = Konfig()
        config.load(StringIO('\n'.join([
            'profile1.name=Foo'
        ])))
        sut = config.profile(1)

        self.assertEqual(sut.exclude, [])

        sut.exclude = ['Worf', 'Garak']

        self.assertEqual(sut.exclude, ['Worf', 'Garak'])

    def test_include_write(self):
        """Write include fields"""
        config = Konfig()
        config.load(StringIO('\n'.join([
            'profile1.name=includewrite'
        ])))
        sut = config.profile(1)

        self.assertEqual(sut.include, [])

        sut.include = [
            ('/Cardassia/Prime', 0),
            ('/Ferengi/Nar', 1),
        ]

        self.assertEqual(
            sut.include,
            [
                ('/Cardassia/Prime', 0),
                ('/Ferengi/Nar', 1),
            ]
        )

    def test_include_read(self):
        """Read include fields"""
        config = Konfig()
        config.load(StringIO('\n'.join([
            'profile1.snapshots.include.1.value=/foo/bar/folder',
            'profile1.snapshots.include.1.type=0',
            'profile1.snapshots.include.2.value=/foo/bar/file',
            'profile1.snapshots.include.2.type=1',
        ])))
        sut = config.profile(1)

        self.assertEqual(
            sut.include,
            [
                ('/foo/bar/folder', 0),
                ('/foo/bar/file', 1)
            ]
        )

    def test_exclude_read(self):
        """Read exclude fields"""
        config = Konfig()
        config.load(StringIO('\n'.join([
            'profile1.snapshots.exclude.2.value=/bar/foo/file',
            'profile1.snapshots.exclude.1.value=/bar/foo/folder',
        ])))
        sut = config.profile(1)

        self.assertEqual(
            sut.exclude,
            [
                '/bar/foo/file',
                '/bar/foo/folder',
            ]
        )

    def test_include_does_not_leak_between_instances(self):
        """Include values do not leak through singleton state.

        This is aregression test covering a specific bug found in the past. It
        is similar to General.test_new_instance_has_clean_state().
        """
        config = Konfig()
        config.load(StringIO('\n'.join([
            'profile1.name=dontleak'
        ])))
        profile = config.profile(1)

        profile.include = [
            ('/foo', 0),
        ]

        Singleton.remove_all_instances()

        config = Konfig()
        config.load(StringIO('\n'.join([
            'profile1.name=dontleak'
        ])))
        profile = config.profile(1)

        self.assertEqual(profile.include, [])
