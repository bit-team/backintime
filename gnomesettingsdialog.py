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
				'on_btn_add_exclude_file_clicked' : self.on_add_exclude_file,
				'on_btn_add_exclude_folder_clicked' : self.on_add_exclude_folder,
				'on_btn_remove_exclude_clicked' : self.on_remove_exclude,
				'on_cb_remove_old_backup_toggled' : self.update_remove_old_backups,
				'on_cb_min_free_space_toggled' : self.update_min_free_space,
				'on_cb_per_directory_schedule_toggled' : self.on_cb_per_directory_schedule_toggled,
			}

		self.glade.signal_autoconnect( signals )

		#set current folder
		self.fcb_where = self.glade.get_widget( 'fcb_where' )
		
		#automatic backup mode store
		self.store_backup_mode = gtk.ListStore( str, int )
		default_automatic_backup_mode_index = 0
		map = self.config.AUTOMATIC_BACKUP_MODES
		self.rev_automatic_backup_modes = {}
		keys = map.keys()
		keys.sort()
		for key in keys:
			self.rev_automatic_backup_modes[ map[key] ] = key
			self.store_backup_mode.append( [ map[key], key ] )

		#per directory schedule
		self.cb_per_directory_schedule = self.glade.get_widget( 'cb_per_directory_schedule' )
		self.lbl_schedule = self.glade.get_widget( 'lbl_schedule' )

		#setup include folders
		self.list_include = self.glade.get_widget( 'list_include' )

		pix_renderer = gtk.CellRendererPixbuf()
		text_renderer = gtk.CellRendererText()

		column = gtk.TreeViewColumn( _('Include folders') )
		column.pack_start( pix_renderer, False )
		column.pack_end( text_renderer, True )
		column.add_attribute( pix_renderer, 'stock-id', 1 )
		column.add_attribute( text_renderer, 'markup', 0 )
		self.list_include.append_column( column )

		column = gtk.TreeViewColumn( _('Schedule') )
		combo_renderer = gtk.CellRendererCombo()
		combo_renderer.set_property( 'editable', True )
		combo_renderer.set_property( 'has-entry', False )
		combo_renderer.set_property( 'model', self.store_backup_mode )
		combo_renderer.set_property( 'text-column', 0 )
		combo_renderer.connect( 'edited', self.on_automatic_backup_mode_changed )
		column.pack_end( combo_renderer, True )
		column.add_attribute( combo_renderer, 'text', 2 )

		self.include_schedule_column = column

		self.store_include = gtk.ListStore( str, str, str, int )
		self.list_include.set_model( self.store_include )

		#setup exclude patterns
		self.list_exclude = self.glade.get_widget( 'list_exclude' )

		pix_renderer = gtk.CellRendererPixbuf()
		text_renderer = gtk.CellRendererText()

		column = gtk.TreeViewColumn( _('Patterns, files or directories') )
		column.pack_start( pix_renderer, False )
		column.pack_end( text_renderer, True )
		column.add_attribute( pix_renderer, 'stock-id', 1 )
		column.add_attribute( text_renderer, 'markup', 0 )
		self.list_exclude.append_column( column )

		self.store_exclude = gtk.ListStore( str, str )
		self.list_exclude.set_model( self.store_exclude )

		#setup automatic backup mode
		self.cb_backup_mode = self.glade.get_widget( 'cb_backup_mode' )
		self.cb_backup_mode.set_model( self.store_backup_mode )

		self.cb_backup_mode.clear()
		renderer = gtk.CellRendererText()
		self.cb_backup_mode.pack_start( renderer, True )
		self.cb_backup_mode.add_attribute( renderer, 'text', 0 )

		#setup remove old backups older then
		self.edit_remove_old_backup_value = self.glade.get_widget( 'edit_remove_old_backup_value' )
		self.cb_remove_old_backup_unit = self.glade.get_widget( 'cb_remove_old_backup_unit' )

		self.store_remove_old_backup_unit = gtk.ListStore( str, int )
		self.cb_remove_old_backup_unit.set_model( self.store_remove_old_backup_unit )

		renderer = gtk.CellRendererText()
		self.cb_remove_old_backup_unit.pack_start( renderer, True )
		self.cb_remove_old_backup_unit.add_attribute( renderer, 'text', 0 )

		self.store_remove_old_backup_unit.clear()
		map = self.config.REMOVE_OLD_BACKUP_UNITS
		keys = map.keys()
		keys.sort()
		for key in keys:
			self.store_remove_old_backup_unit.append( [ map[ key ], key ] )
				
		self.cb_remove_old_backup = self.glade.get_widget( 'cb_remove_old_backup' )

		#setup min free space
		self.edit_min_free_space_value = self.glade.get_widget( 'edit_min_free_space_value' )
		self.cb_min_free_space_unit = self.glade.get_widget( 'cb_min_free_space_unit' )

		self.store_min_free_space_unit = gtk.ListStore( str, int )
		self.cb_min_free_space_unit.set_model( self.store_min_free_space_unit )

		renderer = gtk.CellRendererText()
		self.cb_min_free_space_unit.pack_start( renderer, True )
		self.cb_min_free_space_unit.add_attribute( renderer, 'text', 0 )

		self.store_min_free_space_unit.clear()
		map = self.config.MIN_FREE_SPACE_UNITS
		keys = map.keys()
		keys.sort()
		for key in keys:
			self.store_min_free_space_unit.append( [ map[ key ], key ] )
				
		self.cb_min_free_space = self.glade.get_widget( 'cb_min_free_space' )

		#don't remove named snapshots
		self.cb_dont_remove_named_snapshots = self.glade.get_widget( 'cb_dont_remove_named_snapshots' )
		self.cb_dont_remove_named_snapshots.set_active( self.config.get_dont_remove_named_snapshots() )

		#smart remove
		self.cb_smart_remove = self.glade.get_widget( 'cb_smart_remove' )

		#enable notifications
		self.cb_enable_notifications = self.glade.get_widget( 'cb_enable_notifications' )

	def load_from_config( self ):
		#set current folder
		self.fcb_where.set_filename( self.config.get_snapshots_path() )
		
		#per directory schedule
		self.cb_per_directory_schedule.set_active( self.config.get_per_directory_schedule() )

		#setup include folders
		self.update_per_directory_option()

		self.store_include.clear()
		include_folders = self.config.get_include_folders()
		if len( include_folders ) > 0:
			for include_folder in include_folders:
				self.store_include.append( [include_folder[0], gtk.STOCK_DIRECTORY, self.config.AUTOMATIC_BACKUP_MODES[include_folder[1]], include_folder[1] ] )
		
		#setup exclude patterns
		self.store_exclude.clear()
		exclude_patterns = self.config.get_exclude_patterns()
		if len( exclude_patterns ) > 0:
			for exclude_pattern in exclude_patterns:
				self.store_exclude.append( [exclude_pattern, gtk.STOCK_DELETE] )

		#setup automatic backup mode
		i = 0
		iter = self.store_backup_mode.get_iter_first()
		default_mode = self.config.get_automatic_backup_mode()
		while not iter is None:
			if self.store_backup_mode.get_value( iter, 1 ) == default_mode:
				self.cb_backup_mode.set_active( i )
				break
			iter = self.store_backup_mode.iter_next( iter )
			i = i + 1

		#setup remove old backups older then
		enabled, value, unit = self.config.get_remove_old_snapshots()

		self.edit_remove_old_backup_value.set_value( float( value ) )

		i = 0
		iter = self.store_remove_old_backup_unit.get_iter_first()
		while not iter is None:
			if self.store_remove_old_backup_unit.get_value( iter, 1 ) == unit:
				self.cb_remove_old_backup_unit.set_active( i )
				break
			iter = self.store_remove_old_backup_unit.iter_next( iter )
			i = i + 1
				
		self.cb_remove_old_backup.set_active( enabled )
		self.update_remove_old_backups( self.cb_remove_old_backup )

		#setup min free space
		enabled, value, unit = self.config.get_min_free_space()
		
		self.edit_min_free_space_value.set_value( float(value) )

		i = 0
		iter = self.store_min_free_space_unit.get_iter_first()
		while not iter is None:
			if self.store_min_free_space_unit.get_value( iter, 1 ) == unit:
				self.cb_min_free_space_unit.set_active( i )
				break
			iter = self.store_min_free_space_unit.iter_next( iter )
			i = i + 1

		self.cb_min_free_space.set_active( enabled )
		self.update_min_free_space( self.cb_min_free_space )

		#don't remove named snapshots
		self.cb_dont_remove_named_snapshots.set_active( self.config.get_dont_remove_named_snapshots() )

		#smart remove
		self.cb_smart_remove.set_active( self.config.get_smart_remove() )

		#enable notifications
		self.cb_enable_notifications.set_active( self.config.is_notify_enabled() )

	def on_automatic_backup_mode_changed( self, renderer, path, new_text ):
		iter = self.store_include.get_iter(path)
		self.store_include.set_value( iter, 2, new_text )
		self.store_include.set_value( iter, 3, self.rev_automatic_backup_modes[new_text] )

	def update_remove_old_backups( self, button ):
		enabled = button.get_active()
		self.edit_remove_old_backup_value.set_sensitive( enabled )
		self.cb_remove_old_backup_unit.set_sensitive( enabled )

	def update_min_free_space( self, button ):
		enabled = button.get_active()
		self.edit_min_free_space_value.set_sensitive( enabled )
		self.cb_min_free_space_unit.set_sensitive( enabled )

	def on_cb_per_directory_schedule_toggled( self, button ):
		self.update_per_directory_option()

	def update_per_directory_option( self ):
		if self.cb_per_directory_schedule.get_active():
			if self.list_include.get_column(1) == None:
				self.list_include.append_column( self.include_schedule_column )
			self.cb_backup_mode.hide()
			self.lbl_schedule.hide()
		else:
			if self.list_include.get_column(1) != None:
				self.list_include.remove_column( self.include_schedule_column )
			self.lbl_schedule.show()
			self.cb_backup_mode.show()

	def run( self ):
		self.load_from_config()

		while True:
			if gtk.RESPONSE_OK == self.dialog.run():
				if not self.validate():
					continue
			break
		self.dialog.hide()

	def on_add_include( self, button ):
		fcd = gtk.FileChooserDialog( _('Include directory'), self.dialog, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )

		if fcd.run() == gtk.RESPONSE_OK:
			include_folder = fcd.get_filename()

			iter = self.store_include.get_iter_first()
			while not iter is None:
				if self.store_include.get_value( iter, 0 ) == include_folder:
					break
				iter = self.store_include.iter_next( iter )

			if iter is None:
				self.store_include.append( [include_folder, gtk.STOCK_DIRECTORY, self.config.AUTOMATIC_BACKUP_MODES[self.config.NONE], self.config.NONE ] )

		fcd.destroy()

	def on_remove_include( self, button ):
		store, iter = self.list_include.get_selection().get_selected()
		if not iter is None:
			store.remove( iter )

	def add_exclude_( self, pattern ):
		pattern = pattern.strip()
		if len( pattern ) == 0:
			return

		iter = self.store_exclude.get_iter_first()
		while not iter is None:
			if self.store_exclude.get_value( iter, 0 ) == pattern:
				return
			iter = self.store_exclude.iter_next( iter )

		self.store_exclude.append( [pattern, gtk.STOCK_DELETE] )

	def on_add_exclude( self, button ):
		pattern = gnomemessagebox.text_input_dialog( self.dialog, self.glade, _('Exclude pattern') )
		if pattern is None:
			return
	
		self.add_exclude_( pattern )

	def on_add_exclude_file( self, button ):
		fcd = gtk.FileChooserDialog( _('Exclude file'), self.dialog, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )

		if fcd.run() == gtk.RESPONSE_OK:
			pattern = fcd.get_filename()
			self.add_exclude_( pattern )

		fcd.destroy()

	def on_add_exclude_folder( self, button ):
		fcd = gtk.FileChooserDialog( _('Exclude directory'), self.dialog, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )

		if fcd.run() == gtk.RESPONSE_OK:
			pattern = fcd.get_filename()
			self.add_exclude_( pattern )

		fcd.destroy()

	def on_remove_exclude( self, button ):
		store, iter = self.list_exclude.get_selection().get_selected()
		if not iter is None:
			store.remove( iter )

	def on_cancel( self, button ):
		self.dialog.destroy()

	def validate( self ):
		#snapshots path
		snapshots_path = self.fcb_where.get_filename()

		#hack
		if snapshots_path.startswith( '//' ):
			snapshots_path = snapshots_path[ 1 : ]

		#include list 
		include_list = []
		iter = self.store_include.get_iter_first()
		while not iter is None:
			include_list.append( ( self.store_include.get_value( iter, 0 ), self.store_include.get_value( iter, 3 ) ) )
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
		msg = self.config.set_snapshots_path( snapshots_path )
		if not msg is None:
			gnomemessagebox.show_error( self.dialog, self.config, msg )
			return False

		self.config.set_include_folders( include_list )
		self.config.set_exclude_patterns( exclude_list )

		#global schedule
		self.config.set_automatic_backup_mode( self.store_backup_mode.get_value( self.cb_backup_mode.get_active_iter(), 1 ) )

		#auto-remove snapshots
		self.config.set_remove_old_snapshots( 
						self.cb_remove_old_backup.get_active(), 
						int( self.edit_remove_old_backup_value.get_value() ),
						self.store_remove_old_backup_unit.get_value( self.cb_remove_old_backup_unit.get_active_iter(), 1 ) )
		self.config.set_min_free_space( 
						self.cb_min_free_space.get_active(), 
						int( self.edit_min_free_space_value.get_value() ),
						self.store_min_free_space_unit.get_value( self.cb_min_free_space_unit.get_active_iter(), 1 ) )
		self.config.set_dont_remove_named_snapshots( self.cb_dont_remove_named_snapshots.get_active() )
		self.config.set_smart_remove( self.cb_smart_remove.get_active() )

		#options
		self.config.set_notify_enabled( self.cb_enable_notifications.get_active() )

		#expert options
		self.config.set_per_directory_schedule( self.cb_per_directory_schedule.get_active() )

		self.config.save()

		msg = self.config.setup_cron()
		if not msg is None:
			gnomemessagebox.show_error( self.dialog, self.config, msg )
			return False

		return True
	
