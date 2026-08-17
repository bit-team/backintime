# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raack
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about the tools module."""
import os
import sys
import subprocess
import random
import pathlib
import stat
import signal
import unittest
from io import StringIO
from datetime import datetime
from time import sleep
from unittest.mock import patch
from tempfile import NamedTemporaryFile, TemporaryDirectory
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import tools
from bitbase import TimeUnit
from event import Event

# chroot jails used for building may have no UUID devices (because of tmpfs)
# we need to skip tests that require UUIDs
DISK_BY_UUID_AVAILABLE = os.path.exists(tools.DISK_BY_UUID)

UDEVADM_HAS_UUID = subprocess.Popen(
    ['udevadm', 'info', '-e'],
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL).communicate()[0].find(b'ID_FS_UUID=') > 0


class Basics(unittest.TestCase):
    def test_as_backintime_path(self):
        path = tools.as_backintime_path('common')
        self.assertIn(path, __file__)

    def test_register_backintime_path(self):
        path = tools.as_backintime_path('foo')
        tools.register_backintime_path('foo')

        self.assertIn(path, sys.path)
        sys.path.remove(path)

    def test_which(self):
        self.assertRegex(tools.which('ls'), r'/.*/ls')

        self.assertEqual(tools.which('backintime'),
                         os.path.join(os.getcwd(), 'backintime'))

        self.assertIsNone(tools.which('notExistedCommand'))

    def test_makeDirs(self):
        self.assertFalse(tools.makeDirs('/'))
        self.assertTrue(tools.makeDirs(os.getcwd()))
        with TemporaryDirectory() as d:
            path = os.path.join(d, 'foo', 'bar')
            self.assertTrue(tools.makeDirs(path))

    def test_makeDirs_not_writable(self):
        with TemporaryDirectory() as d:
            os.chmod(d, stat.S_IRUSR)
            path = os.path.join(
                d, 'foobar{}'.format(random.randrange(100, 999)))
            self.assertFalse(tools.makeDirs(path))

    def test_mkdir(self):
        self.assertFalse(tools.mkdir('/'))
        with TemporaryDirectory() as d:
            path = os.path.join(d, 'foo')
            self.assertTrue(tools.mkdir(path))
            for mode in (0o700, 0o644, 0o777):
                msg = 'new path should have octal permissions {0:#o}' \
                      .format(mode)
                path = os.path.join(d, '{0:#o}'.format(mode))
                self.assertTrue(tools.mkdir(path, mode), msg)
                self.assertEqual(
                    '{0:o}'.format(os.stat(path).st_mode & 0o777),
                    '{0:o}'.format(mode), msg)


class General(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.subproc = None

    def tearDown(self):
        super().tearDown()
        self._kill_process()

    def _create_process(self, *args):
        dummyPath = os.path.join(os.path.dirname(__file__), generic.DUMMY)
        cmd = [dummyPath]
        cmd.extend(args)
        self.subproc = subprocess.Popen(cmd)
        sleep(0.1)
        return self.subproc.pid

    def _kill_process(self):
        if self.subproc:
            self.subproc.kill()
            self.subproc.wait()
        self.subproc = None

    def test_sharePath(self):
        share = tools.sharePath()
        self.assertTrue(share.endswith('share'), 'share = {}'.format(share))

    def test_runningFromSource(self):
        self.assertTrue(tools.runningFromSource())

    def test_addSourceToPathEnviron(self):
        source = tools.as_backintime_path('common')
        path = [x for x in os.getenv('PATH').split(':') if x != source]
        os.environ['PATH'] = ':'.join(path)

        tools.addSourceToPathEnviron()
        self.assertIn(source, os.environ['PATH'])

    def test_processStat(self):
        pid = self._create_process()
        stat = tools.processStat(pid)
        self.assertRegex(
            stat, r'{} \({}\) \w .*'.format(pid, generic.DUMMY[:15]))

    @patch('builtins.open')
    def test_processStat_exception(self, mock_open):
        mock_open.side_effect = OSError()
        pid = self._create_process()
        self.assertEqual(tools.processStat(pid), '')

    def test_processPaused(self):
        pid = self._create_process()
        self.assertFalse(tools.processPaused(pid))
        self.subproc.send_signal(signal.SIGSTOP)
        sleep(0.01)
        self.assertTrue(tools.processPaused(pid))
        self.subproc.send_signal(signal.SIGCONT)
        sleep(0.01)
        self.assertFalse(tools.processPaused(pid))

    def test_processName(self):
        pid = self._create_process()
        self.assertEqual(tools.processName(pid), generic.DUMMY[:15])

    def test_processCmdline(self):
        pid = self._create_process()
        self.assertRegex(tools.processCmdline(pid),
                         r'.*/sh.*/common/test/dummy_test_process\.sh')
        self._kill_process()
        pid = self._create_process('foo', 'bar')
        self.assertRegex(tools.processCmdline(pid),
                         r'.*/sh.*/common/test/dummy_test_process\.sh.foo.bar')

    @patch('builtins.open')
    def test_processCmdline_exception(self, mock_open):
        mock_open.side_effect = OSError()
        pid = self._create_process()
        self.assertEqual(tools.processCmdline(pid), '')

    def test_pidsWithName(self):
        self.assertEqual(len(tools.pidsWithName('nonExistingProcess')), 0)
        pid = self._create_process()
        pids = tools.pidsWithName(generic.DUMMY)
        self.assertGreaterEqual(len(pids), 1)
        self.assertIn(pid, pids)

    def test_processExists(self):
        self.assertFalse(tools.processExists('nonExistingProcess'))
        self._create_process()
        self.assertTrue(tools.processExists(generic.DUMMY))

    def test_processAlive(self):
        """
        Test the function processAlive
        """
        # TODO: add test (in chroot) running proc as root and kill as non-root
        self.assertTrue(tools.processAlive(os.getpid()))
        pid = self._create_process()
        self.assertTrue(tools.processAlive(pid))
        self._kill_process()
        self.assertFalse(tools.processAlive(pid))
        self.assertFalse(tools.processAlive(999999))
        with self.assertRaises(ValueError):
            tools.processAlive(0)
        self.assertFalse(tools.processAlive(-1))

    def test_checkXServer(self):
        try:
            tools.checkXServer()
        except Exception as e:
            self.fail(
                'tools.ckeck_x_server() raised exception {}'.format(str(e)))

    def test_powerStatusAvailable(self):
        if tools.processExists('upowerd') and not generic.ON_TRAVIS:
            self.assertTrue(tools.powerStatusAvailable())
        else:
            self.assertFalse(tools.powerStatusAvailable())
        self.assertIsInstance(tools.onBattery(), bool)

    def test_md5sum(self):
        with NamedTemporaryFile() as f:
            f.write(b'foo')
            f.flush()

            self.assertEqual(tools.md5sum(f.name),
                             'acbd18db4cc2f85cedef654fccc4a4d8')

    def test_mountpoint(self):
        self.assertEqual(tools.mountpoint('/nonExistingFolder/foo/bar'), '/')
        proc = os.path.join('/proc', str(os.getpid()), 'fd')
        self.assertEqual(tools.mountpoint(proc), '/proc')

    def test_decodeOctalEscape(self):
        self.assertEqual(tools.decodeOctalEscape('/mnt/normalPath'),
                         '/mnt/normalPath')
        self.assertEqual(
            tools.decodeOctalEscape('/mnt/path\\040with\\040space'),
            '/mnt/path with space')

    def test_readTimeStamp(self):
        with NamedTemporaryFile('wt') as f:
            f.write('20160127 0124')
            f.flush()
            self.assertEqual(tools.readTimeStamp(f.name),
                             datetime(2016, 1, 27, 1, 24))

        with NamedTemporaryFile('wt') as f:
            f.write('20160127')
            f.flush()
            self.assertEqual(tools.readTimeStamp(f.name),
                             datetime(2016, 1, 27, 0, 0))

    def test_writeTimeStamp(self):
        with NamedTemporaryFile('rt') as f:
            tools.writeTimeStamp(f.name)
            s = f.read().strip('\n')
            self.assertTrue(s.replace(' ', '').isdigit())
            self.assertEqual(len(s), 13)

    def test_splitCommands(self):
        ret = list(tools.splitCommands(['echo foo;'],
                                       head='echo start;',
                                       tail='echo end',
                                       maxLength=40))
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0], 'echo start;echo foo;echo end')

        ret = list(tools.splitCommands(['echo foo;']*3,
                                       head='echo start;',
                                       tail='echo end',
                                       maxLength=40))
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret[0], 'echo start;echo foo;echo foo;echo end')
        self.assertEqual(ret[1], 'echo start;echo foo;echo end')

        ret = list(tools.splitCommands(['echo foo;']*3,
                                       head='echo start;',
                                       tail='echo end',
                                       maxLength=0))
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0],
                         'echo start;echo foo;echo foo;echo foo;echo end')

        ret = list(tools.splitCommands(['echo foo;'] * 3,
                                       head='echo start;',
                                       tail='echo end',
                                       maxLength=-10))
        self.assertEqual(len(ret), 1)
        self.assertEqual(
            ret[0],
            'echo start;echo foo;echo foo;echo foo;echo end')


class CheckCronPattern(unittest.TestCase):
    def test_valid(self):
        to_test = (
            '0',
            '0,10,13,15,17,20,23',
            '*/6'
        )

        for sut in to_test:
            self.assertTrue(tools.checkCronPattern(sut))

    def test_not_valid(self):
        to_test = (
            'a',
            ' 1',
            '0,10,13,1a,17,20,23',
            '0,10,13, 15,17,20,23',
            '*/6,8',
            '*/6 a'
        )

        for sut in to_test:
            self.assertFalse(tools.checkCronPattern(sut))


class CheckCommand(unittest.TestCase):
    def test_empty(self):
        self.assertFalse(tools.checkCommand(''))

    def test_not_existing(self):
        self.assertFalse(tools.checkCommand('notExistedCommand'))

    def test_existing(self):
        for sut in ('ls', 'backintime'):
            self.assertTrue(tools.checkCommand(sut))


class EncryptableWildcards(unittest.TestCase):
    def test_has(self):
        to_test = (
            'foo',
            '/foo',
            'foo/*/bar',
            'foo/**/bar',
            '*/foo',
            '**/foo',
            'foo/*',
            'foo/**'
        )

        for sut in to_test:
            self.assertFalse(tools.patternHasNotEncryptableWildcard(sut))

    def test_has_not(self):
        to_test = (
            'foo?',
            'foo[1-2]',
            'foo*',
            '*foo',
            '**foo',
            '*.foo',
            'foo*bar',
            'foo**bar',
            'foo*/bar',
            'foo**/bar',
            'foo/*bar',
            'foo/**bar',
            'foo/*/bar*',
            '*foo/*/bar'
        )

        for sut in to_test:
            self.assertTrue(tools.patternHasNotEncryptableWildcard(sut))


class EscapeIPv6(unittest.TestCase):
    def test_escaped(self):
        values_and_expected = (
            ('fd00:0::5', '[fd00:0::5]'),
            (
                '2001:db8:0:8d3:0:8a2e:70:7344',
                '[2001:db8:0:8d3:0:8a2e:70:7344]'
            ),
            ('::', '[::]'),
            ('::1', '[::1]'),
            ('::ffff:192.0.2.128', '[::ffff:192.0.2.128]'),
            ('fe80::1', '[fe80::1]'),
        )

        for val, exp in values_and_expected:
            with self.subTest(val=val, exp=exp):
                self.assertEqual(tools.escapeIPv6Address(val), exp)

    def test_passed(self):
        test_values = (
            '192.168.1.1',
            '172.17.1.133',
            '255.255.255.255',
            '169.254.0.1',
        )

        for val in test_values:
            with self.subTest(val=val):
                # IPv4 addresses are not escaped
                self.assertEqual(tools.escapeIPv6Address(val), val)

    def test_invalid(self):
        """Invalid IP addresses and hostnames"""
        test_values = (
            'foo.bar',
            'fd00',
            '2001:0db8:::0000:0000:8a2e:0370:7334',
            ':2001:0db8:85a3:0000:0000:8a2e:0370:7334',
            '2001:0gb8:85a3:0000:0000:8a2e:0370:7334',
            '2001:0db8:85a3:0000:0000:8a2e:0370:7334:abcd',
            'localhost',
        )

        for val in test_values:
            with self.subTest(val=val):
                self.assertEqual(tools.escapeIPv6Address(val), val)


class ExecuteSubprocess(unittest.TestCase):
    def setUp(self):
        self.run = False

    def _callback(self, func, *args):
        func(*args)
        self.run = True

    def test_returncode(self):
        self.assertEqual(tools.Execute(['true']).run(), 0)
        self.assertEqual(tools.Execute(['false']).run(), 1)

    def test_callback_simple(self):
        c = lambda x, y: self._callback(self.assertEqual, x, 'foo')
        tools.Execute(['echo', 'foo'], callback=c).run()
        self.assertTrue(self.run)

    def test_callback_extra_user_data(self):
        c = lambda x, y: self._callback(self.assertEqual, x, y)
        tools.Execute(['echo', 'foo'], callback=c, user_data='foo').run()
        self.assertTrue(self.run)
        self.run = False

    def test_callback_no_output(self):
        c = lambda x, y: self._callback(self.fail,
                                       'callback was called unexpectedly')
        tools.Execute(['true'], callback=c).run()
        self.assertFalse(self.run)
        self.run = False

    def test_pausable(self):
        proc = tools.Execute(['true'])
        self.assertTrue(proc.pausable)


class Tools_FakeFS(pyfakefs_ut.TestCase):
    """Tests using a fake filesystem."""

    def setUp(self):
        self.setUpPyfakefs(allow_root_user=False)

    def test_git_repo_info_none(self):
        """Actually not a git repo"""

        self.assertEqual(tools.get_git_repository_info(), None)

    def test_git_repo_info(self):
        """Simulate a git repo"""

        path = pathlib.Path('.git')
        path.mkdir()

        # Branch folders and hash containing file
        foobar = path / 'refs' / 'heads' / 'fix' / 'foobar'
        foobar.parent.mkdir(parents=True)

        with foobar.open('w') as handle:
            handle.write('01234')

        # HEAD file
        head = path / 'HEAD'

        with head.open('w') as handle:
            handle.write('ref: refs/heads/fix/foobar')

        # Test
        self.assertEqual(
            tools.get_git_repository_info(),
            {
                'hash': '01234',
                'branch': 'fix/foobar'
            }
        )


@unittest.skip('See Issue #2461')
class ValidateSnapshotsPath(generic.TestCaseCfg):
    def test_writes(self):
        with TemporaryDirectory() as dirpath:
            ret = tools.validate_and_prepare_snapshots_path(
                path=dirpath,
                host_user_profile=self.cfg.hostUserProfile(),
                mode=self.cfg.snapshotsMode(),
                copy_links=self.cfg.copyLinks(),
                error_event=Event()
            )
            self.assertTrue(ret)

    def test_fails_on_ro(self):
        with TemporaryDirectory() as dirpath:
            # set directory to read only
            ro_dir_stats = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
            with generic.mockPermissions(dirpath, ro_dir_stats):
                ret = tools.validate_and_prepare_snapshots_path(
                    path=dirpath,
                    host_user_profile=self.cfg.hostUserProfile(),
                    mode=self.cfg.snapshotsMode(),
                    copy_links=self.cfg.copyLinks(),
                    error_event=Event()
                )
                self.assertFalse(ret)

    @patch('os.chmod')
    def test_permission_fail(self, mock_chmod):
        mock_chmod.side_effect = PermissionError()
        with TemporaryDirectory() as dirpath:
            ret = tools.validate_and_prepare_snapshots_path(
                path=dirpath,
                host_user_profile=self.cfg.hostUserProfile(),
                mode=self.cfg.snapshotsMode(),
                copy_links=self.cfg.copyLinks(),
                error_event=Event()
            )
            self.assertTrue(ret)


class CrossedAtLeastUnits(unittest.TestCase):
    def test_hours_false(self):
        # 18:56
        self.assertFalse(
            tools.crossed_at_least_units(
                # 18:23 last job run
                datetime(1982, 8, 6, 18, 23, 0, 0),
                # 18:56 end
                datetime(1982, 8, 6, 18, 56, 0, 0),
                # 1 hour
                1, TimeUnit.HOUR
            )
        )

    def test_hours_boundary(self):
        # 18:23
        last_job_run = datetime(1982, 8, 6, 18, 23, 0, 0)

        # 19:01 (only 36 minutes later, but the next hour)
        end = datetime(1982, 8, 6, 19, 1, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 1, TimeUnit.HOUR))
        self.assertFalse(tools.crossed_at_least_units(last_job_run, end, 2, TimeUnit.HOUR))

        # 20:01 (only 1 hour and 36 minutes later, but over the boundary)
        end = datetime(1982, 8, 6, 20, 1, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 2, TimeUnit.HOUR))

    def test_days_not_older(self):
        """Two days"""
        # 6th August, 18:23
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)

        # 7th August, 18:23
        end = datetime(1982, 8, 7, 18, 23, 0, 0)

        self.assertFalse(tools.crossed_at_least_units(birth, end, 2, TimeUnit.DAY))

    def test_days_older(self):
        """Two days plus one ms"""
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)
        end = datetime(1982, 8, 8, 18, 23, 0, 1)

        self.assertTrue(tools.crossed_at_least_units(birth, end, 2, TimeUnit.DAY))

    def test_days_boundary_one_day(self):
        """The boundary of days not their duration."""

        # 18:23 compared to ...
        last_job_run = datetime(1982, 8, 6, 18, 23, 0, 0)

        # next day 2:13 (only 8 hours later)
        end = datetime(1982, 8, 7, 2, 23, 0, 0)

        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 1, TimeUnit.DAY))
        self.assertFalse(tools.crossed_at_least_units(last_job_run, end, 2, TimeUnit.DAY))

    def test_days_boundary_four_days(self):
        """The boundary of days not their duration."""

        # 6th August, 18:23
        last_job_run = datetime(1982, 8, 6, 18, 23, 0, 0)

        # 9th August (the 4th day), at 2:13
        end = datetime(1982, 8, 9, 2, 23, 0, 0)
        # ...four days not finished yet
        self.assertFalse(tools.crossed_at_least_units(last_job_run, end, 4, TimeUnit.DAY))

        # 10th August (the 5th day), at 2:13
        end = datetime(1982, 8, 10, 2, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 4, TimeUnit.DAY))

    def test_weeks_boundary(self):
        """
            August 1982
        Mo Tu We Th Fr Sa Su
                           1
         2  3  4  5  6  7  8
         9 10 11 12 13 14 15
        16 17 18 19 20 21 22
        23 24 25 26 27 28 29
        30 31
        """
        # 6th August (Friday)
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)

        # 9th August (Monday next week)
        end = datetime(1982, 8, 9, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 1, TimeUnit.WEEK))

        # 15th August (Saturday next week)
        end = datetime(1982, 8, 15, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 1, TimeUnit.WEEK))
        self.assertFalse(tools.crossed_at_least_units(birth, end, 2, TimeUnit.WEEK))

        # 16th August
        end = datetime(1982, 8, 16, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 2, TimeUnit.WEEK))

    def test_months_boundary(self):
        # 6th August
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)

        # 1st Sept
        end = datetime(1982, 9, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 1, TimeUnit.MONTH))

        # 30 Sept
        end = datetime(1982, 9, 30, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 1, TimeUnit.MONTH))
        self.assertFalse(tools.crossed_at_least_units(birth, end, 2, TimeUnit.MONTH))

        # 1st Oct
        end = datetime(1982, 10, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 2, TimeUnit.MONTH))

        # 31 October
        end = datetime(1982, 10, 31, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 2, TimeUnit.MONTH))
        self.assertFalse(tools.crossed_at_least_units(birth, end, 3, TimeUnit.MONTH))

        # 1st November
        end = datetime(1982, 11, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 3, TimeUnit.MONTH))

    def test_months_steps(self):
        # 14th January
        last_job_run = datetime(1982, 1, 14, 18, 23, 0, 0)

        # 31th January
        end = datetime(1982, 1, 31, 18, 23, 0, 0)
        self.assertFalse(tools.crossed_at_least_units(last_job_run, end, 1, TimeUnit.MONTH))
        # 1st Feb
        end = datetime(1982, 2, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 1, TimeUnit.MONTH))

        # 28th Feb
        end = datetime(1982, 2, 28, 18, 23, 0, 0)
        self.assertFalse(tools.crossed_at_least_units(last_job_run, end, 2, TimeUnit.MONTH))
        # 1st March
        end = datetime(1982, 3, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 2, TimeUnit.MONTH))

        # 31th March
        end = datetime(1982, 3, 31, 18, 23, 0, 0)
        self.assertFalse(tools.crossed_at_least_units(last_job_run, end, 3, TimeUnit.MONTH))
        # 1st April
        end = datetime(1982, 4, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 3, TimeUnit.MONTH))

        # 1st May
        end = datetime(1982, 5, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 4, TimeUnit.MONTH))

        # 1st June
        end = datetime(1982, 6, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 5, TimeUnit.MONTH))

        # 1st July
        end = datetime(1982, 7, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 6, TimeUnit.MONTH))

        # 1st Aug
        end = datetime(1982, 8, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 7, TimeUnit.MONTH))

        # 1st Sept
        end = datetime(1982, 9, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 8, TimeUnit.MONTH))

        # 1st Oct
        end = datetime(1982, 10, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 9, TimeUnit.MONTH))

        # 1st Nov
        end = datetime(1982, 11, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 10, TimeUnit.MONTH))

        # 1st Dec
        end = datetime(1982, 12, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 11, TimeUnit.MONTH))

        # 1st Jan (next year)
        end = datetime(1983, 1, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(last_job_run, end, 12, TimeUnit.MONTH))

    def test_months_31th(self):
        # 31th May
        birth = datetime(1982, 5, 31, 18, 23, 0, 0)

        # 1st June
        end = datetime(1982, 6, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 1, TimeUnit.MONTH))

        # 30th September
        end = datetime(1982, 9, 30, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 4, TimeUnit.MONTH))
        self.assertFalse(tools.crossed_at_least_units(birth, end, 5, TimeUnit.MONTH))

    def test_months_next_year(self):
        # 6th August, 1982
        birth = datetime(1982, 8, 6, 18, 23, 0, 0)

        # 1st March, 1983
        end = datetime(1983, 3, 1, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 7, TimeUnit.MONTH))

        # 6th March, 1983
        end = datetime(1983, 3, 6, 18, 23, 0, 0)
        self.assertTrue(tools.crossed_at_least_units(birth, end, 7, TimeUnit.MONTH))
        self.assertFalse(tools.crossed_at_least_units(birth, end, 8, TimeUnit.MONTH))


class NestedDictUpdate(unittest.TestCase):
    """About nested_dict_update()"""

    def test_simple(self):
        """Simple"""
        org = {
            'foo': 7,
            'bar': {
                'a': 'drei',
                'b': 'uhr'
            }
        }
        update = {
            'planet': 'erde',
            'bar': {
                'b': 'wecker'
            },
            'ecke': 9
        }

        expect = {
            'planet': 'erde',
            'foo': 7,
            'bar': {
                'a': 'drei',
                'b': 'wecker'
            },
            'ecke': 9
        }

        self.assertDictEqual(
            tools.nested_dict_update(org, update),
            expect)


class InfoIniToDict(unittest.TestCase):
    INI = '\n'.join([
        'group.1.gid=0',
        'group.1.name=root',
        'group.2.gid=1000',
        'group.2.name=user',
        'group.size=2',
        'snapshot_date=20260620-113047',
        'snapshot_machine=TONNE',
        'snapshot_profile_id=1',
        'snapshot_tag=240',
        'snapshot_user=user',
        'user.1.name=root',
        'user.1.uid=0',
        'user.2.name=user',
        'user.2.uid=1000',
        'user.size=2',
    ])

    DICT = {
        'backup': {
            'date': '20260620-113047',
            'machine': 'TONNE',
            'profile_id': '1',
            'tag': '240',
            'user': 'user',
        },
        'users': {
            0: 'root',
            1000: 'user'
        },
        'groups': {
            0: 'root',
            1000: 'user'
        },
    }

    def test_info_ini_to_json(self):
        ini_content = StringIO(self.INI)
        result = tools.convert_info_ini_file_to_dict(ini_content)
        self.assertEqual(result, self.DICT)
