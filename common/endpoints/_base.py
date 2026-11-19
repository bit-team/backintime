# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Constants and other basic variables used by all endpoints"""
import bitbase
import logger
from password import Password_Cache
import tools
import subprocess

# The directory used for all temptorary mount points. In most cases it
# is $HOME/.local/share/backintime/mnt
MOUNT_ROOT_PATH = bitbase.XDG_DATA_HOME / bitbase.BINARY_NAME_BASE / 'mnt'

CTLSOCKET_NAME = 'ctlsocket'

LOCK_SUFFIX = 'lock'


def ensure_password_cache(use_cache: bool):
    """Start the password cache process if isn't already"""

    # WORKAROUND
    if not use_cache:
        return

    cache = Password_Cache()

    if cache.status():
        # Still running
        logger.debug('Password cache already running')
        return

    cmd = [
        tools.which(bitbase.BINARY_NAME_CLI),
        'pw-cache',
        'start'
    ]

    logger.debug(f'Call command: {cmd}')
    with subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ) as proc:
        if proc.returncode:
            logger.error(
                'Password cache start failed with return '
                f'code {proc.returncode}'
            )

        else:
            logger.debug('Password cache started')
