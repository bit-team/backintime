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
import threading

import backintime
import config
import logger
import snapshots
import guiapplicationinstance

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *

import kde4tools
import kde4settingsdialog


_=gettext.gettext


class MainWindow( KMainWindow ):
	def __init__( self, config, app_instance, kapp, kaboutdata ):
		KMainWindow.__init__( self )

		self.config = config
		self.app_instance = app_instance
		self.kapp = kapp
		self.kaboutdata = kaboutdata
		self.snapshots = snapshots.Snapshots( config )

		self.main_toolbar = KToolBar( self )
		self.main_toolbar.setFloatable( False )

		self.btn_take_snapshot = self.main_toolbar.addAction( KIcon( 'document-save' ), '' )
		self.btn_take_snapshot.setToolTip( QString.fromUtf8( _('Take snapshot') ) )

		self.btn_name_snapshot = self.main_toolbar.addAction( KIcon( 'edit-rename' ), '' )
		self.btn_name_snapshot.setToolTip( QString.fromUtf8( _('Snapshot Name') ) )

		self.btn_remove_snapshot = self.main_toolbar.addAction( KIcon( 'edit-delete' ), '' )
		self.btn_remove_snapshot.setToolTip( QString.fromUtf8( _('Remove Snapshot') ) )
	
		self.main_toolbar.addSeparator()

		self.btn_settings = self.main_toolbar.addAction( KIcon( 'configure' ), '' )
		self.btn_settings.setToolTip( QString.fromUtf8( _('Settings') ) )

		self.main_toolbar.addSeparator()

		self.btn_about = self.main_toolbar.addAction( KIcon( 'help-about' ), '' )
		self.btn_about.setToolTip( QString.fromUtf8( _('About') ) )

		self.btn_help = self.main_toolbar.addAction( KIcon( 'help-contents' ), '' )
		self.btn_help.setToolTip( QString.fromUtf8( _('Help') ) )

		self.main_toolbar.addSeparator()

		self.btn_quit = self.main_toolbar.addAction( KIcon( 'application-exit' ), '' )
		self.btn_quit.setToolTip( QString.fromUtf8( _('Exit') ) )

		self.files_view_toolbar = KToolBar( self )
		self.files_view_toolbar.setFloatable( False )

		self.btn_folder_up = self.files_view_toolbar.addAction( KIcon( 'go-up' ), '' )
		self.btn_folder_up.setToolTip( QString.fromUtf8( _('Up') ) )

		self.edit_current_path = QLineEdit( self )
		self.edit_current_path.setReadOnly( True )
		self.files_view_toolbar.addWidget( self.edit_current_path )

		#show hidden files
		self.show_hidden_files = self.config.get_bool_value( 'kde4.show_hidden_files', False )

		self.btn_show_hidden_files = self.files_view_toolbar.addAction( KIcon( 'list-add' ), '' )
		self.btn_show_hidden_files.setCheckable( True )
		self.btn_show_hidden_files.setChecked( self.show_hidden_files )
		self.btn_show_hidden_files.setToolTip( QString.fromUtf8( _('Show hidden files') ) )

		self.files_view_toolbar.addSeparator()

		self.btn_restore = self.files_view_toolbar.addAction( KIcon( 'document-revert' ), '' )
		self.btn_restore.setToolTip( QString.fromUtf8( _('Restore') ) )

		self.btn_copy = self.files_view_toolbar.addAction( KIcon( 'edit-copy' ), '' )
		self.btn_copy.setToolTip( QString.fromUtf8( _('Copy') ) )

		self.btn_snapshots = self.files_view_toolbar.addAction( KIcon( 'view-list-details' ), '' )
		self.btn_snapshots.setToolTip( QString.fromUtf8( _('Snapshots') ) )

		self.list_time_line = QTreeWidget( self )
		self.list_time_line.setHeaderLabel( QString.fromUtf8( _('Timeline') ) )
		self.list_time_line.setRootIsDecorated( False )

		self.list_places = QTreeWidget( self )
		self.list_places.setHeaderLabel( QString.fromUtf8( _('Places') ) )
		self.list_places.setRootIsDecorated( False )

		self.list_files_view = QTreeWidget( self )
		self.list_files_view.setHeaderLabels( [QString.fromUtf8( _('Name') ), QString.fromUtf8( _('Size') ), QString.fromUtf8( _('Date') )] )
		self.list_files_view.setRootIsDecorated( False )
		self.list_files_view.setAlternatingRowColors( True )

		self.second_splitter = QSplitter( self )
		self.second_splitter.setOrientation( Qt.Horizontal )
		self.second_splitter.addWidget( self.list_time_line )
		self.second_splitter.addWidget( self.list_places )

		left_layout = QVBoxLayout()
		left_layout.addWidget( self.main_toolbar )
		left_layout.addWidget( self.second_splitter )
		left, top, right, bottom = left_layout.getContentsMargins()
		left_layout.setContentsMargins( left, top, 0, bottom )

		left_widget = QWidget( self )
		left_widget.setLayout( left_layout )

		right_layout = QVBoxLayout()
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
		
		self.statusBar().showMessage( QString.fromUtf8( _('Done') ) )

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

		self.text_validator = QRegExpValidator( QRegExp( '.*' ), self )

		#force settingdialog if it is not configured
		if not cfg.is_configured():
			kde4settingsdialog.SettingsDialog( self ).exec_()

		if not cfg.is_configured():
			return

		#populate lists
		self.update_time_line()
		self.update_places()
		self.update_files_view( 0 )

		self.list_files_view.setFocus()

		self.update_snapshot_actions()

		QObject.connect( self.list_time_line, SIGNAL('currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)'), self.on_list_time_line_current_item_changed )
		QObject.connect( self.list_places, SIGNAL('currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)'), self.on_list_places_current_item_changed )
		QObject.connect( self.list_files_view, SIGNAL('itemActivated(QTreeWidgetItem*,int)'), self.on_list_files_view_item_activated )

		QObject.connect( self.btn_take_snapshot, SIGNAL('triggered()'), self.on_btn_take_snapshot_clicked )
		QObject.connect( self.btn_name_snapshot, SIGNAL('triggered()'), self.on_btn_name_snapshot_clicked )
		QObject.connect( self.btn_remove_snapshot, SIGNAL('triggered()'), self.on_btn_remove_snapshot_clicked )
		QObject.connect( self.btn_settings, SIGNAL('triggered()'), self.on_btn_settings_clicked )
		QObject.connect( self.btn_about, SIGNAL('triggered()'), self.on_btn_about_clicked )
		QObject.connect( self.btn_help, SIGNAL('triggered()'), self.show_not_implemented )
		QObject.connect( self.btn_quit, SIGNAL('triggered()'), self.close )
		QObject.connect( self.btn_folder_up, SIGNAL('triggered()'), self.on_btn_folder_up_clicked )
		QObject.connect( self.btn_show_hidden_files, SIGNAL('toggled(bool)'), self.on_btn_show_hidden_files_toggled )
		QObject.connect( self.btn_restore, SIGNAL('triggered()'), self.on_btn_restore_clicked )
		QObject.connect( self.btn_copy, SIGNAL('triggered()'), self.show_not_implemented )
		QObject.connect( self.btn_snapshots, SIGNAL('triggered()'), self.show_not_implemented )

		self.force_wait_lock_counter = 0
	
		self.timer_raise_application = QTimer( self )
		self.timer_raise_application.setInterval( 1000 )
		self.timer_raise_application.setSingleShot( False )
		QObject.connect( self.timer_raise_application, SIGNAL('timeout()'), self.raise_application )
		self.timer_raise_application.start()

		self.timer_update_take_snapshot = QTimer( self )
		self.timer_update_take_snapshot.setInterval( 1000 )
		self.timer_update_take_snapshot.setSingleShot( False )
		QObject.connect( self.timer_update_take_snapshot, SIGNAL('timeout()'), self.update_take_snapshot )
		self.timer_update_take_snapshot.start()

	def show_not_implemented( self ):
		KMessageBox.error( self, "Not implemented !!!" )

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

	def raise_application( self ):
		raise_cmd = self.app_instance.raise_command()
		if raise_cmd is None:
			return
		
		print "Raise cmd: " + raise_cmd
		self.kapp.alert( self )

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
				self.statusBar().showMessage( QString.fromUtf8( _('Working ...') ) )
		elif not self.btn_take_snapshot.isEnabled():
			self.btn_take_snapshot.setEnabled( True )
			
			snapshots_list = self.snapshots.get_snapshots_list()

			if snapshots_list != self.snapshots_list:
				self.snapshots_list = snapshots_list
				self.update_time_line( False )
			 	self.statusBar().showMessage( QString.fromUtf8( _('Done') ) )
			else:
				self.statusBar().showMessage( QString.fromUtf8( _('Done, no backup needed') ) )

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
			#item.setFlags( Qt.NoItemFlags )
			item.setFlags( Qt.ItemIsEnabled )
			item.setBackgroundColor( 0, QColor( 196, 196, 196 ) )

		self.list_places.addTopLevelItem( item )

		if path == self.path:
			self.list_places.setCurrentItem( item )

		return item

	def update_places( self ):
		self.list_places.clear()
		self.add_place( QString.fromUtf8( _('Global') ), '', '' )
		self.add_place( QString.fromUtf8( _('Root') ), '/', 'computer' )
		self.add_place( QString.fromUtf8( _('Home') ), os.path.expanduser( '~' ), 'user-home' )

		#add backup folders
		include_folders = self.config.get_include_folders()
		if len( include_folders ) > 0:
			self.add_place( QString.fromUtf8( _('Backup Directories') ), '', '' )
			for folder in include_folders:
				self.add_place( folder, folder, 'document-save' )

	def update_snapshot_actions( self ):
		enabled = False

		item = self.list_time_line.currentItem()
		if not item is None:
			if len( self.time_line_get_snapshot_id( item ) ) > 1:
				enabled = True

		#update remove/name snapshot buttons
		self.btn_name_snapshot.setEnabled( enabled )
		self.btn_remove_snapshot.setEnabled( enabled )

	def on_list_time_line_current_item_changed( self, item, previous ):
		self.update_snapshot_actions()

		if item is None:
			return

		snapshot_id = self.time_line_get_snapshot_id( item )
		if len( snapshot_id ) == 0:
			#self.list_time_line.setCurrentItem( previous )
			return

		if snapshot_id == self.snapshot_id:
			return

		self.snapshot_id = snapshot_id
		self.update_files_view( 2 )

	def time_line_get_snapshot_id( self, item ):
		return str( item.text( 1 ) ) 

	def time_line_update_snapshot_name( self, item ):
		snapshot_id = self.time_line_get_snapshot_id( item )
		if len( snapshot_id ) > 0:
			item.setText( 0, self.snapshots.get_snapshot_display_name( snapshot_id ) )

	def add_time_line( self, snapshot_name, snapshot_id ):
		item = QTreeWidgetItem( self.list_time_line )

		item.setText( 0, snapshot_name )
		item.setText( 1, snapshot_id )

		if len( snapshot_id ) == 0:
			font = item.font( 0 )
			font.setWeight( QFont.Bold )
			item.setFont( 0, font )
			#item.setFlags( Qt.NoItemFlags )
			item.setFlags( Qt.ItemIsEnabled )
			item.setBackgroundColor( 0, QColor( 196, 196, 196 ) )

		self.list_time_line.addTopLevelItem( item )
		return item

	def update_time_line( self, get_snapshots_list = True ):
		self.list_time_line.clear()
		self.add_time_line( QString.fromUtf8( self.snapshots.get_snapshot_display_name( '/' ) ), '/' )

		if get_snapshots_list:
			self.snapshots_list = self.snapshots.get_snapshots_list() 

		groups = []
		now = datetime.date.today()

		#today
		date = now
		groups.append( (QString.fromUtf8( _('Today') ), self.snapshots.get_snapshot_id( date ), []) )

		#yesterday
		date = now - datetime.timedelta( days = 1 )
		groups.append( (QString.fromUtf8( _('Yesterday') ), self.snapshots.get_snapshot_id( date ), []) )

		#this week
		date = now - datetime.timedelta( days = now.weekday() )
		groups.append( (QString.fromUtf8( _('This week') ), self.snapshots.get_snapshot_id( date ), []) )

		#last week
		date = now - datetime.timedelta( days = now.weekday() + 7 )
		groups.append( (QString.fromUtf8( _('Last week') ), self.snapshots.get_snapshot_id( date ), []) )

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

				groups.append( ( QString.fromUtf8( group_name ), self.snapshots.get_snapshot_id( date ), [ snapshot_id ]) )

		#fill time_line list
		for group in groups:
			if len( group[2] ) > 0:
				self.add_time_line( group[0], '' );
				for snapshot_id in group[2]:
					list_item = self.add_time_line( self.snapshots.get_snapshot_display_name( snapshot_id ), snapshot_id )
					if snapshot_id == self.snapshot_id:
						self.list_time_line.setCurrentItem( list_item )

		if self.list_time_line.currentItem() is None:
			self.list_time_line.setCurrentItem( self.list_time_line.topLevelItem( 0 ) )
			if self.snapshot_id != '/':
				self.snapshot_id = '/'
				self.update_files_view( 2 )

	def on_btn_take_snapshot_clicked( self ):
		app = 'backintime'
		if os.path.isfile( './backintime' ):
			app = './backintime'
		cmd = "nice -n 19 %s --backup &" % app
		os.system( cmd )

		self.update_take_snapshot( True )

	def on_btn_name_snapshot_clicked( self ):
		item = self.list_time_line.currentItem()
		if item is None:
			return

		snapshot_id = self.time_line_get_snapshot_id( item )
		if len( snapshot_id ) <= 1:
			return

		name = self.snapshots.get_snapshot_name( snapshot_id )

		ret_val = KInputDialog.getText( _( 'Snapshot Name' ), '', name, self, self.text_validator )
		if not ret_val[1]:
			return
		
		new_name = str( ret_val[0] ).strip()
		if name == new_name:
			return

		self.snapshots.set_snapshot_name( snapshot_id, new_name )
		self.time_line_update_snapshot_name( item )

	def on_btn_remove_snapshot_clicked ( self ):
		item = self.list_time_line.currentItem()
		if item is None:
			return

		snapshot_id = self.time_line_get_snapshot_id( item )
		if len( snapshot_id ) <= 1:
			return
		
		if KMessageBox.Yes != KMessageBox.warningYesNo( self, _( "Are you sure you want to remove the snapshot:\n%s" ) % self.snapshots.get_snapshot_display_name( snapshot_id ) ):
			return

		self.snapshots.remove_snapshot( snapshot_id )
		self.update_time_line()

	def on_btn_settings_clicked( self ):
		snapshots_path = self.config.get_snapshots_path()
		include_folders = self.config.get_include_folders()

		kde4settingsdialog.SettingsDialog( self ).exec_()

		update_files_view = ( include_folders != self.config.get_include_folders() )

		if snapshots_path == self.config.get_snapshots_path() and not update_files_view:
		   return

		if update_files_view:
			self.update_places()

		if snapshots_path != self.config.get_snapshots_path():
			self.update_time_line( True )

	def on_btn_about_clicked( self ):
		dlg = KAboutApplicationDialog( self.kaboutdata, self )
		dlg.exec_()

	def on_btn_show_hidden_files_toggled( self, checked ):
		self.show_hidden_files = checked
		self.update_files_view( 1 )

	def on_btn_restore_clicked( self ):
		item = self.list_files_view.currentItem()
		if item is None:
			return

		if len( self.snapshot_id ) <= 1:
			return

		rel_path = os.path.join( self.path, self.files_view_get_name( item ) )
		self.snapshots.restore( self.snapshot_id, rel_path )

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
			#os.system( "kde-open \"%s\" &" % full_path )
			self.run = KRun( KUrl( full_path ), self, True )

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

		#update copy button state
		self.btn_copy.setEnabled( len( files ) > 0 )

		#update snapshots button state
		self.btn_snapshots.setEnabled( len( files ) > 0 )

#		#show snapshots
#		if show_snapshots:
#			self.on_btn_snapshots_clicked( None )


class KDE4TakeSnapshotCallback( threading.Thread ): #used to display status icon
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
		logger.info( '[KDE4TakeSnapshotCallback.run]' )

		if not check_x_server():
			logger.info( '[KDE4TakeSnapshotCallback.run] no X server' )
			return

		logger.info( '[KDE4TakeSnapshotCallback.run] begin loop' )

		kapp, kaboutdata = create_kapplication( self.cfg )

		status_icon = QSystemTrayIcon()
		status_icon.setIcon( KIcon('document-save') )
		status_icon.setToolTip( _('Back In Time: take snapshot ...') )
		status_icon.show()

		while True:
			kapp.processEvents()
			if self.stop_flag:
				break
			if not kapp.hasPendingEvents():
				time.sleep( 0.2 )
		
		status_icon.hide()
		kapp.processEvents()
		
		logger.info( '[KDE4TakeSnapshotCallback.run] end loop' )


def create_kapplication( cfg ):
	kaboutdata = KAboutData( 'backintime', '', ki18n( cfg.APP_NAME ), cfg.VERSION, ki18n( '' ), KAboutData.License_GPL_V2, ki18n( cfg.COPYRIGHT ), ki18n( '' ), 'http://le-web.org/back-in-time', 'dab@le-web.org' )
	kaboutdata.setProgramIconName( 'document-save' )

	translation_text = cfg.get_translations()
	translators = []
	translator_emails = []
	for line in translation_text.split( '\n' ):
		line = line.strip()
		if len( line ) == 0:
			continue
		
		index1 = line.find( ':' )
		if index1 < 0:
			continue

		index2 = line.find( '<', index1 )
		if index2 < 0:
			continue

		index3 = line.find( '>', index2 )
		if index3 < 0:
			continue

		translators.append( line[ index1 + 1 : index2 ].strip() )
		translator_emails.append( line[ index2 + 1 : index3 ].strip() )

	kaboutdata.setTranslator( ki18n( ','.join( translators ) ), ki18n( ','.join( translator_emails ) ) )

	#KCmdLineArgs.init( sys.argv, kaboutdata )
	KCmdLineArgs.init( [sys.argv[0]], kaboutdata )
	return ( KApplication(), kaboutdata )


def check_x_server():
	return 0 == os.system( 'xdpyinfo >/dev/null 2>&1' )


if __name__ == '__main__':
	cfg = backintime.start_app( KDE4TakeSnapshotCallback() )

	raise_cmd = ''
	if len( sys.argv ) > 1:
		raise_cmd = '\n'.join( sys.argv[ 1 : ] )

	app_instance = guiapplicationinstance.GUIApplicationInstance( cfg.get_app_instance_file(), raise_cmd )

	logger.openlog()
	kapp, kaboutdata = create_kapplication( cfg )

	main_window = MainWindow( cfg, app_instance, kapp, kaboutdata )

	if cfg.is_configured():
		main_window.show()
		kapp.exec_()

	logger.closelog()

	app_instance.exit_application()
snapshots
