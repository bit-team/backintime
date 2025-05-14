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
"""Module about CLI commands"""
import sys
import argparse
from datetime import datetime
from time import sleep
import tools
# Workaround for situations where startApp() is not invoked.
# E.g. when using --diagnostics and other argparse.Action
tools.initiate_translation(None)
import logger
import snapshots
import sshtools
import password
import encfstools
import cli
import config
import bitbase
import mount
from exceptions import MountException
from applicationinstance import ApplicationInstance
from shutdownagent import ShutdownAgent


def _deprecation_msg(command: str, replacement: str) -> str:
    if not replacement:
        replacement = 'A replacement is not planned.'

    msg = (
        'The command "{command}" is deprecated and will be removed from Back '
        'In Time in the foreseeable future. {replacement} Feel free to '
        'contact the project team if you have any questions or suggestions.')

    return msg.format(
        command=command,
        replacement=replacement)

def _show_deprecation_message(cmd: str):
    """Centralize management of deprecation message regarding CLI commands and
    flags.

    As an exception the deprecation messages for flag-aliases (e.g. '--backup'
    for 'backup') are managed in `cliargument.alias_parser()`.
    """
    replacement = {
        'benchmark-cipher': None,
        'snapshots-path': None,
        'snapshots-list': 'Use "show" instead.',
        'snapshots-list-path': 'Use "show --path" instead.',
        'last-snapshot': 'Use "show --last" instead.',
        'last-snapshot-path': 'Use "show --last --path" instead.',
    }[cmd]

    msg = _deprecation_msg(cmd, replacement)

    # ToDo: Switch this later to ERROR
    logger.warning(msg)


def _get_config(args: argparse.Namespace) -> config.Config:
    """A dirty little helper. Feel free to refactor."""
    return cli.get_config_and_select_profile(
        config_path=args.config,
        data_path=args.share_path,
        profile_id=args.profile_id,
        profile_name=args.profile,
        checksum=getattr(args, 'checksum', None)
    )


def backup(args: argparse.Namespace, force: bool = True):
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
    cli.set_quiet(args)
    cli.print_header()
    cfg = _get_config(args)

    tools.envLoad(cfg.cronEnvFile())
    ret = snapshots.Snapshots(cfg).backup(force)

    sys.exit(int(ret))


def backup_job(args: argparse.Namespace):
    """
    Command for taking a new snapshot in background. Mainly used for cronjobs.
    This will run the snapshot inside a daemon and detach from it. It will
    return immediately back to commandline.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0
    """
    cli.BackupJobDaemon(backup, args).start()


def benchmark_cipher(args: argparse.Namespace):
    """
    Command for transferring a file with scp to remote host with all
    available ciphers and print its speed and time.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    _show_deprecation_message('benchmark-cipher')

    cli.set_quiet(args)
    cli.print_header()

    cfg = _get_config(args)

    if cfg.snapshotsMode() in ('ssh', 'ssh_encfs'):
        ssh = sshtools.SSH(cfg)
        ssh.benchmarkCipher(args.FILE_SIZE)
        sys.exit(bitbase.RETURN_OK)

    # else
    logger.error(
        f"SSH is not configured for profile '{cfg.profileName()}'!")
    sys.exit(bitbase.RETURN_ERR)


def check_config(args: argparse.Namespace):
    """Check the config file.

    In case of no errors application exists with 0, otherwise 1.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0 if config is okay, 1 if not.

    """
    force_stdout = cli.set_quiet(args)
    cli.print_header()
    cfg = _get_config(args)

    msg = f'\nConfig {cfg._LOCAL_CONFIG_PATH} profile ' \
          f"'{cfg.profileName()}'"

    if cli.checkConfig(cfg, crontab=not args.no_crontab):
        print(f'{msg} is fine.', file=force_stdout)
        sys.exit(bitbase.RETURN_OK)

    # else
    print(f'{msg} has errors.', file=force_stdout)
    sys.exit(bitbase.RETURN_ERR)


def decode(args: argparse.Namespace):
    """Decoding paths given paths with 'encfsctl'.

    Will listen on stdin if no path was given.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0
    """
    force_stdout = cli.set_quiet(args)
    cfg = _get_config(args)

    if cfg.snapshotsMode() not in ('local_encfs', 'ssh_encfs'):
        logger.error(f"Profile '{cfg.profileName()}' is not encrypted.")
        sys.exit(bitbase.RETURN_ERR)

    _mount(cfg)
    decoder = encfstools.Decode(cfg)

    if not args.PATH:

        while True:

            try:
                path = input()
            except EOFError:
                break

            if not path:
                break

            print(decoder.path(path), file=force_stdout)

    else:
        print('\n'.join(decoder.list(args.PATH)), file=force_stdout)

    decoder.close()
    _umount(cfg)

    sys.exit(bitbase.RETURN_OK)


def _last_snapshot_base(args: argparse.Namespace, path_info: bool):
    """Print info about the very last (youngest) snapshot in current profile.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0
    """
    force_stdout = cli.set_quiet(args)
    cfg = _get_config(args)
    _mount(cfg)
    sid = snapshots.lastSnapshot(cfg)

    if sid:
        # Path or ID
        label = 'SnapshotPath' if path_info else 'SnapshotID'
        data = sid.path() if path_info else sid

        msg = f'{data}' if args.quiet else f'{label}: {data}'
        print(msg, file=force_stdout)

    else:
        logger.error(f"There are no snapshots in '{cfg.profileName()}'")

    if not getattr(args, 'keep_mount', None):
        _umount(cfg)

    sys.exit(bitbase.RETURN_OK)


def last_snapshot(args: argparse.Namespace):
    """Print the very last (youngest) snapshot in current profile.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0
    """
    _show_deprecation_message('last-snapshot')
    _last_snapshot_base(args=args, path_info=False)


def last_snapshot_path(args: argparse.Namespace):
    """Print the path of the very last (youngest) snapshot in
    current profile.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    _show_deprecation_message('last-snapshot-path')
    _last_snapshot_base(args=args, path_info=True)


def pw_cache(args: argparse.Namespace):
    """Startpassword cache daemon.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0 if daemon is running, 1 if not.
    """
    force_stdout = cli.set_quiet(args)
    cli.print_header()

    cfg = _get_config(args)
    ret = bitbase.RETURN_OK

    daemon = password.Password_Cache(cfg)

    if args.ACTION and args.ACTION != 'status':
        # call action method
        getattr(daemon, args.ACTION)()

    elif args.ACTION == 'status':

        print(f'{cfg.APP_NAME} Password Cache: ', end=' ', file=force_stdout)

        if daemon.status():
            print(f'{cli.bcolors.OKGREEN}running{cli.bcolors.ENDC}',
                  file=force_stdout)
            ret = bitbase.RETURN_OK

        else:
            print(f'{cli.bcolors.FAIL}not running{cli.bcolors.ENDC}',
                  file=force_stdout)
            ret = bitbase.RETURN_ERR

    else:
        daemon.run()

    sys.exit(ret)


def remove(args: argparse.Namespace, force: bool = False):
    """Remove snapshots.

    Args:
        args: Previously parsed arguments.
        force: Don't ask before removing (BE CAREFUL!).

    Raises:
        SystemExit: 0
    """
    cli.set_quiet(args)
    cli.print_header()

    cfg = _get_config(args)
    _mount(cfg)

    cli.remove(cfg, args.SNAPSHOT_ID, force)
    _umount(cfg)

    sys.exit(bitbase.RETURN_OK)


def remove_and_donot_ask_again(args):
    """Removing snapshots without asking (BE CAREFUL!).

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    remove(args=args, force=True)


def restore(args: argparse.Namespace):
    """Restore files from snapshots.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    cli.set_quiet(args)
    cli.print_header()
    cfg = _get_config(args)
    _mount(cfg)

    if cfg.backupOnRestore() and not args.no_local_backup:
        isbackup = True
    else:
        isbackup = args.local_backup

    cli.restore(cfg,
                args.SNAPSHOT_ID,
                args.WHAT,
                args.WHERE,
                delete=args.delete,
                backup=isbackup,
                only_new=args.only_new)

    _umount(cfg)

    sys.exit(bitbase.RETURN_OK)


def shutdown(args: argparse.Namespace):
    """Shut down the computer after the current snapshot has
    finished.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0 if successful; 1 if it failed either because there is no
            active snapshot for this profile or shutdown is not supported.

    """
    cli.set_quiet(args)
    cli.print_header()
    cfg = _get_config(args)

    sd = ShutdownAgent()

    if not sd.can_shutdown():
        logger.warning('Shutdown is not supported.')
        sys.exit(bitbase.RETURN_ERR)

    instance = ApplicationInstance(cfg.takeSnapshotInstanceFile(), False)
    profile = '='.join((cfg.currentProfile(), cfg.profileName()))

    if not instance.busy():
        logger.info('Skip shutdown because there is no active snapshot '
                    f'for profile {profile}.')
        sys.exit(bitbase.RETURN_ERR)

    print(f'Shutdown is waiting for the snapshot in profile {profile} to end.'
          '\nPress CTRL+C to interrupt shutdown.\n')
    sd.activate_shutdown = True

    try:
        while instance.busy():
            logger.debug('Snapshot is still active. Wait for shutdown.')
            sleep(5)

    except KeyboardInterrupt:
        print('Shutdown interrupted.')

    else:
        logger.info('Shuting down now.')
        sd.shutdown()

    sys.exit(bitbase.RETURN_OK)


def snapshots_path(args: argparse.Namespace):
    """Print the full snapshot path of current profile.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    _show_deprecation_message('snapshots-path')

    force_stdout = cli.set_quiet(args)
    cfg = _get_config(args)

    if args.keep_mount:
        _mount(cfg)

    msg = '{}' if args.quiet else 'SnapshotsPath: {}'
    print(msg.format(cfg.snapshotsFullPath()), file=force_stdout)

    sys.exit(bitbase.RETURN_OK)


def _snapshots_list_base(args: argparse.Namespace, path_info: bool):
    """Print infos about a list of all snapshots in current profile.

    Args:
        args: Ppreviously parsed arguments

    Raises:
        SystemExit: 0
    """
    force_stdout = cli.set_quiet(args)
    cfg = _get_config(args)
    _mount(cfg)

    if path_info:
        msg = '{}' if args.quiet else 'SnapshotPath: {}'
    else:
        msg = '{}' if args.quiet else 'SnapshotID: {}'

    # Use snapshots.listSnapshots instead of iterSnapshots because of sorting
    if path_info:
        data = [
            sid.path() for sid in snapshots.listSnapshots(cfg, reverse=False)]
    else:
        data = list(snapshots.listSnapshots(cfg, reverse=False))

    for sid_info in data:
        print(msg.format(sid_info), file=force_stdout)

    if not data:
        logger.error(f"There are no snapshots in '{cfg.profileName()}'")

    if not args.keep_mount:
        _umount(cfg)

    sys.exit(bitbase.RETURN_OK)


def snapshots_list(args: argparse.Namespace):
    """Print a list of all snapshots in current profile.

    Args:
        args: Ppreviously parsed arguments

    Raises:
        SystemExit: 0
    """
    _show_deprecation_message('snapshots-list')
    _snapshots_list_base(args=args, path_info=False)


def snapshots_list_path(args: argparse.Namespace):
    """Print a list of all snapshots paths in current profile.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    _show_deprecation_message('snapshots-list-path')
    _snapshots_list_base(args=args, path_info=True)


def show_backups(args: argparse.Namespace):
    """Command 'show'.

    Args:
        args: Parsed command-line arguments.

    Raises:
        SystemExit: With errors or no backups available
            `bitbase.RETURN_ERR` (1),  otherwise `bitbase.RETURN_OK' (0).
    """

    cfg = _get_config(args)
    _mount(cfg)

    # raw data
    backups = snapshots.get_backup_ids_and_paths(
        cfg=cfg, descending=True, include_new=False)

    if args.last:
        backups = backups[-1:]

    if args.path:
        # Path
        def _element(e):
            return str(e[1])
    else:
        # ID
        def _element(e):
            return e[0]

    # one line for each ID/Path
    result = '\n'.join(
        map(_element, backups)
    )

    print(result)
    _umount(cfg)

    if not backups:
        logger.error(f'No backups in profile "{cfg.profileName()}"')
        sys.exit(bitbase.RETURN_ERR)

    sys.exit(bitbase.RETURN_OK)


def smart_remove(args: argparse.Namespace):
    """Run Remove & Retention (aka Smart-Removal) from Terminal.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0 if okay. 2 if Smart-Removal is not configured.
    """
    cli.set_quiet(args)
    cli.print_header()
    cfg = _get_config(args)
    sn = snapshots.Snapshots(cfg)

    enabled, \
        keep_all, \
        keep_one_per_day, \
        keep_one_per_week, \
        keep_one_per_month = cfg.smartRemove()

    if enabled:
        _mount(cfg)
        del_snapshots = sn.smartRemoveList(datetime.today(),
                                           keep_all,
                                           keep_one_per_day,
                                           keep_one_per_week,
                                           keep_one_per_month)
        logger.info(f'{len(del_snapshots)} snapshots are marked for removal.')
        sn.smartRemove(del_snapshots, log=logger.info)
        _umount(cfg)
        sys.exit(bitbase.RETURN_OK)

    # else
    logger.error('Remove & Retention is not configured.')
    sys.exit(bitbase.RETURN_NO_CFG)


def unmount(args):
    """Unmount all filesystems.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0
    """
    cli.set_quiet(args)

    cfg = _get_config(args)

    _mount(cfg)
    _umount(cfg)

    sys.exit(bitbase.RETURN_OK)


def _mount(cfg: config.Config):
    """Mount external filesystems of current selected profile.

    Args:
        cfg: Config to identify the current profile.
    """
    try:
        hash_id = mount.Mount(cfg=cfg).mount()

    except MountException as ex:
        logger.error(str(ex))
        sys.exit(bitbase.RETURN_ERR)

    else:
        cfg.setCurrentHashId(hash_id)


def _umount(cfg: config.Config):
    """Unmount external filesystems of current selected profile.

    Args:
        cfg: Config to identify the current profile.
    """
    try:
        mount.Mount(cfg=cfg).umount(cfg.current_hash_id)

    except MountException as ex:
        logger.error(str(ex))
