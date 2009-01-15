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

	def get_icon( self, path ):
		if not os.path.exists(path):
			return gtk.STOCK_FILE
		
		#get mime type
		mime_type = gnomevfs.get_mime_type( path ).replace( '/', '-' )

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
		if os.path.isdir(path):
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

