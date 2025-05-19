# SPDX-FileCopyrightText: © 2016 Taylor Raack
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
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
import getpass
import unittest
import datetime
from pathlib import Path
from unittest.mock import patch
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config


class RemoveOldSnapshotsDate(unittest.TestCase):
    def test_invalid_unit(self):
        """1st January Year 1 on errors"""
        unit = 99999
        value = 99

        self.assertEqual(
            config._remove_old_snapshots_date(value, unit),
            datetime.date(1, 1, 1))

    @patch('datetime.date', wraps=datetime.date)
    def test_day(self, m):
        """Three days"""
        m.today.return_value = datetime.date(2025, 1, 10)
        sut = config._remove_old_snapshots_date(3, config.Config.DAY)
        self.assertEqual(sut, datetime.date(2025, 1, 7))

    @patch('datetime.date', wraps=datetime.date)
    def test_week_always_monday(self, m):
        """Result is always a Monday"""

        # 1-53 weeks back
        for weeks in range(1, 54):
            start = datetime.date(2026, 1, 1)

            # Every day in the year
            for count in range(366):
                m.today.return_value = start - datetime.timedelta(days=count)

                sut = config._remove_old_snapshots_date(
                    weeks, config.Config.WEEK)

                # 0=Monday
                self.assertEqual(sut.weekday(), 0, f'{sut=} {weeks=}')

    @patch('datetime.date', wraps=datetime.date)
    def test_week_ignore_current(self, m):
        """Current (incomplete) week is ignored."""
        for day in range(25, 32):  # Monday (25th) to Sunday (31th)
            m.today.return_value = datetime.date(2025, 8, day)
            sut = config._remove_old_snapshots_date(2, config.Config.WEEK)
            self.assertEqual(
                sut,
                datetime.date(2025, 8, 11)  # Monday
            )

    @patch('datetime.date', wraps=datetime.date)
    def test_year_ignore_current_month(self, m):
        """Not years but 12 months are counted. But current month is
        ignored."""
        m.today.return_value = datetime.date(2025, 7, 30)
        sut = config._remove_old_snapshots_date(2, config.Config.YEAR)
        self.assertEqual(sut, datetime.date(2023, 7, 1))


class SshCommand(generic.SSHTestCase):
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


class TestSshPrivateKeySelectionWithMock(generic.TestCaseCfg):
    def setUp(self):
        super().setUp()
        self.ssh_dir_path = os.path.join(str(Path.home()), ".ssh")

    @patch('os.path.isfile')
    def test_selects_id_ed25519_first_if_others_exist(self, mock_isfile):
        """
        Test that when both id_ed25519 and id_rsa exist, id_ed25519 is preferred.
        """
        def side_effect_isfile(path):
            if path == os.path.join(self.ssh_dir_path, "id_ed25519"):
                return True
            if path == os.path.join(self.ssh_dir_path, "id_rsa"):
                return True
            return False
        mock_isfile.side_effect = side_effect_isfile

        with patch.object(self.cfg, 'sshPrivateKeyFolder', return_value=self.ssh_dir_path):
            expected_key_path = os.path.join(self.ssh_dir_path, "id_ed25519")
            self.assertEqual(self.cfg.sshPrivateKeyFile(), expected_key_path)

    @patch('os.path.isfile')
    def test_selects_id_ed25519_when_it_is_the_only_key(self, mock_isfile):
        """
        Test that when only the id_ed25519 key exists, it is correctly selected.
        """
        def side_effect_isfile(path):
            return path == os.path.join(self.ssh_dir_path, "id_ed25519")
        mock_isfile.side_effect = side_effect_isfile

        with patch.object(self.cfg, 'sshPrivateKeyFolder', return_value=self.ssh_dir_path):
            expected_key_path = os.path.join(self.ssh_dir_path, "id_ed25519")
            self.assertEqual(self.cfg.sshPrivateKeyFile(), expected_key_path)

    @patch('os.path.isfile')
    def test_selects_id_rsa_if_id_ed25519_is_absent(self, mock_isfile):
        """
        Test that when id_ed25519 does not exist but id_rsa exists, id_rsa is selected.
        """
        def side_effect_isfile(path):
            if path == os.path.join(self.ssh_dir_path, "id_rsa"):
                return True

            if path == os.path.join(self.ssh_dir_path, "id_ed25519"):
                return False
            if path == os.path.join(self.ssh_dir_path, "id_ecdsa"):
                 return False

            return False
        mock_isfile.side_effect = side_effect_isfile

        with patch.object(self.cfg, 'sshPrivateKeyFolder', return_value=self.ssh_dir_path):
            expected_key_path = os.path.join(self.ssh_dir_path, "id_rsa")
            self.assertEqual(self.cfg.sshPrivateKeyFile(), expected_key_path)

    @patch('os.path.isfile')
    def test_returns_empty_string_if_no_default_keys_found(self, mock_isfile):
        """
        Test that when no predefined key files are found in the ~/.ssh directory, an empty string is returned.
        """
        mock_isfile.return_value = False

        with patch.object(self.cfg, 'sshPrivateKeyFolder', return_value=self.ssh_dir_path):
            self.assertEqual(self.cfg.sshPrivateKeyFile(), "")

    @patch('os.path.isfile')
    def test_uses_explicitly_configured_key_over_defaults(self, mock_isfile):
        """
        Test that when private_key_file is explicitly specified in the configuration,
        it takes precedence over default key selection.
        """
        mock_isfile.return_value = True

        custom_key_filename = "my_explicit_key"
        with patch.object(self.cfg, 'sshPrivateKeyFolder', return_value=self.ssh_dir_path):
            custom_key_path_str = os.path.join(self.ssh_dir_path, custom_key_filename)

            profile_id_to_test = self.cfg.currentProfile()
            config_key_name = 'snapshots.ssh.private_key_file'

            original_value = self.cfg.profileStrValue(config_key_name, profile_id=profile_id_to_test)

            self.cfg.setProfileStrValue(config_key_name, custom_key_path_str, profile_id=profile_id_to_test)

            self.assertEqual(self.cfg.sshPrivateKeyFile(profile_id=profile_id_to_test), custom_key_path_str)

            self.cfg.setProfileStrValue(config_key_name, original_value, profile_id=profile_id_to_test)
