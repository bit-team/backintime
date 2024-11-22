# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about lock mechanic while mounting."""
import os
import sys
import inspect
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config
import mount  # noqa: E402,RUF100


class CheckLocks(pyfakefs_ut.TestCase):
    """Testing MountControl.checkLocks()"""

    def setUp(self):
        """Setup a fake filesystem."""
        self.setUpPyfakefs(allow_root_user=False)

        # cleanup() happens automatically
        self._temp_dir = TemporaryDirectory(prefix='bit.')
        # Workaround: tempfile and pathlib not compatible yet
        self.temp_path = Path(self._temp_dir.name)

        self.config_fp = self._create_config_file(parent_path=self.temp_path)

    def _create_config_file(self, parent_path):
        """Minimal config file"""
        # pylint: disable-next=R0801
        cfg_content = inspect.cleandoc('''
            config.version=6
            profile1.snapshots.include.1.type=0
            profile1.snapshots.include.1.value=rootpath/source
            profile1.snapshots.include.size=1
            profile1.snapshots.no_on_battery=false
            profile1.snapshots.notify.enabled=true
            profile1.snapshots.path=rootpath/destination
            profile1.snapshots.path.host=test-host
            profile1.snapshots.path.profile=1
            profile1.snapshots.path.user=test-user
            profile1.snapshots.preserve_acl=false
            profile1.snapshots.preserve_xattr=false
            profile1.snapshots.remove_old_snapshots.enabled=true
            profile1.snapshots.remove_old_snapshots.unit=80
            profile1.snapshots.remove_old_snapshots.value=10
            profile1.snapshots.rsync_options.enabled=false
            profile1.snapshots.rsync_options.value=
            profiles.version=1
        ''')

        # config file location
        config_fp = parent_path / 'config_path' / 'config'
        config_fp.parent.mkdir()
        config_fp.write_text(cfg_content, 'utf-8')

        return config_fp

    def test_not_existing_dir(self):
        """The lock directory does not exists."""
        conf = config.Config(str(self.config_fp))
        mntctrl = mount.MountControl(cfg=conf)

        with self.assertRaises(FileNotFoundError):
            mntctrl.checkLocks(path='notexisting', lockSuffix='.lock')

    def test_foobar(self):
        conf = config.Config(str(self.config_fp))
        mntctrl = mount.MountControl(cfg=conf)

        path = 'mountlockdir'
        Path(path).mkdir()
        suffix = '.lock'
        self.assertTrue(mntctrl.checkLocks(path, suffix))
