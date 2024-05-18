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


class _FlockContext:
    """Context manager to manage file locks (flock).

    The flock file is stored in the folder `/run/lock` or if not present in
    `/var/lock`.

    Usage example ::

        class MyFlock(_FlockContext):
            def __init__(self):
                super().__init__('my.lock')

        with MyFlock():
             do_fancy_things()

    """
    def __init__(self, filename: str, folder: Path = None):
        if folder is None:
            folder = Path(Path.cwd().root) / 'run' / 'lock'

            # out-dated default
            if not folder.exists():
                folder = Path(Path.cwd().root) / 'var' / 'lock'

        self._file_path = folder / filename
        """Path to used for flock"""

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
