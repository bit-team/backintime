# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
# pylint: disable=duplicate-code
"""Backends for the mounting subsystem"""
from __future__ import annotations
from enum import Enum, auto
from pathlib import Path
import os
import subprocess
import logger
import tools
import sshcore
from sshcore import SSHHost
from ._error import MountError


try:
    _('Warning')
except NameError:
    def _(val):
        return val


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
        """See `MountManager.fingerprint`"""
        return self._fingerprint

    def set_fingerprint(self, fingerprint: str):
        """See `MountManager.fingerprint`"""
        self._fingerprint = fingerprint

    def get_fingerprint_base(self) -> str:
        """Return backend-specific string for fingerprint calculation."""
        raise NotImplementedError

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
                + f'\n{self.path}\n\n'
                + _('If it is on a removable drive, please plug it in.')
                + ' ' + _('Then press OK.')
            )
            log_msg = f"Can't find backup destination directory. {self.path}"

            raise MountError(log_msg, gui_msg)

    def mount(self):
        """See ``Backend.mount()``"""

    def umount(self):
        """See ``Backend.umount()``"""


class SSHBackend(Backend):
    """SSH mount backend"""
    TYPE = Backend.Type.SSH
    ERR_MSG_CONTEXT = (
        _('Back In Time could not connect to the '
          'remote backup location.')
        + '\n\n' + _('Reason:') + '\n'
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

        # final host
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

        self.path = self.mount_root / self.fingerprint / 'ssh'

    def get_fingerprint_base(self) -> str:
        return f'{self.TYPE}: {self.host}'

    def _check_tcp_connectivity(self):
        # effective SSH entry point
        is_proxy = self.host.proxy is not None
        target = self.host.proxy if is_proxy else self.host

        if not sshcore.can_connect_tcp(target):
            hp = f'{target.host}:{target.port}'

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

            gui_msg = f'{self.ERR_MSG_CONTEXT}{gui_msg}'

            raise MountError(log_msg, gui_msg)

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
            text=True,
            check=False
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

        # Finalize
        remote_cmd = ssh + remote_cmd

        logger.debug(f'Calling {remote_cmd}...')
        proc = subprocess.Popen(  # pylint: disable=consider-using-with
            remote_cmd,
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
                _('The remote backup directory is missing or is not a '
                  'valid directory.')
            ),
            (
                ['test', '-w', path],
                'Remote path is not writable',
                _('Write access to the remote backup directory was '
                  'denied (missing permissions).')
            ),
            (
                ['test', '-x', path],
                'Remote path is not accessible/searchable',
                _('Access to the remote backup directory denied '
                  '(missing permissions).')
            )
        ]

        for cmd, log_msg, gui_msg in checks:
            rc, _out, err = self._ssh_command(cmd)

            if rc != 0 and err:
                err = err.strip()
                log_msg = f'{log_msg}: "{path}" ({err})'

                raise MountError(
                    f'{log_msg}: "{path}" ({err})',
                    self.ERR_MSG_CONTEXT + gui_msg + '\n\n'
                    + _('Path:') + f'\n{path}'
                )

    def validate(self):
        """See ``Backend.validate()``"""
        if not self.host.host:
            raise MountError(
                'SSH host not configured',
                self.ERR_MSG_CONTEXT + _('No SSH host configured.')
            )

        if not self.path:
            raise MountError(
                'SSH destination path not set',
                self.ERR_MSG_CONTEXT
                + _('No destination backup directory configured.')
            )

        if self.cfg.sshCheckPingHost():  # See issue #2482
            self._check_tcp_connectivity()

        self._check_host_auth()

        self._check_remote_directory_access()

    def mount(self):
        """See ``Backend.mount()``"""
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
                f'ssh_command=ssh -J {self.host.proxy.user_host_port}'
            ])

        logger.debug(f'Calling mount command: {cmd}')
        proc = subprocess.Popen(  # pylint: disable=consider-using-with
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
                self.ERR_MSG_CONTEXT
                + _('Could not mount the remote backup location.')
                + '\n\n'
                + _('Details:')
                + f'\n{err}'
            )
            raise MountError(log_msg, gui_msg)

        logger.info(
            'Remote directory mounted '
            f'(source: {self.host.user_host_port} "{self.host.path}" '
            f'-> target: "{self.path}")')

    def umount(self):
        if tools.is_mounted(self.path):
            cmd = ['fusermount', '-u', str(self.path)]
            logger.debug(f'Calling {cmd=}...')
            subprocess.run(cmd, check=False)
