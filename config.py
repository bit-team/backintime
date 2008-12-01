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


import os.path
import os
import datetime
import gettext

_=gettext.gettext


gettext.bindtextdomain( 'backintime', '/usr/share/locale' )
gettext.textdomain( 'backintime' )


class Config:
	APP_NAME = 'Back In Time'
	VERSION = '0.8.12'

	NONE = 0
	_5_MIN = 2
	_10_MIN = 4
	HOUR = 10
	DAY = 20
	WEEK = 30
	MONTH = 40
	YEAR = 80

	DISK_UNIT_MB = 10
	DISK_UNIT_GB = 20

	AUTOMATIC_BACKUP_MODES = { 
				NONE : _('None'), 
				_5_MIN: _('Every 5 minutes'), 
				_10_MIN: _('Every 10 minutes'), 
				HOUR : _('Every Hour'), 
				DAY : _('Every Day'), 
				WEEK : _('Every Week'), 
				MONTH : _('Every Month')
				}

	REMOVE_OLD_BACKUP_UNITS = { 
				DAY : _('Day(s)'), 
				WEEK : _('Week(s)'), 
				YEAR : _('Year(s)')
				}

	MIN_FREE_SPACE_UNITS = { DISK_UNIT_MB : 'Mb', DISK_UNIT_GB : 'Gb' }


	def __init__( self ):
		self._APP_PATH = os.path.abspath( os.path.dirname( __file__ ) )
		self._DOC_PATH = '/usr/share/doc/backintime'
		if os.path.exists( os.path.join( self._APP_PATH, 'LICENSE' ) ):
			self._DOC_PATH = self._APP_PATH

		self._GLOBAL_CONFIG_PATH = '/etc/backintime/config'
		self._CONFIG_FOLDER = os.path.expanduser( '~/.config/backintime' )
		os.system( "mkdir -p \"%s\"" % self._CONFIG_FOLDER )

		self._CONFIG_PATH = os.path.join( self._CONFIG_FOLDER, 'config' )
		self._LOCK_FILE_NAME = 'lock'

		self._BASE_BACKUP_PATH = ''
		self._INCLUDE_FOLDERS = ''
		self._EXCLUDE_PATTERNS = '.*:*.backup*:*~'
		self._AUTOMATIC_BACKUP = self.NONE
		self._REMOVE_OLD_BACKUPS = 1
		self._REMOVE_OLD_BACKUPS_VALUE = 10
		self._REMOVE_OLD_BACKUPS_UNIT = self.YEAR
		self._MIN_FREE_SPACE = 1
		self._MIN_FREE_SPACE_VALUE = 1
		self._MIN_FREE_SPACE_UNIT = self.DISK_UNIT_GB
		self._DONT_REMOVE_NAMED_SNAPSHOTS = 1

		self.MAIN_WINDOW_X = -1
		self.MAIN_WINDOW_Y = -1
		self.MAIN_WINDOW_WIDTH = -1
		self.MAIN_WINDOW_HEIGHT = -1
		self.MAIN_WINDOW_HPANED1_POSITION = -1
		self.MAIN_WINDOW_HPANED2_POSITION = -1
		self.LAST_PATH = ''

		self.DIFF_CMD = 'meld'
		self.DIFF_CMD_PARAMS = '%1 %2'

		self.load()

	def appPath( self ):
		return self._APP_PATH

	def gladeFile( self ):
		return os.path.join( self.appPath(), 'backintime.glade' )

	def baseInstanceFile( self ):
		return os.path.join( self._CONFIG_FOLDER, 'appinstance' )

	def getFileContent( self, path, defaultValue = None ):
		retVal = defaultValue 
		try:
			file = open( path )
			retVal = file.read()
			file.close()
		except:
			pass
		return retVal

	def getLinesFileContent( self, path, defaultValue = None ):
		retVal = defaultValue 
		try:
			file = open( path )
			retVal = file.readlines()
			file.close()
		except:
			pass
		return retVal

	def license( self ):
		return self.getFileContent( os.path.join( self._DOC_PATH, 'LICENSE' ) )

	def translations( self ):
		return self.getFileContent( os.path.join( self._DOC_PATH, 'TRANSLATIONS' ) )

	def authors( self ):
		return self.getLinesFileContent( os.path.join( self._DOC_PATH, 'AUTHORS' ) )

	def backupName( self, date ):
		if type( date ) is datetime.datetime:
			return date.strftime( '%Y%m%d-%H%M%S' )

		if type( date ) is datetime.date:
			return date.strftime( '%Y%m%d-000000' )

		if type( date ) is str:
			return date
		
		return ""

	def backupPath( self, date = None ):
		path = os.path.join( self._BASE_BACKUP_PATH, 'backintime' )

		if date is None:
			return path

		#print "[backupPath] date: %s" % date
		#print "[backupPath] name: %s" % self.backupName( date )
		return os.path.join( path, self.backupName( date ) )

	def backupBasePath( self ):
		return self._BASE_BACKUP_PATH

	def snapshotPath( self, snapshot ):
		if len( snapshot ) <= 1:
			return '/';
		return os.path.join( self.backupPath( snapshot ), 'backup' )
	
	def snapshotPathTo( self, snapshot, toPath = '/' ):
		return os.path.join( self.snapshotPath( snapshot ), toPath[ 1 : ] )

	def snapshotDisplayName( self, snapshot, simple = False ):
		if len( snapshot ) <= 1:
			return _('Now')

		retVal = "%s-%s-%s %s:%s:%s" % ( snapshot[ 0 : 4 ], snapshot[ 4 : 6 ], snapshot[ 6 : 8 ], snapshot[ 9 : 11 ], snapshot[ 11 : 13 ], snapshot[ 13 : 15 ]  )
		name = self.snapshotName( snapshot )
		if len( name ) > 0:
			if not simple:
				name = "<b>%s</b>" % name
			retVal = retVal + ' - ' + name
		return retVal

	def snapshotName( self, snapshot ):
		if len( snapshot ) <= 1: #not a snapshot
			return ''

		path = self.backupPath( snapshot )
		if not os.path.isdir( path ):
			return ''
		
		retVal = ''

		try:
			file = open( os.path.join( path, 'name' ), 'rt' )
			retVal = file.read()
			file.close()
		except:
			pass

		return retVal

	def setSnapshotName( self, snapshot, name ):
		if len( snapshot ) <= 1: #not a snapshot
			return

		path = self.backupPath( snapshot )
		if not os.path.isdir( path ):
			return

		name_path = os.path.join( path, 'name' )

		os.system( "chmod a+w \"%s\"" % path )

		try:
			file = open( name_path, 'wt' )
			file.write( name )
			file.close()
		except:
			pass

		os.system( "chmod a-w \"%s\"" % path )

	def setBackupBasePath( self, value ):
		self._BASE_BACKUP_PATH = value

	def lockFile( self ):
		return os.path.join( self.backupPath(), self._LOCK_FILE_NAME )

	def includeFolders( self ):
		return self._INCLUDE_FOLDERS

	def setIncludeFolders( self, value ):
		self._INCLUDE_FOLDERS = value

	def excludePatterns( self ):
		return self._EXCLUDE_PATTERNS

	def setExcludePatterns( self, value ):
		self._EXCLUDE_PATTERNS = value

	def automaticBackup( self ):
		return self._AUTOMATIC_BACKUP

	def setAutomaticBackup( self, value ):
		self._AUTOMATIC_BACKUP = value
		self.setupCron()

	def dontRemoveNamedSnapshots( self ):
		return self._DONT_REMOVE_NAMED_SNAPSHOTS != 0

	def setDontRemoveNamedSnapshots( self, value ):
		if value:
			self._DONT_REMOVE_NAMED_SNAPSHOTS = 1
		else:
			self._DONT_REMOVE_NAMED_SNAPSHOTS = 0

	def removeOldBackups( self ):
		return self._REMOVE_OLD_BACKUPS != 0 and self._REMOVE_OLD_BACKUPS_VALUE > 0

	def removeOldBackupsValue( self ):
		return self._REMOVE_OLD_BACKUPS_VALUE

	def removeOldBackupsUnit( self ):
		return self._REMOVE_OLD_BACKUPS_UNIT

	def setRemoveOldBackups( self, enabled, value, unit ):
		if enabled:
			self._REMOVE_OLD_BACKUPS = 1
		else:
			self._REMOVE_OLD_BACKUPS = 0

		self._REMOVE_OLD_BACKUPS_VALUE = value
		self._REMOVE_OLD_BACKUPS_UNIT = unit

	def removeOldBackupsDate( self ):
		if not self.removeOldBackups():
			return datetime.date( 1, 1, 1 )

		if self._REMOVE_OLD_BACKUPS_UNIT == self.DAY: 
			date = datetime.date.today()
			date = date - datetime.timedelta( days = self._REMOVE_OLD_BACKUPS_VALUE )
			return date

		if self._REMOVE_OLD_BACKUPS_UNIT == self.WEEK:
			date = datetime.date.today()
			date = date - datetime.timedelta( days = 7 * self._REMOVE_OLD_BACKUPS_VALUE )
			return date
		
		if self._REMOVE_OLD_BACKUPS_UNIT == self.YEAR:
			date = datetime.date.today()
			return date.replace( year = date.year - self._REMOVE_OLD_BACKUPS_VALUE )
		
		return datetime.date( 1, 1, 1 )

	def diffCmd( self ):
		return ( self.DIFF_CMD, self.DIFF_CMD_PARAMS )

	def setDiffCmd( self, diffCmd, diffCmdParams ):
		self.DIFF_CMD = diffCmd
		self.DIFF_CMD_PARAMS = diffCmdParams

	def minFreeSpace( self ):
		return self._MIN_FREE_SPACE != 0 and self._MIN_FREE_SPACE_VALUE > 0

	def minFreeSpaceValue( self ):
		return self._MIN_FREE_SPACE_VALUE

	def minFreeSpaceUnit( self ):
		return self._MIN_FREE_SPACE_UNIT

	def setMinFreeSpace( self, enabled, value, unit ):
		if enabled:
			self._MIN_FREE_SPACE = 1
		else:
			self._MIN_FREE_SPACE = 0

		self._MIN_FREE_SPACE_VALUE = value
		self._MIN_FREE_SPACE_UNIT = unit

	def minFreeSpaceValueInMb( self ):
		if not self.minFreeSpace():
			return 0

		value = self.minFreeSpaceValue() #Mb
		if self._MIN_FREE_SPACE_UNIT == self.DISK_UNIT_MB:
			return value

		value *= 1024 #Gb
		if self._MIN_FREE_SPACE_UNIT == self.DISK_UNIT_GB:
			return value

		return 0

	def load( self ):
		configFile = ConfigFile()
		configFile.load( self._GLOBAL_CONFIG_PATH )
		configFile.append( self._CONFIG_PATH )

		self._BASE_BACKUP_PATH = configFile.getString( 'BASE_BACKUP_PATH', self._BASE_BACKUP_PATH )
		self._INCLUDE_FOLDERS = configFile.getString( 'INCLUDE_FOLDERS', self._INCLUDE_FOLDERS )
		self._EXCLUDE_PATTERNS = configFile.getString( 'EXCLUDE_PATTERNS', self._EXCLUDE_PATTERNS )
		self._AUTOMATIC_BACKUP = configFile.getInt( 'AUTOMATIC_BACKUP', self._AUTOMATIC_BACKUP )
		self._REMOVE_OLD_BACKUPS = configFile.getInt( 'REMOVE_OLD_BACKUPS', self._REMOVE_OLD_BACKUPS )
		self._REMOVE_OLD_BACKUPS_VALUE = configFile.getInt( 'REMOVE_OLD_BACKUPS_VALUE', self._REMOVE_OLD_BACKUPS_VALUE )
		self._REMOVE_OLD_BACKUPS_UNIT = configFile.getInt( 'REMOVE_OLD_BACKUPS_UNIT', self._REMOVE_OLD_BACKUPS_UNIT )
		self._MIN_FREE_SPACE = configFile.getInt( 'MIN_FREE_SPACE', self._MIN_FREE_SPACE )
		self._MIN_FREE_SPACE_VALUE = configFile.getInt( 'MIN_FREE_SPACE_VALUE', self._MIN_FREE_SPACE_VALUE )
		self._MIN_FREE_SPACE_UNIT = configFile.getInt( 'MIN_FREE_SPACE_UNIT', self._MIN_FREE_SPACE_UNIT )
		self._DONT_REMOVE_NAMED_SNAPSHOTS = configFile.getInt( 'DONT_REMOVE_NAMED_SNAPSHOTS', 1 )

		self.MAIN_WINDOW_X = configFile.getInt( 'MAIN_WINDOW_X', -1 )
		self.MAIN_WINDOW_Y = configFile.getInt( 'MAIN_WINDOW_Y', -1 )
		self.MAIN_WINDOW_HEIGHT = configFile.getInt( 'MAIN_WINDOW_HEIGHT', -1 )
		self.MAIN_WINDOW_WIDTH = configFile.getInt( 'MAIN_WINDOW_WIDTH', -1 )
		self.MAIN_WINDOW_HPANED1_POSITION = configFile.getInt( 'MAIN_WINDOW_HPANED1_POSITION', -1 )
		self.MAIN_WINDOW_HPANED2_POSITION = configFile.getInt( 'MAIN_WINDOW_HPANED2_POSITION', -1 )
		self.LAST_PATH = configFile.getString( 'LAST_PATH', '' )

		self.DIFF_CMD = configFile.getString( 'DIFF_CMD', 'meld' )
		self.DIFF_CMD_PARAMS = configFile.getString( 'DIFF_CMD_PARAMS', '%1 %2' )

	def save( self ):
		os.system( "mkdir -p \"%s\"" % self._CONFIG_FOLDER )
		configFile = ConfigFile()

		configFile.setString( 'BASE_BACKUP_PATH', self._BASE_BACKUP_PATH )
		configFile.setString( 'INCLUDE_FOLDERS', self._INCLUDE_FOLDERS )
		configFile.setString( 'EXCLUDE_PATTERNS', self._EXCLUDE_PATTERNS )
		configFile.setInt( 'AUTOMATIC_BACKUP', self._AUTOMATIC_BACKUP )
		configFile.setInt( 'REMOVE_OLD_BACKUPS', self._REMOVE_OLD_BACKUPS )
		configFile.setInt( 'REMOVE_OLD_BACKUPS_VALUE', self._REMOVE_OLD_BACKUPS_VALUE )
		configFile.setInt( 'REMOVE_OLD_BACKUPS_UNIT', self._REMOVE_OLD_BACKUPS_UNIT )
		configFile.setInt( 'MIN_FREE_SPACE', self._MIN_FREE_SPACE )
		configFile.setInt( 'MIN_FREE_SPACE_VALUE', self._MIN_FREE_SPACE_VALUE )
		configFile.setInt( 'MIN_FREE_SPACE_UNIT', self._MIN_FREE_SPACE_UNIT )
		configFile.setInt( 'DONT_REMOVE_NAMED_SNAPSHOTS', self._DONT_REMOVE_NAMED_SNAPSHOTS )

		configFile.setInt( 'MAIN_WINDOW_X', self.MAIN_WINDOW_X )
		configFile.setInt( 'MAIN_WINDOW_Y', self.MAIN_WINDOW_Y )
		configFile.setInt( 'MAIN_WINDOW_HEIGHT', self.MAIN_WINDOW_HEIGHT )
		configFile.setInt( 'MAIN_WINDOW_WIDTH', self.MAIN_WINDOW_WIDTH )
		configFile.setInt( 'MAIN_WINDOW_HPANED1_POSITION', self.MAIN_WINDOW_HPANED1_POSITION )
		configFile.setInt( 'MAIN_WINDOW_HPANED2_POSITION', self.MAIN_WINDOW_HPANED2_POSITION )
		configFile.setString( 'LAST_PATH', self.LAST_PATH )

		configFile.setString( 'DIFF_CMD', self.DIFF_CMD )
		configFile.setString( 'DIFF_CMD_PARAMS', self.DIFF_CMD_PARAMS )

		configFile.save( self._CONFIG_PATH )

	def isConfigured( self ):
		if len( self._BASE_BACKUP_PATH ) == 0:
			return False

		if len( self._INCLUDE_FOLDERS ) == 0:
			return False

		return True

	def canBackup( self ):
		if not self.isConfigured():
			return False

		if not os.path.isdir( self._BASE_BACKUP_PATH ):
			return False

		path = self.backupPath()
		os.system( "mkdir -p \"%s\"" % path )
	
		if not os.path.isdir( path ):
			return False

		return True

	def setupCron( self ):
		#remove old cron
		os.system( "crontab -l | grep -v backintime | crontab -" )

		newCron = ""

		if self.automaticBackup() == self.HOUR:
			newCron = 'echo "@hourly {cmd}"'
		elif self.automaticBackup() == self.DAY:
			newCron = 'echo "@daily {cmd}"'
		elif self.automaticBackup() == self.WEEK:
			newCron = 'echo "@weekly {cmd}"'
		elif self.automaticBackup() == self.MONTH:
			newCron = 'echo "@monthly {cmd}"'
		elif self.automaticBackup() == self._5_MIN:
			newCron = ''
			for minute in xrange( 0, 59, 5 ):
				if 0 != minute:
					newCron = newCron + '; '
				newCron = newCron + "echo \"%s * * * * {cmd}\"" % minute
		elif self.automaticBackup() == self._10_MIN:
			newCron = ''
			for minute in xrange( 0, 59, 10 ):
				if 0 != minute:
					newCron = newCron + '; '
				newCron = newCron + "echo \"%s * * * * {cmd}\"" % minute

		if len( newCron ) > 0:
			newCron = newCron.replace( '{cmd}', 'nice -n 19 /usr/bin/backintime --backup' )
			os.system( "( crontab -l; %s ) | crontab -" % newCron )

class ConfigFile:
	def __init__( self ):
		self.dict = {}

	def save( self, filename ):
		try:
			file = open( filename, 'w' )
			for key, value in self.dict.items():
				file.write( "%s=%s\n" % ( key, value ) )
			file.close()
		except:
			pass

	def load( self, filename ):
		self.dict = {}
		self.append( filename )

	def append( self, filename ):
		lines = []

		try:
			file = open( filename, 'r' )
			lines = file.readlines()
			file.close()
		except:
			pass

		for line in lines:
			items = line.split( '=' )
			if len( items ) == 2:
				self.dict[ items[ 0 ] ] = items[ 1 ][ : -1 ]

	def getString( self, key, defaultValue = '' ):
		try:
			return self.dict[ key ]
		except:
			return defaultValue

	def setString( self, key, value ):
		self.dict[ key ] = value

	def getInt( self, key, defaultValue = 0 ):
		try:
			return int( self.dict[ key ] )
		except:
			return defaultValue

	def setInt( self, key, value ):
		self.dict[ key ] = str( value )


if __name__ == "__main__":
	config = Config()
	print "BASE_BACKUP_PATH = %s" % config._BASE_BACKUP_PATH
	print "INCLUDE_FOLDERS = %s" % config._INCLUDE_FOLDERS
	print "EXCLUDE_PATTERNS = %s" % config._EXCLUDE_PATTERNS
	print "AUTOMATIC_BACKUP = %s" % config._AUTOMATIC_BACKUP
	print "REMOVE_OLD_BACKUPS = %s" % config._REMOVE_OLD_BACKUPS
	print "REMOVE_OLD_BACKUPS_VALUE = %s" % config._REMOVE_OLD_BACKUPS_VALUE
	print "REMOVE_OLD_BACKUPS_UNIT = %s" % config._REMOVE_OLD_BACKUPS_UNIT
	print "MIN_FREE_SPACE = %s" % config._MIN_FREE_SPACE
	print "MIN_FREE_SPACE_VALUE = %s" % config._MIN_FREE_SPACE_VALUE
	print "MIN_FREE_SPACE_UNIT = %s" % config._MIN_FREE_SPACE_UNIT

