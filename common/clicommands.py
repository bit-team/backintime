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
from bitbase import URL_ENCRYPT_TRANSITION
from diagnostics import collect_diagnostics, collect_minimal_diagnostics
from exceptions import MountException
from applicationinstance import ApplicationInstance
from version import __version__
from shutdownagent import ShutdownAgent

RETURN_OK = 0
RETURN_ERR = 1
RETURN_NO_CFG = 2


def backup(args, force=True):
    """
    Command for force taking a new snapshot.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments
        force (bool):   take the snapshot even if it wouldn't need to or would
                        be prevented (e.g. running on battery)

    Raises:
        SystemExit:     0 if successful, 1 if not
    """
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    ret = takeSnapshot(cfg, force)
    sys.exit(int(ret))


def backup_job(args):
    """
    Command for taking a new snapshot in background. Mainly used for cronjobs.
    This will run the snapshot inside a daemon and detach from it. It will
    return immediately back to commandline.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    cli.BackupJobDaemon(backup, args).start()


def benchmark_cipher(args):
    """
    Command for transferring a file with scp to remote host with all
    available ciphers and print its speed and time.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    setQuiet(args)
    printHeader()

    cfg = getConfig(args)

    if cfg.snapshotsMode() in ('ssh', 'ssh_encfs'):
        ssh = sshtools.SSH(cfg)
        ssh.benchmarkCipher(args.FILE_SIZE)
        sys.exit(RETURN_OK)

    else:
        logger.error("SSH is not configured for profile '%s'!" % cfg.profileName())
        sys.exit(RETURN_ERR)


def check_config(args):
    """
    Command for checking the config file.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0 if config is okay, 1 if not
    """
    force_stdout = setQuiet(args)
    printHeader()
    cfg = getConfig(args)

    if cli.checkConfig(cfg, crontab=not args.no_crontab):
        print("\nConfig %(cfg)s profile '%(profile)s' is fine."
              % {'cfg': cfg._LOCAL_CONFIG_PATH,
                 'profile': cfg.profileName()},
              file=force_stdout)
        sys.exit(RETURN_OK)

    else:
        print("\nConfig %(cfg)s profile '%(profile)s' has errors."
              % {'cfg': cfg._LOCAL_CONFIG_PATH,
                 'profile': cfg.profileName()},
              file=force_stdout)
        sys.exit(RETURN_ERR)


def decode(args):
    """
    Command for decoding paths given paths with 'encfsctl'.
    Will listen on stdin if no path was given.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    force_stdout = setQuiet(args)
    cfg = getConfig(args)

    if cfg.snapshotsMode() not in ('local_encfs', 'ssh_encfs'):
        logger.error("Profile '%s' is not encrypted." % cfg.profileName())
        sys.exit(RETURN_ERR)

    _mount(cfg)
    d = encfstools.Decode(cfg)

    if not args.PATH:

        while True:

            try:
                path = input()
            except EOFError:
                break

            if not path:
                break

            print(d.path(path), file=force_stdout)

    else:
        print('\n'.join(d.list(args.PATH)), file=force_stdout)

    d.close()
    _umount(cfg)

    sys.exit(RETURN_OK)


def last_snapshot(args):
    """
    Command for printing the very last snapshot in current profile.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    sid = snapshots.lastSnapshot(cfg)
    if sid:
        if args.quiet:
            msg = '{}'
        else:
            msg = 'SnapshotID: {}'
        print(msg.format(sid), file=force_stdout)
    else:
        logger.error("There are no snapshots in '%s'" % cfg.profileName())
    _umount(cfg)
    sys.exit(RETURN_OK)


def last_snapshot_path(args):
    """
    Command for printing the path of the very last snapshot in
    current profile.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    sid = snapshots.lastSnapshot(cfg)
    if sid:
        if args.quiet:
            msg = '{}'
        else:
            msg = 'SnapshotPath: {}'
        print(msg.format(sid.path()), file=force_stdout)
    else:
        logger.error("There are no snapshots in '%s'" % cfg.profileName())
    if not args.keep_mount:
        _umount(cfg)
    sys.exit(RETURN_OK)


def pw_cache(args):
    """
    Command for starting password cache daemon.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0 if daemon is running, 1 if not
    """
    force_stdout = setQuiet(args)
    printHeader()

    cfg = getConfig(args)
    ret = RETURN_OK
    daemon = password.Password_Cache(cfg)

    if args.ACTION and args.ACTION != 'status':
        getattr(daemon, args.ACTION)()

    elif args.ACTION == 'status':

        print('%(app)s Password Cache: ' % {'app': cfg.APP_NAME},
              end=' ',
              file=force_stdout)

        if daemon.status():
            print(cli.bcolors.OKGREEN + 'running' + cli.bcolors.ENDC,
                  file=force_stdout)
            ret = RETURN_OK

        else:
            print(cli.bcolors.FAIL + 'not running' + cli.bcolors.ENDC,
                  file=force_stdout)
            ret = RETURN_ERR

    else:
        daemon.run()

    sys.exit(ret)


def remove(args, force=False):
    """
    Command for removing snapshots.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments
        force (bool):   don't ask before removing (BE CAREFUL!)

    Raises:
        SystemExit:     0
    """
    setQuiet(args)
    printHeader()

    cfg = getConfig(args)
    _mount(cfg)

    cli.remove(cfg, args.SNAPSHOT_ID, force)
    _umount(cfg)

    sys.exit(RETURN_OK)


def remove_and_donot_ask_again(args):
    """
    Command for removing snapshots without asking before remove
    (BE CAREFUL!)

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    remove(args, True)
