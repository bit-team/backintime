# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""Centralize management about the version.

That file is a workaround until the project migrated to a Python build-system.
See Issue #1575 for details about that migration.
"""
import re

# Version string regularyly used by the application and presented to users.
__version__ = '1.6.0-dev.a5c44451'


def is_release_candidate() -> bool:
    """Test if the current version is a release candidate.

    It is the case if the version string ends with lower case ``rc`` and
    optionally with a number.
    """
    return bool(re.search(r'^.+rc\d+$', __version__))
