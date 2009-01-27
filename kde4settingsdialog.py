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


class SettingsDialog( KDialog ):
	def __init__( self, parent ):
		KDialog.__init__( self, parent )
		self.config = parent.config

		self.setWindowIcon( KIcon( 'configure' ) )
		self.setCaption( QString.fromUtf8( _( 'Settings' ) ) )
		#self.setButtons( KDialog.Ok | KDialog.Cancel );	

		self.main_widget = QWidget( self )
		self.main_layout = QVBoxLayout()
		self.main_widget.setLayout( self.main_layout )
		self.setMainWidget( self.main_widget )

		#where to save snapshots
		self.group_box_where = QGroupBox( self )
		self.main_layout.addWidget( self.group_box_where )
		self.group_box_where.setTitle( QString.fromUtf8( _( 'Where to save snapshots' ) ) )

		layout = QHBoxLayout()
		self.group_box_where.setLayout( layout )

		self.edit_snapshots_path = QLineEdit( self.config.get_snapshots_path(), self )
		self.edit_snapshots_path.setReadOnly( True )
		layout.addWidget( self.edit_snapshots_path )

		self.btn_snapshots_path = QPushButton( QString.fromUtf8( _( '...' ) ), self )
		layout.addWidget( self.btn_snapshots_path )
		QObject.connect( self.btn_snapshots_path, SIGNAL('clicked()'), self.on_btn_snapshots_path_clicked )
		
		#what to save
		self.group_box_what = QGroupBox( self )
		self.main_layout.addWidget( self.group_box_what )
		self.group_box_what.setTitle( QString.fromUtf8( _( 'What to save' ) ) )

		wts_layout = QHBoxLayout()
		self.group_box_what.setLayout( wts_layout )

		#include directories
		wts_left_layout = QVBoxLayout()
		wts_layout.addLayout( wts_left_layout )

		self.list_include = QTreeWidget( self )
		wts_left_layout.addWidget( self.list_include )
		self.list_include.setHeaderLabel( QString.fromUtf8( _('Include folders') ) )
		self.list_include.setRootIsDecorated( False )

		for include in self.config.get_include_folders():
			self.add_include( include )
		
		layout = QHBoxLayout()
		wts_left_layout.addLayout( layout )

		self.btn_include_add = QPushButton( QString.fromUtf8( _( 'Add' ) ), self )
		layout.addWidget( self.btn_include_add )
		QObject.connect( self.btn_include_add, SIGNAL('clicked()'), self.on_btn_include_add_clicked )
		
		self.btn_include_remove = QPushButton( QString.fromUtf8( _( 'Remove' ) ), self )
		layout.addWidget( self.btn_include_remove )
		QObject.connect( self.btn_include_remove, SIGNAL('clicked()'), self.on_btn_include_remove_clicked )

		#exclude patterns
		wts_right_layout = QVBoxLayout()
		wts_layout.addLayout( wts_right_layout )

		self.list_exclude = QTreeWidget( self )
		wts_right_layout.addWidget( self.list_exclude )
		self.list_exclude.setHeaderLabel( QString.fromUtf8( _('Exclude patterns') ) )
		self.list_exclude.setRootIsDecorated( False )
		
		for exclude in self.config.get_exclude_patterns():
			self.add_exclude( exclude )

		layout = QHBoxLayout()
		wts_right_layout.addLayout( layout )

		self.btn_exclude_add = QPushButton( QString.fromUtf8( _( 'Add' ) ), self )
		layout.addWidget( self.btn_exclude_add )
		QObject.connect( self.btn_exclude_add, SIGNAL('clicked()'), self.on_btn_exclude_add_clicked )
		
		self.btn_exclude_remove = QPushButton( QString.fromUtf8( _( 'Remove' ) ), self )
		layout.addWidget( self.btn_exclude_remove )
		QObject.connect( self.btn_exclude_remove, SIGNAL('clicked()'), self.on_btn_exclude_remove_clicked )

		#Automatic snapshots
		self.group_box_when = QGroupBox( self )
		self.main_layout.addWidget( self.group_box_when )
		self.group_box_when.setTitle( QString.fromUtf8( _( 'When' ) ) )

		layout = QHBoxLayout()
		self.group_box_when.setLayout( layout )
		layout.addWidget( QLabel( QString.fromUtf8( _( 'Automatic snapshots:' ) ), self ) )

		self.combo_automatic_snapshots = QComboBox( self )
		layout.addWidget( self.combo_automatic_snapshots )
		self.fill_combo( self.combo_automatic_snapshots, self.config.AUTOMATIC_BACKUP_MODES, self.config.get_automatic_backup_mode() )

		#Remove snapshots
		self.group_box_remove = QGroupBox( self )
		self.main_layout.addWidget( self.group_box_remove )
		self.group_box_remove.setTitle( QString.fromUtf8( _( 'Remove Snapshots' ) ) )

		layout = QGridLayout()
		self.group_box_remove.setLayout( layout )

		#remove old snapshots
		enabled, value, unit = self.config.get_remove_old_snapshots()

		self.cb_remove_older_then = QCheckBox( QString.fromUtf8( _( 'Older then:' ) ), self )
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

		self.cb_min_free_space = QCheckBox( QString.fromUtf8( _( 'If free space is less then:' ) ), self )
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
		self.cb_dont_remove_named_snapshots = QCheckBox( QString.fromUtf8( _( 'Don\'t remove named snapshots' ) ), self )
		layout.addWidget( self.cb_dont_remove_named_snapshots, 2, 0 )
		self.cb_dont_remove_named_snapshots.setChecked( self.config.get_dont_remove_named_snapshots() )

		#make titles bold
		kde4tools.set_font_bold( self.group_box_where )
		kde4tools.set_font_bold( self.group_box_what )
		kde4tools.set_font_bold( self.group_box_when )
		kde4tools.set_font_bold( self.group_box_remove )

		self.update_remove_older_than()
		self.update_min_free_space()

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
			include_list.append( str( self.list_include.topLevelItem( index ).text( 0 ) ) )

		#exclude patterns
		exclude_list = []
		for index in xrange( self.list_exclude.topLevelItemCount() ):
			exclude_list.append( str( self.list_exclude.topLevelItem( index ).text( 0 ) ) )

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
		ret_val = KInputDialog.getText( QString.fromUtf8( _( 'Exclude pattern' ) ), '', '', self )
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
		path = str( KFileDialog.getExistingDirectory( KUrl(), self, QString.fromUtf8( _( 'Include folder' ) ) ) )
		if len( path ) == 0 :
			return

		for index in xrange( self.list_include.topLevelItemCount() ):
			if path == self.list_include.topLevelItem( index ):
				return
		self.add_include( self.config.prepare_path( path ) )

	def on_btn_snapshots_path_clicked( self ):
		path = str( KFileDialog.getExistingDirectory( KUrl( self.edit_snapshots_path.text() ), self, QString.fromUtf8( _( 'Where to save snapshots' ) ) ) )
		if len( path ) > 0 :
			self.edit_snapshots_path.setText( self.config.prepare_path( path ) )

	def accept( self ):
		if self.validate():
			QDialog.accept( self )

