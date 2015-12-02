#    Copyright (C) 2015 Germar Reitze
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

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "common/"))
import backintime

def shuffleArgs(*args):
    '''
    Return every possible combination of arguments. Those arguments which need
    to keep in line have to be inside a tuple.
    '''
    for i in itertools.permutations(args):
        ret = []
        for j in i:
            if isinstance(j, (tuple, list)):
                ret.extend(j)
            else:
                ret.append(j)
        yield ret

class TestArgParser(unittest.TestCase):
    def setUp(self):
        backintime.create_parsers()

    def tearDown(self):
        global parsers
        parsers = {}

    def test_invalid_arg(self):
        self.assertRaises(SystemExit, backintime.arg_parse, ['not_existing_command'])
        self.assertRaises(SystemExit, backintime.arg_parse, ['--not_existing_argument'])

    def test_config(self):
        args = backintime.arg_parse(['--config', '/tmp/config'])
        self.assertIn('config', args)
        self.assertEqual(args.config, '/tmp/config')

    def test_quiet(self):
        args = backintime.arg_parse(['--quiet',])
        self.assertIn('quiet', args)
        self.assertTrue(args.quiet)

    def test_config_no_path(self):
        self.assertRaises(SystemExit, backintime.arg_parse, ['--config'])

    ############################################################################
    ###                               Backup                                 ###
    ############################################################################
    def test_cmd_backup(self):
        args = backintime.arg_parse(['backup'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'backup')
        self.assertIn('func', args)
        self.assertIs(args.func, backintime.backup)

    def test_cmd_backup_backwards_compatiblity_alias(self):
        args = backintime.arg_parse(['--backup'])
        self.assertIn('func', args)
        self.assertIs(args.func, backintime.aliasParser)
        self.assertIn('replace', args)
        self.assertEqual(args.replace, '--backup')
        self.assertIn('alias', args)
        self.assertEqual(args.alias, 'backup')

    def test_cmd_backup_profile(self):
        for argv in shuffleArgs('backup', ('--profile', 'foo')):
            with self.subTest(argv = argv):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'argv = %s' %argv
                args = backintime.arg_parse(argv)
                self.assertIn('command', args, msg)
                self.assertEqual(args.command, 'backup', msg)
                self.assertIn('profile', args, msg)
                self.assertEqual(args.profile, 'foo', msg)

    def test_cmd_backup_profile_id(self):
        args = backintime.arg_parse(['backup', '--profile-id', '2'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'backup')
        self.assertIn('profile_id', args)
        self.assertEqual(args.profile_id, 2)

    def test_cmd_backup_profile_and_profile_id(self):
        self.assertRaises(SystemExit, backintime.arg_parse, ['backup', '--profile', 'foo', '--profile-id', '2'])

    def test_cmd_backup_debug(self):
        args = backintime.arg_parse(['backup', '--debug'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'backup')
        self.assertIn('debug', args)
        self.assertTrue(args.debug)

    def test_cmd_backup_multi_args(self):
        for argv in shuffleArgs('--debug', 'backup', ('--profile', 'foo'), '--checksum',
                                ('--config', 'bar')):
            with self.subTest(argv = argv):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'argv = %s' %argv
                args = backintime.arg_parse(argv)
                self.assertIn('command', args, msg)
                self.assertEqual(args.command, 'backup', msg)
                self.assertIn('profile', args, msg)
                self.assertEqual(args.profile, 'foo', msg)
                self.assertIn('debug', args, msg)
                self.assertTrue(args.debug, msg)
                self.assertIn('checksum', args, msg)
                self.assertTrue(args.checksum, msg)
                self.assertIn('config', args, msg)
                self.assertEqual(args.config, 'bar', msg)

    ############################################################################
    ###                               Restore                                ###
    ############################################################################
    def test_cmd_restore(self):
        args = backintime.arg_parse(['restore'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'restore')
        self.assertIn('func', args)
        self.assertIs(args.func, backintime.restore)

    def test_cmd_restore_what_where_snapshot_id(self):
        args = backintime.arg_parse(['restore', '/home', '/tmp', '20151130-230501-984'])
        self.assertIn('command', args)
        self.assertEqual(args.command, 'restore')
        self.assertIn('WHAT', args)
        self.assertEqual(args.WHAT, '/home')
        self.assertIn('WHERE', args)
        self.assertEqual(args.WHERE, '/tmp')
        self.assertIn('SNAPSHOT_ID', args)
        self.assertEqual(args.SNAPSHOT_ID, '20151130-230501-984')

    def test_cmd_restore_what_where_snapshot_id_multi_args(self):
        for argv in shuffleArgs('--debug', ('restore', '/home', '/tmp', '20151130-230501-984'),
                                '--checksum', ('--profile-id', '2'), '--local-backup',
                                '--delete', ('--config', 'foo')):
            with self.subTest(argv = argv):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'argv = %s' %argv
                args = backintime.arg_parse(argv)
                self.assertIn('debug', args, msg)
                self.assertTrue(args.debug, msg)
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

    def test_cmd_restore_multi_args(self):
        for argv in shuffleArgs(('--profile-id', '2'), '--debug', 'restore', '--checksum',
                                '--local-backup',
                                '--delete', ('--config', 'foo')):
            with self.subTest(argv = argv):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'argv = %s' %argv
                print(msg)
                args = backintime.arg_parse(argv)
                self.assertIn('debug', args, msg)
                self.assertTrue(args.debug, msg)
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

    def test_cmd_restore_snapshot_id_index(self):
        args = backintime.arg_parse(['restore', '/home', '/tmp', '1'])
        self.assertIn('SNAPSHOT_ID', args)
        self.assertEqual(args.SNAPSHOT_ID, '1')

    def test_cmd_restore_empty_where(self):
        args = backintime.arg_parse(['restore', '/home', '', '20151130-230501-984'])
        self.assertIn('WHERE', args)
        self.assertEqual(args.WHERE, '')

    def test_cmd_restore_where_space_in_path(self):
        args = backintime.arg_parse(['restore', '/home', '/tmp/foo bar/baz', '20151130-230501-984'])
        self.assertIn('WHERE', args)
        self.assertEqual(args.WHERE, '/tmp/foo bar/baz')

    def test_cmd_restore_what_space_in_path(self):
        args = backintime.arg_parse(['restore', '/home/foo bar/baz', '/tmp', '20151130-230501-984'])
        self.assertIn('WHAT', args)
        self.assertEqual(args.WHAT, '/home/foo bar/baz')

    def test_cmd_restore_local_backup_and_no_local_backup(self):
        self.assertRaises(SystemExit, backintime.arg_parse, ('restore', '--local-backup', '--no-local-backup'))
