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


class ConfigFile:
	def __init__( self ):
		self.dict = {}

	def save( self, filename ):
		try:
			file = open( filename, 'w' )
			for key, value in self.dict.items():
				file.write( "%s=%s\n" % ( key, value ) )
			file.close()
		except:
			pass

	def load( self, filename ):
		self.dict = {}
		self.append( filename )

	def append( self, filename ):
		lines = []

		try:
			file = open( filename, 'r' )
			lines = file.readlines()
			file.close()
		except:
			pass

		for line in lines:
			items = line.split( '=' )
			if len( items ) == 2:
				self.dict[ items[ 0 ] ] = items[ 1 ][ : -1 ]

	def get_if_dont_exists( self, dict, config2 ):
		#key is the old key, value is the new key 
		changed = False

		for key, value in dict.iteritems():
			if key in config2.dict:
				if not value in self.dict:
					self.dict[value] = config2.dict[key]
					changed = True

		return changed

	def get_str_value( self, key, default_value = '' ):
		try:
			return self.dict[ key ]
		except:
			return default_value

	def set_str_value( self, key, value ):
		self.dict[ key ] = value

	def get_int_value( self, key, default_value = 0 ):
		try:
			return int( self.dict[ key ] )
		except:
			return default_value

	def set_int_value( self, key, value ):
		self.dict[ key ] = str( value )

	def get_bool_value( self, key, default_value = False ):
		try:
			val = self.dict[ key ]
			if "1" == val or "TRUE" == val.upper():
				return True
			return False
		except:
			return default_value

	def set_bool_value( self, key, value ):
		if value:
			self.dict[ key ] = 'true'
		else:
			self.dict[ key ] = 'false'

