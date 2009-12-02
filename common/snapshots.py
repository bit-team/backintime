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


import os
import os.path
import stat
import datetime
import gettext
import statvfs
import stat
import bz2
import pwd
import grp
import socket

import config
import configfile
import logger
import applicationinstance
import tools
import pluginmanager


_=gettext.gettext


class Snapshots:
	SNAPSHOT_VERSION = 3

	def __init__( self, cfg = None ):
		self.config = cfg
		if self.config is None:
			self.config = config.Config()

		self.plugin_manager = pluginmanager.PluginManager()

	def get_snapshot_id( self, date ):
		profile_id = self.config.get_current_profile()
		tag = self.config.get_tag( profile_id )
		
		if type( date ) is datetime.datetime:
			snapshot_id = date.strftime( '%Y%m%d-%H%M%S' ) + '-' + tag
			return snapshot_id

		if type( date ) is datetime.date:
			snapshot_id = date.strftime( '%Y%m%d-000000' ) + '-' + tag
			return snapshot_id

		if type( date ) is str:
			snapshot_id = date
			return snapshot_id
		
		return ""

	def get_snapshot_old_id( self, date ):
		profile_id = self.config.get_current_profile()
		
		if type( date ) is datetime.datetime:
			snapshot_id = date.strftime( '%Y%m%d-%H%M%S' )
			return snapshot_id

		if type( date ) is datetime.date:
			snapshot_id = date.strftime( '%Y%m%d-000000' )
			return snapshot_id

		if type( date ) is str:
			snapshot_id = date
			return snapshot_id
		
		return ""

	def get_snapshot_path( self, date ):
		profile_id = self.config.get_current_profile()
		path = os.path.join( self.config.get_snapshots_full_path( profile_id ), self.get_snapshot_id( date ) )
		if os.path.exists( path ):
			#print path
			return path
		other_folders = self.config.get_other_folders_paths()
		for folder in other_folders:
			path_other = os.path.join( folder, self.get_snapshot_id( date ) )
			if os.path.exists( path_other ):
				#print path_other
				return path_other
		old_path = os.path.join( self.config.get_snapshots_full_path( profile_id ), self.get_snapshot_old_id( date ) )
		if os.path.exists( path ):
			#print path
			return path
		other_folders = self.config.get_other_folders_paths()
		for folder in other_folders:
			path_other = os.path.join( folder, self.get_snapshot_old_id( date ) )
			if os.path.exists( path_other ):
				#print path_other
				return path_other				
		#print path
		return path

	def get_snapshot_info_path( self, date ):
		return os.path.join( self.get_snapshot_path( date ), 'info' )

	def get_snapshot_fileinfo_path( self, date ):
		return os.path.join( self.get_snapshot_path( date ), 'fileinfo.bz2' )

	def _get_snapshot_data_path( self, snapshot_id ):
		if len( snapshot_id ) <= 1:
			return '/';
		return os.path.join( self.get_snapshot_path( snapshot_id ), 'backup' )
	
	def get_snapshot_path_to( self, snapshot_id, toPath = '/' ):
		return os.path.join( self._get_snapshot_data_path( snapshot_id ), toPath[ 1 : ] )

	def can_open_path( self, snapshot_id, full_path ):
		#full_path = self.get_snapshot_path_to( snapshot_id, path )
		if not os.path.exists( full_path ):
			return False
		if not os.path.islink( full_path ):
			return True
		base_path = self.get_snapshot_path_to( snapshot_id )
		target = os.readlink( full_path )
		target = os.path.join( os.path.abspath( os.path.dirname( full_path ) ), target )
		#print "[can_open_path] full_path %s" % full_path
		#print "[can_open_path] base_path %s" % base_path
		return target.startswith( base_path )

	def get_snapshot_display_id( self, snapshot_id ):
		if len( snapshot_id ) <= 1:
			return _('Now')
		return "%s-%s-%s %s:%s:%s" % ( snapshot_id[ 0 : 4 ], snapshot_id[ 4 : 6 ], snapshot_id[ 6 : 8 ], snapshot_id[ 9 : 11 ], snapshot_id[ 11 : 13 ], snapshot_id[ 13 : 15 ]  )
	
	def get_snapshot_display_name( self, snapshot_id ):
		display_name = self.get_snapshot_display_id( snapshot_id )
		name = self.get_snapshot_name( snapshot_id )
		if len( name ) > 0:
			display_name = display_name + ' - ' + name
		return display_name

	def get_snapshot_name( self, snapshot_id ):
		if len( snapshot_id ) <= 1: #not a snapshot
			return ''

		path = self.get_snapshot_path( snapshot_id )
		if not os.path.isdir( path ):
			return ''
		
		name = ''
		try:
			file = open( os.path.join( path, 'name' ), 'rt' )
			name = file.read()
			file.close()
		except:
			pass

		return name

	def set_snapshot_name( self, snapshot_id, name ):
		if len( snapshot_id ) <= 1: #not a snapshot
			return

		path = self.get_snapshot_path( snapshot_id )
		if not os.path.isdir( path ):
			return

		name_path = os.path.join( path, 'name' )

		info_file = configfile.ConfigFile()
		info_file.load( self.get_snapshot_info_path( snapshot_id ) )
		if info_file.get_int_value( 'snapshot_version' ) == 0:
			os.system( "chmod a+w \"%s\"" % path )

		try:
			file = open( name_path, 'wt' )
			file.write( name )
			file.close()
		except:
			pass

	def get_take_snapshot_message( self ):
		try:
			file = open( self.config.get_take_snapshot_message_file(), 'rt' )
			items = file.read().split( '\n' )
			file.close()
		except:
			return None 

		if len( items ) < 2:
			return None

		id = 0
		try:
			id = int( items[0] )
		except:
			pass

		del items[0]
		message = '\n'.join( items )

		return( id, message )

	def set_take_snapshot_message( self, type_id, message ):
		data = str(type_id) + '\n' + message

		try:
			file = open( self.config.get_take_snapshot_message_file(), 'wt' )
			items = file.write( data )
			file.close()
			#logger.info( "Take snapshot message: %s" % data )
		except:
			pass

	def clear_take_snapshot_message( self ):
		os.system( "rm \"%s\"" % self.config.get_take_snapshot_message_file() )

	def is_busy( self ):
		instance = applicationinstance.ApplicationInstance( self.config.get_take_snapshot_instance_file(), False )
		return not instance.check()

	def load_fileinfo_dict( self, snapshot_id, version = None ):
		if version is None:
			info_file = configfile.ConfigFile()
			info_file.load( self.get_snapshot_info_path( snapshot_id ) )
			version = info_file.get_int_value( 'snapshot_version' )
			info_file = None

		dict = {}

		if 0 == version:
			return file_info_dict

		fileinfo_path = self.get_snapshot_fileinfo_path( snapshot_id )
		if not os.path.exists( fileinfo_path ):
			return dict

		#try:
		fileinfo = bz2.BZ2File( fileinfo_path, 'r' )
		while True:
			line = fileinfo.readline()
			if len( line ) <= 0:
				break

			line = line[ : -1 ]
			if len( line ) <= 0:
				continue
		
			index = line.find( '/' )
			if index < 0:
				continue

			file = line[ index: ]
			if len( file ) <= 0:
				continue

			info = line[ : index ].strip()
			info = info.split( ' ' )

			if len( info ) == 3:
				dict[ file ] = [ int( info[0] ), info[1], info[2] ] #perms, user, group

		fileinfo.close()
		#except:
		#	pass

		return dict

	def _restore_path_info( self, path, dict ):
		if path not in dict:
			return

		info = dict[path]

		#restore perms
		try:
			os.chmod( path, info[0] )
		except:
			pass

		#restore uid/gid
		uid = -1
		gid = -1

		if info[1] != '-':
			try:
				uid = pwd.getpwnam( info[1] ).pw_uid
			except:
				pass

		if info[2] != '-':
			try:
				gid = grp.getgrnam( info[2] ).gr_gid
			except:
				pass

		if uid != -1 or gid != -1:
			try:
				os.chown( path, uid, gid )
			except:
				pass

	def restore( self, snapshot_id, path ):
		logger.info( "Restore: %s" % path )

		info_file = configfile.ConfigFile()
		info_file.load( self.get_snapshot_info_path( snapshot_id ) )

		backup_suffix = '.backup.' + datetime.date.today().strftime( '%Y%m%d' )
		#cmd = "rsync -avR --copy-unsafe-links --whole-file --backup --suffix=%s --chmod=+w %s/.%s %s" % ( backup_suffix, self.get_snapshot_path_to( snapshot_id ), path, '/' )
		cmd = tools.get_rsync_prefix()
		cmd = cmd + "-R --whole-file --backup --suffix=%s " % backup_suffix
		#cmd = cmd + '--chmod=+w '
		cmd = cmd + "\"%s.%s\" %s" % ( self.get_snapshot_path_to( snapshot_id ), path, '/' )
		self._execute( cmd )

		#restore permissions
		logger.info( "Restore permissions" )
		file_info_dict = self.load_fileinfo_dict( snapshot_id, info_file.get_int_value( 'snapshot_version' ) )
		if len( file_info_dict ) > 0:
			#explore items
			snapshot_path_to = self.get_snapshot_path_to( snapshot_id, path ).rstrip( '/' )
			root_snapshot_path_to = self.get_snapshot_path_to( snapshot_id ).rstrip( '/' )
			all_dirs = [] #restore dir permissions after all files are done

			path_items = path.strip( '/' ).split( '/' )
			curr_path = '/'
			for path_item in path_items:
				curr_path = os.path.join( curr_path, path_item )
				all_dirs.append( curr_path )

			if not os.path.isfile( snapshot_path_to ):
				for explore_path, dirs, files in os.walk( snapshot_path_to ):
					for item in dirs:
						item_path = os.path.join( explore_path, item )[ len( root_snapshot_path_to ) : ]
						all_dirs.append( item_path )

					for item in files:
						item_path = os.path.join( explore_path, item )[ len( root_snapshot_path_to ) : ]
						self._restore_path_info( item_path, file_info_dict )

			all_dirs.reverse()
			for item_path in all_dirs:
				self._restore_path_info( item_path, file_info_dict )

	def get_snapshots_list( self, sort_reverse = True ):
		'''Returns a list with the snapshot_ids of all snapshots in the snapshots folder'''
		biglist = []
		profile_id = self.config.get_current_profile()
		snapshots_path = self.config.get_snapshots_full_path( profile_id )
		
		try:
			biglist = os.listdir( snapshots_path )
		except:
			pass

		list = []

		for item in biglist:
			if len( item ) != 15 and len( item ) != 19:
				continue
			if os.path.isdir( os.path.join( snapshots_path, item, 'backup' ) ):
				list.append( item )

		list.sort( reverse = sort_reverse )
		return list
		
	def get_snapshots_and_other_list( self, sort_reverse = True ):
		'''Returns a list with the snapshot_ids, and paths, of all snapshots in the snapshots_folder and the other_folders'''

		biglist = []
		profile_id = self.config.get_current_profile()
		snapshots_path = self.config.get_snapshots_full_path( profile_id )
		snapshots_other_paths = self.config.get_other_folders_paths()
		
		try:
			biglist = os.listdir( snapshots_path )
		except:
			pass
			
		list = []

		for item in biglist:
			if len( item ) != 15 and len( item ) != 19:
				continue
			if os.path.isdir( os.path.join( snapshots_path, item, 'backup' ) ):
				#a = ( item, snapshots_path )
				list.append( item )

				
		if len( snapshots_other_paths ) > 0:	
			for folder in snapshots_other_paths:
				folderlist = []
				try:
					folderlist = os.listdir( folder )
				except:
					pass
				
				for member in folderlist:
					if len( member ) != 15 and len( member ) != 19:
						continue
					if os.path.isdir( os.path.join( folder, member,  'backup' ) ):
						#a = ( member, folder )
						list.append( member )
		
		list.sort( reverse = sort_reverse )
		return list

	def remove_snapshot( self, snapshot_id ):
		if len( snapshot_id ) <= 1:
			return

		path = self.get_snapshot_path( snapshot_id )
		#cmd = "chmod -R a+rwx \"%s\"" %  path
		cmd = "find \"%s\" -type d -exec chmod u+wx {} \\;" % path #Debian patch
		self._execute( cmd )
		cmd = "rm -rfv \"%s\"" % path
		self._execute( cmd )

	def copy_snapshot( self, snapshot_id, new_folder ):
		'''Copies a known snapshot to a new location'''
		current.path = self.get_snapshot_path( snapshot_id )
		#need to implement hardlinking to existing folder -> cp newest snapshot folder, rsync -aEAXHv --delete to this folder
		cmd = "cp -al \"%s\"* \"%s\"" % ( current_path, new_folder )
		logger.info( '%s is copied to folder %s' %( snapshot_id, new_folder ) )
		self._execute( cmd )

	#def _get_last_snapshot_info( self ):
	#	lines = ''
	#	dict = {}

	#	try:
	#		if os.path.exists( self.config.get_last_snapshot_info_file() ):
	#			file = open( self.config.get_last_snapshot_info_file(), 'rt' )
	#			lines = file.read()
	#			file.close()
	#	except:
	#		pass

	#	lines = lines.split( '\n' )
	#	for line in lines:
	#		line = line.strip()
	#		if len( line ) <= 0:
	#			continue
	#		fields = line.split( ':' )
	#		if len( fields ) < 6:
	#			continue

	#		dict[ fields[0] ] = datetime.datetime( int(fields[1]), int(fields[2]), int(fields[3]), int(fields[4]), int(fields[5]) )

	#	return dict

	#def _set_last_snapshot_info( self, dict ):
	#	lines = []

	#	for key, value in dict.items():
	#		lines.append( "%s:%s:%s:%s:%s:%s" % ( key, value.year, value.month, value.day, value.hour, value.minute ) )

	#	try:
	#		file = open( self.config.get_last_snapshot_info_file(), 'wt' )
	#		file.write( '\n'.join( lines ) )
	#		file.close()
	#	except:
	#		pass

	#def call_user_callback( self, args ):
	#	cmd = self.config.get_take_snapshot_user_callback()
	#	if os.path.isfile( cmd ):
	#		self._execute( 'sh ' + cmd + ' ' + args )

	def take_snapshot( self, force = False ):
		ret_val = False
		sleep = True

		self.plugin_manager.load_plugins( self )

		if not self.config.is_configured():
			logger.warning( 'Not configured' )
			self.plugin_manager.on_error( 1 ) #not configured
		elif self.config.is_no_on_battery_enabled() and tools.on_battery():
			logger.info( 'Deferring backup while on battery' )
			logger.warning( 'Backup not performed' )
		elif self.config.get_update_other_folders() == True:
			logger.info( 'The application needs to change the backup format. Start the GUI to proceed. (As long as you do not you will not be able to make new snapshots!)' )
			logger.warning( 'Backup not performed' )
		else:
			instance = applicationinstance.ApplicationInstance( self.config.get_take_snapshot_instance_file(), False )
			if not instance.check():
				logger.warning( 'A backup is already running' )
				self.plugin_manager.on_error( 2 ) #a backup is already running
			else:
				if self.config.is_no_on_battery_enabled () and not tools.power_status_available():
					logger.warning( 'Backups disabled on battery but power status is not available' )
								
				instance.start_application()
				logger.info( 'Lock' )

				#if not self.config.get_per_directory_schedule():
				#	force = True

				now = datetime.datetime.today()
				#if not force:
				#	now = now.replace( second = 0 )

				#include_folders, ignore_folders, dict = self._get_backup_folders( now, force )
				include_folders = self.config.get_include_folders()

				if len( include_folders ) <= 0:
					logger.info( 'Nothing to do' )
				else:
					self.plugin_manager.on_process_begins() #take snapshot process begin
					logger.info( "on process begins" )
					self.set_take_snapshot_message( 0, '...' )
					profile_id = self.config.get_current_profile()
					logger.info( "Profile_id: %s" % profile_id )
					
					if not self.config.can_backup( profile_id ):
						if self.plugin_manager.has_gui_plugins() and self.config.is_notify_enabled():
							for counter in xrange( 30, 0, -1 ):
								self.set_take_snapshot_message( 1, 
										_('Can\'t find snapshots folder.\nIf it is on a removable drive please plug it.' ) +
										'\n' +
										gettext.ngettext( 'Waiting %s second.', 'Waiting %s seconds.', counter ) % counter )
								os.system( 'sleep 1' )
								if self.config.can_backup():
									break

					if not self.config.can_backup( profile_id ):
						logger.warning( 'Can\'t find snapshots folder !' )
						self.plugin_manager.on_error( 3 ) #Can't find snapshots directory (is it on a removable drive ?)
					else:
						snapshot_id = self.get_snapshot_id( now )
						snapshot_path = self.get_snapshot_path( snapshot_id )
						
						if os.path.exists( snapshot_path ):
							logger.warning( "Snapshot path \"%s\" already exists" % snapshot_path )
							self.plugin_manager.on_error( 4, snapshot_id ) #This snapshots already exists
						else:
							#ret_val = self._take_snapshot( snapshot_id, now, include_folders, ignore_folders, dict, force )
							ret_val = self._take_snapshot( snapshot_id, now, include_folders )

						if not ret_val:
							os.system( "rm -rf \"%s\"" % snapshot_path )
							logger.warning( "No new snapshot (not needed or error)" )
						
						self._free_space( now )

						self.set_take_snapshot_message( 0, _('Finalizing') )

					os.system( 'sleep 2' )
					sleep = False

					if ret_val:
						self.plugin_manager.on_new_snapshot( snapshot_id, snapshot_path ) #new snapshot

					self.plugin_manager.on_process_ends() #take snapshot process end

				if sleep:
					os.system( 'sleep 2' )
					sleep = False

				self.clear_take_snapshot_message()
				instance.exit_application()
				logger.info( 'Unlock' )

		if sleep:
			os.system( 'sleep 2' ) #max 1 backup / second

		return ret_val

	def _exec_rsync_callback( self, line, user_data ):
		self.set_take_snapshot_message( 0, _('Take snapshot') + " (rsync: %s)" % line )

	def _exec_rsync_compare_callback( self, line, user_data ):
		self.set_take_snapshot_message( 0, _('Compare with snapshot %s') % user_data + " (rsync: %s)"% line )

	def _append_item_to_list( self, item, list ):
		for list_item in list:
			if item == list_item:
				return
		list.append( item )

	def _is_auto_backup_needed( self, now, last, mode ):
		#print "now: %s, last: %s, mode: %s" % ( now, last, mode )

		if self.config.NONE == mode:
			return False

		if now <= last:
			return False

		if now.year > last.year: #year changed
			return True

		if self.config.MONTH == mode: #month changed
			return now.month > last.month
		
		if self.config.WEEK == mode: #weekly
			if now.date() <= last.date():
				return False
			return now.isoweekday() == 7 #Sunday

		if now.date() > last.date(): #day changed
			return True

		if self.config.DAY == mode:
			return False

		if now.hour > last.hour: #hour changed
			return True
		
		if self.config.HOUR == mode:
			return False

		if self.config._10_MIN == mode: #every 10 minutes
			return ( int( now.minute / 10 ) ) > ( int( last.minute / 10 ) )

		if self.config._5_MIN == mode: #every 5 minutes
			return ( int( now.minute / 5 ) ) > ( int( last.minute / 5 ) )

		return False

	#def _get_backup_folders( self, now, force ):
	#	include_folders = []
	#	ignore_folders = []
	#	dict = self._get_last_snapshot_info()
	#	dict2 = {}

	#	all_include_folders = self.config.get_include_folders()
	#	
	#	for item in all_include_folders:
	#		path = item[0]
	#		path = os.path.expanduser( path )
	#		path = os.path.abspath( path )

	#		if path in dict:
	#			dict2[ path ] = dict[ path ]

	#		if not os.path.isdir( path ):
	#			continue

	#		if not force and path in dict:
	#			if not self._is_auto_backup_needed( now, dict[path], item[1] ):
	#				ignore_folders.append( path )
	#				continue

	#		include_folders.append( path )

	#	logger.info( "Include folders: %s" % include_folders )
	#	logger.info( "Ignore folders: %s" % ignore_folders )
	#	logger.info( "Last snapshots: %s" % dict2 )

	#	return ( include_folders, ignore_folders, dict2 )

	def _create_directory( self, folder ):
		tools.make_dirs( folder )

		if not os.path.exists( folder ):
			logger.error( "Can't create folder: %s" % folder )
			self.set_take_snapshot_message( 1, _('Can\'t create folder: %s') % folder )
			os.system( 'sleep 2' ) #max 1 backup / second
			return False

		return True
	
	def _save_path_info_line( self, fileinfo, path, info ):
		fileinfo.write( "%s %s %s %s\n" % ( info[0], info[1], info[2], path ) )

	def _save_path_info( self, fileinfo, path ):
		try:
			info = os.stat( path )
			user = '-'
			group = '-'

			try:
				user = pwd.getpwuid( info.st_uid ).pw_name
			except:
				pass

			try:
				group = grp.getgrgid( info.st_gid ).gr_name
			except:
				pass

			self._save_path_info_line( fileinfo, path, [ info.st_mode, user, group ] )
		except:
			pass

	def _take_snapshot( self, snapshot_id, now, include_folders ): # ignore_folders, dict, force ):
		self.set_take_snapshot_message( 0, _('...') )

		new_snapshot_id = 'new_snapshot'
		new_snapshot_path = self.get_snapshot_path( new_snapshot_id )
		
		if os.path.exists( new_snapshot_path ):
			#self._execute( "find \"%s\" -type d -exec chmod +w {} \;" % new_snapshot_path )
			#self._execute( "chmod -R a+rwx \"%s\"" %  new_snapshot_path )
			self._execute( "find \"%s\" -type d -exec chmod u+wx {} \\;" % new_snapshot_path ) #Debian patch
			self._execute( "rm -rf \"%s\"" % new_snapshot_path )
		
			if os.path.exists( new_snapshot_path ):
				logger.error( "Can't remove folder: %s" % new_snapshot_path )
				self.set_take_snapshot_message( 1, _('Can\'t remove folder: %s') % new_snapshot_path )
				os.system( 'sleep 2' ) #max 1 backup / second
				return False

		new_snapshot_path_to = self.get_snapshot_path_to( new_snapshot_id )
		
		#create exclude patterns string
		items = []
		for exclude in self.config.get_exclude_patterns():
			self._append_item_to_list( "--exclude=\"%s\"" % exclude, items )
		#for folder in ignore_folders:
		#	self._append_item_to_list( "--exclude=\"%s\"" % folder, items )
		rsync_exclude = ' '.join( items )

		#create include patterns list
		items = []
		items2 = []
		for include_folder in include_folders:
			if include_folder == "/":	# If / is selected as included folder it should be changed to ""
				include_folder = ""	# because an extra / is added below. Patch thanks to Martin Hoefling
			self._append_item_to_list( "--include=\"%s/**\"" % include_folder, items2 )
			while True:
				self._append_item_to_list( "--include=\"%s/\"" % include_folder, items )
				include_folder = os.path.split( include_folder )[0]
				if len( include_folder ) <= 1:
					break
		rsync_include = ' '.join( items )
		rsync_include2 = ' '.join( items2 )

		#rsync prefix & suffix
		rsync_prefix = tools.get_rsync_prefix() # 'rsync -aEAXH '
		rsync_exclude_backup_directory = " --exclude=\"%s\" --exclude=\"%s\" " % ( self.config.get_snapshots_path(), self.config._LOCAL_DATA_FOLDER )
		rsync_suffix = ' --chmod=Fa-w,Da-w --whole-file --delete ' + rsync_exclude_backup_directory  + rsync_include + ' ' + rsync_exclude + ' ' + rsync_include2 + ' --exclude=\"*\" / '

		#update dict
		#if not force:
		#	for folder in include_folders:
		#		dict[ folder ] = now
		#
		#	self._set_last_snapshot_info( dict )

		#check previous backup
		#should only contain the personal snapshots
		snapshots = self.get_snapshots_list()
		prev_snapshot_id = ''
		
		if len( snapshots ) == 0:
			snapshots = self.get_snapshots_and_other_list()

		# When there is no snapshots it takes the last snapshot from the other folders
		# It should delete the excluded folders then
		rsync_prefix = rsync_prefix + '--delete-excluded '
			
		if len( snapshots ) > 0:
			prev_snapshot_id = snapshots[0]
			prev_snapshot_name = self.get_snapshot_display_id( prev_snapshot_id )
			self.set_take_snapshot_message( 0, _('Compare with snapshot %s') % prev_snapshot_name )
			logger.info( "Compare with old snapshot: %s" % prev_snapshot_id )
			
			prev_snapshot_folder = self.get_snapshot_path_to( prev_snapshot_id )
			cmd = rsync_prefix + ' -i --dry-run ' + rsync_suffix + '"' + prev_snapshot_folder + '"'
			try_cmd = self._execute_output( cmd, self._exec_rsync_compare_callback, prev_snapshot_name )
			changed = False

			for line in try_cmd.split( '\n' ):
				if len( line ) < 1:
					continue

				if line[0] != '.':
					changed = True
					break

			if not changed:
				logger.info( "Nothing changed, no back needed" )
				return False

			if not self._create_directory( new_snapshot_path_to ):
				return False
			
			self.set_take_snapshot_message( 0, _('Create hard-links') )
			logger.info( "Create hard-links" )
			
			# When schedule per included folders is enabled this did not work (cp -alb iso cp -al?)
			# This resulted in a complete rsync for the whole snapshot consuming time and space
			# The ignored folders were copied afterwards. To solve this, the whole last snapshot is now hardlinked
			# and rsync is called only for the folders that should be synced (without --delete-excluded).  
			#if force or len( ignore_folders ) == 0:
			cmd = "cp -al \"%s\"* \"%s\"" % ( self.get_snapshot_path_to( prev_snapshot_id ), new_snapshot_path_to )
			self._execute( cmd )
			#else:
			#	for folder in include_folders:
			#		prev_path = self.get_snapshot_path_to( prev_snapshot_id, folder )
			#		new_path = self.get_snapshot_path_to( new_snapshot_id, folder )
			#		tools.make_dirs( new_path )
			#		cmd = "cp -alb \"%s\"* \"%s\"" % ( prev_path, new_path )
			#		self._execute( cmd )
		else:
			if not self._create_directory( new_snapshot_path_to ):
				return False

		#sync changed folders
		logger.info( "Call rsync to take the snapshot" )
		cmd = rsync_prefix + ' -v --delete-excluded ' + rsync_suffix + '"' + new_snapshot_path_to + '"'
		self.set_take_snapshot_message( 0, _('Take snapshot') )
		self._execute( cmd, self._exec_rsync_callback )

		#save permissions for sync folders
		logger.info( 'Save permissions' )
		self.set_take_snapshot_message( 0, _('Save permission ...') )

		fileinfo = bz2.BZ2File( self.get_snapshot_fileinfo_path( new_snapshot_id ), 'w' )
		path_to_explore = self.get_snapshot_path_to( new_snapshot_id ).rstrip( '/' )
		fileinfo_dict = {}

		for path, dirs, files in os.walk( path_to_explore ):
			dirs.extend( files )
			for item in dirs:
				item_path = os.path.join( path, item )[ len( path_to_explore ) : ]
				fileinfo_dict[item_path] = 1
				self._save_path_info( fileinfo, item_path )

		# We now copy on forehand, so copying afterwards is not necessary anymore
		##copy ignored folders
		#if not force and len( prev_snapshot_id ) > 0 and len( ignore_folders ) > 0:
		#	prev_fileinfo_dict = self.load_fileinfo_dict( prev_snapshot_id )
		#
		#	for folder in ignore_folders:
		#		prev_path = self.get_snapshot_path_to( prev_snapshot_id, folder )
		#		new_path = self.get_snapshot_path_to( new_snapshot_id, folder )
		#		tools.make_dirs( new_path )
		#		cmd = "cp -alb \"%s/\"* \"%s\"" % ( prev_path, new_path )
		#		self._execute( cmd )
		#
		#		if len( prev_fileinfo_dict ) > 0:
		#			#save permissions for all items to folder
		#			item_path = '/'
		#			prev_path_items = folder.strip( '/' ).split( '/' )
		#			for item in items:
		#				item_path = os.path.join( item_path, item )
		#				if item_path not in fileinfo_dict and item_path in prev_fileinfo_dict:
		#					self._save_path_info_line( fileinfo, item_path, prev_fileinfo_dict[item_path] )

		#			#save permission for all items in folder
		#			for path, dirs, files in os.walk( new_path ):
		#				dirs.extend( files )
		#				for item in dirs:
		#					item_path = os.path.join( path, item )[ len( path_to_explore ) : ]
		#					if item_path not in fileinfo_dict and item_path in prev_fileinfo_dict:
		#						self._save_path_info_line( fileinfo, item_path, prev_fileinfo_dict[item_path] )

		fileinfo.close()

		#create info file 
		logger.info( "Create info file" ) 
		machine = socket.gethostname()
		user = os.environ['LOGNAME']
		profile_id = self.config.get_current_profile()
		tag = self.config.get_tag( profile_id )
		info_file = configfile.ConfigFile()
		info_file.set_int_value( 'snapshot_version', self.SNAPSHOT_VERSION )
		info_file.set_str_value( 'snapshot_date', snapshot_id[0:15] )
		info_file.set_str_value( 'snapshot_machine', machine )
		info_file.set_str_value( 'snapshot_user', user )
		info_file.set_int_value( 'snapshot_profile_id', profile_id )
		info_file.set_int_value( 'snapshot_tag', tag )
		info_file.save( self.get_snapshot_info_path( new_snapshot_id ) )
		info_file = None

		#rename snapshot
		snapshot_path = self.get_snapshot_path( snapshot_id )
		os.system( "mv \"%s\" \"%s\"" % ( new_snapshot_path, snapshot_path ) )
		if not os.path.exists( snapshot_path ):
			logger.error( "Can't rename %s to %s" % ( new_snapshot_path, snapshot_path ) )
			self.set_take_snapshot_message( 1, _('Can\'t rename %s to %s') % ( new_snapshot_path, snapshot_path ) )
			os.system( 'sleep 2' ) #max 1 backup / second
			return False

		#make new snapshot read-only
		#self._execute( "chmod -R a-w \"%s\"" % snapshot_path )

		return True

	def _smart_remove_keep_all_( self, snapshots, keep_snapshots, min_date ):
		min_id = self.get_snapshot_id( min_date )

		logger.info( "[smart remove] keep all >= %s" % min_id )

		for snapshot_id in snapshots:
			if snapshot_id >= min_id:
				if snapshot_id not in keep_snapshots:
					keep_snapshots.append( snapshot_id )

		return keep_snapshots

	def _smart_remove_keep_first_( self, snapshots, keep_snapshots, min_date, max_date ):
		max_id = self.get_snapshot_id( max_date + datetime.timedelta( days = 1 ) )
		min_id = self.get_snapshot_id( min_date )

		logger.info( "[smart remove] keep first >= %s and < %s" % ( min_id, max_id ) )

		for snapshot_id in snapshots:
			if snapshot_id >= min_id and snapshot_id < max_id:
				if snapshot_id not in keep_snapshots:
					keep_snapshots.append( snapshot_id )
				break

		return keep_snapshots

	def smart_remove( self, now_full = None ):
		snapshots = self.get_snapshots_list()
		logger.info( "[smart remove] considered: %s" % snapshots )
		if len( snapshots ) <= 1:
			logger.info( "[smart remove] There is only one snapshots, so keep it" )
			return

		if now_full is None:
			now_full = datetime.datetime.today()

		now = datetime.datetime( now_full.year, now_full.month, now_full.day )

		#keep the last snapshot
		keep_snapshots = [ snapshots[0] ]

		#keep all from today and yesterday
		keep_snapshots = self._smart_remove_keep_all_( snapshots, keep_snapshots, now - datetime.timedelta( days = 1 ) )

		#last week	
		max_date = now - datetime.timedelta( days = now.weekday() + 1 )
		min_date = max_date - datetime.timedelta( days = 6 )
		keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, min_date, max_date )

		#2 weeks ago
		max_date = max_date - datetime.timedelta( days = 7 )
		min_date = min_date - datetime.timedelta( days = 7 )
		keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, min_date, max_date )

		#one per month for all months of this year
		if now.date > 1:
			for month in xrange( 1, now.month ):
				#print "month: %s" % month
				min_date = datetime.date( now.year, month, 1 )
				max_date = datetime.date( now.year, month + 1, 1 ) - datetime.timedelta( days = 1 )
				keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, min_date, max_date )

		#one per year for all previous years
		min_year = int( snapshots[ -1 ][ :4 ] )
		for year in xrange( min_year, now.year ):
			#print "year: %s" % year
			min_date = datetime.date( year, 1, 1 )
			max_date = datetime.date( year + 1, 1, 1 ) - datetime.timedelta( days = 1 )
			keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, min_date, max_date )

		logger.info( "[smart remove] keep snapshots: %s" % keep_snapshots )

		for snapshot_id in snapshots:
			if snapshot_id in keep_snapshots:
				continue

			if self.config.get_dont_remove_named_snapshots():
				if len( self.get_snapshot_name( snapshot_id ) ) > 0:
					logger.info( "[smart remove] keep snapshot: %s, it has a name" % snapshot_id )
					continue

			logger.info( "[smart remove] remove snapshot: %s" % snapshot_id )
			self.remove_snapshot( snapshot_id )

	def _free_space( self, now ):
		#remove old backups
		if self.config.is_remove_old_snapshots_enabled():
			self.set_take_snapshot_message( 0, _('Remove old snapshots') )
			snapshots = self.get_snapshots_list( False )

			old_backup_id = self.get_snapshot_id( self.config.get_remove_old_snapshots_date() )
			logger.info( "Remove backups older than: %s" % old_backup_id[0:15] )

			while True:
				if len( snapshots ) <= 1:
					break

				if snapshots[0] >= old_backup_id:
					break

				if self.config.get_dont_remove_named_snapshots():
					if len( self.get_snapshot_name( snapshots[0] ) ) > 0:
						del snapshots[0]
						continue

				self.remove_snapshot( snapshots[0] )
				del snapshots[0]

		#smart remove
		if self.config.get_smart_remove():
			self.set_take_snapshot_message( 0, _('Smart remove') )
			self.smart_remove( now )

		#try to keep min free space
		if self.config.is_min_free_space_enabled():
			self.set_take_snapshot_message( 0, _('Try to keep min free space') )

			min_free_space = self.config.get_min_free_space_in_mb()

			logger.info( "Keep min free disk space: %s Mb" % min_free_space )

			snapshots = self.get_snapshots_list( False )

			while True:
				if len( snapshots ) <= 1:
					break

				info = os.statvfs( self.config.get_snapshots_path() )
				free_space = info[ statvfs.F_FRSIZE ] * info[ statvfs.F_BAVAIL ] / ( 1024 * 1024 )

				if free_space >= min_free_space:
					break

				if self.config.get_dont_remove_named_snapshots():
					if len( self.get_snapshot_name( snapshots[0] ) ) > 0:
						del snapshots[0]
						continue

				logger.info( "free disk space: %s Mb" % free_space )
				self.remove_snapshot( snapshots[0] )
				del snapshots[0]

	def _execute( self, cmd, callback = None, user_data = None ):
		ret_val = 0

		if callback is None:
			ret_val = os.system( cmd )
		else:
			pipe = os.popen( cmd, 'r' )

			while True:
				line = pipe.readline()
				if len( line ) == 0:
					break
				callback( line.strip(), user_data )

			ret_val = pipe.close()
			if ret_val is None:
				ret_val = 0

		if ret_val != 0:
			logger.warning( "Command \"%s\" returns %s" % ( cmd, ret_val ) )
		else:
			logger.info( "Command \"%s\" returns %s" % ( cmd, ret_val ) )

		return ret_val

	def _execute_output( self, cmd, callback = None, user_data = None ):
		output = ''

		pipe = os.popen( cmd, 'r' )
		
		while True:
			line = pipe.readline()
			if len( line ) == 0:
				break
			output = output + line
			if not callback is None:
				callback( line.strip(), user_data )

		ret_val = pipe.close()
		if ret_val is None:
			ret_val = 0

		if ret_val != 0:
			logger.warning( "Command \"%s\" returns %s" % ( cmd, ret_val ) )
		else:
			logger.info( "Command \"%s\" returns %s" % ( cmd, ret_val ) )

		return output


if __name__ == "__main__":
	config = config.Config()
	snapshots = Snapshots( config )
	snapshots.take_snapshot()

