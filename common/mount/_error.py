# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Error class related to mount subsystem."""
from typing import Optional
from exceptions import ApplicationError


class MountError(ApplicationError):
    """Raised for failures in the mount subsystem.

    Design decisions: The class is intentionally kept generic to avoid a
       hierarchy of specialized mount-related exception types.
    """
    def __init__(
            self,
            log_msg: str,
            gui_msg: Optional[str] = None
    ):
        super().__init__(log_msg=log_msg, gui_msg=gui_msg)
