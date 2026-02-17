# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Provide operations related to manipulating backup profiles.

This module contains the application logic independed from the GUI layer.

Dev note (buhtz, 2026-02): Copeling to the config modul will be refactored
soon. See PR #1850
"""
from pathlib import Path
from event import Event


class ProfileOperations:
    def __init__(self, profile_id, config):
        self.profile_id = profile_id
        self._config = config

        self.event_dir_added_to_include = Event()

    def add_include(self, paths: list[str] | list[Path]) -> None:
        """Add entries to the include list."""
        # Dev note (buhtz, 2026-02): str to Path conversation is a workaround,
        # and will be refactored soon.
        if isinstance(paths[0], str):
            paths = [Path(val) for val in paths]

        includes = self.config.include(profile_id=self.profile_id)

        contains_dir = False

        for fp in paths:
            # 0 = directory, 1 = file
            type_mod = 0 if fp.is_dir() else 1
            if fp.is_dir():
                type_mod = 0
                contains_dir = True
            else:
                type_mod = 1
            include.append((str(fp), type_mod))

            # # Dev note: Could be an event.Event connected to PlacesWidget
            # if type_mod == 0:
            #     updatePlaces = True | places.do_update()

        self._config.setInclude(includes, profile_id=self.profile_id)

        if contains_dir:
            self.event_dir_added_to_include.notify()

    def add_exclude(self, paths: list[str]):
        """Add entries to the exclude list"""
        excludes = self._config.exclude(profile_id=self._profile_id)

        excludes.extend(paths)

        self._config.setExclude(excludes, profile_id=self._profile_id)
