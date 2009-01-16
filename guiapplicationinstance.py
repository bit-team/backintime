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
import time


#class used to handle one application instance mechanism
class GUIApplicationInstance:

	#specify the base for control files
	def __init__( self, base_control_file, raise_cmd = '' ):
		self.pid_file = base_control_file + '.pid'
		self.raise_file = base_control_file + '.raise'
		self.raise_cmd = raise_cmd

		#remove raise_file is already exists
		try:
			os.remove( self.raise_file )
		except:
			pass

		self.check( raise_cmd )
		self.start_application()

	#check if the current application is already running
	def check( self, raise_cmd ):
		#check if the pidfile exists
		if not os.path.isfile( self.pid_file ):
			return

		#read the pid from the file
		pid = 0
		try:
			file = open( self.pid_file, 'rt' )
			data = file.read()
			file.close()
			pid = int( data )
		except:
			pass

		#check if the process with specified by pid exists
		if 0 == pid:
			return

		try:
			os.kill( pid, 0 )	#this will raise an exception if the pid is not valid
		except:
			return

		#exit the application
		print "The application is already running ! (pid: %s)" % pid

		#notify raise
		try:
			file = open( self.raise_file, 'wt' )
			file.write( raise_cmd )
			file.close()
		except:
			pass

		exit(0) #exit raise an exception so don't put it in a try/except block

	#called when the single instance starts to save it's pid
	def start_application( self ):
		file = open( self.pid_file, 'wt' )
		file.write( str( os.getpid() ) )
		file.close()

	#called when the single instance exit ( remove pid file )
	def exit_application( self ):
		try:
			os.remove( self.pid_file )
		except:
			pass

	#check if the application must to be raised
	#return None if no raise needed, or a string command to raise
	def raise_command( self ):
		ret_val = None

		try:
			if os.path.isfile( self.raise_file ):
				file = open( self.raise_file, 'rt' )
				ret_val = file.read()
				file.close()
				os.remove( self.raise_file )
		except:
			pass

		return ret_val

