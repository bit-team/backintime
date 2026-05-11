# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Backends for the mounting subsystem"""
from __future__ import annotations
from enum import Enum, auto
from pathlib import Path
from typing import Optional
import os
import socket
import ipaddress
import subprocess
import bitbase
import logger
import tools
from ._error import MountError


class Backend:
    """Base class for mount backends"""

    class Type(Enum):
        """Supported backend types"""
        LOCAL = auto()
        SSH = auto()

    TYPE = None

    def __init__(self, cfg):
        self.cfg = cfg
        # Refactor: bitbase.XDG_DATA_DIR / 'backintime' / 'mnt'
        self.mount_root = Path(self.cfg._LOCAL_MOUNT_ROOT)
        # logger.critical(f'{self=} {self.mount_root=}', self)

        self._fingerprint = None
        self.path = None

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    def set_fingerprint(self, fingerprint: str):
        """See `MountManager.fingerprint`"""
        self._fingerprint = fingerprint

    def get_fingerprint_base(self) -> str:
        """Return backend-specific string for fingerprint calculation."""
        raise NotImplementedError

    def prepare(self):
        """Prepare the state for backend operations.
        """
        pass

    def validate(self):
        """Everything correct setup"""
        raise NotImplementedError

    def mount(self):
        """Mount the backend"""
        raise NotImplementedError

    def umount(self):
        """Release the backend mount"""
        raise NotImplementedError


class LocalBackend(Backend):
    """No-mounting backend"""
    TYPE = Backend.Type.LOCAL

    def __init__(self, cfg):
        super().__init__(cfg)
        self.path = cfg.get_backup_destination_path(cfg.currentProfile())

        # logger.critical(f'{self=} {self.path=}')

    def get_fingerprint_base(self) -> str:
        """See ``Backend.get_fingerprint_base()``"""
        return str(self.TYPE) + f': {self.path}'

    def validate(self):
        """Check if ready to mount.

        Raises: MountError
        """
        if not self.path.exists():
            gui_msg = (
                _("Can't find backup destination directory.")
                + f'\n{self.path}'
                + '\n\n'
                + _('If it is on a removable drive, please plug it in.')
                + ' ' + _('Then press OK.')
            )
            log_msg = f"Can't find backup destination directory. {self.path}"

            raise MountError(log_msg, gui_msg)

    def mount(self):
        """See ``Backend.mount()``"""

    def umount(self):
        """See ``Backend.umount()``"""


class SSHHost:
    """SSH connection parameters."""

    DEFAULT_PORT = bitbase.DEFAULT_SSH_PORT

    def __init__(
            self,
            host: str,
            user: str = None,
            port: int = DEFAULT_PORT,
            priv_key_file: str = None,
            proxy: Optional[SSHHost] = None,
            path: str = './',
    ):
        self.host = self.ensure_ipv6_brackets(host)
        self.user = user
        self.port = port
        self.priv_key_file = priv_key_file
        self.proxy = proxy
        self.path = path

    @staticmethod
    def ensure_ipv6_brackets(address: str) -> str:
        """Escape IP addresses with square brackets ``[]`` if they are IPv6.

        IPv6 addresses contain ``:``, which conflicts with separators used in
        contexts like SSH/URLs (e.g. host:port). Wrapping IPv6 in ``[]`` ensures
        unambiguous parsing.

        If it is an IPv4 address or a hostname (lettersonly) nothing is changed.

        Args:
            address (str): IP-Address to escape if needed.

        Returns:
            str: The address, escaped if it is IPv6.

        Dev note (buhtz, 2026-04): The host shouldn't to this escaping. It
        becomes relevant only when the shell command is constructed. Move it
        their if #1966 is solved.
        """

        try:
            ip = ipaddress.ip_address(address)

        except ValueError:
            # invalid IP, e.g. a hostname
            return address

        if ip.version == 6:
            return f'[{address}]'

        return address

    @property
    def user_host(self) -> str:
        if self.user:
            return f'{self.user}@{self.host}'
        else:
            return self.host

    @property
    def user_host_path(self) -> str:
        return f'{self.user_host}:{self.path}'

    @property
    def user_host_port(self) -> str:
        return f'{self.user_host}:{self.port}'

    def __str__(self) -> str:
        """Return unique string for mount fingerprint"""
        return (
            f'{self.user_host_port};{self.path};{self.priv_key_file} '
            f'-> {self.proxy}'
        )


class SSHBackend(Backend):
    """SSH mounting backend"""
    TYPE = Backend.Type.SSH
    ERR_MSG_CONTEXT = (
        _('Back In Time could not connect to the '
          'remote backup location.')
        + '\n\n'
        + _('Reason:')
        + '\n'
    )

    def __init__(self, cfg):
        super().__init__(cfg)

        # jump host
        if cfg.sshProxyHost():
            proxy = SSHHost(
                host=cfg.sshProxyHost(),
                user=cfg.sshProxyUser(),
                port=cfg.sshProxyPort()
            )
        else:
            proxy = None

        # TODO: nice, ionice, nocache
        self.host = SSHHost(
            host=cfg.sshHost(),
            user=cfg.sshUser(),
            port=cfg.sshPort(),
            priv_key_file=cfg.sshPrivateKeyFile(),
            proxy=proxy,
            path=cfg.sshSnapshotsPath()
        )

    def set_fingerprint(self, fingerprint: str):
        """See `MountManager.fingerprint`"""
        super().set_fingerprint(fingerprint)

        # self.path = cfg.get_backup_destination_path(cfg.currentProfile())
        self.path = self.mount_root / self.fingerprint / 'mountpoint'

    def get_fingerprint_base(self) -> str:
        return f'{self.TYPE}: {self.host}'

    def _check_host_reachable(self, timeout: float = 2.0):
        target = self.host.proxy if self.host.proxy else self.host

        try:
            with socket.create_connection(
                (
                    # See SSHHost.ensure_ipv6_brackets() about that strip()
                    target.host.strip('[]'),
                    target.port
                ),
                timeout=timeout
            ):
                return

        except OSError as exc:
            log_msg = f'SSH host unreachable: {target.host}:{target.port}'
            gui_msg = _('Could not reach the SSH host:') \
                + f'\n{target.host}:{target.port}'
            raise MountError(log_msg, f'{self.ERR_MSG_CONTEXT}{gui_msg}') from exc

    def _check_host_auth(self):
        cmd = ['ssh']

        if self.host.priv_key_file:
            cmd.extend([
                '-o',
                f'IdentityFile={self.host.priv_key_file}'
            ])

        # Jump host
        if self.host.proxy:
            cmd.extend(['-J', self.host.proxy.user_host_port])

        cmd.extend([
            # no interactive password prompt
            '-o', 'BatchMode=yes',
            # force key auth
            '-o', 'PreferredAuthentications=publickey',
            # prevent freeze/hanging
            '-o', 'ConnectTimeout=5',
        ])

        # port
        cmd.extend(['-p', str(self.host.port)])

        cmd.extend([
            self.host.user_host,
            'exit'
        ])

        logger.debug(f'Call SSH auth check command: {cmd}', self)
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if proc.returncode != 0:
            err = proc.stderr.strip()
            log_msg = (
                'Passwordless SSH authentication failed for '
                f'{self.host} | Error: {err} | Command: {cmd}'
            )
            logger.error(log_msg)
            gui_msg = (
                _('SSH authentication failed for:')
                + f'\n{self.host}\n\n'
                + _('Details:')
                + f'\n{err}'
            )
            raise MountError(log_msg, f'{self.ERR_MSG_CONTEXT}{gui_msg}')

    def _ssh_command(self, remote_cmd: list[str]) -> tuple:
        ssh = ['ssh']

        # specifying key file here allows to override for potentially
        # conflicting .ssh/config key entry
        if self.host.priv_key_file:
            ssh += ['-o', f'IdentityFile={self.host.priv_key_file}']

        # Proxy (aka Jump host)
        if self.host.proxy:
            ssh += ['-J', self.host.proxy.user_host_port]

        # remote port
        ssh += ['-p', str(self.host.port)]

        # user@host
        ssh.append(self.host.user_host)

        proc = subprocess.Popen(
            ssh + remote_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, err = proc.communicate()

        return proc.returncode, out, err

    def _check_remote_directory_access(self):
        """Check if the remote backup directory is usable.

        Checks:
            - path exists
            - path is a directory
            - path is writable
            - path is executable/searchable

        Raises:
            MountError: if one requirement is not fulfilled.
        """
        path = self.host.path

        checks = [
            (
                ['test', '-d', path],
                'Remote path is not a directory or does not exist"',
                _('The remote backup directory does not exist or is not '
                'a directory.') + '\n\n' + _('Path:') + f'\n{path}'
            ),
            (
                ['test', '-w', path],
                'Remote path is not writable',
                _('The remote backup directory is not writable.')
            ),
            (
                ['test', '-x', path],
                'Remote path is not accessible/searchable',
                _('The remote backup directory cannot be accessed.')
            )
        ]

        for cmd, log_msg, gui_msg in checks:
            rc, _, err = self._ssh_command(cmd)

            if rc != 0 and err:
                err = err.strip()
                log_msg = f'{log_msg}: "{path}" ({err})'

                raise MountError(
                    f'{log_msg}: "{path}" ({err})',
                    self.ERR_MSG_CONTEXT + gui_msg + '\n\n'
                    + _('Path:') + f'\n{path}'
                )

    def validate(self):
        # TODO
        if not self.host.host:
            raise MountError(
                'SSH host not configured',
                self.ERR_MSG_CONTEXT + _('No SSH host configured.')
            )

        if not self.path:
            raise MountError(
                'SSH destination path not set',
                self.ERR_MSG_CONTEXT + _('No estination backup directory configured.')
            )

        if self.cfg.sshCheckPingHost():
            self._check_host_reachable()

        self._check_host_auth()

        self._check_remote_directory_access()

    def mount(self):
        if tools.is_mounted(self.path):
            logger.info('SSH directory already mounted')
            return

        self.path.mkdir(parents=True, exist_ok=True)

        cmd = [
            'sshfs',
            # keep connection alive
            '-o', 'ServerAliveInterval=240',
            # disable ssh banner
            '-o', 'LogLevel=Error',
        ]

        # key file
        if self.host.priv_key_file:
            cmd.extend(['-o', f'IdentityFile={self.host.priv_key_file}'])

        # port
        cmd.extend(['-p', f'{self.host.port}'])

        cmd.extend([
            '-o', 'idmap=user',
            '-o', 'cache_dir_timeout=2',
            '-o', 'cache_stat_timeout=2'
        ])

        cmd.extend([
            self.host.user_host_path,
            self.path  # mountpoint
        ])

        # bugfix: sshfs doesn't mount if locale in LC_ALL is not available on
        # remote host
        # LANG or other environment variable are no problem.
        env = os.environ.copy()
        if 'LC_ALL' in list(env.keys()):
            env['LC_ALL'] = 'C'

        # SSH Proxy (aka Jump host)
        if self.host.proxy:
            cmd.extend([
                '-o',
                'ssh_command=ssh -J '
                f'{self.host.proxy.user_host_port}'
            ])

        logger.debug(f'Call mount command: {cmd}', self)
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        err = proc.communicate()[1]

        if proc.returncode != 0:
            err = err.strip()
            log_msg = (
                f'Mount failed via "{cmd}"'
                + f' | Error: {err}'
                + f' | Return code: {proc.returncode}'
            )
            logger.critical(log_msg)

            gui_msg = (
                _('Could not mount the remote backup location.')
                + '\n\n'
                + _('Details:')
                + '\n{err}'
            )
            raise MountError(log_msg, self.ERR_MSG_CONTEXT + gui_msg)

        logger.info(
            'Remote directory mounted '
            f'(source: {self.host.user_host_port} "{self.host.path}" '
            f'-> target: "{self.path}")')

    def umount(self):
        if tools.is_mounted(self.path):
            subprocess.run(['fusermount', '-u', str(self.path)], check=False)
