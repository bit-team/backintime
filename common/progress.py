# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""A file that is written and read by different processes to interchange
information. Back IN Time is using it to communicate rsync progress from CLI
to GUI.

This will be replaced by proper IPC (#2260).
"""
import os
import json
from typing import Union
from pathlib import Path


class ProgressFile():

    RSYNC = 50

    def __init__(self, filename: Union[Path, str]):
        if isinstance(filename, str):
            filename = Path(filename)

        self.filename = filename

        self._data = None

    def get_data(self) -> dict:
        return self._data

    def set_data(self, data: dict):
        self._data = data

    def save(self):
        self.filename.write_text(json.dumps(self._data), encoding='utf-8')

    def load(self):
        content = self.filename.read_text(encoding='utf-8')
        # Ugly workaround. See #2260
        if content:
            self._data = json.loads(content)

    def fileReadable(self):
        return os.access(self.filename, os.R_OK)
