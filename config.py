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


import os.path
import os
import datetime
import gettext

import configfile
import tools


_=gettext.gettext

gettext.bindtextdomain( 'backintime', '/usr/share/locale' )
gettext.textdomain( 'backintime' )


class Config( configfile.ConfigFile ):
	APP_NAME = 'Back In Time'
	VERSION = '0.9.3beta1'

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

		self._GLOBAL_CONFIG_PATH = '/etc/backintime/config2'
		self._LOCAL_CONFIG_FOLDER = os.path.expanduser( '~/.config/backintime' )
		os.system( "mkdir -p \"%s\"" % self._LOCAL_CONFIG_FOLDER )
		self._LOCAL_CONFIG_PATH = os.path.join( self._LOCAL_CONFIG_FOLDER, 'config2' )

		self.load( self._GLOBAL_CONFIG_PATH )
		self.append( self._LOCAL_CONFIG_PATH )

		OLD_CONFIG_PATH = os.path.join( self._LOCAL_CONFIG_FOLDER, 'config' )
		if os.path.exists( OLD_CONFIG_PATH ): 
			#import old config
			old_config = configfile.ConfigFile()
			old_config.load( OLD_CONFIG_PATH )

			dict = {
				'BASE_BACKUP_PATH' : 'snapshots.path',
				'INCLUDE_FOLDERS' : 'snapshots.include_folders',
				'EXCLUDE_PATTERNS' : 'snapshots.exclude_patterns',
				'AUTOMATIC_BACKUP' : 'snapshots.automatic_backup_mode',
				'REMOVE_OLD_BACKUPS' : 'snapshots.remove_old_snapshots.enabled',
				'REMOVE_OLD_BACKUPS_VALUE' : 'snapshots.remove_old_snapshots.value',
				'REMOVE_OLD_BACKUPS_UNIT' : 'snapshots.remove_old_snapshots.unit',
				'MIN_FREE_SPACE' : 'snapshots.min_free_space.enabled',
				'MIN_FREE_SPACE_VALUE' : 'snapshots.min_free_space.value',
				'MIN_FREE_SPACE_UNIT' : 'snapshots.min_free_space.unit',
				'DONT_REMOVE_NAMED_SNAPSHOTS' : 'snapshots.dont_remove_named_snapshots',
				'DIFF_CMD' : 'gnome.diff.cmd',
				'DIFF_CMD_PARAMS' : 'gnome.diff.params',
				'LAST_PATH' : 'gnome.last_path',
				'MAIN_WINDOW_X' : 'gnome.main_window.x',
				'MAIN_WINDOW_Y' : 'gnome.main_window.y',
				'MAIN_WINDOW_WIDTH' : 'gnome.main_window.width',
				'MAIN_WINDOW_HEIGHT' : 'gnome.main_window.height',
				'MAIN_WINDOW_HPANED1_POSITION' : 'gnome.main_window.hpaned1',
				'MAIN_WINDOW_HPANED2_POSITION' : 'gnome.main_window.hpaned2'
			}

			if self.get_if_dont_exists( dict, old_config ):
				self.save()

			os.system( "rm \"%s\"" % OLD_CONFIG_PATH )

	def save( self ):
		configfile.ConfigFile.save( self, self._LOCAL_CONFIG_PATH )

	def check_take_snapshot_params( self, snapshots_path, include_list, exclude_list ):
		#returns None or ( ID, message ) //0 - snapshots path, 1 - include list, 2 - exclude list
		if len( snapshots_path ) == 0 or not os.path.isdir( snapshots_path ):
			return ( 0, _('Snapshots directory is not valid !') )

		if len( snapshots_path ) <= 1:
			return ( 0, _('Snapshots directory can\'t be the root directory !') )

		if len( include_list ) <= 0:
			return ( 1, _('You must select at least one directory to backup !') )

		snapshots_path2 = snapshots_path + '/'

		for path in include_list:
			if path == snapshots_path:
				print "Path: " + path
				print "SnapshotsPath: " + snapshots_path 
				return ( 1, _('Snapshots directory can\'t be in "Backup Directories" !') )
			
			if len( path ) >= len( snapshots_path2 ):
				if path[ : len( snapshots_path2 ) ] == snapshots_path2:
					print "Path: " + path
					print "SnapshotsPath2: " + snapshots_path2
					return ( 1, _('Snapshots directory can\'t be in "Backup Directories" !') )
			else:
				path2 = path + '/'
				if len( path2 ) < len( snapshots_path ):
					if path2 == snapshots_path[ : len( path2 ) ]:
						print "Path2: " + path2
						print "SnapshotsPath: " + snapshots_path 
						return ( 1, _('"Backup directories" can\'t include snapshots directory !') )

		for exclude in exclude_list:
			if exclude.find( ':' ) >= 0:
				return ( 2, _('"Exclude pattern" can\'t contain ":" char !') )

		return None

	def get_snapshots_path( self ):
		return self.get_str_value( 'snapshots.path', '' )

	def get_snapshots_full_path( self ):
		return os.path.join( self.get_snapshots_path(), 'backintime' ) 

	def set_snapshots_path( self, value ):
		self.set_str_value( 'snapshots.path', value )
		if len( value ) > 0:
			if os.path.isdir( value ):
				os.system( "mkdir -p \"%s\"" % self.get_snapshots_full_path() )

	def get_include_folders( self ):
		value = self.get_str_value( 'snapshots.include_folders', '' )
		if len( value ) <= 0:
			return []
		return value.split(':')

	def set_include_folders( self, list ):
		self.set_str_value( 'snapshots.include_folders', ':'.join( list ) )

	def get_exclude_patterns( self ):
		value = self.get_str_value( 'snapshots.exclude_patterns', '.*:*.backup*:*~' )
		if len( value ) <= 0:
			return []
		return value.split(':')

	def set_exclude_patterns( self, list ):
		self.set_str_value( 'snapshots.exclude_patterns', ':'.join( list ) )

	def get_automatic_backup_mode( self ):
		return self.get_int_value( 'snapshots.automatic_backup_mode', self.NONE )

	def set_automatic_backup_mode( self, value ):
		self.set_int_value( 'snapshots.automatic_backup_mode', value )
		self.setup_cron()

	def get_remove_old_snapshots( self ):
		return ( self.get_bool_value( 'snapshots.remove_old_snapshots.enabled', True ),
				 self.get_int_value( 'snapshots.remove_old_snapshots.value', 10 ),
				 self.get_int_value( 'snapshots.remove_old_snapshots.unit', self.YEAR ) )
	
	def is_remove_old_snapshots_enabled( self ):
		return self.get_bool_value( 'snapshots.remove_old_snapshots.enabled', True )
	
	def get_remove_old_snapshots_date( self ):
		enabled, value, unit = self.get_remove_old_snapshots()
		if not enabled:
			return datetime.date( 1, 1, 1 )

		if unit == self.DAY: 
			date = datetime.date.today()
			date = date - datetime.timedelta( days = value )
			return date

		if unit == self.WEEK:
			date = datetime.date.today()
			date = date - datetime.timedelta( days = 7 * value )
			return date
		
		if unit == self.YEAR:
			date = datetime.date.today()
			return date.replace( year = date.year - value )
		
		return datetime.date( 1, 1, 1 )

	def set_remove_old_snapshots( self, enabled, value, unit ):
		self.set_bool_value( 'snapshots.remove_old_snapshots.enabled', enabled )
		self.set_int_value( 'snapshots.remove_old_snapshots.value', value )
		self.set_int_value( 'snapshots.remove_old_snapshots.unit', unit )

	def get_min_free_space( self ):
		return ( self.get_bool_value( 'snapshots.min_free_space.enabled', True ),
				 self.get_int_value( 'snapshots.min_free_space.value', 1 ),
				 self.get_int_value( 'snapshots.min_free_space.unit', self.DISK_UNIT_GB ) )
	
	def is_min_free_space_enabled( self ):
		return self.get_bool_value( 'snapshots.min_free_space.enabled', True )

	def get_min_free_space_in_mb( self ):
		enabled, value, unit = self.get_min_free_space()
		if not enabled:
			return 0

		if self.DISK_UNIT_MB == unit:
			return value

		value *= 1024 #Gb
		if self.DISK_UNIT_GB == unit:
			return value

		return 0

	def set_min_free_space( self, enabled, value, unit ):
		self.set_bool_value( 'snapshots.min_free_space.enabled', enabled )
		self.set_int_value( 'snapshots.min_free_space.value', value )
		self.set_int_value( 'snapshots.min_free_space.unit', unit )

	def get_dont_remove_named_snapshots( self ):
		return self.get_bool_value( 'snapshots.dont_remove_named_snapshots', True )

	def set_dont_remove_named_snapshots( self, value ):
		self.get_bool_value( 'snapshots.dont_remove_named_snapshots', value )
	
	def get_app_path( self ):
		return self._APP_PATH

	def get_doc_path( self ):
		return self._DOC_PATH

	def get_app_instance_file( self ):
		return os.path.join( self._LOCAL_CONFIG_FOLDER, 'app.lock' )

	def get_take_snapshot_instance_file( self ):
		return os.path.join( self._LOCAL_CONFIG_FOLDER, 'snapshot.lock' )

	def get_license( self ):
		return tools.read_file( os.path.join( self.get_doc_path(), 'LICENSE' ) )

	def get_translations( self ):
		return tools.read_file( os.path.join( self.get_doc_path(), 'TRANSLATIONS' ) )

	def get_authors( self ):
		return tools.read_file( os.path.join( self.get_doc_path(), 'AUTHORS' ) )

	def is_configured( self ):
		if len( self.get_snapshots_path() ) == 0:
			return False

		if len( self.get_include_folders() ) == 0:
			return False

		return True

	def can_backup( self ):
		if not self.is_configured():
			return False

		if not os.path.isdir( self.get_snapshots_path() ):
			return False

		path = self.get_snapshots_full_path()
		os.system( "mkdir -p \"%s\"" % path )
	
		if not os.path.isdir( path ):
			return False

		return True

	def setup_cron( self ):
		#remove old cron
		os.system( "crontab -l | grep -v backintime | crontab -" )

		cron_lines = ''
		auto_backup_mode = self.get_automatic_backup_mode()

		if self.HOUR == auto_backup_mode:
			cron_lines = 'echo "@hourly {cmd}"'
		elif self.DAY == auto_backup_mode:
			cron_lines = 'echo "@daily {cmd}"'
		elif self.WEEK == auto_backup_mode:
			cron_lines = 'echo "@weekly {cmd}"'
		elif self.MONTH == auto_backup_mode:
			cron_lines = 'echo "@monthly {cmd}"'
		elif self._5_MIN == auto_backup_mode:
			cron_lines = ''
			for minute in xrange( 0, 59, 5 ):
				if 0 != minute:
					cron_lines = cron_lines + '; '
				cron_lines = cron_lines + "echo \"%s * * * * {cmd}\"" % minute
		elif self._10_MIN == auto_backup_mode:
			cron_lines = ''
			for minute in xrange( 0, 59, 10 ):
				if 0 != minute:
					cron_lines = cron_lines + '; '
				cron_lines = cron_lines + "echo \"%s * * * * {cmd}\"" % minute

		if len( cron_lines ) > 0:
			cron_lines = cron_lines.replace( '{cmd}', 'nice -n 19 /usr/bin/backintime --backup' )
			os.system( "( crontab -l; %s ) | crontab -" % cron_lines )


if __name__ == "__main__":
	config = Config()
	print config.dict
	print "snapshots path=" + config.get_snapshots_path()
	print "include folders=" + config.get_include_folders()
	print "explude patterns=" + config.get_exclude_patterns()

