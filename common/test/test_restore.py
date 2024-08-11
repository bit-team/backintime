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
import pwd
import grp
import stat
from tempfile import TemporaryDirectory
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import mount

CURRENTUID = os.geteuid()
CURRENTUSER = pwd.getpwuid(CURRENTUID).pw_name

CURRENTGID = os.getegid()
CURRENTGROUP = grp.getgrgid(CURRENTGID).gr_name

class RestoreTestCase(generic.SnapshotsWithSidTestCase):
    def setUp(self):
        super(RestoreTestCase, self).setUp()
        self.include = TemporaryDirectory()
        generic.create_test_files(self.sid.pathBackup(self.include.name))

    def tearDown(self):
        super(RestoreTestCase, self).tearDown()
        self.include.cleanup()

    def prepairFileInfo(self, restoreFile, mode = 33260):
        d = self.sid.fileInfo
        d[restoreFile.encode('utf-8', 'replace')] = (mode,
                                                     CURRENTUSER.encode('utf-8', 'replace'),
                                                     CURRENTGROUP.encode('utf-8', 'replace'))
        self.sid.fileInfo = d

class TestRestore(RestoreTestCase):
    def test_restore_multiple_files(self):
        restoreFile1 = os.path.join(self.include.name, 'test')
        self.prepairFileInfo(restoreFile1)
        restoreFile2 = os.path.join(self.include.name, 'foo', 'bar', 'baz')
        self.prepairFileInfo(restoreFile2)

        self.sn.restore(self.sid, (restoreFile1, restoreFile2))
        self.assertIsFile(restoreFile1)
        with open(restoreFile1, 'rt') as f:
            self.assertEqual(f.read(), 'bar')
        self.assertEqual(33260, os.stat(restoreFile1).st_mode)

        self.assertIsFile(restoreFile2)
        with open(restoreFile2, 'rt') as f:
            self.assertEqual(f.read(), 'foo')
        self.assertEqual(33260, os.stat(restoreFile2).st_mode)

    def test_restore_to_different_destination(self):
        restoreFile = os.path.join(self.include.name, 'test')
        self.prepairFileInfo(restoreFile)
        with TemporaryDirectory() as dest:
            destRestoreFile = os.path.join(dest, 'test')
            self.sn.restore(self.sid, restoreFile, restore_to = dest)
            self.assertIsFile(destRestoreFile)
            with open(destRestoreFile, 'rt') as f:
                self.assertEqual(f.read(), 'bar')
            self.assertEqual(33260, os.stat(destRestoreFile).st_mode)

    def test_restore_folder_to_different_destination(self):
        restoreFolder = self.include.name
        self.prepairFileInfo(restoreFolder)
        self.prepairFileInfo(os.path.join(restoreFolder, 'test'))
        self.prepairFileInfo(os.path.join(restoreFolder, 'file with spaces'))

        with TemporaryDirectory() as dest:
            destRestoreFile = os.path.join(dest, os.path.basename(restoreFolder), 'test')
            self.sn.restore(self.sid, restoreFolder, restore_to = dest)
            self.assertIsFile(destRestoreFile)
            with open(destRestoreFile, 'rt') as f:
                self.assertEqual(f.read(), 'bar')
            self.assertEqual(33260, os.stat(destRestoreFile).st_mode)

    def test_delete(self):
        restoreFolder = self.include.name
        junkFolder = os.path.join(self.include.name, 'junk')
        os.makedirs(junkFolder)
        self.assertExists(junkFolder)
        self.prepairFileInfo(restoreFolder)

        self.sn.restore(self.sid, restoreFolder, delete = True)
        self.assertIsFile(restoreFolder, 'test')
        self.assertNotExists(junkFolder)

    def test_backup(self):
        restoreFile = os.path.join(self.include.name, 'test')
        self.prepairFileInfo(restoreFile)
        with open(restoreFile, 'wt') as f:
            f.write('fooooooooooooooooooo')

        self.sn.restore(self.sid, restoreFile, backup = True)
        self.assertIsFile(restoreFile)
        with open(restoreFile, 'rt') as f:
            self.assertEqual(f.read(), 'bar')
        backupFile = restoreFile + self.sn.backupSuffix()
        self.assertIsFile(backupFile)
        with open(backupFile, 'rt') as f:
            self.assertEqual(f.read(), 'fooooooooooooooooooo')

    def test_no_backup(self):
        restoreFile = os.path.join(self.include.name, 'test')
        self.prepairFileInfo(restoreFile)
        with open(restoreFile, 'wt') as f:
            f.write('fooooooooooooooooooo')

        self.sn.restore(self.sid, restoreFile, backup = False)
        self.assertIsFile(restoreFile)
        with open(restoreFile, 'rt') as f:
            self.assertEqual(f.read(), 'bar')
        backupFile = restoreFile + self.sn.backupSuffix()
        self.assertIsNoFile(backupFile)

    def test_only_new(self):
        restoreFile = os.path.join(self.include.name, 'test')
        self.prepairFileInfo(restoreFile)
        with open(restoreFile, 'wt') as f:
            f.write('fooooooooooooooooooo')

        # change mtime to be newer than the one in snapshot
        st = os.stat(restoreFile)
        atime = st[stat.ST_ATIME]
        mtime = st[stat.ST_MTIME]
        new_mtime = mtime + 3600
        os.utime(restoreFile, (atime, new_mtime))

        self.sn.restore(self.sid, restoreFile, only_new = True)
        self.assertIsFile(restoreFile)
        with open(restoreFile, 'rt') as f:
            self.assertEqual(f.read(), 'fooooooooooooooooooo')

class TestRestoreLocal(RestoreTestCase):
    """
    Tests which should run on local and ssh profile
    """
    def test_restore(self):
        restoreFile = os.path.join(self.include.name, 'test')
        self.prepairFileInfo(restoreFile)

        self.sn.restore(self.sid, restoreFile)
        self.assertIsFile(restoreFile)
        with open(restoreFile, 'rt') as f:
            self.assertEqual(f.read(), 'bar')
        self.assertEqual(33260, os.stat(restoreFile).st_mode)

    def test_restore_file_with_spaces(self):
        restoreFile = os.path.join(self.include.name, 'file with spaces')
        self.prepairFileInfo(restoreFile)

        self.sn.restore(self.sid, restoreFile)
        self.assertIsFile(restoreFile)
        with open(restoreFile, 'rt') as f:
            self.assertEqual(f.read(), 'asdf')
        self.assertEqual(33260, os.stat(restoreFile).st_mode)

@unittest.skipIf(not generic.LOCAL_SSH, 'Skip as this test requires a local ssh server, public and private keys installed')
class TestRestoreSSH(generic.SSHSnapshotsWithSidTestCase, TestRestoreLocal):
    """BUHTZ 2022-10-09: Seems to me that testing restore via SSH isn't
    implemented yet.
    """

    def setUp(self):
        super(TestRestoreSSH, self).setUp()
        self.include = TemporaryDirectory()
        generic.create_test_files(os.path.join(self.remoteSIDBackupPath, self.include.name[1:]))

        #mount
        self.cfg.setCurrentHashId(mount.Mount(cfg = self.cfg).mount())

    def tearDown(self):
        #unmount
        mount.Mount(cfg = self.cfg).umount(self.cfg.current_hash_id)
        super(TestRestoreSSH, self).tearDown()

        self.include.cleanup()
