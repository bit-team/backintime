# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about statefile module."""
# pylint: disable=R0801
import unittest
import inspect
import atexit
import argparse
from pathlib import Path
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
import statedata
import backintime
import config


class IsSingleton(unittest.TestCase):
    """StateData instance is a singleton."""

    @classmethod
    def tearDownClass(cls):
        # Delete existing StateData instance
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def setUp(self):
        # Clean up all instances
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def test_identity(self):
        """Identical identity."""
        one = statedata.StateData()
        two = statedata.StateData()

        self.assertEqual(id(one), id(two))

    def test_content(self):
        """Identical values."""
        one = statedata.StateData()
        two = statedata.StateData()

        one['foobar'] = 7

        self.assertEqual(one, two)


class Migration(pyfakefs_ut.TestCase):
    """Migration from config file into state file."""
    @classmethod
    def tearDownClass(cls):
        # Delete existing StateData instance
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def _create_config_file(self, extra_content=None):
        """Minimal config file"""
        # pylint: disable-next=duplicate-code
        cfg_content = inspect.cleandoc('''
            config.version=6
            profile1.snapshots.no_on_battery=false
            profile1.snapshots.notify.enabled=true
            profile1.snapshots.path=rootpath/destination
            profile1.snapshots.path.host=test-host
            profile1.snapshots.path.profile=1
            profile1.snapshots.path.user=test-user
            profile1.snapshots.remove_old_snapshots.enabled=true
            profile1.snapshots.remove_old_snapshots.unit=80
            profile1.snapshots.remove_old_snapshots.value=10
            profile1.snapshots.include.1.type=0
            profile1.snapshots.include.1.value=rootpath/source
            profile1.snapshots.include.size=1
            profile1.snapshots.preserve_acl=false
            profile1.snapshots.preserve_xattr=false
            profile1.snapshots.rsync_options.enabled=false
            profile1.snapshots.rsync_options.value=
            profiles.version=1
            qt.main_window.x=123
            qt.main_window.y=456
        ''')  # pylint: disable=R0801

        if extra_content:
            cfg_content = cfg_content + '\n' + '\n'.join(extra_content)

        # config file location
        config_fp = Path.home() / '.config' / 'backintime' / 'config'
        config_fp.parent.mkdir(parents=True)
        config_fp.write_text(cfg_content, 'utf-8')

        return config_fp

    def tearDown(self):
        self.config_fp.unlink(missing_ok=True)
        self.state_fp.unlink(missing_ok=True)

    def setUp(self):
        """Setup a fake filesystem with a config file."""
        self.setUpPyfakefs(allow_root_user=False)

        # Delete existing StateData instance
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

        self.config_fp = self._create_config_file()
        self.state_fp = Path.home() / '.local' / 'state' / 'backintime.json'

    def test_create_json_file_at_exit(self):
        """Create state file if not exists."""

        # State file does not exist
        self.assertFalse(self.state_fp.exists())

        # Try to load statefile will trigger migration of config values
        # into a fresh state object
        args = argparse.Namespace(
            config="/home/user/.config/backintime/config",
            share_path="/home/user/.local/share")
        backintime.load_state_data(args)

        statedata.StateData()

        # File still not written to filesystem
        self.assertFalse(self.state_fp.exists())

        # Exit application trigger state file write
        atexit._run_exitfuncs()  # pylint: disable=protected-access

        # Not it exists
        self.assertTrue(self.state_fp.exists())

    def test_migrate_config(self):
        """Values from config file migrated to state data."""

        # State file does not exist
        self.assertFalse(self.state_fp.exists())

        # Try to load statefile will trigger migration of config values
        # into a fresh state object
        args = argparse.Namespace(
            config=str(Path.home() / ".config" / "backintime" / "config"),
            share_path=str(Path.home() / ".local" / "share"))
        backintime.load_state_data(args)

        sut = statedata.StateData()

        self.assertEqual(sut.mainwindow_coords, (123, 456))


class Properties(unittest.TestCase):
    """Property access without errors."""

    @classmethod
    def tearDownClass(cls):
        # Delete existing StateData instance
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def setUp(self):
        # Delete existing StateData instance
        try:
            # pylint: disable-next=protected-access
            del statedata.StateData._instances[statedata.StateData]
        except KeyError:
            pass

    def test_read_empty_global(self):
        """Read properties from empty state data"""
        sut = statedata.StateData()

        self.assertEqual(sut.msg_release_candidate, None)
        self.assertEqual(sut.msg_encfs_global, False)
        self.assertEqual(sut.mainwindow_show_hidden, False)
        self.assertEqual(sut.files_view_sorting, (0, 0))
        self.assertEqual(sut.mainwindow_main_splitter_widths, (150, 450))
        self.assertEqual(sut.mainwindow_second_splitter_widths, (150, 300))

        with self.assertRaises(KeyError):
            # pylint: disable=pointless-statement
            sut.mainwindow_coords
            sut.mainwindow_dims
            sut.logview_dims
            sut.files_view_col_widths

    def test_profile_not_exist(self):
        """Profile does not exists."""
        sut = statedata.StateData()
        profile = sut.profile(42)

        with self.assertRaises(KeyError):
            # pylint: disable=pointless-statement
            profile.last_path

    @pyfakefs_ut.patchfs(allow_root_user=False)
    def test_read_non_existing_profile(self, _fake_fs):
        """Read state value from non existing profile."""
        cfg_content = inspect.cleandoc('''
        ''')  # pylint: disable=R0801

        # config file location
        config_fp = Path.home() / '.config' / 'backintime' / 'config'
        config_fp.parent.mkdir(parents=True)
        config_fp.write_text(cfg_content, 'utf-8')

        cfg = config.Config(config_fp)
        # pylint: disable-next=protected-access
        sut = backintime._get_state_data_from_config(cfg)

        # empty profile
        profile = sut.profile('1')

        with self.assertRaises(KeyError) as exc:
            # pylint: disable=pointless-statement
            profile.msg_encfs

        # Profile 1 does not exist
        self.assertEqual(exc.exception.args[0], '1')

    @pyfakefs_ut.patchfs(allow_root_user=False)
    def test_write_non_existing_profile(self, _fake_fs):
        """Write state value to non existing profile."""
        cfg_content = inspect.cleandoc('''
        ''')  # pylint: disable=R0801

        # config file location
        config_fp = Path.home() / '.config' / 'backintime' / 'config'
        config_fp.parent.mkdir(parents=True)
        config_fp.write_text(cfg_content, 'utf-8')

        cfg = config.Config(config_fp)
        # pylint: disable-next=protected-access
        sut = backintime._get_state_data_from_config(cfg)

        # empty profile
        profile = sut.profile('1')

        # nothing raised
        profile.msg_encfs = True

        self.assertEqual(profile.msg_encfs, True)
