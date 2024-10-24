# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
import pathlib
import shutil
import stat
import grp
import re
import random
import string
import unittest
from unittest.mock import patch
from datetime import date, datetime
from tempfile import TemporaryDirectory
from test import generic
from test.constants import CURRENTUSER, CURRENTGROUP, CURRENTGID, CURRENTUID

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logger
import config
import snapshots
import tools
import mount


# all groups the current user is member in
GROUPS = [i.gr_name for i in grp.getgrall() if CURRENTUSER in i.gr_mem]


class SetTakeSnapshotMessage(generic.SnapshotsTestCase):
    def test_info(self):
        self.sn.setTakeSnapshotMessage(0, 'first message')
        self.sn.snapshotLog.flush()

        # test NotifyPlugin
        self.mockNotifyPlugin.assert_called_once_with(self.sn.config.currentProfile(),
                                                      self.sn.config.profileName(),
                                                      0,
                                                      'first message',
                                                      -1)
        self.assertExists(self.sn.config.takeSnapshotMessageFile())
        # test message file
        with open(self.sn.config.takeSnapshotMessageFile(), 'rt') as f:
            message = f.read()
        self.assertEqual(message, '0\nfirst message')
        # test snapshot log
        self.assertEqual('\n'.join(self.sn.snapshotLog.get()), '[I] first message')

    def test_error(self):
        self.sn.setTakeSnapshotMessage(1, 'second message')
        self.sn.snapshotLog.flush()

        # test NotifyPlugin
        self.mockNotifyPlugin.assert_called_once_with(self.sn.config.currentProfile(),
                                                      self.sn.config.profileName(),
                                                      1,
                                                      'second message',
                                                      -1)
        # test message file
        self.assertExists(self.sn.config.takeSnapshotMessageFile())
        with open(self.sn.config.takeSnapshotMessageFile(), 'rt') as f:
            message = f.read()
        self.assertEqual(message, '1\nsecond message')
        # test snapshot log
        self.assertEqual('\n'.join(self.sn.snapshotLog.get()), '[E] second message')


class UserAndGroups(generic.SnapshotsTestCase):
    def test_uid_valid(self):
        self.assertEqual(self.sn.uid('root'), 0)
        self.assertEqual(self.sn.uid(b'root'), 0)

        self.assertEqual(self.sn.uid(CURRENTUSER), CURRENTUID)
        self.assertEqual(self.sn.uid(CURRENTUSER.encode()), CURRENTUID)

    def test_uid_invalid(self):
        self.assertEqual(self.sn.uid('nonExistingUser'), -1)
        self.assertEqual(self.sn.uid(b'nonExistingUser'), -1)

    def test_uid_backup(self):
        self.assertEqual(self.sn.uid('root', backup = 99999), 0)
        self.assertEqual(self.sn.uid(b'root', backup = 99999), 0)
        self.assertEqual(self.sn.uid('nonExistingUser', backup = 99999), 99999)
        self.assertEqual(self.sn.uid(b'nonExistingUser', backup = 99999), 99999)

        self.assertEqual(self.sn.uid(CURRENTUSER,  backup = 99999), CURRENTUID)
        self.assertEqual(self.sn.uid(CURRENTUSER.encode(),  backup = 99999), CURRENTUID)

    def test_gid_valid(self):
        self.assertEqual(self.sn.gid('root'), 0)
        self.assertEqual(self.sn.gid(b'root'), 0)

        self.assertEqual(self.sn.gid(CURRENTGROUP), CURRENTGID)
        self.assertEqual(self.sn.gid(CURRENTGROUP.encode()), CURRENTGID)

    def test_gid_invalid(self):
        self.assertEqual(self.sn.gid('nonExistingGroup'), -1)
        self.assertEqual(self.sn.gid(b'nonExistingGroup'), -1)

    def test_gid_backup(self):
        self.assertEqual(self.sn.gid('root', backup = 99999), 0)
        self.assertEqual(self.sn.gid(b'root', backup = 99999), 0)
        self.assertEqual(self.sn.gid('nonExistingGroup', backup = 99999), 99999)
        self.assertEqual(self.sn.gid(b'nonExistingGroup', backup = 99999), 99999)

        self.assertEqual(self.sn.gid(CURRENTGROUP,  backup = 99999), CURRENTGID)
        self.assertEqual(self.sn.gid(CURRENTGROUP.encode(),  backup = 99999), CURRENTGID)

    def test_username_valid(self):
        self.assertEqual(self.sn.userName(0), 'root')

        self.assertEqual(self.sn.userName(CURRENTUID), CURRENTUSER)

    def test_username_invalid(self):
        self.assertEqual(self.sn.userName(99999), '-')

    def test_groupname_valid(self):
        self.assertEqual(self.sn.groupName(0), 'root')

        self.assertEqual(self.sn.groupName(CURRENTGID), CURRENTGROUP)

    def test_groupname_invalid(self):
        self.assertEqual(self.sn.groupName(99999), '-')


class HelperScripts(generic.SnapshotsTestCase):
    def test_rsync_remote_path(self):
        self.assertEqual(self.sn.rsyncRemotePath('/foo'),
                         '/foo')
        # "quote" is ignored because the "mode" isn't ssh or ssh_encfs
        self.assertEqual(self.sn.rsyncRemotePath('/foo', quote = '\\\"'),
                         '/foo')
        self.assertEqual(self.sn.rsyncRemotePath('/foo', use_mode = ['local']),
                         '/foo')

        # The same as above.
        self.assertEqual(self.sn.rsyncRemotePath('/foo', use_mode = ['local'], quote = '\\\"'),
                         '/foo')

        #set up SSH profile
        self.cfg.setSnapshotsMode('ssh')
        self.cfg.setSshHost('localhost')
        self.cfg.setSshUser('foo')
        self.assertEqual(self.sn.rsyncRemotePath('/bar'),
                         'foo@localhost:"/bar"')
        self.assertEqual(self.sn.rsyncRemotePath('/bar', quote = '\\\"'),
                         'foo@localhost:\\\"/bar\\\"')

        self.assertEqual(self.sn.rsyncRemotePath('/bar', use_mode = []),
                         '/bar')

    def test_create_last_snapshot_symlink(self):
        sid1 = snapshots.SID('20151219-010324-123', self.cfg)
        sid1.makeDirs()
        symlink = self.cfg.lastSnapshotSymlink()
        self.assertNotExists(symlink)

        self.assertTrue(self.sn.createLastSnapshotSymlink(sid1))
        self.assertIsLink(symlink)
        self.assertEqual(os.path.realpath(symlink), sid1.path())

        sid2 = snapshots.SID('20151219-020324-123', self.cfg)
        sid2.makeDirs()
        self.assertTrue(self.sn.createLastSnapshotSymlink(sid2))
        self.assertIsLink(symlink)
        self.assertEqual(os.path.realpath(symlink), sid2.path())

    def test_stat_free_space_local(self):
        self.assertIsInstance(self.sn.statFreeSpaceLocal('/'), int)

    @patch('time.sleep') # speed up unittest
    def test_make_dirs(self, sleep):
        self.assertFalse(self.sn.makeDirs('/'))
        self.assertTrue(self.sn.makeDirs(os.getcwd()))
        with TemporaryDirectory() as d:
            path = os.path.join(d, 'foo', 'bar')
            self.assertTrue(self.sn.makeDirs(path))


class RsyncExcludeIncludeSuffix(generic.SnapshotsTestCase):
    def test_exclude_unique_items(self):
        exclude = self.sn.rsyncExclude(['/foo', '*bar', '/baz/1'])
        self.assertListEqual(list(exclude), ['--exclude=/foo',
                                             '--exclude=*bar',
                                             '--exclude=/baz/1'])

    def test_include_unique_items(self):
        i1, i2 = self.sn.rsyncInclude([('/foo', 0),
                                       ('/bar', 1),
                                       ('/baz/1/2', 1)])
        self.assertListEqual(list(i1), ['--include=/foo/',
                                        '--include=/baz/1/',
                                        '--include=/baz/'])
        self.assertListEqual(list(i2), ['--include=/foo/**',
                                        '--include=/bar',
                                        '--include=/baz/1/2'])

    def test_include_root(self):
        i1, i2 = self.sn.rsyncInclude([('/', 0), ])
        self.assertListEqual(list(i1), [])
        self.assertListEqual(list(i2), ['--include=/',
                                        '--include=/**'])

    def test_rsync_suffix(self):
        suffix = self.sn.rsyncSuffix(includeFolders = [('/foo', 0),
                                                       ('/bar', 1),
                                                       ('/baz/1/2', 1)],
                                     excludeFolders = ['/foo/bar',
                                                       '*blub',
                                                       '/bar/2'])
        self.assertIsInstance(suffix, list)
        self.assertRegex(' '.join(suffix), r'^--chmod=Du\+wx '      +
                                           r'--exclude=/tmp/.*? '   +
                                           r'--exclude=.*?\.local/share/backintime '  +
                                           r'--exclude=\.local/share/backintime/mnt ' +
                                           r'--include=/foo/ '      +
                                           r'--include=/baz/1/ '    +
                                           r'--include=/baz/ '      +
                                           r'--exclude=/foo/bar '   +
                                           r'--exclude=\*blub '     +
                                           r'--exclude=/bar/2 '     +
                                           r'--include=/foo/\*\* '  +
                                           r'--include=/bar '       +
                                           r'--include=/baz/1/2 '   +
                                           r'--exclude=\* /$')


class Callbacks(generic.SnapshotsTestCase):
    def test_restore(self):
        msg = 'foo'
        callback = lambda x: self.callback(self.assertEqual, x, msg)
        self.sn.restoreCallback(callback, True, msg)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restorePermissionFailed)

        self.run = False
        callback = lambda x: self.callback(self.assertRegex, x, r'{} : \w+'.format(msg))
        self.sn.restoreCallback(callback, False, msg)
        self.assertTrue(self.run)
        self.assertTrue(self.sn.restorePermissionFailed)

    def test_callback(self):
        params = [False, False]

        self.sn.rsyncCallback('foo', params)
        self.assertListEqual([False, False], params)
        with open(self.cfg.takeSnapshotMessageFile(), 'rt') as f:
            self.assertEqual('0\nTake snapshot (rsync: foo)', f.read())
        self.sn.snapshotLog.flush()
        with open(self.cfg.takeSnapshotLogFile(), 'rt') as f:
            self.assertEqual('[I] Take snapshot (rsync: foo)\n', f.read())

    def test_keep_params(self):
        params = [True, True]

        self.sn.rsyncCallback('foo', params)
        self.assertListEqual([True, True], params)

    def test_transfer(self):
        params = [False, False]

        self.sn.rsyncCallback('BACKINTIME: <f+++++++++ /foo/bar', params)
        self.assertListEqual([False, True], params)
        with open(self.cfg.takeSnapshotMessageFile(), 'rt') as f:
            self.assertEqual('0\nTake snapshot (rsync: BACKINTIME: <f+++++++++ /foo/bar)', f.read())
        self.sn.snapshotLog.flush()
        with open(self.cfg.takeSnapshotLogFile(), 'rt') as f:
            self.assertEqual('[I] Take snapshot (rsync: BACKINTIME: <f+++++++++ /foo/bar)\n[C] <f+++++++++ /foo/bar\n', f.read())

    def test_dir(self):
        params = [False, False]

        self.sn.rsyncCallback('BACKINTIME: cd..t...... /foo/bar', params)
        self.assertListEqual([False, False], params)
        with open(self.cfg.takeSnapshotMessageFile(), 'rt') as f:
            self.assertEqual('0\nTake snapshot (rsync: BACKINTIME: cd..t...... /foo/bar)', f.read())
        self.sn.snapshotLog.flush()
        with open(self.cfg.takeSnapshotLogFile(), 'rt') as f:
            self.assertEqual('[I] Take snapshot (rsync: BACKINTIME: cd..t...... /foo/bar)\n', f.read())

    def test_error(self):
        params = [False, False]

        self.sn.rsyncCallback('rsync: send_files failed to open "/foo/bar": Operation not permitted (1)', params)
        self.assertListEqual([True, False], params)
        with open(self.cfg.takeSnapshotMessageFile(), 'rt') as f:
            self.assertEqual('1\nError: rsync: send_files failed to open "/foo/bar": Operation not permitted (1)', f.read())
        self.sn.snapshotLog.flush()
        with open(self.cfg.takeSnapshotLogFile(), 'rt') as f:
            self.assertEqual('[I] Take snapshot (rsync: rsync: send_files failed to open "/foo/bar": Operation not permitted (1))\n' \
                             '[E] Error: rsync: send_files failed to open "/foo/bar": Operation not permitted (1)\n', f.read())


class SmartRemove(generic.SnapshotsTestCase):
    def test_increment_month(self):
        self.assertEqual(self.sn.incMonth(date(2016,  4, 21)), date(2016, 5, 1))
        self.assertEqual(self.sn.incMonth(date(2016, 12, 24)), date(2017, 1, 1))

    def test_decrement_month(self):
        self.assertEqual(self.sn.decMonth(date(2016, 4, 21)), date(2016,  3, 1))
        self.assertEqual(self.sn.decMonth(date(2016, 1, 14)), date(2015, 12, 1))

    def test_keep_all(self):
        sid1 = snapshots.SID('20160424-215134-123', self.cfg)
        sid2 = snapshots.SID('20160422-030324-123', self.cfg)
        sid3 = snapshots.SID('20160422-020324-123', self.cfg)
        sid4 = snapshots.SID('20160422-010324-123', self.cfg)
        sid5 = snapshots.SID('20160421-013218-123', self.cfg)
        sid6 = snapshots.SID('20160410-134327-123', self.cfg)
        sids = [sid1, sid2, sid3, sid4, sid5, sid6]

        keep = self.sn.smartRemoveKeepAll(sids,
                                               date(2016, 4, 20),
                                               date(2016, 4, 23))
        self.assertSetEqual(keep, set((sid2, sid3, sid4, sid5)))

        keep = self.sn.smartRemoveKeepAll(sids,
                                               date(2016, 4, 11),
                                               date(2016, 4, 18))
        self.assertSetEqual(keep, set())

    def test_keep_first(self):
        sid1 = snapshots.SID('20160424-215134-123', self.cfg)
        sid2 = snapshots.SID('20160422-030324-123', self.cfg)
        sid3 = snapshots.SID('20160422-020324-123', self.cfg)
        sid4 = snapshots.SID('20160422-010324-123', self.cfg)
        sid5 = snapshots.SID('20160421-013218-123', self.cfg)
        sid6 = snapshots.SID('20160410-134327-123', self.cfg)
        sids = [sid1, sid2, sid3, sid4, sid5, sid6]

        keep = self.sn.smartRemoveKeepFirst(sids,
                                            date(2016, 4, 20),
                                            date(2016, 4, 23))
        self.assertSetEqual(keep, set((sid2,)))

        keep = self.sn.smartRemoveKeepFirst(sids,
                                            date(2016, 4, 11),
                                            date(2016, 4, 18))
        self.assertSetEqual(keep, set())

    def test_keep_first_no_errors(self):
        sid1 = snapshots.SID('20160424-215134-123', self.cfg)
        sid2 = snapshots.SID('20160422-030324-123', self.cfg)
        sid2.makeDirs()
        sid2.failed = True
        sid3 = snapshots.SID('20160422-020324-123', self.cfg)
        sid4 = snapshots.SID('20160422-010324-123', self.cfg)
        sid5 = snapshots.SID('20160421-013218-123', self.cfg)
        sid6 = snapshots.SID('20160410-134327-123', self.cfg)
        sids = [sid1, sid2, sid3, sid4, sid5, sid6]

        # keep the first healthy snapshot
        keep = self.sn.smartRemoveKeepFirst(sids,
                                            date(2016, 4, 20),
                                            date(2016, 4, 23),
                                            keep_healthy = True)
        self.assertSetEqual(keep, set((sid3,)))

        # if all snapshots failed, keep the first at all
        for sid in (sid3, sid4, sid5):
            sid.makeDirs()
            sid.failed = True
        keep = self.sn.smartRemoveKeepFirst(sids,
                                            date(2016, 4, 20),
                                            date(2016, 4, 23),
                                            keep_healthy = True)
        self.assertSetEqual(keep, set((sid2,)))

    def test_smart_remove_list(self):
        sid1  = snapshots.SID('20160424-215134-123', self.cfg)
        sid2  = snapshots.SID('20160422-030324-123', self.cfg)
        sid3  = snapshots.SID('20160422-020324-123', self.cfg)
        sid4  = snapshots.SID('20160422-010324-123', self.cfg)
        sid5  = snapshots.SID('20160421-033218-123', self.cfg)
        sid6  = snapshots.SID('20160421-013218-123', self.cfg)
        sid7  = snapshots.SID('20160420-013218-123', self.cfg)
        sid8  = snapshots.SID('20160419-013218-123', self.cfg)
        sid9  = snapshots.SID('20160419-003218-123', self.cfg)
        sid10 = snapshots.SID('20160418-003218-123', self.cfg)
        sid11 = snapshots.SID('20160417-033218-123', self.cfg)
        sid12 = snapshots.SID('20160417-003218-123', self.cfg)
        sid13 = snapshots.SID('20160416-134327-123', self.cfg)
        sid14 = snapshots.SID('20160416-114327-123', self.cfg)
        sid15 = snapshots.SID('20160415-134327-123', self.cfg)
        sid16 = snapshots.SID('20160411-134327-123', self.cfg)
        sid17 = snapshots.SID('20160410-134327-123', self.cfg)
        sid18 = snapshots.SID('20160409-134327-123', self.cfg)
        sid19 = snapshots.SID('20160407-134327-123', self.cfg)
        sid20 = snapshots.SID('20160403-134327-123', self.cfg)
        sid21 = snapshots.SID('20160402-134327-123', self.cfg)
        sid22 = snapshots.SID('20160401-134327-123', self.cfg)
        sid23 = snapshots.SID('20160331-134327-123', self.cfg)
        sid24 = snapshots.SID('20160330-134327-123', self.cfg)
        sid25 = snapshots.SID('20160323-133715-123', self.cfg)
        sid26 = snapshots.SID('20160214-134327-123', self.cfg)
        sid27 = snapshots.SID('20160205-134327-123', self.cfg)
        sid28 = snapshots.SID('20160109-134327-123', self.cfg)
        sid29 = snapshots.SID('20151224-134327-123', self.cfg)
        sid30 = snapshots.SID('20150904-134327-123', self.cfg)
        sid31 = snapshots.SID('20140904-134327-123', self.cfg)

        sids = [       sid1,  sid2,  sid3,  sid4,  sid5,  sid6,  sid7,  sid8,  sid9,
                sid10, sid11, sid12, sid13, sid14, sid15, sid16, sid17, sid18, sid19,
                sid20, sid21, sid22, sid23, sid24, sid25, sid26, sid27, sid28, sid29,
                sid30, sid31]
        for sid in sids:
            sid.makeDirs()
        now = datetime(2016, 4, 24, 21, 51, 34)

        del_snapshots = self.sn.smartRemoveList(now,
                                                3, #keep_all
                                                7, #keep_one_per_day
                                                5, #keep_one_per_week
                                                3  #keep_one_per_month
                                                )
        self.assertListEqual(del_snapshots, [sid6, sid9, sid12, sid13, sid14,
                                             sid15, sid16, sid18, sid19, sid21,
                                             sid22, sid24, sid27, sid28, sid30])

        # test failed snapshots
        for sid in (sid5, sid8, sid11, sid12, sid20, sid21, sid22):
            sid.failed = True
        del_snapshots = self.sn.smartRemoveList(now,
                                                3, #keep_all
                                                7, #keep_one_per_day
                                                5, #keep_one_per_week
                                                3  #keep_one_per_month
                                                )
        self.assertListEqual(del_snapshots, [sid5, sid8, sid11, sid12, sid14,
                                             sid15, sid16, sid18, sid19, sid20, sid21,
                                             sid22, sid24, sid27, sid28, sid30])


class SnapshotWithSID(generic.SnapshotsWithSidTestCase):
    def test_backup_config(self):
        self.sn.backupConfig(self.sid)
        self.assertIsFile(self.sid.path('config'))
        self.assertEqual(tools.md5sum(self.sid.path('config')),
                         tools.md5sum(self.cfgFile))

    def test_backup_info_file(self):
        """Creation and content of the 'info' file contained in each snapshot
        """

        # Create the file
        self.sn._backup_info_file(self.sid)
        sut_fp = pathlib.Path(self.sid.path('info'))

        self.assertTrue(sut_fp.is_file())

        sut = sut_fp.read_text()
        self.assertRegex(sut, re.compile('''group.size=.+
snapshot_date=20151219-010324
snapshot_machine=.+
snapshot_profile_id=1
snapshot_tag=123
snapshot_user=.+
user.size=.+''', re.MULTILINE))

    def test_backup_permissions(self):
        #TODO: add test for save permissions over SSH (and one SSH-test for path with spaces)
        infoFilePath = os.path.join(self.snapshotPath,
                                    '20151219-010324-123',
                                    'fileinfo.bz2')

        include = self.cfg.include()[0][0]
        with TemporaryDirectory(dir = include) as tmp:

            file_path = os.path.join(tmp, 'foo')
            with open(file_path, 'wt') as f:
                f.write('bar')
                f.flush()

            self.sid.makeDirs(tmp)
            with open(self.sid.pathBackup(file_path), 'wt') as snapshot_f:
                snapshot_f.write('bar')
                snapshot_f.flush()

            self.sn.backupPermissions(self.sid)

            fileInfo = self.sid.fileInfo
            self.assertIsFile(infoFilePath)
            self.assertIn(include.encode(), fileInfo)
            self.assertIn(tmp.encode(), fileInfo)
            self.assertIn(file_path.encode(), fileInfo)

    def test_collect_permission(self):
        # force permissions because different distributions will have different umask
        os.chmod(self.testDirFullPath, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
        os.chmod(self.testFileFullPath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)

        d = snapshots.FileInfoDict()
        testDir  = self.testDirFullPath.encode()
        testFile = self.testFileFullPath.encode()
        self.sn.collectPermission(d, testDir)
        self.sn.collectPermission(d, testFile)

        self.assertIn(testDir, d)
        self.assertIn(testFile, d)
        self.assertTupleEqual(d[testDir],  (16893, CURRENTUSER.encode(), CURRENTGROUP.encode()))
        self.assertTupleEqual(d[testFile], (33204, CURRENTUSER.encode(), CURRENTGROUP.encode()))


class RestorePathInfo(generic.SnapshotsTestCase):
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

        super(RestorePathInfo, self).setUp()

    def tearDown(self):
        super(RestorePathInfo, self).tearDown()
        if os.path.exists(self.pathFolder):
            shutil.rmtree(self.pathFolder)
        if os.path.exists(self.pathFile):
            os.remove(self.pathFile)

    def test_no_changes(self):
        d = snapshots.FileInfoDict()
        d[b'foo'] = (self.modeFolder, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))
        d[b'bar'] = (self.modeFile, CURRENTUSER.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.fail,
                             'callback function was called unexpectedly')
        self.sn.restorePermission(b'foo', b'/tmp/test/foo', d, callback)
        self.sn.restorePermission(b'bar', b'/tmp/test/bar', d, callback)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, self.modeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, self.modeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

    def test_change_owner_without_root(self):
        d = snapshots.FileInfoDict()
        d[b'foo'] = (self.modeFolder, 'root'.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))
        d[b'bar'] = (self.modeFile, 'root'.encode('utf-8','replace'), CURRENTGROUP.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.assertRegex, x,
                             r'^chown /tmp/test/(?:foo|bar) 0 : {} : \w+$'.format(CURRENTGID))

        self.sn.restorePermission(b'foo', b'/tmp/test/foo', d, callback)
        self.assertTrue(self.run)
        self.assertTrue(self.sn.restorePermissionFailed)
        self.run, self.sn.restorePermissionFailed = False, False
        self.sn.restorePermission(b'bar', b'/tmp/test/bar', d, callback)
        self.assertTrue(self.run)
        self.assertTrue(self.sn.restorePermissionFailed)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, self.modeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, self.modeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

    @unittest.skipIf(len(GROUPS) < 2,
                     'Current user must be a mamber of more than one group.')
    def test_change_group(self):
        newGroup = [x for x in GROUPS if x != CURRENTGROUP][0]
        newGID = grp.getgrnam(newGroup).gr_gid
        d = snapshots.FileInfoDict()
        d[b'foo'] = (self.modeFolder, CURRENTUSER.encode('utf-8','replace'), newGroup.encode('utf-8','replace'))
        d[b'bar'] = (self.modeFile, CURRENTUSER.encode('utf-8','replace'), newGroup.encode('utf-8','replace'))

        callback = lambda x: self.callback(self.assertRegex, x,
                             r'^chgrp /tmp/test/(?:foo|bar) {}$'.format(newGID))

        self.sn.restorePermission(b'foo', b'/tmp/test/foo', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restorePermissionFailed)
        self.run = False
        self.sn.restorePermission(b'bar', b'/tmp/test/bar', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restorePermissionFailed)

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
        self.sn.restorePermission(b'foo', b'/tmp/test/foo', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restorePermissionFailed)
        self.run = False
        self.sn.restorePermission(b'bar', b'/tmp/test/bar', d, callback)
        self.assertTrue(self.run)
        self.assertFalse(self.sn.restorePermissionFailed)

        s = os.stat(self.pathFolder)
        self.assertEqual(s.st_mode, newModeFolder)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)

        s = os.stat(self.pathFile)
        self.assertEqual(s.st_mode, newModeFile)
        self.assertEqual(s.st_uid, CURRENTUID)
        self.assertEqual(s.st_gid, CURRENTGID)


class DeletePath(generic.SnapshotsWithSidTestCase):
    def test_file(self):
        self.assertExists(self.testFileFullPath)
        self.sn.deletePath(self.sid, self.testFile)
        self.assertNotExists(self.testFileFullPath)

    def test_file_readonly(self):
        os.chmod(self.testFileFullPath, stat.S_IRUSR)
        self.sn.deletePath(self.sid, self.testFile)
        self.assertNotExists(self.testFileFullPath)

    def test_dir(self):
        self.assertExists(self.testDirFullPath)
        self.sn.deletePath(self.sid, self.testDir)
        self.assertNotExists(self.testDirFullPath)

    def test_dir_readonly(self):
        os.chmod(self.testFileFullPath, stat.S_IRUSR)
        os.chmod(self.testDirFullPath, stat.S_IRUSR | stat.S_IXUSR)
        self.sn.deletePath(self.sid, self.testDir)
        self.assertNotExists(self.testDirFullPath)

    def test_pardir_readonly(self):
        os.chmod(self.testFileFullPath, stat.S_IRUSR)
        os.chmod(self.testDirFullPath, stat.S_IRUSR | stat.S_IXUSR)
        self.sn.deletePath(self.sid, 'foo')
        self.assertNotExists(self.testDirFullPath)


class RemoveSnapshot(generic.SnapshotsWithSidTestCase):
    """Integration test about removing a snapshot."""

    def test_remove(self):

        self.assertTrue(self.sid.exists())
        self.sn.remove(self.sid)
        self.assertFalse(self.sid.exists())

    def test_remove_read_only(self):
        for path in (self.sid.pathBackup(), self.testDirFullPath):
            os.chmod(path, stat.S_IRUSR | stat.S_IXUSR)
        os.chmod(self.testFileFullPath, stat.S_IRUSR)

        self.assertTrue(self.sid.exists())
        self.sn.remove(self.sid)
        self.assertFalse(self.sid.exists())


@unittest.skipIf(not generic.LOCAL_SSH, generic.SKIP_SSH_TEST_MESSAGE)
class SshSnapshots(generic.SSHTestCase):
    def setUp(self):
        super().setUp()
        self.sn = snapshots.Snapshots(self.cfg)
        os.makedirs(self.remoteFullPath)

    def test_stat_free_space_ssh(self):
        self.assertIsInstance(self.sn.statFreeSpaceSsh(), int)


def _rand_string(self, max_length=10, min_length=1):
    """Create a string with random uppercase characters and digits and
    a random length between `min_length` and `max_length`.

    Args:
        max_length (int): Max length of the string (default: 10).
        min_length (int): Min string length (default: 1)

    Returns:
        (string): The created random string.
    """
    return ''.join(random.choices(
        string.ascii_uppercase+string.digits,
        k=random.randint(min_length, max_length)
    ))


def _create_selfdestructing_path(test_case, path):
    """Create a path that removes itself after the test.

    Args:
        test_case (unittest.TestCase): Test instance used to call
                                       `addCleanup()`.
        path (str, pathlib.Path): Path or its name to create.

    Returns:
        (pathlib.Path): The created path object.
    """
    p = pathlib.Path(path)
    p.mkdir()

    test_case.addCleanup(lambda: shutil.rmtree(p))

    return p


def _init_basic_config(data_dir_prefix='DATADIR', data_dir_suffix=''):
    """Prepare configuration for a test.

    Args:
        data_dir_prefix (str): Prefix of the temporary data directory.
        data_dir_suffix (str): Suffix of the temporary data directory.

    Returns:
        config.Config: The configuriation object.

    It is a helper function to setup an environment for integration and unit
    tests.

    What it does:

        - Prepare the logging.
        - Read the config (for tests) and instanticate a
          :py:class:`config.Config` object.
        - Creates a (temporary) "data" directory as specified by
          `XDG_DATA_HOME`.
        - Loading the plugin manager.

    The "data" directory is a ``TemporaryDirectory()`` instance. It is alive
    as long as the returned configuration objects is alive because it is
    attached to it as a member.
    """

    # Initialize logging
    logger.APP_NAME = 'BIT_unittest'
    logger.openlog()
    logger.DEBUG = '-v' in sys.argv

    # Path to config file (in "common/test/config")
    config_path = pathlib.Path(__file__).parent / 'config'

    # data path
    # e.g. /tmp/l9pxsfh2
    # Used for
    # e.g. /tmp/lpxsfh2/.local/share/backintime/mnt/83B5CA1B/mountpoin
    data_dir = TemporaryDirectory(prefix=data_dir_prefix,
                                  suffix=data_dir_suffix)

    # BUHTZ 2022-10-19 Because of unusual importing of "config.Config" we
    # can not use the variable name "config".
    # Fix this in the future when migrated to source layout.
    # The "Config" class should be imported explicate or should be named
    # with its full package path. e.g. "backintime.config.Config()".

    # config instance
    cfg = config.Config(
        config_path=str(config_path),
        data_path=data_dir.name
    )

    # keep the (temporary) data dir alive
    cfg._tmp_data_dir = data_dir

    # ?
    cfg.PLUGIN_MANAGER.load()

    return cfg


def _init_source_path(cfg,
                      source_dir_prefix='SOURCEDIR',
                      source_dir_suffix=''):
    """Prepare the (backup) source directory but keep it empty.

    Args:
        cfg (config.Config): The configuration instance.
        source_dir_prefix (str): Prefix of the (temporary) source directory.
        source_dir_suffix (str): Suffix of the (temporary) source directory.

    It is a helper function to setup an environment for integration and unit
    tests. The term "source directory" means the directory that is to be
    backed up.

    What it does:
        - Create a (temporary) directory as backup source.
        - Add it as an include folder to the profile configuration.
    """
    source_dir = TemporaryDirectory(prefix=source_dir_prefix,
                                    suffix=source_dir_suffix)

    # set it as include folder
    cfg.setInclude([(source_dir.name, 0)])

    # keep the (temporary) dir alive
    cfg._tmp_source_dir = source_dir


def _init_ssh_profile(cfg,
                      destination_dir_prefix='DESTINATIONDIRparent',
                      destination_dir_suffix=''):
    """Setup a "SSH local" snapshots profile and it's snapshots folder.

    Args:
        cfg (config.Config): The configuration instance.
        destination_dir_prefix (str): Prefix of the (temporary) destination
                                      directory.
        destination_dir_suffix (str): Suffix of the (temporary) destination
                                      directory.

    Returns:
        snapshots.Snapshots: The instance representing the "SSH local" profile.

    It is a helper function to setup an environment for integration and unit
    tests. The term "snapshots folder" is synonmy with the "destination
    directory" means the directory where the backed up files are stored.

    What it does:
        - Modify the configuration to a "SSH local" profile.
        - Create a (temporary) directory as the parent(!) of the snapshots
          folder.
        - Create the snapshots folder (aka "backup destination") with name
          `foo` in it.
        - Return a :py:class:`snapshots.Snapshots` instance.

    """
    # configure a SSH snapshot profile
    cfg.setSnapshotsMode('ssh')
    cfg.setSshHost('localhost')
    cfg.setSshPrivateKeyFile(generic.PRIV_KEY_FILE)

    # use a TemporaryDirectory for remote snapshot path
    # e.g. /tmp/tmp_mzi0qqo/foo
    remote_dir_parent = TemporaryDirectory(prefix=destination_dir_prefix,
                                           suffix=destination_dir_suffix)
    remote_path = pathlib.Path(remote_dir_parent.name) / 'foo'

    # keep dir alive
    cfg._tmp_remote_dir_parent = remote_dir_parent

    # set remote snapshot path to config
    cfg.setSshSnapshotsPath(str(remote_path))

    # Create a full snapshot profile paths
    # e.g. /tmp/tmp_mzi0qqo/foo/backintime/test-host/test-user/1
    snapshots_path = pathlib.Path(cfg.sshSnapshotsFullPath())

    snapshots_path.mkdir(parents=True)

    # use a tmp-file for flock because test_flockExclusive would deadlock
    # otherwise if a regular snapshot is running in background
    snapshots.Snapshots.GLOBAL_FLOCK = generic.TMP_FLOCK.name

    # The snapshot instance
    return snapshots.Snapshots(cfg)


def _init_concrete_snapshot(cfg, sid_name='20151219-010324-123'):
    """Create a SID instance which is a snapshot on a specific timepoint.

    Args:
        cfg (config.Config): The configuration instance.
        sid_name (str): The name of the snapshot.

    Returns:
        snapshots.SID: The SID instance.

    It is a helper function to setup an environment or integration and unit
    tests. The term "SID" means a snapshot that was taken on a specific point
    in time. It could be described as the resulting files of one run of a
    backup job.

    What that function does:
        - Create the SID instance.
        - Create the the full directory tree for that SID.
        - Create files and folders (via
          :py:func:`generic.create_test_files()`) in it.
    """
    # +++ Create a concrete snapshot (SID)
    sid = snapshots.SID(sid_name, cfg)

    # e.g. /tmp/DESTINATIONDIRparent89h5l0f9/foo/backintime/ \
    # test-host/test-user/1/20151219-010324-123/backup
    sid_path = pathlib.Path(cfg.sshSnapshotsFullPath()) / sid.sid / 'backup'

    # The source path should be reflected in the destination snapshot.
    # It means the folder structure (including the parent folders) of the
    # backup source are mirrored into the backup destination.
    # e.g. /tmp/tmpq8cbewug/foo/backintime/test-host/test-user/1/
    # 20151219-010324-123/backup/tmp/xyz
    sid_path = sid_path / cfg.include()[0][0][1:]
    sid_path.mkdir(parents=True)

    generic.create_test_files(str(sid_path))

    return sid


def _init_mounting(cfg):
    """Handle the mounting for integration and unittesting.

    Args:
        cfg (config.Config): The configuration instance.

    Returns:
        mount.Mount: The mount object.

    Development note (BUHTZ 2022-10-22): I didn't understand all details here.
    But it seems to be necessary.

    Unmounting is not done automatically! It is recommended to use
    ``unittest.TestCase.addCleanup()`` for that::

        class MyTest(unittest.TestCase):
            def test_mytest(self):
                # cfg = ...
                mount_obj = _init_mounting(cfg)
                self.addCleanup(lambda: mount_obj.umount(cfg.current_hash_id))
    """
    # mount
    mount_obj = mount.Mount(cfg=cfg)

    hash_id = mount_obj.mount()  # e.g. FA3E732E

    # ?
    cfg.setCurrentHashId(hash_id)

    return mount_obj


@unittest.skipIf(not generic.LOCAL_SSH, generic.SKIP_SSH_TEST_MESSAGE)
class SshPermissions(unittest.TestCase):
    """Testing to backup the file permissions in a "SSH local"
    snapshot profile.
    """

    def test_backup_permissions(self):
        """Backup file permissions in SSH backup mode."""

        # --- prepare environment ---

        # config instance
        cfg = _init_basic_config()
        # snapshots profile
        snapshot = _init_ssh_profile(cfg)
        # backup source directory
        _init_source_path(cfg)
        # simulate a taken snapshot
        sid = _init_concrete_snapshot(cfg)

        # BUHTZ 2022-10-21: The mounting is needed but I didn't understand
        # all details yet.
        # mount
        mount_obj = _init_mounting(cfg)
        # ...unmount when test finished
        self.addCleanup(lambda: mount_obj.umount(cfg.current_hash_id))

        # --- prepare the backup source ---

        # Does the concrete snapshot exists?
        self.assertTrue(sid.exists())

        # The backup source path
        # e.g. /tmp/e2uij3y
        source_path = pathlib.Path(cfg.include()[0][0])
        # ...exists?
        self.assertTrue(source_path.exists())

        # create the test files in the backup source directory
        generic.create_test_files(str(source_path))

        # --- Do the job to test. ---

        # backup permissions of files/folders in the backup source
        rc = snapshot.backupPermissions(sid)

        self.assertEqual(rc, 0, 'rsync return code')

        # --- Validate the job. ---

        # resulted permissions
        fileInfo = sid.fileInfo

        # source path in the fileInfo present?
        self.assertIn(str(source_path).encode(), fileInfo)

        # expected field where the permissions are stored in
        # e.g. /tmp/BITa6ekd80lTEST/foo/backintime/test-host/test-user/1
        infoFilePath = pathlib.Path(cfg.snapshotsFullPath())
        # ...'/20151219-010324-123/fileinfo.bz2'
        infoFilePath = infoFilePath / str(sid.sid) / 'fileinfo.bz2'

        # Does it exists as a file?
        self.assertTrue(infoFilePath.exists())
        self.assertTrue(infoFilePath.is_file())


@unittest.skipIf(not generic.LOCAL_SSH, generic.SKIP_SSH_TEST_MESSAGE)
class SshRemoveSnapshots(unittest.TestCase):
    """Testing to remove snapshots(SID) in a "SSH local" snapshot profile.
    """

    def test_remove(self):
        """Remove concrete snapshot.

        Here there is no blank in the path name.
        """
        self._generic_test_remove(path_suffix='')

    def test_remove_with_blank(self):
        """Remove concrete snapshot with blank in path name.
        """
        self._generic_test_remove(path_suffix=' with blank')

    def _generic_test_remove(self, path_suffix):
        """
        """
        cfg = _init_basic_config()
        snapshot = _init_ssh_profile(cfg)
        sid = _init_concrete_snapshot(cfg)

        # mount
        mount_obj = _init_mounting(cfg)
        # ...unmount when test finished
        self.addCleanup(lambda: mount_obj.umount(cfg.current_hash_id))

        # Does the snapshot exists?
        self.assertTrue(sid.exists())

        # Remove it
        self.assertTrue(snapshot.remove(sid))

        # Shouldn't exist anymore.
        self.assertFalse(sid.exists())
