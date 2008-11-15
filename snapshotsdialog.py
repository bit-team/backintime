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


import os
import os.path
import sys
import pygtk
pygtk.require("2.0")
import gtk
import gobject
import gtk.glade
import datetime
import gettext

import config


_=gettext.gettext


class SnapshotsDialog:
	def __init__( self, config, glade ):
		self.config = config
		self.glade = glade
		self.path = None
		self.snapshots = None
		self.dialog = self.glade.get_widget( 'SnapshotsDialog' )

		signals = { 
				#'on_cbMinFreeSpace_toggled' : self.updateMinFreeSpace,
			}

		self.glade.signal_autoconnect( signals )
		
		#path
		self.editPath = self.glade.get_widget( 'editPath' )

		#setup backup folders
		self.listSnapshots = self.glade.get_widget( 'listSnapshots' )

		textRenderer = gtk.CellRendererText()

		column = gtk.TreeViewColumn( _('Snapshots') )
		column.pack_end( textRenderer, True )
		column.add_attribute( textRenderer, 'markup', 0 )
		self.listSnapshots.append_column( column )

		self.storeSnapshots = gtk.ListStore( str, str )
		self.listSnapshots.set_model( self.storeSnapshots )

	def update_snapshots( self ):
		self.editPath.set_text( path )

	def run( self, path, snapshots ):
		self.path = path
		self.snapshots = snapshots
		self.update_snapshots()

		retVal = None
		while True:
			retVal = self.dialog.run()
			if gtk.RESPONSE_CANCEL == retVal:
				break
			if gtk.RESPONSE_OK == retVal:
				break
		self.dialog.hide()
		return retVal

