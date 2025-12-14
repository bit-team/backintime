# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2012-2022 Taylor Raack
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Split from common/encfstools.py.

"""Module related to encrypted backup profiles.
"""
import os


class Bounce:
    """Dummy class that will simply return all input.

    This is the standard for config.ENCODE.
    """

    def __init__(self):
        self.chroot = os.sep

    def path(self, path: str) -> str:
        """The path."""
        return path

    def exclude(self, path: str) -> str:
        """Exclude entry."""
        return path

    def include(self, path: str) -> str:
        """Include entry."""
        return path

    def remote(self, path: str) -> str:
        """Remote path."""
        return path

    def close(self) -> None:
        """Nothing."""
