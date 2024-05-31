# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""Basic routings regarding scheduing.

Basic functions for handling Cron, Crontab, and other scheduling-related
features.
"""
import subprocess
import tools
import logger
# config.*


def read_crontab():
    """Read current users crontab.

    On errors an empty list is returned.

    Returns:
        list: Crontab lines.

    Dev notes (buhtz, 2024-05): Might should raise exception on errors.
    """

    try:
        proc = subprocess.run(
            ['crontab', '-l'],
            check=True,
            capture_output=True,
            text=True)

    except FileNotFoundError:
        logger.error('Command "crontab" not found.')
        return []

    except subprocess.CalledProcessError as err:
        logger.error('Failed to get crontab lines. Return code '
                     f'of {err.cmd} was {err.returncode}.')
        return []

    content = proc.stdout.split('\n')

    # Fixes issue #1181 (line count of empty crontab was 1 instead of 0)
    if content == ['']:
        content = []

    return content


def write_crontab(lines):
    """Write users crontab.

    This will overwrite the whole users crontab. So to keep the old crontab
    and only add new entries you need to read it first with
    :py:func:`tools.readCrontab`, append new entries to the list and write
    it back.

    Args:
        lines (list, tuple): Lines that should be written to crontab.

    Returns:
        bool: ``True`` if successful.

    """
    content = '\n'.join(lines)

    # Pipe the content (via echo over stdout) to crontab's stdin
    with subprocess.Popen(['echo', content], stdout=subprocess.PIPE) as echo:

        try:
            subprocess.run(
                ['crontab', '-'],
                stdin=echo.stdout,
                check=True,
                capture_output=True,
                text=True
            )

        except FileNotFoundError as err:
            logger.error('Command "crontab" not found.')
            return False

        except subprocess.CalledProcessError as err:
            logger.error('Failed to write crontab lines. Return code '
                         f'was {err.returncode}. Error was:\n{err.stderr}')

    return True
