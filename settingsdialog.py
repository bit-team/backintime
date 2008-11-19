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
import gobject
import gtk.glade
import datetime
import gettext

import config
import messagebox


_=gettext.gettext


class SettingsDialog:
	def __init__( self, config, glade ):
		self.config = config
		self.glade = glade
		self.dialog = self.glade.get_widget( 'SettingsDialog' )

		signals = { 
				'on_btnAddInclude_clicked' : self.on_add_include,
				'on_btnRemoveInclude_clicked' : self.on_remove_include,
				'on_btnAddExclude_clicked' : self.on_add_exclude,
				'on_btnRemoveExclude_clicked' : self.on_remove_exclude,
				'on_cbRemoveOldBackup_toggled' : self.updateRemoveOldBackups,
				'on_cbMinFreeSpace_toggled' : self.updateMinFreeSpace,
			}

		self.glade.signal_autoconnect( signals )

		#set current folder
		self.fcbWhere = self.glade.get_widget( 'fcbWhere' )
		self.fcbWhere.set_filename( self.config.backupBasePath() )

		#setup backup folders
		self.listInclude = self.glade.get_widget( 'listInclude' )

		pixRenderer = gtk.CellRendererPixbuf()
		textRenderer = gtk.CellRendererText()

		column = gtk.TreeViewColumn( _('Backup Directories') )
		column.pack_start( pixRenderer, False )
		column.pack_end( textRenderer, True )
		column.add_attribute( pixRenderer, 'stock-id', 1 )
		column.add_attribute( textRenderer, 'markup', 0 )
		self.listInclude.append_column( column )

		self.storeInclude = gtk.ListStore( str, str )
		self.listInclude.set_model( self.storeInclude )

		includeFolders = self.config.includeFolders()
		if len( includeFolders ) > 0:
			includeFolders = includeFolders.split( ':' )
			for includeFolder in includeFolders:
				self.storeInclude.append( [includeFolder, gtk.STOCK_DIRECTORY] )
		
		self.fcbInclude = self.glade.get_widget( 'fcbInclude' )

		#setup exclude patterns
		self.listExclude = self.glade.get_widget( 'listExclude' )

		pixRenderer = gtk.CellRendererPixbuf()
		textRenderer = gtk.CellRendererText()

		column = gtk.TreeViewColumn( _('Exclude Patterns') )
		column.pack_start( pixRenderer, False )
		column.pack_end( textRenderer, True )
		column.add_attribute( pixRenderer, 'stock-id', 1 )
		column.add_attribute( textRenderer, 'markup', 0 )
		self.listExclude.append_column( column )

		self.storeExclude = gtk.ListStore( str, str )
		self.listExclude.set_model( self.storeExclude )

		excludePatterns = self.config.excludePatterns()
		if len( excludePatterns ) > 0:
			excludePatterns = excludePatterns.split( ':' )
			for excludePattern in excludePatterns:
				self.storeExclude.append( [excludePattern, gtk.STOCK_DELETE] )

		self.editPattern = self.glade.get_widget( 'editPattern' )

		#setup automatic backup mode
		self.cbBackupMode = self.glade.get_widget( 'cbBackupMode' )
		self.storeBackupMode = gtk.ListStore( str, int )

		cb = self.cbBackupMode
		store = self.storeBackupMode

		index = 0
		i = 0
		map = self.config.AUTOMATIC_BACKUP_MODES
		keys = map.keys()
		keys.sort()
		for key in keys:
			store.append( [ map[ key ], key ] )
			if key == self.config.automaticBackup():
				index = i
			i = i + 1
				
		cb.clear()
		renderer = gtk.CellRendererText()
		cb.pack_start( renderer, True )
		cb.add_attribute( renderer, 'text', 0 )
		cb.set_model( store )
		cb.set_active( index )

		#setup remove old backups older then
		self.editRemoveOldBackupValue = self.glade.get_widget( 'editRemoveOldBackupValue' )
		self.editRemoveOldBackupValue.set_value( float(self.config.removeOldBackupsValue() ) )

		self.cbRemoveOldBackupUnit = self.glade.get_widget( 'cbRemoveOldBackupUnit' )
		self.storeRemoveOldBackupUnit= gtk.ListStore( str, int )

		cb = self.cbRemoveOldBackupUnit
		store = self.storeRemoveOldBackupUnit

		index = 0
		i = 0
		map = self.config.REMOVE_OLD_BACKUP_UNITS
		keys = map.keys()
		keys.sort()
		for key in keys:
			store.append( [ map[ key ], key ] )
			if key == self.config.removeOldBackupsUnit():
				index = i
			i = i + 1
				
		cb.clear()
		renderer = gtk.CellRendererText()
		cb.pack_start( renderer, True )
		cb.add_attribute( renderer, 'text', 0 )
		cb.set_model( store )
		cb.set_active( index )

		self.cbRemoveOldBackup = self.glade.get_widget( 'cbRemoveOldBackup' )
		self.cbRemoveOldBackup.set_active( self.config.removeOldBackups() )
		self.updateRemoveOldBackups( self.cbRemoveOldBackup )

		#setup min free space
		self.editMinFreeSpaceValue = self.glade.get_widget( 'editMinFreeSpaceValue' )
		self.editMinFreeSpaceValue.set_value( float(self.config.minFreeSpaceValue() ) )

		self.cbMinFreeSpaceUnit = self.glade.get_widget( 'cbMinFreeSpaceUnit' )
		self.storeMinFreeSpaceUnit = gtk.ListStore( str, int )

		cb = self.cbMinFreeSpaceUnit
		store = self.storeMinFreeSpaceUnit

		index = 0
		i = 0
		map = self.config.MIN_FREE_SPACE_UNITS
		keys = map.keys()
		keys.sort()
		for key in keys:
			store.append( [ map[ key ], key ] )
			if key == self.config.minFreeSpaceUnit():
				index = i
			i = i + 1
				
		cb.clear()
		renderer = gtk.CellRendererText()
		cb.pack_start( renderer, True )
		cb.add_attribute( renderer, 'text', 0 )
		cb.set_model( store )
		cb.set_active( index )

		self.cbMinFreeSpace = self.glade.get_widget( 'cbMinFreeSpace' )
		self.cbMinFreeSpace.set_active( self.config.minFreeSpace() )
		self.updateMinFreeSpace( self.cbMinFreeSpace )

	def updateRemoveOldBackups( self, button ):
		enabled = button.get_active()
		self.editRemoveOldBackupValue.set_sensitive( enabled )
		self.cbRemoveOldBackupUnit.set_sensitive( enabled )

	def updateMinFreeSpace( self, button ):
		enabled = button.get_active()
		self.editMinFreeSpaceValue.set_sensitive( enabled )
		self.cbMinFreeSpaceUnit.set_sensitive( enabled )

	def run( self ):
		while True:
			if gtk.RESPONSE_OK == self.dialog.run():
				if not self.validate():
					continue
			break
		self.dialog.hide()

	def on_add_include( self, button ):
		includeFolder = self.fcbInclude.get_filename()

		iter = self.storeInclude.get_iter_first()
		while not iter is None:
			if self.storeInclude.get_value( iter, 0 ) == includeFolder:
				return
			iter = self.storeInclude.iter_next( iter )

		self.storeInclude.append( [includeFolder, gtk.STOCK_DIRECTORY] )

	def on_remove_include( self, button ):
		store, iter = self.listInclude.get_selection().get_selected()
		if not iter is None:
			store.remove( iter )

	def on_add_exclude( self, button ):
		excludePattern = self.editPattern.get_text().strip()
		self.editPattern.set_text('')
		if len( excludePattern ) == 0:
			return

		iter = self.storeExclude.get_iter_first()
		while not iter is None:
			if self.storeExclude.get_value( iter, 0 ) == excludePattern:
				return
			iter = self.storeExclude.iter_next( iter )

		self.storeExclude.append( [excludePattern, gtk.STOCK_DELETE] )

	def on_remove_exclude( self, button ):
		store, iter = self.listExclude.get_selection().get_selected()
		if not iter is None:
			store.remove( iter )

	def on_cancel( self, button ):
		self.dialog.destroy()

	def validate( self ):
		#check backup path
		backupPath = self.fcbWhere.get_filename()

		if len( backupPath ) == 0 or not os.path.isdir( backupPath ):
			messagebox.show_error( self.dialog, self.config, _('Snapshots directory can\'t be empty !') )
			return False

		if len( backupPath ) <= 1:
			messagebox.show_error( self.dialog, self.config, _('Snapshots directory can\'t be the root directory !') )
			return False

		backupPath2 = backupPath + "/"

		#check if back folder changed
		if len( self.config.backupBasePath() ) > 0 and self.config.backupBasePath() != backupPath:
			if gtk.RESPONSE_YES != messagebox.show_question( self.dialog, self.config, _('Are you sure you want to change snapshots directory ?') ):
				return False 

		#check if there are some include folders
		iter = self.storeInclude.get_iter_first()
		if iter is None:
			messagebox.show_error( self.dialog, self.config, _('You must select at least one directory to backup !') )
			return False

		#check it backup and include don't overlap each other
		while not iter is None:
			path = self.storeInclude.get_value( iter, 0 )

			if path == backupPath:
				print "Path: " + path
				print "BackupPath: " + backupPath 
				messagebox.show_error( self.dialog, self.config, _('Snapshots directory can\'t be in "Backup Directories" !') )
				return False
			
			if len( path ) >= len( backupPath2 ):
				if path[ : len( backupPath2 ) ] == backupPath2:
					print "Path: " + path
					print "BackupPath2: " + backupPath2
					messagebox.show_error( self.dialog, self.config, _('Snapshots directory can\'t be in "Backup Directories" !') )
					return False
			else:
				path2 = path + "/"
				if len( path2 ) < len( backupPath ):
					if path2 == backupPath[ : len( path2 ) ]:
						print "Path2: " + path2
						print "BackupPath: " + backupPath 
						messagebox.show_error( self.dialog, self.config, _('"Backup directories" can\'t include snapshots directory !') )
						return False

			iter = self.storeInclude.iter_next( iter )

		#ok let's save to config
		self.config.setBackupBasePath( backupPath )
	
		#include paths
		include_folders = ""
		iter = self.storeInclude.get_iter_first()
		while not iter is None:
			if len( include_folders ) > 0:
				include_folders = include_folders + ":"
			include_folders = include_folders + self.storeInclude.get_value( iter, 0 )
			iter = self.storeInclude.iter_next( iter )
		self.config.setIncludeFolders( include_folders )

		#exclude patterns
		exclude_patterns = ""
		iter = self.storeExclude.get_iter_first()
		while not iter is None:
			if len( exclude_patterns ) > 0:
				exclude_patterns = exclude_patterns + ":"
			exclude_patterns = exclude_patterns + self.storeExclude.get_value( iter, 0 )
			iter = self.storeExclude.iter_next( iter )
		self.config.setExcludePatterns( exclude_patterns )

		#other settings
		self.config.setAutomaticBackup( self.storeBackupMode.get_value( self.cbBackupMode.get_active_iter(), 1 ) )
		self.config.setRemoveOldBackups( 
						self.cbRemoveOldBackup.get_active(), 
						int( self.editRemoveOldBackupValue.get_value() ),
						self.storeRemoveOldBackupUnit.get_value( self.cbRemoveOldBackupUnit.get_active_iter(), 1 ) )
		self.config.setMinFreeSpace( 
						self.cbMinFreeSpace.get_active(), 
						int( self.editMinFreeSpaceValue.get_value() ),
						self.storeMinFreeSpaceUnit.get_value( self.cbMinFreeSpaceUnit.get_active_iter(), 1 ) )

		self.config.save()
		return True
	
