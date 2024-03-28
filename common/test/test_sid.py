# Back In Time
# Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys
import unittest
import stat
import re
from datetime import date, datetime
from test import generic
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import configfile
import snapshots
import logger
from snapshotlog import LogFilter, SnapshotLog

class TestSID(generic.SnapshotsTestCase):
    def test_new_object_with_valid_date(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        sid2 = snapshots.SID('20151219-010324', self.cfg)
        sid3 = snapshots.SID(datetime(2015, 12, 19, 1, 3, 24), self.cfg)
        sid4 = snapshots.SID(date(2015, 12, 19), self.cfg)

        self.assertEqual(sid1.sid,  '20151219-010324-123')
        self.assertEqual(sid2.sid,  '20151219-010324')
        self.assertRegex(sid3.sid, r'20151219-010324-\d{3}')
        self.assertRegex(sid4.sid, r'20151219-000000-\d{3}')

    def test_new_object_with_invalid_value(self):
        with self.assertRaises(ValueError):
            snapshots.SID('20151219-010324-1234', self.cfg)
        with self.assertRaises(ValueError):
            snapshots.SID('20151219-01032', self.cfg)
        with self.assertRaises(ValueError):
            snapshots.SID('2015121a-010324-1234', self.cfg)

    def test_new_object_with_invalid_type(self):
        with self.assertRaises(TypeError):
            snapshots.SID(123, self.cfg)

    def test_equal_sid(self):
        sid1a = snapshots.SID('20151219-010324-123', self.cfg)
        sid1b = snapshots.SID('20151219-010324-123', self.cfg)
        sid2  = snapshots.SID('20151219-020324-123', self.cfg)

        self.assertIsNot(sid1a, sid1b)
        self.assertTrue(sid1a == sid1b)
        self.assertTrue(sid1a == '20151219-010324-123')
        self.assertTrue(sid1a != sid2)
        self.assertTrue(sid1a != '20151219-020324-123')

    def test_sort_sids(self):
        root = snapshots.RootSnapshot(self.cfg)
        new  = snapshots.NewSnapshot(self.cfg)
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        sid2 = snapshots.SID('20151219-020324-123', self.cfg)
        sid3 = snapshots.SID('20151219-030324-123', self.cfg)
        sid4 = snapshots.SID('20151219-040324-123', self.cfg)

        sids1 = [sid3, sid1, sid4, sid2]
        sids1.sort()
        self.assertEqual(sids1, [sid1, sid2, sid3, sid4])

        #RootSnapshot 'Now' should always stay on top
        sids2 = [sid3, sid1, root, sid4, sid2]
        sids2.sort()
        self.assertEqual(sids2, [sid1, sid2, sid3, sid4, root])

        sids2.sort(reverse = True)
        self.assertEqual(sids2, [root, sid4, sid3, sid2, sid1])

        #new_snapshot should always be the last
        sids3 = [sid3, sid1, new, sid4, sid2]
        sids3.sort()
        self.assertEqual(sids3, [sid1, sid2, sid3, sid4, new])

        sids3.sort(reverse = True)
        self.assertEqual(sids3, [new, sid4, sid3, sid2, sid1])

    def test_hash(self):
        sid1a = snapshots.SID('20151219-010324-123', self.cfg)
        sid1b = snapshots.SID('20151219-010324-123', self.cfg)
        sid2  = snapshots.SID('20151219-020324-123', self.cfg)

        self.assertEqual(sid1a.__hash__(), sid1b.__hash__())
        self.assertNotEqual(sid1a.__hash__(), sid2.__hash__())

        s = set()
        s.add(sid1a)
        self.assertEqual(len(s), 1)
        s.add(sid2)
        self.assertEqual(len(s), 2)
        s.add(sid1b)
        self.assertEqual(len(s), 2)

    def test_split(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertTupleEqual(sid.split(), (2015, 12, 19, 1, 3, 24))

    def test_displayID(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.displayID, '2015-12-19 01:03:24')

    def test_displayName(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        with open(sid.path('name'), 'wt') as f:
            f.write('foo')

        self.assertEqual(sid.displayName, '2015-12-19 01:03:24 - foo')

        with open(sid.path('failed'), 'wt') as f:
            pass

        self.assertRegex(sid.displayName, r'2015-12-19 01:03:24 - foo (.+?)')

    def test_withoutTag(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.withoutTag, '20151219-010324')

    def test_tag(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.tag, '123')

    def test_path(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.path(),
                         os.path.join(self.snapshotPath, '20151219-010324-123'))
        self.assertEqual(sid.path('foo', 'bar', 'baz'),
                         os.path.join(self.snapshotPath,
                                      '20151219-010324-123',
                                      'foo', 'bar', 'baz'))
        self.assertEqual(sid.pathBackup(),
                         os.path.join(self.snapshotPath,
                                      '20151219-010324-123',
                                      'backup'))
        self.assertEqual(sid.pathBackup('/foo'),
                         os.path.join(self.snapshotPath,
                                      '20151219-010324-123',
                                      'backup', 'foo'))

    def test_makeDirs(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        self.assertTrue(sid.makeDirs())
        self.assertTrue(os.path.isdir(os.path.join(self.snapshotPath,
                                                   '20151219-010324-123',
                                                   'backup')))

        self.assertTrue(sid.makeDirs('foo', 'bar', 'baz'))
        self.assertTrue(os.path.isdir(os.path.join(self.snapshotPath,
                                                   '20151219-010324-123',
                                                   'backup',
                                                   'foo', 'bar', 'baz')))

    def test_exists(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        self.assertFalse(sid.exists())

        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        self.assertFalse(sid.exists())

        os.makedirs(os.path.join(self.snapshotPath,
                                 '20151219-010324-123',
                                 'backup'))
        self.assertTrue(sid.exists())

    def test_isExistingPathInsideSnapshotFolder(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        backupPath = os.path.join(self.snapshotPath,
                                  '20151219-010324-123',
                                  'backup')
        os.makedirs(os.path.join(backupPath, 'foo'))

        #test existing file and non existing file
        self.assertTrue(sid.isExistingPathInsideSnapshotFolder('/foo'))
        self.assertFalse(sid.isExistingPathInsideSnapshotFolder('/tmp'))

        #test valid absolute symlink inside snapshot
        os.symlink(os.path.join(backupPath, 'foo'),
                   os.path.join(backupPath, 'bar'))
        self.assertIsLink(backupPath, 'bar')
        self.assertTrue(sid.isExistingPathInsideSnapshotFolder('/bar'))

        #test valid relative symlink inside snapshot
        os.symlink('./foo',
                   os.path.join(backupPath, 'baz'))
        self.assertIsLink(backupPath, 'baz')
        self.assertTrue(sid.isExistingPathInsideSnapshotFolder('/baz'))

        #test invalid symlink
        os.symlink(os.path.join(backupPath, 'asdf'),
                   os.path.join(backupPath, 'qwer'))
        self.assertIsLink(backupPath, 'qwer')
        self.assertFalse(sid.isExistingPathInsideSnapshotFolder('/qwer'))

        #test valid symlink outside snapshot
        os.symlink('/tmp',
                   os.path.join(backupPath, 'bla'))
        self.assertIsLink(backupPath, 'bla')
        self.assertFalse(sid.isExistingPathInsideSnapshotFolder('/bla'))

    def test_name(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        self.assertEqual(sid.name, '')

        sid.name = 'foo'
        with open(sid.path('name'), 'rt') as f:
            self.assertEqual(f.read(), 'foo')

        self.assertEqual(sid.name, 'foo')

    def test_lastChecked(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'info')

        #no info file
        self.assertEqual(sid.lastChecked, '2015-12-19 01:03:24')

        #set time manually to 2015-12-19 02:03:24
        with open(infoFile, 'wt'):
            pass
        d = datetime(2015, 12, 19, 2, 3, 24)
        os.utime(infoFile, (d.timestamp(), d.timestamp()))
        self.assertEqual(sid.lastChecked, '2015-12-19 02:03:24')

        #setLastChecked and check if it matches current date
        sid.setLastChecked()
        now = datetime.now()
        self.assertRegex(sid.lastChecked, now.strftime(r'%Y-%m-%d %H:%M:\d{2}'))

    def test_failed(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        snapshotPath = os.path.join(self.snapshotPath, '20151219-010324-123')
        failedPath   = os.path.join(snapshotPath, sid.FAILED)
        os.makedirs(snapshotPath)

        self.assertNotExists(failedPath)
        self.assertFalse(sid.failed)
        sid.failed = True
        self.assertExists(failedPath)
        self.assertTrue(sid.failed)

        sid.failed = False
        self.assertNotExists(failedPath)
        self.assertFalse(sid.failed)

    def test_info(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'info')

        i1 = configfile.ConfigFile()
        i1.setStrValue('foo', 'bar')
        sid1.info = i1

        #test if file exist and has correct content
        self.assertIsFile(infoFile)
        with open(infoFile, 'rt') as f:
            self.assertEqual(f.read(), 'foo=bar\n')

        #new sid instance and test if correct value is returned
        sid2 = snapshots.SID('20151219-010324-123', self.cfg)
        i2 = sid2.info
        self.assertEqual(i2.strValue('foo', 'default'), 'bar')

    def test_fileInfo(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath,
                                '20151219-010324-123',
                                'fileinfo.bz2')

        d = snapshots.FileInfoDict()
        d[b'/tmp']     = (123, b'foo', b'bar')
        d[b'/tmp/foo'] = (456, b'asdf', b'qwer')
        sid1.fileInfo = d

        self.assertIsFile(infoFile)

        #load fileInfo in a new snapshot
        sid2 = snapshots.SID('20151219-010324-123', self.cfg)
        self.assertDictEqual(sid2.fileInfo, d)

    @patch('logger.error')
    def test_fileInfoErrorRead(self, mock_logger):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = sid.path(sid.FILEINFO)
        # remove all permissions from file
        with open(infoFile, 'wt') as f:
            pass

        with generic.mockPermissions(infoFile):
            self.assertEqual(sid.fileInfo, snapshots.FileInfoDict())
            self.assertTrue(mock_logger.called)

    @patch('logger.error')
    def test_fileInfoErrorWrite(self, mock_logger):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = sid.path(sid.FILEINFO)
        # remove all permissions from file
        with open(infoFile, 'wt') as f:
            pass

        with generic.mockPermissions(infoFile):
            d = snapshots.FileInfoDict()
            d[b'/tmp']     = (123, b'foo', b'bar')
            d[b'/tmp/foo'] = (456, b'asdf', b'qwer')
            sid.fileInfo = d
            self.assertTrue(mock_logger.called)

    def test_log(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath,
                               '20151219-010324-123',
                               'takesnapshot.log.bz2')

        #no log available
        self.assertRegex('\n'.join(sid.log()), r'Failed to get snapshot log from.*')

        sid.setLog('foo bar\nbaz')
        self.assertIsFile(logFile)

        self.assertEqual('\n'.join(sid.log()), 'foo bar\nbaz')

    def test_log_filter(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath,
                               '20151219-010324-123',
                               'takesnapshot.log.bz2')

        sid.setLog('foo bar\n[I] 123\n[C] baz\n[E] bla')
        self.assertIsFile(logFile)

        self.assertEqual('\n'.join(sid.log(mode = LogFilter.CHANGES)), 'foo bar\n[C] baz')

    def test_setLog_binary(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath,
                               '20151219-010324-123',
                               'takesnapshot.log.bz2')

        sid.setLog(b'foo bar\nbaz')
        self.assertIsFile(logFile)

        self.assertEqual('\n'.join(sid.log()), 'foo bar\nbaz')

    def test_makeWritable(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        sidPath = os.path.join(self.snapshotPath,   '20151219-010324-123')
        os.makedirs(sidPath)
        testFile = os.path.join(sidPath, 'test')

        #make only read and explorable
        os.chmod(sidPath, stat.S_IRUSR | stat.S_IXUSR)
        with self.assertRaises(PermissionError):
            with open(testFile, 'wt') as f:
                f.write('foo')

        sid.makeWritable()

        self.assertEqual(os.stat(sidPath).st_mode & stat.S_IWUSR, stat.S_IWUSR)
        try:
            with open(testFile, 'wt') as f:
                f.write('foo')
        except PermissionError:
            msg = 'writing to {} raised PermissionError unexpectedly!'
            self.fail(msg.format(testFile))

class TestNewSnapshot(generic.SnapshotsTestCase):
    def test_create_new(self):
        new = snapshots.NewSnapshot(self.cfg)
        self.assertFalse(new.exists())

        self.assertTrue(new.makeDirs())
        self.assertTrue(new.exists())
        self.assertTrue(os.path.isdir(os.path.join(self.snapshotPath,
                                                   new.NEWSNAPSHOT,
                                                   'backup')))

    def test_saveToContinue(self):
        new = snapshots.NewSnapshot(self.cfg)
        snapshotPath = os.path.join(self.snapshotPath, new.NEWSNAPSHOT)
        saveToContinuePath = os.path.join(snapshotPath, new.SAVETOCONTINUE)
        os.makedirs(snapshotPath)

        self.assertNotExists(saveToContinuePath)
        self.assertFalse(new.saveToContinue)

        new.saveToContinue = True
        self.assertExists(saveToContinuePath)
        self.assertTrue(new.saveToContinue)

        new.saveToContinue = False
        self.assertNotExists(saveToContinuePath)
        self.assertFalse(new.saveToContinue)

    def test_hasChanges(self):
        now = datetime(2016, 7, 10, 16, 24, 17)

        new = snapshots.NewSnapshot(self.cfg)
        new.makeDirs()

        log = SnapshotLog(self.cfg)
        log.new(now)
        self.assertFalse(new.hasChanges)
        log.append('[I] foo', log.ALL)
        log.append('[E] bar', log.ALL)
        log.flush()
        self.assertFalse(new.hasChanges)
        log.append('[C] baz', log.ALL)
        log.flush()
        self.assertTrue(new.hasChanges)

class TestRootSnapshot(generic.SnapshotsTestCase):
    #TODO: add test with 'sid.path(use_mode=['ssh_encfs'])'
    def test_create(self):
        sid = snapshots.RootSnapshot(self.cfg)
        self.assertTrue(sid.isRoot)
        self.assertEqual(sid.sid, '/')
        self.assertEqual(sid.name, 'Now')

    def test_path(self):
        sid = snapshots.RootSnapshot(self.cfg)
        self.assertEqual(sid.path(), '/')
        self.assertEqual(sid.path('foo', 'bar'), '/foo/bar')

class TestIterSnapshots(generic.SnapshotsTestCase):
    def setUp(self):
        super(TestIterSnapshots, self).setUp()

        for i in ('20151219-010324-123',
                  '20151219-020324-123',
                  '20151219-030324-123',
                  '20151219-040324-123'):
            os.makedirs(os.path.join(self.snapshotPath, i, 'backup'))

    def test_list_valid(self):
        l1 = snapshots.listSnapshots(self.cfg)
        self.assertListEqual(l1, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])
        self.assertIsInstance(l1[0], snapshots.SID)

    def test_list_new_snapshot(self):
        os.makedirs(os.path.join(self.snapshotPath, 'new_snapshot', 'backup'))
        l2 = snapshots.listSnapshots(self.cfg, includeNewSnapshot = True)
        self.assertListEqual(l2, ['new_snapshot',
                                  '20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])
        self.assertIsInstance(l2[0], snapshots.NewSnapshot)
        self.assertIsInstance(l2[-1], snapshots.SID)

    def test_list_snapshot_without_backup(self):
        #new snapshot without backup folder shouldn't be added
        os.makedirs(os.path.join(self.snapshotPath, '20151219-050324-123'))
        l3 = snapshots.listSnapshots(self.cfg)
        self.assertListEqual(l3, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])

    def test_list_invalid_snapshot(self):
        #invalid snapshot shouldn't be added
        os.makedirs(os.path.join(self.snapshotPath,
                                 '20151219-000324-abc',
                                 'backup'))
        l4 = snapshots.listSnapshots(self.cfg)
        self.assertListEqual(l4, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])

    def test_list_without_new_snapshot(self):
        os.makedirs(os.path.join(self.snapshotPath, 'new_snapshot', 'backup'))
        l5 = snapshots.listSnapshots(self.cfg, includeNewSnapshot = False)
        self.assertListEqual(l5, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])

    def test_list_symlink_last_snapshot(self):
        os.symlink('./20151219-040324-123',
                   os.path.join(self.snapshotPath, 'last_snapshot'))
        l6 = snapshots.listSnapshots(self.cfg)
        self.assertListEqual(l6, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])

    def test_list_not_reverse(self):
        os.makedirs(os.path.join(self.snapshotPath, 'new_snapshot', 'backup'))
        l7 = snapshots.listSnapshots(self.cfg,
                                     includeNewSnapshot = True,
                                     reverse = False)
        self.assertListEqual(l7, ['20151219-010324-123',
                                  '20151219-020324-123',
                                  '20151219-030324-123',
                                  '20151219-040324-123',
                                  'new_snapshot'])
        self.assertIsInstance(l7[0], snapshots.SID)
        self.assertIsInstance(l7[-1], snapshots.NewSnapshot)

    def test_iter_snapshots(self):
        for i, sid in enumerate(snapshots.iterSnapshots(self.cfg)):
            self.assertIn(sid, ['20151219-040324-123',
                                '20151219-030324-123',
                                '20151219-020324-123',
                                '20151219-010324-123'])
            self.assertIsInstance(sid, snapshots.SID)
        self.assertEqual(i, 3)

    def test_lastSnapshot(self):
        self.assertEqual(snapshots.lastSnapshot(self.cfg),
                         '20151219-040324-123')

class TestIterSnapshotsNonexistingSnapshotPath(generic.TestCaseSnapshotPath):
    def test_iterSnapshots(self):
        for item in snapshots.iterSnapshots(self.cfg):
            self.fail('got unexpected snapshot')

    def test_listSnapshots(self):
        self.assertEqual(snapshots.listSnapshots(self.cfg), [])

    def test_lastSnapshots(self):
        self.assertIsNone(snapshots.lastSnapshot(self.cfg))

if __name__ == '__main__':
    unittest.main()
