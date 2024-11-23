# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about lock mechanic while mounting."""
# pylint: disable=wrong-import-position
import os
import sys
import inspect
import random
import string
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config  # noqa: E402,RUF100
import mount  # noqa: E402,RUF100


class CheckLocks(pyfakefs_ut.TestCase):
    """Testing MountControl.checkLocks()"""

    def setUp(self):
        """Setup a fake filesystem."""
        self.setUpPyfakefs(allow_root_user=False)

        # cleanup() happens automatically
        # pylint: disable-next=consider-using-with
        self._temp_dir = TemporaryDirectory(prefix='bit.')
        # Workaround: tempfile and pathlib not compatible yet
        self.temp_path = Path(self._temp_dir.name)

        self._config_fp = self._create_config_file(parent_path=self.temp_path)
        self.cfg = config.Config(str(self._config_fp))

        # setup mount root
        fp = Path.cwd() / ''.join(random.choices(string.ascii_letters, k=10))
        fp.mkdir()
        # pylint: disable-next=protected-access
        self.cfg._LOCAL_MOUNT_ROOT = str(fp)

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
        mntctrl = mount.MountControl(cfg=self.cfg)
        mntctrl.setDefaultArgs()

        with self.assertRaises(FileNotFoundError):
            mntctrl.checkLocks('notexisting', '.lock')

    def test_ignore_own_lock(self):
        """Lock file of own process ignored."""
        mntctrl = mount.MountControl(cfg=self.cfg)
        mntctrl.setDefaultArgs()

        fp = Path(mntctrl.mount_root) / f'{os.getpid()}.lock'
        fp.touch()

        self.assertFalse(mntctrl.checkLocks(str(fp.parent), fp.suffix))

    def test_own_lock_but_diff_tmpmount(self):
        """Lock file of own process but diff tmp-mount."""
        mntctrl = mount.MountControl(cfg=self.cfg, tmp_mount=True)
        mntctrl.setDefaultArgs()

        fp = Path(mntctrl.mount_root) / f'{os.getpid()}.lock'
        fp.touch()

        self.assertTrue(mntctrl.checkLocks(str(fp.parent), fp.suffix))

    @mock.patch('tools.processAlive', return_value=True)
    def test_foreign_lock(self, _mock_process_alive):
        """Lock file of foreign and existing process."""
        mntctrl = mount.MountControl(cfg=self.cfg)
        mntctrl.setDefaultArgs()

        fp = Path(mntctrl.mount_root) / '123456.lock'
        fp.touch()

        self.assertTrue(mntctrl.checkLocks(str(fp.parent), fp.suffix))

    @mock.patch('tools.processAlive', return_value=False)
    def test_foreign_lock_notexisting_pid(self, _mock_process_alive):
        """Lock file of foreign and NOT existing process."""
        mntctrl = mount.MountControl(cfg=self.cfg)
        mntctrl.setDefaultArgs()

        pid = '123456'
        fp = Path(mntctrl.mount_root) / f'{pid}.lock'
        fp.touch()

        self.assertFalse(mntctrl.checkLocks(str(fp.parent), fp.suffix))

    @mock.patch('tools.processAlive', return_value=False)
    def test_lock_remove(self, _mock_process_alive):
        """Remove lock files of NOT existing processes."""
        mntctrl = mount.MountControl(cfg=self.cfg)
        mntctrl.setDefaultArgs()

        pid = '123456'
        fp = Path(mntctrl.mount_root) / f'{pid}.lock'
        fp.touch()

        self.assertTrue(fp.exists())
        mntctrl.checkLocks(str(fp.parent), fp.suffix)

        self.assertFalse(fp.exists())

    @mock.patch('tools.processAlive', return_value=False)
    def test_symlinks_remove(self, _mock_process_alive):
        """Remove symlinks related to lock files of NOT existing processes."""
        mntctrl = mount.MountControl(cfg=self.cfg)
        mntctrl.setDefaultArgs()

        pid = '123456'
        fp = Path(mntctrl.mount_root) / f'{pid}.lock'
        fp.touch()

        real = Path.cwd() / 'real'
        real.mkdir()
        sym = Path(mntctrl.mount_root) / f'symlink_mountpoint_{pid}'
        sym.symlink_to(real)

        self.assertTrue(sym.exists())
        mntctrl.checkLocks(str(fp.parent), fp.suffix)

        self.assertFalse(sym.exists())
