# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
import unittest
import schedule


class Schedule(unittest.TestCase):
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

        result = schedule.remove_bit_from_crontab(content)

        self.assertEqual(result, expect)
        self.assertIn('--profile-id 7', result[-1])

    def test_bit_to_crontab(self):
        result = schedule.append_bit_to_crontab(
            [],
            ['foo', 'bar']
        )

        self.assertEqual(len(result), 4)
        self.assertTrue(result[0][0], '#')
        self.assertTrue(result[1], 'foo')
        self.assertTrue(result[2][0], '#')
        self.assertTrue(result[3], 'bar')
