# Back In Time
# Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
# You should have received a copy of the GNU General Public Licensealong
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys
import tempfile
import unittest
import shutil
import stat
import pwd
import grp
from datetime import date, datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import config
import configfile
import snapshots
import logger


class TestSnapshots(unittest.TestCase):
    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.cfg = config.Config(os.path.abspath(os.path.join(__file__, os.pardir, 'config')))
        self.sn = snapshots.Snapshots(self.cfg)
        self.snapshotPath = self.cfg.get_snapshots_full_path()
        if os.path.exists(self.snapshotPath):
            self.tearDown()
        os.makedirs(self.snapshotPath)

    def tearDown(self):
        shutil.rmtree(self.snapshotPath)

    ############################################################################
    ###                              get_uid                                 ###
    ############################################################################
    def test_get_uid_valid(self):
        self.assertEqual(self.sn.get_uid(b'root'), 0)

        currentUID = os.geteuid()
        currentUser = pwd.getpwuid(currentUID).pw_name.encode()
        self.assertEqual(self.sn.get_uid(currentUser), currentUID)

    def test_get_uid_invalid(self):
        self.assertEqual(self.sn.get_uid(b'nonExistingUser'), -1)

    def test_get_uid_backup(self):
        self.assertEqual(self.sn.get_uid(b'root', backup = 99999), 0)
        self.assertEqual(self.sn.get_uid(b'nonExistingUser', backup = 99999), 99999)

        currentUID = os.geteuid()
        currentUser = pwd.getpwuid(currentUID).pw_name.encode()
        self.assertEqual(self.sn.get_uid(currentUser,  backup = 99999), currentUID)

    ############################################################################
    ###                              get_gid                                 ###
    ############################################################################
    def test_get_gid_valid(self):
        self.assertEqual(self.sn.get_gid(b'root'), 0)

        currentGID = os.getegid()
        currentGroup = grp.getgrgid(currentGID).gr_name.encode()
        self.assertEqual(self.sn.get_gid(currentGroup), currentGID)

    def test_get_gid_invalid(self):
        self.assertEqual(self.sn.get_gid(b'nonExistingGroup'), -1)

    def test_get_gid_backup(self):
        self.assertEqual(self.sn.get_gid(b'root', backup = 99999), 0)
        self.assertEqual(self.sn.get_gid(b'nonExistingGroup', backup = 99999), 99999)

        currentGID = os.getegid()
        currentGroup = grp.getgrgid(currentGID).gr_name.encode()
        self.assertEqual(self.sn.get_gid(currentGroup,  backup = 99999), currentGID)

    ############################################################################
    ###                          get_user_name                               ###
    ############################################################################
    def test_get_user_name_valid(self):
        self.assertEqual(self.sn.get_user_name(0), 'root')

        currentUID = os.geteuid()
        currentUser = pwd.getpwuid(currentUID).pw_name
        self.assertEqual(self.sn.get_user_name(currentUID), currentUser)

    def test_get_user_name_invalid(self):
        self.assertEqual(self.sn.get_user_name(99999), '-')

    ############################################################################
    ###                         get_group_name                               ###
    ############################################################################
    def test_get_group_name_valid(self):
        self.assertEqual(self.sn.get_group_name(0), 'root')

        currentGID = os.getegid()
        currentGroup = grp.getgrgid(currentGID).gr_name
        self.assertEqual(self.sn.get_group_name(currentGID), currentGroup)

    def test_get_group_name_invalid(self):
        self.assertEqual(self.sn.get_group_name(99999), '-')

    ############################################################################
    ###                   rsync Ex-/Include and suffix                       ###
    ############################################################################
    def test_rsyncExclude_unique_items(self):
        exclude = self.sn.rsyncExclude(['/foo', '*bar', '/baz/1'])
        self.assertEqual(exclude, '--exclude="/foo" --exclude="*bar" --exclude="/baz/1"')

    def test_rsyncExclude_duplicate_items(self):
        exclude = self.sn.rsyncExclude(['/foo', '*bar', '/baz/1', '/foo', '/baz/1'])
        self.assertEqual(exclude, '--exclude="/foo" --exclude="*bar" --exclude="/baz/1"')

    def test_rsyncInclude_unique_items(self):
        i1, i2 = self.sn.rsyncInclude([('/foo', 0),
                                       ('/bar', 1),
                                       ('/baz/1/2', 1)])
        self.assertEqual(i1, '--include="/foo/" --include="/baz/1/" --include="/baz/"')
        self.assertEqual(i2, '--include="/foo/**" --include="/bar" --include="/baz/1/2"')

    def test_rsyncInclude_duplicate_items(self):
        i1, i2 = self.sn.rsyncInclude([('/foo', 0),
                                       ('/bar', 1),
                                       ('/foo', 0),
                                       ('/baz/1/2', 1),
                                       ('/baz/1/2', 1)])
        self.assertEqual(i1, '--include="/foo/" --include="/baz/1/" --include="/baz/"')
        self.assertEqual(i2, '--include="/foo/**" --include="/bar" --include="/baz/1/2"')

    def test_rsyncInclude_root(self):
        i1, i2 = self.sn.rsyncInclude([('/', 0), ])
        self.assertEqual(i1, '')
        self.assertEqual(i2, '--include="/" --include="/**"')

    def test_rsyncSuffix(self):
        suffix = self.sn.rsyncSuffix(includeFolders = [('/foo', 0),
                                                       ('/bar', 1),
                                                       ('/baz/1/2', 1)],
                                     excludeFolders = ['/foo/bar',
                                                       '*blub',
                                                       '/bar/2'])
        self.assertRegex(suffix, r' --chmod=Du\+wx  ' +
                                 r'--exclude="/tmp/snapshots" ' +
                                 r'--exclude=".*?\.local/share/backintime" ' +
                                 r'--exclude="\.local/share/backintime/mnt" ' +
                                 r'--include="/foo/" '      +
                                 r'--include="/baz/1/" '    +
                                 r'--include="/baz/" '      +
                                 r'--exclude="/foo/bar" '   +
                                 r'--exclude="\*blub" '     +
                                 r'--exclude="/bar/2" '     +
                                 r'--include="/foo/\*\*" '  +
                                 r'--include="/bar" '       +
                                 r'--include="/baz/1/2" '   +
                                 r'--exclude="\*" / ')

class TestSID(unittest.TestCase):
    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.cfg = config.Config(os.path.abspath(os.path.join(__file__, os.pardir, 'config')))
        self.snapshotPath = self.cfg.get_snapshots_full_path()
        if os.path.exists(self.snapshotPath):
            self.tearDown()
        os.makedirs(self.snapshotPath)

    def tearDown(self):
        shutil.rmtree(self.snapshotPath)

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

    def test_split(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertTupleEqual(sid.split(), (2015, 12, 19, 1, 3, 24))

    def test_displayID(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.displayID(), '2015-12-19 01:03:24')

    def test_displayName(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        with open(sid.path('name'), 'wt') as f:
            f.write('foo')

        self.assertEqual(sid.displayName(), '2015-12-19 01:03:24 - foo')

        with open(sid.path('failed'), 'wt') as f:
            pass

        self.assertRegex(sid.displayName(), r'2015-12-19 01:03:24 - foo (.+?)')

    def test_withoutTag(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.withoutTag(), '20151219-010324')

    def test_tag(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.assertEqual(sid.tag(), '123')

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

        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123', 'backup'))
        self.assertTrue(sid.exists())

    def test_canOpenPath(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        backupPath = os.path.join(self.snapshotPath, '20151219-010324-123', 'backup')
        os.makedirs(os.path.join(backupPath, 'foo'))

        #test existing file and non existing file
        self.assertTrue(sid.canOpenPath('/foo'))
        self.assertFalse(sid.canOpenPath('/tmp'))

        #test valid absolut symlink inside snapshot
        os.symlink(os.path.join(backupPath, 'foo'),
                   os.path.join(backupPath, 'bar'))
        self.assertTrue(os.path.islink(os.path.join(backupPath, 'bar')))
        self.assertTrue(sid.canOpenPath('/bar'))

        #test valid relativ symlink inside snapshot
        os.symlink('./foo',
                   os.path.join(backupPath, 'baz'))
        self.assertTrue(os.path.islink(os.path.join(backupPath, 'baz')))
        self.assertTrue(sid.canOpenPath('/baz'))

        #test invalid symlink
        os.symlink(os.path.join(backupPath, 'asdf'),
                   os.path.join(backupPath, 'qwer'))
        self.assertTrue(os.path.islink(os.path.join(backupPath, 'qwer')))
        self.assertFalse(sid.canOpenPath('/qwer'))

        #test valid symlink outside snapshot
        os.symlink('/tmp',
                   os.path.join(backupPath, 'bla'))
        self.assertTrue(os.path.islink(os.path.join(backupPath, 'bla')))
        self.assertFalse(sid.canOpenPath('/bla'))

    def test_name(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        self.assertEqual(sid.name(), '')

        sid.setName('foo')
        with open(sid.path('name'), 'rt') as f:
            self.assertEqual(f.read(), 'foo')

        self.assertEqual(sid.name(), 'foo')

    def test_lastChecked(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'info')

        #no info file
        self.assertEqual(sid.lastChecked(), '2015-12-19 01:03:24')

        #set time manually to 2015-12-19 02:03:24
        with open(infoFile, 'wt'):
            pass
        d = datetime(2015, 12, 19, 2, 3, 24)
        os.utime(infoFile, (d.timestamp(), d.timestamp()))
        self.assertEqual(sid.lastChecked(), '2015-12-19 02:03:24')

        #setLastChecked and check if it matches current date
        sid.setLastChecked()
        now = datetime.now()
        self.assertRegex(sid.lastChecked(), now.strftime(r'%Y-%m-%d %H:%M:\d{2}'))

    def test_failed(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))

        self.assertFalse(sid.failed())
        sid.setFailed()
        self.assertTrue(sid.failed())

    def test_info(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'info')

        sid1.info.set_str_value('foo', 'bar')
        sid1.saveInfo()

        #test if file exist and has correct content
        self.assertTrue(os.path.isfile(infoFile))
        with open(infoFile, 'rt') as f:
            self.assertEqual(f.read(), 'foo=bar\n')

        #new sid instance and test if default value is returned
        sid2 = snapshots.SID('20151219-010324-123', self.cfg)
        self.assertEqual(sid2.info.get_str_value('foo', 'default'), 'default')

        #load info and test if correct value is returned
        sid2.loadInfo()
        self.assertEqual(sid2.info.get_str_value('foo', 'default'), 'bar')

    def test_fileInfo(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'fileinfo.bz2')

        sid1.fileInfoDict['/tmp'] = (123, 'foo', 'bar')
        sid1.fileInfoDict['/tmp/foo'] = (456, 'asdf', 'qwer')
        sid1.saveFileInfo()

        self.assertTrue(os.path.isfile(infoFile))

        sid2 = snapshots.SID('20151219-010324-123', self.cfg)
        self.assertDictEqual(sid2.fileInfoDict, {})

        #load fileInfo
        d = sid2.fileInfo()
        self.assertDictEqual(d, {'/tmp':     (123, 'foo', 'bar'),
                                 '/tmp/foo': (456, 'asdf', 'qwer')})

        #reload again but without force it shouldn't overwrite local
        sid2.fileInfoDict['/tmp/bar'] = (789, 'bla', 'blub')
        d = sid2.fileInfo()
        self.assertDictEqual(d, {'/tmp':     (123, 'foo', 'bar'),
                                 '/tmp/foo': (456, 'asdf', 'qwer'),
                                 '/tmp/bar': (789, 'bla', 'blub')})

        #force reload
        d = sid2.fileInfo(force = True)
        self.assertDictEqual(d, {'/tmp':     (123, 'foo', 'bar'),
                                 '/tmp/foo': (456, 'asdf', 'qwer')})

    def test_log(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'takesnapshot.log.bz2')

        #no log available
        self.assertRegex(sid.log(), r'Failed to get snapshot log from.*')

        sid.setLog('foo bar\nbaz')
        self.assertTrue(os.path.isfile(logFile))

        self.assertEqual(sid.log(), 'foo bar\nbaz')

    def test_setLog_binary(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'takesnapshot.log.bz2')

        sid.setLog(b'foo bar\nbaz')
        self.assertTrue(os.path.isfile(logFile))

        self.assertEqual(sid.log(), 'foo bar\nbaz')

    def test_makeWriteable(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        sidPath = os.path.join(self.snapshotPath, '20151219-010324-123')
        testFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'test')

        #make only read and exploreable
        os.chmod(sidPath, stat.S_IRUSR | stat.S_IXUSR)
        with self.assertRaises(PermissionError):
            with open(testFile, 'wt') as f:
                f.write('foo')

        sid.makeWriteable()

        self.assertEqual(os.stat(sidPath).st_mode & stat.S_IWUSR, stat.S_IWUSR)
        try:
            with open(testFile, 'wt') as f:
                f.write('foo')
        except PermissionError:
            self.fail('writing to %s raised PermissionError unexpectedly!' %testFile)

class TestNewSnapshot(unittest.TestCase):
    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.cfg = config.Config(os.path.abspath(os.path.join(__file__, os.pardir, 'config')))
        self.snapshotPath = self.cfg.get_snapshots_full_path()
        if os.path.exists(self.snapshotPath):
            self.tearDown()
        os.makedirs(self.snapshotPath)

    def tearDown(self):
        shutil.rmtree(self.snapshotPath)

    def test_create_new(self):
        new = snapshots.NewSnapshot(self.cfg)
        self.assertFalse(new.exists())

        self.assertTrue(new.makeDirs())
        self.assertTrue(new.exists())
        self.assertTrue(os.path.isdir(os.path.join(self.snapshotPath, 'new_snapshot', 'backup')))

    def test_saveToContinue(self):
        new = snapshots.NewSnapshot(self.cfg)
        self.assertTrue(new.makeDirs())
        self.assertFalse(new.saveToContinue())

        new.setSaveToContinue()
        self.assertTrue(new.saveToContinue())

        new.unsetSaveToContinue()
        self.assertFalse(new.saveToContinue())

class TestIterSnapshots(unittest.TestCase):
    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.cfg = config.Config(os.path.abspath(os.path.join(__file__, os.pardir, 'config')))
        self.snapshotPath = self.cfg.get_snapshots_full_path()
        if os.path.exists(self.snapshotPath):
            self.tearDown()
        os.makedirs(self.snapshotPath)

        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123', 'backup'))
        os.makedirs(os.path.join(self.snapshotPath, '20151219-020324-123', 'backup'))
        os.makedirs(os.path.join(self.snapshotPath, '20151219-030324-123', 'backup'))
        os.makedirs(os.path.join(self.snapshotPath, '20151219-040324-123', 'backup'))

    def tearDown(self):
        shutil.rmtree(self.snapshotPath)

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
        #new snapshot without backup folder should't be added
        os.makedirs(os.path.join(self.snapshotPath, '20151219-050324-123'))
        l3 = snapshots.listSnapshots(self.cfg)
        self.assertListEqual(l3, ['20151219-040324-123',
                                  '20151219-030324-123',
                                  '20151219-020324-123',
                                  '20151219-010324-123'])

    def test_list_invalid_snapshot(self):
        #invalid snapshot shouldn't be added
        os.makedirs(os.path.join(self.snapshotPath, '20151219-000324-abc', 'backup'))
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
        l7 = snapshots.listSnapshots(self.cfg, includeNewSnapshot = True, reverse = False)
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
        self.assertEqual(snapshots.lastSnapshot(self.cfg), '20151219-040324-123')

if __name__ == '__main__':
    unittest.main()
