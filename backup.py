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


_=gettext.gettext


class Backup:
	def __init__( self, cfg = None ):
		self.config = cfg
		if self.config is None:
			self.config = config.Config()
		self.lockFile = None

	def execute( self, cmd, log = None ):
		print "Execute: %s" % cmd
		if not log is None:
			cmd = "%s 2>&1 >\"%s\"" % ( cmd, log )
		os.system( cmd )

	def execute2( self, cmd, log = None ):
		print "Execute: %s" % cmd
		if not log is None:
			cmd = "%s 2>&1 >\"%s\"" % ( cmd, log )

		pipe = os.popen( cmd, 'r' )
		cmdOutput = pipe.read()
		pipe.close()
		return cmdOutput

	def log( self, message, log = None ):
		print message
		if not log is None:
			os.system( "echo \"%s\" 2>&1 >\"%s\"" % ( message, log ) )

	def lock( self ):
		if not self.lockFile is None:
			return False

		lockFile = self.config.lockFile()
		if os.path.exists( lockFile ):
			return False

		try:
			file = os.open( lockFile, os.O_WRONLY + os.O_CREAT + os.O_EXCL )
			os.close( file )
		except:
			return False

		self.lockFile = lockFile
		return True

	def unlock( self, force = False ):
		lockFile = self.lockFile
		self.lockFile = None

		if force:
			if lockFile is None:
				lockFile = self.config.lockFile()
		
		if lockFile is None:
			return False

		self.execute( "rm \"%s\"" % lockFile )

		if os.path.exists( lockFile ):
			self.lockFile = lockFile
			return False

		return True

	def isBusy( self ):
		return os.path.exists( self.config.lockFile() )

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

	def _backup( self, backup_path, log ):
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
			self.log( '[backup_] Compare with old backup' )

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
				print '[backup_] Nothing changed, no back needed'
				return False
		
			#create hard links
			self.execute( "mkdir -p \"%s\"" % backup_path )
			cmd = "cp -al \"%s/\"* \"%s\"" % ( prev_backup_path, backup_path )
			self.execute( cmd )
			cmd = "chmod -R a+w \"%s\"" % backup_path
			self.execute( cmd )

		#create new backup folder
		self.execute( "mkdir -p \"%s\"" % backup_path )
		if not os.path.exists( backup_path ):
			print "[backup_] Can't create %s" % backup_path
			return False

		#sync changed folders
		print '[backup_] Start rsync'
		for folder in changed_folders:
			backup_folder_path = os.path.join( backup_path, 'backup', folder[ 1 : ] )
			self.execute( "mkdir -p \"%s\"" % backup_folder_path, log )
			cmd = "rsync -av --delete --one-file-system " + rsync_exclude + " \"%s/\" \"%s/\"" % ( folder, backup_folder_path )
			self.execute( cmd, log )

		#make new folder read-only
		self.execute( "chmod -R a-w \"%s\"" % backup_path )
		return True

	def freeSpace( self, log ):
		#remove old backups
		if self.config.removeOldBackups():
			listBackups = self.getBackupList()
			listBackups.reverse()

			oldBackupDate = self.config.backupName( self.config.removeOldBackupsDate() )

			self.log( "[freeSpace] Remove backups older then: %s" % oldBackupDate, log )

			while True:
				if len( listBackups ) <= 1:
					break
				if listBackups[0] >= oldBackupDate:
					break

				path = self.config.backupPath( listBackups[0] )
				cmd = "chmod -R a+w \"%s\"" %  path
				self.execute( cmd, log )
				cmd = "rm -rf \"%s\"" % path
				self.execute( cmd, log )

				del listBackups[0]

		#try to keep min free space
		if self.config.minFreeSpace():
			minValue = self.config.minFreeSpaceValueInMb()

			self.log( "[freeSpace] Min free disk space: %s Mb" % minValue, log )

			listBackups = self.getBackupList()
			listBackups.reverse()

			while True:
				if len( listBackups ) <= 1:
					break

				info = os.statvfs( self.config.backupBasePath() )
				realValue = info[ statvfs.F_FRSIZE ] * info[ statvfs.F_BAVAIL ] / ( 1024 * 1024 )
				print "Free disk space: %s Mb" % realValue

				if realValue >= minValue:
					break

				path = self.config.backupPath( listBackups[0] )
				cmd = "chmod -R a+w \"%s\"" %  path
				self.execute( cmd, log )
				cmd = "rm -rf \"%s\"" % path
				self.execute( cmd, log )

				del listBackups[0]


	def backup( self ):
		backup_date = datetime.datetime.today()

		if not self.config.canBackup():
			print '[backup] not configured or backup path don\'t exists'
			return False

		if self.isBusy():
			print '[backup] isBusy'
			return False

		if not self.lock():
			print '[backup] lock failed'
			return False
		
		print '[backup] LOCK'

		retVal = False
		
		backup_path = self.config.backupPath( backup_date )
		backup_log_path = os.path.join( backup_path, 'log.txt' )

		if os.path.exists( backup_path ):
			print "[backup] %s already exists" % backup_path
			retVal = True
		else:
			#try:
			retVal = self._backup( backup_path, backup_log_path )
			#except:
			#	retVal = False

		if not retVal:
			os.system( "rm -rf \"%s\"" % backup_path )
		
		#try:
		self.freeSpace( None )
		#except:
		#	pass

		os.system( 'sleep 2' ) #max 1 backup / second
		self.unlock()
		print '[backup] UNLOCK'
		return retVal


if __name__ == '__main__':
	Backup().backup()

