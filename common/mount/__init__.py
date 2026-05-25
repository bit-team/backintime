# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Mount subsystem for Back In Time.

This module provides the core abstractions and utilities for handling
filesystem mounts, including encryption.

Responsibilities:
- Managing mount lifecycle (mount, unmount, validation, initialization)
- Coordinating backend-specific mount operations (e.g., local, SSH)
- Supporting encryption strategies via encryptors (e.g., gocrytpfs)
- Providing a unified fingerprint mechanism for mount identification and
  mountpoint reference counting.

Mountpoint layout and rules for all profile types.

Base directory:
    ~/.local/share/backintime/mnt/<fp>/

Where:
    <fp> = fingerprint derived from the full mount setup configuration,
           including backend (local or SSH) AND optional encryptor.

Profiles:
    Users backup destination path: ~/MyBackups

    local (unencrypted):
        No mount logic.
        rsync works on:
            ~/MyBackups

    local_gocryptfs (encrypted):
        Backend mount:
            ~/MyBackups
        Encryptor:
            Mounts backend path to <fp>/mountpoint
        rsync works on:
            <fp>/mountpoint

    ssh (unencrypted):
        Backend mount (sshfs):
            Mounts user@localhost:/home/user/MyBackups' to <fp>/ssh
        rsync works on:
            <fp>/ssh

    ssh_gocryptfs (encrypted over SSH):
        Backend mount (sshfs):
            Mounts user@localhost:/home/user/MyBackups' to <fp>/ssh
        Encryptor (gocryptfs):
            Mounts <fp>/ssh to <fp>/mountpoint
        rsync works on:
            <fp>/mountpoint

Rules:
  - The encryptor (if present) is always mounted on top of the backend.
  - Only the ssh_gocryptfs profile introduces an additional intermediate
    mount directory ("ssh").
  - Lock files belong to the final mountpoint directory.
  - The fingerprint (<fp>) is derived from the COMPLETE setup to avoid
    collisions between different encryptor configurations on the same backend.
"""
import os
import subprocess
import hashlib
from contextlib import contextmanager
from time import sleep
from pathlib import Path
import tools
import logger
import bitbase
from password import Password_Cache
from ._backends import Backend, LocalBackend, SSHBackend, SSHHost  # noqa: F401
from ._encryptors import Encryptor, NoEncryption, GoCryptFS
from ._error import MountError  # noqa: F401


LOCK_SUFFIX = 'lock'

_BACKENDS = {
    Backend.Type.LOCAL: LocalBackend,
    Backend.Type.SSH: SSHBackend,
}

_ENCRYPT = {
    Encryptor.Type.NONE: NoEncryption,
    Encryptor.Type.GOCRYPTFS: GoCryptFS,
}


class MountManager:
    """Orchestrates and manages filesystem mounts.

    The manager is responsible for coordinating mount operations across
    different backends and encryptors. It provides the interface for
    initializing, validating, mounting, and unmounting filesystems. It
    maintaines maintaining mount state, fingerprints, and error handling.

    Use the factory method ``MountManager.create()`` to get an instance.
    """
    @classmethod
    def create(cls, cfg):
        """Factory method to get a MountManager based on the current
        configuration and profile
        """
        mode = cfg.snapshotsMode()

        if 'local' in mode:
            backend_type = Backend.Type.LOCAL
        elif 'ssh' in mode:
            backend_type = Backend.Type.SSH
        else:
            backend_type = None

        if 'gocryptfs' in mode:
            encryptor_type = Encryptor.Type.GOCRYPTFS
        else:
            encryptor_type = Encryptor.Type.NONE

        try:
            backend = _BACKENDS[backend_type](cfg)
            encryptor = _ENCRYPT[encryptor_type](cfg, backend)

        except Exception as exc:
            print(f'{mode=}')  # DEBUG
            raise exc

        manager = MountManager(backend, encryptor, cfg)

        return manager

    def __init__(self, backend, encryptor, cfg):
        """Don't directly instantiate. Use ``MountManager.create()``
        instead.
        """
        self.backend = backend
        self.encryptor = encryptor
        self.cfg = cfg
        self._lock_mountpoint = None

        logger.debug(
            f'{self.backend=} {self.encryptor=} '
            f'{self.mount_root=}',
            self
        )

        self._ensure_password_cache()

        self.backend.set_fingerprint(self._compute_fingerprint())
        self.encryptor.setup()

    def _compute_fingerprint(self) -> str:
        """Compute a unique mount fingerprint.

        The fingerprint is a deterministic hex string and based on the
        encryptors configuration parameters and the backend.

        Returns:
            A SHA256 hash cut to a 12-character hexadecimal string.

        """
        data = '|'.join([
            self.backend.get_fingerprint_base(),
            self.encryptor.get_fingerprint_base()
        ])
        logger.debug(f'fingerprint: {data=}', self)

        return hashlib.sha256(data.encode()).hexdigest()[:12]

    def _ensure_password_cache(self):
        """Start the password cache process if isn't already"""
        if not self.cfg.passwordUseCache():
            return

        cache = Password_Cache(self.cfg)

        if cache.status():
            # Still running
            logger.debug('Password cache already running')
            return

        cmd = [
            tools.which(bitbase.BINARY_NAME_CLI),
            'pw-cache',
            'start'
        ]
        logger.debug(f'Call command: {cmd}')
        with subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ) as proc:
            if proc.returncode:
                logger.error(
                    'Password cache start failed with return '
                    f'code {proc.returncode}',
                    self
                )
            else:
                logger.debug('Password cache started')

    @contextmanager
    def mounted(self):
        """Mount on enter and umount on exit."""
        self.mount()
        try:
            yield self
        finally:
            self.umount()

    @property
    def fingerprint(self) -> str:
        """A fingerprint unique to the combined configuration of backend and
        encryptor.

        That fingerprint is unique to the configuration but independent from
        the instance used. Every backintime instance with the identical mount
        setup and configuratino should return an identical fingerprint.

        In combination with mountpoint lock mechanic, it serves as a stable
        identifier for mountpoints, allowing mounts with identical
        configurations to be recognized and potentially reused across
        processes.

        See also `MountManager._compute_fingerprint()` for more details.
        """
        return self.encryptor.fingerprint

    @property
    def mount_root(self) -> Path:
        """The root directory containing mount points and lock files.

        See ``Backend.__init__()`` for details.
        """
        return self.backend.mount_root

    @property
    def path(self) -> Path:
        """The path to work with after backend and encryptor is mounted."""
        return self.encryptor.path

    def is_initialized(self) -> bool:
        """Check if the encryptor is initialized.

        The backend is not relevant at this point.
        """
        return self.encryptor.is_initialized()

    def initialize(self):
        """Initialize encryptor.

        The backend is not relevant at this point.
        """
        self.encryptor.initialize()

    def validate(self):
        """Check if backend and encryptor are ready.

        TODO: Check for availability of binaries
        Raises: MountError
        """
        self.backend.validate()
        self.encryptor.validate()

    def _requires_mountpoint_lock(self) -> bool:
        """Whether runtime mountpoint locking is required."""

        if self.backend.TYPE is Backend.Type.SSH:
            return True

        if self.encryptor.TYPE is Encryptor.Type.GOCRYPTFS:
            return True

        return False

    def mount(self):
        """Initiate mount in backend and encryptor"""
        # Workaround
        self.cfg.PLUGIN_MANAGER.load(cfg=self.cfg)
        self.cfg.PLUGIN_MANAGER.mount(self.cfg.currentProfile())

        # Dev note (buhtz, 2026-05): The validate- and initialize-methods need
        # a redesign, because I often run into problems and starting
        # workarounds. I am not sure about a solution. I need to think about a
        # better concept.

        with self._process_lock():
            if self._requires_mountpoint_lock():
                self._acquire_mountpoint_lock()

            self.backend.validate()
            self.backend.mount()

            if not self.encryptor.is_initialized():
                self.encryptor.initialize()
            self.encryptor.validate()
            self.encryptor.mount()

    def umount(self):
        """Release encryptor and backend mounts"""
        self.cfg.PLUGIN_MANAGER.load(cfg=self.cfg)
        self.cfg.PLUGIN_MANAGER.unmount(self.cfg.currentProfile())

        try:
            if not self._mountpoint_locks_active():
                self.encryptor.umount()
                self.backend.umount()
            else:
                logger.info(
                    f'{os.getpid()=} Skipping unmount, because '
                    f'mountpoint "{self.path}" in '
                    'use by other processes.',
                    self
                )
        finally:
            if self._requires_mountpoint_lock():
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

        for fp in path.glob(f'*.{LOCK_SUFFIX}'):

            pid = int(fp.stem)

            if pid == os.getpid():
                # Ignore process's own lock files.
                continue

            if tools.processAlive(pid):
                active = True
                continue

            logger.debug(f'{os.getpid()=} Remove stale lock {fp}', self)
            fp.unlink()

        return active

    def _mountpoint_locks_active(self) -> bool:
        """Check for active mountpoint locks but excluding own lock.

        Also return `False` if no own lock exists.
        """
        if not self._lock_mountpoint:
            return False

        active = False

        for fp in self._lock_mountpoint.parent.glob(f'*.{LOCK_SUFFIX}'):

            pid = int(fp.stem)

            # Ignore own lock
            if pid == os.getpid():
                continue

            if tools.processAlive(pid):
                logger.debug(
                    f'{os.getpid()=} Foreign mountpoint lock alive: {fp}',
                    self
                )
                # foreign lock is active
                active = True
                continue

            # foreign lock is dead
            logger.debug(
                f'{os.getpid()=} Remove stale mountpoint lock {fp}',
                self
            )
            fp.unlink(missing_ok=True)

        return active

    @contextmanager
    def _process_lock(self, timeout: int = 60):
        """Short-term lock to prevent concurrent mount modifications.

        Dev note (buhtz, 2026-03): Refactoring and use of flock.py
        """
        pid = os.getpid()
        fp = self.mount_root / f'{pid}.{LOCK_SUFFIX}'
        count = 0

        while self._process_locks_active(self.mount_root):
            count += 1

            if count >= timeout:
                raise RuntimeError('Process lock - Timeout')

            sleep(1)

        logger.debug(
            f'{os.getpid()=} Process lock - Acquire {fp}',
            self
        )

        # ??? Isn't touch enough?
        fp.write_text(str(pid))

        try:
            yield

        finally:
            logger.debug(
                f'{os.getpid()=} Process lock - Release {fp}',
                self
            )
            fp.unlink(missing_ok=True)

    def _acquire_mountpoint_lock(self):
        """Long-term lock for a mountpoint, preventing unmount while in use."""
        pid = os.getpid()

        self._lock_mountpoint = self.mount_root / self.fingerprint \
            / 'locks' / f'{pid}.{LOCK_SUFFIX}'

        # full access for owner (rwx), traversal (x) for others - 0o711
        # Reason: Fusemount needs other processes to traverse the mountpoint
        # directory to check or acquire locks, without granting them write
        # access. Using 700 would block these operations.
        self._lock_mountpoint.parent.mkdir(
            mode=0o711, parents=True, exist_ok=True)

        logger.debug(
            f'{os.getpid()=} Mount point lock - Acquire '
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
            # DEBUG
            # pylint: disable-next=import-outside-toplevel
            import traceback  # noqa: PLC0415
            traceback.print_stack(limit=5)

            logger.warning(
                'Mount point lock - Unexpected state. '
                f'{self._lock_mountpoint} '
                'does not exist.', self
            )
            return

        logger.debug(
            f'{os.getpid()=} Mount point lock - Release '
            f'{self._lock_mountpoint.relative_to(self.mount_root)}',
            self
        )
        self._lock_mountpoint.unlink(missing_ok=True)
        self._lock_mountpoint = None
