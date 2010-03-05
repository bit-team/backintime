#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
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
import copy
import pygtk
pygtk.require("2.0")
import gtk
import gobject
import datetime
import gettext

import config
import messagebox
import tools


_=gettext.gettext


class SettingsDialog(object):
	
	def __init__( self, config, snapshots, parent ):
		
		self.config = config
		self.parent = parent
		self.snapshots = snapshots
		
		builder = gtk.Builder()
		self.builder = builder
		
		glade_file = os.path.join(self.config.get_app_path(),
			'gnome', 'settingsdialog.glade')
		
		builder.add_from_file(glade_file)
		
		get = builder.get_object
		
		self.dialog = get('SettingsDialog')
		self.dialog.set_transient_for( parent.window )
		
		signals = { 
				'on_btn_add_profile_clicked' : self.on_add_profile,
				'on_btn_edit_profile_clicked' : self.on_edit_profile,
				'on_btn_remove_profile_clicked' : self.on_remove_profile,
				'on_btn_add_include_clicked' : self.on_add_include,
				'on_btn_remove_include_clicked' : self.on_remove_include,
				'on_btn_add_exclude_clicked' : self.on_add_exclude,
				'on_btn_add_exclude_file_clicked' : self.on_add_exclude_file,
				'on_btn_add_exclude_folder_clicked' : self.on_add_exclude_folder,
				'on_btn_remove_exclude_clicked' : self.on_remove_exclude,
				'on_cb_remove_old_backup_toggled' : self.update_remove_old_backups,
				'on_cb_min_free_space_toggled' : self.update_min_free_space,
				#'on_cb_per_directory_schedule_toggled' : self.on_cb_per_directory_schedule_toggled,
				'on_combo_profiles_changed': self.on_combo_profiles_changed,
				'on_btn_where_clicked': self.on_btn_where_clicked,
				'on_cb_backup_mode_changed': self.on_cb_backup_mode_changed,
			}
		
		builder.connect_signals(signals)
		
		#profiles
		self.btn_edit_profile = get( 'btn_edit_profile' )
		self.btn_add_profile = get( 'btn_add_profile' )
		self.btn_remove_profile = get( 'btn_remove_profile' )
		self.combo_profiles = get( 'combo_profiles' )
		
		self.disable_combo_changed = True
		
		self.store_profiles = gtk.ListStore( str, str )
		
		self.combo_profiles = get( 'combo_profiles' )
		
		text_renderer = gtk.CellRendererText()
		self.combo_profiles.pack_start( text_renderer, True )
		self.combo_profiles.add_attribute( text_renderer, 'text', 0 )
		
		self.combo_profiles.set_model( self.store_profiles )
		
		self.disable_combo_changed = False
		
		#set current folder
		#self.fcb_where = get( 'fcb_where' )
		#self.fcb_where.set_show_hidden( self.parent.show_hidden_files )
		self.edit_where = get( 'edit_where' )
		
		#automatic backup mode store
		self.store_backup_mode = gtk.ListStore( str, int )
		map = self.config.AUTOMATIC_BACKUP_MODES
		self.rev_automatic_backup_modes = {}
		keys = map.keys()
		keys.sort()
		for key in keys:
			self.rev_automatic_backup_modes[ map[key] ] = key
			self.store_backup_mode.append( [ map[key], key ] )

		#automatic backup time store
		self.store_backup_time = gtk.ListStore( str, int )
		for t in xrange( 0, 2400, 100 ):
			self.store_backup_time.append( [ datetime.time( t/100, t%100 ).strftime("%H:%M"), t ] )

		#per directory schedule
		#self.cb_per_directory_schedule = get( 'cb_per_directory_schedule' )
		#self.lbl_schedule = get( 'lbl_schedule' )
		
		#setup include folders
		self.list_include = get( 'list_include' )
		
		pix_renderer = gtk.CellRendererPixbuf()
		text_renderer = gtk.CellRendererText()
		
		column = gtk.TreeViewColumn( _('Include folders') )
		column.pack_start( pix_renderer, False )
		column.pack_end( text_renderer, True )
		column.add_attribute( pix_renderer, 'stock-id', 1 )
		column.add_attribute( text_renderer, 'markup', 0 )
		self.list_include.append_column( column )
		
		#column = gtk.TreeViewColumn( _('Schedule') )
		#combo_renderer = gtk.CellRendererCombo()
		#combo_renderer.set_property( 'editable', True )
		#combo_renderer.set_property( 'has-entry', False )
		#combo_renderer.set_property( 'model', self.store_backup_mode )
		#combo_renderer.set_property( 'text-column', 0 )
		#combo_renderer.connect( 'edited', self.on_automatic_backup_mode_changed )
		#column.pack_end( combo_renderer, True )
		#column.add_attribute( combo_renderer, 'text', 2 )
		
		#self.include_schedule_column = column
		
		self.store_include = gtk.ListStore( str, str, int ) #, str, int )
		self.list_include.set_model( self.store_include )
		
		#setup exclude patterns
		self.list_exclude = get( 'list_exclude' )
		
		pix_renderer = gtk.CellRendererPixbuf()
		text_renderer = gtk.CellRendererText()
		
		column = gtk.TreeViewColumn( _('Patterns, files or folders') )
		column.pack_start( pix_renderer, False )
		column.pack_end( text_renderer, True )
		column.add_attribute( pix_renderer, 'stock-id', 1 )
		column.add_attribute( text_renderer, 'text', 0 )
		self.list_exclude.append_column( column )
		
		self.store_exclude = gtk.ListStore( str, str )
		self.list_exclude.set_model( self.store_exclude )
		
		#setup automatic backup mode
		self.cb_backup_mode = get( 'cb_backup_mode' )
		self.cb_backup_mode.set_model( self.store_backup_mode )
		
		self.cb_backup_mode.clear()
		renderer = gtk.CellRendererText()
		self.cb_backup_mode.pack_start( renderer, True )
		self.cb_backup_mode.add_attribute( renderer, 'text', 0 )
		
		#setup automatic backup time
		self.cb_backup_time = get( 'cb_backup_time' )
		self.cb_backup_time.set_model( self.store_backup_time )

		self.cb_backup_time.clear()
		renderer = gtk.CellRendererText()
		self.cb_backup_time.pack_start( renderer, True )
		self.cb_backup_time.add_attribute( renderer, 'text', 0 )
		
		self.hbox_backup_time = get( 'hbox_backup_time' )

		#setup remove old backups older than
		self.edit_remove_old_backup_value = get( 'edit_remove_old_backup_value' )
		self.cb_remove_old_backup_unit = get( 'cb_remove_old_backup_unit' )
		
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
		
		self.cb_remove_old_backup = get( 'cb_remove_old_backup' )
		
		#setup min free space
		self.edit_min_free_space_value = get( 'edit_min_free_space_value' )
		self.cb_min_free_space_unit = get( 'cb_min_free_space_unit' )
		
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
				
		self.cb_min_free_space = get( 'cb_min_free_space' )
		
		#don't remove named snapshots
		self.cb_dont_remove_named_snapshots = get( 'cb_dont_remove_named_snapshots' )
		self.cb_dont_remove_named_snapshots.set_active( self.config.get_dont_remove_named_snapshots() )
		
		#smart remove
		self.cb_smart_remove = get( 'cb_smart_remove' )
		
		#enable notifications
		self.cb_enable_notifications = get( 'cb_enable_notifications' )
		self.cb_backup_on_restore = get( 'cb_backup_on_restore' )

		#nice & ionice
		self.cb_run_nice_from_cron = get('cb_run_nice_from_cron')
		self.cb_run_ionice_from_cron = get('cb_run_ionice_from_cron')
		self.cb_run_ionice_from_user = get('cb_run_ionice_from_user')
		
		#don't run when on battery
		self.cb_no_on_battery = get( 'cb_no_on_battery' )
		if not tools.power_status_available ():
			self.cb_no_on_battery.set_sensitive( False )
			self.cb_no_on_battery.set_tooltip_text( 'Power status not available from system' )
		
		self.update_profiles()
	
	def error_handler( self, message ):
		messagebox.show_error( self.dialog, self.config, message )
	
	def question_handler( self, message ):
		return gtk.RESPONSE_YES == messagebox.show_question( self.dialog, self.config, message )
	
	#def on_automatic_backup_mode_changed( self, renderer, path, new_text ):
	#	iter = self.store_include.get_iter(path)
	#	self.store_include.set_value( iter, 2, new_text )
	#	self.store_include.set_value( iter, 3, self.rev_automatic_backup_modes[new_text] )
	
	def on_btn_where_clicked( self, button ):
		path = self.edit_where.get_text()
		
		fcd = gtk.FileChooserDialog( _('Snapshots folder'), self.dialog, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
		if len( path ) > 0:
			fcd.set_filename( path )
		
		if fcd.run() == gtk.RESPONSE_OK:
			new_path = tools.prepare_path( fcd.get_filename() )
			fcd.destroy()
			if len( path ) > 0 and new_path != path:
				if not self.question_handler( _('Are you sure you want to change snapshots folder ?') ):
					return
			self.edit_where.set_text( new_path )
		else:
			fcd.destroy()

	def on_cb_backup_mode_changed( self, *params ):
		iter = self.cb_backup_mode.get_active_iter()

		hide_time = True

		if not iter is None:
			backup_mode = self.store_backup_mode.get_value( iter, 1 )
			if backup_mode >= self.config.DAY:
				hide_time = False

		if hide_time:
			self.hbox_backup_time.hide()
		else:
			self.hbox_backup_time.show()

	def on_combo_profiles_changed( self, *params ):
		if self.disable_combo_changed:
			return
		
		iter = self.combo_profiles.get_active_iter()
		if iter is None:
			return
		
		profile_id = self.store_profiles.get_value( iter, 1 )
		if profile_id != self.config.get_current_profile():
			self.save_profile()
			self.config.set_current_profile( profile_id )
		
		self.update_profile()
	
	def update_profiles( self ):
		self.disable_combo_changed = True
		
		profiles = self.config.get_profiles_sorted_by_name()
		
		select_iter = None
		self.store_profiles.clear()

		for profile_id in profiles:
			iter = self.store_profiles.append( [ self.config.get_profile_name( profile_id ), profile_id ] )
			if profile_id == self.config.get_current_profile():
				select_iter = iter
		
		self.disable_combo_changed = False
		
		if not select_iter is None:
			self.combo_profiles.set_active_iter( select_iter )
	
	def update_profile( self ):
		if self.config.get_current_profile() == '1':
			self.btn_edit_profile.set_sensitive( False )
			self.btn_remove_profile.set_sensitive( False )
		else:
			self.btn_edit_profile.set_sensitive( True )
			self.btn_remove_profile.set_sensitive( True )
		
		#set current folder
		#self.fcb_where.set_filename( self.config.get_snapshots_path() )
		self.edit_where.set_text( self.config.get_snapshots_path() )
		
		#per directory schedule
		#self.cb_per_directory_schedule.set_active( self.config.get_per_directory_schedule() )
		
		#setup include folders
		#self.update_per_directory_option()
		
		self.store_include.clear()
		include_folders = self.config.get_include()
		if len( include_folders ) > 0:
			for include_folder in include_folders:
				if include_folder[1] == 0:
					self.store_include.append( [include_folder[0], gtk.STOCK_DIRECTORY, 0] ) #, self.config.AUTOMATIC_BACKUP_MODES[include_folder[1]], include_folder[1] ] )
				else:
					self.store_include.append( [include_folder[0], gtk.STOCK_FILE, include_folder[1]] ) #, self.config.AUTOMATIC_BACKUP_MODES[include_folder[1]], include_folder[1] ] )
		
		#setup exclude patterns
		self.store_exclude.clear()
		exclude_patterns = self.config.get_exclude()
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

		#setup automatic backup time
		i = 0
		iter = self.store_backup_time.get_iter_first()
		default_mode = self.config.get_automatic_backup_time()
		while not iter is None:
			if self.store_backup_time.get_value( iter, 1 ) == default_mode:
				self.cb_backup_time.set_active( i )
				break
			iter = self.store_backup_time.iter_next( iter )
			i = i + 1
		
		self.on_cb_backup_mode_changed()

		#setup remove old backups older than
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
		
		#backup on restore
		self.cb_backup_on_restore.set_active( self.config.is_backup_on_restore_enabled() )
		
		#run 'nice' from cron
		self.cb_run_nice_from_cron.set_active(self.config.is_run_nice_from_cron_enabled())

		#run 'ionice' from cron
		self.cb_run_ionice_from_cron.set_active(self.config.is_run_ionice_from_cron_enabled())
		
		#run 'ionice' from user
		self.cb_run_ionice_from_user.set_active(self.config.is_run_ionice_from_user_enabled())
		
		#don't run when on battery
		self.cb_no_on_battery.set_active( self.config.is_no_on_battery_enabled() )
	
	def save_profile( self ):
		profile_id = self.config.get_current_profile()
		#snapshots path
		snapshots_path = self.edit_where.get_text()
		
		#hack
		if snapshots_path.startswith( '//' ):
			snapshots_path = snapshots_path[ 1 : ]
		
		#include list 
		include_list = []
		iter = self.store_include.get_iter_first()
		while not iter is None:
			#include_list.append( ( self.store_include.get_value( iter, 0 ), self.store_include.get_value( iter, 3 ) ) )
			value = self.store_include.get_value( iter, 0 )
			type = self.store_include.get_value( iter, 2 )
			include_list.append( ( value, type ) )
			iter = self.store_include.iter_next( iter )
		
		#exclude patterns
		exclude_list = []
		iter = self.store_exclude.get_iter_first()
		while not iter is None:
			exclude_list.append( self.store_exclude.get_value( iter, 0 ) )
			iter = self.store_exclude.iter_next( iter )
		
		#check if back folder changed
		#if len( self.config.get_snapshots_path() ) > 0 and self.config.get_snapshots_path() != snapshots_path:
		#   if gtk.RESPONSE_YES != messagebox.show_question( self.dialog, self.config, _('Are you sure you want to change snapshots folder ?') ):
		#	   return False 
		
		#ok let's save to config
		self.config.set_snapshots_path( snapshots_path, profile_id )
		#if not msg is None:
		#   messagebox.show_error( self.dialog, self.config, msg )
		#   return False
		
		self.config.set_include( include_list )
		self.config.set_exclude( exclude_list )
		
		#global schedule
		self.config.set_automatic_backup_mode( self.store_backup_mode.get_value( self.cb_backup_mode.get_active_iter(), 1 ) )
		self.config.set_automatic_backup_time( self.store_backup_time.get_value( self.cb_backup_time.get_active_iter(), 1 ) )
		
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
		self.config.set_backup_on_restore( self.cb_backup_on_restore.get_active() )
		
		#expert options
		#self.config.set_per_directory_schedule( self.cb_per_directory_schedule.get_active() )
		self.config.set_run_nice_from_cron_enabled( self.cb_run_nice_from_cron.get_active() )
		self.config.set_run_ionice_from_cron_enabled( self.cb_run_ionice_from_cron.get_active() )
		self.config.set_run_ionice_from_user_enabled( self.cb_run_ionice_from_user.get_active() )
		self.config.set_no_on_battery_enabled( self.cb_no_on_battery.get_active() )
	
	def update_remove_old_backups( self, button ):
		enabled = self.cb_remove_old_backup.get_active()
		self.edit_remove_old_backup_value.set_sensitive( enabled )
		self.cb_remove_old_backup_unit.set_sensitive( enabled )
	
	def update_min_free_space( self, button ):
		enabled = self.cb_min_free_space.get_active()
		self.edit_min_free_space_value.set_sensitive( enabled )
		self.cb_min_free_space_unit.set_sensitive( enabled )
	
	#def on_cb_per_directory_schedule_toggled( self, button ):
	#	self.update_per_directory_option()
	
	#def update_per_directory_option( self ):
	#	if self.cb_per_directory_schedule.get_active():
	#		if self.list_include.get_column(1) == None:
	#			self.list_include.append_column( self.include_schedule_column )
	#		self.cb_backup_mode.hide()
	#		self.lbl_schedule.hide()
	#	else:
	#		if self.list_include.get_column(1) != None:
	#			self.list_include.remove_column( self.include_schedule_column )
	#		self.lbl_schedule.show()
	#		self.cb_backup_mode.show()
	
	def run( self ):
		self.config.set_question_handler( self.question_handler )
		self.config.set_error_handler( self.error_handler )
		
		self.config_copy_dict = copy.copy( self.config.dict )
		self.current_profile_org = self.config.get_current_profile()
		
		while True:
			if gtk.RESPONSE_OK == self.dialog.run():
				if not self.validate():
					continue
			else:
				self.config.dict = self.config_copy_dict
			
			break
		
		self.config.set_current_profile( self.current_profile_org )
		self.config.clear_handlers()
		
		self.dialog.destroy()
	   
	def update_snapshots_location( self ):
		'''Update snapshot location dialog'''
		self.config.set_question_handler( self.question_handler )
		self.config.set_error_handler( self.error_handler )
		self.snapshots.update_snapshots_location()

	def on_add_profile(self, button, data=None):
		
		name = messagebox.text_input_dialog( self.dialog, self.config, _('New profile'), None )
		if name is None:
			return
		if len( name ) <= 0:
			return
		
		if not self.config.add_profile( name ):
			return
		
		self.update_profiles()
	
	def on_edit_profile( self, button ):
		name = messagebox.text_input_dialog( self.dialog, self.config, _('Rename profile'), None )
		if name is None:
			return
		if len( name ) <= 0:
			return
		
		if not self.config.set_profile_name( name ):
			return
		
		self.update_profiles()
	
	def on_remove_profile( self, button ):
		if gtk.RESPONSE_YES == messagebox.show_question( self.dialog, self.config, _('Are you sure you want to delete the profile "%s" ?') % self.config.get_profile_name() ):
			self.config.remove_profile()
			self.update_profiles()
	
	def on_add_include( self, button ):
		fcd = gtk.FileChooserDialog( _('Include folder'), self.dialog, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
		fcd.set_show_hidden( self.parent.show_hidden_files  )
		
		if fcd.run() == gtk.RESPONSE_OK:
			include_folder = tools.prepare_path( fcd.get_filename() )
			
			iter = self.store_include.get_iter_first()
			while not iter is None:
				if self.store_include.get_value( iter, 0 ) == include_folder:
					break
				iter = self.store_include.iter_next( iter )
			
			if iter is None:
				#self.store_include.append( [include_folder, gtk.STOCK_DIRECTORY, self.config.AUTOMATIC_BACKUP_MODES[self.config.NONE], self.config.NONE ] )
				self.store_include.append( [ include_folder, gtk.STOCK_DIRECTORY, 0 ] )
		
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
		pattern = messagebox.text_input_dialog( self.dialog, self.config, _('Exclude pattern') )
		if pattern is None:
			return
		
		if pattern.find( ':' ) >= 0:
			messagebox.show_error( self.dialog, self.config, _('Exclude patterns can\'t contain \':\' char !') )
			return

		self.add_exclude_( pattern )
	
	def on_add_exclude_file( self, button ):
		fcd = gtk.FileChooserDialog( _('Exclude file'), self.dialog, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
		fcd.set_show_hidden( self.parent.show_hidden_files  )
		
		if fcd.run() == gtk.RESPONSE_OK:
			pattern = tools.prepare_path( fcd.get_filename() )
			self.add_exclude_( pattern )
		
		fcd.destroy()
	
	def on_add_exclude_folder( self, button ):
		fcd = gtk.FileChooserDialog( _('Exclude folder'), self.dialog, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
		fcd.set_show_hidden( self.parent.show_hidden_files  )
		
		if fcd.run() == gtk.RESPONSE_OK:
			pattern = tools.prepare_path( fcd.get_filename() )
			self.add_exclude_( pattern )
		
		fcd.destroy()
	
	def on_remove_exclude( self, button ):
		store, iter = self.list_exclude.get_selection().get_selected()
		if not iter is None:
			store.remove( iter )
	
	def on_cancel( self, button ):
		self.dialog.destroy()
	
	def validate( self ):
		self.save_profile()
		
		if not self.config.check_config():
			return False
		
		if not self.config.setup_cron():
			return False
		
		self.config.save()
		return True
	
