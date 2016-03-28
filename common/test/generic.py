# Back In Time
# Copyright (C) 2016 Germar Reitze
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
import unittest
from tempfile import TemporaryDirectory, NamedTemporaryFile

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logger
import config
import snapshots

TMP_FLOCK = NamedTemporaryFile()

class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        os.environ['LANGUAGE'] = 'en_US.UTF-8'
        self.cfgFile = os.path.abspath(os.path.join(__file__, os.pardir, 'config'))
        self.sharePath = '/tmp/bit'
        logger.APP_NAME = 'BIT_unittest'
        logger.openlog()
        super(TestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        logger.DEBUG = '-v' in sys.argv

class SnapshotsTestCase(TestCase):
    def setUp(self):
        super(SnapshotsTestCase, self).setUp()
        self.cfg = config.Config(self.cfgFile, self.sharePath)
        #use a new TemporaryDirectory for snapshotPath to avoid
        #side effects on leftovers
        self.tmpDir = TemporaryDirectory()
        self.cfg.dict['profile1.snapshots.path'] = self.tmpDir.name
        self.snapshotPath = self.cfg.get_snapshots_full_path()
        os.makedirs(self.snapshotPath)

        self.sn = snapshots.Snapshots(self.cfg)
        #use a tmp-file for flock because test_flockExclusive would deadlock
        #otherwise if a regular snapshot is running in background
        self.sn.GLOBAL_FLOCK = TMP_FLOCK.name

    def tearDown(self):
        self.tmpDir.cleanup()

class SnapshotsWithSidTestCase(SnapshotsTestCase):
    def setUp(self):
        super(SnapshotsWithSidTestCase, self).setUp()
        self.sid = snapshots.SID('20151219-010324-123', self.cfg)

        self.sid.makeDirs()
        self.testDir = 'foo/bar'
        self.testDirFullPath = self.sid.pathBackup(self.testDir)
        self.testFile = 'foo/bar/baz'
        self.testFileFullPath = self.sid.pathBackup(self.testFile)

        self.sid.makeDirs(self.testDir)
        with open(self.sid.pathBackup(self.testFile), 'wt') as f:
            pass
