# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The backup source endpoint"""
import os
import tempfile
from pathlib import Path
from gocrypt import reverse_mount_dir
from profilecontext import ProfileContext
from ._base import MOUNT_ROOT_PATH
from ._destination import BackupDestination


class BackupSources:
    """The source endpoint of a backup.

    One instance manage all include entries of a backup profile at once. That
    is the reason why the class name is in plural form.
    """
    def __init__(self, include_paths: list[Path], dest: BackupDestination):
        """
        Args:
            include_paths: List of files and directories (set by the user) to
                be included in the backup.
            dest: The destination endpoint.
        """
        profile = ProfileContext().profile
        if 'local_gocryptfs' != profile.mode:
            raise NotImplementedError

        # The original source paths. In mode "local encrypted" it is the not
        # encrypted.
        self._include_paths = include_paths

        # # The (reverse mounted) encrypted view of the original source path
        self._reverse_mountpoint = MOUNT_ROOT_PATH / 'reverse'
        self._reverse_mountpoint.mkdir(parents=True, exist_ok=True)
        self._reverse_mountpoint = Path(tempfile.mkdtemp(
            prefix=f'{os.getpid()}.',
            dir=self._reverse_mountpoint
        ))

        reverse_mount_dir(
            path_to_mount=Path('/'),
            mountpoint=self._reverse_mountpoint,
            cipher_path=dest.get_transfer_path(),
            password=dest.gocrypt_password
        )

    def get_include_paths_missing_in_source(self) -> list[Path]:
        """Return include entries that are missing in the backup source.

        Returns:
            list: List of entries missing.
        """
        missing_entries = filter(
            lambda path: not path.exists(),
            self._include_paths
        )

        return list(missing_entries)

    def get_transfer_root_path(self) -> Path:
        """Return the path used by rsync as SRC for the transfer.

        The return value depends on the backup mode of the current profile.
        That path is the root of the file system or a mountpoint connected to
        the filesystems root.
        Include paths are specified relative to this root path.

        Returns:
            In "local" or "ssh" mode: File system root.
            In "local encrypted" or "ssh encrypted" mode: An encrypted view
                (gocryptfs reverse mount) of file system root.
        """
        # ...

    # def get_local_mounted_path(self) -> Path:
    #     """Return the source path through a local mount."""
    #     pass
