# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
from pathlib import Path
from typing import Optional

class MountError(Exception):
    """Raised for failures in the mount subsystem.

    It is intentionally kept generic to avoid multiple custom exceptions.
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
