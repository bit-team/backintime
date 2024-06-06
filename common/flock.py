# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
import os
import fcntl
from pathlib import Path
import logger

logger.DEBUG = True  # REMOVE BEFORE MERGE


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
    def __init__(self, filename: str, folder: Path = None):
        if folder is None:
            folder = Path(Path.cwd().root) / 'run' / 'lock'

            # out-dated default
            if not folder.exists():
                folder = Path(Path.cwd().root) / 'var' / 'lock'

        self._file_path = folder / filename
        """Path used for flock"""

        if not self._can_use_file(self._file_path):
            # Try user specific file lock
            # e.g. /run/user/<UID>
            self._file_path = Path(os.environ['XDG_RUNTIME_DIR']) / filename

        if not self._can_use_file(self._file_path):
            # Last try users cache dir
            self._file_path \
                = Path(os.environ.get('XDG_CACHE_HOME', '~/.cache')) / filename

        if not self._can_use_file(self._file_path):
            raise RuntimeError('Can not set global flock')

    def _can_use_file(self, file_path: Path) -> bool:
        """
        """
        if file_path.exists():
            return True

        # Try to create it
        try:
            file_path.touch(mode=0o666)
        except PermissionError:
            logger.debug(f'Cannot use file lock on {file_path}.')
        except Exception as err:
            logger.error(f'Unknown error while testing file '
                         f'lock on {file_path}. Error was {err}.')
        else:
            print('X'*100)
            logger.debug(f'Use {file_path} for file lock.')
            return True

        return False

    def __enter__(self):
        self._log('Set')

        # Open (and create if needed) the file
        mode = 'r' if self._file_path.exists() else 'w'
        self._flock_handle = self._file_path.open(mode)

        # blocks (waits) until an existing flock is released
        fcntl.flock(self._flock_handle, fcntl.LOCK_EX)

        # If new created file set itspermissions to "rw-rw-rw".
        # otherwise a foreign user is not able to use it.
        if mode == 'w':
            self._file_path.chmod(int('0o666', 8))

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._log('Release')
        fcntl.fcntl(self._flock_handle, fcntl.LOCK_UN)
        self._flock_handle.close()

    def _log(self, prefix: str):
        """Generate a log message including the current lock files path and the
        process ID.
        """
        logger.debug(f'{prefix} flock {self._file_path} by PID {os.getpid()}',
                     self)


class GlobalFlock(_FlockContext):
    """Flock context manager used for global flock in Back In Time."""
    def __init__(self):
        super().__init__('backintime.lock')
