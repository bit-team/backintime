#    Back In Time
#    Copyright (c) 2012-2013 Germar Reitze
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
        what = raw_input('File to restore: ')
    what = tools.prepare_path(os.path.abspath(os.path.expanduser(what)))

    if where is None:
        where = raw_input('Restore to (empty for original path): ')
    if len(where) >= 1:
        where = tools.prepare_path(os.path.abspath(os.path.expanduser(where)))

    _snapshots = snapshots.Snapshots(cfg)
    snapshot_list = _snapshots.get_snapshots_list()
    if not snapshot_id is None:
        if len(snapshot_id) == 19:
            if not snapshot_id in snapshot_list:
                print 'SnapshotID %s not found.' % snapshot_id
                snapshot_id = None
        else:
            try:
                index = int(snapshot_id)
                snapshot_id = snapshot_list[index]
            except (ValueError, IndexError):
                print 'Invalid SnaphotID index: %s' % snapshot_id
                snapshot_id = None
    if snapshot_id is None:
        print '\nSnapshotID\'s:'
        #get terminal size
        size = (24, 80)
        for fd in (sys.stdin, sys.stdout, sys.stderr):
            try:
                import fcntl, termios, struct
                rc = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
            except:
                rc = None
            if not rc is None:
                size = rc
                break
        len_snapshots = len(snapshot_list)
        columns = (int(size[1]) - 25) / 26 + 1
        rows = len_snapshots // columns
        if len_snapshots % columns > 0:
            rows += 1
        for row in range(rows):
            line = []
            for column in range(columns):
                index = row + column * rows
                if index > len_snapshots - 1:
                    continue
                line.append('{i:>4}: {s}'.format(i = index, s = snapshot_list[index]))
            print ' '.join(line)
        print ''
        while snapshot_id is None:
            try:
                input = int(raw_input('SnapshotID to restore ( 0 - %d ): ' % (len_snapshots - 1) ))
                snapshot_id = snapshot_list[input]
            except (ValueError, IndexError):
                print 'Invalid Input'
                continue

    print ''
    RestoreDialog(cfg, _snapshots, snapshot_id, what, where).run()

class RestoreDialog(object):
    def __init__(self, cfg, _snapshots, snapshot_id, what, where):
        self.config = cfg
        self.snapshots = _snapshots
        self.snapshot_id = snapshot_id
        self.what = what
        self.where = where
        
        self.log_file = self.config.get_restore_log_file()
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def callback(self, line, *params):
        print line
        with open(self.log_file, 'a') as log:
            log.write(line + '\n')

    def run(self):
        self.snapshots.restore(self.snapshot_id, self.what, self.callback, self.where)
        print '\nLog saved to %s' % self.log_file