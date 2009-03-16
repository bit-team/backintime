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


import os.path
import os


def read_file( path, default_value = None ):
	ret_val = default_value 

	try:
		file = open( path )
		ret_val = file.read()
		file.close()
	except:
		pass

	return ret_val


def read_file_lines( path, default_value = None ):
	ret_val = default_value 

	try:
		file = open( path )
		ret_val = file.readlines()
		file.close()
	except:
		pass

	return ret_val


def read_command_output( cmd ):
	ret_val = ''

	try:
		pipe = os.popen( cmd )
		ret_val = pipe.read().strip()
		pipe.close() 
	except:
		return ''

	return ret_val


def check_command( cmd ):
	cmd = cmd.strip()

	if len( cmd ) < 1:
		return False

	if os.path.isfile( cmd ):
		return True

	cmd = read_command_output( "which \"%s\"" % cmd )

	if len( cmd ) < 1:
		return False

	if os.path.isfile( cmd ):
		return True

	return False

