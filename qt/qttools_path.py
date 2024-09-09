# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""Helper functions extracted from qt/qttools.py file.

Extraction happened of problems with import dependencies. The whole path
manipulation will become obsolete when migrating to state of the art Python
packaging standards. This module is a workaround and will get refactored in
the future.
"""
import os
import sys


def backintimePath(*path):
    """Return the path of the backintime project folder."""
    return os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, *path))


def registerBackintimePath(*path):
    """Find duplicate in common/tools.py
    """
    path = backintimePath(*path)

    if path not in sys.path:
        sys.path.insert(0, path)
