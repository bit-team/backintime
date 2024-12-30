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
import singleton
import logger
from pathlib import Path
from datetime import datetime, timezone
from version import __version__


class StateData(dict, metaclass=singleton.Singleton):
    """Manage state data for Back In Time.

    Dev note (buhtz, 2024-12): It is recommended and prefered to derive from
    `collections.UserDict` instead of just `dict`. But this conflicts with the
    ``metaclass=``. To my current knowledge this is not a big deal.
    """

    @staticmethod
    def file_path() -> Path:
        """Returns the state file path."""
        xdg_state = os.environ.get('XDG_STATE_HOME',
                                   Path.home() / '.local' / 'state')
        fp = xdg_state / 'backintime.json'

        logger.debug(f'State file path: {fp}')

        return fp

    def __init__(self, data: dict):
        """Constructor."""

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
