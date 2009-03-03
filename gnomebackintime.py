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
import stat
import sys

if len( os.getenv( 'DISPLAY', '' ) ) == 0:
	os.putenv( 'DISPLAY', ':0.0' )

import pygtk
pygtk.require("2.0")
import gtk
import threading
import gobject
import gtk.glade
import gnome
import gnomevfs
import datetime
import gettext
import time

import backintime
import config
import logger
import snapshots
import guiapplicationinstance
import tools

import gnomesettingsdialog
import gnomesnapshotsdialog
import gnomesnapshotnamedialog
import gnomemessagebox
import gnomefileicons
import gnomeclipboardtools
import gnomesnapshotstools


_=gettext.gettext


class AboutDialog:
	def __init__( self, config, glade ):
		self.glade = glade 
		self.dialog = self.glade.get_widget( 'AboutDialog' )
		self.dialog.set_name( config.APP_NAME )
		self.dialog.set_version( config.VERSION )
		self.dialog.set_copyright( 'Copyright (C) 2008-2009 Oprea Dan' )
		self.dialog.set_website( 'http://www.le-web.org/back-in-time/' )
		self.dialog.set_website_label( 'http://www.le-web.org/back-in-time/' )
		self.dialog.set_license( config.get_license() )
		authors = config.get_authors()
		if not authors is None:
			self.dialog.set_authors( authors.split('\n') )
		self.dialog.set_translator_credits( config.get_translations() )

		signals = { 
				'on_AboutDialog_response' : self.close,
			}

		self.glade.signal_autoconnect( signals )

	def close( self, button, response ):
		self.dialog.hide()

	def run( self ):
		return self.dialog.run()


class MainWindow:
	def __init__( self, config, app_instance ):
		self.config = config
		self.app_instance = app_instance
		self.snapshots = snapshots.Snapshots( config )
		self.special_background_color = 'lightblue'
		self.popup_menu = None

		self.folder_path = None
		self.snapshot_id = ''

		self.about_dialog = None
		self.settings_dialog = None
		self.snapshots_dialog = None
		self.snapshot_name_dialog = None

		self.glade = gtk.glade.XML( os.path.join( self.config.get_app_path(), 'gnomebackintime.glade' ), None, 'backintime' )

		signals = { 
				'on_MainWindow_destroy' : gtk.main_quit,
				'on_MainWindow_delete_event' : self.on_close,
				'on_MainWindow_key_release_event': self.on_key_release_event,
				'on_btn_exit_clicked' : self.on_close,
				'on_btn_help_clicked' : self.on_btn_help_clicked,
				'on_btn_about_clicked' : self.on_btn_about_clicked,
				'on_btn_settings_clicked' : self.on_btn_settings_clicked,
				'on_btn_backup_clicked' : self.on_btn_backup_clicked,
				'on_btn_update_snapshots_clicked' : self.on_btn_update_snapshots_clicked,
				'on_btn_snapshot_name_clicked' : self.on_btn_snapshot_name_clicked,
				'on_btn_remove_snapshot_clicked' : self.on_btn_remove_snapshot_clicked,
				'on_btn_restore_clicked' : self.on_btn_restore_clicked,
				'on_btn_copy_clicked' : self.on_btn_copy_clicked,
				'on_btn_snapshots_clicked' : self.on_btn_snapshots_clicked,
				'on_btn_hidden_files_toggled' : self.on_btn_hidden_files_toggled,
				'on_list_places_cursor_changed' : self.on_list_places_cursor_changed,
				'on_list_time_line_cursor_changed' : self.on_list_time_line_cursor_changed,
				'on_btn_folder_up_clicked' : self.on_btn_fodler_up_clicked,
				'on_list_folder_view_row_activated' : self.on_list_folder_view_row_activated,
				'on_list_folder_view_popup_menu' : self.on_list_folder_view_popup_menu,
				'on_list_folder_view_button_press_event': self.on_list_folder_view_button_press_event,
				'on_list_folder_view_drag_data_get': self.on_list_folder_view_drag_data_get
			}

		self.glade.signal_autoconnect( signals )

		self.window = self.glade.get_widget( 'MainWindow' )
		self.window.set_title( self.config.APP_NAME )

		#icons
		self.icon_names = gnomefileicons.GnomeFileIcons()

		#fix a glade bug
		self.glade.get_widget( 'btn_current_path' ).set_expand( True )

		#status bar
		self.status_bar = self.glade.get_widget( 'status_bar' )
		self.status_bar.push( 0, _('Done') )

		#show hidden files
		self.show_hidden_files = self.config.get_bool_value( 'gnome.show_hidden_files', False )
		self.btn_hidden_files = self.glade.get_widget( 'btn_hidden_files' )
		self.btn_hidden_files.set_active( self.show_hidden_files )

		#setup places view
		self.list_places = self.glade.get_widget( 'list_places' )

		pix_renderer = gtk.CellRendererPixbuf()
		text_renderer = gtk.CellRendererText()
		
		column = gtk.TreeViewColumn( _('Places') )
		column.pack_start( pix_renderer, False )
		column.pack_end( text_renderer, True )
		column.add_attribute( pix_renderer, 'icon-name', 2 )
		column.add_attribute( text_renderer, 'markup', 0 )
		column.set_cell_data_func( pix_renderer, self.places_pix_renderer_function, None )
		column.set_cell_data_func( text_renderer, self.places_text_renderer_function, None )
		#column.set_alignment( 0.5 )
		self.list_places.append_column( column )

		#name, icon, path
		self.store_places = gtk.ListStore( str, str, str )
		self.list_places.set_model( self.store_places )
		self.list_places.get_selection().set_select_function( self.places_select_function, self.store_places )

		#setup folder view
		self.list_folder_view = self.glade.get_widget( 'list_folder_view' )

		pix_renderer = gtk.CellRendererPixbuf()
		text_renderer = gtk.CellRendererText()

		column = gtk.TreeViewColumn( _('Name') )
		column.pack_start( pix_renderer, False )
		column.pack_end( text_renderer, True )
		column.add_attribute( pix_renderer, 'icon-name', 2 )
		column.add_attribute( text_renderer, 'markup', 0 )
		column.set_expand( True )
		column.set_sizing( gtk.TREE_VIEW_COLUMN_AUTOSIZE )
		column.set_sort_column_id( 0 )
		self.list_folder_view.append_column( column )

		text_renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn( _('Size') )
		column.pack_end( text_renderer, True )
		column.add_attribute( text_renderer, 'markup', 4 )
		column.set_sort_column_id( 1 )
		self.list_folder_view.append_column( column )

		text_renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn( _('Date') )
		column.pack_end( text_renderer, True )
		column.add_attribute( text_renderer, 'markup', 5 )
		column.set_sort_column_id( 2 )
		self.list_folder_view.append_column( column )

		# display name, relative path, icon_name, type (0 - directory, 1 - file), size (str), date, size (int)
		self.store_folder_view = gtk.ListStore( str, str, str, int, str, str, int )
		self.store_folder_view.set_sort_func( 0, self.sort_folder_view_by_column, 0 ) #name
		self.store_folder_view.set_sort_func( 1, self.sort_folder_view_by_column, 6 ) #size
		self.store_folder_view.set_sort_func( 2, self.sort_folder_view_by_column, 5 )	#date
		self.store_folder_view.set_sort_column_id( 0, gtk.SORT_ASCENDING )

		self.list_folder_view.set_model( self.store_folder_view )

		#setup time line view
		self.list_time_line = self.glade.get_widget( 'list_time_line' )

		text_renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn( _('Timeline'), text_renderer, markup = 0 )
		column.set_cell_data_func( text_renderer, self.places_text_renderer_function, None )
		self.list_time_line.append_column( column )

		#display name, id
		self.store_time_line = gtk.ListStore( str, str )
		self.list_time_line.set_model( self.store_time_line )
		self.list_time_line.get_selection().set_select_function( self.places_select_function, self.store_time_line )
		self.update_time_line = False

		#calculate specialBackgroundColor
		style = self.list_time_line.get_style()
		bg1 = style.bg[gtk.STATE_NORMAL]
		bg2 = style.bg[gtk.STATE_SELECTED]
		self.special_background_color = gtk.gdk.Color( (2 * bg1.red + bg2.red) / 3, (2 * bg1.green + bg2.green) / 3,(2 * bg1.blue + bg2.blue) / 3 ).to_string()

		#restore size & position
		main_window_x = self.config.get_int_value( 'gnome.main_window.x', -1 )
		main_window_y = self.config.get_int_value( 'gnome.main_window.y', -1 )
		if main_window_x >= 0 and main_window_y >= 0:
			self.window.move( main_window_x, main_window_y )

		main_window_width = self.config.get_int_value( 'gnome.main_window.width', -1 )
		main_window_height = self.config.get_int_value( 'gnome.main_window.height', -1 )
		if main_window_width > 0 and main_window_height > 0:
			self.window.resize( main_window_width, main_window_height )

		main_window_hpaned1 = self.config.get_int_value( 'gnome.main_window.hpaned1', -1 )
		main_window_hpaned2 = self.config.get_int_value( 'gnome.main_window.hpaned2', -1 )
		if main_window_hpaned1 > 0 and main_window_hpaned2 > 0:
			self.glade.get_widget('hpaned1').set_position( main_window_hpaned1 )
			self.glade.get_widget('hpaned2').set_position( main_window_hpaned2 )

		#prepare popup menu ids
		gtk.stock_add( 
				[ ('backintime.open', _('Open'), 0, 0, 'backintime' ),
				  ('backintime.copy', _('Copy'), 0, 0, 'backintime' ),
				  ('backintime.snapshots', _('Snapshots'), 0, 0, 'backintime' ),
				  ('backintime.diff', _('Diff'), 0, 0, 'backintime' ),
				  ('backintime.restore', _('Restore'), 0, 0, 'backintime' ) ] )

		#show main window
		self.window.show()

		gobject.timeout_add( 100, self.on_init )
		gobject.timeout_add( 1000, self.raise_application )

	def sort_folder_view_by_column( self, treemodel, iter1, iter2, column ):
		if 0 == column:
			ascending = 1
			if self.store_folder_view.get_sort_column_id()[1] != gtk.SORT_ASCENDING:
				ascending = -1

			type1 = self.store_folder_view.get_value( iter1, 3 )
			type2 = self.store_folder_view.get_value( iter2, 3 )

			if type1 == 0 and type2 != 0:
				return -1 * ascending

			if type1 != 0 and type2 == 0:
				return 1 * ascending

		data1 = self.store_folder_view.get_value( iter1, column )
		data2 = self.store_folder_view.get_value( iter2, column )

		if type(data1) is str:
			data1 = data1.upper()

		if type(data2) is str:
			data2 = data2.upper()

		#print "sort_folder_view_by_column: " + str( data1 ) + " - " + str( data2 )

		if data1 < data2:
			return -1

		if data1 > data2:
			return 1

		return 0

	def show_settings_dialog_( self ):
		if self.settings_dialog is None:
			self.settings_dialog = gnomesettingsdialog.SettingsDialog( self.config, self.glade )
		self.settings_dialog.run()

	def on_init( self ):
		if not self.config.is_configured():
			self.show_settings_dialog_()

			if not self.config.is_configured():
				gtk.main_quit()
				return False

		self.update_all( True )

		self.force_wait_lock_counter = 0
		self.update_backup_info()
		gobject.timeout_add( 1000, self.update_backup_info )
		return False

	def get_default_startup_folder_and_file( self ):
		last_path = self.config.get_str_value( 'gnome.last_path', '' )
		if len(last_path) > 0 and os.path.isdir(last_path):
			return ( last_path, None, False )
		return ( '/', None, False )

	def get_cmd_startup_folder_and_file( self, cmd ):
		if cmd is None:
			cmd = self.app_instance.raise_cmd

		if len( cmd ) < 1:
			return None

		path = None
		show_snapshots = False

		for arg in cmd.split( '\n' ):
			if len( arg ) < 1:
				continue
			if arg == '-s' or arg == '--snapshots':
				show_snapshots = True
				continue
			if arg[0] == '-':
				continue
			if path is None:
				path = arg

		if path is None:
			return None

		if len( path ) < 1:
			return None

		path = os.path.expanduser( path )
		path = os.path.abspath( path )

		if os.path.isdir( path ):
			if len( path ) < 1:
				show_snapshots = False

			if show_snapshots:
				return ( os.path.dirname( path ), path, True )
			else:
				return ( path, '', False )

		if os.path.isfile( path ):
			return ( os.path.dirname( path ), path, show_snapshots )

		return None

	def get_startup_folder_and_file( self, cmd = None ):
		startup_folder = self.get_cmd_startup_folder_and_file( cmd )
		if startup_folder is None:
			return self.get_default_startup_folder_and_file()
		return startup_folder

	def update_all( self, init ):
		#fill lists
		selected_file = None
		show_snapshots = False
		if init:
			self.folder_path, selected_file, show_snapshots = self.get_startup_folder_and_file()
		self.snapshot_id = '/'
		self.snapshots_list = []

		self.fill_places()
		self.fill_time_line( False )
		self.update_folder_view( 1, selected_file, show_snapshots )

	def places_pix_renderer_function( self, column, renderer, model, iter, user_data ):
		if len( model.get_value( iter, 1 ) ) == 0:
			renderer.set_property( 'visible', False )
		else:
			renderer.set_property( 'visible', True )

	def places_text_renderer_function( self, column, renderer, model, iter, user_data ):
		if len( model.get_value( iter, 1 ) ) == 0:
			renderer.set_property( 'cell-background-set', True )
			renderer.set_property( 'cell-background', self.special_background_color )
		else:
			renderer.set_property( 'cell-background-set', False )

	def places_select_function( self, info, store ):
		if len( store.get_value( store.get_iter( info[0] ), 1 ) ) == 0:
			return False
		return True

	def raise_application( self ):
		raise_cmd = self.app_instance.raise_command()
		if raise_cmd is None:
			return True

		print "Raise cmd: " + raise_cmd
		self.window.present_with_time( int(time.time()) )
		self.window.window.focus()
		#self.window.present()

		if len( raise_cmd ) == 0:
			return True

		print "Check if the main window is the only top level visible window"
		for window in gtk.window_list_toplevels():
			if window.get_property( 'visible' ):
				if window != self.window:
					print "Failed"
					return True

		print "OK"

		folder_and_file = self.get_cmd_startup_folder_and_file( raise_cmd )
		if folder_and_file is None:
			return True

		folder_path, file_name, show_snapshots = folder_and_file

		#select now
		self.snapshot_id = '/'
		self.list_time_line.get_selection().select_iter( self.store_time_line.get_iter_first() )

		#select the specified file
		self.folder_path = folder_path
		self.update_folder_view( 1, file_name, show_snapshots )

		return True

	def update_backup_info( self, force_wait_lock = False ):
		if None is self.glade.get_widget( 'btn_backup' ):
			return True

		#print "forceWaitLock: %s" % forceWaitLock

		if force_wait_lock:
			self.force_wait_lock_counter = 10
		
		busy = self.snapshots.is_busy()
		if busy:
			self.force_wait_lock_counter = 0

		if self.force_wait_lock_counter > 0:
			self.force_wait_lock_counter = self.force_wait_lock_counter - 1

		fake_busy = busy or self.force_wait_lock_counter > 0
		self.glade.get_widget( 'btn_backup' ).set_sensitive( not fake_busy )

		if fake_busy:
			if not self.update_time_line or force_wait_lock:
				self.status_bar.push( 0, _('Working ...') )
				self.update_time_line = True
		elif self.update_time_line:
			self.update_time_line = False
			snapshots_list = self.snapshots_list

			self.fill_time_line()

			#print "New backup: %s" % self.lastBackupList
			#print "Last backup: %s" % lastBackupList

			if snapshots_list != self.snapshots_list:
				self.status_bar.push( 0, _('Done') )
			else:
				self.status_bar.push( 0, _('Done, no backup needed') )

		return True

	def fill_places( self ):
		self.store_places.clear()

		#add global places
		self.store_places.append( [ "<b>%s</b>" % _('Global'), '', '' ] )
		self.store_places.append( [ _('Root'), '/', gtk.STOCK_HARDDISK ] )
		self.store_places.append( [ _('Home'), os.path.expanduser( '~' ), gtk.STOCK_HOME ] )

		#add bookmarks
		rawbookmarks = ''
		
		try:
			file = open( os.path.expanduser('~/.gtk-bookmarks') )
			rawbookmarks = file.read()
			file.close()
		except:
			pass

		bookmarks = []
		for rawbookmark in rawbookmarks.split( '\n' ):
			if rawbookmark.startswith( 'file://' ):
				index = rawbookmark.find( ' ' )
				if index > 0:
					bookmarks.append( ( gnomevfs.unescape_string_for_display( rawbookmark[ 7 : index ] ), rawbookmark[ index + 1 : ] ) )
				elif index < 0:
					index = rawbookmark.rfind( '/' )
					if index > 0:
						bookmarks.append( ( gnomevfs.unescape_string_for_display( rawbookmark[ 7 : ] ), gnomevfs.unescape_string_for_display( rawbookmark[ index + 1 : ] ) ) )

		if len( bookmarks ) > 0:
			self.store_places.append( [ "<b>%s</b>" % _('Bookmarks'), '', '' ] )
			for bookmark in bookmarks:
				self.store_places.append( [ bookmark[1], bookmark[0], self.icon_names.get_icon(bookmark[0]) ] )

		#add backup folders
		include_folders = self.config.get_include_folders()
		if len( include_folders ) > 0:
			if len( include_folders ) > 0:
				self.store_places.append( [ "<b>%s</b>" % _('Backup Directories'), '', '' ] )
				for folder in include_folders:
					self.store_places.append( [ folder, folder, gtk.STOCK_SAVE ] )

	def fill_time_line( self, update_folder_view = True ):
		current_selection = '/'
		iter = self.list_time_line.get_selection().get_selected()[1]
		if not iter is None:
			current_selection = self.store_time_line.get_value( iter, 1 )

		self.store_time_line.clear()
		self.store_time_line.append( [ gnomesnapshotstools.get_snapshot_display_markup( self.snapshots, '/' ), '/' ] )

		self.snapshots_list = self.snapshots.get_snapshots_list() 

		groups = []
		now = datetime.date.today()

		#today
		date = now
		groups.append( (_('Today'), self.snapshots.get_snapshot_id( date ), []) )

		#yesterday
		date = now - datetime.timedelta( days = 1 )
		groups.append( (_('Yesterday'), self.snapshots.get_snapshot_id( date ), []) )

		#this week
		date = now - datetime.timedelta( days = now.weekday() )
		groups.append( (_('This week'), self.snapshots.get_snapshot_id( date ), []) )

		#last week
		date = now - datetime.timedelta( days = now.weekday() + 7 )
		groups.append( (_('Last week'), self.snapshots.get_snapshot_id( date ), []) )

		#fill groups
		for snapshot_id in self.snapshots_list:
			found = False

			for group in groups:
				if snapshot_id >= group[1]:
					group[2].append( snapshot_id )
					found = True
					break

			if not found:
				year = int( snapshot_id[ 0 : 4 ] )
				month = int( snapshot_id[ 4 : 6 ] )
				date = datetime.date( year, month, 1 )

				group_name = ''
				if year == now.year:
					group_name = date.strftime( '%B' ).capitalize()
				else:
					group_name = date.strftime( '%B, %Y' ).capitalize()

				groups.append( ( group_name, self.snapshots.get_snapshot_id( date ), [ snapshot_id ]) )

		#fill time_line list
		for group in groups:
			if len( group[2] ) > 0:
				self.store_time_line.append( [ "<b>%s</b>" % group[0], '' ] );
				for snapshot_id in group[2]:
					self.store_time_line.append( [ gnomesnapshotstools.get_snapshot_display_markup( self.snapshots, snapshot_id ), snapshot_id ] )

		#select previous item
		iter = self.store_time_line.get_iter_first()
		while not iter is None:
			if current_selection == self.store_time_line.get_value( iter, 1 ):
				break
			iter = self.store_time_line.iter_next( iter )

		changed = False
		if iter is None:
			changed = True
			iter = self.store_time_line.get_iter_first()

		self.list_time_line.get_selection().select_iter( iter )

		if changed and update_folder_view:
			self.update_folder_view( 2 )

	def on_close( self, *params ):
		main_window_x, main_window_y = self.window.get_position()
		main_window_width, main_window_height = self.window.get_size()
		main_window_hpaned1 = self.glade.get_widget('hpaned1').get_position()
		main_window_hpaned2 = self.glade.get_widget('hpaned2').get_position()

		self.config.set_int_value( 'gnome.main_window.x', main_window_x )
		self.config.set_int_value( 'gnome.main_window.y', main_window_y )
		self.config.set_int_value( 'gnome.main_window.width', main_window_width )
		self.config.set_int_value( 'gnome.main_window.height', main_window_height )
		self.config.set_int_value( 'gnome.main_window.hpaned1', main_window_hpaned1 )
		self.config.set_int_value( 'gnome.main_window.hpaned2', main_window_hpaned2 )
		self.config.set_str_value( 'gnome.last_path', self.folder_path )
		self.config.set_bool_value( 'gnome.show_hidden_files', self.show_hidden_files )

		self.config.save()
		self.window.destroy()
		return True

	def on_list_time_line_cursor_changed( self, list ):
		if list.get_selection().path_is_selected( list.get_cursor()[ 0 ] ):
			self.update_folder_view( 2 )

	def on_list_places_cursor_changed( self, list ):
		if list.get_selection().path_is_selected( list.get_cursor()[ 0 ] ):
			iter = list.get_selection().get_selected()[1]
			folder_path = self.store_places.get_value( iter, 1 )
			if folder_path != self.folder_path:
				self.folder_path = folder_path
				self.update_folder_view( 0 )

	def on_list_folder_view_drag_data_get( self, widget, drag_context, selection_data, info, timestamp, user_param1 = None ):
		iter = self.list_folder_view.get_selection().get_selected()[1]
		if not iter is None:
			path = self.store_folder_view.get_value( iter, 1 )
			path = self.snapshots.get_snapshot_path_to( self.snapshot_id, path )
			path = gnomevfs.escape_path_string( path )
			selection_data.set_uris( [ 'file://' + path ] )

	def on_list_folder_view_button_press_event( self, list, event ):
		if event.button != 3:
			return

		if len( self.store_folder_view ) <= 0:
			return

		path = self.list_folder_view.get_path_at_pos( int( event.x ), int( event.y ) )
		if path is None:
			return
		path = path[0]
	
		self.list_folder_view.get_selection().select_path( path )
		self.show_folder_view_menu_popup( self.list_folder_view, event.button, event.time )

	def on_list_folder_view_popup_menu( self, list ):
		self.show_folder_view_menu_popup( list, 1, gtk.get_current_event_time() )

	def show_folder_view_menu_popup( self, list, button, time ):
		iter = list.get_selection().get_selected()[1]
		if iter is None:
			return

		#print "popup-menu"
		self.popup_menu = gtk.Menu()

		menu_item = gtk.ImageMenuItem( 'backintime.open' )
		menu_item.set_image( gtk.image_new_from_icon_name( self.store_folder_view.get_value( iter, 2 ), gtk.ICON_SIZE_MENU ) )
		menu_item.connect( 'activate', self.on_list_folder_view_open_item )
		self.popup_menu.append( menu_item )

		self.popup_menu.append( gtk.SeparatorMenuItem() )

		menu_item = gtk.ImageMenuItem( 'backintime.copy' )
		menu_item.set_image( gtk.image_new_from_stock( gtk.STOCK_COPY, gtk.ICON_SIZE_MENU ) )
		menu_item.connect( 'activate', self.on_list_folder_view_copy_item )
		self.popup_menu.append( menu_item )

		menu_item = gtk.ImageMenuItem( 'backintime.snapshots' )
		menu_item.set_image( gtk.image_new_from_stock( gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU ) )
		menu_item.connect( 'activate', self.on_list_folder_view_snapshots_item )
		self.popup_menu.append( menu_item )

		if len( self.snapshot_id ) > 1:
			menu_item = gtk.ImageMenuItem( 'backintime.restore' )
			menu_item.set_image( gtk.image_new_from_stock( gtk.STOCK_UNDELETE, gtk.ICON_SIZE_MENU ) )
			menu_item.connect( 'activate', self.on_list_folder_view_restore_item )
			self.popup_menu.append( menu_item )

		self.popup_menu.show_all()
		self.popup_menu.popup( None, None, None, button, time )

	def on_list_folder_view_restore_item( self, widget, data = None ):
		self.on_btn_restore_clicked( self.glade.get_widget( 'btn_restore' ) )

	def on_list_folder_view_copy_item( self, widget, data = None ):
		self.on_btn_copy_clicked( self.glade.get_widget( 'btn_copy' ) )

	def on_list_folder_view_snapshots_item( self, widget, data = None ):
		self.on_btn_snapshots_clicked( self.glade.get_widget( 'btn_snapshots' ) )

	def on_list_folder_view_open_item( self, widget, data = None ):
		iter = self.list_folder_view.get_selection().get_selected()[1]
		if iter is None:
			return

		path = self.store_folder_view.get_value( iter, 1 )
		path = self.snapshots.get_snapshot_path_to( self.snapshot_id, path )
		cmd = "gnome-open \"%s\" &" % path
		print cmd
		os.system( cmd )

	def on_list_folder_view_row_activated( self, list, path, column ):
		iter = list.get_selection().get_selected()[1]
		path = self.store_folder_view.get_value( iter, 1 )

		#directory
		if 0 == self.store_folder_view.get_value( iter, 3 ):
			self.folder_path = path
			self.update_folder_view( 1 )
			return

		#file
		path = self.snapshots.get_snapshot_path_to( self.snapshot_id, path )
		cmd = "gnome-open \"%s\" &" % path
		print cmd
		os.system( cmd )

	def on_btn_fodler_up_clicked( self, button ):
		if len( self.folder_path ) <= 1:
			return

		index = self.folder_path.rfind( '/' )
		if index < 1:
			parent_path = "/"
		else:
			parent_path = self.folder_path[ : index ]

		self.folder_path = parent_path
		self.update_folder_view( 1 )

	def on_btn_restore_clicked( self, button ):
		iter = self.list_folder_view.get_selection().get_selected()[1]
		if not iter is None:
			button.set_sensitive( False )
			gobject.timeout_add( 100, self.restore_ )
	
	def on_btn_copy_clicked( self, button ):
		iter = self.list_folder_view.get_selection().get_selected()[1]
		if iter is None:
			return

		path = self.store_folder_view.get_value( iter, 1 )
		path = self.snapshots.get_snapshot_path_to( self.snapshot_id, path )

		gnomeclipboardtools.clipboard_copy_path( path )

	def on_btn_hidden_files_toggled( self, button ):
		if self.folder_path is None:
			return

		self.show_hidden_files = button.get_active()
		self.update_folder_view( 0 )

	def on_btn_snapshots_clicked( self, button ):
		iter = self.list_folder_view.get_selection().get_selected()[1]
		if iter is None:
			return

		path = self.store_folder_view.get_value( iter, 1 )
		icon_name = self.store_folder_view.get_value( iter, 2 )

		if self.snapshots_dialog is None:
			self.snapshots_dialog = gnomesnapshotsdialog.SnapshotsDialog( self.snapshots, self.glade )

		retVal = self.snapshots_dialog.run( path, self.snapshots_list, self.snapshot_id, icon_name )
		
		#select the specified file
		if not retVal is None:
			iter = self.store_time_line.get_iter_first()
			while not iter is None:
				snapshot_id = self.store_time_line.get_value( iter, 1 )
				if snapshot_id == retVal:
					break
				iter = self.store_time_line.iter_next( iter )

			if not iter is None:
				self.list_time_line.get_selection().select_iter( iter )
				self.update_folder_view( 2 )

	def restore_( self ):
		iter = self.list_folder_view.get_selection().get_selected()[1]
		if not iter is None:
			self.snapshots.restore( self.snapshot_id, self.store_folder_view.get_value( iter, 1 ) )

		self.glade.get_widget( 'btn_restore' ).set_sensitive( True )
		return False

	def on_btn_about_clicked( self, button ):
		if self.about_dialog is None:
			self.about_dialog = AboutDialog( self.config, self.glade )
		self.about_dialog.run()

	def on_help( self ):
		gnome.help_display('backintime')

	def on_btn_help_clicked( self, button ):
		self.on_help()

	def on_key_release_event( self, widget, event ):
		if 'F1' == gtk.gdk.keyval_name( event.keyval ) and ( event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK) ) == 0:
			self.on_help()

	def on_btn_settings_clicked( self, button, ):
		snapshots_path = self.config.get_snapshots_path()
		include_folders = self.config.get_include_folders()

		self.show_settings_dialog_()

		if not self.config.is_configured():
			gtk.main_quit()
		else:
			if snapshots_path != self.config.get_snapshots_path() or include_folders != self.config.get_include_folders():
				self.update_all( False )

	def on_btn_snapshot_name_clicked( self, button ):
		iter = self.list_time_line.get_selection().get_selected()[1]
		if iter is None:
			return

		snapshot_id = self.store_time_line.get_value( iter, 1 )
		if len( snapshot_id ) <= 1:
			return

		old_name = self.snapshots.get_snapshot_name( snapshot_id )
		new_name = gnomemessagebox.text_input_dialog( self.window, self.glade, _('Snapshot Name'), old_name )
		if new_name is None:
			return

		if old_name == new_name:
			return

		self.snapshots.set_snapshot_name( snapshot_id, new_name )
		self.store_time_line.set_value( iter, 0, gnomesnapshotstools.get_snapshot_display_markup( self.snapshots, snapshot_id ) )

	def on_btn_remove_snapshot_clicked( self, button ):
		iter = self.list_time_line.get_selection().get_selected()[1]
		if iter is None:
			return

		snapshot_id = self.store_time_line.get_value( iter, 1 )
		if len( snapshot_id ) <= 1:
			return

		if gtk.RESPONSE_YES == gnomemessagebox.show_question( self.window, self.config, _( "Are you sure you want to remove the snapshot:\n<b>%s</b>" ) % self.snapshots.get_snapshot_display_name( snapshot_id ) ):
			print "Remove Snapshot: %s" % snapshot_id
			self.snapshots.remove_snapshot( snapshot_id )
			self.fill_time_line()

	def on_btn_backup_clicked( self, button ):
		button.set_sensitive( False )
		self.updatetime_line = True
		
		if self.snapshots.is_busy():
			self.update_backup_info()
			return

		#backup.backup()
		app = 'backintime'
		if os.path.isfile( './backintime' ):
			app = './backintime'
		cmd = "nice -n 19 %s --backup &" % app
		os.system( cmd )

		self.update_backup_info( True )

	def on_btn_update_snapshots_clicked( self, button ):
		self.fill_time_line()

	def update_folder_view( self, changed_from, selected_file = None, show_snapshots = False ): #0 - places, 1 - folder view, 2 - time_line
		#update backup time
		if 2 == changed_from:
			iter = self.list_time_line.get_selection().get_selected()[1]
			self.snapshot_id = self.store_time_line.get_value( iter, 1 )
			#self.lblTime.set_markup( "<b>%s</b>" % backupTime )

		self.window.set_title( self.config.APP_NAME + ': ' + self.snapshots.get_snapshot_display_id( self.snapshot_id ) )

		#update selected places item
		if 1 == changed_from:
			iter = self.store_places.get_iter_first()
			while not iter is None:
				place_path = self.store_places.get_value( iter, 1 )
				if place_path == self.folder_path:
					break
				iter = self.store_places.iter_next( iter )

			if iter is None:
				self.list_places.get_selection().unselect_all()
			else:
				self.list_places.get_selection().select_iter( iter )

		#update folder view
		full_path = self.snapshots.get_snapshot_path_to( self.snapshot_id, self.folder_path )
		all_files = []

		try:
			all_files = os.listdir( full_path )
			all_files.sort()
		except:
			pass

		files = []
		for file in all_files:
			if len( file ) == 0:
				continue

			if not self.show_hidden_files:
				if file[ 0 ] == '.':
					continue
				if file[ -1 ] == '~':
					continue

			path = os.path.join( full_path, file )

			file_size = -1
			file_date = -1

			try:
				file_stat = os.stat( path )
				file_size = file_stat[stat.ST_SIZE]
				file_date = file_stat[stat.ST_MTIME]
			except:
				pass

			#format size
			file_size_int = file_size
			if file_size_int < 0:
				file_size_int = 0

			if file_size < 0:
				file_size = 'unknown'
			elif file_size < 1024:
				file_size = str( file_size ) + ' bytes'
			elif file_size < 1024 * 1024:
				file_size = file_size / 1024
				file_size = str( file_size ) + ' KB'
			elif file_size < 1024 * 1024 * 1024:
				file_size = file_size / ( 1024 * 1024 )
				file_size = str( file_size ) + ' MB'
			else:
				file_size = file_size / ( 1024 * 1024 * 1024 )
				file_size = str( file_size ) + ' GB'

			#format date
			if file_date < 0:
				file_date = 'unknown'
			else:
				file_date = datetime.datetime.fromtimestamp(file_date).isoformat(' ')

			if os.path.isdir( path ):
				files.append( [ file, file_size, file_date, self.icon_names.get_icon(path), file_size_int, 0 ] )
			else:
				files.append( [ file, file_size, file_date, self.icon_names.get_icon(path), file_size_int, 1 ] )

		#try to keep old selected file
		if selected_file is None:
			selected_file = ''
			iter = self.list_folder_view.get_selection().get_selected()[1]
			if not iter is None:
				selected_file = self.store_folder_view.get_value( iter, 1 )

		#populate the list
		self.store_folder_view.clear()

		selected_iter = None
		for item in files:
			rel_path = os.path.join( self.folder_path, item[0] )
			new_iter = self.store_folder_view.append( [ item[0], rel_path, item[3], item[5], item[1], item[2], item[4] ] )
			if selected_file == rel_path:
				selected_iter = new_iter 

		#select old item or the first item
		if len( files ) > 0:
			if selected_iter is None:
				selected_iter = self.store_folder_view.get_iter_first()
			self.list_folder_view.get_selection().select_iter( selected_iter )
			self.list_folder_view.drag_source_set( gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK, gtk.target_list_add_uri_targets(), gtk.gdk.ACTION_COPY )
		else:
			self.list_folder_view.drag_source_unset()

		#update folderup button state
		self.glade.get_widget( 'btn_folder_up' ).set_sensitive( len( self.folder_path ) > 1 )

		#update restore button state
		self.glade.get_widget( 'btn_restore' ).set_sensitive( len( self.snapshot_id ) > 1 and len( self.store_folder_view ) > 0 )

		#update remove/name snapshot buttons
		self.glade.get_widget( 'btn_snapshot_name' ).set_sensitive( len( self.snapshot_id ) > 1 )
		self.glade.get_widget( 'btn_remove_snapshot' ).set_sensitive( len( self.snapshot_id ) > 1 )

		#update copy button state
		self.glade.get_widget( 'btn_copy' ).set_sensitive( len( self.store_folder_view ) > 0 )

		#update snapshots button state
		self.glade.get_widget( 'btn_snapshots' ).set_sensitive( len( self.store_folder_view ) > 0 )

		#display current folder
		self.glade.get_widget( 'edit_current_path' ).set_text( self.folder_path )

		#show snapshots
		if show_snapshots:
			self.on_btn_snapshots_clicked( None )


def open_url( dialog, link, user_data ):
	os.system( "gnome-open \"%s\" &" % link )


class GnomeTakeSnapshotCallback( threading.Thread ): #used to display status icon
	def __init__( self ):
		threading.Thread.__init__( self )
		self.stop_flag = False
		self.cfg = None

	def init( self, cfg ):
		self.cfg = cfg
	
	def snapshot_begin( self ):
		self.stop_flag = False
		self.start()

	def snapshot_end( self ):
		self.stop_flag = True
		try:
			self.join()
		except:
			pass

	def run(self):
		logger.info( '[GnomeTakeSnapshotCallback.run]' )

		create_gnome_app( self.cfg )

		gtk.gdk.threads_init()
		display = gtk.gdk.display_get_default()
		
		if display is None:
			logger.info( '[GnomeTakeSnapshotCallback.run] display KO' )
			return

		status_icon = None
		try:
			status_icon = gtk.StatusIcon()
		except:
			pass

		if status_icon is None:
			logger.info( '[GnomeTakeSnapshotCallback.run] no status_icon' )
			return
		
		status_icon.set_from_stock( gtk.STOCK_SAVE )
		status_icon.set_visible( True )
		status_icon.set_tooltip(_('Back In Time: take snapshot ...'))

		logger.info( '[GnomeTakeSnapshotCallback.run] begin loop' )

		while True:
			gtk.main_iteration( False )
			if self.stop_flag:
				break
			if not gtk.events_pending():
				time.sleep( 0.2 )
		
		status_icon.set_visible( False )
		gtk.main_iteration( False )
		
		logger.info( '[GnomeTakeSnapshotCallback.run] end loop' )


def create_gnome_app( cfg ):
	gnome_props = { gnome.PARAM_APP_DATADIR : '/usr/share' }
	return gnome.program_init( 'backintime', cfg.VERSION, properties = gnome_props )


if __name__ == '__main__':
	cfg = backintime.start_app( GnomeTakeSnapshotCallback() )

	raise_cmd = ''
	if len( sys.argv ) > 1:
		raise_cmd = '\n'.join( sys.argv[ 1 : ] )

	app_instance = guiapplicationinstance.GUIApplicationInstance( cfg.get_app_instance_file(), raise_cmd )

	create_gnome_app( cfg )

	gtk.about_dialog_set_url_hook( open_url, None )

	logger.openlog()
	main_window = MainWindow( cfg, app_instance )
	gtk.main()
	logger.closelog()

	app_instance.exit_application()

