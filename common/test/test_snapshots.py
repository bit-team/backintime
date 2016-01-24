# Back In Time
# Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
from threading import Thread
from tempfile import TemporaryDirectory, NamedTemporaryFile
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import config
import configfile
import snapshots
import logger

CURRENTUID = os.geteuid()
CURRENTUSER = pwd.getpwuid(CURRENTUID).pw_name

CURRENTGID = os.getegid()
CURRENTGROUP = grp.getgrgid(CURRENTGID).gr_name

#all groups the current user is member in
GROUPS = [i.gr_name for i in grp.getgrall() if CURRENTUSER in i.gr_mem]
NO_GROUPS = not GROUPS

IS_ROOT = os.geteuid() == 0

TMP_FLOCK = NamedTemporaryFile()

class GenericSnapshotsTestCase(unittest.TestCase):
    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.cfgFile = os.path.abspath(os.path.join(__file__,
                                                    os.pardir,
                                                    'config'))
        self.cfg = config.Config(self.cfgFile)
        #use a new TemporaryDirectory for snapshotPath to avoid
        #side effects on leftovers
        self.tmpDir = TemporaryDirectory()
        self.cfg.dict['profile1.snapshots.path'] = self.tmpDir.name
        self.snapshotPath = self.cfg.get_snapshots_full_path()
        os.makedirs(self.snapshotPath)

    def tearDown(self):
        self.tmpDir.cleanup()

class TestSnapshots(GenericSnapshotsTestCase):
    def setUp(self):
        super(TestSnapshots, self).setUp()
        self.sn = snapshots.Snapshots(self.cfg)
        #use a tmp-file for flock because test_flockExclusive would deadlock
        #otherwise if a regular snapshot is running in background
        self.sn.GLOBAL_FLOCK = TMP_FLOCK.name

    ############################################################################
    ###                              get_uid                                 ###
    ############################################################################
    def test_get_uid_valid(self):
        self.assertEqual(self.sn.get_uid('root'), 0)
        self.assertEqual(self.sn.get_uid(b'root'), 0)

        self.assertEqual(self.sn.get_uid(CURRENTUSER), CURRENTUID)
        self.assertEqual(self.sn.get_uid(CURRENTUSER.encode()), CURRENTUID)

    def test_get_uid_invalid(self):
        self.assertEqual(self.sn.get_uid('nonExistingUser'), -1)
        self.assertEqual(self.sn.get_uid(b'nonExistingUser'), -1)

    def test_get_uid_backup(self):
        self.assertEqual(self.sn.get_uid('root', backup = 99999), 0)
        self.assertEqual(self.sn.get_uid(b'root', backup = 99999), 0)
        self.assertEqual(self.sn.get_uid('nonExistingUser', backup = 99999), 99999)
        self.assertEqual(self.sn.get_uid(b'nonExistingUser', backup = 99999), 99999)

        self.assertEqual(self.sn.get_uid(CURRENTUSER,  backup = 99999), CURRENTUID)
        self.assertEqual(self.sn.get_uid(CURRENTUSER.encode(),  backup = 99999), CURRENTUID)

    ############################################################################
    ###                              get_gid                                 ###
    ############################################################################
    def test_get_gid_valid(self):
        self.assertEqual(self.sn.get_gid('root'), 0)
        self.assertEqual(self.sn.get_gid(b'root'), 0)

        self.assertEqual(self.sn.get_gid(CURRENTGROUP), CURRENTGID)
        self.assertEqual(self.sn.get_gid(CURRENTGROUP.encode()), CURRENTGID)

    def test_get_gid_invalid(self):
        self.assertEqual(self.sn.get_gid('nonExistingGroup'), -1)
        self.assertEqual(self.sn.get_gid(b'nonExistingGroup'), -1)

    def test_get_gid_backup(self):
        self.assertEqual(self.sn.get_gid('root', backup = 99999), 0)
        self.assertEqual(self.sn.get_gid(b'root', backup = 99999), 0)
        self.assertEqual(self.sn.get_gid('nonExistingGroup', backup = 99999), 99999)
        self.assertEqual(self.sn.get_gid(b'nonExistingGroup', backup = 99999), 99999)

        self.assertEqual(self.sn.get_gid(CURRENTGROUP,  backup = 99999), CURRENTGID)
        self.assertEqual(self.sn.get_gid(CURRENTGROUP.encode(),  backup = 99999), CURRENTGID)

    ############################################################################
    ###                          get_user_name                               ###
    ############################################################################
    def test_get_user_name_valid(self):
        self.assertEqual(self.sn.get_user_name(0), 'root')

        self.assertEqual(self.sn.get_user_name(CURRENTUID), CURRENTUSER)

    def test_get_user_name_invalid(self):
        self.assertEqual(self.sn.get_user_name(99999), '-')

    ############################################################################
    ###                         get_group_name                               ###
    ############################################################################
    def test_get_group_name_valid(self):
        self.assertEqual(self.sn.get_group_name(0), 'root')

        self.assertEqual(self.sn.get_group_name(CURRENTGID), CURRENTGROUP)

    def test_get_group_name_invalid(self):
        self.assertEqual(self.sn.get_group_name(99999), '-')

    ############################################################################
    ###                                                                      ###
    ############################################################################
    def test_rsync_remote_path(self):
        self.assertEqual(self.sn.rsync_remote_path('/foo'),
                         '"/foo"')
        self.assertEqual(self.sn.rsync_remote_path('/foo', use_modes = ['local']),
                         '"/foo"')

        #set up SSH profile
        self.cfg.set_snapshots_mode('ssh')
        self.cfg.set_ssh_host('localhost')
        self.cfg.set_ssh_user('foo')
        self.assertEqual(self.sn.rsync_remote_path('/bar'),
                         '\'foo@localhost:"/bar"\'')

        self.assertEqual(self.sn.rsync_remote_path('/bar', use_modes = []),
                         '"/bar"')

    def test_create_last_snapshot_symlink(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        sid1.makeDirs()
        symlink = self.cfg.get_last_snapshot_symlink()
        self.assertFalse(os.path.exists(symlink))

        self.assertTrue(self.sn.create_last_snapshot_symlink(sid1))
        self.assertTrue(os.path.islink(symlink))
        self.assertEqual(os.path.realpath(symlink), sid1.path())

        sid2 = snapshots.SID('20151219-020324-123', self.cfg)
        sid2.makeDirs()
        self.assertTrue(self.sn.create_last_snapshot_symlink(sid2))
        self.assertTrue(os.path.islink(symlink))
        self.assertEqual(os.path.realpath(symlink), sid2.path())

    def flockSecondInstance(self):
        cfgFile = os.path.abspath(os.path.join(__file__, os.pardir, 'config'))
        cfg = config.Config(cfgFile)
        sn = snapshots.Snapshots(cfg)
        sn.GLOBAL_FLOCK = TMP_FLOCK.name

        cfg.set_use_global_flock(True)
        sn.flockExclusive()
        sn.flockRelease()

    def test_flockExclusive(self):
        RWUGO = 33206 #-rw-rw-rw
        self.cfg.set_use_global_flock(True)
        thread = Thread(target = self.flockSecondInstance, args = ())
        self.sn.flockExclusive()

        self.assertTrue(os.path.exists(self.sn.GLOBAL_FLOCK))
        mode = os.stat(self.sn.GLOBAL_FLOCK).st_mode
        self.assertEqual(mode, RWUGO)

        thread.start()
        thread.join(0.01)
        self.assertTrue(thread.is_alive())

        self.sn.flockRelease()
        thread.join()
        self.assertFalse(thread.is_alive())

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
        self.assertRegex(suffix, r'^ --chmod=Du\+wx  ' +
                                 r'--exclude="/tmp/.*?" ' +
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
                                 r'--exclude="\*" / $')

class TestRestore(GenericSnapshotsTestCase):
    def setUp(self):
        super(TestRestore, self).setUp()
        self.sn = snapshots.Snapshots(self.cfg)
        self.run = False

    def callback(self, func, *args):
        func(*args)
        self.run = True

    def test_callback(self):
        msg = 'foo'
        callback = lambda x: self.callback(self.assertEqual, x, msg)
        self.sn.restore_callback(callback, True, msg)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)

        self.run = False
        callback = lambda x: self.callback(self.assertRegex, x, r'{} : \w+'.format(msg))
        self.sn.restore_callback(callback, False, msg)
        self.assertTrue(self.run)
        self.assertTrue(self.sn.restore_permission_failed)

class TestRestorePathInfo(GenericSnapshotsTestCase):
    def setUp(self):
        self.pathFolder = '/tmp/test/foo'
        self.pathFile   = '/tmp/test/bar'
        if os.path.exists(self.pathFolder):
            shutil.rmtree(self.pathFolder)
        if os.path.exists(self.pathFile):
            os.remove(self.pathFile)
        os.makedirs(self.pathFolder)
        with open(self.pathFile, 'wt') as f:
            pass

        self.modeFolder = os.stat(self.pathFolder).st_mode
        self.modeFile   = os.stat(self.pathFile).st_mode

        super(TestRestorePathInfo, self).setUp()
        self.sn = snapshots.Snapshots(self.cfg)
        self.run = False

    def tearDown(self):
        super(TestRestorePathInfo, self).tearDown()
        if os.path.exists(self.pathFolder):
            shutil.rmtree(self.pathFolder)
        if os.path.exists(self.pathFile):
            os.remove(self.pathFile)

    def callback(self, func, *args):
        func(*args)
        self.run = True

    def test_no_changes(self):
        d = snapshots.FileInfoDict()
        d[b'foo'] = (self.modeFolder, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))
        d[b'bar'] = (self.modeFile, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.fail,
                             'callback function was called unexpectedly')
        self.sn._restore_path_info(b'foo', b'/tmp/test/foo', d, callback)
        self.sn._restore_path_info(b'bar', b'/tmp/test/bar', d, callback)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, self.modeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, self.modeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

    #TODO: add fakeroot tests with https://github.com/yaybu/fakechroot
    @unittest.skipIf(IS_ROOT, "We're running as root. So this test won't work.")
    def test_change_owner_without_root(self):
        d = snapshots.FileInfoDict()
        d[b'foo'] = (self.modeFolder, 'root'.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))
        d[b'bar'] = (self.modeFile, 'root'.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.assertRegex, x,
                             r'^chown /tmp/test/(?:foo|bar) 0 : {} : \w+$'.format(CURRENTGID))

        self.sn._restore_path_info(b'foo', b'/tmp/test/foo', d, callback)
        self.assertTrue(self.run)
        self.assertTrue(self.sn.restore_permission_failed)
        self.run, self.sn.restore_permission_failed = False, False
        self.sn._restore_path_info(b'bar', b'/tmp/test/bar', d, callback)
        self.assertTrue(self.run)
        self.assertTrue(self.sn.restore_permission_failed)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, self.modeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, self.modeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

    @unittest.skipIf(NO_GROUPS, "Current user is in no other group. So this test won't work.")
    def test_change_group(self):
        newGroup = GROUPS[0]
        newGID = grp.getgrnam(newGroup).gr_gid
        d = snapshots.FileInfoDict()
        d[b'foo'] = (self.modeFolder, CURRENTUSER.encode('utf-8','replace'), newGroup.encode('utf-8','replace'))
        d[b'bar'] = (self.modeFile, CURRENTUSER.encode('utf-8','replace'), newGroup.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.assertRegex, x,
                             r'^chgrp /tmp/test/(?:foo|bar) {}$'.format(newGID))

        self.sn._restore_path_info(b'foo', b'/tmp/test/foo', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)
        self.run = False
        self.sn._restore_path_info(b'bar', b'/tmp/test/bar', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, self.modeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, newGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, self.modeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, newGID)

    def test_change_permissions(self):
        newModeFolder = 16832 #rwx------
        newModeFile   = 33152 #rw-------
        d = snapshots.FileInfoDict()
        d[b'foo'] = (newModeFolder, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))
        d[b'bar'] = (newModeFile, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.assertRegex, x,
                             r'^chmod /tmp/test/(?:foo|bar) \d+$')
        self.sn._restore_path_info(b'foo', b'/tmp/test/foo', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)
        self.run = False
        self.sn._restore_path_info(b'bar', b'/tmp/test/bar', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restore_permission_failed)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, newModeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, newModeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

class TestDelete(GenericSnapshotsTestCase):
    def setUp(self):
        super(TestDelete, self).setUp()
        self.sn = snapshots.Snapshots(self.cfg)
        self.sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.sid.makeDirs()
        self.testDir = 'foo/bar'
        self.testDirFullPath = self.sid.pathBackup(self.testDir)
        self.testFile = 'foo/bar/baz'
        self.testFileFullPath = self.sid.pathBackup(self.testFile)

        self.sid.makeDirs(self.testDir)
        with open(self.sid.pathBackup(self.testFile), 'wt') as f:
            pass

    def test_delete_file(self):
        self.assertTrue(os.path.exists(self.testFileFullPath))
        self.sn.delete_path(self.sid, self.testFile)
        self.assertFalse(os.path.exists(self.testFileFullPath))

    def test_delete_file_readonly(self):
        os.chmod(self.testFileFullPath, stat.S_IRUSR)
        self.sn.delete_path(self.sid, self.testFile)
        self.assertFalse(os.path.exists(self.testFileFullPath))

    def test_delete_dir(self):
        self.assertTrue(os.path.exists(self.testDirFullPath))
        self.sn.delete_path(self.sid, self.testDir)
        self.assertFalse(os.path.exists(self.testDirFullPath))

    def test_delete_dir_readonly(self):
        os.chmod(self.testFileFullPath, stat.S_IRUSR)
        os.chmod(self.testDirFullPath, stat.S_IRUSR | stat.S_IXUSR)
        self.sn.delete_path(self.sid, self.testDir)
        self.assertFalse(os.path.exists(self.testDirFullPath))

    def test_delete_pardir_readonly(self):
        os.chmod(self.testFileFullPath, stat.S_IRUSR)
        os.chmod(self.testDirFullPath, stat.S_IRUSR | stat.S_IXUSR)
        self.sn.delete_path(self.sid, 'foo')
        self.assertFalse(os.path.exists(self.testDirFullPath))

class TestSID(GenericSnapshotsTestCase):
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

    def test_canOpenPath(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        backupPath = os.path.join(self.snapshotPath,
                                  '20151219-010324-123',
                                  'backup')
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

        self.assertFalse(os.path.exists(failedPath))
        self.assertFalse(sid.failed)
        sid.failed = True
        self.assertTrue(os.path.exists(failedPath))
        self.assertTrue(sid.failed)

        sid.failed = False
        self.assertFalse(os.path.exists(failedPath))
        self.assertFalse(sid.failed)

    def test_info(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        infoFile = os.path.join(self.snapshotPath, '20151219-010324-123', 'info')

        i1 = configfile.ConfigFile()
        i1.set_str_value('foo', 'bar')
        sid1.info = i1

        #test if file exist and has correct content
        self.assertTrue(os.path.isfile(infoFile))
        with open(infoFile, 'rt') as f:
            self.assertEqual(f.read(), 'foo=bar\n')

        #new sid instance and test if correct value is returned
        sid2 = snapshots.SID('20151219-010324-123', self.cfg)
        i2 = sid2.info
        self.assertEqual(i2.get_str_value('foo', 'default'), 'bar')

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

        self.assertTrue(os.path.isfile(infoFile))

        #load fileInfo in a new snapshot
        sid2 = snapshots.SID('20151219-010324-123', self.cfg)        
        self.assertDictEqual(sid2.fileInfo, d)

    def test_log(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath,
                               '20151219-010324-123',
                               'takesnapshot.log.bz2')

        #no log available
        self.assertRegex(sid.log(), r'Failed to get snapshot log from.*')

        sid.setLog('foo bar\nbaz')
        self.assertTrue(os.path.isfile(logFile))

        self.assertEqual(sid.log(), 'foo bar\nbaz')

    def test_setLog_binary(self):
        sid = snapshots.SID('20151219-010324-123', self.cfg)
        os.makedirs(os.path.join(self.snapshotPath, '20151219-010324-123'))
        logFile = os.path.join(self.snapshotPath,
                               '20151219-010324-123',
                               'takesnapshot.log.bz2')

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
            msg = 'writing to {} raised PermissionError unexpectedly!'
            self.fail(msg.format(testFile))

class TestNewSnapshot(GenericSnapshotsTestCase):
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

        self.assertFalse(os.path.exists(saveToContinuePath))
        self.assertFalse(new.saveToContinue)

        new.saveToContinue = True
        self.assertTrue(os.path.exists(saveToContinuePath))
        self.assertTrue(new.saveToContinue)

        new.saveToContinue = False
        self.assertFalse(os.path.exists(saveToContinuePath))
        self.assertFalse(new.saveToContinue)

class TestIterSnapshots(GenericSnapshotsTestCase):
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
        #new snapshot without backup folder should't be added
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

if __name__ == '__main__':
    unittest.main()
