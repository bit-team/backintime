# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import syslog
import os
import pwd
import sys
import atexit
import bcolors


DEBUG = False  # Set to "True" when passing "--debug" as cmd arg
SYSLOG_IDENTIFIER = 'backintime'
SYSLOG_MESSAGE_PREFIX = ''
USER = pwd.getpwuid(os.getuid()).pw_name

# Labels for the syslog levels
_level_names = {
    syslog.LOG_INFO: 'INFO',
    syslog.LOG_WARNING: 'WARNING',
    syslog.LOG_ERR: 'ERROR',
    syslog.LOG_CRIT: 'CRITICAL',
    syslog.LOG_DEBUG: 'DEBUG',
}

syslog_id_suffix = '<unknown>'


_level_colors = {
    syslog.LOG_INFO: bcolors.OKGREEN,
    syslog.LOG_WARNING: bcolors.WARNING,
    syslog.LOG_ERR: bcolors.FAIL,
    syslog.LOG_CRIT: bcolors.CRITICAL,
    syslog.LOG_DEBUG: bcolors.OKBLUE
}


def openlog(suffix: str):
    """Initialize the BIT logger system using syslog.

    Attention: Call it in each sub process that uses logging.
    """
    global syslog_id_suffix
    syslog_id_suffix = suffix
    syslog.openlog(SYSLOG_IDENTIFIER)
    atexit.register(closelog)


def changeProfile(profile_id, profile_name):
    global SYSLOG_MESSAGE_PREFIX
    SYSLOG_MESSAGE_PREFIX = f'{profile_name}({profile_id}) :: '


def closelog():
    syslog.closelog()


def _do_syslog(message: str, level: int):
    syslog.syslog(level, '{:8}: {}{}{}'.format(
        _level_names[level],
        f'{USER} ' if DEBUG else '',
        SYSLOG_MESSAGE_PREFIX,
        message
    ))


def _do_stderr(message: str, level: int):
    print(
        f'{_level_colors[level]}{_level_names[level]:8}{bcolors.ENDC}'
        f'{message}',
        file=sys.stderr
    )


def critical(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = _debugHeader(parent, traceDepth) + ' ' + msg

    msg = f' {msg}'
    _do_stderr(msg, syslog.LOG_CRIT)
    _do_syslog(msg, syslog.LOG_CRIT)


def error(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = _debugHeader(parent, traceDepth) + ' ' + msg

    _do_stderr(msg, syslog.LOG_ERR)
    _do_syslog(msg, syslog.LOG_ERR)


def warning(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = _debugHeader(parent, traceDepth) + ' ' + msg

    _do_stderr(msg, syslog.LOG_WARNING)
    _do_syslog(msg, syslog.LOG_WARNING)


def info(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = _debugHeader(parent, traceDepth) + ' ' + msg

    _do_stderr(msg, syslog.LOG_INFO)
    _do_syslog(msg, syslog.LOG_INFO)


def debug(msg, parent=None, traceDepth=0):
    if not DEBUG:
        return

    msg = _debugHeader(parent, traceDepth) + ' ' + msg

    _do_stderr(msg, syslog.LOG_DEBUG)
    _do_syslog(msg, syslog.LOG_DEBUG)


def _debugHeader(parent, traceDepth):
    frame = sys._getframe(2 + traceDepth)
    line = frame.f_lineno
    func = frame.f_code.co_name

    fdir, fname = os.path.split(frame.f_code.co_filename)
    fmodule = os.path.basename(fdir)

    fclass = f'{parent.__class__.__name__}.' if parent else ''

    return f'[{syslog_id_suffix}::{fmodule}/{fname}:{line} {fclass}{func}]'
