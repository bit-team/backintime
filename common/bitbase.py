# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Basic constants used in multiple modules."""
import os
from enum import Enum
from pathlib import Path

# |-------------|
# | Application |
# |-------------|

APP_NAME = 'Back In Time'
BINARY_NAME_BASE = 'backintime'
BINARY_NAME_CLI = f'{BINARY_NAME_BASE}'
BINARY_NAME_GUI = f'{BINARY_NAME_BASE}-qt'
PACKAGE_NAME_CLI = f'{BINARY_NAME_BASE}-common'
PACKAGE_NAME_GUI = f'{BINARY_NAME_BASE}-qt'


# |-----------------|
# | Several strings |
# |-----------------|

COPYRIGHT = 'Copyright © 2008-2024 ' \
            'Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze\n' \
            'Copyright © 2022 ' \
            'Christian Buhtz, Michael Büker, Jürgen Altfeld'

# Used in about dialog to add language independent translator credits
TRANSLATION_CREDITS_MISC = (
    'Launchpad translators <https://translations.launchpad.net/backintime/'
    'trunk/+pots/back-in-time>',
    'https://www.reddit.com/r/translator',
    'Several mailing lists in Debian (@lists.debian.org) & Ubuntu '
    '(@lists.ubuntu.com) especially the user related lists',
)

# |-------------------------------|
# | Online resources & references |
# |-------------------------------|

# See issue #1734 and #1735
URL_ENCRYPT_TRANSITION = 'https://github.com/bit-team/backintime' \
                         '/blob/-/doc/ENCRYPT_TRANSITION.md'
URL_SOURCE = 'https://github.com/bit-team/backintime'
URL_WEBSITE = URL_SOURCE
URL_FAQ = f'{URL_WEBSITE}/blob/-/FAQ.md'
URL_ISSUES = f'{URL_WEBSITE}/issues'
URL_ISSUES_CREATE_NEW = f'{URL_ISSUES}/new'
URL_CHANGELOG = f'{URL_WEBSITE}/blob/dev/CHANGES'
URL_TRANSLATION = 'https://translate.codeberg.org/engage/backintime'
URL_GPL_TWO = 'https://spdx.org/licenses/GPL-2.0-or-later.html'
URL_USER_MANUAL = 'https://backintime.readthedocs.io'

# |---------------------|
# | Directories & files |
# |---------------------|

FILENAME_CONFIG = 'config'

_DIR_DOC_PATH_BASE = Path('/') / 'usr' / 'share' / 'doc'

USER_MANUAL_LOCAL_PATH = _DIR_DOC_PATH_BASE / PACKAGE_NAME_CLI \
    / 'manual' / 'index.html'
USER_MANUAL_LOCAL_AVAILABLE = USER_MANUAL_LOCAL_PATH.exists()

CHANGELOG_LOCAL_PATH = _DIR_DOC_PATH_BASE / PACKAGE_NAME_CLI / 'CHANGES'
CHANGELOG_LOCAL_AVAILABLE = CHANGELOG_LOCAL_PATH.exists()

DIR_CALLBACK_EXAMPLES = _DIR_DOC_PATH_BASE / PACKAGE_NAME_CLI \
    / 'user-callback-examples'
DEFAULT_CALLBACK = DIR_CALLBACK_EXAMPLES / 'user-callback.default'

# Names used for backup directories (or symlinks to them) indicating a specific
# state.
DIR_NAME_LAST_SNAPSHOT = 'last_snapshot'
DIR_NAME_NEWSNAPSHOT = 'new_snapshot'
DIR_NAME_SAVETOCONTINUE = 'save_to_continue'


def _determine_licenses_dir():
    for pkg in (PACKAGE_NAME_GUI,
                PACKAGE_NAME_CLI,
                BINARY_NAME_GUI,
                BINARY_NAME_CLI,
                BINARY_NAME_BASE):
        for path in (Path('/usr/share/doc'), Path('/usr/share/licenses')):

            fp = path / pkg / 'LICENSES'
            if fp.is_dir():
                return fp

    return None


DIR_LICENSES = _determine_licenses_dir()
DIR_SSH_KEYS = Path.home() / '.ssh'

# |-------------------|
# | Enums & constants |
# |-------------------|

# Used in context of CLI and argument parsing
RETURN_OK = 0
RETURN_ERR = 1
RETURN_NO_CFG = 2


class TimeUnit(Enum):
    """Describe time units used in context of scheduling."""
    HOUR = 10  # Config.HOUR
    DAY = 20  # Config.DAY
    WEEK = 30  # Config.WEEK
    MONTH = 40  # Config.MONTH
    YEAR = 80  # Config.YEAR


class ScheduleMode(Enum):
    """Describe schedule mode.

    0 = Disabled
    1 = at every boot
    2 = every 5 minute
    4 = every 10 minute
    7 = every 30 minute
    10 = every hour
    12 = every 2 hours
    14 = every 4 hours
    16 = every 6 hours
    18 = every 12 hours
    19 = custom defined hours
    20 = every day
    25 = daily anacron
    27 = when drive get connected
    30 = every week
    40 = every month
    80 = every year
    """
    DISABLED = 0
    AT_EVERY_BOOT = 1
    MINUTES_5 = 2
    MINUTES_10 = 4
    MINUTES_30 = 7
    HOUR = 10
    HOUR_1 = 10
    HOURS_2 = 12
    HOURS_4 = 14
    HOURS_6 = 16
    HOURS_12 = 18
    CUSTOM_HOUR = 19
    DAY = 20
    REPEATEDLY = 25
    UDEV = 27
    WEEK = 30
    MONTH = 40
    YEAR = 80


HOURLY_BACKUPS = (
    ScheduleMode.HOUR,
    ScheduleMode.HOUR_1,
    ScheduleMode.HOURS_2,
    ScheduleMode.HOURS_4,
    ScheduleMode.HOURS_6,
    ScheduleMode.HOURS_12,
    ScheduleMode.CUSTOM_HOUR)

# |------|
# | Misc |
# |------|

# Indicator if BIT is running in root mode
IS_IN_ROOT_MODE = os.geteuid() == 0

# About transition of encryption feature and the removal of EncFS (see #1734).
# The warnings and deprecation messages are gradually increased in intensity
# and clarity. This constant is the currently desired stage of intensity. The
# last shown intensity is stored in the state data file. If they don't fit, the
# message is displayed.
ENCFS_MSG_STAGE = 2
