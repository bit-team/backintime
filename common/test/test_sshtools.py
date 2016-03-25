# Back In Time
# Copyright (C) 2016 Taylor Raack, Germar Reitze
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
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import config
import logger
import mount

ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'

class TestSSH(generic.TestCase):
    # running this test requires that user has public / private key pair created and ssh server running

    def setUp(self):
        super(TestSSH, self).setUp()
        logger.DEBUG = '-v' in sys.argv
        self.config = config.Config()
        self.config.set_snapshots_mode('ssh')
        self.config.set_ssh_host('localhost')
        self.config.set_ssh_private_key_file(os.path.expanduser(os.path.join("~",".ssh","id_rsa")))
        self.mount_kwargs = {}

    @unittest.skipIf(not ON_TRAVIS, 'Skip as this test requires a local ssh server, public and private keys installed')
    def test_can_mount_ssh_rw(self):
        with tempfile.TemporaryDirectory() as dirpath:
            self.config.set_snapshots_path_ssh(dirpath)

            mnt = mount.Mount(cfg = self.config, tmp_mount = True)
            mnt.pre_mount_check(mode = 'ssh', first_run = True, **self.mount_kwargs)

            try:
                hash_id = mnt.mount(mode = 'ssh', check = False, **self.mount_kwargs)
                full_path = os.path.expanduser(os.path.join("~",".local","share","backintime","mnt",hash_id,"mountpoint","testfile"))

                # warning - don't use os.access for checking writability
                # https://github.com/bit-team/backintime/issues/490#issuecomment-156265196
                with open(full_path, 'wt') as f:
                    f.write('foo')
            finally:
                mnt.umount(hash_id = hash_id)
