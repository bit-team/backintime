#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
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
import socket
import random

import configfile
import tools
import logger

_=gettext.gettext

gettext.bindtextdomain( 'backintime', '/usr/share/locale' )
gettext.textdomain( 'backintime' )


class Config( configfile.ConfigFileWithProfiles ):
	APP_NAME = 'Back In Time'
	VERSION = '0.9.99beta11'
	COPYRIGHT = 'Copyright (c) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey'
	CONFIG_VERSION = 4

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
				NONE : _('Disabled'), 
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
		configfile.ConfigFileWithProfiles.__init__( self, _('Main profile') )

		self._APP_PATH =  os.path.dirname( os.path.abspath( os.path.dirname( __file__ ) ) )
		self._DOC_PATH = '/usr/share/doc/backintime'
		if os.path.exists( os.path.join( self._APP_PATH, 'LICENSE' ) ):
			self._DOC_PATH = self._APP_PATH

		self._GLOBAL_CONFIG_PATH = '/etc/backintime/config'

		HOME_FOLDER = os.path.expanduser( '~' )
		self._LOCAL_DATA_FOLDER = os.path.join( os.getenv( 'XDG_DATA_HOME', '$HOME/.local/share' ).replace( '$HOME', HOME_FOLDER ), 'backintime' )
		self._LOCAL_CONFIG_FOLDER = os.path.join( os.getenv( 'XDG_CONFIG_HOME', '$HOME/.config' ).replace( '$HOME', HOME_FOLDER ), 'backintime' )

		#self._LOCAL_CONFIG_FOLDER = os.path.expanduser( '~/.config/backintime' )
		tools.make_dirs( self._LOCAL_CONFIG_FOLDER )
		tools.make_dirs( self._LOCAL_DATA_FOLDER )

		self._LOCAL_CONFIG_PATH = os.path.join( self._LOCAL_CONFIG_FOLDER, 'config' )
		old_path = os.path.join( self._LOCAL_CONFIG_FOLDER, 'config2' )

		if os.path.exists( old_path ):
			if os.path.exists( self._LOCAL_CONFIG_PATH ):
				os.system( "rm \"%s\"" % old_path )
			else:
				os.system( "mv \"%s\" \"%s\"" % ( old_path, self._LOCAL_CONFIG_PATH ) )

		self.load( self._GLOBAL_CONFIG_PATH )
		self.append( self._LOCAL_CONFIG_PATH )

		if self.get_int_value( 'config.version', 1 ) < 2:
			#remap old items
			self.remap_key( 'BASE_BACKUP_PATH', 'snapshots.path' )
			self.remap_key( 'INCLUDE_FOLDERS', 'snapshots.include_folders' )
			self.remap_key( 'EXCLUDE_PATTERNS', 'snapshots.exclude_patterns' )
			self.remap_key( 'AUTOMATIC_BACKUP', 'snapshots.automatic_backup_mode' )
			self.remap_key( 'REMOVE_OLD_BACKUPS', 'snapshots.remove_old_snapshots.enabled' )
			self.remap_key( 'REMOVE_OLD_BACKUPS_VALUE', 'snapshots.remove_old_snapshots.value' )
			self.remap_key( 'REMOVE_OLD_BACKUPS_UNIT', 'snapshots.remove_old_snapshots.unit' )
			self.remap_key( 'MIN_FREE_SPACE', 'snapshots.min_free_space.enabled' )
			self.remap_key( 'MIN_FREE_SPACE_VALUE', 'snapshots.min_free_space.value' )
			self.remap_key( 'MIN_FREE_SPACE_UNIT', 'snapshots.min_free_space.unit' )
			self.remap_key( 'DONT_REMOVE_NAMED_SNAPSHOTS', 'snapshots.dont_remove_named_snapshots' )
			self.remap_key( 'DIFF_CMD', 'gnome.diff.cmd' )
			self.remap_key( 'DIFF_CMD_PARAMS', 'gnome.diff.params' )
			self.remap_key( 'LAST_PATH', 'gnome.last_path' )
			self.remap_key( 'MAIN_WINDOW_X', 'gnome.main_window.x' )
			self.remap_key( 'MAIN_WINDOW_Y', 'gnome.main_window.y' )
			self.remap_key( 'MAIN_WINDOW_WIDTH', 'gnome.main_window.width' )
			self.remap_key( 'MAIN_WINDOW_HEIGHT', 'gnome.main_window.height' )
			self.remap_key( 'MAIN_WINDOW_HPANED1_POSITION', 'gnome.main_window.hpaned1' )
			self.remap_key( 'MAIN_WINDOW_HPANED2_POSITION', 'gnome.main_window.hpaned2' )
			self.set_int_value( 'config.version', 2 )

		if self.get_int_value( 'config.version', 1 ) < 3:
			self.remap_key( 'snapshots.path', 'profile1.snapshots.path' )
			self.remap_key( 'snapshots.include_folders', 'profile1.snapshots.include_folders' )
			self.remap_key( 'snapshots.exclude_patterns', 'profile1.snapshots.exclude_patterns' )
			self.remap_key( 'snapshots.automatic_backup_mode', 'profile1.snapshots.automatic_backup_mode' )
			self.remap_key( 'snapshots.remove_old_snapshots.enabled', 'profile1.snapshots.remove_old_snapshots.enabled' )
			self.remap_key( 'snapshots.remove_old_snapshots.value', 'profile1.snapshots.remove_old_snapshots.value' )
			self.remap_key( 'snapshots.remove_old_snapshots.unit', 'profile1.snapshots.remove_old_snapshots.unit' )
			self.remap_key( 'snapshots.min_free_space.enabled', 'profile1.snapshots.min_free_space.enabled' )
			self.remap_key( 'snapshots.min_free_space.value', 'profile1.snapshots.min_free_space.value' )
			self.remap_key( 'snapshots.min_free_space.unit', 'profile1.snapshots.min_free_space.unit' )
			self.remap_key( 'snapshots.dont_remove_named_snapshots', 'profile1.snapshots.dont_remove_named_snapshots' )
			self.set_int_value( 'config.version', 3 )
			
		if self.get_int_value( 'config.version', 1 ) < 4:
			# version 4 uses as path backintime/machine/user/profile_id
			# but must be able to read old paths
			profiles = self.get_profiles()
			self.set_bool_value( 'update.other_folders', True )
			logger.info( "Update to config version 4: other snapshot locations" )
									
			for profile_id in profiles:
				old_folder = self.get_snapshots_path( profile_id )
				other_folder = os.path.join( old_folder, 'backintime' )
				other_folder_key = 'profile' + str( profile_id ) + '.snapshots.other_folders'
				self.set_str_value( other_folder_key, other_folder )
				#self.set_snapshots_path( old_folder, profile_id )
				tag = str( random.randint(100, 999) )
				logger.info( "Random tag for profile %s: %s" %( profile_id, tag ) )
				self.set_profile_str_value( 'snapshots.tag', tag, profile_id ) 
	
			self.set_int_value( 'config.version', 4 )

	def save( self ):
		configfile.ConfigFile.save( self, self._LOCAL_CONFIG_PATH )

	def check_config( self ):
		profiles = self.get_profiles()

		checked_profiles = []

		for profile_id in profiles:
			profile_name = self.get_profile_name( profile_id )
			snapshots_path = self.get_snapshots_path( profile_id )

			#check snapshots path
			if len( snapshots_path ) <= 0:
				self.notify_error( _('Profile: "%s"') % profile_name + '\n' + _('Snapshots folder is not valid !') )
				return False

			## Should not check for similar snapshot paths any longer! 
			#for other_profile in checked_profiles:
			#	if snapshots_path == self.get_snapshots_path( other_profile[0] ):
			#		self.notify_error( _('Profiles "%s" and "%s" have the same snapshots path !') % ( profile_name, other_profile[1] ) )
			#		return False
			#
			#if not os.path.isdir( snapshots_path ):
			#	return ( 0, _('Snapshots folder is not valid !') )

			#if len( self.get_snapshots_path( profile_id ) ) <= 1:
			#	return ( 0, _('Snapshots folder can\'t be the root folder !') )

			#check include
			include_list = self.get_include_folders( profile_id )
			if len( include_list ) <= 0:
				self.notify_error( _('Profile: "%s"') % profile_name + '\n' + _('You must select at least one folder to backup !') )
				return False

			snapshots_path2 = snapshots_path + '/'

			for item in include_list:
				path = item[0]
				if path == snapshots_path:
					self.notify_error( _('Profile: "%s"') % profile_name + '\n' + _('You can\'t include backup folder !') )
					return False
			
				if len( path ) >= len( snapshots_path2 ):
					if path[ : len( snapshots_path2 ) ] == snapshots_path2:
						self.notify_error( _('Profile: "%s"') % profile_name + '\n' + _('You can\'t include a backup sub-folder !') )
						return False

			checked_profiles.append( ( profile_id, profile_name ) )

		return True

	def get_snapshots_path( self, profile_id = None ):
		return self.get_profile_str_value( 'snapshots.path', '', profile_id )

	def get_snapshots_full_path( self, profile_id = None, version = None ):
		'''Returns the full path for the snapshots: .../backintime/machine/user/profile_id/'''
		if version is None:
			version = self.get_int_value( 'config.version', 1 )

		if version < 4:
			return os.path.join( self.get_snapshots_path( profile_id ), 'backintime' )
		else:
			machine = socket.gethostname()
			user = os.environ['LOGNAME']
			if profile_id is None:
				profile_id = self.get_current_profile()
			return os.path.join( self.get_snapshots_path( profile_id ), 'backintime', machine, user, profile_id ) 

	def set_snapshots_path( self, value, profile_id = None ):
		"""Sets the snapshot path to value, initializes, and checks it"""
		if len( value ) <= 0:
			return False

		if profile_id == None:
		#	print "BUG: calling set_snapshots_path without profile_id!"
		#	tjoep
		#	return False
			profile_id = self.get_current_profile()

		if not os.path.isdir( value ):
			self.notify_error( _( '%s is not a folder !' ) )
			return False

		#Initialize the snapshots folder
		print "Check snapshot folder: %s" % value
		machine = socket.gethostname()
		user = os.environ['LOGNAME']
		full_path = os.path.join( value, 'backintime', machine, user, profile_id ) 
		if not os.path.isdir( full_path ):
			print "Create folder: %s" % full_path
			tools.make_dirs( full_path )
			if not os.path.isdir( full_path ):
				self.notify_error( _( 'Can\'t write to: %s\nAre you sure you have write access ?' % value ) )
				return False
		
		#Test write access for the folder
		check_path = os.path.join( full_path, 'check' )
		tools.make_dirs( check_path )
		if not os.path.isdir( check_path ):
			self.notify_error( _( 'Can\'t write to: %s\nAre you sure you have write access ?' % full_path ) )
			return False
		
		os.rmdir( check_path )
		self.set_profile_str_value( 'snapshots.path', value, profile_id )
		return True

	def get_other_folders_paths( self, profile_id = None ):
		'''Returns the other snapshots folders paths as a list'''
		value = self.get_profile_str_value( 'snapshots.other_folders', '', profile_id )
		if len( value ) <= 0:
			return []
			
		paths = []

		for item in value.split(':'):
			fields = item.split( '|' )

			path = os.path.expanduser( item )
			path = os.path.abspath( path )

			paths.append( ( path ) )

		return paths
	
	def get_include_folders( self, profile_id = None ):
		value = self.get_profile_str_value( 'snapshots.include_folders', '', profile_id )
		if len( value ) <= 0:
			return []

		paths = []

		for item in value.split(':'):
			fields = item.split( '|' )

			path = os.path.expanduser( fields[0] )
			path = os.path.abspath( path )

			if len( fields ) >= 2:
				automatic_backup_mode = int( fields[1] )
			else:
				automatic_backup_mode = self.get_automatic_backup_mode()

			#paths.append( ( path, automatic_backup_mode ) )
			paths.append( path )

		return paths

	def set_include_folders( self, list, profile_id = None ):
		value = ''

		for item in list:
			if len( value ) > 0:
				value = value + ':'
			#value = value + item[0] + '|' + str( item[1] )
			value = value + item

		self.set_profile_str_value( 'snapshots.include_folders', value, profile_id )
 
	def get_exclude_patterns( self, profile_id = None ):
		'''Gets the exclude patterns (default: virtual file systems, caches, thumbnails, trashbins, and backups)'''
		value = self.get_profile_str_value( 'snapshots.exclude_patterns', '.gvfs:.cache*:[Cc]ache*:.thumbnails*:[Tt]rash*:*.backup*:*~', profile_id )
		if len( value ) <= 0:
			return []
		return value.split(':')

	def set_exclude_patterns( self, list, profile_id = None ):
		self.set_profile_str_value( 'snapshots.exclude_patterns', ':'.join( list ), profile_id )

	def get_tag( self, profile_id = None ):
		return self.get_profile_str_value( 'snapshots.tag', str(random.randint(100, 999)), profile_id )

	def get_automatic_backup_mode( self, profile_id = None ):
		return self.get_profile_int_value( 'snapshots.automatic_backup_mode', self.NONE, profile_id )

	def set_automatic_backup_mode( self, value, profile_id = None ):
		self.set_profile_int_value( 'snapshots.automatic_backup_mode', value, profile_id )

	#def get_per_directory_schedule( self, profile_id = None ):
	#	return self.get_profile_bool_value( 'snapshots.expert.per_directory_schedule', False, profile_id )

	#def set_per_directory_schedule( self, value, profile_id = None ):
	#	return self.set_profile_bool_value( 'snapshots.expert.per_directory_schedule', value, profile_id )

	def get_remove_old_snapshots( self, profile_id = None ):
		return ( self.get_profile_bool_value( 'snapshots.remove_old_snapshots.enabled', True, profile_id ),
				 self.get_profile_int_value( 'snapshots.remove_old_snapshots.value', 10, profile_id ),
				 self.get_profile_int_value( 'snapshots.remove_old_snapshots.unit', self.YEAR, profile_id ) )
	
	def is_remove_old_snapshots_enabled( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.remove_old_snapshots.enabled', True, profile_id )
	
	def get_remove_old_snapshots_date( self, profile_id = None ):
		enabled, value, unit = self.get_remove_old_snapshots( profile_id )
		if not enabled:
			return datetime.date( 1, 1, 1 )

		if unit == self.DAY: 
			date = datetime.date.today()
			date = date - datetime.timedelta( days = value )
			return date

		if unit == self.WEEK:
			date = datetime.date.today()
			date = date - datetime.timedelta( days = date.weekday() + 7 * value )
			return date
		
		if unit == self.YEAR:
			date = datetime.date.today()
			return date.replace( year = date.year - value )
		
		return datetime.date( 1, 1, 1 )

	def set_remove_old_snapshots( self, enabled, value, unit, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.remove_old_snapshots.enabled', enabled, profile_id )
		self.set_profile_int_value( 'snapshots.remove_old_snapshots.value', value, profile_id )
		self.set_profile_int_value( 'snapshots.remove_old_snapshots.unit', unit, profile_id )

	def get_min_free_space( self, profile_id = None ):
		return ( self.get_profile_bool_value( 'snapshots.min_free_space.enabled', True, profile_id ),
				 self.get_profile_int_value( 'snapshots.min_free_space.value', 1, profile_id ),
				 self.get_profile_int_value( 'snapshots.min_free_space.unit', self.DISK_UNIT_GB, profile_id ) )
	
	def is_min_free_space_enabled( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.min_free_space.enabled', True, profile_id )

	def get_min_free_space_in_mb( self, profile_id = None ):
		enabled, value, unit = self.get_min_free_space( profile_id )
		if not enabled:
			return 0

		if self.DISK_UNIT_MB == unit:
			return value

		value *= 1024 #Gb
		if self.DISK_UNIT_GB == unit:
			return value

		return 0

	def set_min_free_space( self, enabled, value, unit, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.min_free_space.enabled', enabled, profile_id )
		self.set_profile_int_value( 'snapshots.min_free_space.value', value, profile_id )
		self.set_profile_int_value( 'snapshots.min_free_space.unit', unit, profile_id )

	def get_dont_remove_named_snapshots( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.dont_remove_named_snapshots', True, profile_id )

	def set_dont_remove_named_snapshots( self, value, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.dont_remove_named_snapshots', value, profile_id )
	
	def get_smart_remove( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.smart_remove', False, profile_id )

	def set_smart_remove( self, value, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.smart_remove', value, profile_id )
	
	def is_notify_enabled( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.notify.enabled', True, profile_id )

	def set_notify_enabled( self, value, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.notify.enabled', value, profile_id )

	def is_backup_on_restore_enabled( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.backup_on_restore.enabled', True, profile_id )

	def set_backup_on_restore( self, value, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.backup_on_restore.enabled', value, profile_id )

	def is_run_nice_from_cron_enabled( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.cron.nice', True, profile_id )

	def set_run_nice_from_cron_enabled( self, value, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.cron.nice', value, profile_id )

	def is_run_ionice_from_cron_enabled( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.cron.ionice', True, profile_id )

	def set_run_ionice_from_cron_enabled( self, value, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.cron.ionice', value, profile_id )

	def is_run_ionice_from_user_enabled( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.user_backup.ionice', False, profile_id )

	def set_run_ionice_from_user_enabled( self, value, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.user_backup.ionice', value, profile_id )

	def is_no_on_battery_enabled( self, profile_id = None ):
		return self.get_profile_bool_value( 'snapshots.no_on_battery', False, profile_id )

	def set_no_on_battery_enabled( self, value, profile_id = None ):
		self.set_profile_bool_value( 'snapshots.no_on_battery', value, profile_id )

	def get_take_snapshot_user_script( self, step, profile_id = None ):
		return self.get_profile_str_value ( "snapshots.take_snapshot.%s.user.script" % step, '', profile_id )

	def set_take_snapshot_user_script( self, step, path, profile_id = None ):
		self.set_profile_str_value( "snapshots.take_snapshot.%s.user.script" % step, path, profile_id )

	def get_take_snapshot_user_script_before( self, profile_id = None ):
		return self.get_take_snapshot_user_script( 'before', profile_id )

	def set_take_snapshot_user_script_before( self, path, profile_id = None ):
		self.set_take_snapshot_user_script( 'before', path, profile_id )

	def get_take_snapshot_user_script_after( self, profile_id = None ):
		return self.get_take_snapshot_user_script( 'after', profile_id )

	def set_take_snapshot_user_script_after( self, path, profile_id = None ):
		self.set_take_snapshot_user_script( 'after', path, profile_id )

	def get_take_snapshot_user_script_new_snapshot( self, profile_id = None ):
		return self.get_take_snapshot_user_script( 'new_snapshot', profile_id = None )

	def set_take_snapshot_user_script_new_snapshot( self, path, profile_id = None ):
		self.set_take_snapshot_user_script( 'new_snapshot', path, profile_id )

	def get_take_snapshot_user_script_error( self, profile_id = None ):
		return self.get_take_snapshot_user_script( 'error', profile_id )

	def set_take_snapshot_user_script_error( self, path, profile_id = None ):
		self.set_take_snapshot_user_script( 'error', path, profile_id )

	def get_app_path( self ):
		return self._APP_PATH

	def get_doc_path( self ):
		return self._DOC_PATH

	def get_app_instance_file( self ):
		return os.path.join( self._LOCAL_DATA_FOLDER, 'app.lock' )

	def __get_file_id__( self, profile_id = None ):
		if profile_id is None:
			profile_id = self.get_current_profile()
		if profile_id == '1':
			return ''
		return profile_id

	def get_take_snapshot_message_file( self, profile_id = None ):
		return os.path.join( self._LOCAL_DATA_FOLDER, "worker%s.message" % self.__get_file_id__( profile_id ) )

	def get_take_snapshot_instance_file( self, profile_id = None ):
		return os.path.join( self._LOCAL_DATA_FOLDER, "worker%s.lock" % self.__get_file_id__( profile_id ) )

	#def get_last_snapshot_info_file( self, profile_id = None ):
	#	return os.path.join( self._LOCAL_DATA_FOLDER, "snapshot%s.last" % self.__get_file_id__( profile_id ) )

	def get_take_snapshot_user_callback( self, profile_id = None ):
		return os.path.join( self._LOCAL_CONFIG_FOLDER, "user%s.callback" % self.__get_file_id__( profile_id ) )

	def get_license( self ):
		return tools.read_file( os.path.join( self.get_doc_path(), 'LICENSE' ), '' )

	def get_translations( self ):
		return tools.read_file( os.path.join( self.get_doc_path(), 'TRANSLATIONS' ), '' )

	def get_authors( self ):
		return tools.read_file( os.path.join( self.get_doc_path(), 'AUTHORS' ), '' )

	def prepare_path( self, path ):
		if len( path ) > 1:
			if path[ -1 ] == os.sep:
				path = path[ : -1 ]
		return path

	def is_configured( self, profile_id = None ):
		'''Checks if the program is configured''' 
		if len( self.get_snapshots_path( profile_id ) ) == 0:
			return False

		if len( self.get_include_folders( profile_id ) ) == 0:
			return False

		return True
	
	def can_backup( self, profile_id = None ):
		'''Checks if snapshots_path exists''' 
		if not self.is_configured( profile_id ):
			return False

		if not os.path.isdir( self.get_snapshots_full_path( profile_id ) ):
			print "%s does not exist" % self.get_snapshots_full_path( profile_id )
			return False

		return True

	def setup_cron( self ):
		system_entry_message = "#Back In Time system entry, this will be edited by the gui:"
		
		"""We have to check if the system_entry_message is in use,
		if not then the entries are most likely from Back in Time 0.9.26
		or earlier."""
		if os.system( "crontab -l | grep '%s' > /dev/null" % system_entry_message ) != 0:
			"""Then the system entry message has not yet been used in this crontab
			therefore we assume all entries are system entries and clear them all.
			This is the old behaviour"""
			print "Clearing all backintime entries"
			os.system( "crontab -l | grep -v backintime | crontab -" )
		
		print "Clearing system backintime entries"
		os.system( "crontab -l | grep -Pv '(?s)%s.*?backintime' | crontab -" % system_entry_message )
		
		profiles = self.get_profiles()
		
		for profile_id in profiles:
			profile_name = self.get_profile_name( profile_id )
			print "Profile: %s" % profile_name
			min_backup_mode = self.NONE
			max_backup_mode = self.NONE

			#if self.get_per_directory_schedule( profile_id ):
			#	for item in self.get_include_folders( profile_id ):
			#		backup_mode = item[1]

			#		if self.NONE != backup_mode:
			#			if self.NONE == min_backup_mode:
			#				min_backup_mode = backup_mode
			#				max_backup_mode = backup_mode
			#			elif backup_mode < min_backup_mode:
			#				min_backup_mode = backup_mode
			#			elif backup_mode > max_backup_mode:
			#				max_backup_mode = backup_mode
		
			#	print "Min automatic backup: %s" % self.AUTOMATIC_BACKUP_MODES[ min_backup_mode ]
			#	print "Max automatic backup: %s" % self.AUTOMATIC_BACKUP_MODES[ max_backup_mode ]
			#else:
			min_backup_mode = self.get_automatic_backup_mode( profile_id )
			max_backup_mode = min_backup_mode
			print "Automatic backup: %s" % self.AUTOMATIC_BACKUP_MODES[ min_backup_mode ]

			if self.NONE == min_backup_mode:
				continue

			if not tools.check_command( 'crontab' ):
				self.notify_error( _( 'Can\'t find crontab.\nAre you sure cron is installed ?\nIf not you should disable all automatic backups.' ) )
				return False

			cron_line = ''
			
			if self._5_MIN == min_backup_mode:
				cron_line = 'echo "{msg}\n*/5 * * * * {cmd}"'
			elif self._10_MIN == min_backup_mode:
				cron_line = 'echo "{msg}\n*/10 * * * * {cmd}"'
			if self.HOUR == min_backup_mode:
				cron_line = 'echo "{msg}\n0 * * * * {cmd}"'
			elif self.DAY == min_backup_mode:
				cron_line = 'echo "{msg}\n15 15 * * * {cmd}"'
			elif self.WEEK == min_backup_mode and self.MONTH == max_backup_mode: #for every-week and every-month use every-day
				cron_line = 'echo "{msg}\n15 15 * * * {cmd}"'
			elif self.WEEK == min_backup_mode:
				cron_line = 'echo "{msg}\n15 15 * * 0 {cmd}"'
			elif self.MONTH == min_backup_mode:
				cron_line = 'echo "{msg}\n15 15 1 * * {cmd}"'

			if len( cron_line ) > 0:
				cmd = "/usr/bin/backintime --profile \\\"%s\\\" --backup-job >/dev/null 2>&1" % profile_name
				if self.is_run_ionice_from_cron_enabled():
					cmd = 'ionice -c2 -n7 ' + cmd
				if self.is_run_nice_from_cron_enabled( profile_id ):
					cmd = 'nice -n 19 ' + cmd
				cron_line = cron_line.replace( '{cmd}', cmd )
				cron_line = cron_line.replace( '{msg}', system_entry_message )
				os.system( "( crontab -l; %s ) | crontab -" % cron_line )

		return True
	
	#def get_update_other_folders( self ):
	#	return self.get_bool_value( 'update.other_folders', True )
		
	#def set_update_other_folders( self, value ):
	#	self.set_bool_value( 'update.other_folders', value )

if __name__ == "__main__":
	config = Config()
	print "snapshots path = %s" % config.get_snapshots_full_path()

