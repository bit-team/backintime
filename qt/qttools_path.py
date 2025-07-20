# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Helper functions extracted from qt/qttools.py file.

Extraction happened of problems with import dependencies. The whole path
manipulation will become obsolete when migrating to state of the art Python
packaging standards. This module is a workaround and will get refactored in
the future.
"""
import sys
from pathlib import Path


def as_backintime_path(*path: str) -> str:
    """Get path inside ``backintime`` install folder.

    Args:
        *path (str): Paths that should be joined to ``backintime``.

    Returns:
        str: Child path of ``backintime`` child path e.g.
            ``/usr/share/backintime/common``or ``/usr/share/backintime/qt``.
    """
    result = Path(__file__).parent.parent / Path(*path)
    result = result.resolve()

    return str(result)


def register_backintime_path(*path: str):
    """Find duplicate in common/tools.py
    """
    path = as_backintime_path(*path)

    if path not in sys.path:
        sys.path.insert(0, path)
