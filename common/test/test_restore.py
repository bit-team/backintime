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
import unittest
import pwd
import grp
from tempfile import TemporaryDirectory
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config
import snapshots
import mount

CURRENTUID = os.geteuid()
CURRENTUSER = pwd.getpwuid(CURRENTUID).pw_name

CURRENTGID = os.getegid()
CURRENTGROUP = grp.getgrgid(CURRENTGID).gr_name

class TestRestore(generic.SnapshotsWithSidTestCase):
    def setUp(self):
        super(TestRestore, self).setUp()
        self.include = TemporaryDirectory()
        generic.create_test_files(self.sid.pathBackup(self.include.name))

    def tearDown(self):
        super(TestRestore, self).tearDown()
        self.include.cleanup()

    def remount(self):
        pass

    def prepairFileInfo(self, restoreFile, mode = 33260):
        d = self.sid.fileInfo
        d[restoreFile.encode('utf-8', 'replace')] = (mode,
                                                     CURRENTUSER.encode('utf-8', 'replace'),
                                                     CURRENTGROUP.encode('utf-8', 'replace'))
        self.sid.fileInfo = d

    def test_restore(self):
        restoreFile = os.path.join(self.include.name, 'test')
        self.prepairFileInfo(restoreFile)

        self.sn.restore(self.sid, restoreFile)
        self.assertTrue(os.path.isfile(restoreFile))
        with open(restoreFile, 'rt') as f:
            self.assertEqual(f.read(), 'bar')
        self.assertEqual(33260, os.stat(restoreFile).st_mode)

    def test_restore_file_with_spaces(self):
        restoreFile = os.path.join(self.include.name, 'file with spaces')
        self.prepairFileInfo(restoreFile)

        self.sn.restore(self.sid, restoreFile)
        self.assertTrue(os.path.isfile(restoreFile))
        with open(restoreFile, 'rt') as f:
            self.assertEqual(f.read(), 'asdf')
        self.assertEqual(33260, os.stat(restoreFile).st_mode)

    def test_restore_multiple_files(self):
        restoreFile1 = os.path.join(self.include.name, 'test')
        self.prepairFileInfo(restoreFile1)
        restoreFile2 = os.path.join(self.include.name, 'foo', 'bar', 'baz')
        self.prepairFileInfo(restoreFile2)

        self.sn.restore(self.sid, (restoreFile1, restoreFile2))
        self.assertTrue(os.path.isfile(restoreFile1))
        with open(restoreFile1, 'rt') as f:
            self.assertEqual(f.read(), 'bar')
        self.assertEqual(33260, os.stat(restoreFile1).st_mode)

        self.assertTrue(os.path.isfile(restoreFile2))
        with open(restoreFile2, 'rt') as f:
            self.assertEqual(f.read(), 'foo')
        self.assertEqual(33260, os.stat(restoreFile2).st_mode)

    def test_restore_to_different_destination(self):
        restoreFile = os.path.join(self.include.name, 'test')
        self.prepairFileInfo(restoreFile)
        dest = TemporaryDirectory()
        # destRestoreFile = restoreFile
        destRestoreFile = os.path.join(dest.name, 'test')
        # self.remount()
        #
        # self.assertTrue(self.sid.canOpenPath(restoreFile))
        # self.fail('include: {} | dest: {} | content: {}'.format(self.include.name, dest.name, os.listdir(self.include.name)))
        self.sn.restore(self.sid, restoreFile, restore_to = dest.name)
        self.assertTrue(os.path.isfile(destRestoreFile))
        with open(destRestoreFile, 'rt') as f:
            self.assertEqual(f.read(), 'bar')
        self.assertEqual(33260, os.stat(destRestoreFile).st_mode)

@unittest.skipIf(not generic.LOCAL_SSH, 'Skip as this test requires a local ssh server, public and private keys installed')
class TestRestoreSSH(generic.SSHSnapshotsWithSidTestCase, TestRestore):
    def setUp(self):
        super(TestRestoreSSH, self).setUp()
        self.include = TemporaryDirectory()
        generic.create_test_files(os.path.join(self.remoteSIDBackupPath, self.include.name[1:]))

        #mount
        self.cfg.set_current_hash_id(mount.Mount(cfg = self.cfg).mount())

    def tearDown(self):
        #unmount
        mount.Mount(cfg = self.cfg).umount(self.cfg.current_hash_id)
        super(TestRestoreSSH, self).tearDown()

        self.include.cleanup()

    def remount(self):
        mount.Mount(cfg = self.cfg).umount(self.cfg.current_hash_id)
        hash_id = mount.Mount(cfg = self.cfg).mount()

    @unittest.skip('Bug #595 not yet fixed')
    def test_restore_file_with_spaces(self):
        pass
