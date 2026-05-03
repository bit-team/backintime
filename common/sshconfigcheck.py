# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""SSH setup checks.

The code is based on `sshtools.py:SSH.preMountCheck()`. These checks are now
distinguished between two types of checks.
Checks running on every mount operation now handled in the new mount subsystem
via `Backend.validate()`. Checks that run only when setup or modifiy a profile
are done here.

Feel free to move this code somewhere else.
"""
import os
import tempfile
import subprocess
import shutil
from pathlib import Path
import logger
import sshtools
from mount import MountManager
from config import Config


class SSHConfigCheck:
    """An existing SSH mount is used to check if it is prepared for being a
    backup destination.

    This checks are executed on new profile creation and profile modifications.
    """

    def __init__(self,
                 mount_manager: MountManager,
                 config: Config):
        self.mnt = mount_manager

        # The SSH backends current config, will be used for the tests.
        self.ssh_host = mount_manager.backend.host

        self.cfg = config

        self._cleanup_commands = []

    def _build_ssh_command(self) -> list[str]:
        """Taken from `Config.sshCommand()`. Refactor later. See #1966 about
        encapsulate shell commands.

        Maybe the mount manager could provide some basics SSH commands because
        it knews the host configuration?

        Returns:
            list:               ssh command with chosen arguments
        """
        # Refactor: Use of assert is discouraged in productive code.
        # Raise Exceptions instead.
        ssh = ['ssh']

        # # Taken from `Config.sshDefaultArgs()`
        # ssh += ['-o', 'ServerAliveInterval=240']  # keep connection alive
        # ssh += ['-o', 'LogLevel=Error']  # disable ssh banner

        # specifying key file here allows to override for potentially
        # conflicting .ssh/config key entry
        if self.ssh_host.priv_key_file:
            ssh += ['-o', f'IdentityFile={self.ssh_host.priv_key_file}']

        # Proxy (aka Jump host)
        if self.ssh_host.proxy:
            ssh += ['-J', self.ssh_host.proxy.user_host_port]

        # remote port
        ssh += ['-p', str(self.ssh_host.port)]

        # # custom arguments
        # if custom_args:
        #     ssh += custom_args

        # user@host
        ssh.append(self.ssh_host.user_host)

        # # quote the command running on remote host
        # if quote and cmd:
        #     ssh.append("'")

        # # run 'ionice' on remote host
        # if self.cfg.ioniceOnRemote():
        #     ssh += ['ionice', '-c2', '-n7']

        # # run 'nice' on remote host
        # if self.niceOnRemote():
        #     ssh += ['nice', '-n19']

        # TODO
        # # run prefix on remote host
        # if prefix and cmd and self.sshPrefixEnabled(profile_id):
        #     ssh += self.sshPrefixCmd(profile_id, cmd_type=type(cmd))

        return ssh

    def _ssh(self, cmd: list[str]) -> tuple[int, str, str]:
        proc = subprocess.Popen(
            self._build_ssh_command() + cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, err = proc.communicate()

        return proc.returncode, out, err

    def _check_tool(self, tool_cmd: list[str]):
        """Checks if the named tool is avaiable at the remote machine.

        Raise: RuntimeError if the tool is missing
        """
        rc, _, err = self._ssh(tool_cmd)

        if rc != 0:
            raise RuntimeError(
                f'"{tool_cmd[0]}" not available on remote host. '
                f'Command: {tool_cmd} Error: "{err}"'
            )

    def run(self):
        self._check_sshfs_usable()

        self._check_known_hosts()

        self._ensure_ssh_agent_running()
        self._ensure_private_key_loaded()

        # checkRemoteFolder()  -> evtl. in validate()

        try:
            if self.config.sshCheckCommands():
                self._check_rsync_basic()
                self._check_rsync_hardlinks()
                self._check_remote_tools()
        finally:
            for cmd in self._cleanup_commands:
                try:
                    self._ssh(cmd)
                except Exception as exc:
                    logger.debug(f'Cleanup failed: {cmd=} {exc=}', self)
                    pass

    def _ensure_ssh_agent_running(self):
        """Ensure that an ssh-agent process is running and available in the
        current environment.

        If an existing ssh-agent is detected via SSH_AUTH_SOCK and
        SSH_AGENT_PID environment variables, no action is taken.

        Otherwise, a new ssh-agent process is started and its environment
        variables are injected into the current process environment.

        The started agent is registered for cleanup on process exit.

        Raises:
            RuntimeError: if ssh-agent cannot be started or its output
            cannot be parsed correctly.

        """

        # Detect an existing ssh-agent
        sock = os.getenv('SSH_AUTH_SOCK')
        pid = os.getenv('SSH_AGENT_PID')

        if sock and pid:
            # No action take because agent is running
            return

        ssh_agent = shutil.which('ssh-agent')
        if not ssh_agent:
            raise RuntimeError('ssh-agent not found')

        proc = subprocess.Popen(
            [ssh_agent],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        out, err = proc.communicate()

        if proc.returncode:
            raise RuntimeError(f'ssh-agent failed: {err}')

        sock_path = None
        agent_pid = None

        def _extract_var(var: str, line: str) -> str:
            return line.split('=', 1)[1].split(';', 1)[0].strip()

        for line in out.splitlines():
            if 'SSH_AUTH_SOCK=' in line:
                sock_path = _extract_var('SSH_AUTH_SOCK', line)
            elif 'SSH_AGENT_PID=' in line:
                agent_pid = _extract_var('SSH_AGENT_PID', line)

        if not sock_path or not agent_pid:
            raise RuntimeError(f"Unexpected ssh-agent output: {out}")

        os.environ['SSH_AUTH_SOCK'] = sock_path
        os.environ['SSH_AGENT_PID'] = agent_pid

        atexit.register(
            os.kill,
            int(agent_pid),
            signal.SIGKILL
        )

    def _ensure_private_key_loaded(self, force: bool = False):
        key_file = self.ssh_host.priv_key_file
        if not key_file:
            return

        fingerprint = sshtools.ssh_key_fingerprint(key_file)

        if self._is_key_loaded(fingerprint):
            return

        self._add_key_to_agent(key_file)

        if not self._is_key_loaded(fingerprint):
            raise RuntimeError('key not loaded into ssh-agent')

    def _is_key_loaded(self, key_fingerprint: str) -> bool:
        proc = subprocess.run(
            ['ssh-add', '-l', '-E', 'sha256'],
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )

        return key_fingerprint in proc.stdout

    def _add_key_to_agent(self, key_file: str) -> None:
        proc = subprocess.run(
            ['ssh-add', key_file],
            capture_output=True,
            text=True,
            env=self._provide_ssh_password_env()
        )

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)

    def _provide_ssh_password_env(self) -> dict:
        env = os.environ.copy()

        env['SSH_ASKPASS'] = 'backintime-askpass'
        env['SSH_ASKPASS_REQUIRE'] = 'force'
        env['ASKPASS_PROFILE_ID'] = self.profile_id
        env['ASKPASS_MODE'] = self.mode

        return env

    def _check_sshfs_usable(self):
        """Check if sshfs is callable."""

        path = shutil.which('sshfs')

        if path is None:
            raise RuntimeError('sshfs not found')

        proc = subprocess.run(
            [path, '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if proc.returncode != 0:
            raise RuntimeError(f'sshfs not usable: {proc.stderr}')

    def _check_known_hosts(self):
        """Check if host is present in known_hosts file."""

        hosts_to_check = [
            self.ssh_host.host,
            f'[{self.ssh_host.host}]:{self.ssh_host.port}'
        ]

        for host in hosts_to_check:
            proc = subprocess.run(
                ['ssh-keygen', '-F', host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if proc.returncode == 0:
                return

        raise RuntimeError(f'{self.ssh_host.host} is not a known hosts')

    def _check_rsync_basic(self):
        """Checks if it is possible to write a file via rsync to the SSH
        remote host.
        """
        with tempfile.TemporaryDirectory() as tmp:
            local_fp = Path(tmp) / 'a'
            local_fp.write_text('foo', encoding='utf-8')

            remote_tmp = self.ssh_host.user_host_path + '/bit_check_tmp'

            cmd = [
                'rsync',
                '--archive',
                local_fp,
                remote_tmp + '/'
            ]

            logger.info(f'Calling {cmd}...', self)

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            _, err = proc.communicate()

        # cleanup
        self._cleanup_commands.append(
            ['rm', '--recursive', '--force', remote_tmp]
        )

        if proc.returncode != 0:
            raise RuntimeError(f'rsync basic failed: {err}')

    def _check_rsync_hardlinks(self):
        """Checks if rsync creates real hardlinks on remote file system."""
        with tempfile.TemporaryDirectory() as tmp:
            local_fp = Path(tmp) / 'a'
            local_fp.write_text('foo', encoding='utf-8')

            remote_base = self.ssh_host.user_host_path
            remote_1 = remote_base + '/bit_check_1'
            remote_2 = remote_base + '/bit_check_2'

            self._cleanup_commands.append(
                ['rm', '--recursive', '--force', remote_1]
            )
            self._cleanup_commands.append(
                ['rm', '--recursive', '--force', remote_2]
            )

            # First upload
            cmd1 = [
                'rsync',
                '--archive',
                local_fp,
                remote_1 + '/'
            ]

            # Second upload with link-dest
            cmd2 = [
                'rsync',
                '--archive',
                '--link-dest=../bit_check_1',
                local_fp,
                remote_2 + '/'
            ]

            for cmd in (cmd1, cmd2):
                logger.info(f'Calling {cmd}...', self)
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                _, err = proc.communicate()

                if proc.returncode != 0:
                    raise RuntimeError(f'rsync hardlink test failed: {err}')

            def _remote_stat_inode(path: str) -> int:
                cmd = self._build_ssh_command()
                cmd.extend(['stat', '--format', '%i', path])
                logger.info(f'Calling {cmd}...', self)
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                out, err = proc.communicate()
                if proc.returncode != 0:
                    raise RuntimeError(err)

                return int(out.strip())

            # inode check via ssh
            inode_1 = _remote_stat_inode(f'{remote_1}/a')
            inode_2 = _remote_stat_inode(f'{remote_2}/a')
            if inode_1 != inode_2:
                raise RuntimeError(
                    'Remote file system does not support hardlinks'
                )

    def _check_remote_tools(self):
        """Dev note (buhtz, 2026-05): Need to re-validate if all this commands
        are still in use by Back In Time.
        """
        self._check_tool(['bash', '-c', 'true'])

        if self.cfg.niceOnRemote():
            self._check_tool(['nice', '-n', '19', 'true'])

        if self.cfg.ioniceOnRemote():
            self._check_tool(['ionice', '-c2', '-n7', 'true'])

        if self.cfg.nocacheOnRemote():
            self._check_tool(['nocache', 'true'])

        if self.cfg.setSmartRemoveRunRemoteInBackground():
            self._check_tool(['screen', '-d', '-m', 'bash', '-c', 'true'])
            self._cleanup_commands.append(
                ['rm', '--recursive', '--force', 'smr.lock']
            )
            self._check_tool(
                ['flock', '--exclusive', 'smr.lock', '--command', 'true']
            )
