#    Back In Time
#    Copyright (C) 2012-2015 Germar Reitze
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

def restore(cfg, snapshot_id = None, what = None, where = None):
    if what is None:
        what = input('File to restore: ')
    what = tools.prepare_path(os.path.abspath(os.path.expanduser(what)))

    if where is None:
        where = input('Restore to (empty for original path): ')
    if where:
        where = tools.prepare_path(os.path.abspath(os.path.expanduser(where)))

    snapshots_ = snapshots.Snapshots(cfg)
    snapshot_id = selectSnapshot(snapshots_, snapshot_id, 'SnapshotID to restore')
    print('')
    RestoreDialog(cfg, snapshots_, snapshot_id, what, where).run()

def remove(cfg, snapshot_ids = None, force = None):
    snapshots_ = snapshots.Snapshots(cfg)
    ids = [selectSnapshot(snapshots_, id, 'SnapshotID to remove') for id in snapshot_ids]

    if not force:
        print('Do you really want to remove this snapshots?')
        [print(snapshots_.get_snapshot_display_name(id)) for id in ids]
        if not 'yes' == input('(no/yes): '):
            return
    
    [snapshots_.remove_snapshot(id) for id in ids]

def selectSnapshot(snapshots_, snapshot_id = None, msg = 'SnapshotID'):
    '''check if given snapshot is valid. If not print a list of all
    snapshots and ask to choose one'''
    snapshot_list = snapshots_.get_snapshots_list()
    len_snapshots = len(snapshot_list)

    if not snapshot_id is None:
        if len(snapshot_id) == 19:
            if snapshot_id in snapshot_list:
                return snapshot_id
            else:
                print('SnapshotID %s not found.' % snapshot_id)
        else:
            try:
                index = int(snapshot_id)
                return snapshot_list[index]
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
            line.append('{i:>4}: {s}'.format(i = index, s = snapshot_list[index]))
        print(' '.join(line))
    print('')
    while snapshot_id is None:
        try:
            sid = int(input(msg + ' ( 0 - %d ): ' % (len_snapshots - 1) ))
            snapshot_id = snapshot_list[sid]
        except (ValueError, IndexError):
            print('Invalid Input')
            continue
    return snapshot_id

def terminalSize():
    '''get terminal size'''
    for fd in (sys.stdin, sys.stdout, sys.stderr):
        try:
            import fcntl, termios, struct
            return [int(x) for x in struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))]
        except:
            pass
    return [24, 80]

class RestoreDialog(object):
    def __init__(self, cfg, snapshots_, snapshot_id, what, where):
        self.config = cfg
        self.snapshots = snapshots_
        self.snapshot_id = snapshot_id
        self.what = what
        self.where = where

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
        self.snapshots.restore(self.snapshot_id, self.what, self.callback, self.where)
        print('\nLog saved to %s' % self.log_file)
