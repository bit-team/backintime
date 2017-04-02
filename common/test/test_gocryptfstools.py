# Back In Time
# Copyright (C) 2017 Germar Reitze
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
import logger
import config
from gocryptfstools import GoCryptFS_mount
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TestGoCryptFS_mount(generic.TestCaseSnapshotPath):
    def setUp(self):
        super(TestGoCryptFS_mount, self).setUp()
        logger.DEBUG = '-v' in sys.argv
        self.cfg.setSnapshotsMode('local_gocryptfs')
        self.cfg.dict['profile1.snapshots.local_encfs.path'] = self.tmpDir.name
        self.mnt = GoCryptFS_mount(cfg = self.cfg, tmp_mount = True, password = 'travis')

    def test_init(self):
        self.mnt.init()
        # self.fail(os.system("ls -la %s" %self.tmpDir.name))
        self.assertExists(self.tmpDir.name, 'gocryptfs.conf')
        self.assertExists(self.tmpDir.name, 'gocryptfs.diriv')

    #def test_
