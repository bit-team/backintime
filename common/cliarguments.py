# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Split from backintime.py
"""Module about CLI argument parsing and parsers.

A note about conventions:
 - Help text starts with lower letter, with the exception of names.
 - Help text ends not with a period.

Example (good):
    --help    show this help


Example (don't):
    --help    Show this help.

"""
import sys
import argparse
import json
import re
import tools
# Workaround for situations where startApp() is not invoked.
# E.g. when using --diagnostics and other argparse.Action
tools.initiate_translation(None)
import bitbase  # noqa: E402
import diagnostics  # noqa: E402
import logger  # noqa: E402
import clicommands  # noqa: E402
from argparse import (ArgumentParser,  # noqa: E402
                      Namespace,
                      Action,
                      )
from pathlib import Path  # noqa: E402
from version import __version__  # noqa: E402


def _license_info() -> tuple[str, str]:
    """Collect license info.

    The projects primary license is extracted from SPDX head of the current
    file. Additional licenses in use are extracted from the filenames in
    LICENSES directory. This info is combined and returned as two strings.

    Returns:
        Primary or project license and additional licenses.

    """
    # Extract the SPDX license info from current file.
    # interpreted as primary/project license
    prim = re.search(
        r'SPDX-License-Identifier:\s(:?.*)',
        Path(__file__).read_text(encoding='utf-8')
    )

    try:
        result = prim.groups()[0]

    except (AttributeError, IndexError):
        result = None

    # all used licenses
    licenses = None
    if bitbase.DIR_LICENSES:
        licenses = [
            f.with_suffix('').name for f in bitbase.DIR_LICENSES.iterdir()]

        if result:
            licenses.remove(result)
            licenses = ', '.join(licenses)

    # combine
    result = (result, licenses)

    # any errors?
    if not result[0]:
        result = (
            f'Unable to extract license info from {__file__}',
            result[1])
        logger.error(result[0])

    if not result[1]:
        result = (
            result[0], 'Unable to extract licenses from LICENSES directory.')
        logger.error(result[1])

    return result


class ParserAgent:
    """Create and manage all parsers."""

    def __init__(self,
                 app_name: str,
                 bin_name: str
                 ):
        # Name of the application e.g. "Back In Time"
        self.app_name = app_name

        # Name of the binary e.g. "backintime"
        self.bin_name = bin_name

        # Mapping the command names to their handler functions
        self._cmd_func_dict = {
            'backup': clicommands.backup,
            'check-config': clicommands.check_config,
            'pw-cache': clicommands.pw_cache,
            'remove': clicommands.remove,
            'restore': clicommands.restore,
            'shutdown': clicommands.shutdown,
            'prune': clicommands.prune,
            'show': clicommands.show_backups,
            'unmount': clicommands.unmount,
            # Deprecated commands (#2124)
            'decode': clicommands.decode,
            'backup-job': clicommands.backup_job,
            'smart-remove': clicommands.smart_remove,
            'remove-and-do-not-ask-again':
                clicommands.remove_and_donot_ask_again,
            # See #2120
            'benchmark-cipher': clicommands.benchmark_cipher,
            # See #2130 for this five commands
            'snapshots-path': clicommands.snapshots_path,
            'last-snapshot': clicommands.last_snapshot,
            'last-snapshot-path': clicommands.last_snapshot_path,
            'snapshots-list': clicommands.snapshots_list,
            'snapshots-list-path': clicommands.snapshots_list_path,
        }

        # Public parsers indexed by their (command) name
        self.parsers = {}

        # Helper
        self._command_subparsers = None

        # ???
        self._aliases = []

        # Used as epilog for command parses
        self._reusable_parsers = {}

        # Start creating all parsers, etc
        self._create_reusable_parsers()
        self._create_main_parser()
        self._create_command_parsers()

    def _build_epilog(self):
        # Create with "Text ASCII Generator" by "patorjk"
        # https://patorjk.com/software/taag
        # Font used is "Mini"
        logo = '\n'.join([
            r'  _              ___       ___',
            r' |_)  _.  _ |     |  ._     | o ._ _   _   Version:',
            rf' |_) (_| (_ |<   _|_ | |    | | | | | (/_  {__version__}'
        ])

        prj_license, add_licenses = _license_info()

        epi = '\n'.join([
            logo,
            '',
            f'            Project : {bitbase.URL_WEBSITE}',
            f'        User Manual : {bitbase.USER_MANUAL_ONLINE_URL}',
            '          Copyright : see file LICENSES.md',
            f'    Project License : {prj_license}',
            f'Additional Licenses : {add_licenses}',
        ])

        return epi

    def _create_reusable_parsers(self):
        self._create_common_parser()
        self._create_profile_parser()
        self._create_snapshots_only_parser()  # deprecated
        self._create_rsync_only_parser()

    @property
    def main_parser(self) -> ArgumentParser:
        """The main parser"""
        return self.parsers['main']

    def _create_main_parser(self):
        """Main argument parser"""
        parser = ArgumentParser(
            prog=self.bin_name,
            parents=[
                self._reusable_parsers['profile'],
                self._reusable_parsers['common']
            ],
            description=f'command-line interface (CLI) for {self.app_name}, '
                        'to create and manage incremental backups',
            epilog=self._build_epilog(),
            # because of ASCII art in epilog
            formatter_class=argparse.RawTextHelpFormatter,
            allow_abbrev=False
        )

        self.parsers['main'] = parser

        parser.add_argument(
            '-v', '--version',
            action='version',
            version='%(prog)s ' + __version__,
            help="show %(prog)s's version number.")

        parser.add_argument(
            '--license',
            action=ActionPrintLicense,
            nargs=0,
            help="show %(prog)s's license")

        parser.add_argument(
            '--diagnostics',
            action=ActionPrintDiagnostics,
            nargs=0,
            help='show helpful info (in JSON format) for better support in '
                 'case of issues')

    def _create_common_parser(self) -> ArgumentParser:
        """Common arguments used independent from commands"""

        parser = ArgumentParser(add_help=False)

        parser.add_argument(
            '--config',
            metavar='PATH',
            type=str,
            action='store',
            help='read config from %(metavar)s '
                 '(Default: $XDG_CONFIG_HOME/backintime/config)')

        parser.add_argument(
            '--share-path',
            metavar='PATH',
            type=str,
            action='store',
            # Hide because deprecated (#2125)
            help=argparse.SUPPRESS
            # help='Write runtime data (locks, messages, log and '
            #      'mountpoints) to %(metavar)s.'
        )

        parser.add_argument(
            '--quiet',
            action='store_true',
            help='be quiet and suppress messages on stdout')

        parser.add_argument(
            '--debug',
            action='store_true',
            default=False,
            help='increase verbosity')

        self._reusable_parsers['common'] = parser

    def _create_profile_parser(self):
        """Parser used by commands with profile selection involved."""

        parser = ArgumentParser(add_help=False)

        # Allow only one of "--profile" or "--profile-id"
        profile_group = parser.add_mutually_exclusive_group()

        profile_group.add_argument(
            '--profile', '-p',
            metavar='NAME|ID',
            type=str,
            action='store',
            help='select profile by name or id'
        )

        # Deprecated (#2125)
        profile_group.add_argument(
            '--profile-id',
            metavar='ID',
            type=int,
            action='store',
            help=argparse.SUPPRESS)

        self._reusable_parsers['profile'] = parser

    def _create_snapshots_only_parser(self):
        """Arguments used only by commands
            - snapshots-path
            - snapshots-list-path
            - last-snapshot-path
        """
        parser = ArgumentParser(add_help=False)
        parser.add_argument(
            '--keep-mount',
            action='store_true',
            help="Don't unmount on exit.")

        self._reusable_parsers['snapshots'] = parser

    def _create_rsync_only_parser(self):
        """Arguments used only by rsync related commands:
            - backup
            - restore
        """
        parser = ArgumentParser(add_help=False)
        parser.add_argument(
            '--checksum',
            action='store_true',
            help='force to use checksum for checking if '
                 'files have been changed.')

        self._reusable_parsers['rsync'] = parser

    def _create_cmd_backup(self):
        name = 'backup'
        nargs = 0
        self._aliases.append((name, nargs))
        self._aliases.append(('b', nargs))

        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['profile'],
                self._reusable_parsers['rsync'],
                self._reusable_parsers['common'],
            ],
            help='create new backup, if scheduled and not on battery',
            description='Create a new backup, but only if the profile is '
                        'scheduled and if the machine is not running on '
                        'battery.'
        )

        parser.set_defaults(func=self._cmd_func_dict[name])

        parser.add_argument(
            '--background',
            action='store_true',
            default=False,
            help='run in background via daemonization',
        )

        self.parsers[name] = parser

    def _create_cmd_backup_job(self):
        name = 'backup-job'
        nargs = 0
        self._aliases.append((name, nargs))

        desc = 'Take a new snapshot in background only if the profile is ' \
               'scheduled and the machine is not on battery. This is used ' \
               'by cron jobs.'
        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['common'],
                self._reusable_parsers['profile'],
                self._reusable_parsers['rsync']
            ],
            help='take new backup in background',
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_benchmark_ciphier(self):
        name = 'benchmark-cipher'
        nargs = '?'
        self._aliases.append((name, nargs))
        desc = 'Show a benchmark of all ciphers for ssh transfer.'

        parser = self._command_subparsers.add_parser(
            name,
            help=None,  # suppress help output
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

        parser.add_argument(
            'FILE_SIZE',
            type=int,
            action='store',
            default=40,
            nargs='?',
            help='File size used for benchmark.')

    def _create_cmd_check_config(self):
        name = 'check-config'
        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['common'],
            ],
            help='check full configuration',
            description='Check configuration of all profiles and '
                        'install crontab entries.'
        )

        parser.add_argument(
            '--no-crontab',
            action='store_true',
            help='Do not install crontab entries.')

        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_decode(self):
        name = 'decode'
        nargs = '*'
        self._aliases.append((name, nargs))

        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['profile'],
                self._reusable_parsers['common'],
            ],
            help='decode paths in encrypted profiles',
            description="Decode paths with 'encfsctl decode'."
        )

        parser.set_defaults(func=self._cmd_func_dict[name])

        parser.add_argument(
            'PATH',
            type=str,
            action='store',
            nargs='*',
            help='Decode PATH. If no PATH is specified on command line '
                 'a list of filenames will be read from stdin.')

        self.parsers[name] = parser

    def _create_cmd_last_snapshot(self):
        name = 'last-snapshot'
        nargs = 0
        self._aliases.append((name, nargs))
        desc = 'Show the ID of the last snapshot.'

        parser = self._command_subparsers.add_parser(
            name,
            help=None,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_last_snapshot_path(self):
        name = 'last-snapshot-path'
        nargs = 0
        self._aliases.append((name, nargs))
        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._reusable_parsers['snapshots']],
        )

        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_pw_cache(self):
        name = 'pw-cache'
        nargs = '*'
        self._aliases.append((name, nargs))

        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._reusable_parsers['common']],
            help='control Password Cache',
            description='Control Password Cache for non-interactive cronjobs.')

        parser.set_defaults(func=self._cmd_func_dict[name])

        parser.add_argument(
            'ACTION',
            action='store',
            choices=['start', 'stop', 'restart', 'reload', 'status'],
            nargs='?',
            help='command to send to Password Cache daemon')

        self.parsers[name] = parser

    def _create_cmd_remove(self):
        name = 'remove'
        nargs = '*'
        self._aliases.append((name, nargs))
        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['profile'],
                self._reusable_parsers['common'],
            ],
            help='remove a backup',
            description='Remove a backup.')

        parser.set_defaults(func=self._cmd_func_dict[name])

        parser.add_argument(
            'BACKUP_ID',
            type=str,
            action='store',
            nargs='*',
            help='ID of backup to be removed')

        parser.add_argument(
            '--skip-confirmation',
            action='store_true',
            default=False,
            help='skip confirmation question; be careful!'
        )

        self.parsers[name] = parser

    def _create_cmd_remove_and_donot_ask_again(self):
        name = 'remove-and-do-not-ask-again'
        nargs = '*'
        self._aliases.append((name, nargs))

        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['common'],
                self._reusable_parsers['profile']
            ],
            help=name,  # On purpose, because the command name is to long.
                        # Otherwise print_usage_without_deprecations() won't
                        # work.
            description="Remove backup and don't ask for confirmation "
                        "before."
        )

        parser.set_defaults(func=self._cmd_func_dict[name])

        parser.add_argument(
            'BACKUP_ID',
            type=str,
            action='store',
            nargs='*',
            help='ID of snapshots which should be removed.')

        self.parsers[name] = parser

    def _create_cmd_restore(self):
        name = 'restore'
        nargs = '*'
        self._aliases.append((name, nargs))

        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['profile'],
                self._reusable_parsers['rsync'],
                self._reusable_parsers['common'],
            ],
            help='restores backup or files or folders from them',
            description='Restores entire backups or selected files and '
                        'folders from them.'
        )

        parser.set_defaults(func=self._cmd_func_dict[name])

        backup_group = parser.add_mutually_exclusive_group()

        parser.add_argument(
            'WHAT',
            type=str,
            action='store',
            nargs='?',
            help='restore file or directory WHAT')

        parser.add_argument(
            'WHERE',
            type=str,
            action='store',
            nargs='?',
            help='restore to WHERE; empty argument will default to '
                 'original destination')

        parser.add_argument(
            'BACKUP_ID',
            type=str,
            action='store',
            nargs='?',
            help='specific ID or an integer as index (0=last backup; -1=very '
                 'first backup)')

        parser.add_argument(
            '--delete',
            action='store_true',
            help='Restore and delete newer files which are not in the '
                 'snapshot. WARNING: deleting files in filesystem root could '
                 'break your whole system!!!')

        backup_group.add_argument(
            '--local-backup',
            action='store_true',
            help='Create backup files before changing local files.')

        backup_group.add_argument(
            '--no-local-backup',
            action='store_true',
            help='Temporarily disable creation of backup files before '
                 'changing local files. This can be switched off permanently '
                 'in Settings, too.')

        parser.add_argument(
            '--only-new',
            action='store_true',
            help='Only restore files which do not exist or are newer than '
                 'those in destination. Using "rsync --update" option.')

        self.parsers[name] = parser

    def _create_cmd_shutdown(self):
        name = 'shutdown'
        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['profile'],
                self._reusable_parsers['common'],
            ],
            help='shutdown after backup',
            description='Shut down the computer after the backup is finished.'
        )

        parser.set_defaults(func=self._cmd_func_dict[name])

        self.parsers[name] = parser

    def _create_cmd_smart_remove(self):
        name = 'smart-remove'
        desc = 'Remove snapshots based on "Smart Removal" pattern.'

        parser = self._command_subparsers.add_parser(
            name,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])

        self.parsers[name] = parser

    def _create_cmd_prune(self):
        name = 'prune'

        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['profile'],
                self._reusable_parsers['common'],
            ],
            help='prune backups based on configured "Remove & '
                 'Retention" rules',
            description='Remove and keep backups based on "Remove & '
                        'Retention" policy.'
        )

        parser.set_defaults(func=self._cmd_func_dict[name])

        self.parsers[name] = parser

    def _create_cmd_snapshots_list(self):
        name = 'snapshots-list'
        nargs = 0
        self._aliases.append((name, nargs))
        desc = 'Show a list of snapshot IDs.'

        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._reusable_parsers['snapshots']],
            help=None,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])

        self.parsers[name] = parser

    def _create_cmd_snapshots_list_path(self):
        name = 'snapshots-list-path'
        nargs = 0
        self._aliases.append((name, nargs))
        desc = "Show the paths to snapshots."

        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._reusable_parsers['snapshots']],
            help=None,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_snapshots_path(self):
        name = 'snapshots-path'
        nargs = 0
        self._aliases.append((name, nargs))
        desc = 'Show the path where snapshots are stored.'
        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._reusable_parsers['snapshots']],
            help=None,  # suppress help output
            description=desc)
        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_show(self):
        name = 'show'

        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['profile'],
                self._reusable_parsers['common'],
            ],
            help='show information about backups',
            description="List backup ID's (default) or paths (--path) or "
                        "just the last (--last)",
            allow_abbrev=False
        )

        parser.set_defaults(func=self._cmd_func_dict[name])

        parser.add_argument(
            '--path',
            action='store_true',
            default=False,
            help='list backup paths instead of their ID')

        parser.add_argument(
            '--last',
            action='store_true',
            default=False,
            help='show the last (youngest) backup only')

        self.parsers[name] = parser

    def _create_cmd_unmount(self):
        name = 'unmount'
        nargs = 0
        self._aliases.append((name, nargs))
        parser = self._command_subparsers.add_parser(
            name,
            parents=[
                self._reusable_parsers['profile'],
                self._reusable_parsers['common'],
            ],
            help='unmount the profile',
            description='Unmount the profile.'
        )
        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_aliase_switches(self):
        # define aliases for all commands with trailing --
        # DEPRECATED and REMOVE it
        group = self.parsers['main'].add_mutually_exclusive_group()

        for alias, nargs in self._aliases:

            arg = f'-{alias}'
            if len(alias) != 1:
                arg = f'-{arg}'

            logger.debug(f'COMANND ALIAS: "{alias}" -> "{arg}"', self)
            group.add_argument(
                arg,
                nargs=nargs,
                action=PseudoAliasAction,
                # Don't show that alias in help (-h | --help) output
                help=argparse.SUPPRESS
            )

    def _create_command_parsers(self):
        self._command_subparsers = self.parsers['main'].add_subparsers(
            title='Commands', dest='command')

        self._create_cmd_backup()
        self._create_cmd_backup_job()
        self._create_cmd_show()
        self._create_cmd_restore()
        self._create_cmd_remove()
        self._create_cmd_remove_and_donot_ask_again()
        self._create_cmd_prune()
        self._create_cmd_smart_remove()
        self._create_cmd_unmount()
        self._create_cmd_shutdown()
        self._create_cmd_benchmark_ciphier()
        self._create_cmd_check_config()
        self._create_cmd_decode()
        self._create_cmd_pw_cache()
        self._create_cmd_last_snapshot()
        self._create_cmd_last_snapshot_path()
        self._create_cmd_snapshots_list()
        self._create_cmd_snapshots_list_path()
        self._create_cmd_snapshots_path()

        self._create_cmd_aliase_switches()


def print_usage_without_deprecations(parser):
    """Hidde commands form the parsers help output, print it and exit.

    This is a workaround because argparse can suppress arguments but not
    commands (subparsers). The help output contain a online list of
    commands. This line is the one that gets manipulated here.

        Commands:
            {backup,backup-job,check-config,...,unmount}

    A second location where a command appears is the line-by-line help output.

        Commands:
            backup      Bla bla
            foo         bar

    """
    text = parser.format_help().splitlines()
    # for idx, t in enumerate(text):
    #     print(f'{idx=} {t=}')

    deprecated_cmds = [
        'benchmark-cipher',
        'snapshots-path',
        'last-snapshot',
        'last-snapshot-path',
        'snapshots-list',
        'snapshots-list-path',
        'backup-job',
        'smart-remove',
        'remove-and-do-not-ask-again',
        'decode',
    ]

    def _remove_cmds_from_cmd_list(line: str):
        """Remove all deprecated commands from that one line like this:

            {backup,backup-job,check-config,...,unmount}

        Usually there are two of this lines in a help-usage-output.
        """
        for cmd in deprecated_cmds:
            # replace "cmd" between delemiters with ","
            pattern = r'(?<=[{,])' + re.escape(cmd) + r'(?=[,}])'
            line = re.sub(pattern, ',', line)
            # clean up to much ","
            line = re.sub(r',+', ',', line)
            line = re.sub(r'{,', '{', line)
            line = re.sub(r',}', '}', line)

        return line

    rex = re.compile(r'.*{.*}.*')
    line_idx_to_remove = []

    for idx, line in enumerate(text[:]):
        # Remove commands from the one-line-list
        if rex.match(line):
            text[idx] = _remove_cmds_from_cmd_list(line)
            continue

        # Line-by-line command description?
        for cmd in deprecated_cmds:
            pattern = r'\s+' + re.escape(cmd) + r'(?=\s|$)'
            if re.match(pattern, line):
                line_idx_to_remove.append(idx)
                continue

    # remove lines with deprecated commands
    for idx in reversed(line_idx_to_remove):
        del text[idx]

    print('\n'.join(text))
    sys.exit(0)


def parse_arguments(args: Namespace,
                    agent: ParserAgent) -> Namespace:
    """Parse arguments given on commandline.

    Args:
        args: Namespace that should be enhanced or ``None``.

    Returns:
        New parsed Namespace.
    """

    def join(args, sub_args):
        """
        Add new arguments to existing Namespace.

        Args:
            args (argparse.Namespace):
                        main Namespace that should get new arguments
            sub_args (argparse.Namespace):
                        second Namespace which have new arguments
                        that should be merged into ``args``
        """
        for key, value in vars(sub_args).items():
            # Only add new values if it isn't set already or if there really IS
            # a value
            if getattr(args, key, None) is None or value:
                setattr(args, key, value)

    # First parse the main parser without subparsers
    # otherwise positional args in subparsers will be to greedy
    # but only if -h or --help is not involved because otherwise
    # help will not work for subcommands
    main_parser = agent.main_parser
    sub = []

    if '-h' not in sys.argv and '--help' not in sys.argv:

        for i in main_parser._actions:

            if isinstance(i, argparse._SubParsersAction):
                # Remove subparsers
                main_parser._remove_action(i)
                sub.append(i)

    else:
        # Manipulate the main parsers output only (not the subparsers)
        if sys.argv[1] in ['-h', '--help']:
            print_usage_without_deprecations(main_parser)

    args, unknown_args = main_parser.parse_known_args(args)

    # Read subparsers again
    for i in sub:
        main_parser._add_action(i)

    # Parse it again for unknown args
    if unknown_args:
        sub_args, unknown_args = main_parser.parse_known_args(unknown_args)
        join(args, sub_args)

    # Finally parse only the command parser, otherwise we miss some arguments
    # from command
    if (unknown_args
            and 'command' in args
            and args.command in agent.parsers):
        cmd_parser = agent.parsers[args.command]
        sub_args, unknown_args = cmd_parser.parse_known_args(unknown_args)
        join(args, sub_args)

    try:
        logger.DEBUG = args.debug
    except AttributeError:
        pass

    args_dict = vars(args)
    used_args = {
        key: args_dict[key]
        for key
        in filter(lambda key: args_dict[key] is not None, args_dict)
    }

    logger.debug(f'Argument(s) used: {used_args}')

    # Deprecated (#2125)
    if args.profile_id:
        clicommands.show_deprecation_message('--profile-id')
        args.profile = str(args.profile_id)

    if args.share_path:
        clicommands.show_deprecation_message('--share-path')

    # Report unknown arguments but not if we run aliasParser next because we
    # will parse again in there.
    if unknown_args and not ('func' in args and args.func is alias_parser):
        main_parser.error(f'Unknown argument(s): {unknown_args}')

    return args


class ActionPrintLicense(argparse.Action):
    """Print license text."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        license_path = Path(tools.docPath()) / 'LICENSE'
        # Dev note (buhtz, 2025-05): ToDo
        # display aboutdlg license text (see bitbase)
        # and show path of all license files in LICENSES dir
        print(license_path.read_text('utf-8'))
        sys.exit(bitbase.RETURN_OK)


class ActionPrintDiagnostics(argparse.Action):
    """See `collect_diagnostics()` for details."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        data = diagnostics.collect_diagnostics()
        print(json.dumps(data, indent=4))
        sys.exit(bitbase.RETURN_OK)


def alias_parser(args: Namespace):
    """Call commands which where given with leading -- for backwards
    compatibility.

    Args:
        args: Previously parsed arguments
    """

    if not args.quiet:
        logger.info(f"Run command '{args.alias}' instead of argument "
                    f"'{args.replace}' due to backwards compatibility.")

    msg = (
        f'The command alias "{args.replace}" is deprecated and will be '
        'removed from Back In Time in the foreseeable future, without any '
        'replacement.')
    # ToDo: Switch this later to ERROR
    logger.warning(msg)

    argv = [w.replace(args.replace, args.alias) for w in sys.argv[1:]]

    new_args = parse_arguments(
        argv,
        agent=ParserAgent(bitbase.APP_NAME, 'backintime')
    )

    if 'func' in dir(new_args):
        new_args.func(new_args)


class PseudoAliasAction(Action):
    """Translate '--COMMAND' into 'COMMAND' for backwards compatibility.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        """
        Args:
            parser (argparse.ArgumentParser): NotImplemented
            namespace (argparse.Namespace): Namespace that should get modified
            values: NotImplemented
            option_string: NotImplemented
        """
        dest = self.dest.replace('_', '-')

        if self.dest == 'b':
            replace = '-b'
            alias = 'backup'

        else:
            replace = f'--{dest}'
            alias = dest

        setattr(namespace, 'func', alias_parser)
        setattr(namespace, 'replace', replace)
        setattr(namespace, 'alias', alias)
