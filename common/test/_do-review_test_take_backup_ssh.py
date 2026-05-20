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
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import snapshots
import mount


@unittest.skipIf(not generic.LOCAL_SSH, generic.SKIP_SSH_TEST_MESSAGE)
class TakeSSH(generic.SSHSnapshotTestCase):  # , Take):
    def setUp(self):
        super().setUp()
        self.include = TemporaryDirectory()
        generic.create_test_files(self.include.name)

        # mount
        self.cfg.setCurrentHashId(mount.Mount(cfg = self.cfg).mount())

    def tearDown(self):
        # unmount
        mount.Mount(cfg = self.cfg).umount(self.cfg.current_hash_id)
        super().tearDown()

        self.include.cleanup()

    def remount(self):
        mount.Mount(cfg = self.cfg).umount(self.cfg.current_hash_id)
        mount.Mount(cfg = self.cfg).mount()

    def getInode(self, sid):
        return os.stat(os.path.join(
            self.snapshotPath,
            sid.sid,
            'backup',
            self.include.name[1:],
            'test')).st_ino
