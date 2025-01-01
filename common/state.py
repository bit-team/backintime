# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Managment of the state file."""
from __future__ import annotations
import os
import json
from pathlib import Path
from datetime import datetime, timezone
import singleton
import logger
from version import __version__


class StateData(dict, metaclass=singleton.Singleton):
    """Manage state data for Back In Time.

    Dev note (buhtz, 2024-12): It is recommended and prefered to derive from
    `collections.UserDict` instead of just `dict`. But this conflicts with the
    ``metaclass=``. To my current knowledge this is not a big deal.
    """

    _EMPTY_STRUCT = {
        'gui': {
            'mainwindow': {
                'files_view': {},
            },
            'manage_profiles': {},
            'logview': {},
        },
        'message': {
            'encfs': {}
        },
    }

    @staticmethod
    def file_path() -> Path:
        """Returns the state file path."""
        xdg_state = os.environ.get('XDG_STATE_HOME',
                                   Path.home() / '.local' / 'state')
        fp = xdg_state / 'backintime.json'

        logger.debug(f'State file path: {fp}')

        return fp

    def __init__(self, data: dict = None):
        """Constructor."""

        if not data:
            data = self._EMPTY_STRUCT

        # This will initilize self.data (see UserDict docu)
        super().__init__(data)

    def __str__(self):
        return json.dumps(self, indent=4)

    def _set_save_meta_data(self):
        meta = {
            'saved': datetime.now().isoformat(),
            'saved_utc': datetime.now(timezone.utc).isoformat(),
            'bitversion': __version__,
        }

        self['_meta'] = meta

    def save(self):
        """Store application state data to a file."""
        logger.debug('Save state data.')

        self._set_save_meta_data()

        with self.file_path().open('w', encoding='utf-8') as handle:
            handle.write(str(self))
            # json.dump(obj=self._data, fp=handle, indent=4)

    def manual_starts_countdown(self) -> int:
        """Countdown value about how often the users started the Back In Time
        GUI.

        At the end of the countown the `ApproachTranslatorDialog` is presented
        to the user.
        """
        return self.get('manual_starts_countdown', 10)

    def decrement_manual_starts_countdown(self):
        """Counts down to -1.

        See :py:func:`manual_starts_countdown()` for details.
        """
        val = self.manual_starts_countdown()

        if val > -1:
            self['manual_starts_countdown'] = val - 1

    @property
    def msg_release_candidate(self) -> str:
        return self['message']['release_candidate']

    @msg_release_candidate.setter
    def msg_release_candidate(self, val: str) -> None:
        self['message']['release_candidate'] = val

    @property
    def msg_encfs_global(self) -> bool:
        return self['message']['encfs']['global']

    @msg_encfs_global.setter
    def msg_encfs_global(self, val: bool) -> None:
        self['message']['encfs']['global'] = val

    @property
    def mainwindow_show_hidden(self) -> bool:
        return self['gui']['mainwindow']['show_hidden']

    @mainwindow_show_hidden.setter
    def mainwindow_show_hidden(self, val: boll) -> None:
        self['gui']['mainwindow']['show_hidden'] = val

    @property
    def mainwindow_dims(self) -> tuple[int, int]:
        return self['gui']['mainwindow']['dims']

    @mainwindow_dims.setter
    def mainwindow_dims(self, vals) -> None:
        self['gui']['mainwindow']['dims'] = vals

    @property
    def mainwindow_coords(self) -> tuple[int, int]:
        return self['gui']['mainwindow']['coords']

    @mainwindow_coords.setter
    def mainwindow_coords(self, vals) -> None:
        self['gui']['mainwindow']['coords'] = vals

    @property
    def logview_dims(self) -> tuple[int, int]:
        return self['gui']['logview']['dims']

    @logview_dims.setter
    def logview_dims(self, vals) -> None:
        self['gui']['logview']['dims'] = vals

    @property
    def files_view_sorting(self) -> tuple[int, int]:
        """Column index and sort order.

        Returns:
            Tuple with column index and its sorting order (0=ascending).
        """
        return self['gui']['mainwindow']['files_view']['sorting']

    @files_view_sorting.setter
    def files_view_sorting(self, vals: tupler[int, int]) -> None:
        self['gui']['mainwindow']['files_view']['sorting'] = vals

    @property
    def mainwindow_main_splitter_widths(self) -> tuple[int, int]:
        """Left and right width of main splitter in main window.

        Returns:
            Two entry tuple with right and left widths.
        """
        return self['gui']['mainwindow']['splitter_main_widths']

    @mainwindow_main_splitter_widths.setter
    def mainwindow_main_splitter_widths(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['splitter_main_widths'] = vals

    @property
    def mainwindow_second_splitter_widths(self) -> tuple[int, int]:
        """Left and right width of second splitter in main window.

        Returns:
            Two entry tuple with right and left widths.
        """
        return self['gui']['mainwindow'].get('splitter_second_widths', None)

    @mainwindow_second_splitter_widths.setter
    def mainwindow_second_splitter_widths(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['splitter_second_widths'] = vals
