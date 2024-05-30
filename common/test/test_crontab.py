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
import unittest
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
import sys
import os
import tempfile
import inspect
from pathlib import Path
from unittest import mock
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import backintime
import config
import snapshots
import tools
import logger


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

        sut = conf.cronCmd(profile_id='1')
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

        sut = conf.cronCmd(profile_id='1')
        self.assertNotIn('--debug', sut)


class CrontabContent(unittest.TestCase):
    """Manipulation of crontab content"""
    def test_remove_bit_entries(self):
        """Remove BIT entries from crontab.

        Three BIT entries in the crontab. The 1st and 3rd are auto generated
        by BIT schedule feature and will be removed. But the second is
        user defined and need to stay.
        """
        content = [
            '# -------------- min (0 - 59)',
            '# | --------------- hour (0 - 23)',
            '# | | ---------------- day of month (1 - 31),'
            '# | | | ----------------- month (1 - 12)',
            '# | | | | ------------------ day of week (0 - 6)',
            '# Saturday, or use names; 7 is Sunday, the same as 0)',
            '# | | | | |',
            '# | | | | |',
            '# * * * * *',
            '',
            '30/* * * * * dohyperorg > /def/null',
            '',

            '51 */3 * * * cronjobblock '
            '/home/user/.my.scripts/thunderbird_backup_duplicity.sh',

            '',

            '#Back In Time system entry, this will be edited by the gui:',

            '0 8,12,18,23 * * * /usr/bin/nice -n19 /usr/bin/ionice -c2 -n7 '
            '/usr/bin/backintime backup-job >/dev/null',

            '0 2 3 4 5 /usr/bin/nice -n19 /usr/bin/ionice -c2 -n7 '
            '/usr/bin/backintime --profile-id 7 backup-job >/dev/null',

            '#Back In Time system entry, this will be edited by the gui:',

            '0 0 1 1 * /usr/bin/nice -n19 /usr/bin/ionice -c2 -n7 '
            '/usr/bin/backintime --profile-id 3 backup-job >/dev/null',
        ]

        expect = content[:]
        # Remove the last BIT entry incl. comment
        del expect[-1]
        del expect[-1]
        # Remove the one before the one before the last
        del expect[-2]
        del expect[-2]

        result = config.Config.removeOldCrontab(None, content)

        self.assertEqual(result, expect)
        self.assertIn('--profile-id 7', result[-1])
