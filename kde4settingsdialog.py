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

import config
import kde4tools


_=gettext.gettext


class SettingsDialog( QDialog ):
	def __init__( self, parent ):
		QDialog.__init__( self, parent )
		self.config = parent.config

		self.setWindowTitle( _( 'Settings' ) )
		self.setWindowIcon( KIcon( 'configure' ) )

		self.main_layout = QVBoxLayout()
		self.setLayout( self.main_layout )

		#where to save snapshots
		self.group_box_where = QGroupBox( self )
		self.main_layout.addWidget( self.group_box_where )
		self.group_box_where.setTitle( _( 'Where to save snapshots' ) )

		layout = QHBoxLayout()
		self.group_box_where.setLayout( layout )

		self.edit_snapshots_path = QLineEdit( self.config.get_snapshots_path(), self )
		self.edit_snapshots_path.setReadOnly( True )
		layout.addWidget( self.edit_snapshots_path )

		self.btn_snapshots_path = QPushButton( _( '...' ), self )
		layout.addWidget( self.btn_snapshots_path )
		QObject.connect( self.btn_snapshots_path, SIGNAL('clicked()'), self.on_btn_snapshots_path_clicked )
		
		#what to save
		self.group_box_what = QGroupBox( self )
		self.main_layout.addWidget( self.group_box_what )
		self.group_box_what.setTitle( _( 'What to save' ) )

		wts_layout = QHBoxLayout()
		self.group_box_what.setLayout( wts_layout )

		#include directories
		wts_left_layout = QVBoxLayout()
		wts_layout.addLayout( wts_left_layout )

		self.list_include = QTreeWidget( self )
		wts_left_layout.addWidget( self.list_include )
		self.list_include.setHeaderLabel( _('Include folders') )
		self.list_include.setRootIsDecorated( False )

		for include in self.config.get_include_folders():
			self.add_include( include )
		
		layout = QHBoxLayout( self )
		wts_left_layout.addLayout( layout )

		self.btn_include_add = QPushButton( _( 'Add' ), self )
		layout.addWidget( self.btn_include_add )
		QObject.connect( self.btn_include_add, SIGNAL('clicked()'), self.on_btn_include_add_clicked )
		
		self.btn_include_remove = QPushButton( _( 'Remove' ), self )
		layout.addWidget( self.btn_include_remove )
		QObject.connect( self.btn_include_remove, SIGNAL('clicked()'), self.on_btn_include_remove_clicked )

		#exclude patterns
		wts_right_layout = QVBoxLayout()
		wts_layout.addLayout( wts_right_layout )

		self.list_exclude = QTreeWidget( self )
		wts_right_layout.addWidget( self.list_exclude )
		self.list_exclude.setHeaderLabel( _('Exclude patterns') )
		self.list_exclude.setRootIsDecorated( False )
		
		for exclude in self.config.get_exclude_patterns():
			self.add_exclude( exclude )

		layout = QHBoxLayout( self )
		wts_right_layout.addLayout( layout )

		self.btn_exclude_add = QPushButton( _( 'Add' ), self )
		layout.addWidget( self.btn_exclude_add )
		QObject.connect( self.btn_exclude_add, SIGNAL('clicked()'), self.on_btn_exclude_add_clicked )
		
		self.btn_exclude_remove = QPushButton( _( 'Remove' ), self )
		layout.addWidget( self.btn_exclude_remove )
		QObject.connect( self.btn_exclude_remove, SIGNAL('clicked()'), self.on_btn_exclude_remove_clicked )

		#Automatic snapshots
		self.group_box_when = QGroupBox( self )
		self.main_layout.addWidget( self.group_box_when )
		self.group_box_when.setTitle( _( 'When' ) )

		layout = QHBoxLayout()
		self.group_box_when.setLayout( layout )
		layout.addWidget( QLabel( _( 'Automatic snapshots:' ), self ) )

		self.combo_automatic_snapshots = QComboBox( self )
		layout.addWidget( self.combo_automatic_snapshots )
		self.fill_combo( self.combo_automatic_snapshots, self.config.AUTOMATIC_BACKUP_MODES, self.config.get_automatic_backup_mode() )

		#Remove snapshots
		self.group_box_remove = QGroupBox( self )
		self.main_layout.addWidget( self.group_box_remove )
		self.group_box_remove.setTitle( _( 'Remove Snapshots' ) )

		layout = QGridLayout()
		self.group_box_remove.setLayout( layout )

		#remove old snapshots
		enabled, value, unit = self.config.get_remove_old_snapshots()

		self.cb_remove_older_then = QCheckBox( _( 'Older then:' ), self )
		layout.addWidget( self.cb_remove_older_then, 0, 0 )
		self.cb_remove_older_then.setChecked( enabled )
		QObject.connect( self.cb_remove_older_then, SIGNAL('stateChanged(int)'), self.update_remove_older_than )

		self.edit_remove_older_then = QSpinBox( self )
		layout.addWidget( self.edit_remove_older_then, 0, 1 )
		self.edit_remove_older_then.setRange( 1, 1000 )
		self.edit_remove_older_then.setValue( value )

		self.combo_remove_older_then = QComboBox( self )
		layout.addWidget( self.combo_remove_older_then, 0, 2 )
		self.fill_combo( self.combo_remove_older_then, self.config.REMOVE_OLD_BACKUP_UNITS, unit )

		#min free space
		enabled, value, unit = self.config.get_min_free_space()

		self.cb_min_free_space = QCheckBox( _( 'If free space is less then:' ), self )
		layout.addWidget( self.cb_min_free_space, 1, 0 )
		self.cb_min_free_space.setChecked( enabled )
		QObject.connect( self.cb_min_free_space, SIGNAL('stateChanged(int)'), self.update_min_free_space )

		self.edit_min_free_space = QSpinBox( self )
		layout.addWidget( self.edit_min_free_space, 1, 1 )
		self.edit_min_free_space.setRange( 1, 1000 )
		self.edit_min_free_space.setValue( value )

		self.combo_min_free_space = QComboBox( self )
		layout.addWidget( self.combo_min_free_space, 1, 2 )
		self.fill_combo( self.combo_min_free_space, self.config.MIN_FREE_SPACE_UNITS, unit )

		#don't remove named snapshots
		self.cb_dont_remove_named_snapshots = QCheckBox( _( 'Don\'t remove named snapshots' ), self )
		layout.addWidget( self.cb_dont_remove_named_snapshots, 2, 0 )
		self.cb_dont_remove_named_snapshots.setChecked( self.config.get_dont_remove_named_snapshots() )

		#buttons line
		button_box = QDialogButtonBox( self )
		self.main_layout.addWidget( button_box )

		self.btn_ok = button_box.addButton( QDialogButtonBox.Ok )
		QObject.connect( self.btn_ok, SIGNAL('clicked()'), self.accept )

		self.btn_cancel = button_box.addButton( QDialogButtonBox.Cancel )
		QObject.connect( self.btn_cancel, SIGNAL('clicked()'), self.reject )

		#make titles bold
		kde4tools.set_font_bold( self.group_box_where )
		kde4tools.set_font_bold( self.group_box_what )
		kde4tools.set_font_bold( self.group_box_when )
		kde4tools.set_font_bold( self.group_box_remove )

		self.update_remove_older_than()
		self.update_min_free_space()

		self.btn_ok.setDefault( True )

	def update_remove_older_than( self ):
		enabled = self.cb_remove_older_then.isChecked()
		self.edit_remove_older_then.setEnabled( enabled )
		self.combo_remove_older_then.setEnabled( enabled )

	def update_min_free_space( self ):
		enabled = self.cb_min_free_space.isChecked()
		self.edit_min_free_space.setEnabled( enabled )
		self.combo_min_free_space.setEnabled( enabled )

	def add_include( self, path ):
		item = QTreeWidgetItem( self.list_include )
		item.setIcon( 0, KIcon('folder') )
		item.setText( 0, path )

		self.list_include.addTopLevelItem( item )
		return item

	def add_exclude( self, pattern ):
		item = QTreeWidgetItem( self.list_exclude )
		item.setIcon( 0, KIcon('edit-delete') )
		item.setText( 0, pattern )

		self.list_exclude.addTopLevelItem( item )
		return item

	def fill_combo( self, combo, dict, default_value ):
		keys = dict.keys()
		keys.sort()
		index = 0

		for key in keys:
			combo.addItem( QIcon(), dict[ key ], QVariant( key ) )
			if key == default_value:
				combo.setCurrentIndex( index )
			index = index + 1

#		signals = { 
#				'on_btn_add_include_clicked' : self.on_add_include,
#				'on_btn_remove_include_clicked' : self.on_remove_include,
#				'on_btn_add_exclude_clicked' : self.on_add_exclude,
#				'on_btn_remove_exclude_clicked' : self.on_remove_exclude,
#				'on_cb_remove_old_backup_toggled' : self.update_remove_old_backups,
#				'on_cb_min_free_space_toggled' : self.update_min_free_space,
#			}
#
#		self.glade.signal_autoconnect( signals )
#
#		#set current folder
#		self.fcb_where = self.glade.get_widget( 'fcb_where' )
#		self.fcb_where.set_filename( self.config.get_snapshots_path() )
#		
#		#setup backup folders
#		self.list_include = self.glade.get_widget( 'list_include' )
#		self.list_include.get_model() is None
#
#		pix_renderer = gtk.CellRendererPixbuf()
#		text_renderer = gtk.CellRendererText()
#
#		column = gtk.TreeViewColumn( _('Backup Directories') )
#		column.pack_start( pix_renderer, False )
#		column.pack_end( text_renderer, True )
#		column.add_attribute( pix_renderer, 'stock-id', 1 )
#		column.add_attribute( text_renderer, 'markup', 0 )
#		self.list_include.append_column( column )
#
#		self.store_include = gtk.ListStore( str, str )
#		self.list_include.set_model( self.store_include )
#
#		self.store_include.clear()
#		include_folders = self.config.get_include_folders()
#		if len( include_folders ) > 0:
#			for include_folder in include_folders:
#				self.store_include.append( [include_folder, gtk.STOCK_DIRECTORY] )
#		
#		self.fcb_include = self.glade.get_widget( 'fcb_include' )
#
#		#setup exclude patterns
#		self.list_exclude = self.glade.get_widget( 'list_exclude' )
#
#		pix_renderer = gtk.CellRendererPixbuf()
#		text_renderer = gtk.CellRendererText()
#
#		column = gtk.TreeViewColumn( _('Exclude Patterns') )
#		column.pack_start( pix_renderer, False )
#		column.pack_end( text_renderer, True )
#		column.add_attribute( pix_renderer, 'stock-id', 1 )
#		column.add_attribute( text_renderer, 'markup', 0 )
#		self.list_exclude.append_column( column )
#
#		self.store_exclude = gtk.ListStore( str, str )
#		self.list_exclude.set_model( self.store_exclude )
#
#		self.store_exclude.clear()
#		exclude_patterns = self.config.get_exclude_patterns()
#		if len( exclude_patterns ) > 0:
#			for exclude_pattern in exclude_patterns:
#				self.store_exclude.append( [exclude_pattern, gtk.STOCK_DELETE] )
#
#		self.edit_pattern = self.glade.get_widget( 'edit_pattern' )
#
#		#setup automatic backup mode
#		self.cb_backup_mode = self.glade.get_widget( 'cb_backup_mode' )
#
#		self.store_backup_mode = gtk.ListStore( str, int )
#		self.cb_backup_mode.set_model( self.store_backup_mode )
#			
#		self.cb_backup_mode.clear()
#		renderer = gtk.CellRendererText()
#		self.cb_backup_mode.pack_start( renderer, True )
#		self.cb_backup_mode.add_attribute( renderer, 'text', 0 )
#
#		self.store_backup_mode.clear()
#		index = 0
#		i = 0
#		map = self.config.AUTOMATIC_BACKUP_MODES
#		keys = map.keys()
#		keys.sort()
#		for key in keys:
#			self.store_backup_mode.append( [ map[ key ], key ] )
#			if key == self.config.get_automatic_backup_mode():
#				index = i
#			i = i + 1
#				
#		self.cb_backup_mode.set_active( index )
#
#		#setup remove old backups older then
#		enabled, value, unit = self.config.get_remove_old_snapshots()
#
#		self.edit_remove_old_backup_value = self.glade.get_widget( 'edit_remove_old_backup_value' )
#		self.edit_remove_old_backup_value.set_value( float( value ) )
#
#		self.cb_remove_old_backup_unit = self.glade.get_widget( 'cb_remove_old_backup_unit' )
#
#		self.store_remove_old_backup_unit = gtk.ListStore( str, int )
#		self.cb_remove_old_backup_unit.set_model( self.store_remove_old_backup_unit )
#
#		renderer = gtk.CellRendererText()
#		self.cb_remove_old_backup_unit.pack_start( renderer, True )
#		self.cb_remove_old_backup_unit.add_attribute( renderer, 'text', 0 )
#
#		self.store_remove_old_backup_unit.clear()
#		index = 0
#		i = 0
#		map = self.config.REMOVE_OLD_BACKUP_UNITS
#		keys = map.keys()
#		keys.sort()
#		for key in keys:
#			self.store_remove_old_backup_unit.append( [ map[ key ], key ] )
#			if key == unit:
#				index = i
#			i = i + 1
#				
#		self.cb_remove_old_backup_unit.set_active( index )
#
#		self.cb_remove_old_backup = self.glade.get_widget( 'cb_remove_old_backup' )
#		self.cb_remove_old_backup.set_active( enabled )
#		self.update_remove_old_backups( self.cb_remove_old_backup )
#
#		#setup min free space
#		enabled, value, unit = self.config.get_min_free_space()
#
#		self.edit_min_free_space_value = self.glade.get_widget( 'edit_min_free_space_value' )
#		self.edit_min_free_space_value.set_value( float(value) )
#
#		self.cb_min_free_space_unit = self.glade.get_widget( 'cb_min_free_space_unit' )
#
#		self.store_min_free_space_unit = gtk.ListStore( str, int )
#		self.cb_min_free_space_unit.set_model( self.store_min_free_space_unit )
#
#		renderer = gtk.CellRendererText()
#		self.cb_min_free_space_unit.pack_start( renderer, True )
#		self.cb_min_free_space_unit.add_attribute( renderer, 'text', 0 )
#
#		self.store_min_free_space_unit.clear()
#		index = 0
#		i = 0
#		map = self.config.MIN_FREE_SPACE_UNITS
#		keys = map.keys()
#		keys.sort()
#		for key in keys:
#			self.store_min_free_space_unit.append( [ map[ key ], key ] )
#			if key == unit:
#				index = i
#			i = i + 1
#				
#		self.cb_min_free_space_unit.set_active( index )
#
#		self.cb_min_free_space = self.glade.get_widget( 'cb_min_free_space' )
#		self.cb_min_free_space.set_active( enabled )
#		self.update_min_free_space( self.cb_min_free_space )
#
#		#don't remove named snapshots
#		self.cb_dont_remove_named_snapshots = self.glade.get_widget( 'cb_dont_remove_named_snapshots' )
#		self.cb_dont_remove_named_snapshots.set_active( self.config.get_dont_remove_named_snapshots() )
#
#	def update_remove_old_backups( self, button ):
#		enabled = button.get_active()
#		self.edit_remove_old_backup_value.set_sensitive( enabled )
#		self.cb_remove_old_backup_unit.set_sensitive( enabled )
#
#	def update_min_free_space( self, button ):
#		enabled = button.get_active()
#		self.edit_min_free_space_value.set_sensitive( enabled )
#		self.cb_min_free_space_unit.set_sensitive( enabled )
#
#	def run( self ):
#		while True:
#			if gtk.RESPONSE_OK == self.dialog.run():
#				if not self.validate():
#					continue
#			break
#		self.dialog.hide()
#
#	def on_add_include( self, button ):
#		include_folder = self.fcb_include.get_filename()
#
#		iter = self.store_include.get_iter_first()
#		while not iter is None:
#			if self.store_include.get_value( iter, 0 ) == include_folder:
#				return
#			iter = self.store_include.iter_next( iter )
#
#		self.store_include.append( [include_folder, gtk.STOCK_DIRECTORY] )
#
#	def on_remove_include( self, button ):
#		store, iter = self.list_include.get_selection().get_selected()
#		if not iter is None:
#			store.remove( iter )
#
#	def on_add_exclude( self, button ):
#		exclude_pattern = self.edit_pattern.get_text().strip()
#		self.edit_pattern.set_text('')
#		if len( exclude_pattern ) == 0:
#			return
#
#		iter = self.store_exclude.get_iter_first()
#		while not iter is None:
#			if self.store_exclude.get_value( iter, 0 ) == exclude_pattern:
#				return
#			iter = self.store_exclude.iter_next( iter )
#
#		self.store_exclude.append( [exclude_pattern, gtk.STOCK_DELETE] )
#
#	def on_remove_exclude( self, button ):
#		store, iter = self.list_exclude.get_selection().get_selected()
#		if not iter is None:
#			store.remove( iter )
#
#	def on_cancel( self, button ):
#		self.dialog.destroy()

	def validate( self ):
		#snapshots path
		snapshots_path = str( self.edit_snapshots_path.text() )

		#include list 
		include_list = []
		for index in xrange( self.list_include.topLevelItemCount() ):
			include_list.append( str( self.list_include.topLevelItem( index ).text( 0 ) ) )

		#exclude patterns
		exclude_list = []
		for index in xrange( self.list_exclude.topLevelItemCount() ):
			exclude_list.append( str( self.list_exclude.topLevelItem( index ).text( 0 ) ) )

		#check params
		check_ret_val = self.config.check_take_snapshot_params( snapshots_path, include_list, exclude_list )
		if not check_ret_val is None:
			err_id, err_msg = check_ret_val
			QMessageBox.critical( self, _( 'Error' ), err_msg )
			return False

		#check if back folder changed
		if len( self.config.get_snapshots_path() ) > 0 and self.config.get_snapshots_path() != snapshots_path:
			if QMessageBox.Yes != QMessageBox.question( self, _( 'Warning' ), _('Are you sure you want to change snapshots directory ?'), QMessageBox.Yes | QMessageBox.No ):
				return False 

		#ok let's save to config
		self.config.set_snapshots_path( snapshots_path )
		self.config.set_include_folders( include_list )
		self.config.set_exclude_patterns( exclude_list )

		#other settings
		self.config.set_automatic_backup_mode( self.combo_automatic_snapshots.itemData( self.combo_automatic_snapshots.currentIndex() ).toInt()[0] )
		self.config.set_remove_old_snapshots( 
						self.cb_remove_older_then.isChecked(), 
						self.edit_remove_older_then.value(),
						self.combo_remove_older_then.itemData( self.combo_remove_older_then.currentIndex() ).toInt()[0] )
		self.config.set_min_free_space( 
						self.cb_min_free_space.isChecked(), 
						self.edit_min_free_space.value(),
						self.combo_min_free_space.itemData( self.combo_min_free_space.currentIndex() ).toInt()[0] )
		self.config.set_dont_remove_named_snapshots( self.cb_dont_remove_named_snapshots.isChecked() )

		self.config.save()
		return True

	def on_btn_exclude_remove_clicked ( self ):
		item = self.list_exclude.currentItem()
		if item is None:
			return
		self.list_exclude.removeItemWidget( item, 0 )
	
	def on_btn_exclude_add_clicked( self ):
		ret_val = QInputDialog.getText( self, _( 'Exclude pattern' ), '' )
		if not ret_val[1]:
			return
		
		pattern = str( ret_val[0] ).strip()
		if len( pattern ) == 0:
			return

		for index in xrange( self.list_exclude.topLevelItemCount() ):
			if pattern == self.list_exclude.topLevelItem( index ):
				return
		self.add_exclude( pattern )

	def on_btn_include_remove_clicked ( self ):
		item = self.list_include.currentItem()
		if item is None:
			return
		self.list_include.removeItemWidget( item, 0 )

	def on_btn_include_add_clicked( self ):
		path = QFileDialog.getExistingDirectory( self, _( 'Include folder' ) )
		if len( path ) == 0 :
			return

		for index in xrange( self.list_include.topLevelItemCount() ):
			if path == self.list_include.topLevelItem( index ):
				return
		self.add_include( path[ : -1 ] )

	def on_btn_snapshots_path_clicked( self ):
		path = QFileDialog.getExistingDirectory( self, _( 'Where to save snapshots' ), self.edit_snapshots_path.text() )
		if len( path ) > 0 :
			self.edit_snapshots_path.setText( path[ : -1 ] )

	def accept( self ):
		if self.validate():
			QDialog.accept( self )

