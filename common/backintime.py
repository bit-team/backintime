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
import argparse
import atexit
import subprocess
from datetime import datetime
from time import sleep
import json
import pathlib
import tools
# Workaround for situations where startApp() is not invoked.
# E.g. when using --diagnostics and other argparse.Action
tools.initiate_translation(None)
import config
import logger
import snapshots
import sshtools
import mount
import password
import encfstools
import cli
import cliarguments
import clicommands
from bitbase import URL_ENCRYPT_TRANSITION
from diagnostics import collect_diagnostics, collect_minimal_diagnostics
from applicationinstance import ApplicationInstance
from version import __version__
from shutdownagent import ShutdownAgent

RETURN_OK = 0
RETURN_ERR = 1
RETURN_NO_CFG = 2

# parsers = {}


def takeSnapshotAsync(cfg, checksum=False):
    """
    Fork a new backintime process with 'backup' command which will
    take a new snapshot in background.

    Args:
        cfg (config.Config): config that should be used
    """
    cmd = []

    if cfg.ioniceOnUser():
        cmd.extend(('ionice', '-c2', '-n7'))

    cmd.append('backintime')

    if '1' != cfg.currentProfile():
        cmd.extend(('--profile-id', str(cfg.currentProfile())))
    if cfg._LOCAL_CONFIG_PATH is not cfg._DEFAULT_CONFIG_PATH:
        cmd.extend(('--config', cfg._LOCAL_CONFIG_PATH))
    if cfg._LOCAL_DATA_FOLDER is not cfg._DEFAULT_LOCAL_DATA_FOLDER:
        cmd.extend(('--share-path', cfg.DATA_FOLDER_ROOT))
    if logger.DEBUG:
        cmd.append('--debug')
    if checksum:
        cmd.append('--checksum')

    cmd.append('backup')

    # child process need to start its own ssh-agent because otherwise
    # it would be lost without ssh-agent if parent will close
    env = os.environ.copy()

    for i in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID'):
        try:
            del env[i]

        except:
            pass

    subprocess.Popen(cmd, env=env)


def encfs_deprecation_warning():
    """Warn about encfs deprecation in syslog.

    See Issue #1734 for details. This function is a workraound and will be
    removed if #1734 is closed.
    """

    # Don't warn if EncFS isn't installed
    if not tools.checkCommand('encfs'):
        return

    # Timestamp file
    xdg_state = os.environ.get('XDG_STATE_HOME', None)
    if xdg_state:
        xdg_state = pathlib.Path(xdg_state)
    else:
        xdg_state = pathlib.Path.home() / '.local' / 'state'
    fp = xdg_state / 'backintime.encfs-warning.timestamp'

    # ensure existence
    if not fp.exists():
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.touch()

    # Calculate age of that file
    delta = datetime.now() - datetime.fromtimestamp(fp.stat().st_mtime)

    # Don't warn if to young
    if delta.days < 30:
        return

    logger.warning('EncFS encrypted profiles are deprecated in Back In Time. '
                   'Removal is schedule for minor release 1.7 in year 2026. '
                   'For details and alternatives '
                   f'read: {URL_ENCRYPT_TRANSITION}')


    # refresh timestamp
    fp.touch()


def startApp(app_name='backintime'):
    """
    Start the requested command or return config if there was no command
    in arguments.

    Args:
        app_name (str): string representing the current application

    Returns:
        config.Config:  current config if no command was given in arguments
    """
    # Workaround (maybe)
    # Mapping the command names to their handler functions
    cmd_func = {
        'backup': clicommands.backup,
        'backup-job': clicommands.backup_job,
        'benchmark-cipher': clicommands.benchmark_cipher,
        'check-config': clicommands.check_config,
        'decode': clicommands.decode,
        'last-snapshot': clicommands.last_snapshot,
        'last-snapshot-path': clicommands.last_snapshot_path,
        'pw-cache': clicommands.pw_cache,
        'remove': clicommands.remove,
        'remove-and-do-not-ask-again': clicommands.remove_and_donot_ask_again,
        'restore': clicommands.restore,
        'shutdown': clicommands.shutdown,
        'snapshots-path': clicommands.snapshots_path,
        'snapshots-list': clicommands.snapshots_list,
        'snapshots-list-path': clicommands.snapshots_list_path,
        'smart-remove': clicommands.smart_remove,
        'unmount': clicommands.unmount,
    }
    # global parsers  # REFACTOR!
    parsers = cliarguments.create_parsers(
        app_name='backintime', cmd_func_dict=cmd_func)

    logger.openlog()

    args = cliarguments.parse_arguments(args=None, parsers=parsers)

    # Name, Version, As Root, OS
    msg = ''
    for key, val in collect_minimal_diagnostics().items():
        msg = f'{msg}; {key}: {val}'
    logger.debug(msg[2:])

    # Add source path to $PATH environ if running from source
    if tools.runningFromSource():
        tools.addSourceToPathEnviron()

    # Warn about sudo
    if (tools.usingSudo()
            and os.getenv('BIT_SUDO_WARNING_PRINTED', 'false') == 'false'):

        os.putenv('BIT_SUDO_WARNING_PRINTED', 'true')
        logger.warning(
            "It looks like you're using 'sudo' to start "
            f"{config.Config.APP_NAME}. This will cause some trouble. "
            f"Please use either 'sudo -i {app_name}' or 'pkexec {app_name}'.")

    encfs_deprecation_warning()

    # Call commands
    if 'func' in dir(args):
        args.func(args)
        return None

    # No arguments/commands
    cli.set_quiet(args)
    cli.print_header()

    return cli.get_config_and_select_profile(
        config_path=args.config_path,
        data_path=args.share_path,
        profile_id=args.profile_id,
        profile_name=args.profile,
        checksum=args.checksum,
        check=False)


if __name__ == '__main__':
    startApp()
