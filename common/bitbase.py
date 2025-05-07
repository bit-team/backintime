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

APP_NAME = 'Back In Time'
BINARY_NAME_BASE = 'backintime'
BINARY_NAME_CLI = f'{BINARY_NAME_BASE}'
BINARY_NAME_GUI = f'{BINARY_NAME_BASE}-qt'
PACKAGE_NAME_CLI = f'{BINARY_NAME_BASE}-common'
PACKAGE_NAME_GUI = f'{BINARY_NAME_BASE}-qt'

COPYRIGHT = 'Copyright © 2008-2024 ' \
            'Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze\n' \
            'Copyright © 2022 ' \
            'Christian Buhtz, Michael Büker, Jürgen Altfeld'

# Used in context of CLI and argument parsing
RETURN_OK = 0
RETURN_ERR = 1
RETURN_NO_CFG = 2

# Used in about dialog to add language independent translator credits
TRANSLATION_CREDITS_MISC = (
    'Launchpad translators <https://translations.launchpad.net/backintime/'
    'trunk/+pots/back-in-time>',
    'https://www.reddit.com/r/translator',
    'Several mailing lists in Debian (@lists.debian.org) & Ubuntu '
    '(@lists.ubuntu.com) especially the user related lists',
)

# See issue #1734 and #1735
URL_ENCRYPT_TRANSITION = 'https://github.com/bit-team/backintime' \
                         '/blob/-/doc/ENCRYPT_TRANSITION.md'

URL_SOURCE = 'https://github.com/bit-team/backintime'
URL_WEBSITE = URL_SOURCE
URL_FAQ = f'{URL_WEBSITE}/blob/-/FAQ.md'
URL_ISSUES = f'{URL_WEBSITE}/issues'
URL_ISSUES_CREATE_NEW = f'{URL_ISSUES}/new'
URL_TRANSLATION = 'https://translate.codeberg.org/engage/backintime'
URL_GPL_TWO = 'https://spdx.org/licenses/GPL-2.0-or-later.html'

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

# Names used for backup directories (or symlinks to them) indicating a specific
# state.
DIR_NAME_LAST_SNAPSHOT = 'last_snapshot'
DIR_NAME_NEWSNAPSHOT = 'new_snapshot'
DIR_NAME_SAVETOCONTINUE = 'save_to_continue'


class TimeUnit(Enum):
    """Describe time units used in context of scheduling.
    """
    HOUR = 10  # Config.HOUR
    DAY = 20  # Config.DAY
    WEEK = 30  # Config.WEEK
    MONTH = 40  # Config.MONTH
