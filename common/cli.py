# -*- coding: utf-8 -*-
#    Back In Time
#    Copyright (C) 2012-2016 Germar Reitze
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys

import tools
import snapshots
import bcolors

def restore(cfg, snapshot_id = None, what = None, where = None, **kwargs):
    if what is None:
        what = input('File to restore: ')
    what = tools.prepare_path(os.path.abspath(os.path.expanduser(what)))

    if where is None:
        where = input('Restore to (empty for original path): ')
    if where:
        where = tools.prepare_path(os.path.abspath(os.path.expanduser(where)))

    snapshots_list = snapshots.listSnapshots(cfg)

    sid = selectSnapshot(snapshots_list, cfg, snapshot_id, 'SnapshotID to restore')
    print('')
    RestoreDialog(cfg, sid, what, where, **kwargs).run()

def remove(cfg, snapshot_ids = None, force = None):
    snapshots_list = snapshots.listSnapshots(cfg)
    if not snapshot_ids:
        snapshot_ids = (None,)
    sids = [selectSnapshot(snapshots_list, cfg, sid, 'SnapshotID to remove') for sid in snapshot_ids]

    if not force:
        print('Do you really want to remove this snapshots?')
        [print(sid.displayName) for sid in sids]
        if not 'yes' == input('(no/yes): '):
            return

    s = snapshots.Snapshots(cfg)
    [s.remove_snapshot(sid) for sid in sids]

def checkConfig(cfg, crontab = True):
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

    cfg.set_error_handler(errorHandler)
    mode = cfg.get_snapshots_mode()

    if cfg.SNAPSHOT_MODES[mode][0] is not None:
        #pre_mount_check
        test = 'Run mount tests'
        announceTest()
        mnt = mount.Mount(cfg = cfg, tmp_mount = True)
        try:
            mnt.pre_mount_check(mode = mode, first_run = True)
        except MountException as ex:
            failed()
            print(str(ex))
            return False
        okay()

        #okay, lets try to mount
        test = 'Mount'
        announceTest()
        try:
            hash_id = mnt.mount(mode = mode, check = False)
        except MountException as ex:
            failed()
            print(str(ex))
            return False
        okay()

    test = 'Check/prepair snapshot path'
    announceTest()
    snapshots_path = cfg.get_snapshots_path(mode = mode, tmp_mount = True)

    if not cfg.set_snapshots_path( snapshots_path, mode = mode ):
        failed()
        return False
    okay()

    #umount
    if not cfg.SNAPSHOT_MODES[mode][0] is None:
        test = 'Unmount'
        announceTest()
        try:
            mnt.umount(hash_id = hash_id)
        except MountException as ex:
            failed()
            print(str(ex))
            return False
        okay()

    test = 'Check config'
    announceTest()
    if not cfg.check_config():
        failed()
        return False
    okay()

    if crontab:
        test = 'Install crontab'
        announceTest()
        if not cfg.setup_cron():
            failed()
            return False
        okay()

    return True

def selectSnapshot(snapshots_list, cfg, snapshot_id = None, msg = 'SnapshotID'):
    """
    check if given snapshot is valid. If not print a list of all
    snapshots and ask to choose one
    """
    len_snapshots = len(snapshots_list)

    if not snapshot_id is None:
        try:
            sid = snapshots.SID(snapshot_id, cfg)
            if sid in snapshots_list:
                return sid
            else:
                print('SnapshotID %s not found.' % snapshot_id)
        except ValueError:
            try:
                index = int(snapshot_id)
                return snapshots_list[index]
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
            line.append('{i:>4}: {s}'.format(i = index, s = snapshots_list[index]))
        print(' '.join(line))
    print('')
    while snapshot_id is None:
        try:
            index = int(input(msg + ' ( 0 - %d ): ' % (len_snapshots - 1) ))
            snapshot_id = snapshots_list[index]
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
            import fcntl, termios, struct
            return [int(x) for x in struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))]
        except:
            pass
    return [24, 80]

def frame(msg, size = 32):
    ret  = ' ┌' + '─' * size +       '┐\n'
    ret += ' │' + msg.center(size) + '│\n'
    ret += ' └' + '─' * size +       '┘'
    return ret

class RestoreDialog(object):
    def __init__(self, cfg, sid, what, where, **kwargs):
        self.config = cfg
        self.sid = sid
        self.what = what
        self.where = where
        self.kwargs = kwargs

        self.log_file = self.config.get_restore_log_file()
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def callback(self, line, *params):
        if not line:
            return
        print(line)
        with open(self.log_file, 'a') as log:
            log.write(line + '\n')

    def run(self):
        s = snapshots.Snapshots(self.config)
        s.restore(self.sid, self.what, self.callback, self.where, **self.kwargs)
        print('\nLog saved to %s' % self.log_file)
