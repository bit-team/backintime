# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Exceptions related in the mount module."""
from pathlib import Path
from typing import Optional


class MountError(Exception):
    """Raised for failures in the mount subsystem.

    Design decissions:

        1. The class is intentionally kept generic to avoid a hierarchy of
           specialized mount-related exception types.

    Second design decission:

        Log message is untranslated and UI message is translated. Against
        principels of clean architecture both messages are defined at the
        point of raising the exception. The intention is to avoid any runtime
        mapping layer or translation indirection. This is a deliberate
        design choice to keep the system simple, avoid error-code mapping
        tables and ensure that log output and user-facing messages can evolve
        independently while remaining close together in the code.
    """
    def __init__(
            self,
            problem: str,
            hint: Optional[str] = None,
            path: Optional[Path] = None
    ):
        self.problem = problem
        self.hint = hint
        self.path = path

        msg = ' '.join([self.problem, self.hint])  \
            if self.hint else problem

        if path:
            msg = f'{msg} {path}'

        super().__init__(msg)

    def as_msgbox_string(self, newline='\n') -> str:
        """Full error as multiline string usable in a message box."""

        msg = self.problem

        if self.path:
            msg = f'{msg}{newline}{self.path}'

        if self.hint:
            msg = f'{msg}{newline}{self.hint}'

        return msg
