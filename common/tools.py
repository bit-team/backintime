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
import sys
import subprocess


ON_AC = 0
ON_BATTERY = 1
POWER_ERROR = 255

def get_backintime_path( path ):
	return os.path.join( os.path.dirname( os.path.abspath( os.path.dirname( __file__ ) ) ), path )


def register_backintime_path( path ):
	path = get_backintime_path( path )
	if not path in sys.path:
		sys.path = [path] + sys.path


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


def make_dirs( path ):
	path = path.rstrip( os.sep )
	if len( path ) <= 0:
		return

	if not os.path.isdir( path ):
		try:
			os.makedirs( path )
		except:
			pass


def process_exists( name ):
	output = read_command_output( "ps -o pid= -C %s" % name )
	return len( output ) > 0


def check_x_server():
	return 0 == os.system( 'xdpyinfo >/dev/null 2>&1' )


def prepare_path( path ):
	path = path.strip( "/" )
	path = os.sep + path
	return path


def power_status_available():
	"""Uses the on_ac_power command to detect if the the system is able
	to return the power status."""
	try:
		rt = subprocess.call( 'on_ac_power' )
		if rt == ON_AC or rt == ON_BATTERY:
			return True
	except:
		pass
	return False


def on_battery():
	"""Checks if the system is on battery power."""
	if power_status_available ():
		return subprocess.call ( 'on_ac_power' ) == ON_BATTERY
	else:
		return False

def get_snapshots_list_in_folder( folder, sort_reverse = True ):
	biglist = []
	#print folder

	try:
		biglist = os.listdir( folder )
		#print biglist
	except:
		pass

	list = []

	for item in biglist:
		#print item + ' ' + str(len( item ))
		if len( item ) != 15 and len( item ) != 19:
			continue
		if os.path.isdir( os.path.join( folder, item, 'backup' ) ):
			#print item
			list.append( item )

	list.sort( reverse = sort_reverse )
	return list


