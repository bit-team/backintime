# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
import atexit
import shutil
from pathlib import Path
import tools
import daemon
import snapshots
import bcolors
import logger
import bitbase
import core_events
from typing import Union
from konfig import Konfig
from check_config import CheckConfigAgent
from mount import MountManager, MountError
from version import __version__


def restore(cfg, snapshot_id, what, where, mount_manager, force_checksum_use, **kwargs):
    if what is None:
        what = input('File to restore: ')

    what = os.path.abspath(os.path.expanduser(what))

    if where is None:
        where = input('Restore to (empty for original path): ')

    if where:
        where = os.path.abspath(os.path.expanduser(where))

    snapshotsList = snapshots.listSnapshots(
        cfg=cfg,
        includeNewSnapshot=False,
        reverse=True,
        mounted_path=mount_manager.path
    )

    sid = selectSnapshot(
        snapshotsList,
        cfg,
        snapshot_id,
        'SnapshotID to restore',
        mount_manager.path
    )
    print('')

    RestoreDialog(cfg, sid, what, where, force_checksum_use, **kwargs).run()


def remove(cfg, snapshot_ids, force, mount_manager):
    snapshotsList = snapshots.listSnapshots(
        cfg=cfg,
        includeNewSnapshot=False,
        reverse=True,
        mounted_path=mount_manager.path
    )

    if not snapshot_ids:
        snapshot_ids = (None,)

    sids = [
        selectSnapshot(
            snapshotsList,
            cfg,
            sid,
            'SnapshotID to remove',
            mount_manager.path
        )
        for sid in snapshot_ids
    ]

    if not force:
        print('Do you really want to remove these backups?')

        for sid in sids:
            print(sid.displayName)

        if not 'yes' == input('(no/yes): '):
            return

    s = snapshots.Snapshots(cfg)

    for sid in sids:
        s.remove(sid)


def checkConfig(cfg, crontab=True):
    def announceTest():
        print()
        print(frame(test))

    def failed():
        print(test + ': ' + bcolors.FAIL + 'failed' + bcolors.ENDC)

    def okay():
        print(test + ': ' + bcolors.OKGREEN + 'done' + bcolors.ENDC)

    def errorHandler(msg):
        print(bcolors.WARNING + 'WARNING: ' + bcolors.ENDC + msg)

    core_events.event_error.register(errorHandler)
    # cfg.setErrorHandler(errorHandler)
    mode = cfg.snapshotsMode()

    mount_manager = MountManager.create(cfg)

    if cfg.SNAPSHOT_MODES[mode][0] is not None:
        # preMountCheck
        test = 'Run mount tests'
        announceTest()

        try:
            mount_manager.validate()

        except MountError as exc:
            failed()
            print(str(exc))
            return False

        okay()

        # okay, let's try to mount
        test = 'Mount'
        announceTest()

        try:
            mount_manager.mount()

        except MountError as exc:
            failed()
            print(str(exc))
            return False

        okay()

    test = 'Check/prepare backup path'
    announceTest()
    # snapshots_mountpoint = cfg.get_snapshots_mountpoint(tmp_mount=True)

    ret = tools.validate_and_prepare_snapshots_path(
        path=mount_manager.path,
        host_user_profile=cfg.hostUserProfile(),
        mode=mode,
        copy_links=cfg.copyLinks(),
        error_event=core_events.event_error
    )

    if not ret:
        failed()
        return False

    okay()

    # umount
    if not cfg.SNAPSHOT_MODES[mode][0] is None:
        test = 'Unmount'
        announceTest()

        try:
            mount_manager.umount()

        except MountError as exc:
            failed()
            print(str(exc))
            return False

        okay()

    test = 'Check config'
    announceTest()

    agent = CheckConfigAgent()
    if agent.check() is False:
        failed()
        return False

    okay()

    if crontab:
        test = 'Install crontab'
        announceTest()

        try:
            cfg.setup_automation()

        except Exception as exc:
            failed()
            print(str(exc))
            return False

        okay()

    return True


def selectSnapshot(snapshotsList,
                   cfg,
                   snapshot_id=None,
                   msg='SnapshotID',
                   mounted_path=None
                   ):
    """
    check if given snapshot is valid. If not print a list of all
    snapshots and ask to choose one
    """
    len_snapshots = len(snapshotsList)

    if not snapshot_id is None:

        try:
            sid = snapshots.SID(
                date=snapshot_id,
                cfg=cfg,
                mounted_path=mounted_path)

            if sid in snapshotsList:
                return sid
            else:
                print('SnapshotID %s not found.' % snapshot_id)

        except ValueError:
            try:
                index = int(snapshot_id)
                return snapshotsList[index]

            except (ValueError, IndexError):
                print('Invalid SnaphotID index: %s' % snapshot_id)

    snapshot_id = None

    columns = (terminalSize()[1] - 25) // 26 + 1
    rows = len_snapshots // columns

    if len_snapshots % columns > 0:
        rows += 1

    print('SnapshotID\'s:')

    for row in range(rows):
        line = []

        for column in range(columns):
            index = row + column * rows

            if index > len_snapshots - 1:
                continue

            line.append('{i:>4}: {s}'.format(i=index, s=snapshotsList[index]))

        print(' '.join(line))

    print('')

    while snapshot_id is None:

        try:
            index = int(input(msg + ' (0 - %d): ' % (len_snapshots - 1)))
            snapshot_id = snapshotsList[index]

        except (ValueError, IndexError):
            print('Invalid Input')
            continue

    return snapshot_id


def terminalSize():
    """
    get terminal size
    """
    for fd in (sys.stdin, sys.stdout, sys.stderr):

        try:
            import fcntl
            import termios
            import struct
            return [
                int(x) for x in struct.unpack(
                    'hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
            ]

        except ImportError:
            pass

    return [24, 80]


def frame(msg, size=32):
    ret = ' +' + '-' * size + '+\n'
    ret += ' |' + msg.center(size) + '|\n'
    ret += ' +' + '-' * size + '+'

    return ret


class RestoreDialog:
    def __init__(self, cfg, sid, what, where, force_checksum_use, **kwargs):
        self.config = cfg
        self.sid = sid
        self.what = what
        self.where = where
        self.kwargs = kwargs
        self.force_checksum_use = force_checksum_use

        self.logFile = self.config.restoreLogFile()

        if os.path.exists(self.logFile):
            os.remove(self.logFile)

    def callback(self, line, *_args):
        if not line:
            return

        print(line)

        with open(self.logFile, mode='a', encoding='utf-8') as log:
            log.write(line + '\n')

    def run(self):
        s = snapshots.Snapshots(self.config)
        s.restore(
            self.sid,
            self.what,
            self.callback,
            self.where,
            self.force_checksum_use,
            **self.kwargs
        )
        print('\nLog saved to %s' % self.logFile)


class BackupJobDaemon(daemon.Daemon):
    def __init__(self, func, args):
        super(BackupJobDaemon, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.func(self.args, False)


def set_quiet(quiet: bool):
    """
    Redirect :py:data:`sys.stdout` to ``/dev/null`` if ``--quiet`` was set on
    commandline. Return the original :py:data:`sys.stdout` file object which
    can be used to print absolute necessary information.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Returns:
        sys.stdout:     default sys.stdout
    """
    force_stdout = sys.stdout

    if quiet:
        # do not replace with subprocess.DEVNULL - will not work
        sys.stdout = open(os.devnull, 'w')
        atexit.register(sys.stdout.close)
        atexit.register(force_stdout.close)

    return force_stdout


def detect_cipher_settings() -> tuple[str, str, str]:
    """See issue #2176."""
    result = []
    cfg = Konfig()
    cipher_keys = list(filter(
        lambda key: 'cipher' in key, cfg._conf.keys()
    ))

    for key in cipher_keys:
        val = cfg._conf[key]
        if val.lower() == 'default':
            continue

        pid = key.split('.')[0].replace('profile', '')
        if pid == '1':
            name = 'Main profile'
        else:
            name = cfg._conf[f'{key.split('.')[0]}.name']

        result.append((f'"{name}" ({pid})', val, key))

    return result


def _warn_about_global_config():
    """See issue #2493. Global config is not supported anymore.
    """

    if not bitbase.GLOBAL_CONFIG_PATH.exists():
        return

    logger.critical(
        f'The global config file ({bitbase.GLOBAL_CONFIG_PATH}) is no longer '
        'supported. Remove it. Back In Time only supports per-user '
        'configuration files.'
    )


def _warn_about_cipher() -> None:
    """See issue #2176. Cipher options is not used anymore by BIT.
    Therefore, users having it in config need to be warned about it.
    """
    for name, val, _key in detect_cipher_settings():
        logger.critical(
            f'Oboslete cipher setting "{val}" detected in profile {name}. '
            f'Cipher support was removed from Back In Time. Check the backup '
            'profile and also remove this setting from the config file.'
        )


def _warn_about_remote_host_check() -> None:
    """See issue #2482. Those settings are deprecated.
    """
    for name, key in detect_remote_host_check_settings():
        logger.critical(
            f'DEPRECATED setting "{key}" not set to default "true" detected '
            f'in profile {name}. Please contact the project and describe '
            'your use case and why you need this setting be disabled.'
        )


def detect_remote_host_check_settings() -> tuple[str, str, str]:
    """See issue #2482."""
    result = []
    cfg = Konfig()

    rh_keys = sorted(filter(
        lambda key: 'snapshots.ssh.check_' in key, cfg._conf.keys()
    ))

    for key in rh_keys:
        # ignore default (true)
        if cfg._conf[key].lower() == 'true':
            continue

        pid = key.split('.')[0].replace('profile', '')

        # SSH mode ?
        if 'ssh' not in cfg._conf[f'profile{pid}.snapshots.mode']:
            # irrelevant not SSH
            continue

        if pid == '1':
            name = 'Main profile'
        else:
            name = cfg._conf[f'{key.split('.')[0]}.name']

        result.append((f'"{name}" ({pid})', key))

    return result


def _backup_and_remove_encfs_config(cfg: Konfig) -> bool:
    """EncFS encryption feature was removed from Back In Time (#1734).
    This function detects existing EncFS profiles. If detected a backup is
    created of the complete config file and the EncFS profiles removed after.
    """
    encfs_pids = []
    names = ''

    for profile in cfg.iter_profiles():
        if 'encfs' in profile.mode.lower():
            name = profile.name
            pid = profile.profile_id
            logger.critical(
                f'Profile "{name}" ({pid}) uses '
                'obsolete EncFS encryption. '
                'EncFS support was removed from Back In Time.'
            )
            encfs_pids.append(pid)
            names += f', "{name}" ({pid})'

    # no further action needed
    if not encfs_pids:
        return False

    # do backup
    config_fp = Path(cfg._LOCAL_CONFIG_PATH)
    config_fp_backup = config_fp.with_suffix(
        bitbase.ENCFS_BACKUP_CONFIG_SUFFIX
    )
    shutil.copyfile(config_fp, config_fp_backup)

    for pid in encfs_pids:
        cfg.profile(pid).remove()

    if len(cfg.profiles):
        cfg.save(config_fp)
    else:
        # If no profile is left, remove the file itself
        config_fp.unlink()

    logger.critical(
        f'A backup of the current config file was created: {config_fp} -> '
        f'{config_fp_backup}. All detected EncFS profiles were removed '
        f'from the active configuration. Affected profiles are: {names}'
    )

    return True


def get_config_and_select_profile(
        config_path: Path,
        # data_path: str,
        pid_or_name: Union[str, int]
        # checksum: Optional[bool] = None
        # check: bool = True
) -> Konfig:
    """Load config and change to profile selected on commandline.

    Args:
        config_path: Path to config file.
        data_path: Path to "share_path".
        pid_or_name: Name or ID of the profile.
        checksum: Use checksum option.
        check: If ``True`` check if config is valid.

    Returns:
        Current the config

    Raises: SystemExit: 1 if ``profile`` or ``profile_id`` is no valid
        profile. 2 if ``check`` is ``True`` and config is not configured

    """
    logger.debug(f'Config path: {config_path}')

    # Workaround: Sometimes the id is given as string.
    if pid_or_name and pid_or_name.isdigit():
        pid_or_name = int(pid_or_name)

    _warn_about_global_config()

    cfg = Konfig()
    cfg.load(config_path)

    # cfg = config.Config(config_path=config_path, data_path=data_path)

    # detect and remove encfs profiles
    if _backup_and_remove_encfs_config(cfg):
        # re-read again
        cfg.load(config_path)

    # Just warn about cipher settings if present.
    _warn_about_cipher()

    # Warn about deprecated remote host check settings (#2482)
    _warn_about_remote_host_check()

    # explicit select a profile?
    if pid_or_name and not cfg.has_profile(pid_or_name):
        logger.error(f'Profile not found: {pid_or_name}')
        sys.exit(bitbase.RETURN_ERR)

    # if check and not cfg.isConfigured():
    #     logger.error(f'{cfg.APP_NAME} is not configured!')
    #     sys.exit(bitbase.RETURN_NO_CFG)

    # if checksum is not None:
    #     cfg.forceUseChecksum = checksum

    return cfg
