# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about timeline widget."""
# pylint: disable=wrong-import-position,wrong-import-order
import unittest
from datetime import date
from qttools_path import register_backintime_path
register_backintime_path('common')
import timeline  # noqa: E402

STRFTIME = '%Y-%m-%d %a %H:%M'


def _datetime_to_str(result):
    for idx, val in enumerate(result):
        result[idx] = (
            val[0],
            val[1].strftime(STRFTIME),
            val[2].strftime(STRFTIME)
        )

    return result


class Periods(unittest.TestCase):
    """StateData instance is a singleton."""
    # pylint: disable=protected-access,missing-function-docstring

    def test_simple_a(self):
        """Simple situations without edge cases"""
        today = date(2026, 3, 28)  # Saturday
        sut = timeline._calculate_timeline_periods(today)

        expect = [
            ('Today', '2026-03-28 Sat 00:00', '2026-03-28 Sat 23:59'),
            ('Yesterday', '2026-03-27 Fri 00:00', '2026-03-27 Fri 23:59'),
            ('This week', '2026-03-23 Mon 00:00', '2026-03-26 Thu 23:59'),
            ('Last week', '2026-03-16 Mon 00:00', '2026-03-22 Sun 23:59'),
            ('This month', '2026-03-01 Sun 00:00', '2026-03-15 Sun 23:59'),
            ('Last month', '2026-02-01 Sun 00:00', '2026-02-28 Sat 23:59'),
        ]

        self.assertEqual(
            _datetime_to_str(sut),
            expect
        )

    def test_simple_b(self):
        today = date(2026, 3, 18)
        sut = timeline._calculate_timeline_periods(today)

        expect = [
            ('Today', '2026-03-18 Wed 00:00', '2026-03-18 Wed 23:59'),
            ('Yesterday', '2026-03-17 Tue 00:00', '2026-03-17 Tue 23:59'),
            ('This week', '2026-03-16 Mon 00:00', '2026-03-16 Mon 23:59'),
            ('Last week', '2026-03-09 Mon 00:00', '2026-03-15 Sun 23:59'),
            ('This month', '2026-03-01 Sun 00:00', '2026-03-08 Sun 23:59'),
            ('Last month', '2026-02-01 Sun 00:00', '2026-02-28 Sat 23:59'),
        ]

        self.assertEqual(
            _datetime_to_str(sut),
            expect
        )

    def test_simple_c(self):
        today = date(2026, 3, 12)
        sut = timeline._calculate_timeline_periods(today)

        expect = [
            ('Today', '2026-03-12 Thu 00:00', '2026-03-12 Thu 23:59'),
            ('Yesterday', '2026-03-11 Wed 00:00', '2026-03-11 Wed 23:59'),
            ('This week', '2026-03-09 Mon 00:00', '2026-03-10 Tue 23:59'),
            ('Last week', '2026-03-02 Mon 00:00', '2026-03-08 Sun 23:59'),
            ('This month', '2026-03-01 Sun 00:00', '2026-03-01 Sun 23:59'),
            ('Last month', '2026-02-01 Sun 00:00', '2026-02-28 Sat 23:59'),
        ]

        self.assertEqual(_datetime_to_str(sut), expect)

    def test_last_week_overlap_last_month(self):
        """Without 'This month' and shorter 'Last month'

        This months, is covered by all previous periods in the list.
        Last months is shorted because of Last week lapping into the last
        months.
        """
        today = date(2026, 3, 7)
        sut = timeline._calculate_timeline_periods(today)

        expect = [
            ('Today', '2026-03-07 Sat 00:00', '2026-03-07 Sat 23:59'),
            ('Yesterday', '2026-03-06 Fri 00:00', '2026-03-06 Fri 23:59'),
            ('This week', '2026-03-02 Mon 00:00', '2026-03-05 Thu 23:59'),
            ('Last week', '2026-02-23 Mon 00:00', '2026-03-01 Sun 23:59'),
            ('Last month', '2026-02-01 Sun 00:00', '2026-02-22 Sun 23:59'),
        ]

        self.assertEqual(_datetime_to_str(sut), expect)

    def test_this_week_overlap_yesterday(self):
        """Without 'This week' because it touches 'Yesterday'.
        """
        today = date(2026, 3, 3)
        sut = timeline._calculate_timeline_periods(today)

        expect = [
            ('Today', '2026-03-03 Tue 00:00', '2026-03-03 Tue 23:59'),
            ('Yesterday', '2026-03-02 Mon 00:00', '2026-03-02 Mon 23:59'),
            ('Last week', '2026-02-23 Mon 00:00', '2026-03-01 Sun 23:59'),
            ('Last month', '2026-02-01 Sun 00:00', '2026-02-22 Sun 23:59'),
        ]

        self.assertEqual(_datetime_to_str(sut), expect)
