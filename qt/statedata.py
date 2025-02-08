# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Management of the state file."""
# pylint: disable=wrong-import-position,wrong-import-order
from __future__ import annotations
import os
import json
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
from qttools_path import registerBackintimePath
registerBackintimePath('common')
import singleton  # noqa: E402
import logger  # noqa: E402
import tools  # noqa: E402
from version import __version__  # noqa: E402


class StateData(dict, metaclass=singleton.Singleton):
    """Manage state data for Back In Time.

    Dev note (buhtz, 2024-12): It is usually recommended and preferred to
    derive from `collections.UserDict` instead of just `dict`. But this
    conflicts with the ``metaclass=``. To my current knowledge this is not a
    big deal and won't introduce any problems.

    """
    # pylint: disable=too-many-instance-attributes
    # The default structure. All properties do rely on them and assuming
    # it is there.
    _EMPTY_STRUCT = {
        'gui': {
            'mainwindow': {
                'files_view': {},
                'last_path': {},
                'places_sorting': {},
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
        def msg_encfs(self) -> int:
            """Stage of EncFS deprecation warning shown as last."""
            try:
                return self._state['message']['encfs'][self._profile_id]
            except KeyError:
                self.msg_encfs = 0
                return self.msg_encfs

        @msg_encfs.setter
        def msg_encfs(self, val: int) -> None:
            self._state['message']['encfs'][self._profile_id] = val

        @property
        def last_path(self) -> Path:
            """Last path used in the GUI.

            Raises:
                KeyError
            """
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
        xdg_state = os.environ.get('XDG_STATE_HOME', None)
        if xdg_state:
            xdg_state = Path(xdg_state)
        else:
            xdg_state = Path.home() / '.local' / 'state'

        fp = xdg_state / 'backintime-qt.json'

        logger.debug(f'State file path: {fp}')

        return fp

    def __init__(self, data: dict = None):
        """Constructor."""

        # default
        full = deepcopy(self._EMPTY_STRUCT)

        if data:
            full = tools.nested_dict_update(full, data)

        super().__init__(full)

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

        fp = self.file_path()
        fp.parent.mkdir(parents=True, exist_ok=True)

        with fp.open('w', encoding='utf-8') as handle:
            handle.write(str(self))

    def profile(self, profile_id: str) -> StateData.Profile:
        """Return a `Profile` object related to the given id.

        Args:
            profile_id: A profile_id of a snapshot profile.

        Returns:
            A profile surrogate.

        Raises:
            KeyError: If profile does not exists.
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
        try:
            return self['message']['release_candidate']
        except KeyError:
            self.msg_release_candidate = None
            return self.msg_release_candidate

    @msg_release_candidate.setter
    def msg_release_candidate(self, val: str) -> None:
        self['message']['release_candidate'] = val

    @property
    def msg_encfs_global(self) -> int:
        """Last stage of global EncFS deprecation message that was shown."""
        try:
            return self['message']['encfs']['global']
        except KeyError:
            self.msg_encfs_global = 0
            return self.msg_encfs_global

    @msg_encfs_global.setter
    def msg_encfs_global(self, val: int) -> None:
        self['message']['encfs']['global'] = val

    @property
    def mainwindow_show_hidden(self) -> bool:
        """Show hidden files in files view."""
        try:
            return self['gui']['mainwindow']['show_hidden']
        except KeyError:
            self.mainwindow_show_hidden = False
            return self.mainwindow_show_hidden

    @mainwindow_show_hidden.setter
    def mainwindow_show_hidden(self, val: bool) -> None:
        self['gui']['mainwindow']['show_hidden'] = val

    @property
    def mainwindow_dims(self) -> tuple[int, int]:
        """Dimensions of the main window.

        Raises:
            KeyError
        """
        return self['gui']['mainwindow']['dims']

    @mainwindow_dims.setter
    def mainwindow_dims(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['dims'] = vals

    @property
    def mainwindow_coords(self) -> tuple[int, int]:
        """Coordinates (position) of the main window.

        Raises:
            KeyError
        """
        return self['gui']['mainwindow']['coords']

    @mainwindow_coords.setter
    def mainwindow_coords(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['coords'] = vals

    @property
    def logview_dims(self) -> tuple[int, int]:
        """Dimensions of the log view dialog.

        Raises:
            KeyError
        """
        try:
            return self['gui']['logview']['dims']
        except KeyError:
            self.logview_dims = (800, 500)
            return self.logview_dims

    @logview_dims.setter
    def logview_dims(self, vals: tuple[int, int]) -> None:
        self['gui']['logview']['dims'] = vals

    @property
    def files_view_sorting(self) -> tuple[int, int]:
        """Column index and sort order.

        Returns:
            Tuple with column index and its sorting order (0=ascending).
        """
        try:
            return self['gui']['mainwindow']['files_view']['sorting']
        except KeyError:
            self.files_view_sorting = (0, 0)
            return self.files_view_sorting

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
        try:
            return self['gui']['mainwindow']['splitter_main_widths']
        except KeyError:
            self.mainwindow_main_splitter_widths = (150, 450)
            return self.mainwindow_main_splitter_widths

    @mainwindow_main_splitter_widths.setter
    def mainwindow_main_splitter_widths(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['splitter_main_widths'] = vals

    @property
    def mainwindow_second_splitter_widths(self) -> tuple[int, int]:
        """Left and right width of second splitter in main window.

        Returns:
            Two entry tuple with right and left widths.
        """
        try:
            return self['gui']['mainwindow']['splitter_second_widths']
        except KeyError:
            self.mainwindow_second_splitter_widths = (150, 300)
            return self.mainwindow_second_splitter_widths

    @mainwindow_second_splitter_widths.setter
    def mainwindow_second_splitter_widths(self, vals: tuple[int, int]) -> None:
        self['gui']['mainwindow']['splitter_second_widths'] = vals

    @property
    def toolbar_button_style(self) -> int:
        """Style of icons for the main toolbar.

        Returns:
           Style value as integer (default: 0 as ``ToolButtonIconOnly``)
        """
        try:
            return self['gui']['mainwindow']['toolbar_button_style']
        except KeyError:
            self.toolbar_button_style = 0
            return self.toolbar_button_style

    @toolbar_button_style.setter
    def toolbar_button_style(self, value) -> None:
        self['gui']['mainwindow']['toolbar_button_style'] = value
