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
import gnomemessagebox


_=gettext.gettext


class SettingsDialog:
	def __init__( self, config, glade ):
		self.config = config
		self.glade = glade
		self.dialog = self.glade.get_widget( 'SettingsDialog' )

		signals = { 
				'on_btn_add_include_clicked' : self.on_add_include,
				'on_btn_remove_include_clicked' : self.on_remove_include,
				'on_btn_add_exclude_clicked' : self.on_add_exclude,
				'on_btn_remove_exclude_clicked' : self.on_remove_exclude,
				'on_cb_remove_old_backup_toggled' : self.update_remove_old_backups,
				'on_cb_min_free_space_toggled' : self.update_min_free_space,
			}

		self.glade.signal_autoconnect( signals )

		#set current folder
		self.fcb_where = self.glade.get_widget( 'fcb_where' )
		self.fcb_where.set_filename( self.config.get_snapshots_path() )
		
		#setup backup folders
		self.list_include = self.glade.get_widget( 'list_include' )
		self.list_include.get_model() is None

		pix_renderer = gtk.CellRendererPixbuf()
		text_renderer = gtk.CellRendererText()

		column = gtk.TreeViewColumn( _('Backup Directories') )
		column.pack_start( pix_renderer, False )
		column.pack_end( text_renderer, True )
		column.add_attribute( pix_renderer, 'stock-id', 1 )
		column.add_attribute( text_renderer, 'markup', 0 )
		self.list_include.append_column( column )

		self.store_include = gtk.ListStore( str, str )
		self.list_include.set_model( self.store_include )

		self.store_include.clear()
		include_folders = self.config.get_include_folders()
		if len( include_folders ) > 0:
			for include_folder in include_folders:
				self.store_include.append( [include_folder, gtk.STOCK_DIRECTORY] )
		
		self.fcb_include = self.glade.get_widget( 'fcb_include' )

		#setup exclude patterns
		self.list_exclude = self.glade.get_widget( 'list_exclude' )

		pix_renderer = gtk.CellRendererPixbuf()
		text_renderer = gtk.CellRendererText()

		column = gtk.TreeViewColumn( _('Exclude Patterns') )
		column.pack_start( pix_renderer, False )
		column.pack_end( text_renderer, True )
		column.add_attribute( pix_renderer, 'stock-id', 1 )
		column.add_attribute( text_renderer, 'markup', 0 )
		self.list_exclude.append_column( column )

		self.store_exclude = gtk.ListStore( str, str )
		self.list_exclude.set_model( self.store_exclude )

		self.store_exclude.clear()
		exclude_patterns = self.config.get_exclude_patterns()
		if len( exclude_patterns ) > 0:
			for exclude_pattern in exclude_patterns:
				self.store_exclude.append( [exclude_pattern, gtk.STOCK_DELETE] )

		self.edit_pattern = self.glade.get_widget( 'edit_pattern' )

		#setup automatic backup mode
		self.cb_backup_mode = self.glade.get_widget( 'cb_backup_mode' )

		self.store_backup_mode = gtk.ListStore( str, int )
		self.cb_backup_mode.set_model( self.store_backup_mode )
			
		self.cb_backup_mode.clear()
		renderer = gtk.CellRendererText()
		self.cb_backup_mode.pack_start( renderer, True )
		self.cb_backup_mode.add_attribute( renderer, 'text', 0 )

		self.store_backup_mode.clear()
		index = 0
		i = 0
		map = self.config.AUTOMATIC_BACKUP_MODES
		keys = map.keys()
		keys.sort()
		for key in keys:
			self.store_backup_mode.append( [ map[ key ], key ] )
			if key == self.config.get_automatic_backup_mode():
				index = i
			i = i + 1
				
		self.cb_backup_mode.set_active( index )

		#setup remove old backups older then
		enabled, value, unit = self.config.get_remove_old_snapshots()

		self.edit_remove_old_backup_value = self.glade.get_widget( 'edit_remove_old_backup_value' )
		self.edit_remove_old_backup_value.set_value( float( value ) )

		self.cb_remove_old_backup_unit = self.glade.get_widget( 'cb_remove_old_backup_unit' )

		self.store_remove_old_backup_unit = gtk.ListStore( str, int )
		self.cb_remove_old_backup_unit.set_model( self.store_remove_old_backup_unit )

		renderer = gtk.CellRendererText()
		self.cb_remove_old_backup_unit.pack_start( renderer, True )
		self.cb_remove_old_backup_unit.add_attribute( renderer, 'text', 0 )

		self.store_remove_old_backup_unit.clear()
		index = 0
		i = 0
		map = self.config.REMOVE_OLD_BACKUP_UNITS
		keys = map.keys()
		keys.sort()
		for key in keys:
			self.store_remove_old_backup_unit.append( [ map[ key ], key ] )
			if key == unit:
				index = i
			i = i + 1
				
		self.cb_remove_old_backup_unit.set_active( index )

		self.cb_remove_old_backup = self.glade.get_widget( 'cb_remove_old_backup' )
		self.cb_remove_old_backup.set_active( enabled )
		self.update_remove_old_backups( self.cb_remove_old_backup )

		#setup min free space
		enabled, value, unit = self.config.get_min_free_space()

		self.edit_min_free_space_value = self.glade.get_widget( 'edit_min_free_space_value' )
		self.edit_min_free_space_value.set_value( float(value) )

		self.cb_min_free_space_unit = self.glade.get_widget( 'cb_min_free_space_unit' )

		self.store_min_free_space_unit = gtk.ListStore( str, int )
		self.cb_min_free_space_unit.set_model( self.store_min_free_space_unit )

		renderer = gtk.CellRendererText()
		self.cb_min_free_space_unit.pack_start( renderer, True )
		self.cb_min_free_space_unit.add_attribute( renderer, 'text', 0 )

		self.store_min_free_space_unit.clear()
		index = 0
		i = 0
		map = self.config.MIN_FREE_SPACE_UNITS
		keys = map.keys()
		keys.sort()
		for key in keys:
			self.store_min_free_space_unit.append( [ map[ key ], key ] )
			if key == unit:
				index = i
			i = i + 1
				
		self.cb_min_free_space_unit.set_active( index )

		self.cb_min_free_space = self.glade.get_widget( 'cb_min_free_space' )
		self.cb_min_free_space.set_active( enabled )
		self.update_min_free_space( self.cb_min_free_space )

		#don't remove named snapshots
		self.cb_dont_remove_named_snapshots = self.glade.get_widget( 'cb_dont_remove_named_snapshots' )
		self.cb_dont_remove_named_snapshots.set_active( self.config.get_dont_remove_named_snapshots() )

	def update_remove_old_backups( self, button ):
		enabled = button.get_active()
		self.edit_remove_old_backup_value.set_sensitive( enabled )
		self.cb_remove_old_backup_unit.set_sensitive( enabled )

	def update_min_free_space( self, button ):
		enabled = button.get_active()
		self.edit_min_free_space_value.set_sensitive( enabled )
		self.cb_min_free_space_unit.set_sensitive( enabled )

	def run( self ):
		while True:
			if gtk.RESPONSE_OK == self.dialog.run():
				if not self.validate():
					continue
			break
		self.dialog.hide()

	def on_add_include( self, button ):
		include_folder = self.fcb_include.get_filename()

		iter = self.store_include.get_iter_first()
		while not iter is None:
			if self.store_include.get_value( iter, 0 ) == include_folder:
				return
			iter = self.store_include.iter_next( iter )

		self.store_include.append( [include_folder, gtk.STOCK_DIRECTORY] )

	def on_remove_include( self, button ):
		store, iter = self.list_include.get_selection().get_selected()
		if not iter is None:
			store.remove( iter )

	def on_add_exclude( self, button ):
		exclude_pattern = self.edit_pattern.get_text().strip()
		self.edit_pattern.set_text('')
		if len( exclude_pattern ) == 0:
			return

		iter = self.store_exclude.get_iter_first()
		while not iter is None:
			if self.store_exclude.get_value( iter, 0 ) == exclude_pattern:
				return
			iter = self.store_exclude.iter_next( iter )

		self.store_exclude.append( [exclude_pattern, gtk.STOCK_DELETE] )

	def on_remove_exclude( self, button ):
		store, iter = self.list_exclude.get_selection().get_selected()
		if not iter is None:
			store.remove( iter )

	def on_cancel( self, button ):
		self.dialog.destroy()

	def validate( self ):
		#snapshots path
		snapshots_path = self.fcb_where.get_filename()

		#include list 
		include_list = []
		iter = self.store_include.get_iter_first()
		while not iter is None:
			include_list.append( self.store_include.get_value( iter, 0 ) )
			iter = self.store_include.iter_next( iter )

		#exclude patterns
		exclude_list = []
		iter = self.store_exclude.get_iter_first()
		while not iter is None:
			exclude_list.append( self.store_exclude.get_value( iter, 0 ) )
			iter = self.store_exclude.iter_next( iter )

		#check params
		check_ret_val = self.config.check_take_snapshot_params( snapshots_path, include_list, exclude_list )
		if not check_ret_val is None:
			err_id, err_msg = check_ret_val
			gnomemessagebox.show_error( self.dialog, self.config, err_msg )
			return False

		#check if back folder changed
		if len( self.config.get_snapshots_path() ) > 0 and self.config.get_snapshots_path() != snapshots_path:
			if gtk.RESPONSE_YES != gnomemessagebox.show_question( self.dialog, self.config, _('Are you sure you want to change snapshots directory ?') ):
				return False 

		#ok let's save to config
		self.config.set_snapshots_path( snapshots_path )
		self.config.set_include_folders( include_list )
		self.config.set_exclude_patterns( exclude_list )

		#other settings
		self.config.set_automatic_backup_mode( self.store_backup_mode.get_value( self.cb_backup_mode.get_active_iter(), 1 ) )
		self.config.set_remove_old_snapshots( 
						self.cb_remove_old_backup.get_active(), 
						int( self.edit_remove_old_backup_value.get_value() ),
						self.store_remove_old_backup_unit.get_value( self.cb_remove_old_backup_unit.get_active_iter(), 1 ) )
		self.config.set_min_free_space( 
						self.cb_min_free_space.get_active(), 
						int( self.edit_min_free_space_value.get_value() ),
						self.store_min_free_space_unit.get_value( self.cb_min_free_space_unit.get_active_iter(), 1 ) )
		self.config.set_dont_remove_named_snapshots( self.cb_dont_remove_named_snapshots.get_active() )

		self.config.save()
		return True
	
