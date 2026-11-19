# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The backup destination endpoint"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import os
from time import sleep
from profilecontext import ProfileContext
from sshcore import SSHHost
from storagesize import StorageSize
import logger
import tools
from gocrypt import (init_gocryptfs_dir,
                     is_initialized,
                     forward_mount_dir,
                     umount,
                     GocryptPathMapper)
from ._base import CTLSOCKET_NAME, LOCK_SUFFIX, MOUNT_ROOT_PATH
from pluginmanager import PluginManager


def compute_fingerprint_from_string(source: str) -> str:
    """Compute a unique fingerprint used for mountpoints.

    The fingerprint is a deterministic hex string and based on the
    given `source` string. That source string consists in most cases of the
    profile configuration regarding destination path, SSH and Gocryptfs
    configuration.

    That fingerprint is unique to the configuration but independent from
    the instance used. Every backintime instance with the identical mount
    setup and configuration should return an identical fingerprint.

    In combination with mountpoint lock mechanic, it serves as a stable
    identifier for mountpoints, allowing mounts with identical
    configurations to be recognized and potentially reused across
    processes.

    Returns:
        A SHA256 hash cut to a 12-character hexadecimal string.
    """
    logger.debug(f'fingerprint: {source=}')

    return hashlib.sha256(source.encode()).hexdigest()[:12]


class BackupDestination:
    """The destination endpoint of a backup.

    """
    def __init__(self,
                 path: Path,
                 gocrypt_password: str | None,
                 plugin_manager: PluginManager,
                 ssh_host: SSHHost | None = None):
        # WORKAROUND
        self._plugin_manager = plugin_manager

        profile = ProfileContext().profile
        if 'local_gocryptfs' != profile.mode:
            raise NotImplementedError

        # The original destination path.
        # In mode "local" it is the original regular path.
        # In mode "local encrypted" it is the encrypted path.
        # In mode "ssh" it is the original remote path.
        # In mode "ssh encrpyted" it is the original remote path.
        self._destination_path = path

        # Gocryptfs encryption password
        self._gocrypt_password = gocrypt_password

        # In case of SSH profiles
        self._ssh_host = ssh_host

        # The (forward mounted) decrypted view of the original destination path
        self._decrypted_path = None

        # Used to map/translated between en-/decrypted paths
        self._mapper = None

        self._lock_mountpoint = None

    def get_transfer_path(self) -> Path | str:
        """Return the destination path used by rsync as DEST for the transfer.

        The return value depends on the backup mode of the current profile.

        Returns:
            In "local" and "local encrypted": The regular destination path.
            In "ssh" and "ssh encrypted" mode: Remote path in SSH syntax.
                (e.g. user@host:/path)
        """
        return self._destination_path

    def get_local_path(self) -> Path:
        """Return the destination path through a local mount.

        The return value depends on the backup mode of the current profile.

        Returns:
            In "local": The destination path.
            In "local encrypted": A decrypted (gocryptfs forward) mounted view
                of the destination path.
            In "ssh" mode: An sshfs mounted mountpoint.
            In "ssh encrypted" mode: A decrypted (gocryptfs forward) mounted
                mountpoint, of an sshfs mounted mountpoint to the remote
                destination.
        """
        return self._decrypted_path

    def _get_ctlsocket_path(self) -> Path:
        return self._decrypted_path.parent / CTLSOCKET_NAME

    @property
    def gocrypt_password(self):
        """The gocrypt password"""
        return self._gocrypt_password

    def _get_fingerprint(self):
        # WORKAROUND DRAFT
        # This is "local_gocryptfs" only
        data = f'LOCAL: {self._destination_path}'
        data = f'{data} | '
        data = f'{data} GOCRYPTFS: '

        return compute_fingerprint_from_string(data)

    def is_ready(self) -> bool:
        """Return ``True`` if the gocryptfs cipher dir is initialized and a
        (forward) mountpoint exists providing a decrypted view.
        """

        if not self._is_initialized():
            return False

        if self._decrypted_path is None:
            return False

        return tools.is_mounted(self._decrypted_path)

    def _is_initialized(self) -> bool:
        return is_initialized(self._destination_path)

    def _initialize_if_needed(self):
        """Initialize the destination directory if not still initialized.

        For local encrypted profiles the destination path will be initialized
        for being usable.
        """

        if self._is_initialized():
            return

        init_gocryptfs_dir(
            self._destination_path,
            self._gocrypt_password
        )

    def mount(self):
        """Mount the gocryptfs destination.

        A forward mount is used.
        """
        self._initialize_if_needed()

        if self._decrypted_path is not None:
            raise RuntimeError('Unexpected situation')

        self._plugin_manager.load()
        self._plugin_manager.mount()

        with self._process_lock():

            # E.g., ``~/.local/share/backintime/mnt/<fp>/mountpoint/``.
            self._decrypted_path = MOUNT_ROOT_PATH / \
                self._get_fingerprint() / 'mountpoint'
            self._decrypted_path.mkdir(parents=True, exist_ok=True)

            forward_mount_dir(
                path_to_mount=self._destination_path,
                mountpoint=self._decrypted_path,
                password=self.gocrypt_password,
                socket_path=self._get_ctlsocket_path(),
            )

            self._mapper = GocryptPathMapper(self._get_ctlsocket_path())

    def umount(self):
        """Release the gocryptfs mountpoint"""

        self._plugin_manager.load()  # Why loading again?
        self._plugin_manager

        try:
            if not self._mountpoint_locks_active():
                umount(self._decrypted_path)

            else:
                logger.info(
                    f'{os.getpid()=} Skipping unmount, because '
                    f'mountpoint "{self._decrypted_path}" in '
                    'use by other processes.',
                )

        finally:
            if self._requires_mountpoint_lock():
                self._release_mountpoint_lock()

            self._mapper = None

        # QUESTION: What about the ctlsocket?

    def is_free_space_less_than(self, value: StorageSize) -> bool:
        """Compare the endpoints free space left with `value`.

        Args:
            value: Storage space threshold

        Returns:
            ``True`` if the free space is less than ``value``.
        """
        real = self._get_free_space()

        if real is None:
            return False

        return real < value

    def _get_free_space(self) -> StorageSize | None:
        """Free space at destination.

        Return:
            A StorageSize object holding the value or `None` in case of errors.
        """

        ssh_cmd = None

        # TODO
        # # Prepare getting free space value
        # if 'ssh' in mode:
        #     # ...on remote host
        #     # dest_path = self.config.sshSnapshotsFullPath()
        #     ssh_cmd = self.config.sshCommand(
        #         [], nice=False, ionice=False)

        return tools.free_space(self._destination_path, ssh_cmd)

    @contextmanager
    def _process_lock(self, timeout: int = 60):
        """Short-term lock to prevent concurrent mount modifications.

        Dev note (buhtz, 2026-03): Refactoring and use of flock.py
        """
        pid = os.getpid()
        fp = MOUNT_ROOT_PATH / f'{pid}.{LOCK_SUFFIX}'
        count = 0

        while self._process_locks_active(MOUNT_ROOT_PATH):
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
            # # DEBUG
            # # pylint: disable-next=import-outside-toplevel
            # import traceback  # no-qa: PLC0415
            # traceback.print_stack(limit=5)

            # logger.warning(
            #     'Mount point lock - Unexpected state. '
            #     f'{self._lock_mountpoint} '
            #     'does not exist.', self
            # )
            return

        logger.debug(
            f'{os.getpid()=} Mount point lock - Release '
            f'{self._lock_mountpoint.relative_to(self.mount_root)}'
        )

        self._lock_mountpoint.unlink(missing_ok=True)
        self._lock_mountpoint = None
