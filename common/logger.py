#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import syslog
import os
import sys
import atexit

import bcolors

DEBUG = False            # Set to "True" when passing "--debug" as cmd arg
SYSLOG_IDENTIFIER = 'backintime'
SYSLOG_MESSAGE_PREFIX = ''

# Labels for the syslog levels
_level_names = {
    syslog.LOG_INFO: 'INFO',
    syslog.LOG_ERR: 'ERROR',
    syslog.LOG_WARNING: 'WARNING',
    syslog.LOG_DEBUG: 'DEBUG'
}


def openlog():
    """
    Initialize the BiT logger system (which uses syslog)

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


def error(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = '%s %s' % (_debugHeader(parent, traceDepth), msg)

    print('%sERROR%s: %s' % (bcolors.FAIL, bcolors.ENDC, msg), file=sys.stderr)

    _do_syslog(msg, syslog.LOG_ERR)


def warning(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = '%s %s' % (_debugHeader(parent, traceDepth), msg)

    print('%sWARNING%s: %s' % (bcolors.WARNING, bcolors.ENDC, msg),
          file=sys.stderr)

    _do_syslog(msg, syslog.LOG_WARNING)


def info(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = '%s %s' % (_debugHeader(parent, traceDepth), msg)

    print('%sINFO%s: %s' % (bcolors.OKGREEN, bcolors.ENDC, msg),
          file=sys.stderr)

    _do_syslog(msg, syslog.LOG_INFO)


def debug(msg, parent=None, traceDepth=0):
    if DEBUG:
        msg = '%s %s' % (_debugHeader(parent, traceDepth), msg)

        # Why does this code differ from eg. "error()"
        # (where the following lines are NOT part of the "if")?
        print('%sDEBUG%s: %s' % (bcolors.OKBLUE, bcolors.ENDC, msg),
              file=sys.stderr)

        _do_syslog(msg, syslog.LOG_DEBUG)


def deprecated(parent=None):
    """Dev note (buhtz 2023-07-23): To my knowledge this function is called
    only one time in BIT. I assume it could be replace with python's own
    deprecation warning system.
    """

    frame = sys._getframe(1)
    fdir, fname = os.path.split(frame.f_code.co_filename)
    fmodule = os.path.basename(fdir)
    line = frame.f_lineno
    if parent:
        fclass = '%s.' %parent.__class__.__name__
    else:
        fclass = ''
    func = frame.f_code.co_name

    frameCaller = sys._getframe(2)
    fdirCaller, fnameCaller = os.path.split(frameCaller.f_code.co_filename)
    fmoduleCaller = os.path.basename(fdirCaller)
    lineCaller = frameCaller.f_lineno

    msg = '%s/%s:%s %s%s called from ' %(fmodule, fname, line, fclass, func)
    msgCaller = '%s/%s:%s' %(fmoduleCaller, fnameCaller, lineCaller)

    print('%sDEPRECATED%s: %s%s%s%s' %(bcolors.WARNING, bcolors.ENDC, msg, bcolors.OKBLUE, msgCaller, bcolors.ENDC), file=sys.stderr)

    _do_syslog('DEPRECATED: %s%s' % (msg, msgCaller), syslog.LOG_WARNING)


def _debugHeader(parent, traceDepth):
    frame = sys._getframe(2 + traceDepth)
    fdir, fname = os.path.split(frame.f_code.co_filename)
    fmodule = os.path.basename(fdir)
    line = frame.f_lineno

    fclass = '%s.' % parent.__class__.__name__ if parent else ''

    func = frame.f_code.co_name
    return '[%s/%s:%s %s%s]' % (fmodule, fname, line, fclass, func)
