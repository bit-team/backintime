# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Management of the state file."""
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

    Dev note (buhtz, 2024-12): It is usually recommended and preferred to
    derive from `collections.UserDict` instead of just `dict`. But this
    conflicts with the ``metaclass=``. To my current knowledge this is not a
    big deal and won't introduce any problems.

    """
    # The default structure. All properties do rely on them and assuming
    # it is there.
    _EMPTY_STRUCT = {
        'gui': {
            'mainwindow': {
                'files_view': {},
            },
            'manage_profiles': {
                'incl_sorting': {},
                'excl_sorting': {},
            },
            'logview': {},
        },
        'message': {
            'encfs': {}
        },
    }

    class Profile:
        """A surrogate to access profile-specific state data."""

        def __init__(self, profile_id: str, state: StateData):
            self._state = state
            self._profile_id = profile_id

        @property
        def msg_encfs(self) -> bool:
            """If message box about EncFS deprecation was shown already."""
            return self._state['message']['encfs'][self._profile_id]

        @msg_encfs.setter
        def msg_encfs(self, val: bool) -> None:
            self._state['message']['encfs'][self._profile_id] = val

        @property
        def last_path(self) -> Path:
            """Last path used in the GUI."""
            return Path(self._state['gui']['mainwindow'][
                'last_path'][self._profile_id])

        @last_path.setter
        def last_path(self, path: Path) -> None:
            self._state['gui']['mainwindow'][
                'last_path'][self._profile_id] = str(path)

        @property
        def places_sorting(self) -> tuple[int, int]:
            """Column index and sort order.

            Returns:
                Tuple with column index and its sorting order (0=ascending).
            """
            return self._state['gui']['mainwindow'][
                'places_sorting'][self._profile_id]

        @places_sorting.setter
        def places_sorting(self, vals: tuple[int, int]) -> None:
            self._state['gui']['mainwindow'][
                'places_sorting'][self._profile_id] = vals

        @property
        def exclude_sorting(self) -> tuple[int, int]:
            """Column index and sort order.

            Returns:
                Tuple with column index and its sorting order (0=ascending).
            """
            return self._state['gui']['manage_profiles'][
                'excl_sorting'][self._profile_id]

        @exclude_sorting.setter
        def exclude_sorting(self, vals: tuple[int, int]) -> None:
            self._state['gui']['manage_profiles'][
                'excl_sorting'][self._profile_id] = vals

        @property
        def include_sorting(self) -> tuple[int, int]:
            """Column index and sort order.

            Returns:
                Tuple with column index and its sorting order (0=ascending).
            """
            return self._state['gui']['manage_profiles'][
                'incl_sorting'][self._profile_id]

        @include_sorting.setter
        def include_sorting(self, vals: tuple[int, int]) -> None:
            self._state['gui']['manage_profiles'][
                'incl_sorting'][self._profile_id] = vals

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

        if data:
            self._EMPTY_STRUCT.update(data)
        else:
            data = self._EMPTY_STRUCT

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

    def profile(self, profile_id: str) -> StateData.Profile:
        """Return a `Profile` object related to the given id.

        Args:
            profile_id: A profile_id of a snapshot profile.

        Returns:
            A profile surrogate.
        """
        return StateData.Profile(profile_id=profile_id, state=self)

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
        """Last version of Back In Time in which the release candidate message
        box was displayed.
        """
        return self['message'].get('release_candidate', None)

    @msg_release_candidate.setter
    def msg_release_candidate(self, val: str) -> None:
        self['message']['release_candidate'] = val

    @property
    def msg_encfs_global(self) -> bool:
        """If global EncFS deprecation message box was displayed already."""
        return self['message']['encfs'].get('global', False)

    @msg_encfs_global.setter
    def msg_encfs_global(self, val: bool) -> None:
        self['message']['encfs']['global'] = val

    @property
    def mainwindow_show_hidden(self) -> bool:
        """Show hidden files in files view."""
        return self['gui']['mainwindow'].get('show_hidden', False)

    @mainwindow_show_hidden.setter
    def mainwindow_show_hidden(self, val: bool) -> None:
        self['gui']['mainwindow']['show_hidden'] = val

    @property
    def mainwindow_dims(self) -> tuple[int, int]:
        """Dimensions of the main window."""
        return self['gui']['mainwindow']['dims']

    @mainwindow_dims.setter
    def mainwindow_dims(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['dims'] = vals

    @property
    def mainwindow_coords(self) -> tuple[int, int]:
        """Coordinates (position) of the main window."""
        return self['gui']['mainwindow']['coords']

    @mainwindow_coords.setter
    def mainwindow_coords(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['coords'] = vals

    @property
    def logview_dims(self) -> tuple[int, int]:
        """Dimensions of the log view dialog."""
        return self['gui']['logview'].get('dims', (800, 500))

    @logview_dims.setter
    def logview_dims(self, vals: tuple[int, int]) -> None:
        self['gui']['logview']['dims'] = vals

    @property
    def files_view_sorting(self) -> tuple[int, int]:
        """Column index and sort order.

        Returns:
            Tuple with column index and its sorting order (0=ascending).
        """
        return self['gui']['mainwindow']['files_view'].get('sorting', (0, 0))

    @files_view_sorting.setter
    def files_view_sorting(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['files_view']['sorting'] = vals

    @property
    def files_view_col_widths(self) -> tuple:
        """Widths of columns in the files view."""
        return self['gui']['mainwindow']['files_view']['col_widths']

    @files_view_col_widths.setter
    def files_view_col_widths(self, widths: tuple) -> None:
        self['gui']['mainwindow']['files_view']['col_widths'] = widths

    @property
    def mainwindow_main_splitter_widths(self) -> tuple[int, int]:
        """Left and right width of main splitter in main window.

        Returns:
            Two entry tuple with right and left widths.
        """
        return self['gui']['mainwindow'] \
            .get('splitter_main_widths', (150, 450))

    @mainwindow_main_splitter_widths.setter
    def mainwindow_main_splitter_widths(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['splitter_main_widths'] = vals

    @property
    def mainwindow_second_splitter_widths(self) -> tuple[int, int]:
        """Left and right width of second splitter in main window.

        Returns:
            Two entry tuple with right and left widths.
        """
        return self['gui']['mainwindow'] \
            .get('splitter_second_widths', (150, 300))

    @mainwindow_second_splitter_widths.setter
    def mainwindow_second_splitter_widths(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['splitter_second_widths'] = vals
