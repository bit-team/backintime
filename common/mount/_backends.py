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
from exceptions import HashCollision


class Backend:

    class Type(Enum):
        LOCAL = auto()
        SSH = auto()

    TYPE = None

    def __init__(self, cfg):
        self.cfg = cfg
        self.currentMountpoint = None
        self._fingerprint = None

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    def _set_fingerprint(self, mount_data: dict[str, str]):
        fp = str(self.TYPE) + ': '

    def mount(self):
        raise NotImplementedError

    def umount(self):
        raise NotImplementedError


class LocalBackend(Backend):
    TYPE = Backend.Type.LOCAL

    def __init__(self, cfg):
        self.cfg = cfg
        self.profile_id = cfg.currentProfile()
        self.hash_id = cfg.current_hash_id
        self.pid = str(getpass.getuser())  # PID analog
        self.mount_root = Path(cfg._LOCAL_MOUNT_ROOT)
        self.mountpoint = self.mount_root / self.hash_id / "mountpoint"
        self.lock_path = self.mount_root / self.hash_id / "locks"
        self.umount_info = self.mount_root / self.hash_id / "umount"
        self.current_kwargs = {"mode": self.TYPE}

    def mount(self):
        self._prepare_mount_structure()
        self._acquire_mount_lock()

        # Prüfen ob schon gemountet
        if self._is_mounted():
            if not self._compare_umount_info():
                raise HashCollision(f"Hash collision for {self.hash_id}")
            logger.info(f"Mountpoint {self.mountpoint} already mounted")
        else:
            self._write_umount_info()
            logger.info(f"Mounted {self.mountpoint}")

        return str(self.mountpoint)

    def umount(self):
        self._acquire_mount_lock()
        if self.mountpoint.exists():
            # bei lokal: nur symlink/lock entfernen
            if self.lock_path.exists():
                for f in self.lock_path.iterdir():
                    f.unlink()
            if self.umount_info.exists():
                self.umount_info.unlink()
        self._release_mount_lock()
        logger.info(f"Unmounted {self.mountpoint}")

    def _prepare_mount_structure(self):
        self.mountpoint.mkdir(parents=True, exist_ok=True)
        self.lock_path.mkdir(parents=True, exist_ok=True)

    def _acquire_mount_lock(self):
        lock_file = self.lock_path / f"{self.pid}.lock"
        lock_file.write_text(self.pid)

    def _release_mount_lock(self):
        lock_file = self.lock_path / f"{self.pid}.lock"
        if lock_file.exists():
            lock_file.unlink()

    def _is_mounted(self):
        # lokal: nur prüfen, ob mountpoint existiert
        return self.mountpoint.exists()

    def _write_umount_info(self):
        data_string = json.dumps(self.current_kwargs)
        self.umount_info.write_text(data_string)

    def _compare_umount_info(self):
        if not self.umount_info.exists():
            return True
        saved = json.loads(self.umount_info.read_text())
        return saved == self.current_kwargs


class SSHBackend(Backend):
    TYPE = Backend.Type.SSH
