# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
# pylint: disable=duplicate-code
"""SSH setup checks.

The code is based on `sshtools.py:SSH.preMountCheck()`. These checks are now
distinguished between two types of checks.
Checks running on every mount operation now handled in the new mount subsystem
via `Backend.validate()`. Checks that run only when setup or modify a profile
are done here.

Feel free to move this code somewhere else.
"""
import os
import tempfile
import subprocess
import shutil
import atexit
import signal
from pathlib import Path
import logger
import sshcore
from mount import MountManager
from exceptions import ApplicationError


class SSHSetupError(ApplicationError):
    """Raised for failures while the SSH setup validation.

    Design decisions: The class is intentionally kept generic to avoid a
       hierarchy of specialized mount-related exception types.
    """
    def __init__(
            self,
            log_msg: str,
            gui_msg: str | None = None
    ):
        super().__init__(log_msg=log_msg, gui_msg=gui_msg)


class SSHSetupValidator:  # pylint: disable=too-few-public-methods
    """An existing SSH mount is used to check if it is prepared for being a
    backup destination.

    This checks are executed on new profile creation and profile modifications.
    """

    def __init__(self, mount_manager: MountManager):
        self.mnt = mount_manager
        # The SSH backends current config, will be used for the tests.
        self.ssh_host = mount_manager.backend.host
        self.cfg = self.mnt.cfg
        self._cleanup_commands = []

    def _build_ssh_command(self) -> list[str]:
        """Taken from `Config.sshCommand()`. Refactor later. See #1966 about
        encapsulate shell commands.

        Maybe the mount manager could provide some basics SSH commands because
        it knews the host configuration?

        Returns:
            list:               ssh command with chosen arguments
        """
        ssh = ['ssh']

        # specifying key file here allows to override for potentially
        # conflicting .ssh/config key entry
        if self.ssh_host.priv_key_file:
            ssh += ['-o', f'IdentityFile={self.ssh_host.priv_key_file}']

        # Proxy (aka Jump host)
        if self.ssh_host.proxy:
            ssh += ['-J', self.ssh_host.proxy.user_host_port]

        # remote port
        ssh += ['-p', str(self.ssh_host.port)]

        # user@host
        ssh.append(self.ssh_host.user_host)

        # Dev note (2026-05, buhtz):
        # Keep this comment as a reminder. To my understanding the SSH remote
        # prefix commands are not relevant while SSH setup validation step.
        # But I am not sure.
        # # run prefix on remote host
        # if prefix and cmd and self.sshPrefixEnabled(profile_id):
        #     ssh += self.sshPrefixCmd(profile_id, cmd_type=type(cmd))

        return ssh

    def _ssh(self, cmd: list[str]) -> tuple[int, str, str]:
        cmd = self._build_ssh_command() + cmd
        logger.info(f'Calling {cmd}...', self)

        # pylint: disable-next=consider-using-with
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, err = proc.communicate()

        return proc.returncode, out, err

    def _check_tool(self, tool_cmd: list[str]):
        """Checks if the named tool is available at the remote machine.

        Raise: RuntimeError if the tool is missing
        """
        rc, _out, err = self._ssh(tool_cmd)

        if rc != 0:
            raise SSHSetupError(
                f'"{tool_cmd[0]}" not available on remote host. '
                f'Command: {tool_cmd} Error: "{err}"',
                _('"{tool}" is not installed on the remote host.').format(
                    tool=tool_cmd[0])
            )

    def run(self):
        """Entry point for all setup validation checks"""
        self._check_tcp_connectivity()

        # --- Ensure local prerequisites ---
        self._check_sshfs_usable()
        self._check_known_hosts()
        self._ensure_ssh_agent_running()
        self._ensure_private_key_loaded()

        self._ensure_remote_directory()

        # --- Check remote capabilities ---
        try:
            if self.cfg.sshCheckCommands():  # Deprecated. See issue #2509
                self._check_rsync_basic()
                self._check_rsync_hardlinks()
                self._check_remote_tools()

        finally:
            for cmd in self._cleanup_commands:
                try:
                    self._ssh(cmd)
                except (subprocess.SubprocessError, OSError) as exc:
                    logger.error(f'Cleanup failed: {cmd=} {exc=}', self)

    def _check_tcp_connectivity(self):
        """Check if configured SSH endpoints are reachable via TCP.

        Proxy (jump host) and target host are checked.

        Raises:
            SSHSetupError: If an endpoint is unreachable.
        """
        # pylint: disable-next=duplicate-code
        hosts = []

        # Proxy first if present
        if self.ssh_host.proxy:
            hosts.append((self.ssh_host.proxy, True))

        # Final host
        hosts.append((self.ssh_host, False))

        for host, is_proxy in hosts:
            if sshcore.can_connect_tcp(host):
                continue

            hp = f'{host.host}:{host.port}'

            if is_proxy:
                log_msg = f'SSH proxy endpoint unreachable: {hp}'
                gui_msg = _(
                    'Could not reach the SSH proxy host "{host_port}".'
                ).format(host_port=hp)
            else:
                log_msg = f'SSH endpoint unreachable: {hp}'
                gui_msg = _(
                    'Could not reach the SSH host "{host_port}".'
                ).format(host_port=hp)

            raise SSHSetupError(log_msg, gui_msg)

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
            raise SSHSetupError(
                'ssh-agent not found',
                _('ssh-agent is not installed')
            )

        proc = subprocess.Popen(  # pylint: disable=consider-using-with
            [ssh_agent],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        out, err = proc.communicate()

        if proc.returncode:
            raise SSHSetupError(
                f'ssh-agent failed: {err}',
                _('Unexpected response from ssh-agent.') + '\n\n'
                + _('Details:') + f'\n{err}'
            )

        sock_path = None
        agent_pid = None

        for line in [line.strip() for line in out.split(';')]:
            if 'SSH_AUTH_SOCK=' in line:
                sock_path = line.split('=', 1)[1]
            elif 'SSH_AGENT_PID=' in line:
                agent_pid = line.split('=', 1)[1]

        if not sock_path or not agent_pid:
            raise SSHSetupError(
                f'Unexpected ssh-agent output: {out}',
                _('Unexpected output from ssh-agent.') + '\n\n'
                + _('Output:') + f'\n{out}'
            )

        os.environ['SSH_AUTH_SOCK'] = sock_path
        os.environ['SSH_AGENT_PID'] = agent_pid

        atexit.register(
            os.kill,
            int(agent_pid),
            signal.SIGKILL
        )

    def _ensure_private_key_loaded(self):
        key_file = self.ssh_host.priv_key_file
        if not key_file:
            return

        fingerprint = sshcore.ssh_key_fingerprint(Path(key_file))

        if self._is_key_loaded(fingerprint):
            return

        self._add_key_to_agent(key_file)

        if not self._is_key_loaded(fingerprint):
            raise SSHSetupError(
                'SSH key not loaded into ssh-agent',
                _('The SSH key is not loaded into ssh-agent.')
            )

    def _is_key_loaded(self, key_fingerprint: str) -> bool:
        proc = subprocess.run(
            ['ssh-add', '-l', '-E', 'sha256'],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False
        )

        return key_fingerprint in proc.stdout

    def _add_key_to_agent(self, key_file: str) -> None:
        cmd = ['ssh-add', key_file]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=self._provide_ssh_password_env(),
            check=False
        )

        err = proc.stderr

        if proc.returncode != 0:
            raise SSHSetupError(
                f'Adding SSH key failed ({cmd=}): "{err}"',
                _('Failed to add SSH key.') + '\n\n'
                + _('Details:') + f'\n{err.strip()}\n{cmd}'
            )

    def _provide_ssh_password_env(self) -> dict:
        env = os.environ.copy()

        env['SSH_ASKPASS'] = 'backintime-askpass'
        env['SSH_ASKPASS_REQUIRE'] = 'force'
        env['ASKPASS_PROFILE_ID'] = self.cfg.currentProfile()
        env['ASKPASS_MODE'] = self.cfg.snapshotsMode()

        return env

    def _check_sshfs_usable(self):
        """Check if sshfs is callable."""

        path = shutil.which('sshfs')

        if path is None:
            raise SSHSetupError(
                'sshfs not found',
                _('sshfs is not installed')
            )

        proc = subprocess.run(
            [path, '--version'],
            capture_output=True,
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            text=True,
            check=False
        )

        err = proc.stderr

        if proc.returncode != 0:
            raise SSHSetupError(
                f'sshfs not usable: {proc.stderr}',
                _('Unexpected response from sshfs.') + '\n\n'
                + _('Details:') + f'\n{err.strip()}'
            )

    def _check_known_hosts(self):
        """Check if host is present in known_hosts file."""

        hosts_to_check = [
            self.ssh_host.host,
            f'[{self.ssh_host.host}]:{self.ssh_host.port}'
        ]

        for host in hosts_to_check:
            proc = subprocess.run(
                ['ssh-keygen', '-F', host],
                capture_output=True,
                # stdout=subprocess.PIPE,
                # stderr=subprocess.PIPE,
                text=True,
                check=False
            )

            if proc.returncode == 0:
                return

        raise SSHSetupError(
            f'{self.ssh_host.host} is not a known host',
            _('The SSH host "{host}" is not trusted yet.').format(
                host=self.ssh_host.host)
            + '\n\n' + _('Please connect to the host manually once to '
                         'confirm its fingerprint.')
        )

    def _check_rsync_basic(self):
        """Checks if it is possible to write a file via rsync to the SSH
        remote host.
        """
        with tempfile.TemporaryDirectory() as tmp:
            local_fp = Path(tmp) / 'a'
            local_fp.write_text('foo', encoding='utf-8')

            tmp_dir = '/bit_check_tmp'
            remote_tmp = self.ssh_host.user_host_path + tmp_dir

            cmd = [
                'rsync',
                '--archive',
                local_fp,
                remote_tmp + '/'
            ]

            logger.info(f'Calling {cmd}...', self)

            proc = subprocess.Popen(  # pylint: disable=consider-using-with
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            _out, err = proc.communicate()

        # cleanup
        self._cleanup_commands.append(
            ['rm', '--recursive', '--force', self.ssh_host.path + tmp_dir]
        )

        if proc.returncode != 0:
            raise SSHSetupError(
                f'rsync basic failed: {err.strip()}',
                _('Could not write files to the remote host using rsync.')
                + '\n\n' + _('Details:') + f'\n{err.strip()}'
            )

    def _check_rsync_hardlinks(self):  # pylint: disable=too-many-locals
        """Checks if rsync creates real hardlinks on remote file system."""
        with tempfile.TemporaryDirectory() as tmp:
            local_fp = Path(tmp) / 'a'
            local_fp.write_text('foo', encoding='utf-8')

            remote_base = self.ssh_host.user_host_path
            locale_base = self.ssh_host.path
            remote_1 = remote_base + '/bit_check_1'
            remote_2 = remote_base + '/bit_check_2'
            locale_1 = locale_base + '/bit_check_1'
            locale_2 = locale_base + '/bit_check_2'

            self._cleanup_commands.append(
                ['rm', '--recursive', '--force', locale_1]
            )
            self._cleanup_commands.append(
                ['rm', '--recursive', '--force', locale_2]
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
                proc = subprocess.Popen(  # pylint: disable=consider-using-with
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                _out, err = proc.communicate()

                if proc.returncode != 0:
                    raise SSHSetupError(
                        f'rsync hardlink test failed: {err.strip()}',
                        _('Could not verify rsync hardlink support.') + '\n\n'
                        + _('Details:') + f'\n{err.strip()}'
                    )

            def _remote_stat_inode(path: str) -> int:
                cmd = self._build_ssh_command()
                cmd.extend(['stat', '--format', '%i', path])
                logger.info(f'Calling {cmd}...', self)

                proc = subprocess.Popen(  # pylint: disable=consider-using-with
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
            try:
                inode_1 = _remote_stat_inode(f'{locale_1}/a')
                inode_2 = _remote_stat_inode(f'{locale_2}/a')

            except RuntimeError as exc:
                raise SSHSetupError(
                    f'Unexpected error while receiving inodes: {exc}',
                    _('Unexpected error while verifying rsync hardlink '
                      'support.') + '\n\n' + _('Details:') + f'\n{exc}'
                ) from exc

            if inode_1 != inode_2:
                raise SSHSetupError(
                    'No hardlinks support on remote file system',
                    _('The remote file system does not support hardlinks.')
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

        if self.cfg.smartRemoveRunRemoteInBackground():
            self._check_tool(['screen', '-d', '-m', 'bash', '-c', 'true'])
            self._cleanup_commands.append(
                ['rm', '--recursive', '--force', 'smr.lock']
            )
            self._check_tool(
                ['flock', '--exclusive', 'smr.lock', '--command', 'true']
            )

    def _ensure_remote_directory(self):
        """Ensure that the remote backup directory exists and is usable.

        If the directory does not exist it will be created.

        Raises:
            RuntimeError: if the path is unusable as backup destination.
        """
        path = self.ssh_host.path

        # Create if missing
        rc, _out, err = self._ssh(['mkdir', '--parents', path])

        if rc != 0:
            raise SSHSetupError(
                f'Create remote directory failed ("{path}"): {err}',
                _('Could not create remote backup directory: {path}').format(
                    path=path) + '\n\n' + _('Details:') + f'\n{err}'
            )
