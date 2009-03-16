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
import stat
import datetime
import gettext
import statvfs

import config
import logger
import applicationinstance


_=gettext.gettext


class Snapshots:
	def __init__( self, cfg = None ):
		self.config = cfg
		if self.config is None:
			self.config = config.Config()

	def get_snapshot_id( self, date ):
		if type( date ) is datetime.datetime:
			return date.strftime( '%Y%m%d-%H%M%S' )

		if type( date ) is datetime.date:
			return date.strftime( '%Y%m%d-000000' )

		if type( date ) is str:
			return date
		
		return ""

	def get_snapshot_path( self, date ):
		return os.path.join( self.config.get_snapshots_full_path(), self.get_snapshot_id( date ) )

	def _get_snapshot_data_path( self, snapshot_id ):
		if len( snapshot_id ) <= 1:
			return '/';
		return os.path.join( self.get_snapshot_path( snapshot_id ), 'backup' )
	
	def get_snapshot_path_to( self, snapshot_id, toPath = '/' ):
		return os.path.join( self._get_snapshot_data_path( snapshot_id ), toPath[ 1 : ] )

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

		os.system( "chmod a+w \"%s\"" % path )

		try:
			file = open( name_path, 'wt' )
			file.write( name )
			file.close()
		except:
			pass

		os.system( "chmod a-w \"%s\"" % path )

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

	def restore( self, snapshot_id, path ):
		logger.info( "Restore: %s" % path )
		backup_suffix = '.backup.' + datetime.date.today().strftime( '%Y%m%d' )
		#cmd = "rsync -avR --copy-unsafe-links --whole-file --backup --suffix=%s --chmod=+w %s/.%s %s" % ( backup_suffix, self.get_snapshot_path_to( snapshot_id ), path, '/' )
		cmd = "rsync -avR --safe-links --whole-file --backup --suffix=%s --chmod=+w \"%s/.%s\" %s" % ( backup_suffix, self.get_snapshot_path_to( snapshot_id ), path, '/' )
		self._execute( cmd )

	def get_snapshots_list( self, sort_reverse = True ):
		biglist = []
		snapshots_path = self.config.get_snapshots_full_path()

		try:
			biglist = os.listdir( snapshots_path )
		except:
			pass

		list = []

		current_snapshot = '99999999-999999'
		try:
			instance_file = self.config.get_take_snapshot_instance_file()
			if os.path.exists( instance_file ):
				ctime = os.stat( instance_file )[stat.ST_CTIME]
				current_snapshot = self.get_snapshot_id( datetime.datetime.fromtimestamp( ctime ) )
		except:
			pass

		for item in biglist:
			if len( item ) != 15:
				continue
			if os.path.isdir( os.path.join( snapshots_path, item ) ):
				if item < current_snapshot:
					list.append( item )

		list.sort( reverse = sort_reverse )
		return list

	def remove_snapshot( self, snapshot_id ):
		if len( snapshot_id ) <= 1:
			return

		path = self.get_snapshot_path( snapshot_id )
		cmd = "chmod -R a+w \"%s\"" %  path
		self._execute( cmd )
		cmd = "rm -rf \"%s\"" % path
		self._execute( cmd )

	def _get_last_snapshot_info( self ):
		lines = ''
		dict = {}

		try:
			if os.path.exists( self.config.get_last_snapshot_info_file() ):
				file = open( self.config.get_last_snapshot_info_file(), 'rt' )
				lines = file.read()
				file.close()
		except:
			pass

		lines = lines.split( '\n' )
		for line in lines:
			line = line.strip()
			if len( line ) <= 0:
				continue
			fields = line.split( ':' )
			if len( fields ) < 6:
				continue

			dict[ fields[0] ] = datetime.datetime( int(fields[1]), int(fields[2]), int(fields[3]), int(fields[4]), int(fields[5]) )

		return dict

	def _set_last_snapshot_info( self, dict ):
		lines = []

		for key, value in dict.items():
			lines.append( "%s:%s:%s:%s:%s:%s" % ( key, value.year, value.month, value.day, value.hour, value.minute ) )

		try:
			print self.config.get_last_snapshot_info_file()
			file = open( self.config.get_last_snapshot_info_file(), 'wt' )
			file.write( '\n'.join( lines ) )
			file.close()
		except:
			pass

	def take_snapshot( self, callback = None, force = False ):
		if not self.config.is_configured():
			logger.warning( 'Not configured' )
			os.system( 'sleep 2' ) #max 1 backup / second
			return False

		instance = applicationinstance.ApplicationInstance( self.config.get_take_snapshot_instance_file(), False )
		if not instance.check():
			logger.warning( 'A backup is already running' )
			os.system( 'sleep 2' ) #max 1 backup / second
			return False

		instance.start_application()
		logger.info( 'Lock' )

		now = datetime.datetime.today()
		if not force:
			now = now.replace( second = 0 )

		include_folders, ignore_folders, dict = self._get_backup_folders( now, force )

		if len( include_folders ) <= 0:
			logger.info( 'Nothing to do' )
			os.system( 'sleep 2' ) #max 1 backup / second
			instance.exit_application()
			logger.info( 'Unlock' )
			return False

		if not callback is None:
			callback.snapshot_begin()

		self.set_take_snapshot_message( 0, '...' )

		if not self.config.can_backup():
			if not callback is None and self.config.is_notify_enabled():
				for counter in xrange( 30, 0, -1 ):
					self.set_take_snapshot_message( 1, 
							_('Can\'t find snapshots directory.\nIf it is on a removable drive please plug it.' ) +
							'\n' +
							gettext.ngettext( 'Waiting %s second.', 'Waiting %s seconds.', counter ) % counter )
					os.system( 'sleep 1' )
					if self.config.can_backup():
						break
			else:
				os.system( 'sleep 2' ) #max 1 backup / second

		ret_val = False
	
		if not self.config.can_backup():
			logger.warning( 'Can\'t find snapshots directory !' )
		else:
			snapshot_id = self.get_snapshot_id( now )
			snapshot_path = self.get_snapshot_path( snapshot_id )

			if os.path.exists( snapshot_path ):
				logger.warning( "Snapshot path \"%s\" already exists" % snapshot_path )
				retVal = True
			else:
				#try:
				ret_val = self._take_snapshot( snapshot_id, now, include_folders, ignore_folders, dict, force )
				#except:
				#	retVal = False

			if not ret_val:
				os.system( "rm -rf \"%s\"" % snapshot_path )
				logger.warning( "No new snapshot (not needed or error)" )
			
			#try:
			self._free_space( now )
			#except:
			#	pass

			self.set_take_snapshot_message( 0, _('Finalizing') )
			os.system( 'sleep 2' ) #max 1 backup / second

		if not callback is None:
			callback.snapshot_end()
		
		self.clear_take_snapshot_message()
		instance.exit_application()
		logger.info( 'Unlock' )
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

	def _get_backup_folders( self, now, force ):
		include_folders = []
		ignore_folders = []
		dict = self._get_last_snapshot_info()

		all_include_folders = self.config.get_include_folders()
		
		for item in self.config.get_include_folders():
			path = item[0]
			path = os.path.expanduser( path )
			path = os.path.abspath( path )

			if not os.path.isdir( path ):
				continue

			if not force and path in dict:
				if not self._is_auto_backup_needed( now, dict[path], item[1] ):
					ignore_folders.append( path )
					continue

			include_folders.append( path )

		return ( include_folders, ignore_folders, dict )

	def _take_snapshot( self, snapshot_id, now, include_folders, ignore_folders, dict, force ):
		#print "Snapshot: %s" % snapshot_id
		#print "\tInclude: %s" % include_folders
		#print "\tIgnore: %s" % ignore_folders
		#print "\tDict: %s" % dict

		self.set_take_snapshot_message( 0, _('...') )

		snapshot_path = self.get_snapshot_path( snapshot_id )
		snapshot_path_to = self.get_snapshot_path_to( snapshot_id )

		#create exclude patterns string
		items = []
		for exclude in self.config.get_exclude_patterns():
			self._append_item_to_list( "--exclude=\"%s\"" % exclude, items )
		for folder in ignore_folders:
			self._append_item_to_list( "--exclude=\"%s\"" % folder, items )
		rsync_exclude = ' '.join( items )

		#create include patterns list
		items = []
		items2 = []
		for include_folder in include_folders:
			self._append_item_to_list( "--include=\"%s/**\"" % include_folder, items2 )
			while True:
				self._append_item_to_list( "--include=\"%s/\"" % include_folder, items )
				include_folder = os.path.split( include_folder )[0]
				if len( include_folder ) <= 1:
					break
		rsync_include = ' '.join( items )
		rsync_include2 = ' '.join( items2 )

		#rsync prefix & suffix
		rsync_prefix = 'rsync -a'
		rsync_suffix = '--safe-links --whole-file --delete ' + rsync_include + ' ' + rsync_exclude + ' ' + rsync_include2 + ' --exclude=\"*\" / '

		#update dict
		if not force:
			for folder in include_folders:
				dict[ folder ] = now

			self._set_last_snapshot_info( dict )

		#check previous backup
		snapshots = self.get_snapshots_list()
		prev_snapshot_id = ''

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

			#create hard links
			self.set_take_snapshot_message( 0, _('Create hard-links') )
			logger.info( "Create hard-links" )
			self._execute( "mkdir -p \"%s\"" % snapshot_path_to )

			if force:
				cmd = "cp -al \"%s/\"* \"%s\"" % ( self.get_snapshot_path_to( prev_snapshot_id ), snapshot_path_to )
				self._execute( cmd )
			else:
				for folder in include_folders:
					prev_path = self.get_snapshot_path_to( prev_snapshot_id, folder )
					new_path = self.get_snapshot_path_to( snapshot_id, folder )
					self._execute( "mkdir -p \"%s\"" % new_path )
					cmd = "cp -alb \"%s/\"* \"%s\"" % ( prev_path, new_path )
					self._execute( cmd )

			cmd = "chmod -R a+w \"%s\"" % snapshot_path
			self._execute( cmd )
		else:
			self._execute( "mkdir -p \"%s\"" % snapshot_path_to )

		#create new backup folder
		if not os.path.exists( snapshot_path_to ):
			logger.error( "Can't create snapshot directory: %s" % snapshot_path_to )
			return False

		#sync changed folders
		logger.info( "Call rsync to take the snapshot" )
		cmd = rsync_prefix + ' -v --delete-excluded ' + rsync_suffix + '"' + snapshot_path_to + '"'
		self.set_take_snapshot_message( 0, _('Take snapshot') )
		self._execute( cmd, self._exec_rsync_callback )

		#copy ignored directories
		if not force and len( prev_snapshot_id ) > 0:
			for folder in ignore_folders:
				prev_path = self.get_snapshot_path_to( prev_snapshot_id, folder )
				new_path = self.get_snapshot_path_to( snapshot_id, folder )
				self._execute( "mkdir -p \"%s\"" % new_path )
				cmd = "cp -alb \"%s/\"* \"%s\"" % ( prev_path, new_path )
				self._execute( cmd )

		#make new folder read-only
		self._execute( "chmod -R a-w \"%s\"" % snapshot_path )
		return True

	def smart_remove( self, now = None ):
		if now is None:
			now = datetime.datetime.today()

		#build groups
		groups = []

		#
		yesterday = now - datetime.timedelta( days = 1 )
		yesterday_id = self.get_snapshot_id( yesterday )

		#last week
		date = now - datetime.timedelta( days = now.weekday() + 7 )
		groups.append( ( self.get_snapshot_id( date ), [] ) )

		#2 weeks ago
		date = now - datetime.timedelta( days = now.weekday() + 14 )
		groups.append( ( self.get_snapshot_id( date ), [] ) )

		#all months for this year
		for m in xrange( now.month-1, 0, -1 ):
			date = now.replace( month = m, day = 1 )
			groups.append( ( self.get_snapshot_id( date ), [] ) )

		#fill groups
		snapshots = self.get_snapshots_list()
		print snapshots

		for snapshot_id in snapshots:
			#keep all item since yesterday
			if snapshot_id >= yesterday_id:
				continue

			found = False
			for group in groups:
				if snapshot_id >= group[0]:
					group[1].append( snapshot_id )
					found = True
					break

			if not found: #new year group
				groups.append( ( snapshot_id[ : 4 ] + "0101-000000", [ snapshot_id ] ) )

		#remove items from each group
		for group in groups:
			print group

			if len( group[1] ) <= 1: #nothing to do
				continue

			if self.config.get_dont_remove_named_snapshots():
				#if the group contains a named snapshots keep only this snapshots
				has_names = False

				for snapshot_id in group[1]:
					if len( self.get_snapshot_name( snapshot_id ) ) > 0:
						has_names = True
						break

				if has_names:
					for snapshot_id in group[1]:
						if len( self.get_snapshot_name( snapshot_id ) ) <= 0:
							self.remove_snapshot( snapshot_id )
							print "[SMART] remove snapshot (not name): " + snapshot_id
					continue

			#keep only the first snapshot
			del group[1][0]
			for snapshot_id in group[1]:
				self.remove_snapshot( snapshot_id )
				print "[SMART] remove snapshot: " + snapshot_id

	def _free_space( self, now ):
		#remove old backups
		if self.config.is_remove_old_snapshots_enabled():
			self.set_take_snapshot_message( 0, _('Remove old snapshots') )
			snapshots = self.get_snapshots_list( False )

			old_backup_id = self.get_snapshot_id( self.config.get_remove_old_snapshots_date() )
			logger.info( "Remove backups older then: %s" % old_backup_id )

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

