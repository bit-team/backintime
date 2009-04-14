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
import datetime
import gettext

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *

import config
import kde4tools


_=gettext.gettext


class PopupAutomaticBackupAction( KAction ):
	def __init__( self, list, id, label ):
		KAction.__init__( self, label, list )
		self.list = list
		self.id = id
		self.label = label
	
		QObject.connect( self, SIGNAL('triggered()'), self.on_selected )

	def on_selected( self ):
		item = self.list.currentItem()
		if not item is None:
			item.setText( 1, QString.fromUtf8( self.label ) )
			item.setData( 0, Qt.UserRole, QVariant( self.id ) )


class SettingsDialog( KDialog ):
	def __init__( self, parent ):
		KDialog.__init__( self, parent )
		self.config = parent.config

		self.setWindowIcon( KIcon( 'configure' ) )
		self.setCaption( QString.fromUtf8( _( 'Settings' ) ) )

		self.main_widget = KTabWidget( self )
		self.setMainWidget( self.main_widget )

		#TAB: General
		tab_widget = QWidget( self )
		self.main_widget.addTab( tab_widget, QString.fromUtf8( _( 'General' ) ) )
		layout = QVBoxLayout( tab_widget )

		#Where to save snapshots
		group_box = QGroupBox( self )
		group_box.setTitle( QString.fromUtf8( _( 'Where to save snapshots' ) ) )
		layout.addWidget( group_box )

		hlayout = QHBoxLayout( group_box )

		self.edit_snapshots_path = KLineEdit( self.config.get_snapshots_path(), self )
		self.edit_snapshots_path.setReadOnly( True )
		hlayout.addWidget( self.edit_snapshots_path )

		self.btn_snapshots_path = KPushButton( KIcon( 'folder' ), '', self )
		hlayout.addWidget( self.btn_snapshots_path )
		QObject.connect( self.btn_snapshots_path, SIGNAL('clicked()'), self.on_btn_snapshots_path_clicked )

		#Schedule
		group_box = QGroupBox( self )
		self.global_schedule_group_box = group_box
		group_box.setTitle( QString.fromUtf8( _( 'Schedule' ) ) )
		layout.addWidget( group_box )

		hlayout = QHBoxLayout( group_box )

		self.combo_automatic_snapshots = KComboBox( self )
		hlayout.addWidget( self.combo_automatic_snapshots )
		self.fill_combo( self.combo_automatic_snapshots, self.config.AUTOMATIC_BACKUP_MODES, self.config.get_automatic_backup_mode() )

		#
		layout.addStretch()
		
		#TAB: Include
		tab_widget = QWidget( self )
		self.main_widget.addTab( tab_widget, QString.fromUtf8( _( 'Include' ) ) )
		layout = QVBoxLayout( tab_widget )

		self.list_include = QTreeWidget( self )
		self.list_include.setRootIsDecorated( False )
		#self.list_include.setEditTriggers( QAbstractItemView.NoEditTriggers )
		self.list_include.setHeaderLabels( [ QString.fromUtf8( _('Include folders') ), QString.fromUtf8( _('Automatic backup') ) ] )
		self.list_include.header().setResizeMode( 0, QHeaderView.Stretch )

		self.popup_automatic_backup = KMenu( self )
		keys = self.config.AUTOMATIC_BACKUP_MODES.keys()
		keys.sort()
		for key in keys:
			self.popup_automatic_backup.addAction( PopupAutomaticBackupAction( self.list_include, key, QString.fromUtf8( self.config.AUTOMATIC_BACKUP_MODES[ key ] ) ) )

		QObject.connect( self.list_include, SIGNAL('itemActivated(QTreeWidgetItem*,int)'), self.on_list_include_item_activated )
		layout.addWidget( self.list_include )

		for include in self.config.get_include_folders():
			self.add_include( include )
		
		buttons_layout = QHBoxLayout()
		layout.addLayout( buttons_layout )

		self.btn_include_add = KPushButton( KStandardGuiItem.add(), self )
		buttons_layout.addWidget( self.btn_include_add )
		QObject.connect( self.btn_include_add, SIGNAL('clicked()'), self.on_btn_include_add_clicked )
		
		self.btn_include_remove = KPushButton( KStandardGuiItem.remove(), self )
		buttons_layout.addWidget( self.btn_include_remove )
		QObject.connect( self.btn_include_remove, SIGNAL('clicked()'), self.on_btn_include_remove_clicked )

		#TAB: exclude
		tab_widget = QWidget( self )
		self.main_widget.addTab( tab_widget, QString.fromUtf8( _( 'Exclude' ) ) )
		layout = QVBoxLayout( tab_widget )

		self.list_exclude = KListWidget( self )
		layout.addWidget( self.list_exclude )
		
		for exclude in self.config.get_exclude_patterns():
			self.add_exclude( exclude )

		buttons_layout = QHBoxLayout()
		layout.addLayout( buttons_layout )

		self.btn_exclude_add = KPushButton( KStandardGuiItem.add(), self )
		buttons_layout.addWidget( self.btn_exclude_add )
		QObject.connect( self.btn_exclude_add, SIGNAL('clicked()'), self.on_btn_exclude_add_clicked )
		
		self.btn_exclude_file = KPushButton( KStandardGuiItem.add(), self )
		self.btn_exclude_file.setText( QString.fromUtf8( _( 'Add file' ) ) )
		buttons_layout.addWidget( self.btn_exclude_file )
		QObject.connect( self.btn_exclude_file, SIGNAL('clicked()'), self.on_btn_exclude_file_clicked )
		
		self.btn_exclude_folder = KPushButton( KStandardGuiItem.add(), self )
		self.btn_exclude_folder.setText( QString.fromUtf8( _( 'Add folder' ) ) )
		buttons_layout.addWidget( self.btn_exclude_folder )
		QObject.connect( self.btn_exclude_folder, SIGNAL('clicked()'), self.on_btn_exclude_folder_clicked )
		
		self.btn_exclude_remove = KPushButton( KStandardGuiItem.remove(), self )
		buttons_layout.addWidget( self.btn_exclude_remove )
		QObject.connect( self.btn_exclude_remove, SIGNAL('clicked()'), self.on_btn_exclude_remove_clicked )

		#TAB: Auto-remove
		tab_widget = QWidget( self )
		self.main_widget.addTab( tab_widget, QString.fromUtf8( _( 'Auto-remove' ) ) )
		layout = QGridLayout( tab_widget )

		#remove old snapshots
		enabled, value, unit = self.config.get_remove_old_snapshots()

		self.cb_remove_older_then = QCheckBox( QString.fromUtf8( _( 'Older then:' ) ), self )
		layout.addWidget( self.cb_remove_older_then, 0, 0 )
		self.cb_remove_older_then.setChecked( enabled )
		QObject.connect( self.cb_remove_older_then, SIGNAL('stateChanged(int)'), self.update_remove_older_than )

		self.edit_remove_older_then = KIntSpinBox( 1, 1000, 1, value, self )
		layout.addWidget( self.edit_remove_older_then, 0, 1 )

		self.combo_remove_older_then = KComboBox( self )
		layout.addWidget( self.combo_remove_older_then, 0, 2 )
		self.fill_combo( self.combo_remove_older_then, self.config.REMOVE_OLD_BACKUP_UNITS, unit )

		#min free space
		enabled, value, unit = self.config.get_min_free_space()

		self.cb_min_free_space = QCheckBox( QString.fromUtf8( _( 'If free space is less then:' ) ), self )
		layout.addWidget( self.cb_min_free_space, 1, 0 )
		self.cb_min_free_space.setChecked( enabled )
		QObject.connect( self.cb_min_free_space, SIGNAL('stateChanged(int)'), self.update_min_free_space )

		self.edit_min_free_space = KIntSpinBox( 1, 1000, 1, value, self )
		layout.addWidget( self.edit_min_free_space, 1, 1 )

		self.combo_min_free_space = KComboBox( self )
		layout.addWidget( self.combo_min_free_space, 1, 2 )
		self.fill_combo( self.combo_min_free_space, self.config.MIN_FREE_SPACE_UNITS, unit )

		#smart remove
		self.cb_smart_remove = QCheckBox( QString.fromUtf8( _( 'Smart remove' ) ), self )
		layout.addWidget( self.cb_smart_remove, 2, 0 )
		self.cb_smart_remove.setChecked( self.config.get_smart_remove() )

		label = QLabel( QString.fromUtf8( _( '- keep all snapshots from today and yesterday\n- keep one snapshot for the last week and one for two weeks ago\n- keep one snapshot per month for all previous months of this year\n- keep one snapshot per year for all previous years' ) ),self )
		label.setContentsMargins( 25, 0, 0, 0 )
		layout.addWidget( label, 3, 0 )

		#don't remove named snapshots
		self.cb_dont_remove_named_snapshots = QCheckBox( QString.fromUtf8( _( 'Don\'t remove named snapshots' ) ), self )
		layout.addWidget( self.cb_dont_remove_named_snapshots, 4, 0 )
		self.cb_dont_remove_named_snapshots.setChecked( self.config.get_dont_remove_named_snapshots() )

		#
		layout.addWidget( QWidget(), 5, 0 )
		layout.setRowStretch( 5, 2 )
		
		#TAB: Options
		tab_widget = QWidget( self )
		self.main_widget.addTab( tab_widget, QString.fromUtf8( _( 'Options' ) ) )
		layout = QVBoxLayout( tab_widget )

		self.cb_notify_enabled = QCheckBox( QString.fromUtf8( _( 'Enable notifications' ) ), self )
		layout.addWidget( self.cb_notify_enabled )
		self.cb_notify_enabled.setChecked( self.config.is_notify_enabled() )

		#
		layout.addStretch()

		#TAB: Expert Options
		tab_widget = QWidget( self )
		self.main_widget.addTab( tab_widget, QString.fromUtf8( _( 'Expert Options' ) ) )
		layout = QVBoxLayout( tab_widget )

		label = QLabel( QString.fromUtf8( _('Change this options only if you really know what you are doing !') ), self )
		kde4tools.set_font_bold( label )
		layout.addWidget( label )

		self.cb_per_diretory_schedule = QCheckBox( QString.fromUtf8( _( 'Enable schedule per included directory (see Include tab; default: disabled)' ) ), self )
		layout.addWidget( self.cb_per_diretory_schedule )
		self.cb_per_diretory_schedule.setChecked( self.config.get_per_directory_schedule() )
		QObject.connect( self.cb_per_diretory_schedule, SIGNAL('clicked()'), self.update_include_columns )

		#
		layout.addStretch()

		self.update_include_columns()

		self.update_remove_older_than()
		self.update_min_free_space()

	def update_include_columns( self ):
		if self.cb_per_diretory_schedule.isChecked():
			self.list_include.showColumn( 1 )
			self.global_schedule_group_box.hide()
		else:
			self.list_include.hideColumn( 1 )
			self.global_schedule_group_box.show()

	def on_list_include_item_activated( self, item, column ):
		if not self.cb_per_diretory_schedule.isChecked():
			return
		
		if item is None:
			return

		#if column != 1:
		#	return

		self.popup_automatic_backup.popup( QCursor.pos() )

	def on_popup_automatic_backup( self ):
		print "ABC"

	def update_remove_older_than( self ):
		enabled = self.cb_remove_older_then.isChecked()
		self.edit_remove_older_then.setEnabled( enabled )
		self.combo_remove_older_then.setEnabled( enabled )

	def update_min_free_space( self ):
		enabled = self.cb_min_free_space.isChecked()
		self.edit_min_free_space.setEnabled( enabled )
		self.combo_min_free_space.setEnabled( enabled )

	def add_include( self, data ):
		item = QTreeWidgetItem()
		item.setText( 0, data[0] )
		item.setText( 1, QString.fromUtf8( self.config.AUTOMATIC_BACKUP_MODES[ data[1] ] ) )
		item.setData( 0, Qt.UserRole, QVariant( data[1]) )
		self.list_include.addTopLevelItem( item )

		if self.list_include.currentItem() is None:
			self.list_include.setCurrentItem( item )

		return item

	def add_exclude( self, pattern ):
		item = QListWidgetItem( KIcon('edit-delete'), pattern, self.list_exclude )

		if self.list_exclude.currentItem() is None:
			self.list_exclude.setCurrentItem( item )

		return item

	def fill_combo( self, combo, dict, default_value ):
		keys = dict.keys()
		keys.sort()
		index = 0

		for key in keys:
			combo.addItem( QIcon(), QString.fromUtf8( dict[ key ] ), QVariant( key ) )
			if key == default_value:
				combo.setCurrentIndex( index )
			index = index + 1

	def validate( self ):
		#snapshots path
		snapshots_path = str( self.edit_snapshots_path.text() )

		#include list 
		include_list = []
		for index in xrange( self.list_include.topLevelItemCount() ):
			item = self.list_include.topLevelItem( index )
			include_list.append( [ str( item.text(0) ), item.data( 0, Qt.UserRole ).toInt()[0] ] )

		#exclude patterns
		exclude_list = []
		for index in xrange( self.list_exclude.count() ):
			exclude_list.append( str( self.list_exclude.item( index ).text() ) )

		#check params
		check_ret_val = self.config.check_take_snapshot_params( snapshots_path, include_list, exclude_list )
		if not check_ret_val is None:
			err_id, err_msg = check_ret_val
			KMessageBox.error( self, QString.fromUtf8( err_msg ) )
			return False

		#check if back folder changed
		if len( self.config.get_snapshots_path() ) > 0 and self.config.get_snapshots_path() != snapshots_path:
			if KMessageBox.Yes != KMessageBox.warningYesNo( self, QString.fromUtf8( _('Are you sure you want to change snapshots directory ?') ) ):
				return False 

		#ok let's save to config
		msg = self.config.set_snapshots_path( snapshots_path )
		if not msg is None:
			KMessageBox.error( self, QString.fromUtf8( msg ) )
			return False

		self.config.set_include_folders( include_list )
		self.config.set_exclude_patterns( exclude_list )

		#schedule
		self.config.set_automatic_backup_mode( self.combo_automatic_snapshots.itemData( self.combo_automatic_snapshots.currentIndex() ).toInt()[0] )

		#auto-remove
		self.config.set_remove_old_snapshots( 
						self.cb_remove_older_then.isChecked(), 
						self.edit_remove_older_then.value(),
						self.combo_remove_older_then.itemData( self.combo_remove_older_then.currentIndex() ).toInt()[0] )
		self.config.set_min_free_space( 
						self.cb_min_free_space.isChecked(), 
						self.edit_min_free_space.value(),
						self.combo_min_free_space.itemData( self.combo_min_free_space.currentIndex() ).toInt()[0] )
		self.config.set_dont_remove_named_snapshots( self.cb_dont_remove_named_snapshots.isChecked() )
		self.config.set_smart_remove( self.cb_smart_remove.isChecked() )

		#options
		self.config.set_notify_enabled( self.cb_notify_enabled.isChecked() )

		#expert options
		self.config.set_per_directory_schedule( self.cb_per_diretory_schedule.isChecked() )

		self.config.save()
		
		msg = self.config.setup_cron()
		if not msg is None:
			KMessageBox.error( self, QString.fromUtf8( msg ) )
			return False

		return True

	def on_btn_exclude_remove_clicked ( self ):
		self.list_exclude.takeItem( self.list_exclude.currentRow() )

		if self.list_exclude.count() > 0:
			self.list_exclude.setCurrentItem( self.list_exclude.item(0) )

	def add_exclude_( self, pattern ):
		if len( pattern ) == 0:
			return

		for index in xrange( self.list_exclude.count() ):
			if pattern == self.list_exclude.item( index ).text():
				return

		self.add_exclude( pattern )
	
	def on_btn_exclude_add_clicked( self ):
		ret_val = KInputDialog.getText( QString.fromUtf8( _( 'Exclude pattern' ) ), '', '', self )
		if not ret_val[1]:
			return
		
		self.add_exclude_( str( ret_val[0] ).strip() )

	def on_btn_exclude_file_clicked( self ):
		path = str( KFileDialog.getOpenFileName( KUrl(), '', self, QString.fromUtf8( _( 'Exclude file' ) ) ) )
		self.add_exclude_( path )

	def on_btn_exclude_folder_clicked( self ):
		path = str( KFileDialog.getExistingDirectory( KUrl(), self, QString.fromUtf8( _( 'Exclude folder' ) ) ) )
		self.add_exclude_( path )

	def on_btn_include_remove_clicked ( self ):
		item = self.list_include.currentItem()
		if item is None:
			return

		index = self.list_include.indexOfTopLevelItem( item )
		if index < 0:
			return

		self.list_include.takeTopLevelItem( index )

		if self.list_include.topLevelItemCount() > 0:
			self.list_include.setCurrentItem( self.list_include.topLevelItem(0) )

	def on_btn_include_add_clicked( self ):
		path = str( KFileDialog.getExistingDirectory( KUrl(), self, QString.fromUtf8( _( 'Include folder' ) ) ) )
		if len( path ) == 0 :
			return

		path = self.config.prepare_path( path )

		for index in xrange( self.list_include.topLevelItemCount() ):
			if path == self.list_include.topLevelItem( index ).text( 0 ):
				return

		self.add_include( [ path, self.config.NONE ] )

	def on_btn_snapshots_path_clicked( self ):
		path = str( KFileDialog.getExistingDirectory( KUrl( self.edit_snapshots_path.text() ), self, QString.fromUtf8( _( 'Where to save snapshots' ) ) ) )
		if len( path ) > 0 :
			self.edit_snapshots_path.setText( self.config.prepare_path( path ) )

	def accept( self ):
		if self.validate():
			KDialog.accept( self )

