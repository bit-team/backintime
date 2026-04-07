# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Backends for the mounting subsystem"""
from typing import __future__
from enum import Enum, auto
from pathlib import Path
# import logger
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
            raise MountError(
                _("Can't find backup destination directory."),
                _('If it is on a removable drive, please plug it in.')
                + ' ' + _('Then press OK.'),
                self.path
            )

    def mount(self):
        """See ``Backend.mount()``"""

    def umount(self):
        """See ``Backend.umount()``"""


class SSHHost:
    """SSH connection parameters."""

    DEFAULT_PORT = 22

    def __init__(
            self,
            host: str,
            user: str = None,
            port: int = SSHHost.DEFAULT_PORT,
            identity_file: str = None,
            proxy: Optional[SSHHost]
    ):
        self.host = host
        self.user = user
        self.port = port
        self.identity_file = identity_file
        self.proxy = proxy

    def __str__(self) -> str:
        """Return unique string for mount fingerprint"""
        return f'{self.user}@{self.host}:{self.port} -> {self.proxy}'


class SSHBackend(Backend):
    """SSH mounting backend"""
    TYPE = Backend.Type.SSH

    def __init__(self, cfg):
        super().__init__(cfg)

        # TODO: Proxy
        self.host = SSHHost(
            host=cfg.get_ssh_host(),
            user=cfg.get_ssh_user(),
            port=cfg.get_ssh_port(),
            identity_file=cfg.get_ssh_identity_file()
        )
        # self.path = cfg.get_backup_destination_path(cfg.currentProfile())
        self.path = self.mount_root / self.fingerprint / 'mountpoint'

    def get_fingerprint_base(self) -> str:
        return f'{self.TYPE}: {self.host}'

    def validate(self):
        # TODO
        if not self.host.host:
            raise MountError('SSH host not configured')

        if not self.path:
            raise MountError('SSH destination path not set')

    def mount(self):
        mount_point = self.mount_root / self.get_fingerprint_base() / 'mountpoint'
        mount_point.mkdir(parents=True, exist_ok=True)
        if tools.is_mounted(mount_point):
            return

        cmd = ['sshfs']
        if self.host.identity_file:
            cmd += ['-o', f'IdentityFile={self.host.identity_file}']
        cmd += [
            f'{self.host.user}@{self.host.host}:{self.path}',
            str(mount_point)
        ]
        subprocess.run(cmd, check=True)

        self.path = mount_point

    def umount(self):
        if tools.is_mounted(self.path):
            subprocess.run(['fusermount', '-u', str(self.path)], check=False)
