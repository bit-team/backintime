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


class RenameSnapshotDialog:
	def __init__( self, config, glade ):
		self.config = config
		self.glade = glade

		self.snapshot = None

		self.dialog = self.glade.get_widget( 'RenameSnapshotDialog' )

		signals = { 
			#'on_btnRestoreSnapshot_clicked' : self.on_btnRestoreSnapshot_clicked
			}

		self.glade.signal_autoconnect( signals )
		
		#name
		self.editName = self.glade.get_widget( 'editSnapshotName' )

	def run( self, snapshot ):
		self.snapshot = snapshot
		old_name = self.config.snapshotName( self.snapshotName )
		self.editName.set_text( old_name )

		returnValue = False
		while True:
			retVal = self.dialog.run()
			
			if gtk.RESPONSE_OK == retVal: #go to
				new_name = self.editName.get_text()
				if new_name != old_name:
					self.config.setSnapshotName( new_name )
					returnValue = True
				break
			else:
				#cancel, close ...
				break

		self.dialog.hide()
		return returnValue

