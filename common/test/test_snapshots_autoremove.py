# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
import inspect
from unittest import mock
from typing import Union
from datetime import date, time, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from test import generic
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config  # noqa: E402,RUF100
import snapshots  # noqa: E402,RUF100


def dt2sidstr(d: Union[date, datetime], t: time = None, tag: int = 123):
    """Create a SID identification string out ouf a date and time infos."""
    if not t:
        try:
            # If d is datetime
            t = d.time()
        except AttributeError:
            t = time(7, 42, 31)

    return datetime.combine(d, t).strftime(f'%Y%m%d-%H%M%S-{tag}')


def dt2str(d: Union[date, datetime]):
    return d.strftime('%a %d %b %Y')


def sid2str(sid):
    """Convert a SID string into human readable date incl. weekday."""

    if isinstance(sid, snapshots.SID):
        sid = str(sid)

    result = datetime.strptime(sid.split('-')[0], '%Y%m%d') \
        .date().strftime('%c').strip()

    if result.endswith(' 00:00:00'):
        result = result[:-9]

    return result


def create_SIDs(start_date: Union[date, datetime, list[date]],
                days: int,
                cfg: config.Config):
    sids = []

    if isinstance(start_date, list):
        the_dates = start_date
    else:
        the_dates = [start_date + timedelta(days=x) for x in range(days)]

    for d in the_dates:
        sids.append(snapshots.SID(dt2sidstr(d), cfg))

    return list(reversed(sids))


class KeepFirst(pyfakefs_ut.TestCase):
    """Test Snapshot.removeKeepFirst().

    PyFakeFS is used here because of Config file dependency."""

    def setUp(self):
        """Setup a fake filesystem."""
        self.setUpPyfakefs(allow_root_user=False)

        # cleanup() happens automatically
        self._temp_dir = TemporaryDirectory(prefix='bit.')
        # Workaround: tempfile and pathlib not compatible yet
        self.temp_path = Path(self._temp_dir.name)

        self._config_fp = self._create_config_file(parent_path=self.temp_path)
        self.cfg = config.Config(str(self._config_fp))

        self.sn = snapshots.Snapshots(self.cfg)

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

    def test_one_but_set(self):
        """Return value is always a set with always only one element."""
        # One SID for each of 20 days beginning with 5th March 2022 07:42:31
        sids = create_SIDs(
            datetime(2020, 3, 5, 7, 42, 31), 700, self.cfg)

        sut = self.sn.smartRemoveKeepFirst(
            sids, date(2021, 8, 5), datetime.now().date())

        self.assertIsInstance(sut, set)
        self.assertTrue(len(sut), 1)

    def test_simple_one(self):
        """First element in a range of SIDs"""
        sids = create_SIDs(
            datetime(2022, 3, 5, 7, 42, 31), 20, self.cfg)

        sut = self.sn.smartRemoveKeepFirst(
            sids, date(2022, 3, 5), datetime.now().date())

        sut = sut.pop()

        self.assertTrue(str(sut).startswith('20220324-074231-'))

    def test_no_date_ordering(self):
        """Hit first in the list and ignoring its date ordering.

        The list of snapshots is not ordered anywhere."""
        sids = []
        # April, 2016...
        for timestamp_string in ['20160424-215134-123',  # …24th
                                 # This SID will hit because it is the first
                                 # in the range specified.
                                 '20160422-030324-123',  # …22th
                                 '20160422-020324-123',  # …22th
                                 '20160422-010324-123',  # …22th
                                 # This might be the earliest/first SID in the
                                 # date range specified but it is not the first
                                 # in the list. So it won't be hit.
                                 '20160421-013218-123',  # …21th
                                 '20160410-134327-123']:  # …10th
            sids.append(snapshots.SID(timestamp_string, self.cfg))

        sut = self.sn.smartRemoveKeepFirst(sids,
                                            date(2016, 4, 20),
                                            date(2016, 4, 23))

        self.assertEqual(str(sut.pop()), '20160422-030324-123')

    def test_keep_first_range_outside(self):
        sids = []
        # April, 2016...
        for timestamp_string in ['20160424-215134-123',  # …24th
                                 '20160422-030324-123',  # …22th
                                 '20160422-020324-123',  # …22th
                                 '20160422-010324-123',  # …22th
                                 '20160421-013218-123',  # …21th
                                 '20160410-134327-123']:  # …10th
            sids.append(snapshots.SID(timestamp_string, self.cfg))

        # Between 11th and 18th April
        sut = self.sn.smartRemoveKeepFirst(sids,
                                           date(2016, 4, 11),
                                           date(2016, 4, 18))

        # None will hit, because no SID in that range.
        self.assertEqual(len(sut), 0)

    @mock.patch.object(snapshots.SID, 'failed', new_callable=lambda: True)
    def test_all_invalid(self, _mock_failed):
        """All SIDS invalid (not healthy)"""
        sids = create_SIDs(
            datetime(2022, 3, 5, 7, 42, 31), 20, self.cfg)

        # By default healthy/invalid status is irrelevant
        sut = self.sn.smartRemoveKeepFirst(
            sids, date(2022, 3, 5), datetime.now().date())
        self.assertTrue(len(sut), 1)

        # Now make it relevant
        sut = self.sn.smartRemoveKeepFirst(
            sids, date(2022, 3, 5), datetime.now().date(),
            keep_healthy=True)
        self.assertTrue(len(sut), 0)

    @mock.patch.object(snapshots.SID, 'failed', new_callable=mock.PropertyMock)
    def test_ignore_unhealthy(self, mock_failed):
        # The second call to failed-property returns True
        mock_failed.side_effect = [False, True, False, False, False, False]
        sids = []
        for timestamp_string in ['20160424-215134-123',
                                 # could be hit, but is NOT healthy
                                 '20160422-030324-123',
                                 # hit this
                                 '20160422-020324-123',
                                 '20160422-010324-123',
                                 '20160421-013218-123',
                                 '20160410-134327-123']:
            sids.append(snapshots.SID(timestamp_string, self.cfg))

        # keep the first healthy snapshot
        sut = self.sn.smartRemoveKeepFirst(sids,
                                           date(2016, 4, 20),
                                           date(2016, 4, 23),
                                           keep_healthy=True)
        self.assertEqual(str(sut.pop()), '20160422-020324-123')


class KeepAll(pyfakefs_ut.TestCase):
    """Test Snapshot.removeKeepAll().

    PyFakeFS is used here because of Config file dependency."""

    def setUp(self):
        """Setup a fake filesystem."""
        self.setUpPyfakefs(allow_root_user=False)

        # cleanup() happens automatically
        self._temp_dir = TemporaryDirectory(prefix='bit.')
        # Workaround: tempfile and pathlib not compatible yet
        self.temp_path = Path(self._temp_dir.name)

        self._config_fp = self._create_config_file(parent_path=self.temp_path)
        self.cfg = config.Config(str(self._config_fp))

        self.sn = snapshots.Snapshots(self.cfg)

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

    def test_simple(self):
        """Simple"""
        # 10th to 25th
        sids = create_SIDs(datetime(2024, 2, 10), 15, self.cfg)

        # keep...
        sut = self.sn.smartRemoveKeepAll(
            sids,
            # ... from 12th ...
            date(2024, 2, 12),
            # ... to 19th.
            date(2024, 2, 20)
        )

        self.assertEqual(len(sut), 8)

        sut = sorted(sut)

        self.assertEqual(sut[0].date.date(), date(2024, 2, 12))
        self.assertEqual(sut[1].date.date(), date(2024, 2, 13))
        self.assertEqual(sut[2].date.date(), date(2024, 2, 14))
        self.assertEqual(sut[3].date.date(), date(2024, 2, 15))
        self.assertEqual(sut[4].date.date(), date(2024, 2, 16))
        self.assertEqual(sut[5].date.date(), date(2024, 2, 17))
        self.assertEqual(sut[6].date.date(), date(2024, 2, 18))
        self.assertEqual(sut[7].date.date(), date(2024, 2, 19))


# class OnePerWeek(pyfakefs_ut.TestCase):
#     """Covering the smart remove setting 'Keep one snapshot per week for the
#     last N weeks'.

#     That logic is implemented in 'Snapshots.smartRemoveList()' but not testable
#     in isolation. So for a first shot we just duplicate that code in this
#     tests (see self._org()).
#     """

#     def setUp(self):
#         """Setup a fake filesystem."""
#         self.setUpPyfakefs(allow_root_user=False)

#         # cleanup() happens automatically
#         self._temp_dir = TemporaryDirectory(prefix='bit.')
#         # Workaround: tempfile and pathlib not compatible yet
#         self.temp_path = Path(self._temp_dir.name)

#         self._config_fp = self._create_config_file(parent_path=self.temp_path)
#         self.cfg = config.Config(str(self._config_fp))

#         self.sn = snapshots.Snapshots(self.cfg)

#     def _create_config_file(self, parent_path):
#         """Minimal config file"""
#         # pylint: disable-next=R0801
#         cfg_content = inspect.cleandoc('''
#             config.version=6
#             profile1.snapshots.include.1.type=0
#             profile1.snapshots.include.1.value=rootpath/source
#             profile1.snapshots.include.size=1
#             profile1.snapshots.no_on_battery=false
#             profile1.snapshots.notify.enabled=true
#             profile1.snapshots.path=rootpath/destination
#             profile1.snapshots.path.host=test-host
#             profile1.snapshots.path.profile=1
#             profile1.snapshots.path.user=test-user
#             profile1.snapshots.preserve_acl=false
#             profile1.snapshots.preserve_xattr=false
#             profile1.snapshots.remove_old_snapshots.enabled=true
#             profile1.snapshots.remove_old_snapshots.unit=80
#             profile1.snapshots.remove_old_snapshots.value=10
#             profile1.snapshots.rsync_options.enabled=false
#             profile1.snapshots.rsync_options.value=
#             profiles.version=1
#         ''')

#         # config file location
#         config_fp = parent_path / 'config_path' / 'config'
#         config_fp.parent.mkdir()
#         config_fp.write_text(cfg_content, 'utf-8')

#         return config_fp

#     def _org(self, now, n_weeks, snapshots, keep_healthy=True):
#         """Keep one per week for the last n_weeks weeks.

#         Copied and slightly refactored from inside
#         'Snapshots.smartRemoveList()'.
#         """
#         print(f'\n_org() :: now={dt2str(now)} {n_weeks=}')
#         keep = set()

#         # Sunday ??? (Sonntag) of previous week
#         idx_date = now - timedelta(days=now.weekday() + 1)

#         print(f'  for-loop... idx_date={dt2str(idx_date)}')
#         for _ in range(0, n_weeks):

#             min_date = idx_date
#             max_date = idx_date + timedelta(days=7)

#             print(f'    from {dt2str(min_date)} to/before {dt2str(max_date)}')
#             keep |= self.sn.smartRemoveKeepFirst(
#                 snapshots,
#                 min_date,
#                 max_date,
#                 keep_healthy=keep_healthy)
#             print(f'       {keep=}')

#             idx_date -= timedelta(days=7)
#             print(f'    new idx_date={dt2str(idx_date)}')
#         print('  ...end loop')

#         return keep

#     def test_foobar(self):
#         # start = date(2022, 1, 15)
#         now = date(2024, 11, 26)
#         # sids = create_SIDs(start, 9*7+3, self.cfg)
#         sids = create_SIDs(
#             [
#                 date(2024, 11, 2),
#                 date(2024, 11, 9),
#                 date(2024, 11, 16),
#                 date(2024, 11, 23),
#                 # date(2024, 11, 25)
#             ],
#             None,
#             self.cfg
#         )

#         weeks = 3
#         sut = self._org(
#             # "Today" is Thursday 28th March
#             now=now,
#             # Keep the last week
#             n_weeks=weeks,
#             snapshots=sids)

#         print(f'\noldest snapshot: {sid2str(sids[0])}')
#         for s in sorted(sut):
#             print(f'keep: {sid2str(s)}')
#         print(f'from/now: {dt2str(now)}  {weeks=}')
#         print(f'latest snapshot: {sid2str(sids[-1])}')

#     def test_sunday_last_week(self):
#         """Keep sunday of the last week."""
#         # 9 backups: 18th (Monday) -  26th (Thursday) March 2024
#         sids = create_SIDs(date(2024, 3, 18), 9, self.cfg)

#         sut = self._org(
#             # "Today" is Thursday 28th March
#             now=date(2024, 3, 28),
#             # Keep the last week
#             n_weeks=1,
#             snapshots=sids)

#         # only one kept
#         self.assertTrue(len(sut), 1)
#         # Sunday March 24th
#         self.assertTrue(str(sut.pop()).startswith('20240324-'))

#     def test_three_weeks(self):
#         """Keep sunday of the last 3 weeks and throw away the rest."""

#         # 6 Weeks of backups (2024-02-18 - 2024-03-30)
#         sids = create_SIDs(datetime(2024, 2, 18), 7*6, self.cfg)
#         print(f'{str(sids[0])=} {str(sids[-1])=}')

#         sut = self._org(
#             # "Today" is Thursday 28th March
#             now=date(2024, 3, 28),
#             # Keep the last week
#             n_weeks=3,
#             snapshots=sids)

#         # only one kept
#         self.assertTrue(len(sut), 3)
#         sut = sorted(sut)
#         for s in sut:
#             print(s)


# class ForLastNDays(pyfakefs_ut.TestCase):
#     """Covering the smart remove setting 'Keep one per day for N days.'.

#     That logic is implemented in 'Snapshots.smartRemoveList()' but not testable
#     in isolation. So for a first shot we just duplicate that code in this
#     tests (see self._org()).
#     """

#     def setUp(self):
#         """Setup a fake filesystem."""
#         self.setUpPyfakefs(allow_root_user=False)

#         # cleanup() happens automatically
#         self._temp_dir = TemporaryDirectory(prefix='bit.')
#         # Workaround: tempfile and pathlib not compatible yet
#         self.temp_path = Path(self._temp_dir.name)

#         self._config_fp = self._create_config_file(parent_path=self.temp_path)
#         self.cfg = config.Config(str(self._config_fp))

#         self.sn = snapshots.Snapshots(self.cfg)

#     def _create_config_file(self, parent_path):
#         """Minimal config file"""
#         # pylint: disable-next=R0801
#         cfg_content = inspect.cleandoc('''
#             config.version=6
#             profile1.snapshots.include.1.type=0
#             profile1.snapshots.include.1.value=rootpath/source
#             profile1.snapshots.include.size=1
#             profile1.snapshots.no_on_battery=false
#             profile1.snapshots.notify.enabled=true
#             profile1.snapshots.path=rootpath/destination
#             profile1.snapshots.path.host=test-host
#             profile1.snapshots.path.profile=1
#             profile1.snapshots.path.user=test-user
#             profile1.snapshots.preserve_acl=false
#             profile1.snapshots.preserve_xattr=false
#             profile1.snapshots.remove_old_snapshots.enabled=true
#             profile1.snapshots.remove_old_snapshots.unit=80
#             profile1.snapshots.remove_old_snapshots.value=10
#             profile1.snapshots.rsync_options.enabled=false
#             profile1.snapshots.rsync_options.value=
#             profiles.version=1
#         ''')

#         # config file location
#         config_fp = parent_path / 'config_path' / 'config'
#         config_fp.parent.mkdir()
#         config_fp.write_text(cfg_content, 'utf-8')

#         return config_fp

#     def _org(self, now, n_days, snapshots):
#         """Copied and slightly refactored from inside
#         'Snapshots.smartRemoveList()'.
#         """
#         print(f'\n_org() :: now={dt2str(now)} {n_days=}')

#         keep = self.sn.smartRemoveKeepAll(
#             snapshots,
#             now - timedelta(days=n_days-1),
#             now + timedelta(days=1))

#         return keep

#     def test_foobar(self):
#         sids = create_SIDs(datetime(2024, 2, 18), 10, self.cfg)
#         sut = self._org(now=date(2024, 2, 27),
#                         n_days=3,
#                         snapshots=sids)

#         self.assertEqual(len(sut), 3)

#         sut = sorted(sut)

#         self.assertEqual(sut[0].date.date(), date(2024, 2, 25))
#         self.assertEqual(sut[1].date.date(), date(2024, 2, 26))
#         self.assertEqual(sut[2].date.date(), date(2024, 2, 27))


# class OnePerMonth(pyfakefs_ut.TestCase):
#     """Covering the smart remove setting 'Keep one snapshot per week for the
#     last N weeks'.

#     That logic is implemented in 'Snapshots.smartRemoveList()' but not testable
#     in isolation. So for a first shot we just duplicate that code in this
#     tests (see self._org()).
#     """

#     def setUp(self):
#         """Setup a fake filesystem."""
#         self.setUpPyfakefs(allow_root_user=False)

#         # cleanup() happens automatically
#         self._temp_dir = TemporaryDirectory(prefix='bit.')
#         # Workaround: tempfile and pathlib not compatible yet
#         self.temp_path = Path(self._temp_dir.name)

#         self._config_fp = self._create_config_file(parent_path=self.temp_path)
#         self.cfg = config.Config(str(self._config_fp))

#         self.sn = snapshots.Snapshots(self.cfg)

#     def _create_config_file(self, parent_path):
#         """Minimal config file"""
#         # pylint: disable-next=R0801
#         cfg_content = inspect.cleandoc('''
#             config.version=6
#             profile1.snapshots.include.1.type=0
#             profile1.snapshots.include.1.value=rootpath/source
#             profile1.snapshots.include.size=1
#             profile1.snapshots.no_on_battery=false
#             profile1.snapshots.notify.enabled=true
#             profile1.snapshots.path=rootpath/destination
#             profile1.snapshots.path.host=test-host
#             profile1.snapshots.path.profile=1
#             profile1.snapshots.path.user=test-user
#             profile1.snapshots.preserve_acl=false
#             profile1.snapshots.preserve_xattr=false
#             profile1.snapshots.remove_old_snapshots.enabled=true
#             profile1.snapshots.remove_old_snapshots.unit=80
#             profile1.snapshots.remove_old_snapshots.value=10
#             profile1.snapshots.rsync_options.enabled=false
#             profile1.snapshots.rsync_options.value=
#             profiles.version=1
#         ''')

#         # config file location
#         config_fp = parent_path / 'config_path' / 'config'
#         config_fp.parent.mkdir()
#         config_fp.write_text(cfg_content, 'utf-8')

#         return config_fp

#     def _org(self, now, n_months, snapshots, keep_healthy=True):
#         """Keep one per months for the last n_months weeks.

#         Copied and slightly refactored from inside
#         'Snapshots.smartRemoveList()'.
#         """
#         print(f'\n_org() :: now={dt2str(now)} {n_months=}')
#         keep = set()

#         d1 = date(now.year, now.month, 1)
#         d2 = self.sn.incMonth(d1)

#         # each months
#         for i in range(0, n_months):
#             print(f'{i=} {d1=} {d2}')
#             keep |= self.sn.smartRemoveKeepFirst(
#                 snapshots, d1, d2, keep_healthy=keep_healthy)
#             d2 = d1
#             d1 = self.sn.decMonth(d1)

#         return keep

#     def test_foobarm(self):
#         now = date(2024, 12, 16)
#         # sids = create_SIDs(start, 9*7+3, self.cfg)
#         sids = create_SIDs(date(2023, 10, 26), 500, self.cfg)

#         months = 3
#         sut = self._org(
#             now=now,
#             # Keep the last week
#             n_months=months,
#             snapshots=sids)

#         print(f'\noldest snapshot: {sid2str(sids[0])}')
#         for s in sorted(sut):
#             print(f'keep: {sid2str(s)}')
#         print(f'from/now: {dt2str(now)}  {months=}')
#         print(f'latest snapshot: {sid2str(sids[-1])}')


# class OnePerYear(pyfakefs_ut.TestCase):
#     """Covering the smart remove setting 'Keep one snapshot per year for all
#     years.'

#     That logic is implemented in 'Snapshots.smartRemoveList()' but not testable
#     in isolation. So for a first shot we just duplicate that code in this
#     tests (see self._org()).
#     """

#     def setUp(self):
#         """Setup a fake filesystem."""
#         self.setUpPyfakefs(allow_root_user=False)

#         # cleanup() happens automatically
#         self._temp_dir = TemporaryDirectory(prefix='bit.')
#         # Workaround: tempfile and pathlib not compatible yet
#         self.temp_path = Path(self._temp_dir.name)

#         self._config_fp = self._create_config_file(parent_path=self.temp_path)
#         self.cfg = config.Config(str(self._config_fp))

#         self.sn = snapshots.Snapshots(self.cfg)

#     def _create_config_file(self, parent_path):
#         """Minimal config file"""
#         # pylint: disable-next=R0801
#         cfg_content = inspect.cleandoc('''
#             config.version=6
#             profile1.snapshots.include.1.type=0
#             profile1.snapshots.include.1.value=rootpath/source
#             profile1.snapshots.include.size=1
#             profile1.snapshots.no_on_battery=false
#             profile1.snapshots.notify.enabled=true
#             profile1.snapshots.path=rootpath/destination
#             profile1.snapshots.path.host=test-host
#             profile1.snapshots.path.profile=1
#             profile1.snapshots.path.user=test-user
#             profile1.snapshots.preserve_acl=false
#             profile1.snapshots.preserve_xattr=false
#             profile1.snapshots.remove_old_snapshots.enabled=true
#             profile1.snapshots.remove_old_snapshots.unit=80
#             profile1.snapshots.remove_old_snapshots.value=10
#             profile1.snapshots.rsync_options.enabled=false
#             profile1.snapshots.rsync_options.value=
#             profiles.version=1
#         ''')

#         # config file location
#         config_fp = parent_path / 'config_path' / 'config'
#         config_fp.parent.mkdir()
#         config_fp.write_text(cfg_content, 'utf-8')

#         return config_fp

#     def _org(self, now, snapshots, keep_healthy=True):
#         """Keep one per year

#         Copied and slightly refactored from inside
#         'Snapshots.smartRemoveList()'.
#         """
#         first_year = int(snapshots[-1].sid[:4])

#         print(f'\n_org() :: now={dt2str(now)} {first_year=}')
#         keep = set()

#         for i in range(first_year, now.year+1):
#             keep |= self.sn.smartRemoveKeepFirst(
#                 snapshots,
#                 date(i, 1, 1),
#                 date(i+1, 1, 1),
#                 keep_healthy=keep_healthy)

#         return keep

#     def test_foobary(self):
#         now = date(2024, 12, 16)
#         # sids = create_SIDs(start, 9*7+3, self.cfg)
#         sids = create_SIDs(date(2019, 10, 26), 365*6, self.cfg)

#         sut = self._org(
#             now=now,
#             snapshots=sids)

#         print(f'\noldest snapshot: {sid2str(sids[0])}')
#         for s in sorted(sut):
#             print(f'keep: {sid2str(s)}')
#         print(f'from/now: {dt2str(now)}')
#         print(f'latest snapshot: {sid2str(sids[-1])}')


class IncDecMonths(pyfakefs_ut.TestCase):
    """PyFakeFS is used here because of Config file dependency."""

    def setUp(self):
        """Setup a fake filesystem."""
        self.setUpPyfakefs(allow_root_user=False)

        # cleanup() happens automatically
        self._temp_dir = TemporaryDirectory(prefix='bit.')
        # Workaround: tempfile and pathlib not compatible yet
        self.temp_path = Path(self._temp_dir.name)

        self._config_fp = self._create_config_file(parent_path=self.temp_path)
        self.cfg = config.Config(str(self._config_fp))

        self.sn = snapshots.Snapshots(self.cfg)

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

    def test_inc_simple(self):
        sut = self.sn.incMonth(date(1982, 8, 6))
        self.assertEqual(sut, date(1982, 9, 1))

    def test_inc_next_year(self):
        sut = self.sn.incMonth(date(1982, 12, 16))
        self.assertEqual(sut, date(1983, 1, 1))

    def test_inc_leap_year(self):
        sut = self.sn.incMonth(date(2020, 12, 16))
        self.assertEqual(sut, date(2021, 1, 1))

    def test_inc_leap_months(self):
        sut = self.sn.incMonth(date(2020, 2, 29))
        self.assertEqual(sut, date(2020, 3, 1))

    def test_dec_simple(self):
        sut = self.sn.decMonth(date(1982, 8, 6))
        self.assertEqual(sut, date(1982, 7, 1))

    def test_dec_year(self):
        sut = self.sn.decMonth(date(1982, 1, 6))
        self.assertEqual(sut, date(1981, 12, 1))

    def test_dec_leap_months(self):
        sut = self.sn.decMonth(date(2020, 2, 29))
        self.assertEqual(sut, date(2020, 1, 1))


class OldOrg_SmartRemove(generic.SnapshotsTestCase):
    """This is the old/original test case using real filesystem and to much
    dependencies."""

    def test_keep_all(self):
        sid1 = snapshots.SID('20160424-215134-123', self.cfg)
        sid2 = snapshots.SID('20160422-030324-123', self.cfg)
        sid3 = snapshots.SID('20160422-020324-123', self.cfg)
        sid4 = snapshots.SID('20160422-010324-123', self.cfg)
        sid5 = snapshots.SID('20160421-013218-123', self.cfg)
        sid6 = snapshots.SID('20160410-134327-123', self.cfg)
        sids = [sid1, sid2, sid3, sid4, sid5, sid6]

        keep = self.sn.smartRemoveKeepAll(sids,
                                               date(2016, 4, 20),
                                               date(2016, 4, 23))
        self.assertSetEqual(keep, set((sid2, sid3, sid4, sid5)))

        keep = self.sn.smartRemoveKeepAll(sids,
                                               date(2016, 4, 11),
                                               date(2016, 4, 18))
        self.assertSetEqual(keep, set())

    def test_smart_remove_list(self):
        sid1  = snapshots.SID('20160424-215134-123', self.cfg)
        sid2  = snapshots.SID('20160422-030324-123', self.cfg)
        sid3  = snapshots.SID('20160422-020324-123', self.cfg)
        sid4  = snapshots.SID('20160422-010324-123', self.cfg)
        sid5  = snapshots.SID('20160421-033218-123', self.cfg)
        sid6  = snapshots.SID('20160421-013218-123', self.cfg)
        sid7  = snapshots.SID('20160420-013218-123', self.cfg)
        sid8  = snapshots.SID('20160419-013218-123', self.cfg)
        sid9  = snapshots.SID('20160419-003218-123', self.cfg)
        sid10 = snapshots.SID('20160418-003218-123', self.cfg)
        sid11 = snapshots.SID('20160417-033218-123', self.cfg)
        sid12 = snapshots.SID('20160417-003218-123', self.cfg)
        sid13 = snapshots.SID('20160416-134327-123', self.cfg)
        sid14 = snapshots.SID('20160416-114327-123', self.cfg)
        sid15 = snapshots.SID('20160415-134327-123', self.cfg)
        sid16 = snapshots.SID('20160411-134327-123', self.cfg)
        sid17 = snapshots.SID('20160410-134327-123', self.cfg)
        sid18 = snapshots.SID('20160409-134327-123', self.cfg)
        sid19 = snapshots.SID('20160407-134327-123', self.cfg)
        sid20 = snapshots.SID('20160403-134327-123', self.cfg)
        sid21 = snapshots.SID('20160402-134327-123', self.cfg)
        sid22 = snapshots.SID('20160401-134327-123', self.cfg)
        sid23 = snapshots.SID('20160331-134327-123', self.cfg)
        sid24 = snapshots.SID('20160330-134327-123', self.cfg)
        sid25 = snapshots.SID('20160323-133715-123', self.cfg)
        sid26 = snapshots.SID('20160214-134327-123', self.cfg)
        sid27 = snapshots.SID('20160205-134327-123', self.cfg)
        sid28 = snapshots.SID('20160109-134327-123', self.cfg)
        sid29 = snapshots.SID('20151224-134327-123', self.cfg)
        sid30 = snapshots.SID('20150904-134327-123', self.cfg)
        sid31 = snapshots.SID('20140904-134327-123', self.cfg)

        sids = [       sid1,  sid2,  sid3,  sid4,  sid5,  sid6,  sid7,  sid8,  sid9,
                sid10, sid11, sid12, sid13, sid14, sid15, sid16, sid17, sid18, sid19,
                sid20, sid21, sid22, sid23, sid24, sid25, sid26, sid27, sid28, sid29,
                sid30, sid31]
        for sid in sids:
            sid.makeDirs()
        now = datetime(2016, 4, 24, 21, 51, 34)

        del_snapshots = self.sn.smartRemoveList(now,
                                                3, #keep_all
                                                7, #keep_one_per_day
                                                5, #keep_one_per_week
                                                3  #keep_one_per_month
                                                )
        self.assertListEqual(del_snapshots, [sid6, sid9, sid12, sid13, sid14,
                                             sid15, sid16, sid18, sid19, sid21,
                                             sid22, sid24, sid27, sid28, sid30])

        # test failed snapshots
        for sid in (sid5, sid8, sid11, sid12, sid20, sid21, sid22):
            sid.failed = True
        del_snapshots = self.sn.smartRemoveList(now,
                                                3, #keep_all
                                                7, #keep_one_per_day
                                                5, #keep_one_per_week
                                                3  #keep_one_per_month
                                                )
        self.assertListEqual(del_snapshots, [sid5, sid8, sid11, sid12, sid14,
                                             sid15, sid16, sid18, sid19, sid20, sid21,
                                             sid22, sid24, sid27, sid28, sid30])
