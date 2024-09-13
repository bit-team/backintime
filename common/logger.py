# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import syslog
import os
import sys
import atexit
import bcolors

DEBUG = False  # Set to "True" when passing "--debug" as cmd arg
SYSLOG_IDENTIFIER = 'backintime'
SYSLOG_MESSAGE_PREFIX = ''

# Labels for the syslog levels
_level_names = {
    syslog.LOG_INFO: 'INFO',
    syslog.LOG_WARNING: 'WARNING',
    syslog.LOG_ERR: 'ERROR',
    syslog.LOG_CRIT: 'CRITICAL',
    syslog.LOG_DEBUG: 'DEBUG',
}


def openlog():
    """Initialize the BIT logger system (which uses syslog)

    Esp. sets the app name as identifier for the log entries in the syslog.

    Attention: Call it in each sub process that uses logging.
    """
    syslog.openlog(SYSLOG_IDENTIFIER)
    atexit.register(closelog)


def changeProfile(profile_id, profile_name):
    global SYSLOG_MESSAGE_PREFIX
    SYSLOG_MESSAGE_PREFIX = f'{profile_name}({profile_id}) :: '


def closelog():
    syslog.closelog()


def _do_syslog(message: str, level: int) -> str:
    syslog.syslog(level, '{}{}: {}'.format(
        SYSLOG_MESSAGE_PREFIX, _level_names[level], message))


def critical(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = _debugHeader(parent, traceDepth) + ' ' + msg

    print(f'{bcolors.CRITICAL}CRITICAL{bcolors.ENDC}: {msg}', file=sys.stderr)

    _do_syslog(msg, syslog.LOG_CRIT)


def error(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = _debugHeader(parent, traceDepth) + ' ' + msg

    print(f'{bcolors.FAIL}ERROR{bcolors.ENDC}: {msg}', file=sys.stderr)

    _do_syslog(msg, syslog.LOG_ERR)


def warning(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = _debugHeader(parent, traceDepth) + ' ' + msg

    print(f'{bcolors.WARNING}WARNING{bcolors.ENDC}: {msg}', file=sys.stderr)

    _do_syslog(msg, syslog.LOG_WARNING)


def info(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = _debugHeader(parent, traceDepth) + ' ' + msg

    print(f'{bcolors.OKGREEN}INFO{bcolors.ENDC}: {msg}', file=sys.stderr)

    _do_syslog(msg, syslog.LOG_INFO)


def debug(msg, parent=None, traceDepth=0):
    if not DEBUG:
        return

    msg = _debugHeader(parent, traceDepth) + ' ' + msg

    print(f'{bcolors.OKBLUE}DEBUG{bcolors.ENDC}: {msg}', file=sys.stderr)

    _do_syslog(msg, syslog.LOG_DEBUG)


def _debugHeader(parent, traceDepth):
    frame = sys._getframe(2 + traceDepth)
    line = frame.f_lineno
    func = frame.f_code.co_name

    fdir, fname = os.path.split(frame.f_code.co_filename)
    fmodule = os.path.basename(fdir)

    fclass = f'{parent.__class__.__name__}.' if parent else ''

    return f'[{fmodule}/{fname}:{line} {fclass}{func}]'
