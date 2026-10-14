# SPDX-FileCopyrightText: © 2026 Back In Time Maintainers
# SPDX-License-Identifier: GPL-2.0-or-later
"""Comprehensive unit tests for pure retention calculation engine (issue #1945)."""
import os
import sys
import datetime
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import retention
from retention import SnapshotRecord, RetentionPolicy, calculate_retention, inc_month, dec_month


class TestMonthArithmetic(unittest.TestCase):
    def test_inc_month(self):
        self.assertEqual(inc_month(datetime.date(2026, 1, 15)), datetime.date(2026, 2, 1))
        self.assertEqual(inc_month(datetime.date(2026, 12, 31)), datetime.date(2027, 1, 1))

    def test_dec_month(self):
        self.assertEqual(dec_month(datetime.date(2026, 2, 28)), datetime.date(2026, 1, 1))
        self.assertEqual(dec_month(datetime.date(2026, 1, 1)), datetime.date(2025, 12, 1))


class TestRetentionCalculation(unittest.TestCase):
    def test_empty_and_single(self):
        policy = RetentionPolicy()
        keep, to_delete = calculate_retention([], policy)
        self.assertEqual(keep, set())
        self.assertEqual(to_delete, [])

        single = SnapshotRecord('20260101-120000', datetime.date(2026, 1, 1))
        keep, to_delete = calculate_retention([single], policy)
        self.assertEqual(keep, {single})
        self.assertEqual(to_delete, [])

    def test_keep_all_days(self):
        now = datetime.date(2026, 6, 10)
        # Create snapshots: today, 1 day ago, 2 days ago, 5 days ago
        s0 = SnapshotRecord('s0', datetime.date(2026, 6, 10))
        s1 = SnapshotRecord('s1', datetime.date(2026, 6, 9))
        s2 = SnapshotRecord('s2', datetime.date(2026, 6, 8))
        s5 = SnapshotRecord('s5', datetime.date(2026, 6, 5))

        # keep_all_days=2 should keep s0 and s1; with other buckets disabled, s2 and s5 are deleted
        policy = RetentionPolicy(
            keep_all_days=2,
            keep_one_per_day=0,
            keep_one_per_week=0,
            keep_one_per_month=0,
            keep_one_per_year=False
        )
        keep, to_delete = calculate_retention([s0, s1, s2, s5], policy, now=now)
        self.assertIn(s0, keep)
        self.assertIn(s1, keep)
        self.assertNotIn(s2, keep)
        self.assertNotIn(s5, keep)
        self.assertEqual(to_delete, [s2, s5])

    def test_keep_one_per_day_prunes_same_day(self):
        now = datetime.date(2026, 6, 10)
        # Two snapshots on the same day 3 days ago (outside keep_all)
        s_morning = SnapshotRecord('s_m', datetime.datetime(2026, 6, 7, 8, 0))
        s_evening = SnapshotRecord('s_e', datetime.datetime(2026, 6, 7, 20, 0))
        s_today = SnapshotRecord('s_t', datetime.datetime(2026, 6, 10, 12, 0))

        # Youngest first order: s_today, s_evening, s_morning
        snapshots = [s_today, s_evening, s_morning]

        policy = RetentionPolicy(
            keep_all_days=1,
            keep_one_per_day=7,
            keep_one_per_week=0,
            keep_one_per_month=0,
            keep_one_per_year=False
        )
        keep, to_delete = calculate_retention(snapshots, policy, now=now)

        self.assertIn(s_today, keep)
        # s_evening is younger than s_morning on June 7, so it is kept as the representative for that day
        self.assertIn(s_evening, keep)
        self.assertNotIn(s_morning, keep)
        self.assertEqual(to_delete, [s_morning])

    def test_keep_one_per_week_monday_alignment(self):
        # 2026-06-10 is a Wednesday.
        # Monday of this week is 2026-06-08.
        # Monday of previous week is 2026-06-01.
        now = datetime.date(2026, 6, 10)
        s_now = SnapshotRecord('now', datetime.date(2026, 6, 10))
        s_prev_tue = SnapshotRecord('prev_tue', datetime.date(2026, 6, 2))
        s_prev_fri = SnapshotRecord('prev_fri', datetime.date(2026, 6, 5))
        s_old = SnapshotRecord('old', datetime.date(2026, 5, 10))

        snapshots = [s_now, s_prev_fri, s_prev_tue, s_old]

        policy = RetentionPolicy(
            keep_all_days=0,
            keep_one_per_day=0,
            keep_one_per_week=2,
            keep_one_per_month=0,
            keep_one_per_year=False
        )
        keep, to_delete = calculate_retention(snapshots, policy, now=now)

        self.assertIn(s_now, keep)
        self.assertIn(s_prev_fri, keep)
        self.assertNotIn(s_prev_tue, keep)
        self.assertNotIn(s_old, keep)
        self.assertEqual(to_delete, [s_prev_tue, s_old])

    def test_keep_one_per_year_explicit_finite_limit(self):
        now = datetime.date(2026, 6, 1)
        s_2026 = SnapshotRecord('2026', datetime.date(2026, 1, 15))
        s_2025 = SnapshotRecord('2025', datetime.date(2025, 6, 1))
        s_2024 = SnapshotRecord('2024', datetime.date(2024, 6, 1))
        s_2020 = SnapshotRecord('2020', datetime.date(2020, 6, 1))

        snapshots = [s_2026, s_2025, s_2024, s_2020]

        # Case 1: keep_one_per_year=True -> keep all years
        policy_all = RetentionPolicy(
            keep_all_days=0,
            keep_one_per_day=0,
            keep_one_per_week=0,
            keep_one_per_month=0,
            keep_one_per_year=True
        )
        keep_all, del_all = calculate_retention(snapshots, policy_all, now=now)
        self.assertEqual(len(del_all), 0)

        # Case 2: keep_one_per_year=2 -> keep only last 2 years (2026 and 2025), prune 2024 and 2020
        policy_2yr = RetentionPolicy(
            keep_all_days=0,
            keep_one_per_day=0,
            keep_one_per_week=0,
            keep_one_per_month=0,
            keep_one_per_year=2
        )
        keep_2yr, del_2yr = calculate_retention(snapshots, policy_2yr, now=now)
        self.assertIn(s_2026, keep_2yr)
        self.assertIn(s_2025, keep_2yr)
        self.assertNotIn(s_2024, keep_2yr)
        self.assertNotIn(s_2020, keep_2yr)
        self.assertEqual(del_2yr, [s_2024, s_2020])

        # Case 3: keep_one_per_year=False -> disabled, older years pruned
        policy_none = RetentionPolicy(
            keep_all_days=0,
            keep_one_per_day=0,
            keep_one_per_week=0,
            keep_one_per_month=0,
            keep_one_per_year=False
        )
        keep_none, del_none = calculate_retention(snapshots, policy_none, now=now)
        self.assertEqual(keep_none, {s_2026})
        self.assertEqual(del_none, [s_2025, s_2024, s_2020])

    def test_healthy_vs_failed_fallback(self):
        now = datetime.date(2026, 6, 1)
        s_youngest = SnapshotRecord('young', datetime.date(2026, 6, 1))

        # Interval has failed and healthy snapshots
        s_healthy = SnapshotRecord('healthy', datetime.date(2026, 5, 10), failed=False)
        s_failed = SnapshotRecord('failed', datetime.date(2026, 5, 20), failed=True)

        snapshots = [s_youngest, s_failed, s_healthy]

        policy = RetentionPolicy(
            keep_all_days=0,
            keep_one_per_day=0,
            keep_one_per_week=0,
            keep_one_per_month=2,
            keep_one_per_year=False
        )
        keep, _del = calculate_retention(snapshots, policy, now=now)
        # s_healthy should be preferred over s_failed
        self.assertIn(s_healthy, keep)
        self.assertNotIn(s_failed, keep)

        # But if ALL snapshots in the bucket are failed, the failed one is kept as fallback
        s_only_failed = SnapshotRecord('only_failed', datetime.date(2026, 5, 15), failed=True)
        snapshots2 = [s_youngest, s_only_failed]
        keep2, _del2 = calculate_retention(snapshots2, policy, now=now)
        self.assertIn(s_only_failed, keep2)

    def test_named_snapshots_preserved(self):
        now = datetime.date(2026, 6, 1)
        s_now = SnapshotRecord('now', datetime.date(2026, 6, 1))
        s_named = SnapshotRecord('named', datetime.date(2024, 1, 1), name='Ubuntu 24.04 Fresh Install')
        s_unnamed = SnapshotRecord('unnamed', datetime.date(2024, 1, 1))

        snapshots = [s_now, s_named, s_unnamed]

        policy = RetentionPolicy(
            keep_all_days=0,
            keep_one_per_day=0,
            keep_one_per_week=0,
            keep_one_per_month=0,
            keep_one_per_year=False,
            keep_named=True
        )
        keep, to_delete = calculate_retention(snapshots, policy, now=now)
        self.assertNotIn(s_named, to_delete)
        self.assertIn(s_unnamed, to_delete)
