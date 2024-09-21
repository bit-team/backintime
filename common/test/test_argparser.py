#    Copyright (C) 2015-2022 Germar Reitze
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import unittest
import os
import sys
import itertools
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import backintime

def shuffleArgs(*args):
    """
    Return every possible combination of arguments. Those arguments which need
    to keep in line have to be inside a tuple.

    args:   two or more arguments (str)
    """
    for i in itertools.permutations(args):
        ret = []
        for j in i:
            if isinstance(j, (tuple, list)):
                ret.extend(j)
            else:
                ret.append(j)
        yield ret


class General(generic.TestCase):
    def setUp(self):
        super().setUp()
        backintime.createParsers()

    def tearDown(self):
        super().tearDown()
        global parsers
        parsers = {}

    def test_invalid_arg(self):
        with self.assertRaises(SystemExit):
            backintime.argParse(['not_existing_command'])
        with self.assertRaises(SystemExit):
            backintime.argParse(['--not_existing_argument'])

    def test_config(self):
        args = backintime.argParse(['--config', '/tmp/config'])
        self.assertIn('config', args)
        self.assertEqual(args.config, '/tmp/config')

    def test_quiet(self):
        args = backintime.argParse(['--quiet',])
        self.assertIn('quiet', args)
        self.assertTrue(args.quiet)

    def test_debug(self):
        args = backintime.argParse(['--debug',])
        self.assertIn('debug', args)
        self.assertTrue(args.debug)

    def test_config_no_path(self):
        with self.assertRaises(SystemExit):
            backintime.argParse(['--config'])


class Backup(generic.TestCase):
    def setUp(self):
        super().setUp()
        backintime.createParsers()

    def tearDown(self):
        super().tearDown()
        global parsers
        parsers = {}

    def test_simple(self):
        args = backintime.argParse(['backup'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'backup')
        self.assertIn('func', args)
        self.assertIs(args.func, backintime.backup)

    def test_backwards_compatiblity_alias(self):
        args = backintime.argParse(['--backup'])
        self.assertIn('func', args)
        self.assertIs(args.func, backintime.aliasParser)
        self.assertIn('replace', args)
        self.assertEqual(args.replace, '--backup')
        self.assertIn('alias', args)
        self.assertEqual(args.alias, 'backup')

    def test_profile(self):
        for argv in shuffleArgs('backup', ('--profile', 'foo')):
            with self.subTest(argv = argv):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'argv = %s' %argv
                args = backintime.argParse(argv)
                self.assertIn('command', args, msg)
                self.assertEqual(args.command, 'backup', msg)
                self.assertIn('profile', args, msg)
                self.assertEqual(args.profile, 'foo', msg)

    def test_profile_id(self):
        args = backintime.argParse(['backup', '--profile-id', '2'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'backup')
        self.assertIn('profile_id', args)
        self.assertEqual(args.profile_id, 2)

    def test_profile_and_profile_id(self):
        with self.assertRaises(SystemExit):
            backintime.argParse(['backup', '--profile', 'foo', '--profile-id', '2'])

    def test_quiet(self):
        args = backintime.argParse(['backup', '--quiet'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'backup')
        self.assertIn('quiet', args)
        self.assertTrue(args.quiet)

    def test_multi_args(self):
        for argv in shuffleArgs('--quiet', 'backup', ('--profile', 'foo'), '--checksum',
                                ('--config', 'bar')):
            with self.subTest(argv = argv):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'argv = %s' %argv
                args = backintime.argParse(argv)
                self.assertIn('command', args, msg)
                self.assertEqual(args.command, 'backup', msg)
                self.assertIn('profile', args, msg)
                self.assertEqual(args.profile, 'foo', msg)
                self.assertIn('quiet', args, msg)
                self.assertTrue(args.quiet, msg)
                self.assertIn('checksum', args, msg)
                self.assertTrue(args.checksum, msg)
                self.assertIn('config', args, msg)
                self.assertEqual(args.config, 'bar', msg)


class Restore(generic.TestCase):
    def setUp(self):
        super().setUp()
        backintime.createParsers()

    def tearDown(self):
        super().tearDown()
        global parsers
        parsers = {}

    def test_simple(self):
        args = backintime.argParse(['restore'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'restore')
        self.assertIn('func', args)
        self.assertIs(args.func, backintime.restore)

    def test_what_where_snapshot_id(self):
        args = backintime.argParse(['restore', '/home', '/tmp', '20151130-230501-984'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'restore')
        self.assertIn('WHAT', args)
        self.assertEqual(args.WHAT, '/home')
        self.assertIn('WHERE', args)
        self.assertEqual(args.WHERE, '/tmp')
        self.assertIn('SNAPSHOT_ID', args)
        self.assertEqual(args.SNAPSHOT_ID, '20151130-230501-984')

    def test_what_where_snapshot_id_multi_args(self):
        for argv in shuffleArgs('--quiet', ('restore', '/home', '/tmp', '20151130-230501-984'),
                                '--checksum', ('--profile-id', '2'), '--local-backup',
                                '--delete', ('--config', 'foo')):
            with self.subTest(argv = argv):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'argv = %s' %argv
                args = backintime.argParse(argv)
                self.assertIn('quiet', args, msg)
                self.assertTrue(args.quiet, msg)
                self.assertIn('checksum', args, msg)
                self.assertTrue(args.checksum, msg)
                self.assertIn('profile_id', args, msg)
                self.assertEqual(args.profile_id, 2, msg)
                self.assertIn('command', args, msg)
                self.assertEqual(args.command, 'restore', msg)
                self.assertIn('WHAT', args, msg)
                self.assertEqual(args.WHAT, '/home', msg)
                self.assertIn('WHERE', args, msg)
                self.assertEqual(args.WHERE, '/tmp', msg)
                self.assertIn('SNAPSHOT_ID', args, msg)
                self.assertEqual(args.SNAPSHOT_ID, '20151130-230501-984', msg)
                self.assertIn('local_backup', args, msg)
                self.assertTrue(args.local_backup, msg)
                self.assertIn('delete', args, msg)
                self.assertTrue(args.delete, msg)
                self.assertIn('config', args, msg)
                self.assertEqual(args.config, 'foo', msg)

    def test_multi_args(self):
        for argv in shuffleArgs(('--profile-id', '2'), '--quiet', 'restore', '--checksum',
                                '--local-backup',
                                '--delete', ('--config', 'foo')):
            with self.subTest(argv = argv):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'argv = %s' %argv
                args = backintime.argParse(argv)
                self.assertIn('quiet', args, msg)
                self.assertTrue(args.quiet, msg)
                self.assertIn('checksum', args, msg)
                self.assertTrue(args.checksum, msg)
                self.assertIn('profile_id', args, msg)
                self.assertEqual(args.profile_id, 2, msg)
                self.assertIn('command', args, msg)
                self.assertEqual(args.command, 'restore', msg)
                self.assertIn('local_backup', args, msg)
                self.assertTrue(args.local_backup, msg)
                self.assertIn('delete', args, msg)
                self.assertTrue(args.delete, msg)
                self.assertIn('config', args, msg)
                self.assertEqual(args.config, 'foo', msg)

    def test_snapshot_id_index(self):
        args = backintime.argParse(['restore', '/home', '/tmp', '1'])
        self.assertIn('SNAPSHOT_ID', args)
        self.assertEqual(args.SNAPSHOT_ID, '1')

    def test_empty_where(self):
        args = backintime.argParse(['restore', '/home', '', '20151130-230501-984'])
        self.assertIn('WHERE', args)
        self.assertEqual(args.WHERE, '')

    def test_where_space_in_path(self):
        args = backintime.argParse(['restore', '/home', '/tmp/foo bar/baz', '20151130-230501-984'])
        self.assertIn('WHERE', args)
        self.assertEqual(args.WHERE, '/tmp/foo bar/baz')

    def test_what_space_in_path(self):
        args = backintime.argParse(['restore', '/home/foo bar/baz', '/tmp', '20151130-230501-984'])
        self.assertIn('WHAT', args)
        self.assertEqual(args.WHAT, '/home/foo bar/baz')

    def test_local_backup_and_no_local_backup(self):
        with self.assertRaises(SystemExit):
            backintime.argParse(('restore', '--local-backup', '--no-local-backup'))


if __name__ == '__main__':
    unittest.main()
