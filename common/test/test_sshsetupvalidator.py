# SPDX-FileCopyrightText: © 2026 Iqbalez
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests for sshsetupvalidator known_hosts handling."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sshcore
from sshsetupvalidator import SSHSetupValidator, SSHSetupError


class _ValidatorHarness(SSHSetupValidator):
    """Expose helpers without a full MountManager setup."""

    def __init__(self, ssh_host: sshcore.SSHHost):
        self.mnt = MagicMock()
        self.ssh_host = ssh_host
        self.cfg = MagicMock()
        self._cleanup_commands = []


class ParseSshGOutput(unittest.TestCase):
    """Unit tests for parsing ``ssh -G`` output."""

    def test_hostname_and_port(self):
        output = 'hostname foobar\nport 2222\nuser backup\n'
        hostname, port = SSHSetupValidator._parse_ssh_g_output(output)
        self.assertEqual(hostname, 'foobar')
        self.assertEqual(port, 2222)

    def test_invalid_port_ignored(self):
        output = 'hostname foo\nport not-a-number\n'
        hostname, port = SSHSetupValidator._parse_ssh_g_output(output)
        self.assertEqual(hostname, 'foo')
        self.assertIsNone(port)


class KnownHostsLookup(unittest.TestCase):
    """known_hosts lookup uses OpenSSH-resolved host names."""

    def setUp(self):
        self.host = sshcore.SSHHost(host='FOOBAR', user='u', port=22)
        self.validator = _ValidatorHarness(self.host)

    @patch('sshsetupvalidator.subprocess.run')
    def test_uses_resolved_hostname_for_keygen(self, mock_run):
        def fake_run(cmd, **_kwargs):
            proc = MagicMock()
            proc.returncode = 1
            proc.stdout = ''
            if cmd[0] == 'ssh' and '-G' in cmd:
                proc.returncode = 0
                proc.stdout = 'hostname foobar\nport 22\n'
            elif cmd[:2] == ['ssh-keygen', '-F']:
                if cmd[2] == 'FOOBAR':
                    proc.returncode = 1
                elif cmd[2] == 'foobar':
                    proc.returncode = 0
            return proc

        mock_run.side_effect = fake_run

        self.validator._check_known_hosts()

        keygen_hosts = [
            args[0][2]
            for args, _kwargs in mock_run.call_args_list
            if args[0][:2] == ['ssh-keygen', '-F']
        ]
        self.assertIn('foobar', keygen_hosts)
        self.assertNotIn('FOOBAR', keygen_hosts)

    @patch('sshsetupvalidator.subprocess.run')
    def test_raises_when_resolved_host_not_in_known_hosts(self, mock_run):
        def fake_run(cmd, **_kwargs):
            proc = MagicMock()
            proc.returncode = 1
            proc.stdout = ''
            if cmd[0] == 'ssh' and '-G' in cmd:
                proc.returncode = 0
                proc.stdout = 'hostname foobar\nport 22\n'
            return proc

        mock_run.side_effect = fake_run

        with self.assertRaises(SSHSetupError):
            self.validator._check_known_hosts()

    @patch('sshsetupvalidator.subprocess.run')
    def test_fallback_when_ssh_g_fails(self, mock_run):
        def fake_run(cmd, **_kwargs):
            proc = MagicMock()
            proc.returncode = 1
            proc.stdout = ''
            if cmd[0] == 'ssh' and '-G' in cmd:
                proc.returncode = 127
            elif cmd[:2] == ['ssh-keygen', '-F'] and cmd[2] == 'FOOBAR':
                proc.returncode = 0
            return proc

        mock_run.side_effect = fake_run

        self.validator._check_known_hosts()

        keygen_hosts = [
            args[0][2]
            for args, _kwargs in mock_run.call_args_list
            if args[0][:2] == ['ssh-keygen', '-F']
        ]
        self.assertEqual(keygen_hosts[0], 'FOOBAR')


class BuildSshGCommand(unittest.TestCase):
    """``ssh -G`` command mirrors regular SSH options."""

    def test_inserts_g_flag(self):
        host = sshcore.SSHHost(
            host='example.com',
            user='alice',
            port=2222,
            priv_key_file='/tmp/id_ed25519',
        )
        validator = _ValidatorHarness(host)
        cmd = validator._build_ssh_g_command()
        self.assertEqual(cmd[0], 'ssh')
        self.assertEqual(cmd[1], '-G')
        self.assertIn('-p', cmd)
        self.assertIn('2222', cmd)
        self.assertIn('alice@example.com', cmd)
        self.assertIn('IdentityFile=/tmp/id_ed25519', cmd)
