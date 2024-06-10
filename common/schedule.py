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
"""Basic or low-level routines regarding scheduling.

Basic functions for handling Cron, Crontab, and other scheduling-related
features.
"""
import subprocess
import logger

_MARKER = '#Back In Time system entry, this will be edited by the gui:'
"""The string is used in crontab file to mark entries as owned by Back
In Time. **WARNING**: Don't modify that string in code because it is used
as match target while parsing the crontab file. See
:func:`remove_bit_from_crontab()` for details.
"""


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
        bool: ``True`` if successful otherwise ``False``.

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
            logger.error(f'Command "crontab" not found. Error was: {err}')
            return False

        except subprocess.CalledProcessError as err:
            logger.error('Failed to write crontab lines. Return code '
                         f'was {err.returncode}. Error was:\n{err.stderr}')
            return False

    return True


def remove_bit_from_crontab(crontab):
    """Remove crontab entries related to backintime and having a marker line in
    the line before.

    Args:
        lines(list): List of crontab liens.
    """
    # Indices of lines containing the marker
    marker_indexes = list(filter(
        lambda idx: _MARKER in crontab[idx],
        range(len(crontab))
    ))

    # Check if there is a valid BIT entry after the marker lines
    for idx in marker_indexes[:]:
        try:
            if 'backintime' in crontab[idx+1]:
                continue
        except IndexError:
            pass

        # Remove the current index because the following line is not valid
        marker_indexes.remove(marker_indexes.index(idx))

    modified_crontab = crontab[:]

    # Remove the marker comment line and the following backintime line
    for idx in reversed(marker_indexes):
        del modified_crontab[idx:idx+2]

    return modified_crontab


def append_bit_to_crontab(crontab, bit_lines):
    # Add a new entry to existing crontab content based on the current
    # snapshot profile and its schedule settings.
    for line in bit_lines:
        crontab.append(_MARKER)
        crontab.append(line)

    return crontab
