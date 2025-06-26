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
from typing import Callable
import logger
import tools
from bitbase import ScheduleMode, TimeUnit
from exceptions import InvalidChar, InvalidCmd, LimitExceeded

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
    """
    proc = subprocess.run(
        [CRONTAB_COMMAND, '-l'],
        check=False,
        capture_output=True,
        text=True)

    # Error?
    if proc.returncode != 0:
        # Ignore missing crontabs
        if not proc.stderr.startswith('no crontab for'):
            logger.error(f'Failed to get content via "{CRONTAB_COMMAND}". '
                         f'Return code of {proc.args} was {proc.returncode}. '
                         f'Stderr: {proc.stderr}')

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
        lines(list): List of crontab lines.
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


def add_udev_rule(pid: str,
                  udev_setup: tools.SetupUdev,
                  dest_path: str,
                  exec_command: str,
                  notify_callback: Callable
                  ):
    """Initiate adding udev rule for profile."""

    if not udev_setup.isReady:
        logger.error(
            f'Failed to install Udev rule for profile {pid}. DBus Service '
            '"net.launchpad.backintime.serviceHelper" not available')

        notify_callback(_(
            "Could not install Udev rule for profile {profile_id}. "
            "DBus Service '{dbus_interface}' wasn't available."
        ).format(
            profile_id=pid,
            dbus_interface='net.launchpad.backintime.serviceHelper'))

        return

    uuid = tools.uuidFromPath(dest_path)

    if uuid is None:
        logger.error(
            f"Couldn't find UUID for \"{dest_path}\"")
        notify_callback(_("Couldn't find UUID for {path}").format(
            path=f'"{dest_path}"'))

        return

    try:
        udev_setup.addRule(exec_command, uuid)

    except (InvalidChar, InvalidCmd, LimitExceeded) as exc:
        logger.error(str(exc))
        notify_callback(str(exc))


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def create_cron_line(schedule_mode: ScheduleMode,  # noqa: PLR0913
                     cron_command: str,
                     hour: int,
                     minute: int,
                     day: int,
                     weekday: int,
                     offset: str,
                     custom_backup_time: str,
                     repeat_unit: TimeUnit,
                     pid: str,
                     notify_callback: Callable) -> str:
    """Create a crontab line based on the given arguments.

    Returns:
        A crontab line or `None` in case of errors or unscheduled profiles.
    """
    try:
        return _simple_cron_line(
            schedule_mode=schedule_mode,
            minute=minute,
            hour=hour,
            offset=offset,
            day=day,
            weekday=weekday,
            cmd=cron_command)
    except KeyError:
        pass

    if ScheduleMode.DISABLED is schedule_mode:
        # Might raise an exception?
        return ''

    if ScheduleMode.CUSTOM_HOUR is schedule_mode:
        return f'{offset}  {custom_backup_time} * * * {cron_command}'

    if ScheduleMode.REPEATEDLY is schedule_mode:
        if repeat_unit.value <= TimeUnit.DAY.value:
            return f'*/15 * * * * {cron_command}'

        return f'0 * * * * {cron_command}'

    msg = (f'Unexpected error while creating cron line for profile "{pid}" '
           f'with schedule mode "{schedule_mode}".')
    logger.error(msg)
    notify_callback(msg)

    return None


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def _simple_cron_line(schedule_mode: ScheduleMode,  # noqa: PLR0913
                      minute,  # pylint: disable=unused-argument
                      hour,  # pylint: disable=unused-argument
                      offset,  # pylint: disable=unused-argument
                      day,  # pylint: disable=unused-argument
                      weekday,  # pylint: disable=unused-argument
                      cmd  # pylint: disable=unused-argument
                      ) -> str:
    result = {
        ScheduleMode.AT_EVERY_BOOT: '@reboot {cmd}',
        ScheduleMode.MINUTES_5: '*/5 * * * * {cmd}',
        ScheduleMode.MINUTES_10: '*/10 * * * * {cmd}',
        ScheduleMode.MINUTES_30: '*/30 * * * * {cmd}',
        ScheduleMode.HOUR_1: '{offset} * * * * {cmd}',
        ScheduleMode.HOURS_2: '{offset} */2 * * * {cmd}',
        ScheduleMode.HOURS_4: '{offset} */4 * * * {cmd}',
        ScheduleMode.HOURS_6: '{offset} */6 * * * {cmd}',
        ScheduleMode.HOURS_12: '{offset} */12 * * * {cmd}',
        ScheduleMode.DAY: '{minute} {hour} * * * {cmd}',
        ScheduleMode.WEEK: '{minute} {hour} * * {weekday} {cmd}',
        ScheduleMode.MONTH: '{minute} {hour} {day} * * {cmd}',
        ScheduleMode.YEAR: '{minute} {hour} 1 1 * {cmd}',
    }[schedule_mode]

    return result.format(**locals())
