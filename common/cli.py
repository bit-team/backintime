# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
import atexit
import tools
import daemon
import snapshots
import bcolors
import config
import logger
import bitbase
from typing import Optional
from version import __version__


def restore(cfg, snapshot_id=None, what=None, where=None, **kwargs):
    if what is None:
        what = input('File to restore: ')

    what = tools.preparePath(os.path.abspath(os.path.expanduser(what)))

    if where is None:
        where = input('Restore to (empty for original path): ')

    if where:
        where = tools.preparePath(os.path.abspath(os.path.expanduser(where)))

    snapshotsList = snapshots.listSnapshots(cfg)

    sid = selectSnapshot(snapshotsList, cfg, snapshot_id, 'SnapshotID to restore')
    print('')

    RestoreDialog(cfg, sid, what, where, **kwargs).run()


def remove(cfg, snapshot_ids=None, force=None):
    snapshotsList = snapshots.listSnapshots(cfg)

    if not snapshot_ids:
        snapshot_ids = (None,)

    sids = [
        selectSnapshot(snapshotsList, cfg, sid, 'SnapshotID to remove')
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
    import mount
    from exceptions import MountException

    def announceTest():
        print()
        print(frame(test))

    def failed():
        print(test + ': ' + bcolors.FAIL + 'failed' + bcolors.ENDC)

    def okay():
        print(test + ': ' + bcolors.OKGREEN + 'done' + bcolors.ENDC)

    def errorHandler(msg):
        print(bcolors.WARNING + 'WARNING: ' + bcolors.ENDC + msg)

    cfg.setErrorHandler(errorHandler)
    mode = cfg.snapshotsMode()

    if cfg.SNAPSHOT_MODES[mode][0] is not None:
        # preMountCheck
        test = 'Run mount tests'
        announceTest()
        mnt = mount.Mount(cfg = cfg, tmp_mount = True)

        try:
            mnt.preMountCheck(mode = mode, first_run = True)

        except MountException as ex:
            failed()
            print(str(ex))
            return False

        okay()

        # okay, let's try to mount
        test = 'Mount'
        announceTest()

        try:
            hash_id = mnt.mount(mode=mode, check=False)

        except MountException as ex:
            failed()
            print(str(ex))
            return False

        okay()

    test = 'Check/prepare backup path'
    announceTest()
    snapshots_mountpoint = cfg.get_snapshots_mountpoint(tmp_mount=True)

    ret = tools.validate_and_prepare_snapshots_path(
        path=snapshots_mountpoint,
        host_user_profile=cfg.hostUserProfile(),
        mode=mode,
        copy_links=cfg.copyLinks(),
        error_handler=cfg.notifyError)

    if not ret:
        failed()
        return False

    okay()

    # umount
    if not cfg.SNAPSHOT_MODES[mode][0] is None:
        test = 'Unmount'
        announceTest()

        try:
            mnt.umount(hash_id=hash_id)

        except MountException as ex:
            failed()
            print(str(ex))
            return False

        okay()

    test = 'Check config'
    announceTest()

    if not cfg.checkConfig():
        failed()
        return False

    okay()

    if crontab:
        test = 'Install crontab'
        announceTest()

        if not cfg.setupCron():
            failed()
            return False

        okay()

    return True


def selectSnapshot(snapshotsList, cfg, snapshot_id=None, msg='SnapshotID'):
    """
    check if given snapshot is valid. If not print a list of all
    snapshots and ask to choose one
    """
    len_snapshots = len(snapshotsList)

    if not snapshot_id is None:

        try:
            sid = snapshots.SID(snapshot_id, cfg)

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
    def __init__(self, cfg, sid, what, where, **kwargs):
        self.config = cfg
        self.sid = sid
        self.what = what
        self.where = where
        self.kwargs = kwargs

        self.logFile = self.config.restoreLogFile()
        if os.path.exists(self.logFile):
            os.remove(self.logFile)

    def callback(self, line, *params):
        if not line:
            return
        print(line)
        with open(self.logFile, 'a') as log:
            log.write(line + '\n')

    def run(self):
        s = snapshots.Snapshots(self.config)
        s.restore(self.sid, self.what, self.callback, self.where, **self.kwargs)
        print('\nLog saved to %s' % self.logFile)


class BackupJobDaemon(daemon.Daemon):
    def __init__(self, func, args):
        super(BackupJobDaemon, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.func(self.args, False)


def set_quiet(args):
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

    if args.quiet:
        # do not replace with subprocess.DEVNULL - will not work
        sys.stdout = open(os.devnull, 'w')
        atexit.register(sys.stdout.close)
        atexit.register(force_stdout.close)

    return force_stdout


def print_header():
    """Print application name, version and legal notes."""
    print(
        f'\n{bitbase.APP_NAME}\n'
        f'Version: {__version__}\n'
        '\n'
        'Back In Time comes with ABSOLUTELY NO WARRANTY.\n'
        'This is free software, and you are welcome to redistribute it\n'
        "under certain conditions; type `backintime --license' for details.\n"
        '\n'
    )


def get_config_and_select_profile(
        config_path: str,
        data_path: str,
        profile: str,
        checksum: Optional[bool] = None,
        check: bool = True) -> config.Config:
    """Load config and change to profile selected on commandline.

    Args:
        config_path: Path to config file.
        data_path: Path to "share_path".
        profile: Name or ID of the profile.
        checksum: Use checksum option.
        check: If ``True`` check if config is valid.

    Returns:
        Current config with requested profile selected.

    Raises: SystemExit: 1 if ``profile`` or ``profile_id`` is no valid
        profile. 2 if ``check`` is ``True`` and config is not configured

    """
    cfg = config.Config(
        config_path=config_path,
        data_path=data_path)

    if profile:
        if profile.isdigit():
            if not cfg.setCurrentProfile(int(profile)):
                logger.error(f'Profile-ID not found: {profile}')
                sys.exit(bitbase.RETURN_ERR)
        else:
            if not cfg.setCurrentProfileByName(profile):
                logger.error(f'Profile not found: {profile}')
                sys.exit(bitbase.RETURN_ERR)

    if check and not cfg.isConfigured():
        logger.error(f'{cfg.APP_NAME} is not configured!')
        sys.exit(bitbase.RETURN_NO_CFG)

    if checksum is not None:
        cfg.forceUseChecksum = checksum

    return cfg
