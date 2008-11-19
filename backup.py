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
import datetime
import gettext
import statvfs

import config
import logger
import applicationinstance


_=gettext.gettext


class Backup:
	def __init__( self, cfg = None ):
		self.config = cfg
		if self.config is None:
			self.config = config.Config()
		self.lockFile = None

	def execute( self, cmd ):
		retVal = os.system( cmd )

		if retVal != 0:
			logger.warning( "Command \"%s\" returns %s" % ( cmd, retVal ) )
		else:
			logger.info( "Command \"%s\" returns %s" % ( cmd, retVal ) )

		return retVal

	def execute2( self, cmd ):
		pipe = os.popen( cmd, 'r' )
		cmdOutput = pipe.read()
		retVal = pipe.close()

		if retVal is None:
			retVal = 0

		if retVal != 0:
			logger.warning( "Command \"%s\" returns %s" % ( cmd, retVal ) )
		else:
			logger.info( "Command \"%s\" returns %s" % ( cmd, retVal ) )

		return cmdOutput

	def isBusy( self ):
		instance = applicationinstance.ApplicationInstance( self.config.lockFile(), False )
		return not instance.check()

	def getBackupList( self ):
		biglist = []
		backupPath = self.config.backupPath()

		try:
			biglist = os.listdir( backupPath )
		except:
			pass

		list = []
		
		for item in biglist:
			if len( item ) != 15:
				continue
			if os.path.isdir( os.path.join( backupPath, item ) ):
				list.append( item )

		list.sort( reverse = True )
		return list

	def _backup( self, backup_path ):
		#check only existing paths
		all_folders_to_backup = self.config.includeFolders().split( ':' )
		folders_to_backup = []
		for folder in all_folders_to_backup:
			if os.path.isdir( folder ):
				folders_to_backup.append( folder )

		#create exclude patterns string
		rsync_exclude = ''
		for exclude in self.config.excludePatterns().split( ':' ):
			rsync_exclude += " --exclude=\"%s\"" % exclude

		changed_folders = folders_to_backup

		#check previous backup
		old_backup_list = self.getBackupList()
		if len( old_backup_list ) > 0:
			logger.info( "Compare with old snapshot: %s" % old_backup_list[0] )

			prev_backup_path = self.config.backupPath( old_backup_list[ 0 ] )
			changed_folders = []

			#check for changes
			for folder in folders_to_backup:
				prev_backup_folder_path = os.path.join( prev_backup_path, 'backup', folder[ 1 : ] )

				if os.path.isdir( prev_backup_folder_path ):
					cmd = "diff -qr " + rsync_exclude + " \"%s/\" \"%s/\"" % ( folder, prev_backup_folder_path )
					if len( self.execute2( cmd ) ) > 0:
						changed_folders.append( folder )
				else: #folder don't exists in backup
					changed_folders.append( folder )

			#check if something changed
			if len( changed_folders ) == 0:
				logger.info( "Nothing changed, no back needed" )
				return False
		
			#create hard links
			logger.info( "Create hard-links" )
			self.execute( "mkdir -p \"%s\"" % backup_path )
			cmd = "cp -al \"%s/\"* \"%s\"" % ( prev_backup_path, backup_path )
			self.execute( cmd )
			cmd = "chmod -R a+w \"%s\"" % backup_path
			self.execute( cmd )

		#create new backup folder
		self.execute( "mkdir -p \"%s\"" % backup_path )
		if not os.path.exists( backup_path ):
			logger.error( "Can't create snapshot directory: %s" % backup_path )
			return False

		#sync changed folders
		for folder in changed_folders:
			backup_folder_path = os.path.join( backup_path, 'backup', folder[ 1 : ] )
			self.execute( "mkdir -p \"%s\"" % backup_folder_path )
			cmd = "rsync -av --delete --one-file-system " + rsync_exclude + " \"%s/\" \"%s/\"" % ( folder, backup_folder_path )
			logger.info( "Call rsync for directory: %s" % folder )
			self.execute( cmd )

		#make new folder read-only
		self.execute( "chmod -R a-w \"%s\"" % backup_path )
		return True

	def freeSpace( self ):
		#remove old backups
		if self.config.removeOldBackups():
			listBackups = self.getBackupList()
			listBackups.reverse()

			oldBackupDate = self.config.backupName( self.config.removeOldBackupsDate() )

			logger.info( "Remove backups older then: %s" % oldBackupDate )

			while True:
				if len( listBackups ) <= 1:
					break
				if listBackups[0] >= oldBackupDate:
					break

				path = self.config.backupPath( listBackups[0] )
				cmd = "chmod -R a+w \"%s\"" %  path
				self.execute( cmd )
				cmd = "rm -rf \"%s\"" % path
				self.execute( cmd )

				del listBackups[0]

		#try to keep min free space
		if self.config.minFreeSpace():
			minValue = self.config.minFreeSpaceValueInMb()

			logger.info( "Keep min free disk space: %s Mb" % minValue )

			listBackups = self.getBackupList()
			listBackups.reverse()

			while True:
				if len( listBackups ) <= 1:
					break

				info = os.statvfs( self.config.backupBasePath() )
				realValue = info[ statvfs.F_FRSIZE ] * info[ statvfs.F_BAVAIL ] / ( 1024 * 1024 )

				if realValue >= minValue:
					break

				path = self.config.backupPath( listBackups[0] )
				cmd = "chmod -R a+w \"%s\"" %  path
				self.execute( cmd )
				cmd = "rm -rf \"%s\"" % path
				self.execute( cmd )

				del listBackups[0]


	def backup( self ):
		backup_date = datetime.datetime.today()

		if not self.config.canBackup():
			logger.warning( 'Not configured or backup path don\'t exists' )
			return False

		instance = applicationinstance.ApplicationInstance( self.config.lockFile(), False )
		if not instance.check():
			logger.warning( 'A backup is already running' )
			return False

		instance.startApplication()
		
		logger.info( 'Lock' )

		retVal = False
		
		backup_path = self.config.backupPath( backup_date )

		if os.path.exists( backup_path ):
			logger.warning( "Snapshot path \"%s\" already exists" % backup_path )
			retVal = True
		else:
			#try:
			retVal = self._backup( backup_path )
			#except:
			#	retVal = False

		if not retVal:
			os.system( "rm -rf \"%s\"" % backup_path )
			logger.warning( "No new snapshot (not needed or error)" )
		
		#try:
		self.freeSpace()
		#except:
		#	pass

		os.system( 'sleep 2' ) #max 1 backup / second

		instance.exitApplication()
		logger.info( 'Unlock' )
		return retVal

