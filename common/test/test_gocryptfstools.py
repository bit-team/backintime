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
from tempfile import TemporaryDirectory
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

CONF = """{
        "Creator": "gocryptfs v1.1.1-22-g081015a",
        "EncryptedKey": "+tYXhs56Ulb5nHnmUBdNVnjjXrn8uy1HvPEMBRpaxb4aOpUizlHP3smaerx8Uq20ReeUUYJjVn+W7RRh",
        "ScryptObject": {
                "Salt": "4xPz7gIVtWWQC/y1eJmG05+maaFztcGSdHvwRQ11jU0=",
                "N": 65536,
                "R": 8,
                "P": 1,
                "KeyLen": 32
        },
        "Version": 2,
        "FeatureFlags": [
                "GCMIV128",
                "DirIV",
                "EMENames",
                "LongNames"
        ]
}"""

DIRIV = "ABCDEFGHIJKLMNOP"

def writeConfigFiles(path):
    with open(os.path.join(path, 'gocryptfs.conf'), 'wt') as conf:
        conf.write(CONF)
    with open(os.path.join(path, 'gocryptfs.diriv'), 'wt') as diriv:
        diriv.write(DIRIV)

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

    def test_mount(self):
        cipherDir = self.tmpDir.name
        cipherTestFile = os.path.join(cipherDir, 'Ho0fMHPuBd6Lo8ExGfhEtw==')

        writeConfigFiles(cipherDir)
        # writeConfigFiles('/tmp/keep')
        with TemporaryDirectory() as mntPoint:
            # mntPoint = '/tmp/mnt'
            self.mnt.currentMountpoint = mntPoint
            self.mnt._mount()
            with open(os.path.join(mntPoint, 'test'), 'wt') as test:
                test.write('foo')
            self.assertExists(cipherTestFile)
