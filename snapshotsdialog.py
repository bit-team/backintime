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
import gnomeclipboardtools 


_=gettext.gettext


class SnapshotsDialog:
	def __init__( self, config, glade ):
		self.config = config
		self.glade = glade

		self.path = None
		self.snapshots = None
		self.current_snapshot = None

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

		self.storeSnapshots = gtk.ListStore( str, str, str )
		self.listSnapshots.set_model( self.storeSnapshots )

	def get_snapshot_path( self, snapshot ):
		if len( snapshot ) <= 1:
			return '/'

		snapshot_path = self.config.backupPath( snapshot )
		path = os.path.join( snapshot_path, 'backup' )
		return path

	def update_snapshots( self ):
		self.editPath.set_text( self.path )

		#fill snapshots
		self.storeSnapshots.clear()
	
		path = os.path.join( self.current_snapshot, self.path[ 1 : ] )	
		isdir = os.path.isdir( path )
		
		#add now
		path = self.path
		if os.path.exists( path ):
			if os.path.isdir( path ) == isdir:
				self.storeSnapshots.append( [ _('Now'), '/', path ] )

		#add snapshots
		for snapshot in self.snapshots:
			snapshot_path = self.get_snapshot_path( snapshot )
			path = os.path.join( snapshot_path, self.path[ 1 : ] )
			if os.path.exists( path ):
				if os.path.isdir( path ) == isdir:
					nice_name = "%s-%s-%s %s:%s:%s" % ( snapshot[ 0 : 4 ], snapshot[ 4 : 6 ], snapshot[ 6 : 8 ], snapshot[ 9 : 11 ], snapshot[ 11 : 13 ], snapshot[ 13 : 15 ]  )
					self.storeSnapshots.append( [ nice_name, snapshot_path, path ] )

	def run( self, path, snapshots, current_snapshot ):
		self.path = path
		self.snapshots = snapshots
		self.current_snapshot = current_snapshot

		self.update_snapshots()

		retVal = None
		while True:
			retVal = self.dialog.run()
			if gtk.RESPONSE_CANCEL == retVal:
				break
			elif gtk.RESPONSE_OK == retVal: #go to
				iter = self.listSnapshots.get_selection().get_selected()[1]
				if not iter is None:
					snapshot_path = self.storeSnapshots.get_value( iter, 1 )
					retVal = ( snapshot_path, self.path )
				break
			elif 1 == retVal: #copy to clipboard
				iter = self.listSnapshots.get_selection().get_selected()[1]
				if not iter is None:
					snapshot_path = self.storeSnapshots.get_value( iter, 2 )
					gnomeclipboardtools.clipboard_copy_path( snapshot_path )
				continue 

		self.dialog.hide()
		return retVal

