# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Backends for the mounting subsystem"""
from enum import Enum, auto
from pathlib import Path
from ._error import MountError
import logger


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

        logger.critical(f'{self=} {self.path=}')

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


# class SSHBackend(Backend):
#     TYPE = Backend.Type.SSH
