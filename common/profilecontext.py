# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Provide the application-wide profile context.

This module contains the runtime context describing which backup profile is
currently selected.
"""
from pathlib import Path
import bitbase
import singleton
from konfig import Konfig, Profile

PREFIX_WORKER = 'worker'
PREFIX_RESTORE = 'restore'


class ProfileContext(metaclass=singleton.Singleton):
    """Represent the currently selected backup profile.

    The profile context stores a reference to the currently selected profile
    during runtime.

    The class is implemented as a singleton.
    It does not load, save or manage profiles.
    Be careful not to make this a good object!
    """

    def __init__(self):
        """Initialize an empty profile context."""
        self._profile_ref = None

    @property
    def profile(self) -> Profile | None:
        """The currently selected profile.

        Returns:
            The selected profile or ``None`` if no profile is currently
            selected.
        """
        if self._profile_ref is None:
            return None

        return Konfig().profile(self._profile_ref)

    def switch(self, profile_ref: int | str | Profile | None) -> None:
        """Switch the current profile.

        Args:
            A profile itself or its name or id to become the currently
            selected profile. Passing ``None`` clears the current selection.

        """
        # WORKAROUND regression test
        if isinstance(profile_ref, str) and profile_ref.isdigit():
            raise RuntimeError(f'Digit but string: {profile_ref=}')

        if isinstance(profile_ref, Profile):
            self._profile_ref = profile_ref.name
        else:
            self._profile_ref = profile_ref

    def _get_path(self, prefix: str, suffix: str) -> Path:
        worker_id = self.profile
        base_path = bitbase.XDG_DATA_HOME / bitbase.BINARY_NAME_BASE
        return base_path / f'{prefix}{worker_id}.{suffix}'

    @property
    def message_file_path(self) -> Path:
        """The file used to transfer messages while rsync and similar backup
        related tasks are running.

        A workaround. Formally known as
        `config.Config.takeSnapshotMessageFile()`.
        """
        return self._get_path(PREFIX_WORKER, 'message')

    @property
    def progress_file_path(self) -> Path:
        """The file used to transfer rsync progress data while it is running.

        A workaround. Formally known as
        `config.Config.takeSnapshotProgressFile()`.
        """
        return self._get_path(PREFIX_WORKER, 'progress')

    @property
    def take_backup_instance_file_path(self) -> Path:
        """The lock file used to indicate the running backup instance.
        """
        return self._get_path('lock')

    @property
    def restore_instance_file_path(self) -> Path:
        """The lock file used to indicate the running restore instance.
        """
        return self._get_path(PREFIX_RESTORE, 'lock')
