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
from ._error import MountError


class MountManager:

    LOCK_SUFFIX = 'lock'

    def __init__(self, backend, encryptor, cfg):
        self.backend = backend
        self.encryptor = encryptor
        self.cfg = cfg
        self._lock_mountpoint = None

        logger.debug(
            f'{self.backend=} {self.encryptor=} '
            f'{self.mount_root=}',
            self
        )

    @property
    def fingerprint(self) -> str:
        return self.encryptor.fingerprint

    @property
    def mount_root(self) -> Path:
        return self.backend.mount_root

    def is_initialized(self) -> bool:
        return self.encryptor.is_initialized()

    def initialize(self):
        return self.encryptor.initialize()

    def validate(self):
        """Check if backend and encryptor are ready.

        Raises: MountError
        """
        self.backend.validate()
        self.encryptor.validate()

    def mount(self):
        # Workaround
        self.cfg.PLUGIN_MANAGER.load(cfg=self.cfg)
        self.cfg.PLUGIN_MANAGER.mount(self.cfg.currentProfile())

        with self._process_lock():
            self._acquire_mountpoint_lock()

            self.backend.validate()
            self.backend.mount()

            self.encryptor.validate()
            self.encryptor.mount()
            # self._write_umount_info()

    def umount(self):
        self.cfg.PLUGIN_MANAGER.load(cfg=self.cfg)
        self.cfg.PLUGIN_MANAGER.unmount(self.cfg.currentProfile())

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
        """Check for active mountpoint locks but excluding own lock"""
        active = False

        for fp in self.mount_root.glob(f'*.{self.LOCK_SUFFIX}'):

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
                raise RuntimeError('Process lock - Timeout')

            sleep(1)

        logger.debug(
            f'Process lock - Acquire {fp.relative_to(self.mount_root)}',
            self
        )

        # ??? Isn't touch enough?
        fp.write_text(str(pid))

        try:
            yield

        finally:
            logger.debug(
                f'Process lock - Release {fp.relative_to(self.mount_root)}',
                self
            )
            fp.unlink(missing_ok=True)

    def _acquire_mountpoint_lock(self):
        """Long-term lock for a mountpoint, preventing unmount while in use."""
        pid = os.getpid()

        self._lock_mountpoint = self.mount_root / self.fingerprint \
            / 'locks' / f'{pid}.{self.LOCK_SUFFIX}'

        # owner only 0o700 -rwx------
        self._lock_mountpoint.parent.mkdir(
            mode=0o700, parents=True, exist_ok=True)

        logger.debug(
            'Mount point lock - Acquire '
            f'{self._lock_mountpoint.relative_to(self.mount_root)}',
            self
        )
        self._lock_mountpoint.write_text(str(pid))

    def _release_mountpoint_lock(self):
        """Long-term lock for a mountpoint, preventing unmount while in use."""
        if self._lock_mountpoint is None:
            # No mount beforehand
            return

        if not self._lock_mountpoint.exists():
            import traceback
            traceback.print_stack(limit=4)
            logger.error(
                f'Mount point lock - Unexpected state. {self._lock_mountpoint} '
                'does not exist.', self
            )
            return

        logger.debug(
            'Mount point lock - Release '
            f'{self._lock_mountpoint.relative_to(self.mount_root)}',
            self
        )
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
        mode = cfg.snapshotsMode()

        if 'local' in mode:
            backend_type = Backend.Type.LOCAL

        if 'gocryptfs' in mode:
            encryptor_type = Encryptor.Type.GOCRYPTFS
        else:
            encryptor_type = Encryptor.Type.NONE

        backend = cls.BACKENDS[backend_type](cfg)
        encryptor = cls.ENCRYPT[encryptor_type](cfg, backend)

        return MountManager(backend, encryptor, cfg)
