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
import gtk.glade
import gettext

import config


_=gettext.gettext


class SnapshotNameDialog:
	def __init__( self, snapshots, glade, snapshot_id ):
		self.snapshots = snapshots 
		self.config = snapshots.config
		self.glade = glade
		self.snapshot_id = snapshot_id

		self.dialog = self.glade.get_widget( 'SnapshotNameDialog' )

		signals = { 
			#'on_btnRestoreSnapshot_clicked' : self.on_btnRestoreSnapshot_clicked
			}

		self.glade.signal_autoconnect( signals )
		
		#name
		self.edit_name = self.glade.get_widget( 'edit_snapshot_name' )
		self.old_name = self.snapshots.get_snapshot_name( self.snapshot_id )
		self.edit_name.set_text( self.old_name )

	def run( self ):
		changed = False
		while True:
			ret_val = self.dialog.run()
			
			if gtk.RESPONSE_OK == ret_val: #go to
				new_name = self.edit_name.get_text().strip()
				if new_name != self.old_name:
					self.snapshots.set_snapshot_name( self.snapshot_id, new_name )
					changed = True
				break
			else:
				#cancel, close ...
				break

		self.dialog.hide()
		return changed

