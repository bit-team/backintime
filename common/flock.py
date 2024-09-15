# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""Manage file lock.

Offer context managers to manage file lock (flock) files.
"""
import os
import fcntl
from pathlib import Path
import logger


class _FlockContext:
    """Context manager to manage file locks (flock).

    It will be tried to establish a multi-user file lock; if not feasible a
    single-user file lock will be used. It depends on the GNU Linux
    distribution used and the write permissions to the file lock locations in
    the file system.

    Usage example ::

        class MyFlock(_FlockContext):
            def __init__(self):
                super().__init__('my.lock')

        with MyFlock():
             do_fancy_things()

    The following directories will be checked in sequence to determine if they
    exist, if a file lock file exists within them, or if there are sufficient
    permissions to create such a file within them. ::

        /run/lock
        /var/lock
        /run/user/<UID>/
        ~/.cache

    The first and second directory in that list is for multi-user file lock.

    To the experience of the developers on Debian-based distributions there is
    no problem having a multi-user file lock. But on Arch-based distributions
    only a user with root privileges is able to do it. Because of that on Arch
    a single-user file lock is used by default until Back In Time is started
    once as root.
    """
    def __init__(self,
                 filename: str,
                 disable: bool = False):
        """Check if an flock file can be used or created.

        See the classes documentation about details.

        Args:
            filename: The filename (without path) used for the flock file.
            disabled: Disable the whole context managers behavior. This is a
                workaround. See #1751 and :func:``Snapshots.backup()`` for
                details.

        Raises:
            RuntimeError: If it wasn't possible to use
        """
        self._file_path = None
        """Full path used for the flock file"""

        self._flock_handle = None
        """File handle (descriptor) to the flock file."""

        # Workaround for #1751. Remove after refactoring Snapshots.backup()
        if disable:
            return None

        folder = Path(Path.cwd().root) / 'run' / 'lock'

        if not folder.exists():
            # On older systems
            folder = Path(Path.cwd().root) / 'var' / 'lock'

        self._file_path = folder / filename

        if self._can_use_file(self._file_path):
            return None

        # Try user specific file lock
        # e.g. /run/user/<UID>
        self._file_path = Path(
            os.environ.get('XDG_RUNTIME_DIR',
                           f'/run/user/{os.getuid()}')
        ) / filename

        if self._can_use_file(self._file_path):
            return None

        # At last, try users cache dir.
        self._file_path = Path(
            os.environ.get('XDG_CACHE_HOME',
                           Path.home() / '.cache')
        ) / filename

        if self._can_use_file(self._file_path):
            return None

        raise RuntimeError(
            f'Can not establish global flock file {self._file_path}')

    def _can_use_file(self, file_path: Path) -> bool:
        """Check if ``file_path`` is usable as an flock file.

        The answer is ``True`` if the file exists without checking its
        permissions. If not the file will be created and if successful
        ``True`` will be returned.

        Returns:
            bool: The answer.

        Raises:
            PermissionError: Not enough permissions to create the file.
            Exception: Any other error.
        """
        if file_path.exists():
            return True

        # Try to create it
        try:
            file_path.touch(mode=0o666)

        except PermissionError:
            logger.debug(f'Cannot use file lock on {file_path}.')

        except Exception as err:
            logger.error(
                f'Unknown error while testing file lock on {file_path}. '
                f'Please open a bug report. Error was {err}.')

        else:
            logger.debug(f'Use {file_path} for file lock.')
            return True

        return False

    def __enter__(self):
        """Request an exclucive file lock on :data:``self._file_path``.
        """
        # Workaround for #1751. Remove after refactoring Snapshots.backup()
        # See __init__() for details
        if self._file_path is None:
            return None

        self._log('Set')

        # Open file for reading
        self._flock_handle = self._file_path.open(mode='r')

        # blocks (waits) until an existing flock is released
        fcntl.flock(self._flock_handle, fcntl.LOCK_EX)

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        # Workaround for #1751. Remove after refactoring Snapshots.backup()
        # See __init__() for details
        if self._flock_handle is None:
            return None

        self._log('Release')
        fcntl.fcntl(self._flock_handle, fcntl.LOCK_UN)
        self._flock_handle.close()

    def _log(self, prefix: str):
        """Generate a log message including the current lock files path and the
        process ID.

        Args:
            prefix: Used in front of the log message.
        """
        logger.debug(f'{prefix} flock {self._file_path} by PID {os.getpid()}')


class GlobalFlock(_FlockContext):
    """Context manager used for global file lock in Back In Time.

    If it is a multi-user or single-user flock depends on the several
    aspects. See :class:`_FlockContext` for details.
    """
    def __init__(self, disable: bool = False):
        """See :func:`_FlockContext.__init__()` for details.
        """
        super().__init__('backintime.lock', disable=disable)
