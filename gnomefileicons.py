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
import pygtk
pygtk.require("2.0")
import gtk
import gnomevfs


class GnomeFileIcons:
	def __init__( self ):
		self.all_icons = gtk.icon_theme_get_default().list_icons()
		self.cache = {}
		self.user_path = os.path.expanduser( '~' )
		self.special_folders = {}

		self.update_special_folder_icons()

	def add_special_folder_( self, path, icon_name ):
		if len( path ) <= 0:
			return

		if not icon_name in self.all_icons:
			icon_name = 'folder'

		self.special_folders[ path ] = icon_name

	def get_special_folder_path( self, name ):
		path = ''

		try:
			pipe = os.popen( "cat %s/.config/user-dirs.dirs 2>/dev/null | grep %s=" % ( self.user_path, name ), 'r' )
			path = pipe.read()
			pipe.close()
		except:
			pass

		if len( path ) <= 0:
			return ''

		path = path[ len( name ) + 1 : ]
		if path[ 0 ] == '"':
			path = path[ 1 : -2 ]

		path = path.replace( '$HOME', self.user_path )
		return path

	def update_special_folder_icons( self ):
		self.special_folders = {}

		#add desktop
		self.add_special_folder_( self.get_special_folder_path( 'XDG_DESKTOP_DIR' ), 'user-desktop' )
		
		#add home
		self.add_special_folder_( self.user_path, 'user-home' )
		
	def get_icon( self, path ):
		if not os.path.exists(path):
			return gtk.STOCK_FILE

		#check if it is a special folder
		if path in self.special_folders:
			return self.special_folders[path]

		#get mime type
		mime_type = gnomevfs.get_mime_type( gnomevfs.escape_path_string( path ) )
		mime_type = mime_type.replace( '/', '-' )

		#search in the cache
		if mime_type in self.cache:
			return self.cache[mime_type]

		#print "path: " + path
		#print "mime: " + mime_type

		#try gnome mime
		items = mime_type.split('-')
		for aux in xrange(len(items)-1):
			icon_name = "gnome-mime-" + '-'.join(items[:len(items)-aux])
			if icon_name in self.all_icons:
				#print "icon: " + icon_name
				self.cache[mime_type] = icon_name
				return icon_name

		#try folder
		if os.path.isdir( path ):
			icon_name = 'folder'
			if icon_name in self.all_icons:
				#print "icon: " + icon_name
				self.cache[mime_type] = icon_name
				return icon_name

			#print "icon: " + icon_name
			icon_name = gtk.STOCK_DIRECTORY
			self.cache[mime_type] = icon_name
			return icon_name

		#try simple mime
		for aux in xrange(len(items)-1):
			icon_name = '-'.join(items[:len(items)-aux])
			if icon_name in self.all_icons:
				#print "icon: " + icon_name
				self.cache[mime_type] = icon_name
				return icon_name

		#file icon
		icon_name = gtk.STOCK_FILE
		self.cache[mime_type] = icon_name
		return icon_name

