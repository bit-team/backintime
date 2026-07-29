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
import password
import cli
import config
import bitbase
from mount import MountManager
from applicationinstance import ApplicationInstance
from shutdownagent import ShutdownAgent
import diskusage
from storagesize import StorageSize


def _deprecation_msg(cmd_flag: str, replacement: str) -> str:
    if not replacement:
        replacement = 'A replacement is not planned.'

    kind = 'flag' if cmd_flag[0] == '-' else 'command'

    return (
        f'The {kind} "{cmd_flag}" is deprecated and will be removed from Back '
        f'In Time in the foreseeable future. {replacement} Feel free to '
        'contact the project team if you have any questions or suggestions.')


def show_deprecation_message(cmd_flag: str):
    """Centralize management of deprecation message regarding CLI commands and
    flags.

    As an exception the deprecation messages for flag-aliases (e.g. '--backup'
    for 'backup') are managed in `cliargument.alias_parser()`.
    """

    # 'None' means no replacement planned.
    replacement = {
        'snapshots-path': None,
        'snapshots-list': 'Use "show" instead.',
        'snapshots-list-path': 'Use "show --path" instead.',
        'last-snapshot': 'Use "show --last" instead.',
        'last-snapshot-path': 'Use "show --last --path" instead.',
        'backup-job': 'Use "backup --background" instead.',
        'smart-remove': 'Use "prune" instead.',
        'remove-and-do-not-ask-again':
            'Use "remove --skip-confirmation" instead.',
        '--profile-id': 'Use "--profile" instead.',
    }[cmd_flag]

    msg = _deprecation_msg(cmd_flag, replacement)

    # ToDo: Switch this later to ERROR
    logger.warning(msg)


def _get_config(args: argparse.Namespace) -> config.Config:
    """A dirty little helper. Feel free to refactor."""

    # Crreate a Konfig instance
    cli.get_config_and_select_profile(
        config_path=bitbase.context['--config'],  # args.config,
        pid_or_name=args.profile
        # checksum=getattr(args, 'checksum', None)
    )

    # A surrogate using Konfig() in the back
    return config.Config()


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

    # Run backup in background?
    if args.background:
        # "Force" will be False
        cli.BackupJobDaemon(_do_backup, args).start()
    else:
        _do_backup(args, force)


def _do_backup(args: argparse.Namespace, force: bool):
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
    print(bitbase.APP_HEADER)
    cfg = _get_config(args)

    tools.envLoad(bitbase.CRON_ENV_PATH)
    ret = snapshots.Snapshots(cfg).backup(
        force=force,
        force_checksum_use = getattr(args, 'checksum', False)
    )

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
    show_deprecation_message('backup-job')
    args.background = True
    backup(args)


def check_config(args: argparse.Namespace):
    """Check the config file.

    In case of no errors application exists with 0, otherwise 1.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0 if config is okay, 1 if not.

    """
    force_stdout = cli.set_quiet(args)
    print(bitbase.APP_HEADER, file=force_stdout)
    cfg = _get_config(args)

    msg = f'Config {bitbase.context["--config"]} profile ' \
          f"'{cfg.profileName()}'"

    if cli.checkConfig(cfg, crontab=not args.no_crontab):
        print(f'{msg} is fine.', file=force_stdout)
        sys.exit(bitbase.RETURN_OK)

    # else
    print(f'{msg} has errors.', file=force_stdout)
    sys.exit(bitbase.RETURN_ERR)


def _last_snapshot_base(args: argparse.Namespace, path_info: bool):
    """Print info about the very last (youngest) snapshot in current profile.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0
    """
    force_stdout = cli.set_quiet(args)
    cfg = _get_config(args)

    mount_manager = MountManager.create(cfg)
    with mount_manager.mounted():
        sid = snapshots.lastSnapshot(cfg, mounted_path=mount_manager.path)

        if sid:
            # Path or ID
            label = 'SnapshotPath' if path_info else 'SnapshotID'
            data = sid.path() if path_info else sid

            msg = f'{data}' if args.quiet else f'{label}: {data}'
            print(msg, file=force_stdout)

        else:
            logger.error(f"There are no snapshots in '{cfg.profileName()}'")

    sys.exit(bitbase.RETURN_OK)


def last_snapshot(args: argparse.Namespace):
    """Print the very last (youngest) snapshot in current profile.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0
    """
    show_deprecation_message('last-snapshot')
    _last_snapshot_base(args=args, path_info=False)


def last_snapshot_path(args: argparse.Namespace):
    """Print the path of the very last (youngest) snapshot in
    current profile.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    show_deprecation_message('last-snapshot-path')
    _last_snapshot_base(args=args, path_info=True)


def pw_cache(args: argparse.Namespace):
    """Startpassword cache daemon.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0 if daemon is running, 1 if not.
    """
    force_stdout = cli.set_quiet(args)
    print(bitbase.APP_HEADER)

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


def remove(args: argparse.Namespace):
    """Remove snapshots.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    cli.set_quiet(args)
    print(bitbase.APP_HEADER)

    cfg = _get_config(args)

    mount_manager = MountManager.create(cfg)
    with mount_manager.mounted():
        cli.remove(
            cfg=cfg,
            snapshot_ids=args.BACKUP_ID,
            force=args.skip_confirmation,
            mount_manager=mount_manager
        )

    sys.exit(bitbase.RETURN_OK)


def remove_and_donot_ask_again(args):
    """Removing snapshots without asking (BE CAREFUL!).

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    show_deprecation_message('remove-and-do-not-ask-again')
    args.skip_confirmation = True
    remove(args=args)


def restore(args: argparse.Namespace):
    """Restore files from snapshots.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    cli.set_quiet(args)
    print(bitbase.APP_HEADER)
    cfg = _get_config(args)

    if cfg.backupOnRestore() and not args.no_local_backup:
        isbackup = True
    else:
        isbackup = args.local_backup

    mount_manager = MountManager.create(cfg)
    with mount_manager.mounted():
        cli.restore(
            cfg=cfg,
            snapshot_id=args.BACKUP_ID,
            what=args.WHAT,
            where=args.WHERE,
            mount_manager=mount_manager,
            force_checksum_use=args.checksum,
            delete=args.delete,
            backup=isbackup,
            only_new=args.only_new
        )

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
    print(bitbase.APP_HEADER)
    cfg = _get_config(args)

    sd = ShutdownAgent()

    if not sd.can_shutdown():
        logger.warning('Shutdown is not supported.')
        sys.exit(bitbase.RETURN_ERR)

    instance = ApplicationInstance(cfg.takeSnapshotInstanceFile(), False)
    profile = '='.join((cfg.currentProfile(), cfg.profileName()))

    if not instance.busy():
        logger.info('Skip shutdown because there is no active bacukp '
                    f'for profile {profile}.')
        sys.exit(bitbase.RETURN_ERR)

    print(f'Shutdown is waiting for the running backup in profile {profile} '
          'to end.\nPress CTRL+C to interrupt shutdown.\n')
    sd.activate_shutdown = True

    try:
        while instance.busy():
            logger.debug('Backup is still active. Wait for shutdown.')
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
    show_deprecation_message('snapshots-path')

    force_stdout = cli.set_quiet(args)
    cfg = _get_config(args)

    # if args.keep_mount:
    #     _mount(cfg)

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

    mount_manager = MountManager.create(cfg)
    with mount_manager.mounted():

        if path_info:
            msg = '{}' if args.quiet else 'SnapshotPath: {}'
        else:
            msg = '{}' if args.quiet else 'SnapshotID: {}'

        if path_info:
            data = [
                sid.path() for sid
                in snapshots.listSnapshots(
                    cfg=cfg,
                    includeNewSnapshot=False,
                    reverse=False,
                    mounted_path=mount_manager.path
                )
            ]
        else:
            data = list(snapshots.listSnapshots(
                cfg=cfg,
                includeNewSnapshot=False,
                reverse=False,
                mounted_path=mount_manager.path
            ))

    for sid_info in data:
        print(msg.format(sid_info), file=force_stdout)

    if not data:
        logger.error(f"There are no snapshots in '{cfg.profileName()}'")

    sys.exit(bitbase.RETURN_OK)


def snapshots_list(args: argparse.Namespace):
    """Print a list of all snapshots in current profile.

    Args:
        args: Ppreviously parsed arguments

    Raises:
        SystemExit: 0
    """
    show_deprecation_message('snapshots-list')
    _snapshots_list_base(args=args, path_info=False)


def snapshots_list_path(args: argparse.Namespace):
    """Print a list of all snapshots paths in current profile.

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0
    """
    show_deprecation_message('snapshots-list-path')
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
    mount_manager = MountManager.create(cfg)

    with mount_manager.mounted():
        # raw data
        backups = snapshots.get_backup_ids_and_paths(
            cfg=cfg,
            descending=True,
            include_new=False,
            mounted_path=mount_manager.path
        )

        if args.last:
            backups = backups[-1:]

        if args.usage:
            size_bytes = diskusage.compute_total_usage(
                cfg, backups, mount_manager.path)

            if size_bytes < 0:
                print('Total disk usage: ERROR '
                      '(could not determine size)')
            else:
                print(f'Total disk usage: '
                      f'{StorageSize(size_bytes).as_human_readable()}')

            # Append space savings from hard-link deduplication
            logical, physical, saved, percent = \
                diskusage.compute_space_savings(
                    cfg, backups, mount_manager.path)
            if logical >= 0 and physical >= 0:
                saved_fmt = StorageSize(saved).as_human_readable()
                print(f'Space saved by hard links: {percent:.1f} %'
                      f' ({saved_fmt})')

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

    if not backups:
        logger.info(f'No backups in profile "{cfg.profileName()}"')
        sys.exit(bitbase.RETURN_ERR)

    sys.exit(bitbase.RETURN_OK)


def smart_remove(args: argparse.Namespace):
    show_deprecation_message('smart-remove')
    prune(args)


def prune(args: argparse.Namespace):
    """Run Remove & Retention (aka Smart-Removal).

    Args:
        args: Previously parsed arguments.

    Raises:
        SystemExit: 0 if okay. 2 if Remove & Retention is not configured.
    """
    cli.set_quiet(args)
    print(bitbase.APP_HEADER)
    cfg = _get_config(args)

    sn = snapshots.Snapshots(cfg)

    enabled, \
        keep_all, \
        keep_one_per_day, \
        keep_one_per_week, \
        keep_one_per_month = cfg.smartRemove()

    if not enabled:
        logger.error('Remove & Retention is not configured.')
        sys.exit(bitbase.RETURN_NO_CFG)

    mount_manager = MountManager.create(cfg)
    with mount_manager.mounted():
        del_snapshots = sn.smartRemoveList(datetime.today(),
                                            keep_all,
                                            keep_one_per_day,
                                            keep_one_per_week,
                                            keep_one_per_month)
        logger.info(f'{len(del_snapshots)} backups are marked for removal.')
        sn.smartRemove(del_snapshots, log=logger.info)
        sys.exit(bitbase.RETURN_OK)


def unmount(args):
    """Unmount all filesystems.

    Args:
        args: Previously parsed arguments

    Raises:
        SystemExit: 0
    """
    cli.set_quiet(args)

    cfg = _get_config(args)

    mount_manager = MountManager.create(cfg)
    with mount_manager.mounted():
        sys.exit(bitbase.RETURN_OK)
