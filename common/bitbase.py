# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Basic constants used in multiple modules."""
from enum import Enum
from pathlib import Path

# See issue #1734 and #1735
URL_ENCRYPT_TRANSITION = 'https://github.com/bit-team/backintime' \
                         '/blob/-/doc/ENCRYPT_TRANSITION.md'

USER_MANUAL_ONLINE_URL = 'https://backintime.readthedocs.io'
USER_MANUAL_LOCAL_PATH = Path('/') / 'usr' / 'share' / 'doc' / \
    'backintime-common' / 'manual' / 'index.html'
USER_MANUAL_LOCAL_AVAILABLE = USER_MANUAL_LOCAL_PATH.exists()

# About transition of encryption feature and the removal of EncFS (see #1734).
# The warnings and deprecation messages are gradually increased in intensity
# and clarity. This constant is the currently desired stage of intensity. The
# last shown intensity is stored in the state data file. If they don't fit, the
# message is displayed.
ENCFS_MSG_STAGE = 2


class TimeUnit(Enum):
    """Describe time units used in context of scheduling.
    """
    HOUR = 10  # Config.HOUR
    DAY = 20  # Config.DAY
    WEEK = 30  # Config.WEEK
    MONTH = 40  # Config.MONTH
