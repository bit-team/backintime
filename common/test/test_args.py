# SPDX-FileCopyrightText: © 2015-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
# pylint: disable=missing-function-docstring, wrong-import-position
"""Tests about argument parsings."""
import unittest
import os
import sys
import itertools
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import bitbase  # noqa: E402, RUF100
import cliarguments  # noqa: E402, RUF100
import clicommands  # noqa: E402, RUF100


def shuffle_args(*args):
    """Return every possible combination of arguments.

    Those arguments which need to keep in line have to be inside a tuple.

    Args:
        args: Two or more arguments (str)

    """
    for i in itertools.permutations(args):
        ret = []

        for j in i:
            if isinstance(j, (tuple, list)):
                ret.extend(j)
            else:
                ret.append(j)

        yield ret


class Basics(unittest.TestCase):
    """Basic tests about parsing arguments."""

    def setUp(self):
        super().setUp()
        self.parser_agent = cliarguments.ParserAgent(
            app_name=bitbase.APP_NAME,
            bin_name=bitbase.BINARY_NAME_CLI)

    def test_invalid_arg(self):
        sut = [
            ['not_existing_command'],
            ['--not_existing_command'],
        ]

        for args in sut:
            with self.assertRaises(SystemExit):
                cliarguments.parse_arguments(args, self.parser_agent)

    def test_config(self):
        sut = cliarguments.parse_arguments(
            ['--config', '/tmp/config'], self.parser_agent)

        self.assertIn('config', sut)
        self.assertEqual(sut.config, '/tmp/config')

    def test_config_no_path(self):
        with self.assertRaises(SystemExit):
            cliarguments.parse_arguments(['--config'], self.parser_agent)

    def test_quiet(self):
        sut = cliarguments.parse_arguments(['--quiet',], self.parser_agent)

        self.assertIn('quiet', sut)
        self.assertTrue(sut.quiet)

    def test_debug(self):
        sut = cliarguments.parse_arguments(['--debug',], self.parser_agent)

        self.assertIn('debug', sut)
        self.assertTrue(sut.debug)


class BackupCommand(unittest.TestCase):
    """Tests about arguments related to the 'backup' command."""

    def setUp(self):
        super().setUp()
        self.parser_agent = cliarguments.ParserAgent(
            app_name=bitbase.APP_NAME,
            bin_name=bitbase.BINARY_NAME_CLI)

    def test_simple(self):
        sut = cliarguments.parse_arguments(['backup'], self.parser_agent)
        self.assertEqual(sut.command, 'backup')
        self.assertIs(sut.func, clicommands.backup)

    # def test_backwards_compatiblity_alias(self):
    #     args = backintime.argParse(['--backup'])
    #     self.assertIn('func', args)
    #     self.assertIs(args.func, backintime.aliasParser)
    #     self.assertIn('replace', args)
    #     self.assertEqual(args.replace, '--backup')
    #     self.assertIn('alias', args)
    #     self.assertEqual(args.alias, 'backup')

    def test_profile(self):
        for argv in shuffle_args('backup', ('--profile', 'foo')):
            sut = cliarguments.parse_arguments(argv, self.parser_agent)
            self.assertEqual(sut.command, 'backup')
            self.assertEqual(sut.profile, 'foo')

    def test_profile_id(self):
        sut = cliarguments.parse_arguments(
            ['backup', '--profile-id', '2'], self.parser_agent)

        self.assertEqual(sut.command, 'backup')
        self.assertIsInstance(sut.profile_id, int)
        self.assertEqual(sut.profile_id, 2)

    def test_profile_and_profile_id(self):
        with self.assertRaises(SystemExit):
            cliarguments.parse_arguments(
                ['backup', '--profile', 'foo', '--profile-id', '2'],
                self.parser_agent)

    def test_quiet(self):
        args = cliarguments.parse_arguments(
            ['backup', '--quiet'], self.parser_agent)

        self.assertEqual(args.command, 'backup')
        self.assertEqual(args.quiet, True)

    def test_multible_args(self):
        for argv in shuffle_args('--quiet',
                                 'backup',
                                 ('--profile', 'foo'),
                                 '--checksum',
                                 ('--config', 'bar')):

            sut = cliarguments.parse_arguments(argv, self.parser_agent)
            self.assertEqual(sut.command, 'backup')
            self.assertEqual(sut.profile, 'foo')
            self.assertEqual(sut.quiet, True)
            self.assertEqual(sut.checksum, True)
            self.assertEqual(sut.config, 'bar')


class RestoreCommand(unittest.TestCase):
    """Tests about arguments related to the 'restore' command."""

    def setUp(self):
        super().setUp()
        self.parser_agent = cliarguments.ParserAgent(
            app_name=bitbase.APP_NAME,
            bin_name=bitbase.BINARY_NAME_CLI)

    def test_simple(self):
        sut = cliarguments.parse_arguments(['restore'], self.parser_agent)
        self.assertEqual(sut.command, 'restore')
        self.assertIs(sut.func, clicommands.restore)

    def test_what_where_snapshot_id(self):
        sut = cliarguments.parse_arguments(
            ['restore', '/home', '/tmp', '20151130-230501-984'],
            self.parser_agent)

        self.assertEqual(sut.command, 'restore')
        self.assertEqual(sut.WHAT, '/home')
        self.assertEqual(sut.WHERE, '/tmp')
        self.assertEqual(sut.BACKUP_ID, '20151130-230501-984')

    def test_what_where_snapshot_id_multi_args(self):
        for argv in shuffle_args('--quiet',
                                 (
                                     'restore',
                                     '/home',
                                     '/tmp',
                                     '20151130-230501-984'
                                 ),
                                 '--checksum',
                                 ('--profile-id', '2'),
                                 '--local-backup',
                                 '--delete',
                                 ('--config', 'foo')):
            sut = cliarguments.parse_arguments(argv, self.parser_agent)

            self.assertEqual(sut.quiet, True)
            self.assertEqual(sut.checksum, True)
            self.assertEqual(sut.profile_id, 2)
            self.assertEqual(sut.command, 'restore')
            self.assertEqual(sut.WHAT, '/home')
            self.assertEqual(sut.WHERE, '/tmp')
            self.assertEqual(sut.BACKUP_ID, '20151130-230501-984')
            self.assertEqual(sut.local_backup, True)
            self.assertEqual(sut.delete, True)
            self.assertEqual(sut.config, 'foo')

    def test_multible_args(self):
        for argv in shuffle_args(('--profile-id', '2'),
                                 '--quiet',
                                 'restore',
                                 '--checksum',
                                 '--local-backup',
                                 '--delete',
                                 ('--config', 'foo')):
            sut = cliarguments.parse_arguments(argv, self.parser_agent)

            self.assertEqual(sut.quiet, True)
            self.assertEqual(sut.checksum, True)
            self.assertEqual(sut.profile_id, 2)
            self.assertEqual(sut.command, 'restore')
            self.assertEqual(sut.local_backup, True)
            self.assertEqual(sut.delete, True)
            self.assertEqual(sut.config, 'foo')

    def test_snapshot_id_index(self):
        sut = cliarguments.parse_arguments(
            ['restore', '/home', '/tmp', '1'], self.parser_agent)

        self.assertIsInstance(sut.BACKUP_ID, str)
        self.assertEqual(sut.BACKUP_ID, '1')

    def test_empty_where(self):
        sut = cliarguments.parse_arguments(
            ['restore', '/home', '', '20151130-230501-984'], self.parser_agent)

        self.assertEqual(sut.WHERE, '')

    def test_where_space_in_path(self):
        sut = cliarguments.parse_arguments(
            ['restore', '/home', '/tmp/foo bar/baz', '20151130-230501-984'],
            self.parser_agent)

        self.assertEqual(sut.WHERE, '/tmp/foo bar/baz')

    def test_what_space_in_path(self):
        sut = cliarguments.parse_arguments(
            ['restore', '/home/foo bar/baz', '/tmp', '20151130-230501-984'],
            self.parser_agent
        )

        self.assertEqual(sut.WHAT, '/home/foo bar/baz')

    def test_local_backup_and_no_local_backup(self):
        with self.assertRaises(SystemExit):
            cliarguments.parse_arguments(
                ('restore', '--local-backup', '--no-local-backup'),
                self.parser_agent
            )


if __name__ == '__main__':
    unittest.main()
