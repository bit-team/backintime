# SPDX-FileCopyrightText: © 2016 Taylor Raack
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about config module.
"""
import os
import sys
import unittest
import getpass
from unittest.mock import patch
import datetime
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config


class TestSshCommand(generic.SSHTestCase):
    @classmethod
    def setUpClass(cls):
        cls._user = getpass.getuser()

    def test_full_command(self):
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])
        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_custom_args(self):
        cmd = self.cfg.sshCommand(
            cmd=['echo', 'foo'],
            custom_args=['-o', 'PreferredAuthentications=publickey'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                '-o', 'PreferredAuthentications=publickey',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_cipher_aes256_cbc(self):
        self.cfg.setSshCipher('aes256-cbc')
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                '-o', 'Ciphers=aes256-cbc',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_cipher_disabled(self):
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'], cipher=False)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_without_command(self):
        cmd = self.cfg.sshCommand()
        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
            ]
        )

    def test_nice_and_ionice(self):
        self.cfg.setNiceOnRemote(True)
        self.cfg.setIoniceOnRemote(True)

        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'ionice', '-c2', '-n7',
                'nice', '-n19',
                'echo', 'foo'
            ]
        )

    def test_nice_and_ionice_without_command(self):
        self.cfg.setNiceOnRemote(True)
        self.cfg.setIoniceOnRemote(True)

        cmd = self.cfg.sshCommand()

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
            ]
        )

    def test_quote(self):
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'], quote=True)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                "'", 'echo', 'foo', "'"
            ]
        )

    def test_quote_without_command(self):
        cmd = self.cfg.sshCommand(quote=True)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
            ]
        )

    def test_prefix(self):
        self.cfg.setSshPrefix(True, 'echo bar')

        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'])

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'echo', 'bar',
                'echo', 'foo'
            ]
        )

    def test_prefix_false(self):
        # disable prefix
        cmd = self.cfg.sshCommand(cmd=['echo', 'foo'], prefix=False)

        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
                '-p', '22',
                f'{self._user}@localhost',
                'echo', 'foo'
            ]
        )

    def test_disable_args(self):
        cmd = self.cfg.sshCommand(port=False, user_host=False)
        self.assertListEqual(
            cmd,
            [
                'ssh',
                '-o', 'ServerAliveInterval=240',
                '-o', 'LogLevel=Error',
                '-o', f'IdentityFile={generic.PRIV_KEY_FILE}',
            ]
        )

@patch(f'{config.__name__}.datetime.datetime', wraps=datetime.datetime)
class OlderThan(unittest.TestCase):
    HOUR = config.Config.HOUR
    DAY = config.Config.DAY
    WEEK = config.Config.WEEK
    MONTH = config.Config.MONTH

    def test_hours_not_older(self, mock_dt):
        """Exact two hours"""
        # year, month, day, hour=0, minute=0, second=0, microsecond=0
        birth = datetime.datetime(1982, 8, 6, 18, 23, 0, 0)

        # exact two hours
        mock_dt.now.return_value = datetime.datetime(1982, 8, 6, 20, 23, 0, 0)

        cfg = config.Config()
        self.assertFalse(cfg.olderThan(birth, 2, self.HOUR))

    def test_hours_older(self, mock_dt):
        """Two hours plus one ms"""
        birth = datetime.datetime(1982, 8, 6, 18, 23, 0, 0)

        # two hours + 1 ms
        mock_dt.now.return_value = datetime.datetime(1982, 8, 6, 20, 23, 0, 1)

        cfg = config.Config()
        self.assertTrue(cfg.olderThan(birth, 2, self.HOUR))

    def test_days_INCONSISTENT(self, mock_dt):
        """Two days

        The behavior is inconsistent compared to the HOUR behavior. 8th
        August 00:00 is less then two days (48 hours), but treated as "older
        then 2 days". Hours and minutes not relevant.
        """
        birth = datetime.datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime.datetime(1982, 8, 8, 0, 0, 0, 0)

        cfg = config.Config()
        self.assertTrue(cfg.olderThan(birth, 2, self.DAY))

    def test_week_INCONSISTENT(self, mock_dt):
        """Two weeks

        Same as in DAYS. Minutes, Seconds, Days not considered.
        """
        birth = datetime.datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime.datetime(1982, 8, 20, 18, 23, 0, 0)

        cfg = config.Config()
        self.assertTrue(cfg.olderThan(birth, 2, self.WEEK))

    def test_month_INCONSISTENT(self, mock_dt):
        """Two months.

        Same as in DAYS. Minutes, Seconds, Days not considered.
        """
        birth = datetime.datetime(1982, 8, 6, 18, 23, 0, 0)
        mock_dt.now.return_value = datetime.datetime(1982, 10, 6, 18, 23, 0, 0)

        cfg = config.Config()
        self.assertTrue(cfg.olderThan(birth, 2, self.MONTH))
