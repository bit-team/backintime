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
import messagebox


_=gettext.gettext


class SnapshotsDialog:
	def __init__( self, backup, glade, path, snapshots, current_snapshot, icon_name ):
		self.backup = backup
		self.config = backup.config
		self.glade = glade

		self.path = path
		self.snapshots = snapshots
		self.current_snapshot = current_snapshot
		self.icon_name = icon_name

		self.dialog = self.glade.get_widget( 'SnapshotsDialog' )

		signals = { 
			'on_listSnapshots_cursor_changed' : self.on_listSnapshots_cursor_changed,
			'on_listSnapshots_row_activated' : self.on_listSnapshots_row_activated,
			'on_listSnapshots_popup_menu' : self.on_listSnapshots_popup_menu,
			'on_listSnapshots_button_press_event': self.on_listSnapshots_button_press_event,
			'on_btnDiffWith_clicked' : self.on_btnDiffWith_clicked,
			'on_btnCopySnapshot_clicked' : self.on_btnCopySnapshot_clicked,
			'on_btnRestoreSnapshot_clicked' : self.on_btnRestoreSnapshot_clicked
			}

		self.glade.signal_autoconnect( signals )
		
		#path
		self.editPath = self.glade.get_widget( 'editPath' )

		#diff
		self.editDiffCmd = self.glade.get_widget( 'editDiffCmd' )
		self.editDiffCmdParams = self.glade.get_widget( 'editDiffCmdParams' )

		diffCmd, diffCmdParams = self.config.diffCmd()
		self.editDiffCmd.set_text( diffCmd )
		self.editDiffCmdParams.set_text( diffCmdParams )

		#setup backup folders
		self.listSnapshots = self.glade.get_widget( 'listSnapshots' )
		initAll = self.listSnapshots.get_model() is None

		if initAll:
			textRenderer = gtk.CellRendererText()
			column = gtk.TreeViewColumn( _('Snapshots') )
			column.pack_end( textRenderer, True )
			column.add_attribute( textRenderer, 'markup', 0 )
			self.listSnapshots.append_column( column )

			self.storeSnapshots = gtk.ListStore( str, str, str )
			self.listSnapshots.set_model( self.storeSnapshots )
		else:
			self.storeSnapshots = self.listSnapshots.get_model()

		#setup diff with combo
		self.comboDiffWith = self.glade.get_widget( 'comboDiffWith' )
		if initAll:
			textRenderer = gtk.CellRendererText()
			self.comboDiffWith.pack_start( textRenderer, True )
			self.comboDiffWith.add_attribute( textRenderer, 'text', 0 )
			self.comboDiffWith.set_model( self.storeSnapshots ) #use the same store

		#update snapshots
		self.update_snapshots()

	def updateToolbar( self ):
		if len( self.storeSnapshots ) <= 0:
			self.glade.get_widget( 'btnCopySnapshot' ).set_sensitive( False )
			self.glade.get_widget( 'btnRestoreSnapshot' ).set_sensitive( False )
		else:
			self.glade.get_widget( 'btnCopySnapshot' ).set_sensitive( True )

			iter = self.listSnapshots.get_selection().get_selected()[1]
			if iter is None:
				self.glade.get_widget( 'btnRestoreSnapshot' ).set_sensitive( False )
			else:
				path = self.storeSnapshots.get_value( iter, 1 )
				self.glade.get_widget( 'btnRestoreSnapshot' ).set_sensitive( len( path ) > 1 )

	def on_btnRestoreSnapshot_clicked( self, button ):
		iter = self.listSnapshots.get_selection().get_selected()[1]
		if not iter is None:
			self.glade.get_widget('btnRestoreSnapshot').set_sensitive( False )
			gobject.timeout_add( 100, self.restore_ )

	def restore_( self ):
		iter = self.listSnapshots.get_selection().get_selected()[1]
		if not iter is None:
			self.backup.restore( self.storeSnapshots.get_value( iter, 1 ), self.path )

		self.glade.get_widget( 'btnRestoreSnapshot' ).set_sensitive( True )
		return False

	def on_btnCopySnapshot_clicked( self, button ):
		iter = self.listSnapshots.get_selection().get_selected()[1]
		if not iter is None:
			path = self.storeSnapshots.get_value( iter, 2 )
			gnomeclipboardtools.clipboard_copy_path( path )
 
	def on_listSnapshots_cursor_changed( self, list ):
		self.updateToolbar()

	def on_listSnapshots_button_press_event( self, list, event ):
		if event.button != 3:
			return

		if len( self.storeSnapshots ) <= 0:
			return

		path = self.listSnapshots.get_path_at_pos( int( event.x ), int( event.y ) )
		if path is None:
			return
		path = path[0]
	
		self.listSnapshots.get_selection().select_path( path )
		self.updateToolbar()
		self.showPopupMenu( self.listSnapshots, event.button, event.time )

	def on_listSnapshots_popup_menu( self, list ):
		self.showPopupMenu( list, 1, gtk.get_current_event_time() )

	def showPopupMenu( self, list, button, time ):
		iter = list.get_selection().get_selected()[1]
		if iter is None:
			return

		#print "popup-menu"
		self.popupMenu = gtk.Menu()

		menuItem = gtk.ImageMenuItem( 'backintime.open' )
		menuItem.set_image( gtk.image_new_from_icon_name( self.icon_name, gtk.ICON_SIZE_MENU ) )
		menuItem.connect( 'activate', self.on_listSnapshots_open_item )
		self.popupMenu.append( menuItem )

		self.popupMenu.append( gtk.SeparatorMenuItem() )

		menuItem = gtk.ImageMenuItem( 'backintime.copy' )
		menuItem.set_image( gtk.image_new_from_stock( gtk.STOCK_COPY, gtk.ICON_SIZE_MENU ) )
		menuItem.connect( 'activate', self.on_listSnapshots_copy_item )
		self.popupMenu.append( menuItem )

		menuItem = gtk.ImageMenuItem( gtk.STOCK_JUMP_TO )
		menuItem.connect( 'activate', self.on_listSnapshots_jumpto_item )
		self.popupMenu.append( menuItem )

		path = self.storeSnapshots.get_value( iter, 1 )
		if len( path ) > 1:
			menuItem = gtk.ImageMenuItem( 'backintime.restore' )
			menuItem.set_image( gtk.image_new_from_stock( gtk.STOCK_UNDELETE, gtk.ICON_SIZE_MENU ) )
			menuItem.connect( 'activate', self.on_listSnapshots_restore_item )
			self.popupMenu.append( menuItem )

		self.popupMenu.append( gtk.SeparatorMenuItem() )

		menuItem = gtk.ImageMenuItem( 'backintime.diff' )
		#menuItem.set_image( gtk.image_new_from_stock( gtk.STOCK_COPY, gtk.ICON_SIZE_MENU ) )
		menuItem.connect( 'activate', self.on_listSnapshots_diff_item )
		self.popupMenu.append( menuItem )

		self.popupMenu.show_all()
		self.popupMenu.popup( None, None, None, button, time )

	def on_listSnapshots_diff_item( self, widget, data = None ):
		self.on_btnDiffWith_clicked( self.glade.get_widget( 'btnDiffWith' ) )

	def on_listSnapshots_jumpto_item( self, widget, data = None ):
		self.dialog.response( gtk.RESPONSE_OK )

	def on_listSnapshots_open_item( self, widget, data = None ):
		self.open_item()

	def on_listSnapshots_restore_item( self, widget, data = None ):
		self.on_btnRestoreSnapshot_clicked( self.glade.get_widget( 'btnRestoreSnapshot' ) )

	def on_listSnapshots_copy_item( self, widget, data = None ):
		self.on_btnCopySnapshot_clicked( self.glade.get_widget( 'btnCopySnapshot' ) )

	def getCmdOutput( self, cmd ):
		retVal = ''

		try:
			pipe = os.popen( cmd )
			retVal = pipe.read().strip()
			pipe.close() 
		except:
			return ''

		return retVal

	def checkCmd( self, cmd ):
		cmd = cmd.strip()

		if len( cmd ) < 1:
			return False

		if os.path.isfile( cmd ):
			return True

		cmd = self.getCmdOutput( "which \"%s\"" % cmd )

		if len( cmd ) < 1:
			return False

		if os.path.isfile( cmd ):
			return True

		return False

	def on_btnDiffWith_clicked( self, button ):
		if len( self.storeSnapshots ) < 1:
			return

		#get path from the list
		iter = self.listSnapshots.get_selection().get_selected()[1]
		if iter is None:
			return
		path1 = self.storeSnapshots.get_value( iter, 2 )

		#get path from the combo
		path2 = self.storeSnapshots.get_value( self.comboDiffWith.get_active_iter(), 2 )

		#check if the 2 paths are different
		if path1 == path2:
			messagebox.show_error( self.dialog, self.config, _("You can't compare a snapshot to itself") )
			return

		diffCmd = self.editDiffCmd.get_text()
		diffCmdParams = self.editDiffCmdParams.get_text()

		if not self.checkCmd( diffCmd ):
			messagebox.show_error( self.dialog, self.config, _("Command not found: %s") % diffCmd )
			return

		params = diffCmdParams
		params = params.replace( '%1', "\"%s\"" % path1 )
		params = params.replace( '%2', "\"%s\"" % path2 )

		cmd = diffCmd + ' ' + params + ' &'
		os.system( cmd  )

		#check if the command changed
		oldDiffCmd, oldDiffCmdParams = self.config.diffCmd()
		if diffCmd != oldDiffCmd or diffCmdParams != oldDiffCmdParams:
			self.config.setDiffCmd( diffCmd, diffCmdParams )
			self.config.save()

	def update_snapshots( self ):
		self.editPath.set_text( self.path )

		#fill snapshots
		self.storeSnapshots.clear()
	
		path = os.path.join( self.current_snapshot, self.path[ 1 : ] )	
		isdir = os.path.isdir( path )

		counter = 0
		indexComboDiffWith = 0
		
		#add now
		path = self.path
		if os.path.exists( path ):
			if os.path.isdir( path ) == isdir:
				self.storeSnapshots.append( [ self.config.snapshotDisplayName( '/' ), '/', path ] )
				if '/' == self.current_snapshot:
					indexComboDiffWith = counter
				counter += 1
				
		#add snapshots
		for snapshot in self.snapshots:
			snapshot_path = self.config.snapshotPath( snapshot )
			path = self.config.snapshotPathTo( snapshot, self.path )
			if os.path.exists( path ):
				if os.path.isdir( path ) == isdir:
					self.storeSnapshots.append( [ self.config.snapshotDisplayName( snapshot ), snapshot_path, path ] )
					if snapshot_path == self.current_snapshot:
						indexComboDiffWith = counter
					counter += 1

		#select first item
		if len( self.storeSnapshots ) > 0:
			iter = self.storeSnapshots.get_iter_first()
			if not iter is None:
				self.listSnapshots.get_selection().select_iter( iter )
			self.comboDiffWith.set_active( indexComboDiffWith )
	
			self.glade.get_widget( 'btnDiffWith' ).set_sensitive( True )
			self.comboDiffWith.set_sensitive( True )
		else:
			self.glade.get_widget( 'btnDiffWith' ).set_sensitive( False )
			self.comboDiffWith.set_sensitive( False )

		self.updateToolbar()

	def on_listSnapshots_row_activated( self, list, path, column ):
		self.open_item()

	def open_item( self ):
		iter = self.listSnapshots.get_selection().get_selected()[1]
		if iter is None:
			return
		path = self.storeSnapshots.get_value( iter, 2 )
		cmd = "gnome-open \"%s\" &" % path
		os.system( cmd )

	def run( self ):
		returnValue = None
		while True:
			retVal = self.dialog.run()
			
			if gtk.RESPONSE_OK == retVal: #go to
				iter = self.listSnapshots.get_selection().get_selected()[1]
				if not iter is None:
					snapshot_path = self.storeSnapshots.get_value( iter, 1 )
					returnValue = snapshot_path
				break
			else:
				#cancel, close ...
				break

		self.dialog.hide()
		return returnValue

