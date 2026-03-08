# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Provide operations related to manipulating backup profiles.

This module contains the application logic independent from the GUI layer.

Dev note (buhtz, 2026-02): Copeling to the config module will be refactored
soon. See PR #1850
"""
from pathlib import Path
from event import Event


class ProfileOperations:
    """Profile related operations"""
    event_dir_added_to_include = Event()

    def __init__(self, profile_id, config):
        self._profile_id = profile_id
        self._config = config

    def _split_duplicates(self,
                          existing: list[str],
                          new_paths: list[str]
                          ) -> tuple[list[str], list[str]]:
        """Split `new_paths` into duplicates and new entries.

        Args:
            existing: List of paths already existing paths.
            new_paths: List of paths to check.

        Returns:
            A 2-entry tuple with lists of duplicated and new existing
            items.
        """
        duplicates, to_add = [], []
        for val in new_paths:
            (duplicates if val in existing else to_add).append(val)

        return duplicates, to_add

    # def get_includes(self) -> list:
    #     """Return the list of include entries."""
    #     includes = self._config.include(profile_id=self._profile_id)

    def add_include(self, paths: list[str] | list[Path]) -> None:
        """Add entries to the include list.

        Returns: List of duplicates otherwise empty list.
        """
        # list of tuples; ('path/', 0)
        includes = self._config.include(profile_id=self._profile_id)

        duplicates, to_add = self._split_duplicates(
            [val for val, _ in includes],
            paths
        )

        contains_dir = False
        for fp in to_add:
            # 0 = directory, 1 = file
            if Path(fp).is_dir():
                type_mod = 0
                contains_dir = True
            else:
                type_mod = 1
            includes.append((fp, type_mod))

        self._config.setInclude(includes, profile_id=self._profile_id)

        if contains_dir:
            self.event_dir_added_to_include.notify()

        return duplicates

    def add_exclude(self, paths: list[str]) -> list[str]:
        """Add entries to the exclude list.

        Returns: List of duplicates otherwise an empty list.
        """
        excludes = self._config.exclude(profile_id=self._profile_id)
        duplicates, to_add = self._split_duplicates(excludes, paths)
        excludes.extend(to_add)
        self._config.setExclude(excludes, profile_id=self._profile_id)

        return duplicates
