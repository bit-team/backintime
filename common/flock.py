# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Manage file lock.

Offer context managers to manage file lock (flock) files.
"""
import os
import fcntl
import time
from pathlib import Path
import logger


class _FlockContext:
    """Context manager to manage file locks (flock).

    For non-root users, defaults to a single-user lock located in the user's
    runtime or cache directory ($XDG_RUNTIME_DIR or ~/.cache/backintime).
    For root users, system-wide lock locations (/run/lock, /var/lock) are used.
    """

    def __init__(self,
                 filename: str,
                 disable: bool = False,
                 timeout: int = 600,
                 multi_user: bool | None = None):
        """Check if an flock file can be used or created.

        Args:
            filename: The filename (without path) used for the flock file.
            disable: Disable the whole context manager behavior.
            timeout: Maximum seconds to wait for lock acquisition. Defaults to 600s.
            multi_user: If True, prioritize /run/lock and /var/lock. Defaults to True
                for root (UID 0) and False for non-root users.

        Raises:
            RuntimeError: If it wasn't possible to establish a lock file in any candidate path.
        """
        self._file_path = None
        """Full path used for the flock file"""

        self._flock_handle = None
        """File handle (descriptor) to the flock file."""

        self.timeout = timeout

        if disable:
            return None

        if multi_user is None:
            try:
                multi_user = (os.geteuid() == 0)
            except AttributeError:
                multi_user = False

        candidate_dirs = []
        if multi_user:
            candidate_dirs.extend([
                Path(Path.cwd().root) / 'run' / 'lock',
                Path(Path.cwd().root) / 'var' / 'lock'
            ])

        # User-specific runtime directory (preferred for unprivileged users)
        xdg_runtime = os.environ.get('XDG_RUNTIME_DIR')
        if xdg_runtime:
            candidate_dirs.append(Path(xdg_runtime))
        else:
            try:
                candidate_dirs.append(Path(f'/run/user/{os.getuid()}'))
            except (AttributeError, OSError):
                pass

        # User cache directory
        xdg_cache = os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')
        candidate_dirs.append(Path(xdg_cache) / 'backintime')

        # Fallback to system-wide directories if not already tried
        if not multi_user:
            candidate_dirs.extend([
                Path(Path.cwd().root) / 'run' / 'lock',
                Path(Path.cwd().root) / 'var' / 'lock'
            ])

        for folder in candidate_dirs:
            if not folder.exists():
                try:
                    folder.mkdir(parents=True, exist_ok=True)
                except (PermissionError, OSError):
                    continue

            test_path = folder / filename
            if self._can_use_file(test_path):
                self._file_path = test_path
                return None

        raise RuntimeError(
            f'Can not establish flock file {filename} in any candidate directory'
        )

    def _can_use_file(self, file_path: Path) -> bool:
        """Check if ``file_path`` is usable as a lock file.

        Verifies read/write accessibility if the file exists, or creates it.
        """
        if file_path.exists():
            return os.access(file_path, os.R_OK | os.W_OK)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(file_path, os.O_CREAT | os.O_RDWR, 0o666)
            os.close(fd)
        except (PermissionError, OSError) as err:
            logger.debug(f'Cannot use file lock on {file_path}: {err}')
            return False
        else:
            logger.debug(f'Use {file_path} for file lock.')
            return True

    def __enter__(self):
        """Request an exclusive file lock on :data:``self._file_path`` with bounded wait."""
        if self._file_path is None:
            return None

        self._log('Set')

        try:
            self._flock_handle = self._file_path.open(mode='r+')
        except (PermissionError, OSError):
            self._flock_handle = self._file_path.open(mode='r')

        start_time = time.time()
        warned = False
        while True:
            try:
                fcntl.flock(self._flock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                if not warned:
                    logger.info(
                        f'Waiting for existing file lock on {self._file_path}...',
                        self
                    )
                    warned = True

                if self.timeout is not None and (time.time() - start_time) >= self.timeout:
                    self._flock_handle.close()
                    self._flock_handle = None
                    raise TimeoutError(
                        f'Timed out waiting for file lock on {self._file_path} after {self.timeout}s'
                    )
                time.sleep(1)

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self._flock_handle is None:
            return None

        self._log('Release')
        try:
            fcntl.flock(self._flock_handle, fcntl.LOCK_UN)
        except OSError:
            pass
        self._flock_handle.close()
        self._flock_handle = None

    def _log(self, prefix: str):
        logger.debug(f'{prefix} flock {self._file_path} by PID {os.getpid()}')


class GlobalFlock(_FlockContext):
    """Context manager used for global file lock in Back In Time."""

    def __init__(self,
                 disable: bool = False,
                 timeout: int = 600,
                 multi_user: bool | None = None):
        super().__init__(
            'backintime.lock',
            disable=disable,
            timeout=timeout,
            multi_user=multi_user
        )

