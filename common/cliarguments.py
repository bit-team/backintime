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
import sys
import argparse
import json
import tools
from argparse import ArgumentParser
from pathlib import Path
# Workaround for situations where startApp() is not invoked.
# E.g. when using --diagnostics and other argparse.Action
tools.initiate_translation(None)
import bitbase
import config
import diagnostics
from version import __version__

RETURN_OK = bitbase.RETURN_OK
RETURN_ERR = bitbase.RETURN_ERR
RETURN_NO_CFG = bitbase.RETURN_NO_CFG


def create_parsers(app_name: str,
                   cmd_func_dict: dict[str, callable]
                   ) -> dict[argparse.ArgumentParser]:
    """Define parsers for commandline arguments.

    Args:
        app_name: String representing the current application.

    Returns:
        Dictionary of argument parsers index by command names.
    """
    parsers = {}

    debugArgsParser = argparse.ArgumentParser(add_help = False)
    debugArgsParser.add_argument('--debug',
                                 action = 'store_true',
                                 help = 'Increase verbosity.')

    configArgsParser = argparse.ArgumentParser(add_help = False)
    configArgsParser.add_argument('--config',
                                 metavar = 'PATH',
                                 type = str,
                                 action = 'store',
                                 help = 'Read config from %(metavar)s. ' +
                                        'Default = ~/.config/backintime/config')

    configArgsParser.add_argument('--share-path',
                                 metavar = 'PATH',
                                 type = str,
                                 action = 'store',
                                 help = 'Write runtime data (locks, messages, log and mountpoints) to %(metavar)s.')

    # Common arguments used by all commands
    commonArgsParser = argparse.ArgumentParser(add_help = False, parents = [configArgsParser, debugArgsParser])
    profileGroup = commonArgsParser.add_mutually_exclusive_group()
    profileGroup.add_argument    ('--profile',
                                  metavar = 'NAME',
                                  type = str,
                                  action = 'store',
                                  help = 'Select profile by %(metavar)s.')
    profileGroup.add_argument    ('--profile-id',
                                  metavar = 'ID',
                                  type = int,
                                  action = 'store',
                                  help = 'Select profile by %(metavar)s.')
    commonArgsParser.add_argument('--quiet',
                                  action = 'store_true',
                                  help = 'Be quiet. Suppress messages on stdout.')

    # Aarguments used only by snapshots-path, snapshots-list-path and last-snapshot-path
    snapshotPathParser = argparse.ArgumentParser(add_help = False)
    snapshotPathParser.add_argument('--keep-mount',
                                    action = 'store_true',
                                    help = "Don't unmount on exit.")

    # Arguments used only by rsync commands (backup and restore)
    rsyncArgsParser = argparse.ArgumentParser(add_help = False)
    rsyncArgsParser.add_argument('--checksum',
                                 action = 'store_true',
                                 help = 'force to use checksum for checking if files have been changed.')

    # Arguments used only by snapshot remove
    removeArgsParser = argparse.ArgumentParser(add_help = False)
    removeArgsParser.add_argument('SNAPSHOT_ID',
                                  type = str,
                                  action = 'store',
                                  nargs = '*',
                                  help = 'ID of snapshots which should be removed.')

    parsers['main'] = _main_parser(
        parent_parser=commonArgsParser, bin_name=app_name)

    #######################
    ### define commands ###
    #######################
    epilog = "Run '%(app_name)s -h' to get help for additional arguments. " %{'app_name': app_name}
    epilogCommon = epilog + 'Additional arguments: --config, --debug, --profile, --profile-id, --quiet'
    epilogConfig = epilog + 'Additional arguments: --config, --debug'

    subparsers = parser.add_subparsers(title = 'Commands', dest = 'command')
    command = 'backup'
    nargs = 0
    aliases = [(command, nargs), ('b', nargs)]
    description = 'Take a new snapshot. Ignore if the profile ' +\
                  'is not scheduled or if the machine is running on battery.'
    backupCP =             subparsers.add_parser(command,
                                                 parents = [rsyncArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    backupCP.set_defaults(func = cmd_func_dict[command])
    parsers[command] = backupCP

    command = 'backup-job'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Take a new snapshot in background only '      +\
                  'if the profile is scheduled and the machine ' +\
                  'is not on battery. This is used by cron jobs.'
    backupJobCP =          subparsers.add_parser(command,
                                                 parents = [rsyncArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    backupJobCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = backupJobCP

    command = 'benchmark-cipher'
    nargs = '?'
    aliases.append((command, nargs))
    description = 'Show a benchmark of all ciphers for ssh transfer.'
    benchmarkCipherCP =    subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    benchmarkCipherCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = benchmarkCipherCP
    benchmarkCipherCP.add_argument              ('FILE_SIZE',
                                                 type = int,
                                                 action = 'store',
                                                 default = 40,
                                                 nargs = '?',
                                                 help = 'File size used for benchmark.')

    command = 'check-config'
    description = 'Check the profiles configuration and install crontab entries.'
    checkConfigCP =        subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    checkConfigCP.add_argument                  ('--no-crontab',
                                                 action = 'store_true',
                                                 help = 'Do not install crontab entries.')
    checkConfigCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = checkConfigCP

    command = 'decode'
    nargs = '*'
    aliases.append((command, nargs))
    description = "Decode paths with 'encfsctl decode'"
    decodeCP =             subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    decodeCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = decodeCP
    decodeCP.add_argument                       ('PATH',
                                                 type = str,
                                                 action = 'store',
                                                 nargs = '*',
                                                 help = 'Decode PATH. If no PATH is specified on command line ' +\
                                                 'a list of filenames will be read from stdin.')

    command = 'last-snapshot'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Show the ID of the last snapshot.'
    lastSnapshotCP =       subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    lastSnapshotCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = lastSnapshotCP

    command = 'last-snapshot-path'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Show the path of the last snapshot.'
    lastSnapshotsPathCP =  subparsers.add_parser(command,
                                                 parents = [snapshotPathParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    lastSnapshotsPathCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = lastSnapshotsPathCP

    command = 'pw-cache'
    nargs = '*'
    aliases.append((command, nargs))
    description = 'Control Password Cache for non-interactive cronjobs.'
    pwCacheCP =            subparsers.add_parser(command,
                                                 epilog = epilogConfig,
                                                 help = description,
                                                 description = description)
    pwCacheCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = pwCacheCP
    pwCacheCP.add_argument                      ('ACTION',
                                                 action = 'store',
                                                 choices = ['start', 'stop', 'restart', 'reload', 'status'],
                                                 nargs = '?',
                                                 help = 'Command to send to Password Cache daemon.')

    command = 'remove'
    nargs = '*'
    aliases.append((command, nargs))
    description = 'Remove a snapshot.'
    removeCP =             subparsers.add_parser(command,
                                                 parents = [removeArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    removeCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = removeCP

    command = 'remove-and-do-not-ask-again'
    nargs = '*'
    aliases.append((command, nargs))
    description = "Remove snapshots and don't ask for confirmation before. Be careful!"
    removeDoNotAskCP =     subparsers.add_parser(command,
                                                 parents = [removeArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    removeDoNotAskCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = removeDoNotAskCP

    command = 'restore'
    nargs = '*'
    aliases.append((command, nargs))
    description = 'Restore files.'
    restoreCP =            subparsers.add_parser(command,
                                                 parents = [rsyncArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    restoreCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = restoreCP
    backupGroup = restoreCP.add_mutually_exclusive_group()
    restoreCP.add_argument                      ('WHAT',
                                                 type = str,
                                                 action = 'store',
                                                 nargs = '?',
                                                 help = 'Restore file or directory WHAT.')

    restoreCP.add_argument                      ('WHERE',
                                                 type = str,
                                                 action = 'store',
                                                 nargs = '?',
                                                 help = "Restore to WHERE. An empty argument '' will restore to original destination.")

    restoreCP.add_argument                      ('SNAPSHOT_ID',
                                                 type = str,
                                                 action = 'store',
                                                 nargs = '?',
                                                 help = 'Which SNAPSHOT_ID should be used. This can be a snapshot ID or ' +\
                                                 'an integer starting with 0 for the last snapshot, 1 for the second to last, ... ' +\
                                                 'the very first snapshot is -1')

    restoreCP.add_argument                      ('--delete',
                                                 action = 'store_true',
                                                 help = 'Restore and delete newer files which are not in the snapshot. ' +\
                                                 'WARNING: deleting files in filesystem root could break your whole system!!!')

    backupGroup.add_argument                    ('--local-backup',
                                                 action = 'store_true',
                                                 help = 'Create backup files before changing local files.')

    backupGroup.add_argument                    ('--no-local-backup',
                                                 action = 'store_true',
                                                 help = 'Temporarily disable creation of backup files before changing local files. ' +\
                                                 'This can be switched off permanently in Settings, too.')

    restoreCP.add_argument                      ('--only-new',
                                                 action = 'store_true',
                                                 help = 'Only restore files which do not exist or are newer than ' +\
                                                        'those in destination. Using "rsync --update" option.')

    command = 'shutdown'
    nargs = 0
    description = 'Shut down the computer after the snapshot is done.'
    shutdownCP =           subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    shutdownCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = shutdownCP

    command = 'smart-remove'
    nargs = 0
    description = 'Remove snapshots based on "Smart Removal" pattern.'
    smartRemoveCP =        subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    smartRemoveCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = smartRemoveCP

    command = 'snapshots-list'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Show a list of snapshot IDs.'
    snapshotsListCP =      subparsers.add_parser(command,
                                                 parents = [snapshotPathParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    snapshotsListCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = snapshotsListCP

    command = 'snapshots-list-path'
    nargs = 0
    aliases.append((command, nargs))
    description = "Show the paths to snapshots."
    snapshotsListPathCP =  subparsers.add_parser(command,
                                                 parents = [snapshotPathParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    snapshotsListPathCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = snapshotsListPathCP

    command = 'snapshots-path'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Show the path where snapshots are stored.'
    snapshotsPathCP =      subparsers.add_parser(command,
                                                 parents = [snapshotPathParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    snapshotsPathCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = snapshotsPathCP

    command = 'unmount'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Unmount the profile.'
    unmountCP =            subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    unmountCP.set_defaults(func=cmd_func_dict[command])
    parsers[command] = unmountCP

    # define aliases for all commands with trailing --
    # DEPRECATED and REMOVE it
    group = parser.add_mutually_exclusive_group()
    for alias, nargs in aliases:
        if len(alias) == 1:
            arg = '-%s' % alias
        else:
            arg = '--%s' % alias

        group.add_argument(arg,
                           nargs=nargs,
                           action=PseudoAliasAction,
                           help=argparse.SUPPRESS)

    return parsers


def _main_parser(parent_parser: ArgumentParser, bin_name: str
                 ) -> ArgumentParser:
    """Main argument parser"""
    desc = f'{config.Config.APP_NAME} - a simple backup tool for GNU/Linux.',
    epi = (
        'For backwards compatibility commands can also be used with trailing '
        "'--'. All listed arguments will work with all commands. Some "
        "commands have extra arguments. Run '%(prog)s <COMMAND> -h' to "
        'see the extra arguments.'
    )

    parser = ArgumentParser(
        prog=bin_name, parents=[parent_parser], description=desc, epilog=epi)

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
        help='show helpful info (in JSON format) for better support in case '
             'of issues')

    return parser


class ActionPrintLicense(argparse.Action):
    """Print license text."""

    def __init__(self, *args, **kwargs):
        super(ActionPrintLicense, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        license_path = Path(tools.docPath()) / 'LICENSE'
        print(license_path.read_text('utf-8'))
        sys.exit(bitbase.RETURN_OK)


class ActionPrintDiagnostics(argparse.Action):
    """See `collect_diagnostics()` for details."""

    def __init__(self, *args, **kwargs):
        super(ActionPrintDiagnostics, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        data = diagnostics.collect_diagnostics()
        print(json.dumps(data, indent=4))
        sys.exit(RETURN_OK)


class PseudoAliasAction(argparse.Action):
    """
    Translate '--COMMAND' into 'COMMAND' for backwards compatibility.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        """
        Translate '--COMMAND' into 'COMMAND' for backwards compatibility.

        Args:
            parser (argparse.ArgumentParser): NotImplemented
            namespace (argparse.Namespace):   Namespace that should get modified
            values:                           NotImplemented
            option_string:                    NotImplemented
        """
        #TODO: find a more elegant way to solve this
        dest = self.dest.replace('_', '-')
        if self.dest == 'b':
            replace = '-b'
            alias = 'backup'
        else:
            replace = '--%s' % dest
            alias = dest
        setattr(namespace, 'func', aliasParser)
        setattr(namespace, 'replace', replace)
        setattr(namespace, 'alias', alias)
