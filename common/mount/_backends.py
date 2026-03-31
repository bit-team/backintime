# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import getpass
import logger
import json
from enum import Enum, auto
from pathlib import Path
# from exceptions import HashCollision
from ._error import MountError


class Backend:

    class Type(Enum):
        LOCAL = auto()
        SSH = auto()

    TYPE = None

    def __init__(self, cfg):
        self.cfg = cfg
        # Refactor: bitbase.XDG_DATA_DIR / 'backintime' / 'mnt'
        self.mount_root = Path(self.cfg._LOCAL_MOUNT_ROOT)

        # logger.debug(f'{self.mount_root=}', self)

    def get_fingerprint_base(self) -> str:
        """String represnation of the backend config for later use in a hash"""
        raise NotImplementedError

    def validate(self):
        """Everything correct setup"""
        raise NotImplementedError

    def mount(self):
        """Mount the backend"""
        raise NotImplementedError

    def umount(self):
        """Relase the backend mount"""
        raise NotImplementedError


class LocalBackend(Backend):
    TYPE = Backend.Type.LOCAL

    def __init__(self, cfg):
        super().__init__(cfg)
        self.path = cfg.get_backup_destination_path(cfg.currentProfile())

        # logger.debug(f'{self.path=}', self)

    def get_fingerprint_base(self) -> str:
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
        return None
        # self._prepare_mount_structure()
        # self._acquire_mount_lock()

        # # Prüfen ob schon gemountet
        # if self._is_mounted():
        #     if not self._compare_umount_info():
        #         raise HashCollision(f"Hash collision for {self.hash_id}")
        #     logger.info(f"Mountpoint {self.mountpoint} already mounted")
        # else:
        #     self._write_umount_info()
        #     logger.info(f"Mounted {self.mountpoint}")

        # return str(self.mountpoint)

    def umount(self):
        pass
        # self._acquire_mount_lock()
        # if self.mountpoint.exists():
        #     # bei lokal: nur symlink/lock entfernen
        #     if self.lock_path.exists():
        #         for f in self.lock_path.iterdir():
        #             f.unlink()
        #     if self.umount_info.exists():
        #         self.umount_info.unlink()
        # self._release_mount_lock()
        # logger.info(f"Unmounted {self.mountpoint}")

    # def _prepare_mount_structure(self):
    #     self.mountpoint.mkdir(parents=True, exist_ok=True)
    #     self.lock_path.mkdir(parents=True, exist_ok=True)

    # def _acquire_mount_lock(self):
    #     lock_file = self.lock_path / f"{self.pid}.lock"
    #     lock_file.write_text(self.pid)

    # def _release_mount_lock(self):
    #     lock_file = self.lock_path / f"{self.pid}.lock"
    #     if lock_file.exists():
    #         lock_file.unlink()

    # def _is_mounted(self):
    #     # lokal: nur prüfen, ob mountpoint existiert
    #     return self.mountpoint.exists()

    # def _write_umount_info(self):
    #     data_string = json.dumps(self.current_kwargs)
    #     self.umount_info.write_text(data_string)

    # def _compare_umount_info(self):
    #     if not self.umount_info.exists():
    #         return True
    #     saved = json.loads(self.umount_info.read_text())
    #     return saved == self.current_kwargs


class SSHBackend(Backend):
    TYPE = Backend.Type.SSH
