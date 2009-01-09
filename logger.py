#    Back In Time
#    Copyright (C) 2008,2009 Oprea Dan
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

def openlog():
	name = os.getenv( 'LOGNAME', 'unknown' )
	syslog.openlog( "backintime (%s)" % name )

def closelog():
	syslog.closelog()

def error( msg ):
	print 'ERROR: ' + msg
	syslog.syslog( syslog.LOG_ERR, 'ERROR: ' + msg )

def warning( msg ):
	print 'WARNING: ' + msg
	syslog.syslog( syslog.LOG_WARNING, 'WARNING: ' + msg )

def info( msg ):
	print 'INFO: ' + msg
	syslog.syslog( syslog.LOG_INFO, 'INFO: ' + msg )

