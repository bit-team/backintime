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
class ApplicationInstance:

	#specify the file used to save the application instance pid
	def __init__( self, pid_file, auto_exit = True ):
		self.pid_file = pid_file

		if auto_exit:
			if self.check( True ):
				self.start_application()

	#check if the current application is already running, returns True if this is the application instance
	def check( self, auto_exit = False ):
		#check if the pidfile exists
		if not os.path.isfile( self.pid_file ):
			return True

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
			return True

		try:
			os.kill( pid, 0 )	#this will raise an exception if the pid is not valid
		except:
			return True

		if auto_exit:
			#exit the application
			print "The application is already running !"
			exit(0) #exit raise an exception so don't put it in a try/except block

		return False

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


if __name__ == '__main__':
	#create application instance
	app_instance = ApplicationInstance( '/tmp/myapp.pid' )

	#do something here
	print "Start MyApp"
	time.sleep(5)	#sleep 5 seconds
	print "End MyApp"

	#remove pid file
	app_instance.exit_application()

