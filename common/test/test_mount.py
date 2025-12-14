# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2025 David Wales (@daviewales)
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about lock mechanic while mounting."""
# pylint: disable=wrong-import-position,R0801
import os
import sys
import inspect
import random
import string
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory
# from test import generic
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
        # pylint: disable-next=duplicate-code
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
        ''')  # pylint: disable=duplicate-code

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


class MountWithLocalBackend(pyfakefs_ut.TestCase):
    """Test high-level ``class Mount`` with 'local' backend.
    """

    def _create_config_file(self, parent_path):
        defaults = '''
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
                '''

        local_encfs_path = '/tmp/bit-test-snapshots'

        minimal_configs = {
            'local': f'''
                {defaults}
                profile1.name=test-local-mount
                profile1.snapshots.mode=local
                ''',
            'ssh': f'''
                {defaults}
                profile1.name=test-ssh-mount
                profile1.snapshots.mode=ssh
                ''',
            'local_encfs': f'''
                {defaults}
                profile1.name=test-local_encfs-mount
                profile1.snapshots.mode=local_encfs
                profile1.snapshots.local_encfs.path={local_encfs_path}
                ''',
            'ssh_encfs': f'''
                {defaults}
                profile1.name=test-ssh_encfs-mount
                profile1.snapshots.mode=ssh_encfs
                ''',
        }

        cfg_content = inspect.cleandoc(minimal_configs['local'])

        # config file location
        config_fp = parent_path / 'config_path' / 'config'
        config_fp.parent.mkdir()
        config_fp.write_text(cfg_content, 'utf-8')

        return config_fp

    def setUp(self):
        """Setup a fake filesystem."""
        self.setUpPyfakefs(allow_root_user=False)

        self.mode = 'local'

        # cleanup() happens automatically
        # pylint: disable-next=consider-using-with
        self._temp_dir = TemporaryDirectory(prefix='bit.')
        # Workaround: tempfile and pathlib not compatible yet
        self.temp_path = Path(self._temp_dir.name)

        self._config_fp = self._create_config_file(self.temp_path)
        self.cfg = config.Config(str(self._config_fp))

        # setup mount root
        fp = Path.cwd() / ''.join(random.choices(string.ascii_letters, k=10))
        fp.mkdir()
        # pylint: disable-next=protected-access
        self.cfg._LOCAL_MOUNT_ROOT = str(fp)

        self.mount = mount.Mount(cfg=self.cfg)

    def test_pre_mount_check_always_true(self):
        """preMountCheck always returns True for 'local' mode, on first run and
        even if still initialised.
        """
        for first in True, False:
            self.assertTrue(self.mount.preMountCheck(first_run=first))

    def test_mount(self):
        """mount always returns 'local' for 'local' mode.
        """
        self.assertEqual('local', self.mount.mount(check=False))

    def test_umount(self):
        """mount.umount always returns None if the hash_id is 'local'
        """
        self.assertIsNone(self.mount.umount(hash_id='local'))

    def test_remount_to_new_local_mount(self):
        """If the new profile to mount is 'local', `remount` always
        returns 'local'.
        """
        self.assertEqual(
            'local',
            self.mount.remount(new_profile_id='2', mode='local'))


# # Don't use pyfakefs, as most EncFS tests need a real filesystem
# # Note: Because EncFS_mount uses subprocess, it's not compatible
# # with pyfakefs:
# # https://pytest-pyfakefs.readthedocs.io/en/latest
# # /troubleshooting.html#subprocess-built-in

# TEST_ENCFS_PASSWORD = 'test_password'


# # NOTE: We specify the `new` argument to `mock.patch`, as this prevents
# # the mocked objects from being passed as arguments to the test methods.

# # Mock passwordFromUser to bypass the interactive password confirmation
# @mock.patch(
#     'password.Password.passwordFromUser',
#     new=mock.MagicMock(return_value=TEST_ENCFS_PASSWORD),
# )
# # Mock askQuestion to bypass the interactive user confirmation
# @mock.patch(
#     'configfile.ConfigFile.askQuestion',
#     new=mock.MagicMock(return_value=True)
# )
# class MountWithLocalEncFs(generic.TestCase):
#     """Test high-level Mount with 'local_encfs' backend.
#     """

#     def _create_config_file(self, parent_path):
#         defaults = '''
#                 config.version=6
#                 profile1.snapshots.include.1.type=0
#                 profile1.snapshots.include.1.value=rootpath/source
#                 profile1.snapshots.include.size=1
#                 profile1.snapshots.no_on_battery=false
#                 profile1.snapshots.notify.enabled=true
#                 profile1.snapshots.path=rootpath/destination
#                 profile1.snapshots.path.host=test-host
#                 profile1.snapshots.path.profile=1
#                 profile1.snapshots.path.user=test-user
#                 profile1.snapshots.preserve_acl=false
#                 profile1.snapshots.preserve_xattr=false
#                 profile1.snapshots.remove_old_snapshots.enabled=true
#                 profile1.snapshots.remove_old_snapshots.unit=80
#                 profile1.snapshots.remove_old_snapshots.value=10
#                 profile1.snapshots.rsync_options.enabled=false
#                 profile1.snapshots.rsync_options.value=
#                 profiles.version=1
#                 '''

#         local_encfs_snapshots_path = '/tmp/bit-test-snapshots'

#         minimal_configs = {
#             'local': f'''
#                 {defaults}
#                 profile1.name=test-local-mount
#                 profile1.snapshots.mode=local
#                 ''',
#             'ssh': f'''
#                 {defaults}
#                 profile1.name=test-ssh-mount
#                 profile1.snapshots.mode=ssh
#                 ''',
#             'local_encfs': f'''
#                 {defaults}
#                 profile1.name=test-local_encfs-mount
#                 profile1.snapshots.mode=local_encfs
#                 profile1.snapshots.local_encfs.path=
#                     {local_encfs_snapshots_path}
#                 ''',
#             'ssh_encfs': f'''
#                 {defaults}
#                 profile1.name=test-ssh_encfs-mount
#                 profile1.snapshots.mode=ssh_encfs
#                 ''',
#         }

#         cfg_content = inspect.cleandoc(minimal_configs['local'])

#         # config file location
#         config_fp = parent_path / 'config_path' / 'config'
#         config_fp.parent.mkdir()
#         config_fp.write_text(cfg_content, 'utf-8')

#         return config_fp

#     def setUp(self):
#         """Setup EncFS config and temporary directory"""

#         # See profiles in test/config
#         # We need two profiles to test remounting to a different
#         # profile.
#         self.local_profile = 1
#         self.local_encfs_profile_id = 3
#         self.local_encfs_profile_id_2 = 4

#         # cleanup() happens automatically
#         # pylint: disable-next=consider-using-with
#         self._temp_dir = TemporaryDirectory(prefix='bit.')
#         # Workaround: tempfile and pathlib not compatible yet
#         self.temp_path = Path(self._temp_dir.name)

#         self._config_fp = self._create_config_file(self.temp_path)
#         self.cfg = config.Config(str(self._config_fp))

#         # # pylint: disable=R1732
#         # self.temp_dir = TemporaryDirectory(prefix='bit-test-')
#         # self.temp_path = Path(self.temp_dir.name)

#         local_encfs_snapshots_path = (
#             self.temp_path / 'local-encfs-snapshots'
#         )
#         local_encfs_snapshots_path.mkdir()

#         # self.cfg = config.Config(self.cfgFile)

#         # setCurrentProfile returns False if it fails.
#         # If this happens, crash to minimise confusion.
#         assert self.cfg.setCurrentProfile(self.local_encfs_profile_id)
#         self.cfg.setLocalEncfsPath(str(local_encfs_snapshots_path))

#         # Ensure the correct test password is set, to hopefully
#         # bypass all the interactive shenanigans that would
#         # normally occur.
#         self.cfg.setPassword(TEST_ENCFS_PASSWORD)
#         self.cfg.setPassword(
#             TEST_ENCFS_PASSWORD,
#             profile_id=self.local_encfs_profile_id_2
#         )

#         # setup mount root
#         fp = self.temp_path / ''.join(
#             random.choices(string.ascii_letters, k=10)
#         )
#         fp.mkdir()
#         # pylint: disable-next=protected-access
#         self.cfg._LOCAL_MOUNT_ROOT = str(fp)

#         self.test_mount = mount.Mount(cfg=self.cfg, tmp_mount=True)

#     def tearDown(self):
#         self.temp_dir.cleanup()

#     def test_pre_mount_check(self):
#         """encfstools.EncFS_mount.preMountCheck returns True if no
#         exceptions are raised.

#         Note that encfstools.EncFS_mount.preMountCheck runs checkFuse(),
#         which in turn runs tools.checkCommand, which checks if the named
#         executable exists in the PATH, and if it has executable permissions.

#         If first_run is true, it also runs checkVersion, which checks to
#         ensure that we are running a new enough encfs version.
#         """
#         for first_run in True, False:
#             with self.subTest(first_run=first_run):
#                 self.assertTrue(
#                     self.test_mount.preMountCheck(first_run=first_run)
#                 )

#     def test_uninitialised_mount_and_unmount(self):
#         """High-level Mount.mount returns the output from backend.mount.
#         Due to inheritence, this is the same as MountControl.mount.
#         If all goes well, MountControl.mount returns self.hash_id.

#         We have to test both mount and unmount within this test, as the test
#         fails when it tries to remove the temporary directory if it finishes
#         without unmounting.
#         """

#         mount_hash = self.test_mount.mount(check=False)
#         self.assertEqual(
#             8,
#             len(mount_hash)
#         )

#         # We need to unmount it, otherwise the test fails when
#         # it tries to delete the temporary directory.
#         self.test_mount.umount(hash_id=mount_hash)

#     def test_remount_current_profile(self):
#         """Test if we can remount an existing mount.
#         """

#         mount_hash = self.test_mount.mount()

#         # Remount current profile
#         remount_hash = self.test_mount.remount(self.local_encfs_profile_id)

#         # When remounting the same profile, the new mount
#         # hash should be the same.
#         self.assertEqual(mount_hash, remount_hash)

#         # We need to unmount it, otherwise the test fails when
#         # it tries to delete the temporary directory.
#         self.test_mount.umount(hash_id=mount_hash)

#     def test_remount_to_new_local_profile(self):
#         """Test if we can remount to a new local profile"""

#         mount_hash = self.test_mount.mount()
#         print(f"{mount_hash=}")

#         # Remount different profile
#         remount_hash = self.test_mount.remount(self.local_profile)
#         print(f'{remount_hash=}')

#         # When remounting a different profile, the new mount
#         # hash should be different.
#         self.assertNotEqual(mount_hash, remount_hash)

#         # We need to unmount it, otherwise the test fails when
#         # it tries to delete the temporary directory.
#         self.test_mount.umount(hash_id=mount_hash)

#     def test_remount_to_new_local_encfs_profile(self):
#         """Test if we can remount to a new local EncFS profile"""

#         local_encfs_snapshots_2_path = (
#             self.temp_path / 'local-encfs-snapshots-2'
#         )
#         local_encfs_snapshots_2_path.mkdir()
#         self.cfg.setLocalEncfsPath(
#             str(local_encfs_snapshots_2_path),
#             profile_id=self.local_encfs_profile_id_2
#         )

#         mount_hash = self.test_mount.mount()
#         # Set the current hash_id, so remount() can find it.
#         self.cfg.setCurrentHashId(mount_hash)

#         # Remount different profile
#         remount_hash = self.test_mount.remount(self.local_encfs_profile_id_2)

#         # When remounting a different profile, the new mount
#         # hash should be different.
#         self.assertNotEqual(mount_hash, remount_hash)

#         # We need to unmount it, otherwise the test fails when
#         # it tries to delete the temporary directory.
#         self.test_mount.umount(hash_id=remount_hash)
