# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Managment of the state file."""
from __future__ import annotations
import json
import singleton
import logger


class State(metaclass=singleton.Singleton):
    """Manage state data for Back In Time.
    """

    def __init__(self, data: dict):
        """Constructor."""
        self._data = data

    def __str__(self):
        return json.dumps(self._data, indent=4)
