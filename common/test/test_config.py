# Back In Time
# Copyright (C) 2016 Taylor Raack
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

from contextlib import contextmanager
import os
import shutil
import stat
import sys
import tempfile
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import config
import logger

@contextmanager
def tempdir():
    name = tempfile.mkdtemp()
    try:
        yield name
    finally:
        shutil.rmtree(name)

class TestConfig(unittest.TestCase):

    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.config = config.Config()

    def test_set_snapshots_path_test_writes(self):
        with tempdir() as dirpath:
            self.assertTrue(self.config.set_snapshots_path(dirpath))

    def test_set_snapshots_path_fails_on_ro(self):
        with tempdir() as dirpath:
            # set directory to read only
            os.chmod(dirpath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            self.assertFalse(self.config.set_snapshots_path(dirpath))
