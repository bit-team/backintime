# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""
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


def _determine_crontab_command() -> str:
    """Return the name of one of the supported crontab commands if available.

    Returns:
        (str): The command name. Usually "crontab" or "fcrontab".

    Raises:
        RuntimeError: If none of the supported commands available.
    """
    to_check_commands = ['crontab', 'fcrontab']
    for cmd in to_check_commands:
        proc = subprocess.run(
            ['which', cmd],
            stdout=subprocess.PIPE,
            check=False
        )
        if proc.returncode == 0:
            return cmd

    # syslog is not yet initialized
    logger.openlog()
    msg = 'Command ' + ' and '.join(to_check_commands) + ' not found.'
    logger.critical(msg)

    raise RuntimeError(msg)


CRONTAB_COMMAND = _determine_crontab_command()


def read_crontab():
    """Read current users crontab.

    On errors an empty list is returned.

    Returns:
        list: Crontab lines.

    Dev notes (buhtz, 2024-05): Might should raise exception on errors.
    """
    try:
        proc = subprocess.run(
            [CRONTAB_COMMAND, '-l'],
            check=True,
            capture_output=True,
            text=True)

    except subprocess.CalledProcessError as err:
        logger.error(f'Failed to get content via "{CRONTAB_COMMAND}". '
                     f'Return code of {err.cmd} was {err.returncode}.')
        return []

    content = proc.stdout.split('\n')

    # Remove empty lines from the end
    try:
        while content[-1] == '':
            content = content[:-1]
    except IndexError:
        pass

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

    # Crontab needs to end with a newline
    if not content.endswith('\n'):
        content += '\n'

    # Pipe the content (via echo over stdout) to crontab's stdin
    with subprocess.Popen(['echo', content], stdout=subprocess.PIPE) as echo:

        try:
            subprocess.run(
                [CRONTAB_COMMAND, '-'],
                stdin=echo.stdout,
                check=True,
                capture_output=True,
                text=True
            )

        except subprocess.CalledProcessError as err:
            logger.error(
                f'Failed to write crontab lines with "{CRONTAB_COMMAND}". '
                f'Return code was {err.returncode}. '
                f'Error was:\n{err.stderr}')
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
    """Add new entries to existing crontab content.

    Args:
        crontab(list): A list of strings as crontab lines.
        bit_lines(list): A list of strings as new crontab lines.

    Returns:
        list: The new crontab lines.
    """
    for line in bit_lines:
        crontab.append(_MARKER)
        crontab.append(line)

    return crontab


def is_cron_running():
    """Validate if a cron instance is running.

    The output of ``ps`` is searched (case-insensitive) via ``grep`` for the
    string ``cron``.

    Returns:
        bool: The answer.
    """

    with subprocess.Popen(['ps', '-eo', 'comm'], stdout=subprocess.PIPE) as ps:
        try:
            subprocess.run(
                ['grep', '--ignore-case', 'cron'],
                stdin=ps.stdout,
                stdout=subprocess.PIPE,
                check=True
            )
        except subprocess.CalledProcessError:
            return False

    return True
