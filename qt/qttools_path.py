#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar
#    Reitze
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""Helper functions extracted from qt/qttools.py file.

Extraction happened of problems with import dependencies. The whole path
manipulation will become obsolete when migrating to state of the art Python
packaging standards. This module is a workaround and will get refactored in
the future.
"""
import os
import sys

def backintimePath(*path):
    return os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, *path))


def registerBackintimePath(*path):
    """Find duplicate in common/tools.py
    """
    path = backintimePath(*path)

    if path not in sys.path:
        sys.path.insert(0, path)
