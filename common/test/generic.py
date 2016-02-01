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
from tempfile import TemporaryDirectory

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logger
import config

class TestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        logger.APP_NAME = 'BIT_unittest'
        logger.openlog()
        super(TestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        logger.DEBUG = '-v' in sys.argv

class SnapshotsTestCase(TestCase):
    def setUp(self):
        super(SnapshotsTestCase, self).setUp()
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
