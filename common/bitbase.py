# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Basic constants used in multiple modules."""

from enum import Enum

# See issue #1734 and #1735
URL_ENCRYPT_TRANSITION = 'https://github.com/bit-team/backintime' \
                         '/blob/-/doc/ENCRYPT_TRANSITION.md'


class TimeUnit(Enum):
    """Describe time units used in context of scheduling.
    """
    HOUR = 10  # Config.HOUR
    DAY = 20  # Config.DAY
    WEEK = 30  # Config.WEEK
    MONTH = 40  # Config.MONTH
