#    Back In Time
#    Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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

import tools
import bcolors

DEBUG = False

def openlog():
    name = os.getenv( 'LOGNAME', 'unknown' )
    syslog.openlog( "backintime (%s)" % name )
    atexit.register(closelog)

def closelog():
    syslog.closelog()

def error(msg , parent = None, traceDepth = 0):
    if DEBUG:
        msg = '%s %s' %(_debugHeader(parent, traceDepth), msg)
    print('%sERROR%s: %s' %(bcolors.FAIL, bcolors.ENDC, msg), file=sys.stderr)
    for line in tools.wrap_line(msg):
        syslog.syslog( syslog.LOG_ERR, 'ERROR: ' + line )

def warning(msg , parent = None, traceDepth = 0):
    if DEBUG:
        msg = '%s %s' %(_debugHeader(parent, traceDepth), msg)
    print('%sWARNING%s: %s' %(bcolors.WARNING, bcolors.ENDC, msg), file=sys.stderr)
    for line in tools.wrap_line(msg):
        syslog.syslog( syslog.LOG_WARNING, 'WARNING: ' + line )

def info(msg , parent = None, traceDepth = 0):
    if DEBUG:
        msg = '%s %s' %(_debugHeader(parent, traceDepth), msg)
    print('%sINFO%s: %s' %(bcolors.OKGREEN, bcolors.ENDC, msg), file=sys.stdout)
    for line in tools.wrap_line(msg):
        syslog.syslog( syslog.LOG_INFO, 'INFO: ' + line )

def debug(msg, parent = None, traceDepth = 0):
    if DEBUG:
        msg = '%s %s' %(_debugHeader(parent, traceDepth), msg)
        print('%sDEBUG%s: %s' %(bcolors.OKBLUE, bcolors.ENDC, msg), file = sys.stdout)
        for line in tools.wrap_line(msg):
            syslog.syslog(syslog.LOG_DEBUG, 'DEBUG: %s' %line)

def _debugHeader(parent, traceDepth):
    frame = sys._getframe(2 + traceDepth)
    fdir, fname = os.path.split(frame.f_code.co_filename)
    fmodule = os.path.basename(fdir)
    line = frame.f_lineno
    if parent:
        fclass = '%s.' %parent.__class__.__name__
    else:
        fclass = ''
    func = frame.f_code.co_name
    return '[%s/%s:%s %s%s]' %(fmodule, fname, line, fclass, func)
