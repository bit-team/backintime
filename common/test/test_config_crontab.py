# Back In Time
# Copyright (C) 2024 Kosta Vukicevic, Christian Buhtz
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
"""Tests about Cron-related behavior of the config module.

See also test_schedule.py for low-level-Cron-behavior implemented in schedule
module."""
import unittest
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
import sys
import os
import tempfile
import inspect
from pathlib import Path
from unittest import mock
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config


class Cron(unittest.TestCase):
    """Cron-related behavior of Config class."""
    def test_cron_lines(self):
        """Creation of crontab lines per profile"""
        # Mock reading a config file
        with mock.patch('configfile.ConfigFile.append'):
            cfg = config.Config()

            # Profile 1 (default profile)
            cfg.setScheduleMode(12)  # 12 = every two hours

            # Profile 2
            profile_id = cfg.addProfile('NoSchedule')
            self.assertEqual(profile_id, '2')

            # Profile 3
            profile_id = cfg.addProfile('Second')
            self.assertEqual(profile_id, '3')
            cfg.setScheduleMode(7, profile_id)  # 7 = every 30 minutes

            result = cfg.profiles_cron_lines()

        self.assertEqual(len(result), 2)

        self.assertIn('*/2 * * *', result[0])
        self.assertIn('backintime', result[0])
        self.assertIn('backup-job', result[0])
        self.assertNotIn('--profile-id', result[0])

        self.assertIn('*/30 * * *', result[1])
        self.assertIn('backintime', result[1])
        self.assertIn('backup-job', result[1])
        self.assertIn('--profile-id 3', result[1])


class CrontabDebug(pyfakefs_ut.TestCase):
    """Debug behavior when scheduled via crontab"""
    def setUp(self):
        """Setup a fake filesystem with a config file."""
        self.setUpPyfakefs(allow_root_user=False)

        # cleanup() happens automatically
        self._temp_dir = tempfile.TemporaryDirectory(prefix='bit.')
        # Workaround: tempfile and pathlib not compatible yet
        self.temp_path = Path(self._temp_dir.name)

        self.config_fp = self._create_config_file(parent_path=self.temp_path)

    def _create_config_file(cls, parent_path):
        """Minimal config file"""
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

    @mock.patch('tools.which', return_value='backintime')
    def test_crontab_contains_debug(self, mock_which):
        """
        About mock_which: A workaround because the function gives
        false-negative when using a fake filesystem.
        """
        conf = config.Config(str(self.config_fp))

        # set and assert start conditions
        conf.setScheduleDebug(True)
        self.assertTrue(conf.scheduleDebug())

        sut = conf._cron_cmd(profile_id='1')
        self.assertIn('--debug', sut)

    @mock.patch('tools.which', return_value='backintime')
    def test_crontab_without_debug(self, mock_which):
        """No debug output in crontab line.

        About mock_which: See test_crontab_with_debug().
        """
        conf = config.Config(str(self.config_fp))

        # set and assert start conditions
        conf.setScheduleDebug(False)
        self.assertFalse(conf.scheduleDebug())

        sut = conf._cron_cmd(profile_id='1')
        self.assertNotIn('--debug', sut)
