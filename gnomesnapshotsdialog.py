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
import gnomevfs
import gobject
import gtk.glade
import datetime
import gettext

import config
import gnomeclipboardtools 
import gnomemessagebox


_=gettext.gettext


class SnapshotsDialog:
	def __init__( self, snapshots, glade ):
		self.snapshots = snapshots
		self.config = snapshots.config
		self.glade = glade

		self.path = None
		self.icon_name = None

		self.dialog = self.glade.get_widget( 'SnapshotsDialog' )

		signals = { 
			'on_list_snapshots_cursor_changed' : self.on_list_snapshots_cursor_changed,
			'on_list_snapshots_row_activated' : self.on_list_snapshots_row_activated,
			'on_list_snapshots_popup_menu' : self.on_list_snapshots_popup_menu,
			'on_list_snapshots_button_press_event': self.on_list_snapshots_button_press_event,
			'on_list_snapshots_drag_data_get': self.on_list_snapshots_drag_data_get,
			'on_btn_diff_with_clicked' : self.on_btn_diff_with_clicked,
			'on_btn_copy_snapshot_clicked' : self.on_btn_copy_snapshot_clicked,
			'on_btn_restore_snapshot_clicked' : self.on_btn_restore_snapshot_clicked
			}

		#path
		self.edit_path = self.glade.get_widget( 'edit_path' )

		#diff
		self.edit_diff_cmd = self.glade.get_widget( 'edit_diff_cmd' )
		self.edit_diff_cmd_params = self.glade.get_widget( 'edit_diff_cmd_params' )

		diff_cmd = self.config.get_str_value( 'gnome.diff.cmd', 'meld' )
		diff_cmd_params = self.config.get_str_value( 'gnome.diff.params', '%1 %2' )

		self.edit_diff_cmd.set_text( diff_cmd )
		self.edit_diff_cmd_params.set_text( diff_cmd_params )

		#setup backup folders
		self.list_snapshots = self.glade.get_widget( 'list_snapshots' )
		self.list_snapshots.drag_source_set( gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK, gtk.target_list_add_uri_targets(), gtk.gdk.ACTION_COPY )

		self.glade.signal_autoconnect( signals )
		
		text_renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn( _('Snapshots') )
		column.pack_end( text_renderer, True )
		column.add_attribute( text_renderer, 'markup', 0 )
		column.set_sort_column_id( 0 )
		self.list_snapshots.append_column( column )

		#display name, snapshot_id
		self.store_snapshots = gtk.ListStore( str, str )
		self.list_snapshots.set_model( self.store_snapshots )

		self.store_snapshots.set_sort_column_id( 0, gtk.SORT_DESCENDING )

		#setup diff with combo
		self.combo_diff_with = self.glade.get_widget( 'combo_diff_with' )
		text_renderer = gtk.CellRendererText()
		self.combo_diff_with.pack_start( text_renderer, True )
		self.combo_diff_with.add_attribute( text_renderer, 'text', 0 )
		self.combo_diff_with.set_model( self.store_snapshots ) #use the same store

	def update_toolbar( self ):
		if len( self.store_snapshots ) <= 0:
			self.glade.get_widget( 'btn_copy_snapshot' ).set_sensitive( False )
			self.glade.get_widget( 'btn_restore_snapshot' ).set_sensitive( False )
		else:
			self.glade.get_widget( 'btn_copy_snapshot' ).set_sensitive( True )

			iter = self.list_snapshots.get_selection().get_selected()[1]
			if iter is None:
				self.glade.get_widget( 'btn_restore_snapshot' ).set_sensitive( False )
			else:
				path = self.store_snapshots.get_value( iter, 1 )
				self.glade.get_widget( 'btn_restore_snapshot' ).set_sensitive( len( path ) > 1 )

	def on_btn_restore_snapshot_clicked( self, button ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if not iter is None:
			self.glade.get_widget('btn_restore_snapshot').set_sensitive( False )
			gobject.timeout_add( 100, self.restore_ )

	def restore_( self ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if not iter is None:
			self.snapshots.restore( self.store_snapshots.get_value( iter, 1 ), self.path )

		self.glade.get_widget( 'btn_restore_snapshot' ).set_sensitive( True )
		return False

	def on_btn_copy_snapshot_clicked( self, button ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if not iter is None:
			path = self.snapshots.get_snapshot_path_to( self.store_snapshots.get_value( iter, 1 ), self.path )
			gnomeclipboardtools.clipboard_copy_path( path )
 
	def on_list_snapshots_drag_data_get( self, widget, drag_context, selection_data, info, timestamp, user_param1 = None ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if not iter is None:
			path = self.store_snapshots.get_value( iter, 2 )
			path = gnomevfs.escape_path_string(path)
			selection_data.set_uris( [ 'file://' + path ] )

	def on_list_snapshots_cursor_changed( self, list ):
		self.update_toolbar()

	def on_list_snapshots_button_press_event( self, list, event ):
		if event.button != 3:
			return

		if len( self.store_snapshots ) <= 0:
			return

		path = self.list_snapshots.get_path_at_pos( int( event.x ), int( event.y ) )
		if path is None:
			return
		path = path[0]
	
		self.list_snapshots.get_selection().select_path( path )
		self.update_toolbar()
		self.show_popup_menu( self.list_snapshots, event.button, event.time )

	def on_list_snapshots_popup_menu( self, list ):
		self.showPopupMenu( list, 1, gtk.get_current_event_time() )

	def show_popup_menu( self, list, button, time ):
		iter = list.get_selection().get_selected()[1]
		if iter is None:
			return

		#print "popup-menu"
		self.popup_menu = gtk.Menu()

		menu_item = gtk.ImageMenuItem( 'backintime.open' )
		menu_item.set_image( gtk.image_new_from_icon_name( self.icon_name, gtk.ICON_SIZE_MENU ) )
		menu_item.connect( 'activate', self.on_list_snapshots_open_item )
		self.popup_menu.append( menu_item )

		self.popup_menu.append( gtk.SeparatorMenuItem() )

		menu_item = gtk.ImageMenuItem( 'backintime.copy' )
		menu_item.set_image( gtk.image_new_from_stock( gtk.STOCK_COPY, gtk.ICON_SIZE_MENU ) )
		menu_item.connect( 'activate', self.on_list_snapshots_copy_item )
		self.popup_menu.append( menu_item )

		menu_item = gtk.ImageMenuItem( gtk.STOCK_JUMP_TO )
		menu_item.connect( 'activate', self.on_list_snapshots_jumpto_item )
		self.popup_menu.append( menu_item )

		path = self.store_snapshots.get_value( iter, 1 )
		if len( path ) > 1:
			menu_item = gtk.ImageMenuItem( 'backintime.restore' )
			menu_item.set_image( gtk.image_new_from_stock( gtk.STOCK_UNDELETE, gtk.ICON_SIZE_MENU ) )
			menu_item.connect( 'activate', self.on_list_snapshots_restore_item )
			self.popup_menu.append( menu_item )

		self.popup_menu.append( gtk.SeparatorMenuItem() )

		menu_item = gtk.ImageMenuItem( 'backintime.diff' )
		#menu_item.set_image( gtk.image_new_from_stock( gtk.STOCK_COPY, gtk.ICON_SIZE_MENU ) )
		menu_item.connect( 'activate', self.on_list_snapshots_diff_item )
		self.popup_menu.append( menu_item )

		self.popup_menu.show_all()
		self.popup_menu.popup( None, None, None, button, time )

	def on_list_snapshots_diff_item( self, widget, data = None ):
		self.on_btn_diff_with_clicked( self.glade.get_widget( 'btn_diff_with' ) )

	def on_list_snapshots_jumpto_item( self, widget, data = None ):
		self.dialog.response( gtk.RESPONSE_OK )

	def on_list_snapshots_open_item( self, widget, data = None ):
		self.open_item()

	def on_list_snapshots_restore_item( self, widget, data = None ):
		self.on_btn_restore_snapshot_clicked( self.glade.get_widget( 'btn_restore_snapshot' ) )

	def on_list_snapshots_copy_item( self, widget, data = None ):
		self.on_btn_copy_snapshot_clicked( self.glade.get_widget( 'btn_copy_snapshot' ) )

	def get_cmd_output( self, cmd ):
		output = ''

		try:
			pipe = os.popen( cmd )
			output = pipe.read().strip()
			pipe.close() 
		except:
			return ''

		return output

	def check_cmd( self, cmd ):
		cmd = cmd.strip()

		if len( cmd ) < 1:
			return False

		if os.path.isfile( cmd ):
			return True

		cmd = self.get_cmd_output( "which \"%s\"" % cmd )

		if len( cmd ) < 1:
			return False

		if os.path.isfile( cmd ):
			return True

		return False

	def on_btn_diff_with_clicked( self, button ):
		if len( self.store_snapshots ) < 1:
			return

		#get path from the list
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if iter is None:
			return
		path1 = self.snapshots.get_snapshot_path_to( self.store_snapshots.get_value( iter, 1 ), self.path )

		#get path from the combo
		path2 = self.snapshots.get_snapshot_path_to( self.store_snapshots.get_value( self.combo_diff_with.get_active_iter(), 1 ), self.path )

		#check if the 2 paths are different
		if path1 == path2:
			gnomemessagebox.show_error( self.dialog, self.config, _("You can't compare a snapshot to itself") )
			return

		diff_cmd = self.edit_diff_cmd.get_text()
		diff_cmd_params = self.edit_diff_cmd_params.get_text()

		if not self.check_cmd( diff_cmd ):
			gnomemessagebox.show_error( self.dialog, self.config, _("Command not found: %s") % diffCmd )
			return

		params = diff_cmd_params
		params = params.replace( '%1', "\"%s\"" % path1 )
		params = params.replace( '%2', "\"%s\"" % path2 )

		cmd = diff_cmd + ' ' + params + ' &'
		os.system( cmd  )

		#check if the command changed
		old_diff_cmd = self.config.get_str_value( 'gnome.diff.cmd', 'meld' )
		old_diff_cmd_params = self.config.get_str_value( 'gnome.diff.params', '%1 %2' )
		if diff_cmd != old_diff_cmd or diff_cmd_params != old_diff_cmd_params:
			self.config.get_str_value( 'gnome.diff.cmd', diff_cmd )
			self.config.get_str_value( 'gnome.diff.params', diff_cmd_params )
			self.config.save()

	def update_snapshots( self, current_snapshot_id, snapshots_list ):
		self.edit_path.set_text( self.path )

		#fill snapshots
		self.store_snapshots.clear()
	
		path = self.snapshots.get_snapshot_path_to( current_snapshot_id, self.path )	
		isdir = os.path.isdir( path )

		counter = 0
		index_combo_diff_with = 0
		
		#add now
		path = self.path
		if os.path.exists( path ):
			if os.path.isdir( path ) == isdir:
				self.store_snapshots.append( [ self.snapshots.get_snapshot_display_name_gtk( '/' ), '/' ] )
				if '/' == current_snapshot_id:
					indexComboDiffWith = counter
				counter += 1
				
		#add snapshots
		for snapshot in snapshots_list:
			path = self.snapshots.get_snapshot_path_to( snapshot, self.path )
			if os.path.exists( path ):
				if os.path.isdir( path ) == isdir:
					self.store_snapshots.append( [ self.snapshots.get_snapshot_display_name_gtk( snapshot ), snapshot ] )
					if snapshot == current_snapshot_id:
						index_combo_diff_with = counter
					counter += 1

		#select first item
		if len( self.store_snapshots ) > 0:
			iter = self.store_snapshots.get_iter_first()
			if not iter is None:
				self.list_snapshots.get_selection().select_iter( iter )
			self.combo_diff_with.set_active( index_combo_diff_with )
	
			self.glade.get_widget( 'btn_diff_with' ).set_sensitive( True )
			self.combo_diff_with.set_sensitive( True )
		else:
			self.glade.get_widget( 'btn_diff_with' ).set_sensitive( False )
			self.combo_diff_with.set_sensitive( False )

		self.list_snapshots.grab_focus()
		self.update_toolbar()

	def on_list_snapshots_row_activated( self, list, path, column ):
		self.open_item()

	def open_item( self ):
		iter = self.list_snapshots.get_selection().get_selected()[1]
		if iter is None:
			return
		path = self.snapshots.get_snapshot_path_to( self.store_snapshots.get_value( iter, 1 ), self.path )
		cmd = "gnome-open \"%s\" &" % path
		os.system( cmd )

	def run( self, path, snapshots_list, current_snapshot_id, icon_name ):
		self.path = path
		self.icon_name = icon_name
		self.update_snapshots( current_snapshot_id, snapshots_list )

		snapshot_id = None
		while True:
			ret_val = self.dialog.run()
			
			if gtk.RESPONSE_OK == ret_val: #go to
				iter = self.list_snapshots.get_selection().get_selected()[1]
				if not iter is None:
					snapshot_id = self.store_snapshots.get_value( iter, 1 )
				break
			else:
				#cancel, close ...
				break

		self.dialog.hide()
		return snapshot_id

