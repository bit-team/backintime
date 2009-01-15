#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan
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


import os
import os.path
import stat
import sys
import gettext

import config
import logger
import snapshots

_=gettext.gettext


def take_snapshot( cfg ):
	logger.openlog()
	snapshots.Snapshots( cfg ).take_snapshot()
	logger.closelog()


def print_version( cfg ):
	print 'Back In Time'
	print 'Version: ' + cfg.VERSION


def print_help( cfg ):
	print 'Back In Time'
	print 'Format: '
	print 'backintime [[-s|--snapshots] path]'
	print '\tStarts GUI mode'
	print '\t\t-s, --snapshots: go directly to snapshots dialog for the specified path'
	print '\t\tpath: go directly to the specified path'
	print 'backintime -b|--backup'
	print '\tTake a snapshot and exit'
	print 'backintime -v|--version'
	print '\tShow version and exit'
	print 'backintime -h|--help'
	print '\tShow this help and exit'


if __name__ == '__main__':
	cfg = config.Config()
	print_version( cfg )

	for arg in sys.argv[ 1 : ]:
		if arg == '--backup' or arg == '-b':
			take_snapshot( cfg )
			sys.exit(0)

		if arg == '--version' or arg == '-v':
			sys.exit(0)

		if arg == '--help' or arg == '-h':
			print_help( cfg )
			sys.exit(0)

		if arg == '--snapshots' or arg == '-s':
			continue

		if arg[0] == '-':
			print "Ignore option: %s" % arg
			continue

	print 'This is a non GUI application, and it only implements --backup | --help | --version'

