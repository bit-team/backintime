#    Back In Time
#    Copyright (C) 2008 Oprea Dan
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


import pygtk
pygtk.require("2.0")
import gtk
import gnomevfs


def clipboard_set_text( text ):
	clipboard = gtk.clipboard_get()
	clipboard.set_text( text )
	clipboard.store()


def clipboard_copy_path( path ):
	targets = gtk.target_list_add_uri_targets()
	targets = gtk.target_list_add_text_targets( targets)
	targets.append( ( 'x-special/gnome-copied-files', 0, 0 ) )

	clipboard = gtk.clipboard_get()
	clipboard.set_with_data( targets, __clipboard_copy_path_get, __clipboard_copy_path_clear, path )
	clipboard.store()


def __clipboard_copy_path_get( clipboard, selectiondata, info, path ):
	selectiondata.set_text( path )
	path2 = gnomevfs.escape_path_string(path)
	selectiondata.set_uris( [ 'file://' + path2 ] )
	selectiondata.set( 'x-special/gnome-copied-files', 8, 'copy\nfile://' + path2 );

def __clipboard_copy_path_clear( self, clipboard, path ):
	return

