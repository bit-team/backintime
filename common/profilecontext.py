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
import singleton
from konfig import Konfig, Profile


class ProfileContext(metaclass=singleton.Singleton):
    """Represent the currently selected backup profile.

    The profile context stores a reference to the currently selected profile
    during runtime.

    The class is implemented as a singleton.
    It does not load, save or manage profiles.
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
        if isinstance(profile_ref, Profile):
            self._profile_ref = profile_ref.name
        else:
            self._profile_ref = profile_ref
