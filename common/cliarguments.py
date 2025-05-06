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
"""Module about CLI argument parsing and parsers."""
import sys
import argparse
import json
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
            'backup-job': clicommands.backup_job,
            'benchmark-cipher': clicommands.benchmark_cipher,
            'check-config': clicommands.check_config,
            'decode': clicommands.decode,
            'last-snapshot': clicommands.last_snapshot,
            'last-snapshot-path': clicommands.last_snapshot_path,
            'pw-cache': clicommands.pw_cache,
            'remove': clicommands.remove,
            'remove-and-do-not-ask-again':
                clicommands.remove_and_donot_ask_again,
            'restore': clicommands.restore,
            'shutdown': clicommands.shutdown,
            'snapshots-path': clicommands.snapshots_path,
            'snapshots-list': clicommands.snapshots_list,
            'snapshots-list-path': clicommands.snapshots_list_path,
            'smart-remove': clicommands.smart_remove,
            'unmount': clicommands.unmount,
        }

        # Public parsers indexed by their (command) name
        self.parsers = {}

        # Helper
        self._command_subparsers = None

        # ???
        self._aliases = []

        # Used as epilog for command parses
        epilog = "Run '%(prog)s -h' to get help for additional arguments."
        self._epilog_cfg = f'{epilog} Additional arguments: --config, --debug'
        self._epilog_com \
            = f'{self._epilog_cfg} --profile, --profile-id, --quiet'

        # Command exclusive parsers
        self._cmd_excl_parsers = {}
        self._create_command_exclusive_parsers()

        # Start creating all parsers, etc
        self._create_main_parser()

        self._create_command_parsers()

    @property
    def main_parser(self) -> ArgumentParser:
        """The main parser"""
        return self.parsers['main']

    def _create_main_parser(self):
        """Main argument parser"""

        desc = f'{self.app_name} - a simple backup tool for GNU/Linux.'
        epi = (
            'For backwards compatibility commands can also be used with '
            "trailing '--'. All listed arguments will work with all commands. "
            "Some commands have extra arguments. Run '%(prog)s <COMMAND> -h' "
            'to see the extra arguments.')

        common_parser = self._create_common_parser()

        parser = ArgumentParser(
            prog=self.bin_name,
            parents=[common_parser],
            description=desc,
            epilog=epi)

        parser.add_argument(
            '--version', '-v',
            action='version',
            version='%(prog)s ' + __version__,
            help="show %(prog)s's version number.")

        parser.add_argument(
            '--license',
            action=ActionPrintLicense,
            nargs=0,
            help="show %(prog)s's license.")

        parser.add_argument(
            '--diagnostics',
            action=ActionPrintDiagnostics,
            nargs=0,
            help='show helpful info (in JSON format) for better support in '
                 'case of issues')

        self.parsers['main'] = parser

    def _create_debug_parser(self) -> ArgumentParser:
        parser = ArgumentParser(add_help=False)
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Increase verbosity.')

        return parser

    def _create_config_parser(self) -> ArgumentParser:
        parser = ArgumentParser(add_help=False)

        parser.add_argument(
            '--config',
            metavar='PATH',
            type=str,
            action='store',
            help='Read config from %(metavar)s. '
                 'Default = ~/.config/backintime/config')

        parser.add_argument(
            '--share-path',
            metavar='PATH',
            type=str,
            action='store',
            help='Write runtime data (locks, messages, log and '
                 'mountpoints) to %(metavar)s.')

        return parser

    def _create_common_parser(self) -> ArgumentParser:
        """Common arguments used by all commands

        """

        debug_parser = self._create_debug_parser()
        config_parser = self._create_config_parser()

        parser = ArgumentParser(
            add_help=False,
            parents=[
                config_parser,
                debug_parser,
            ]
        )

        # Allow only one of "--profile" or "--profile-id"
        profile_group = parser.add_mutually_exclusive_group()

        for switch, name, typ in (('--profile', 'NAME', str),
                                  ('--profile-id', 'ID', int)):
            profile_group.add_argument(
                switch,
                metavar=name,
                type=typ,
                action='store',
                help='Select profile by %(metavar)s.')

        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Be quiet. Suppress messages on stdout.')

        return parser

    def _create_command_exclusive_parsers(self):
        self._create_snapshots_only_parser()
        self._create_rsync_only_parser()
        self._create_remove_only_parser()

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

        self._cmd_excl_parsers['snapshots'] = parser

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

        self._cmd_excl_parsers['rsync'] = parser

    def _create_remove_only_parser(self):
        """Arguments used only by command:
            - remove
        """
        parser = ArgumentParser(add_help=False)
        parser.add_argument(
            'SNAPSHOT_ID',
            type=str,
            action='store',
            nargs='*',
            help='ID of snapshots which should be removed.')

        self._cmd_excl_parsers['remove'] = parser

    def _create_cmd_backup(self):
        name = 'backup'
        nargs = 0
        self._aliases.append((name, nargs))
        self._aliases.append(('b', nargs))

        desc = 'Take a new snapshot. Ignore if the profile is not scheduled ' \
            'or if the machine is running on battery.'

        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._cmd_excl_parsers['rsync']],
            epilog=self._epilog_com,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])
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
            parents=[self._cmd_excl_parsers['rsync']],
            epilog=self._epilog_com,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_benchmark_ciphier(self):
        name = 'benchmark-cipher'
        nargs = '?'
        self._aliases.append((name, nargs))
        desc = 'Show a benchmark of all ciphers for ssh transfer.'

        parser = self._command_subparsers.add_parser(
            name, epilog=self._epilog_com, help=desc, description=desc)

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
        desc = 'Check the profiles configuration and install crontab entries.'
        parser = self._command_subparsers.add_parser(
            name, epilog=self._epilog_com, help=desc, description=desc)

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
        desc = "Decode paths with 'encfsctl decode'"

        parser = self._command_subparsers.add_parser(
            name, epilog=self._epilog_com, help=desc, description=desc)

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
            epilog=self._epilog_com,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_last_snapshot_path(self):
        name = 'last-snapshot-path'
        nargs = 0
        self._aliases.append((name, nargs))
        desc = 'Show the path of the last snapshot.'
        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._cmd_excl_parsers['snapshots']],
            epilog=self._epilog_com,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_pw_cache(self):
        name = 'pw-cache'
        nargs = '*'
        self._aliases.append((name, nargs))
        desc = 'Control Password Cache for non-interactive cronjobs.'

        parser = self._command_subparsers.add_parser(
            name,
            epilog=self._epilog_cfg,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])

        parser.add_argument(
            'ACTION',
            action='store',
            choices=['start', 'stop', 'restart', 'reload', 'status'],
            nargs='?',
            help='Command to send to Password Cache daemon.')

        self.parsers[name] = parser

    def _create_cmd_remove(self):
        name = 'remove'
        nargs = '*'
        self._aliases.append((name, nargs))
        desc = 'Remove a snapshot.'
        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._cmd_excl_parsers['remove']],
            epilog=self._epilog_com,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])

        self.parsers[name] = parser

    def _create_cmd_remove_and_donot_ask_again(self):
        name = 'remove-and-do-not-ask-again'
        nargs = '*'
        self._aliases.append((name, nargs))
        desc = "Remove snapshots and don't ask for confirmation before. " \
               "Be careful!"

        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._cmd_excl_parsers['remove']],
            epilog=self._epilog_com,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])

        self.parsers[name] = parser

    def _create_cmd_restore(self):
        name = 'restore'
        nargs = '*'
        self._aliases.append((name, nargs))
        desc = 'Restore files.'

        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._cmd_excl_parsers['rsync']],
            epilog=self._epilog_com,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])

        backup_group = parser.add_mutually_exclusive_group()

        parser.add_argument(
            'WHAT',
            type=str,
            action='store',
            nargs='?',
            help='Restore file or directory WHAT.')

        parser.add_argument(
            'WHERE',
            type=str,
            action='store',
            nargs='?',
            help="Restore to WHERE. An empty argument '' will restore to "
                 "original destination.")

        parser.add_argument(
            'SNAPSHOT_ID',
            type=str,
            action='store',
            nargs='?',
            help='Which SNAPSHOT_ID should be used. This can be a snapshot ID '
                 'or an integer starting with 0 for the last snapshot, 1 for '
                 'the second to last, ... the very first snapshot is -1')

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
        desc = 'Shut down the computer after the snapshot is done.'
        parser = self._command_subparsers.add_parser(
            name,
            epilog=self._epilog_com,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])

        self.parsers[name] = parser

    def _create_cmd_smart_remove(self):
        name = 'smart-remove'
        desc = 'Remove snapshots based on "Smart Removal" pattern.'

        parser = self._command_subparsers.add_parser(
            name,
            epilog=self._epilog_com,
            help=desc,
            description=desc)

        parser.set_defaults(func=self._cmd_func_dict[name])

        self.parsers[name] = parser

    def _create_cmd_snapshots_list(self):
        name = 'snapshots-list'
        nargs = 0
        self._aliases.append((name, nargs))
        desc = 'Show a list of snapshot IDs.'

        parser = self._command_subparsers.add_parser(
            name,
            parents=[self._cmd_excl_parsers['snapshots']],
            epilog=self._epilog_com,
            help=desc,
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
            parents=[self._cmd_excl_parsers['snapshots']],
            epilog=self._epilog_com,
            help=desc,
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
            parents=[self._cmd_excl_parsers['snapshots']],
            epilog=self._epilog_com,
            help=desc,
            description=desc)
        parser.set_defaults(func=self._cmd_func_dict[name])
        self.parsers[name] = parser

    def _create_cmd_unmount(self):
        name = 'unmount'
        nargs = 0
        self._aliases.append((name, nargs))
        desc = 'Unmount the profile.'
        parser = self._command_subparsers.add_parser(
            name,
            epilog=self._epilog_com,
            help=desc,
            description=desc)
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
        self._create_cmd_benchmark_ciphier()
        self._create_cmd_check_config()
        self._create_cmd_decode()
        self._create_cmd_last_snapshot()
        self._create_cmd_last_snapshot_path()
        self._create_cmd_pw_cache()
        self._create_cmd_remove()
        self._create_cmd_remove_and_donot_ask_again()
        self._create_cmd_restore()
        self._create_cmd_shutdown()
        self._create_cmd_smart_remove()
        self._create_cmd_snapshots_list()
        self._create_cmd_snapshots_list_path()
        self._create_cmd_snapshots_path()
        self._create_cmd_unmount()

        self._create_cmd_aliase_switches()


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
        logger.warning(f"Run command '{args.alias}' instead of argument "
                       f"'{args.replace}' due to backwards compatibility.")

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
