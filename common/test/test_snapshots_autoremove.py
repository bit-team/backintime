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
"""Tests related to Remove & Retention, formally known as Auto- and
Smart-remove.

About the current state of this test module:

    Most of the tests in this module are pseudo-tests. The do not test
    productive code but surrogates (e.g. method name `_org()` in each class).
    Because the productive code is in an untestable state and needs refactoring
    or totally rewrite. This is on the projects todo list. See meta issue
    #1945.
"""
import os
import sys
import inspect
from unittest import mock
from typing import Union
from datetime import date, time, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
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

    return sorted(sids, reverse=True)


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

    def test_min_included_max_not(self):
        """Minimum date is included in range, but max date not"""
        sids = create_SIDs(
            [
                datetime(2022, 3, 5),
                datetime(2022, 3, 3),
            ],
            None,
            self.cfg)

        sut = self.sn.smartRemoveKeepFirst(
            snapshots=sids,
            min_date=date(2022, 3, 3),
            max_date=date(2022, 3, 5),
        )

        self.assertEqual(len(sut), 1)

        sut = sut.pop()

        # the min_date is included
        self.assertEqual(sut.date.date(), date(2022, 3, 3))

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
        """No SID inside the specified range"""
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


class KeepAllForLast(pyfakefs_ut.TestCase):
    """Test Snapshot.removeKeepAll().

    Keep all snapshots for the last N days.
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

    def _org(self, snapshots, now, days_to_keep):
        """Simulated production code. Refactoring is on the todo list."""

        keep_all = days_to_keep
        keep = self.sn.smartRemoveKeepAll(
            snapshots,
            now - timedelta(days=keep_all-1),
            now + timedelta(days=1))

        return sorted(keep, reverse=True)

    def test_border(self):
        """The dates used in the user manual example.

        Here the current (just running incomplete) day is contained in the
        calculation.
        """
        sids = create_SIDs([
            datetime(2025, 4, 17, 22, 0),
            datetime(2025, 4, 17, 18, 1),
            datetime(2025, 4, 17, 12, 0),
            datetime(2025, 4, 17, 4, 0),
            datetime(2025, 4, 16, 8, 30),
            datetime(2025, 4, 15, 16, 0),
            datetime(2025, 4, 15, 0, 0),
            datetime(2025, 4, 14, 23, 59),
            datetime(2025, 4, 14, 9, 0),
            ],
            None,
            self.cfg)

        sut = self._org(
            snapshots=sids,
            now=datetime(2025, 4, 17, 22, 00).date(),
            days_to_keep=2)

        self.assertEqual(sut[0].date, datetime(2025, 4, 17, 22, 0))
        self.assertEqual(sut[1].date, datetime(2025, 4, 17, 18, 1))
        self.assertEqual(sut[2].date, datetime(2025, 4, 17, 12, 0))
        self.assertEqual(sut[3].date, datetime(2025, 4, 17, 4, 0))
        self.assertEqual(sut[4].date, datetime(2025, 4, 16, 8, 30))

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


class KeepOneForLastNDays(pyfakefs_ut.TestCase):
    """Covering the smart remove setting 'Keep the last snapshot of each day
    for the last N  days.'.

    That logic is implemented in 'Snapshots.smartRemoveList()' but not testable
    in isolation. So for a first shot we just duplicate that code in this
    tests (see self._org()).
    """

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

    def _org(self, now, n_days, snapshots):
        """Copied and slightly refactored from inside
        'Snapshots.smartRemoveList()'.
        """

        keep = set()
        d = now
        for _ in range(0, n_days):
            keep |= self.sn.smartRemoveKeepFirst(
                snapshots,
                d,
                d + timedelta(days=1),
                keep_healthy=True)
            d -= timedelta(days=1)

        return sorted(keep, reverse=True)

    def test_doc_example(self):
        sids = create_SIDs([
            datetime(2025, 4, 17, 22, 0),
            datetime(2025, 4, 17, 4, 0),
            datetime(2025, 4, 16, 8, 30),
            datetime(2025, 4, 15, 16, 0),
            datetime(2025, 4, 15, 0, 0),
            datetime(2025, 4, 14, 23, 59),
            datetime(2025, 4, 13, 19, 0),
            datetime(2025, 4, 13, 7, 0),
            datetime(2025, 4, 12, 18, 45),
            datetime(2025, 4, 12, 18, 5),
            datetime(2025, 4, 11, 9, 0),
            ],
            None,
            self.cfg)

        sut = self._org(
            now=date(2025, 4, 17),
            n_days=5,
            snapshots=sids)

        self.assertEqual(sut[0].date, datetime(2025, 4, 17, 22, 0))
        self.assertEqual(sut[1].date, datetime(2025, 4, 16, 8, 30))
        self.assertEqual(sut[2].date, datetime(2025, 4, 15, 16, 0))
        self.assertEqual(sut[3].date, datetime(2025, 4, 14, 23, 59))
        self.assertEqual(sut[4].date, datetime(2025, 4, 13, 19, 0))


class KeepOneForLastNWeeks(pyfakefs_ut.TestCase):
    """Covering the smart remove setting 'Keep the last snapshot for each week for the
    last N weeks'.

    That logic is implemented in 'Snapshots.smartRemoveList()' but not testable
    in isolation. So for a first shot we just duplicate that code in this
    tests (see self._org()).
    """

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

    def _org(self, now, n_weeks, snapshots, keep_healthy=True):
        """Keep one per week for the last n_weeks weeks.

        Copied and slightly refactored from inside
        'Snapshots.smartRemoveList()'.
        """
        keep = set()

        # Sunday ??? (Sonntag) of previous week
        idx_date = now - timedelta(days=now.weekday())

        for _ in range(0, n_weeks):

            min_date = idx_date
            max_date = idx_date + timedelta(days=7)

            keep |= self.sn.smartRemoveKeepFirst(
                snapshots,
                min_date,
                max_date,
                keep_healthy=keep_healthy)

            idx_date -= timedelta(days=7)

        return sorted(keep, reverse=True)

    def test_doc_example(self):
        """Example used in manual"""
        sids = create_SIDs(
            [
                # 5 Weeks, each 3 days
                datetime(2025, 4, 17, 22, 0),
                datetime(2025, 4, 16, 4, 0),
                datetime(2025, 4, 15, 14, 0),
                datetime(2025, 4, 13, 22, 0),
                datetime(2025, 4, 9, 4, 0),
                datetime(2025, 4, 8, 14, 0),
                datetime(2025, 4, 3, 22, 0),
                datetime(2025, 4, 2, 4, 0),
                datetime(2025, 4, 1, 14, 0),
                datetime(2025, 3, 27, 22, 0),
                datetime(2025, 3, 26, 4, 0),
                datetime(2025, 3, 24, 14, 0),
                datetime(2025, 3, 20, 22, 0),
                datetime(2025, 3, 19, 4, 0),
                datetime(2025, 3, 18, 14, 0)
            ],
            None,
            self.cfg
        )

        sut = self._org(
            now=date(2025, 4, 17),
            n_weeks=4,
            snapshots=sids)

        self.assertEqual(sut[0].date, datetime(2025, 4, 17, 22, 0))
        self.assertEqual(sut[1].date, datetime(2025, 4, 13, 22, 0))
        self.assertEqual(sut[2].date, datetime(2025, 4, 3, 22, 0))
        self.assertEqual(sut[3].date, datetime(2025, 3, 27, 22, 0))
        self.assertEqual(len(sut), 4)


class KeepOneForLastNMonths(pyfakefs_ut.TestCase):
    """Covering the smart remove setting 'Keep the last snapshot for each month
    for the last N months'.

    That logic is implemented in 'Snapshots.smartRemoveList()' but not testable
    in isolation. So for a first shot we just duplicate that code in this
    tests (see self._org()).

    """

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

    def _org(self, now, n_months, snapshots, keep_healthy=True):
        """Keep one per months for the last n_months months.

        Copied and slightly refactored from inside
        'Snapshots.smartRemoveList()'.
        """
        keep = set()

        d1 = date(now.year, now.month, 1)
        d2 = self.sn.incMonth(d1)

        # each months
        for _ in range(0, n_months):
            keep |= self.sn.smartRemoveKeepFirst(
                snapshots, d1, d2, keep_healthy=keep_healthy)
            d2 = d1
            d1 = self.sn.decMonth(d1)

        return sorted(keep, reverse=True)

    def test_doc_example(self):
        sids = create_SIDs(
            [
                # 10 months period
                date(2025, 8, 18),
                date(2025, 8, 6),
                date(2025, 7, 31),
                date(2025, 7, 1),
                date(2025, 6, 30),
                date(2025, 6, 1),
                # gap of 2 months
                date(2025, 3, 18),
                date(2025, 2, 9),
                date(2025, 1, 6),
                date(2024, 12, 26),
                date(2024, 11, 14),
            ],
            None,
            self.cfg
        )
        now = sids[0].date.date() + timedelta(days=5)

        months = 6
        sut = self._org(
            now=now,
            # Keep the last week
            n_months=months,
            snapshots=sids)

        expect = [
            date(2025, 8, 18),
            date(2025, 7, 31),
            date(2025, 6, 30),
            date(2025, 3, 18),
        ]
        self.assertEqual(len(sut), len(expect))
        for idx, expect_date in enumerate(expect):
            self.assertEqual(sut[idx].date.date(), expect_date)


class KeepOnePerYearForAllYears(pyfakefs_ut.TestCase):
    """Covering the smart remove setting 'Keep the last snapshot for each year
    for all years.'

    That logic is implemented in 'Snapshots.smartRemoveList()' but not testable
    in isolation. So for a first shot we just duplicate that code in this
    tests (see self._org()).
    """

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

    def _org(self, now, snapshots, keep_healthy=True):
        """Keep one per year

        Copied and slightly refactored from inside
        'Snapshots.smartRemoveList()'.
        """
        first_year = int(snapshots[-1].sid[:4])

        keep = set()

        for i in range(first_year, now.year+1):
            keep |= self.sn.smartRemoveKeepFirst(
                snapshots,
                date(i, 1, 1),
                date(i+1, 1, 1),
                keep_healthy=keep_healthy)

        return sorted(keep, reverse=True)

    def test_doc_example(self):
        now = date(2024, 12, 16)
        sids = create_SIDs(
            [
                date(2024, 10, 26),
                date(2024, 4, 13),
                date(2023, 10, 26),
                date(2023, 10, 8),
                date(2023, 1, 1),
                date(2022, 12, 31),
                date(2022, 4, 13),
                date(2020, 10, 26),
                date(2020, 4, 13),
            ],
            None,
            self.cfg
        )

        sut = self._org(
            now=now,
            snapshots=sids)

        expect = [
            date(2024, 10, 26),
            date(2023, 10, 26),
            date(2022, 12, 31),
            date(2020, 10, 26),
        ]
        self.assertEqual(len(sut), len(expect))
        for idx, expect_date in enumerate(expect):
            self.assertTrue(sut[idx].date.date(), expect_date)


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
