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

import datetime
import gettext
import time

import backintime
import config
import logger
import snapshots
import guiapplicationinstance

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *


import kde4tools


_=gettext.gettext


#class AboutDialog:
#	def __init__( self, config, glade ):
#		self.glade = glade 
#		self.dialog = self.glade.get_widget( 'AboutDialog' )
#		self.dialog.set_name( config.APP_NAME )
#		self.dialog.set_version( config.VERSION )
#		self.dialog.set_copyright( 'Copyright (C) 2008-2009 Oprea Dan' )
#		self.dialog.set_website( 'http://www.le-web.org/back-in-time/' )
#		self.dialog.set_website_label( 'http://www.le-web.org/back-in-time/' )
#		self.dialog.set_license( config.get_license() )
#		authors = config.get_authors()
#		if not authors is None:
#			self.dialog.set_authors( authors.split('\n') )
#		self.dialog.set_translator_credits( config.get_translations() )
#
#		signals = { 
#				'on_AboutDialog_response' : self.close,
#			}
#
#		self.glade.signal_autoconnect( signals )
#
#	def close( self, button, response ):
#		self.dialog.hide()
#
#	def run( self ):
#		return self.dialog.run()


class MainWindow( QMainWindow ):
	def __init__( self, config, app_instance ):
		QMainWindow.__init__( self )

		self.config = config
		self.app_instance = app_instance
		self.snapshots = snapshots.Snapshots( config )

		self.setWindowTitle( self.config.APP_NAME )
		self.setWindowIcon( KIcon( 'document-save' ) )

		self.main_toolbar = QToolBar( self )
		self.main_toolbar.setFloatable( False )

		self.btn_take_snapshot = self.main_toolbar.addAction( KIcon( 'document-save' ), '' )
		self.btn_name_snapshot = self.main_toolbar.addAction( KIcon( 'edit-rename' ), '' )
		self.btn_remove_snapshot = self.main_toolbar.addAction( KIcon( 'edit-delete' ), '' )
	
		self.main_toolbar.addSeparator()

		self.btn_settings = self.main_toolbar.addAction( KIcon( 'configure' ), '' )
		self.main_toolbar.addSeparator()
		self.btn_about = self.main_toolbar.addAction( KIcon( 'help-about' ), '' )
		self.btn_help = self.main_toolbar.addAction( KIcon( 'help-contents' ), '' )
		self.main_toolbar.addSeparator()
		self.btn_quit = self.main_toolbar.addAction( KIcon( 'application-exit' ), '' )

		self.files_view_toolbar = QToolBar( self )
		self.files_view_toolbar.setFloatable( False )

		self.btn_folder_up = self.files_view_toolbar.addAction( KIcon( 'go-up' ), '' )

		self.edit_current_path = QLineEdit( self )
		self.edit_current_path.setReadOnly( True )
		self.files_view_toolbar.addWidget( self.edit_current_path )

		#show hidden files
		self.show_hidden_files = self.config.get_bool_value( 'kde4.show_hidden_files', False )

		self.btn_show_hidden_files = self.files_view_toolbar.addAction( KIcon( 'list-add' ), '' )
		self.btn_show_hidden_files.setCheckable( True )
		self.btn_show_hidden_files.setChecked( self.show_hidden_files )

		self.files_view_toolbar.addSeparator()

		self.btn_restore = self.files_view_toolbar.addAction( KIcon( 'document-revert' ), '' )
		self.btn_copy = self.files_view_toolbar.addAction( KIcon( 'edit-copy' ), '' )
		self.btn_snapshots = self.files_view_toolbar.addAction( KIcon( 'view-list-details' ), '' )

		self.list_time_line = QTreeWidget( self )
		self.list_time_line.setHeaderLabel( _('Timeline') )
		self.list_time_line.setRootIsDecorated( False )

		self.list_places = QTreeWidget( self )
		self.list_places.setHeaderLabel( _('Places') )
		self.list_places.setRootIsDecorated( False )

		self.list_files_view = QTreeWidget( self )
		self.list_files_view.setHeaderLabels( [_('Name'), _('Size'), _('Date')] )
		self.list_files_view.setRootIsDecorated( False )

		self.second_splitter = QSplitter( self )
		self.second_splitter.setOrientation( Qt.Horizontal )
		self.second_splitter.addWidget( self.list_time_line )
		self.second_splitter.addWidget( self.list_places )

		left_layout = QVBoxLayout( self )
		left_layout.addWidget( self.main_toolbar )
		left_layout.addWidget( self.second_splitter )
		left, top, right, bottom = left_layout.getContentsMargins()
		left_layout.setContentsMargins( left, top, 0, bottom )

		left_widget = QWidget( self )
		left_widget.setLayout( left_layout )

		right_layout = QVBoxLayout( self )
		right_layout.addWidget( self.files_view_toolbar )
		right_layout.addWidget( self.list_files_view )
		left, top, right, bottom = right_layout.getContentsMargins()
		right_layout.setContentsMargins( 0, top, right, bottom )

		right_widget = QWidget( self )
		right_widget.setLayout( right_layout )

		self.main_splitter = QSplitter( self )
		self.main_splitter.setOrientation( Qt.Horizontal )
		self.main_splitter.addWidget( left_widget )
		self.main_splitter.addWidget( right_widget )

		self.setCentralWidget( self.main_splitter )
		
		self.statusBar().showMessage( _('Done') )

		self.snapshots_list = []
		self.snapshot_id = '/'
		self.path = self.config.get_str_value( 'kde4.last_path', '/' )
		self.edit_current_path.setText( self.path )

		#restore size and position
		x = self.config.get_int_value( 'kde4.main_window.x', -1 )
		y = self.config.get_int_value( 'kde4.main_window.y', -1 )
		if x >= 0 and y >= 0:
			self.move( x, y )

		w = self.config.get_int_value( 'kde4.main_window.width', 800 )
		h = self.config.get_int_value( 'kde4.main_window.height', 500 )
		self.resize( w, h )

		main_splitter_left_w = self.config.get_int_value( 'kde4.main_window.main_splitter_left_w', 400 )
		main_splitter_right_w = self.config.get_int_value( 'kde4.main_window.main_splitter_right_w', 400 )
		sizes = [ main_splitter_left_w, main_splitter_right_w ]
		self.main_splitter.setSizes( sizes )
		
		second_splitter_left_w = self.config.get_int_value( 'kde4.main_window.second_splitter_left_w', 200 )
		second_splitter_right_w = self.config.get_int_value( 'kde4.main_window.second_splitter_right_w', 200 )
		sizes = [ second_splitter_left_w, second_splitter_right_w ]
		self.second_splitter.setSizes( sizes )

		files_view_name_width = self.config.get_int_value( 'kde4.main_window.files_view.name_width', -1 )
		files_view_size_width = self.config.get_int_value( 'kde4.main_window.files_view.size_width', -1 )
		files_view_date_width = self.config.get_int_value( 'kde4.main_window.files_view.date_width', -1 )
		if files_view_name_width > 0 and files_view_size_width > 0 and files_view_date_width > 0:
			self.list_files_view.header().resizeSection( 0, files_view_name_width )
			self.list_files_view.header().resizeSection( 1, files_view_size_width )
			self.list_files_view.header().resizeSection( 2, files_view_date_width )

		#populate lists
		self.update_time_line()
		self.update_places()
		self.update_files_view( 0 )

		self.list_files_view.setFocus()

		QObject.connect( self.list_time_line, SIGNAL('currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)'), self.on_list_time_line_current_item_changed )
		QObject.connect( self.list_places, SIGNAL('currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)'), self.on_list_places_current_item_changed )
		QObject.connect( self.list_files_view, SIGNAL('itemActivated(QTreeWidgetItem*,int)'), self.on_list_files_view_item_activated )

		QObject.connect( self.btn_take_snapshot, SIGNAL('triggered()'), self.on_btn_take_snapshot_clicked )
		QObject.connect( self.btn_name_snapshot, SIGNAL('triggered()'), self.show_not_implemented )
		QObject.connect( self.btn_remove_snapshot, SIGNAL('triggered()'), self.show_not_implemented )
		QObject.connect( self.btn_settings, SIGNAL('triggered()'), self.show_not_implemented )
		QObject.connect( self.btn_about, SIGNAL('triggered()'), self.show_not_implemented )
		QObject.connect( self.btn_help, SIGNAL('triggered()'), self.show_not_implemented )
		QObject.connect( self.btn_quit, SIGNAL('triggered()'), self.close )
		QObject.connect( self.btn_folder_up, SIGNAL('triggered()'), self.on_btn_folder_up_clicked )
		QObject.connect( self.btn_show_hidden_files, SIGNAL('toggled(bool)'), self.on_btn_show_hidden_files_toggled )
		QObject.connect( self.btn_restore, SIGNAL('triggered()'), self.show_not_implemented )
		QObject.connect( self.btn_copy, SIGNAL('triggered()'), self.show_not_implemented )
		QObject.connect( self.btn_snapshots, SIGNAL('triggered()'), self.show_not_implemented )

		self.force_wait_lock_counter = 0
		self.timer_update_take_snapshot = QTimer( self )
		self.timer_update_take_snapshot.setInterval( 1000 )
		self.timer_update_take_snapshot.setSingleShot( False )
		QObject.connect( self.timer_update_take_snapshot, SIGNAL('timeout()'), self.update_take_snapshot )
		self.timer_update_take_snapshot.start()

#		self.special_background_color = 'lightblue'
#		self.popup_menu = None
#
#		self.folder_path = None
#		self.snapshot_id = ''
#
#		self.about_dialog = None
#		self.settings_dialog = None
#		self.snapshots_dialog = None
#		self.snapshot_name_dialog = None
#
#		self.glade = gtk.glade.XML( os.path.join( self.config.get_app_path(), 'gnomebackintime.glade' ), None, 'backintime' )
#
#		signals = { 
#				'on_MainWindow_destroy' : gtk.main_quit,
#				'on_MainWindow_delete_event' : self.on_close,
#				'on_MainWindow_key_release_event': self.on_key_release_event,
#				'on_btn_exit_clicked' : self.on_close,
#				'on_btn_help_clicked' : self.on_btn_help_clicked,
#				'on_btn_about_clicked' : self.on_btn_about_clicked,
#				'on_btn_settings_clicked' : self.on_btn_settings_clicked,
#				'on_btn_backup_clicked' : self.on_btn_backup_clicked,
#				'on_btn_snapshot_name_clicked' : self.on_btn_snapshot_name_clicked,
#				'on_btn_remove_snapshot_clicked' : self.on_btn_remove_snapshot_clicked,
#				'on_btn_restore_clicked' : self.on_btn_restore_clicked,
#				'on_btn_copy_clicked' : self.on_btn_copy_clicked,
#				'on_btn_snapshots_clicked' : self.on_btn_snapshots_clicked,
#				'on_btn_hidden_files_toggled' : self.on_btn_hidden_files_toggled,
#				'on_list_places_cursor_changed' : self.on_list_places_cursor_changed,
#				'on_list_time_line_cursor_changed' : self.on_list_time_line_cursor_changed,
#				'on_btn_folder_up_clicked' : self.on_btn_fodler_up_clicked,
#				'on_list_folder_view_row_activated' : self.on_list_folder_view_row_activated,
#				'on_list_folder_view_popup_menu' : self.on_list_folder_view_popup_menu,
#				'on_list_folder_view_button_press_event': self.on_list_folder_view_button_press_event,
#				'on_list_folder_view_drag_data_get': self.on_list_folder_view_drag_data_get
#			}
#
#		self.glade.signal_autoconnect( signals )
#
#		self.window = self.glade.get_widget( 'MainWindow' )
#		self.window.set_title( self.config.APP_NAME )
#
#		#icons
#		self.icon_names = gnomefileicons.GnomeFileIcons()
#
#		#fix a glade bug
#		self.glade.get_widget( 'btn_current_path' ).set_expand( True )
#
#		#status bar
#		self.status_bar = self.glade.get_widget( 'status_bar' )
#		self.status_bar.push( 0, _('Done') )
#
#		#show hidden files
#		self.show_hidden_files = self.config.get_bool_value( 'gnome.show_hidden_files', False )
#		self.btn_hidden_files = self.glade.get_widget( 'btn_hidden_files' )
#		self.btn_hidden_files.set_active( self.show_hidden_files )
#
#		#setup places view
#		self.list_places = self.glade.get_widget( 'list_places' )
#
#		pix_renderer = gtk.CellRendererPixbuf()
#		text_renderer = gtk.CellRendererText()
#		
#		column = gtk.TreeViewColumn( _('Places') )
#		column.pack_start( pix_renderer, False )
#		column.pack_end( text_renderer, True )
#		column.add_attribute( pix_renderer, 'icon-name', 2 )
#		column.add_attribute( text_renderer, 'markup', 0 )
#		column.set_cell_data_func( pix_renderer, self.places_pix_renderer_function, None )
#		column.set_cell_data_func( text_renderer, self.places_text_renderer_function, None )
#		#column.set_alignment( 0.5 )
#		self.list_places.append_column( column )
#
#		#name, icon, path
#		self.store_places = gtk.ListStore( str, str, str )
#		self.list_places.set_model( self.store_places )
#		self.list_places.get_selection().set_select_function( self.places_select_function, self.store_places )
#
#		#setup folder view
#		self.list_folder_view = self.glade.get_widget( 'list_folder_view' )
#
#		pix_renderer = gtk.CellRendererPixbuf()
#		text_renderer = gtk.CellRendererText()
#
#		column = gtk.TreeViewColumn( _('Name') )
#		column.pack_start( pix_renderer, False )
#		column.pack_end( text_renderer, True )
#		column.add_attribute( pix_renderer, 'icon-name', 2 )
#		column.add_attribute( text_renderer, 'markup', 0 )
#		column.set_expand( True )
#		column.set_sizing( gtk.TREE_VIEW_COLUMN_AUTOSIZE )
#		column.set_sort_column_id( 0 )
#		self.list_folder_view.append_column( column )
#
#		text_renderer = gtk.CellRendererText()
#		column = gtk.TreeViewColumn( _('Size') )
#		column.pack_end( text_renderer, True )
#		column.add_attribute( text_renderer, 'markup', 4 )
#		column.set_sort_column_id( 1 )
#		self.list_folder_view.append_column( column )
#
#		text_renderer = gtk.CellRendererText()
#		column = gtk.TreeViewColumn( _('Date') )
#		column.pack_end( text_renderer, True )
#		column.add_attribute( text_renderer, 'markup', 5 )
#		column.set_sort_column_id( 2 )
#		self.list_folder_view.append_column( column )
#
#		# display name, relative path, icon_name, type (0 - directory, 1 - file), size (str), date, size (int)
#		self.store_folder_view = gtk.ListStore( str, str, str, int, str, str, int )
#		self.store_folder_view.set_sort_func( 0, self.sort_folder_view_by_column, 0 ) #name
#		self.store_folder_view.set_sort_func( 1, self.sort_folder_view_by_column, 6 ) #size
#		self.store_folder_view.set_sort_func( 2, self.sort_folder_view_by_column, 5 )	#date
#		self.store_folder_view.set_sort_column_id( 0, gtk.SORT_ASCENDING )
#
#		self.list_folder_view.set_model( self.store_folder_view )
#
#		#setup time line view
#		self.list_time_line = self.glade.get_widget( 'list_time_line' )
#
#		text_renderer = gtk.CellRendererText()
#		column = gtk.TreeViewColumn( _('Timeline'), text_renderer, markup = 0 )
#		column.set_cell_data_func( text_renderer, self.places_text_renderer_function, None )
#		self.list_time_line.append_column( column )
#
#		#display name, id
#		self.store_time_line = gtk.ListStore( str, str )
#		self.list_time_line.set_model( self.store_time_line )
#		self.list_time_line.get_selection().set_select_function( self.places_select_function, self.store_time_line )
#		self.update_time_line = False
#
#		#calculate specialBackgroundColor
#		style = self.list_time_line.get_style()
#		bg1 = style.bg[gtk.STATE_NORMAL]
#		bg2 = style.bg[gtk.STATE_SELECTED]
#		self.special_background_color = gtk.gdk.Color( (2 * bg1.red + bg2.red) / 3, (2 * bg1.green + bg2.green) / 3,(2 * bg1.blue + bg2.blue) / 3 ).to_string()
#
#		#restore size & position
#		main_window_x = self.config.get_int_value( 'gnome.main_window.x', -1 )
#		main_window_y = self.config.get_int_value( 'gnome.main_window.y', -1 )
#		if main_window_x >= 0 and main_window_y >= 0:
#			self.window.move( main_window_x, main_window_y )
#
#		main_window_width = self.config.get_int_value( 'gnome.main_window.width', -1 )
#		main_window_height = self.config.get_int_value( 'gnome.main_window.height', -1 )
#		if main_window_width > 0 and main_window_height > 0:
#			self.window.resize( main_window_width, main_window_height )
#
#		main_window_hpaned1 = self.config.get_int_value( 'gnome.main_window.hpaned1', -1 )
#		main_window_hpaned2 = self.config.get_int_value( 'gnome.main_window.hpaned2', -1 )
#		if main_window_hpaned1 > 0 and main_window_hpaned2 > 0:
#			self.glade.get_widget('hpaned1').set_position( main_window_hpaned1 )
#			self.glade.get_widget('hpaned2').set_position( main_window_hpaned2 )
#
#		#prepare popup menu ids
#		gtk.stock_add( 
#				[ ('backintime.open', _('Open'), 0, 0, 'backintime' ),
#				  ('backintime.copy', _('Copy'), 0, 0, 'backintime' ),
#				  ('backintime.snapshots', _('Snapshots'), 0, 0, 'backintime' ),
#				  ('backintime.diff', _('Diff'), 0, 0, 'backintime' ),
#				  ('backintime.restore', _('Restore'), 0, 0, 'backintime' ) ] )
#
#		#show main window
#		self.window.show()
#
#		gobject.timeout_add( 100, self.on_init )
#		gobject.timeout_add( 1000, self.raise_application )
#
#	def sort_folder_view_by_column( self, treemodel, iter1, iter2, column ):
#		if 0 == column:
#			ascending = 1
#			if self.store_folder_view.get_sort_column_id()[1] != gtk.SORT_ASCENDING:
#				ascending = -1
#
#			type1 = self.store_folder_view.get_value( iter1, 3 )
#			type2 = self.store_folder_view.get_value( iter2, 3 )
#
#			if type1 == 0 and type2 != 0:
#				return -1 * ascending
#
#			if type1 != 0 and type2 == 0:
#				return 1 * ascending
#
#		data1 = self.store_folder_view.get_value( iter1, column )
#		data2 = self.store_folder_view.get_value( iter2, column )
#
#		if type(data1) is str:
#			data1 = data1.upper()
#
#		if type(data2) is str:
#			data2 = data2.upper()
#
#		#print "sort_folder_view_by_column: " + str( data1 ) + " - " + str( data2 )
#
#		if data1 < data2:
#			return -1
#
#		if data1 > data2:
#			return 1
#
#		return 0
#
#	def show_settings_dialog_( self ):
#		if self.settings_dialog is None:
#			self.settings_dialog = gnomesettingsdialog.SettingsDialog( self.config, self.glade )
#		self.settings_dialog.run()
#
#	def on_init( self ):
#		if not self.config.is_configured():
#			self.show_settings_dialog_()
#
#			if not self.config.is_configured():
#				gtk.main_quit()
#				return False
#
#		self.update_all( True )
#
#		self.force_wait_lock = False
#		self.update_backup_info()
#		gobject.timeout_add( 1000, self.update_backup_info )
#		return False

	def show_not_implemented( self ):
		QMessageBox.warning( self, "Warning", "Not implemented !!!" )

	def closeEvent( self, event ):
		self.config.set_str_value( 'kde4.last_path', self.path )

		self.config.set_int_value( 'kde4.main_window.x', self.x() )
		self.config.set_int_value( 'kde4.main_window.y', self.y() )
		self.config.set_int_value( 'kde4.main_window.width', self.width() )
		self.config.set_int_value( 'kde4.main_window.height', self.height() )

		sizes = self.main_splitter.sizes()
		self.config.set_int_value( 'kde4.main_window.main_splitter_left_w', sizes[0] )
		self.config.set_int_value( 'kde4.main_window.main_splitter_right_w', sizes[1] )
	
		sizes = self.second_splitter.sizes()
		self.config.set_int_value( 'kde4.main_window.second_splitter_left_w', sizes[0] )
		self.config.set_int_value( 'kde4.main_window.second_splitter_right_w', sizes[1] )

		self.config.set_int_value( 'kde4.main_window.files_view.name_width', self.list_files_view.header().sectionSize( 0 ) )
		self.config.set_int_value( 'kde4.main_window.files_view.size_width', self.list_files_view.header().sectionSize( 1 ) )
		self.config.set_int_value( 'kde4.main_window.files_view.date_width', self.list_files_view.header().sectionSize( 2 ) )

		self.config.save()

		event.accept()

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

#	def update_all( self, init ):
#		#fill lists
#		selected_file = None
#		show_snapshots = False
#		if init:
#			self.folder_path, selected_file, show_snapshots = self.get_startup_folder_and_file()
#		self.snapshot_id = '/'
#		self.snapshots_list = []
#
#		self.fill_places()
#		self.fill_time_line( False )
#		self.update_folder_view( 1, selected_file, show_snapshots )
#
#	def places_pix_renderer_function( self, column, renderer, model, iter, user_data ):
#		if len( model.get_value( iter, 1 ) ) == 0:
#			renderer.set_property( 'visible', False )
#		else:
#			renderer.set_property( 'visible', True )
#
#	def places_text_renderer_function( self, column, renderer, model, iter, user_data ):
#		if len( model.get_value( iter, 1 ) ) == 0:
#			renderer.set_property( 'cell-background-set', True )
#			renderer.set_property( 'cell-background', self.special_background_color )
#		else:
#			renderer.set_property( 'cell-background-set', False )
#
#	def places_select_function( self, info, store ):
#		if len( store.get_value( store.get_iter( info[0] ), 1 ) ) == 0:
#			return False
#		return True
#
#	def raise_application( self ):
#		raise_cmd = self.app_instance.raise_command()
#		if raise_cmd is None:
#			return True
#
#		print "Raise cmd: " + raise_cmd
#		self.window.present_with_time( int(time.time()) )
#		self.window.window.focus()
#		#self.window.present()
#
#		if len( raise_cmd ) == 0:
#			return True
#
#		print "Check if the main window is the only top level visible window"
#		for window in gtk.window_list_toplevels():
#			if window.get_property( 'visible' ):
#				if window != self.window:
#					print "Failed"
#					return True
#
#		print "OK"
#
#		folder_and_file = self.get_cmd_startup_folder_and_file( raise_cmd )
#		if folder_and_file is None:
#			return True
#
#		folder_path, file_name, show_snapshots = folder_and_file
#
#		#select now
#		self.snapshot_id = '/'
#		self.list_time_line.get_selection().select_iter( self.store_time_line.get_iter_first() )
#
#		#select the specified file
#		self.folder_path = folder_path
#		self.update_folder_view( 1, file_name, show_snapshots )
#
#		return True

	def update_take_snapshot( self, force_wait_lock = False ):
		if force_wait_lock:
			self.force_wait_lock_counter = 10
		
		busy = self.snapshots.is_busy()
		if busy:
			self.force_wait_lock_counter = 0

		if self.force_wait_lock_counter > 0:
			self.force_wait_lock_counter = self.force_wait_lock_counter - 1

		fake_busy = busy or self.force_wait_lock_counter > 0

		if fake_busy:
			if self.btn_take_snapshot.isEnabled():
				self.btn_take_snapshot.setEnabled( False )
				self.statusBar().showMessage( _('Working ...') )
		elif not self.btn_take_snapshot.isEnabled():
			self.btn_take_snapshot.setEnabled( True )
			
			snapshots_list = self.snapshots.get_snapshots_list()

			if snapshots_list != self.snapshots_list:
				self.snapshots_list = snapshots_list
				self.update_time_line( False )
			 	self.statusBar().showMessage( _('Done') )
			else:
				self.statusBar().showMessage( _('Done, no backup needed') )

	def on_list_places_current_item_changed( self, item, previous ):
		if item is None:
			return

		path = str( item.text( 1 ) )
		if len( path ) == 0:
			return

		if path == self.path:
			return

		self.path = path
		self.update_files_view( 3 )

	def add_place( self, name, path, icon ):
		item = QTreeWidgetItem( self.list_places )

		if len( icon ) > 0:
			item.setIcon( 0, KIcon( icon ) )

		item.setText( 0, name )
		item.setText( 1, path )

		if len( path ) == 0:
			font = item.font( 0 )
			font.setWeight( QFont.Bold )
			item.setFont( 0, font )
			item.setFlags( Qt.NoItemFlags )

		self.list_places.addTopLevelItem( item )
		return item

	def update_places( self ):
		self.list_places.clear()
		self.add_place( _('Global'), '', '' )
		self.add_place( _('Root'), '/', 'computer' )
		self.add_place( _('Home'), os.path.expanduser( '~' ), 'user-home' )

		#add backup folders
		include_folders = self.config.get_include_folders()
		if len( include_folders ) > 0:
			self.add_place( _('Backup Directories'), '', '' )
			for folder in include_folders:
				self.add_place( folder, folder, 'document-save' )

	def on_list_time_line_current_item_changed( self, item, previous ):
		if item is None:
			return

		snapshot_id = str( item.text( 1 ) ) 
		if len( snapshot_id ) == 0:
			#self.list_time_line.setCurrentItem( previous )
			return

		if snapshot_id == self.snapshot_id:
			return

		self.snapshot_id = snapshot_id
		self.update_files_view( 2 )

	def add_time_line( self, snapshot_name, snapshot_id ):
		item = QTreeWidgetItem( self.list_time_line )

		item.setText( 0, snapshot_name )
		item.setText( 1, snapshot_id )

		if len( snapshot_id ) == 0:
			font = item.font( 0 )
			font.setWeight( QFont.Bold )
			item.setFont( 0, font )
			item.setFlags( Qt.NoItemFlags )

		self.list_time_line.addTopLevelItem( item )
		return item

	def update_time_line( self, get_snapshots_list = True ):
		self.list_time_line.clear()
		self.add_time_line( self.snapshots.get_snapshot_display_name( '/' ), '/' )

		if get_snapshots_list:
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
				self.add_time_line( group[0], '' );
				for snapshot_id in group[2]:
					list_item = self.add_time_line( self.snapshots.get_snapshot_display_name( snapshot_id ), snapshot_id )
					if snapshot_id == self.snapshot_id:
						self.list_time_line.setCurrentItem( list_item )

		if self.list_time_line.currentItem() is None and self.list_time_line.topLevelItemCount() > 0:
			self.list_time_line.setCurrentItem( self.list_time_line.topLevelItem( 0 ) )
			if self.snapshot_id != '/':
				self.snapshot_id = '/'
				self.update_files_view( 2 )

#		#select previous item
#		iter = self.store_time_line.get_iter_first()
#		while not iter is None:
#			if current_selection == self.store_time_line.get_value( iter, 1 ):
#				break
#			iter = self.store_time_line.iter_next( iter )
#
#		changed = False
#		if iter is None:
#			changed = True
#			iter = self.store_time_line.get_iter_first()
#
#		self.list_time_line.get_selection().select_iter( iter )
#
#		if changed and update_folder_view:
#			self.update_folder_view( 2 )
#
#	def on_close( self, *params ):
#		main_window_x, main_window_y = self.window.get_position()
#		main_window_width, main_window_height = self.window.get_size()
#		main_window_hpaned1 = self.glade.get_widget('hpaned1').get_position()
#		main_window_hpaned2 = self.glade.get_widget('hpaned2').get_position()
#
#		self.config.set_int_value( 'gnome.main_window.x', main_window_x )
#		self.config.set_int_value( 'gnome.main_window.y', main_window_y )
#		self.config.set_int_value( 'gnome.main_window.width', main_window_width )
#		self.config.set_int_value( 'gnome.main_window.height', main_window_height )
#		self.config.set_int_value( 'gnome.main_window.hpaned1', main_window_hpaned1 )
#		self.config.set_int_value( 'gnome.main_window.hpaned2', main_window_hpaned2 )
#		self.config.set_str_value( 'gnome.last_path', self.folder_path )
#		self.config.set_bool_value( 'gnome.show_hidden_files', self.show_hidden_files )
#
#		self.config.save()
#		self.window.destroy()
#		return True
#
#	def on_list_time_line_cursor_changed( self, list ):
#		if list.get_selection().path_is_selected( list.get_cursor()[ 0 ] ):
#			self.update_folder_view( 2 )
#
#	def on_list_places_cursor_changed( self, list ):
#		if list.get_selection().path_is_selected( list.get_cursor()[ 0 ] ):
#			iter = list.get_selection().get_selected()[1]
#			folder_path = self.store_places.get_value( iter, 1 )
#			if folder_path != self.folder_path:
#				self.folder_path = folder_path
#				self.update_folder_view( 0 )
#
#	def on_list_folder_view_drag_data_get( self, widget, drag_context, selection_data, info, timestamp, user_param1 = None ):
#		iter = self.list_folder_view.get_selection().get_selected()[1]
#		if not iter is None:
#			path = self.store_folder_view.get_value( iter, 1 )
#			path = self.snapshots.get_snapshot_path_to( self.snapshot_id, path )
#			path = gnomevfs.escape_path_string( path )
#			selection_data.set_uris( [ 'file://' + path ] )
#
#	def on_list_folder_view_button_press_event( self, list, event ):
#		if event.button != 3:
#			return
#
#		if len( self.store_folder_view ) <= 0:
#			return
#
#		path = self.list_folder_view.get_path_at_pos( int( event.x ), int( event.y ) )
#		if path is None:
#			return
#		path = path[0]
#	
#		self.list_folder_view.get_selection().select_path( path )
#		self.show_folder_view_menu_popup( self.list_folder_view, event.button, event.time )
#
#	def on_list_folder_view_popup_menu( self, list ):
#		self.show_folder_view_menu_popup( list, 1, gtk.get_current_event_time() )
#
#	def show_folder_view_menu_popup( self, list, button, time ):
#		iter = list.get_selection().get_selected()[1]
#		if iter is None:
#			return
#
#		#print "popup-menu"
#		self.popup_menu = gtk.Menu()
#
#		menu_item = gtk.ImageMenuItem( 'backintime.open' )
#		menu_item.set_image( gtk.image_new_from_icon_name( self.store_folder_view.get_value( iter, 2 ), gtk.ICON_SIZE_MENU ) )
#		menu_item.connect( 'activate', self.on_list_folder_view_open_item )
#		self.popup_menu.append( menu_item )
#
#		self.popup_menu.append( gtk.SeparatorMenuItem() )
#
#		menu_item = gtk.ImageMenuItem( 'backintime.copy' )
#		menu_item.set_image( gtk.image_new_from_stock( gtk.STOCK_COPY, gtk.ICON_SIZE_MENU ) )
#		menu_item.connect( 'activate', self.on_list_folder_view_copy_item )
#		self.popup_menu.append( menu_item )
#
#		menu_item = gtk.ImageMenuItem( 'backintime.snapshots' )
#		menu_item.set_image( gtk.image_new_from_stock( gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU ) )
#		menu_item.connect( 'activate', self.on_list_folder_view_snapshots_item )
#		self.popup_menu.append( menu_item )
#
#		if len( self.snapshot_id ) > 1:
#			menu_item = gtk.ImageMenuItem( 'backintime.restore' )
#			menu_item.set_image( gtk.image_new_from_stock( gtk.STOCK_UNDELETE, gtk.ICON_SIZE_MENU ) )
#			menu_item.connect( 'activate', self.on_list_folder_view_restore_item )
#			self.popup_menu.append( menu_item )
#
#		self.popup_menu.show_all()
#		self.popup_menu.popup( None, None, None, button, time )
#
#	def on_list_folder_view_restore_item( self, widget, data = None ):
#		self.on_btn_restore_clicked( self.glade.get_widget( 'btn_restore' ) )
#
#	def on_list_folder_view_copy_item( self, widget, data = None ):
#		self.on_btn_copy_clicked( self.glade.get_widget( 'btn_copy' ) )
#
#	def on_list_folder_view_snapshots_item( self, widget, data = None ):
#		self.on_btn_snapshots_clicked( self.glade.get_widget( 'btn_snapshots' ) )
#
#	def on_list_folder_view_open_item( self, widget, data = None ):
#		iter = self.list_folder_view.get_selection().get_selected()[1]
#		if iter is None:
#			return
#
#		path = self.store_folder_view.get_value( iter, 1 )
#		path = self.snapshots.get_snapshot_path_to( self.snapshot_id, path )
#		cmd = "gnome-open \"%s\" &" % path
#		print cmd
#		os.system( cmd )
#
#	def on_list_folder_view_row_activated( self, list, path, column ):
#		iter = list.get_selection().get_selected()[1]
#		path = self.store_folder_view.get_value( iter, 1 )
#
#		#directory
#		if 0 == self.store_folder_view.get_value( iter, 3 ):
#			self.folder_path = path
#			self.update_folder_view( 1 )
#			return
#
#		#file
#		path = self.snapshots.get_snapshot_path_to( self.snapshot_id, path )
#		cmd = "gnome-open \"%s\" &" % path
#		print cmd
#		os.system( cmd )
#
#	def on_btn_fodler_up_clicked( self, button ):
#		if len( self.folder_path ) <= 1:
#			return
#
#		index = self.folder_path.rfind( '/' )
#		if index < 1:
#			parent_path = "/"
#		else:
#			parent_path = self.folder_path[ : index ]
#
#		self.folder_path = parent_path
#		self.update_folder_view( 1 )
#
#	def on_btn_restore_clicked( self, button ):
#		iter = self.list_folder_view.get_selection().get_selected()[1]
#		if not iter is None:
#			button.set_sensitive( False )
#			gobject.timeout_add( 100, self.restore_ )
#	
#	def on_btn_copy_clicked( self, button ):
#		iter = self.list_folder_view.get_selection().get_selected()[1]
#		if iter is None:
#			return
#
#		path = self.store_folder_view.get_value( iter, 1 )
#		path = self.snapshots.get_snapshot_path_to( self.snapshot_id, path )
#
#		gnomeclipboardtools.clipboard_copy_path( path )
#
#	def on_btn_hidden_files_toggled( self, button ):
#		if self.folder_path is None:
#			return
#
#		self.show_hidden_files = button.get_active()
#		self.update_folder_view( 0 )
#
#	def on_btn_snapshots_clicked( self, button ):
#		iter = self.list_folder_view.get_selection().get_selected()[1]
#		if iter is None:
#			return
#
#		path = self.store_folder_view.get_value( iter, 1 )
#		icon_name = self.store_folder_view.get_value( iter, 2 )
#
#		if self.snapshots_dialog is None:
#			self.snapshots_dialog = gnomesnapshotsdialog.SnapshotsDialog( self.snapshots, self.glade )
#
#		retVal = self.snapshots_dialog.run( path, self.snapshots_list, self.snapshot_id, icon_name )
#		
#		#select the specified file
#		if not retVal is None:
#			iter = self.store_time_line.get_iter_first()
#			while not iter is None:
#				snapshot_id = self.store_time_line.get_value( iter, 1 )
#				if snapshot_id == retVal:
#					break
#				iter = self.store_time_line.iter_next( iter )
#
#			if not iter is None:
#				self.list_time_line.get_selection().select_iter( iter )
#				self.update_folder_view( 2 )
#
#	def restore_( self ):
#		iter = self.list_folder_view.get_selection().get_selected()[1]
#		if not iter is None:
#			self.snapshots.restore( self.snapshot_id, self.store_folder_view.get_value( iter, 1 ) )
#
#		self.glade.get_widget( 'btn_restore' ).set_sensitive( True )
#		return False
#
#	def on_btn_about_clicked( self, button ):
#		if self.about_dialog is None:
#			self.about_dialog = AboutDialog( self.config, self.glade )
#		self.about_dialog.run()
#
#	def on_help( self ):
#		gnome.help_display('backintime')
#
#	def on_btn_help_clicked( self, button ):
#		self.on_help()
#
#	def on_key_release_event( self, widget, event ):
#		if 'F1' == gtk.gdk.keyval_name( event.keyval ) and ( event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK) ) == 0:
#			self.on_help()
#
#	def on_btn_settings_clicked( self, button, ):
#		snapshots_path = self.config.get_snapshots_path()
#		include_folders = self.config.get_include_folders()
#
#		self.show_settings_dialog_()
#
#		if not self.config.is_configured():
#			gtk.main_quit()
#		else:
#			if snapshots_path != self.config.get_snapshots_path() or include_folders != self.config.get_include_folders():
#				self.update_all( False )
#
#	def on_btn_snapshot_name_clicked( self, button ):
#		iter = self.list_time_line.get_selection().get_selected()[1]
#		if iter is None:
#			return
#
#		snapshot_id = self.store_time_line.get_value( iter, 1 )
#		if len( snapshot_id ) <= 1:
#			return
#
#		if self.snapshot_name_dialog is None:
#			self.snapshot_name_dialog = gnomesnapshotnamedialog.SnapshotNameDialog( self.snapshots, self.glade )
#
#		if self.snapshot_name_dialog.run( snapshot_id ):
#			self.store_time_line.set_value( iter, 0, gnomesnapshotstools.get_snapshot_display_markup( self.snapshots, snapshot_id ) )
#
#	def on_btn_remove_snapshot_clicked( self, button ):
#		iter = self.list_time_line.get_selection().get_selected()[1]
#		if iter is None:
#			return
#
#		snapshot_id = self.store_time_line.get_value( iter, 1 )
#		if len( snapshot_id ) <= 1:
#			return
#
#		if gtk.RESPONSE_YES == gnomemessagebox.show_question( self.window, self.config, _( "Are you sure you want to remove the snapshot:\n<b>%s</b>" ) % self.snapshots.get_snapshot_display_name( snapshot_id ) ):
#			print "Remove Snapshot: %s" % snapshot_id
#			self.snapshots.remove_snapshot( snapshot_id )
#			self.fill_time_line()
#
#	def on_btn_backup_clicked( self, button ):
#		button.set_sensitive( False )
#		self.updatetime_line = True
#		
#		if self.snapshots.is_busy():
#			self.update_backup_info()
#			return
#
#		#backup.backup()
#		app = 'backintime'
#		if os.path.isfile( './backintime' ):
#			app = './backintime'
#		cmd = "nice -n 19 %s --backup &" % app
#		os.system( cmd )
#
#		self.update_backup_info( True )

	def on_btn_take_snapshot_clicked( self ):
		app = 'backintime'
		if os.path.isfile( './backintime' ):
			app = './backintime'
		cmd = "nice -n 19 %s --backup &" % app
		os.system( cmd )

		self.update_take_snapshot( True )

	def on_btn_show_hidden_files_toggled( self, checked ):
		self.show_hidden_files = checked
		self.update_files_view( 1 )

	def on_btn_folder_up_clicked( self ):
		if len( self.path ) <= 1:
			return

		path = os.path.dirname( self.path )
		if self.path == path:
			return

		self.path = path
		self.update_files_view( 0 )

	def on_list_files_view_item_activated( self, item, column ):
		if item is None:
			return

		rel_path = os.path.join( self.path, self.files_view_get_name( item ) )

		if self.files_view_get_type( item ) ==  0:
			self.path = rel_path
			self.update_files_view( 0 )
		else:
			full_path = self.snapshots.get_snapshot_path_to( self.snapshot_id, rel_path )
			os.system( "kde-open \"%s\" &" % full_path )

	def sort_by_name( self, item1, item2 ):
		if item1[4] < item2[4]:
			return -1

		if item1[4] > item2[4]:
			return 1

		str1 = item1[0].upper()
		str2 = item2[0].upper()

		if str1 < str2:
			return -1

		if str1 > str2:
			return 1

		return 0

	def files_view_get_name( self, item ):
		return str( item.text( 0 ) )

	def files_view_get_type( self, item ):
		return int( item.text( 4 ) )

	def add_files_view( self, name, size_str, date_str, size_int, type ):
		full_path = self.snapshots.get_snapshot_path_to( self.snapshot_id, os.path.join( self.path, name ) )
		icon = KIcon( KMimeType.iconNameForUrl( KUrl( full_path ) ) )

		item = QTreeWidgetItem( self.list_files_view )

		item.setIcon( 0, icon )
		item.setText( 0, name )
		item.setText( 1, size_str )
		item.setText( 2, date_str )
		item.setText( 3, str( size_int ) )
		item.setText( 4, str( type ) )

		self.list_files_view.addTopLevelItem( item )
		return item

	def update_files_view( self, changed_from, selected_file = None, show_snapshots = False ): #0 - files view change directory, 1 - files view, 2 - time_line, 3 - places
		if 0 == changed_from or 3 == changed_from:
			selected_file = ''

		if 0 == changed_from:
			#update places
			self.list_places.setCurrentItem( None )
			for place_index in xrange( self.list_places.topLevelItemCount() ):
				item = self.list_places.topLevelItem( place_index )
				if self.path == str( item.text( 1 ) ):
					self.list_places.setCurrentItem( item )
					break


		#update folder view
		full_path = self.snapshots.get_snapshot_path_to( self.snapshot_id, self.path )
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
				files.append( [ file, file_size, file_date, file_size_int, 0 ] )
			else:
				files.append( [ file, file_size, file_date, file_size_int, 1 ] )

		#try to keep old selected file
		if selected_file is None:
			item = self.list_files_view.currentItem()
			if not item is None:
				selected_file = item.text( 0 )
			else:
				selected_file = ''

		files.sort( self.sort_by_name )

		#populate the list
		self.list_files_view.clear()

		for item in files:
			list_item = self.add_files_view( item[0], item[1], item[2], item[3], item[4] )
			if selected_file == item[0]:
				self.list_files_view.setCurrentItem( list_item )

		if self.list_files_view.currentItem() is None and len( files ) > 0:
			self.list_files_view.setCurrentItem( self.list_files_view.topLevelItem(0) )

		#show current path
		self.edit_current_path.setText( self.path )

		#update folder_up button state
		self.btn_folder_up.setEnabled( len( self.path ) > 1 )

		#update restore button state
		self.btn_restore.setEnabled( len( self.snapshot_id ) > 1 and len( files ) > 0 )

		#update remove/name snapshot buttons
		self.btn_name_snapshot.setEnabled( len( self.snapshot_id ) > 1 )
		self.btn_remove_snapshot.setEnabled( len( self.snapshot_id ) > 1 )

		#update copy button state
		self.btn_copy.setEnabled( len( files ) > 0 )

		#update snapshots button state
		self.btn_snapshots.setEnabled( len( files ) > 0 )

#		#show snapshots
#		if show_snapshots:
#			self.on_btn_snapshots_clicked( None )


def take_snapshot( cfg ):
	logger.openlog()
	snapshots.Snapshots( cfg ).take_snapshot()
	logger.closelog()


if __name__ == '__main__':
	cfg = config.Config()
	backintime.print_version( cfg )

	for arg in sys.argv[ 1 : ]:
		if arg == '--backup' or arg == '-b':
			take_snapshot( cfg )
			sys.exit(0)

		if arg == '--version' or arg == '-v':
			sys.exit(0)

		if arg == '--help' or arg == '-h':
			backintime.print_help( cfg )
			sys.exit(0)

		if arg == '--snapshots' or arg == '-s':
			continue

		if arg[0] == '-':
			print "Ignore option: %s" % arg
			continue

	raise_cmd = ''
	if len( sys.argv ) > 1:
		raise_cmd = '\n'.join( sys.argv[ 1 : ] )

	app_instance = guiapplicationinstance.GUIApplicationInstance( cfg.get_app_instance_file(), raise_cmd )

	logger.openlog()
	#qt_app = QApplication(sys.argv)
	kdeAboutData = KAboutData( 'backintime', 'backintime', ki18n( cfg.APP_NAME ), cfg.VERSION, ki18n( '' ), KAboutData.License_GPL_V2, ki18n( '' ), ki18n( '' ), 'le-web.org/back-in-time', 'dab@le-web.org' )
	KCmdLineArgs.init( sys.argv, kdeAboutData )
	app = KApplication()
	main_window = MainWindow( cfg, app_instance )
	main_window.show()
	app.exec_()
	logger.closelog()

	app_instance.exit_application()

