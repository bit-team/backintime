# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import hashlib
import tools
import logger
from contextlib import contextmanager
from time import sleep
from pathlib import Path
from ._backends import Backend, LocalBackend, SSHBackend
from ._encryptors import Encryptor, NoEncryption, GoCryptFS


class MountManager:

    LOCK_SUFFIX = 'lock'

    def __init__(self, backend, encryptor, cfg):
        self.backend = backend
        self.encryptor = encryptor
        self.cfg = cfg
        # Refactor: bitbase.XDG_DATA_DIR / 'backintime' / 'mnt'
        self._mount_root = Path(self.cfg._LOCAL_MOUNT_ROOT)

    @property
    def fingerprint(self) -> str:
        data = '|'.join([
            self.backend.get_fingerprint_base(),
            self.encryptor.get_fingerprint_base()
        ])
        return hashlib.sha256(data.encode()).hexdigest()[:12]

    def is_initialized(self, path: Path) -> bool:
        return self.encryptor.is_initialized(path)

    def _get_mounpoint_lock_path(self):
        return self.mount_root / self.fingerprint / 'locks'

    def initialize(self):
        return self.encryptor.initialize()

    def mount(self):
        with self._process_lock():
            self._acquire_mountpoint_lock()
            try:
                self.backend.mount()
                self.encryptor.mount(self.backend)
                # self._write_umount_info()
            finally:
                self._release_mountpoint_lock()

    def umount(self):
        try:
            if not self._mountpoint_locks_active():
                self.encryptor.umount()
                self.backend.umount()
            else:
                logger.debug(
                    'Skipping unmount, because mountpoint in use by other '
                    'processes.', self
                )
        finally:
            self._release_mountpoint_lock()

    def _process_locks_active(self, path: Path) -> bool:
        """Check existence of active and foreign locks and clean stale ones.

        The lock owning process is specified by the PID contained in the
        filename of the lock file used. Lock files of the current process are
        ignored and ``False`` is returned.
        If a lock exist but its process not the lock is removed and
        ``False`` returned.

        Returns:
            ``True`` if there are active locks in ``path``.
        """
        active = False

        for fp in path.glob(f'*.{self.LOCK_SUFFIX}'):

            pid = int(fp.stem)

            if pid == os.getpid():
                # Ignore process's own lock files.
                continue

            if tools.processAlive(pid):
                active = True
                continue

            logger.debug(f'Remove stale lock {fp}', self)
            fp.unlink()

        return active

    def _mountpoint_locks_active(self) -> bool:
        """Check for active mountpoint locks excluding own lock"""
        active = False
        for fp in self._locks_path.glob(f'*.{self.LOCK_SUFFIX}'):
            pid = int(fp.stem)
            if pid == os.getpid():
                continue
            if tools.processAlive(pid):
                active = True
        return active

    @contextmanager
    def _process_lock(self, timeout: int = 60):
        """Short-term lock to prevent concurrent mount modifications.

        Dev note (buhtz, 2026-03): Refactoring and use of flock.py
        """
        pid = os.getpid()
        fp = self.mount_root / f'{pid}.{self.LOCK_SUFFIX}'
        count = 0

        while self._process_locks_active(self.mount_root):
            count += 1

            if count >= timeout:
                raise RuntimeError('Mountprocess lock timeout')

            sleep(1)

        logger.debug(f'Acquire process lock {fp}', self)

        # ??? Isn't touch enough?
        fp.write_text(str(pid))

        try:
            yield

        finally:
            logger.debug(f'Release process lock {fp}', self)
            fp.unlink(missing_ok=True)

    def _acquire_mountpoint_lock(self):
        """Long-term lock for a mountpoint, preventing unmount while in use."""
        pid = os.getpid()
        fp = self._get_mounpoint_lock_path() / f'{pid}.{self.LOCK_SUFFIX}'

        # owner only 0o700 -rwx------
        fp.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

        logger.debug(f'Acquire mount point lock {fp}', self)
        fp.write_text(str(pid))

        self._lock_mountpoint = fp

    def _release_mountpoint_lock(self):
        """Long-term lock for a mountpoint, preventing unmount while in use."""
        if not self._lock_mountpoint or self._lock_mountpoint.exists():
            logger.error(
                f'Unexpected state. Mount point lock {self._lock_mountpoint} '
                'does not exist.', self
            )
            return

        logger.debug(f'Release mount point lock {self._lock_mountpoint}', self)
        self._lock_mountpoint.unlink(missing_ok=True)
        self._lock_mountpoint = None


class MountFactory:

    BACKENDS = {
        Backend.Type.LOCAL: LocalBackend,
        Backend.Type.SSH: SSHBackend,
    }

    ENCRYPT = {
        Encryptor.Type.NONE: NoEncryption,
        Encryptor.Type.GOCRYPTFS: GoCryptFS,
    }

    @classmethod
    def create(cls, cfg):
        # backend = cls.BACKENDS[cfg.backend](cfg)
        # encryptor = cls.ENCRYPT[cfg.encryption](cfg)

        if cfg.snapshotsMode() == 'local':
            return MountManager(
                cls.BACKENDS[Backend.Type.LOCAL](cfg),
                cls.ENCRYPT[Encryptor.Type.NONE](cfg),
                cfg
            )

        raise NotImplementedError(cfg.snapshotsMode())
