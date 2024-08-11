# Back In Time
# Copyright (C) 2016-2022 Germar Reitze
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys
import re
from test import generic
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import snapshotlog
import snapshots


class TestLogFilter(generic.TestCase):
    #TODO: add decode test
    def __init__(self, *args, **kwargs):
        super(TestLogFilter, self).__init__(*args, **kwargs)
        self.e = '[E] foo bar'
        self.c = '[C] foo bar'
        self.i = '[I] foo bar'
        self.n = ''
        self.h = '========== header ==========='

    def test_filter(self):
        #No filter
        logFilter = snapshotlog.LogFilter()
        for line in (self.e, self.c, self.i, self.n, self.h):
            self.assertEqual(line, logFilter.filter(line))

        #Error filter
        logFilter = snapshotlog.LogFilter(mode = snapshotlog.LogFilter.ERROR)
        for line in (self.e, self.n, self.h):
            self.assertEqual(line, logFilter.filter(line))
        for line in (self.c, self.i):
            self.assertIsNone(logFilter.filter(line))

        #Changes filter
        logFilter = snapshotlog.LogFilter(mode = snapshotlog.LogFilter.CHANGES)
        for line in (self.c, self.n, self.h):
            self.assertEqual(line, logFilter.filter(line))
        for line in (self.e, self.i):
            self.assertIsNone(logFilter.filter(line))

        #Information filter
        logFilter = snapshotlog.LogFilter(mode = snapshotlog.LogFilter.INFORMATION)
        for line in (self.i, self.n, self.h):
            self.assertEqual(line, logFilter.filter(line))
        for line in (self.c, self.e):
            self.assertIsNone(logFilter.filter(line))

        #Error + Changes filter
        logFilter = snapshotlog.LogFilter(mode = snapshotlog.LogFilter.ERROR_AND_CHANGES)
        for line in (self.e, self.c, self.n, self.h):
            self.assertEqual(line, logFilter.filter(line))
        for line in (self.i,):
            self.assertIsNone(logFilter.filter(line))

        # New filter (#1587): rsync transfer failures (experimental)
        logFilter = snapshotlog.LogFilter(mode=snapshotlog.LogFilter.RSYNC_TRANSFER_FAILURES)
        log_lines = (
            '[I] Take snapshot (rsync: symlink has no referent: "/home/user/Documents/dead-link")',
            '[E] Error: rsync: [sender] send_files failed to open "/home/user/Documents/root_only_file.txt": Permission denied (13)',
            '[I] Schnappschuss erstellen (rsync: IO error encountered -- skipping file deletion)',
            '[I] Schnappschuss erstellen (rsync: rsync error: some files/attrs were not transferred (see previous errors) (code 23) at main.c(1333) [sender=3.2.3])',
            '[I] Take snapshot (rsync: rsync error: some files/attrs were not transferred (see previous errors) (code 23) at main.c(1333) [sender=3.2.3])',
        )
        for line in log_lines:
            self.assertEqual(line, logFilter.filter(line))
        for line in (self.e, self.c, self.i, self.h):
            self.assertIsNone(logFilter.filter(line))
        for line in self.n:
            self.assertEqual(line, logFilter.filter(line))  # empty line stays empty line

class TestSnapshotLog(generic.SnapshotsTestCase):
    def setUp(self):
        super(TestSnapshotLog, self).setUp()
        self.logFile = os.path.join(self.cfg._LOCAL_DATA_FOLDER, 'takesnapshot_.log')

    def test_new(self):
        log = snapshotlog.SnapshotLog(self.cfg)
        now = datetime.today()
        with open(self.logFile, 'wt') as f:
            f.write('foo\nbar\n')

        log.new(now)
        log.flush()
        self.assertExists(self.logFile)
        with open(self.logFile, 'rt') as f:
            self.assertRegex(f.read(), re.compile(r'''========== Take snapshot \(profile .*\): .* ==========

''', re.MULTILINE))

    def test_new_continue(self):
        log = snapshotlog.SnapshotLog(self.cfg)
        now = datetime.today()
        with open(self.logFile, 'wt') as f:
            f.write('foo\nbar\n')
        new = snapshots.NewSnapshot(self.cfg)
        new.makeDirs()
        new.saveToContinue = True

        log.new(now)
        log.flush()
        self.assertExists(self.logFile)
        with open(self.logFile, 'rt') as f:
            self.assertRegex(f.read(), re.compile(r'''foo
bar
Last snapshot didn't finish but can be continued.

======== continue snapshot \(profile .*\): .* ========

''', re.MULTILINE))

    def test_append(self):
        log = snapshotlog.SnapshotLog(self.cfg)

        log.append('foo', 1)
        log.flush()
        self.assertExists(self.logFile)
        with open(self.logFile, 'rt') as f:
            self.assertEqual(f.read(), 'foo\n')

    def test_append_log_level(self):
        self.cfg.setLogLevel(2)
        log = snapshotlog.SnapshotLog(self.cfg)

        log.append('foo', 3)
        log.flush()
        self.assertNotExists(self.logFile)

        log.append('bar', 1)
        log.flush()
        self.assertExists(self.logFile)
        with open(self.logFile, 'rt') as f:
            self.assertEqual(f.read(), 'bar\n')

    def test_get(self):
        log = snapshotlog.SnapshotLog(self.cfg)

        log.append('foo bar', 1)
        log.flush()
        self.assertExists(self.logFile)
        self.assertEqual('\n'.join(log.get()), 'foo bar')

    def test_get_filter(self):
        log = snapshotlog.SnapshotLog(self.cfg)

        log.append('foo bar', 1)
        log.append('[I] 123', 1)
        log.append('[C] baz', 1)
        log.append('[E] bla', 1)
        log.flush()
        self.assertExists(self.logFile)
        self.assertEqual('\n'.join(log.get(mode = snapshotlog.LogFilter.CHANGES)), 'foo bar\n[C] baz')

    def test_skipLines_show_all(self):
        log = snapshotlog.SnapshotLog(self.cfg)

        for i in range(10):
            log.append(str(i), 1)
        log.flush()

        self.assertEqual('\n'.join(log.get(skipLines = 0)),
                         '\n'.join([str(i) for i in range(10)]))

    def test_skipLines(self):
        log = snapshotlog.SnapshotLog(self.cfg)

        for i in range(10):
            log.append(str(i), 1)
        log.flush()

        self.assertEqual('\n'.join(log.get(skipLines = 4)),
                         '\n'.join([str(i) for i in range(4, 10)]))

    def test_skipLines_filtered(self):
        log = snapshotlog.SnapshotLog(self.cfg)

        log.append('foo bar', 1)
        log.append('[I] 123', 1)
        log.append('[C] baz', 1)
        log.append('[E] bla', 1)
        log.append('[C] 456', 1)
        log.append('[C] 789', 1)
        log.append('[E] qwe', 1)
        log.append('[C] asd', 1)
        log.flush()

        self.assertEqual('\n'.join(log.get(mode = snapshotlog.LogFilter.CHANGES, skipLines = 2)),
                         '[C] 456\n[C] 789\n[C] asd')
