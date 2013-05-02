#	Back In Time
#	Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
#
#	This program is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; either version 2 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License along
#	with this program; if not, write to the Free Software Foundation, Inc.,
#	51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


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
import subprocess

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

        self.clear_uid_gid_cache()
        self.clear_uid_gid_names_cache()

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

    def get_snapshot_path( self, date, use_mode = [] ):
        profile_id = self.config.get_current_profile()
        current_mode = self.config.get_snapshots_mode()
        if 'ssh' in use_mode and current_mode == 'ssh':
            path = os.path.join( self.config.get_snapshots_full_path_ssh( profile_id ), self.get_snapshot_id( date ) )
            return path
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

    def get_snapshot_log_path( self, snapshot_id ):
        return os.path.join( self.get_snapshot_path( snapshot_id ), 'takesnapshot.log.bz2' )

    def get_snapshot_failed_path( self, snapshot_id ):
        return os.path.join( self.get_snapshot_path( snapshot_id ), 'failed' )

    def _get_snapshot_data_path( self, snapshot_id, **kwargs ):
        current_mode = self.config.get_snapshots_mode()
        if len( snapshot_id ) <= 1:
            return '/';
        return os.path.join( self.get_snapshot_path( snapshot_id, **kwargs ), 'backup' )
    
    def get_snapshot_path_to( self, snapshot_id, toPath = '/', **kwargs ):
        return os.path.join( self._get_snapshot_data_path( snapshot_id, **kwargs ), toPath[ 1 : ] )

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

        if self.is_snapshot_failed( snapshot_id ):
            display_name = display_name + " (%s)" % _("WITH ERRORS !")

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

        #info_file = configfile.ConfigFile()
        #info_file.load( self.get_snapshot_info_path( snapshot_id ) )
        #if info_file.get_int_value( 'snapshot_version' ) == 0:
        os.system( "chmod +w \"%s\"" % path )

        try:
            file = open( name_path, 'wt' )
            file.write( name )
            file.close()
        except:
            pass

    def is_snapshot_failed( self, snapshot_id ):
        if len( snapshot_id ) <= 1: #not a snapshot
            return False

        path = self.get_snapshot_failed_path( snapshot_id )
        return os.path.isfile( path )

    def clear_take_snapshot_message( self ):
        os.system( "rm \"%s\"" % self.config.get_take_snapshot_message_file() )

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

    def set_take_snapshot_message( self, type_id, message, timeout = -1 ):
        data = str(type_id) + '\n' + message

        try:
            file = open( self.config.get_take_snapshot_message_file(), 'wt' )
            file.write( data )
            file.close()
            #logger.info( "Take snapshot message: %s" % data )
        except:
            pass

        if 1 == type_id:
            self.append_to_take_snapshot_log( '[E] ' + message, 1 )
        else:
            self.append_to_take_snapshot_log( '[I] '  + message, 3 )

        try:
            profile_id =self.config.get_current_profile() 
            profile_name = self.config.get_profile_name( profile_id )
            self.plugin_manager.on_message( profile_id, profile_name, type_id, message, timeout )
        except:
            pass

    def _filter_take_snapshot_log( self, log, mode ):
        if 0 == mode:
            return log

        lines = log.split( '\n' )
        log = ''

        for line in lines:
            if line.startswith( '[' ):
                if mode == 1 and line[1] != 'E':
                    continue
                elif mode == 2 and line[1] != 'C':
                    continue
                elif mode == 3 and line[1] != 'I':
                    continue

            log = log + line + '\n'

        return log

    def get_snapshot_log( self, snapshot_id, mode = 0, profile_id = None ):
        try:
            file = bz2.BZ2File( self.get_snapshot_log_path( snapshot_id ), 'r' )
            data = file.read()
            file.close()
            return self._filter_take_snapshot_log( data, mode )
        except:
            return ''

    def get_take_snapshot_log( self, mode = 0, profile_id = None ):
        try:
            file = open( self.config.get_take_snapshot_log_file( profile_id ), 'rt' )
            data = file.read()
            file.close()
            return self._filter_take_snapshot_log( data, mode )
        except:
            return ''

    def new_take_snapshot_log( self, date ):
        os.system( "rm \"%s\"" % self.config.get_take_snapshot_log_file() )
        self.append_to_take_snapshot_log( "========== Take snapshot (profile %s): %s ==========\n" % ( self.config.get_current_profile(), date.strftime( '%c' ) ), 1 )

    def append_to_take_snapshot_log( self, message, level ):
        if level > self.config.log_level():
            return

        try:
            file = open( self.config.get_take_snapshot_log_file(), 'at' )
            file.write( message + '\n' )
            file.close()
        except:
            pass

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
            return dict

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

    def clear_uid_gid_names_cache(self):
        self.user_cache = {}
        self.group_cache = {}

    def clear_uid_gid_cache(self):
        self.uid_cache = {}
        self.gid_cache = {}

    def get_uid( self, name ):
        try:
            return self.uid_cache[name]
        except:
            uid = -1
            try:
                uid = pwd.getpwnam(name).pw_uid
            except:
                pass

            self.uid_cache[name] = uid
            return uid
            
    def get_gid( self, name ):
        try:
            return self.gid_cache[name]
        except:
            gid = -1
            try:
                gid = grp.getgrnam(name).gr_gid
            except:
                pass

            self.gid_cache[name] = gid
            return gid

    def get_user_name( self, uid ):
        try:
            return self.user_cache[uid]
        except:
            name = '-'
            try:
                name = pwd.getpwuid(uid).pw_name
            except:
                pass

            self.user_cache[uid] = name
            return name
            
    def get_group_name( self, gid ):
        try:
            return self.group_cache[gid]
        except:
            name = '-'
            try:
                name = grp.getgrgid(gid).gr_name
            except:
                pass

            self.group_cache[gid] = name
            return name

    def restore_callback( self, callback, ok, msg ):
        if not callback is None:
            if not ok:
                msg = msg + " : " + _("FAILED")
            callback( msg )
    
    def _restore_path_info( self, key_path, path, dict, callback = None ):
        #print "restore infos - key: %s ; path: %s" % ( key_path, path )

        if key_path not in dict:
            return
        info = dict[key_path]

        #restore uid/gid
        uid = self.get_uid(info[1])
        gid = self.get_gid(info[2])
        
        if uid != -1 or gid != -1:
            ok = False
            try:
                os.chown( path, uid, gid )
                ok = True
            except:
                pass
            self.restore_callback( callback, ok, "chown %s %s : %s" % ( path, uid, gid ) )
            
            #if restore uid/gid failed try to restore at least gid
            if not ok:
                try:
                    os.chown( path, -1, gid )
                    ok = True
                except:
                    pass
                self.restore_callback( callback, ok, "chgrp %s %s" % ( path, gid ) )
                
        #restore perms
        ok = False
        try:
            os.chmod( path, info[0] )
            ok = True
        except:
            pass
        self.restore_callback( callback, ok, "chmod %s %04o" % ( path, info[0] ) )

    def restore( self, snapshot_id, path, callback = None, restore_to = '' ):
        if restore_to.endswith('/'):
            restore_to = restore_to[ : -1 ]

        #full rsync
        full_rsync = self.config.full_rsync()

        logger.info( "Restore: %s to: %s" % (path, restore_to) )

        info_file = configfile.ConfigFile()
        info_file.load( self.get_snapshot_info_path( snapshot_id ) )

        backup_suffix = '.backup.' + datetime.date.today().strftime( '%Y%m%d' )
        #cmd = "rsync -avR --copy-unsafe-links --whole-file --backup --suffix=%s --chmod=+w %s/.%s %s" % ( backup_suffix, self.get_snapshot_path_to( snapshot_id ), path, '/' )
        cmd = tools.get_rsync_prefix( self.config, not full_rsync )
        cmd = cmd + '-R -v '
        if not full_rsync:
            cmd = cmd + '--chmod=ugo=rwX '
        if self.config.is_backup_on_restore_enabled():
            cmd = cmd + "--backup --suffix=%s " % backup_suffix
        #cmd = cmd + '--chmod=+w '
        src_base = self.get_snapshot_path_to( snapshot_id, use_mode = ['ssh'] )

        src_path = path
        src_delta = 0
        if len(restore_to) > 0:
            aux = src_path
            if aux.startswith('/'):
                aux = aux[1:]
            items = os.path.split(src_path)
            aux = items[0]
            if aux.startswith('/'):
                aux = aux[1:]
            if len(aux) > 0: #bugfix: restore system root ended in <src_base>//.<src_path>
                src_base = os.path.join(src_base, aux) + '/'
            src_path = '/' + items[1]
            if items[0] == '/':
                src_delta = 0
            else:
                src_delta = len(items[0])
    
        #print "src_base: %s" % src_base
        #print "src_path: %s" % src_path
        #print "src_delta: %s" % src_delta
        #print "snapshot_id: %s" % snapshot_id 
    
        cmd += self.rsync_remote_path('%s.%s' %(src_base, src_path))
        cmd += ' "%s/"' % restore_to
        self.restore_callback( callback, True, cmd )
        self._execute( cmd, callback )

        if full_rsync and not self.config.get_snapshots_mode() == 'ssh':
            return

        #restore permissions
        logger.info( 'Restore permissions' )
        self.restore_callback( callback, True, '' )
        self.restore_callback( callback, True, _("Restore permissions:") )
        file_info_dict = self.load_fileinfo_dict( snapshot_id, info_file.get_int_value( 'snapshot_version' ) )
        if len( file_info_dict ) > 0:
            #explore items
            snapshot_path_to = self.get_snapshot_path_to( snapshot_id, path ).rstrip( '/' )
            root_snapshot_path_to = self.get_snapshot_path_to( snapshot_id ).rstrip( '/' )
            all_dirs = [] #restore dir permissions after all files are done

            if len(restore_to) == 0:
                path_items = path.strip( '/' ).split( '/' )
                curr_path = '/'
                for path_item in path_items:
                    curr_path = os.path.join( curr_path, path_item )
                    all_dirs.append( curr_path )
            else:
                    all_dirs.append(path)

            #print "snapshot_path_to: %s" % snapshot_path_to
            if os.path.isdir( snapshot_path_to ) and not os.path.islink( snapshot_path_to ):
                for explore_path, dirs, files in os.walk( snapshot_path_to ):
                    for item in dirs:
                        item_path = os.path.join( explore_path, item )[ len( root_snapshot_path_to ) : ]
                        all_dirs.append( item_path )

                    for item in files:
                        item_path = os.path.join( explore_path, item )[ len( root_snapshot_path_to ) : ]
                        real_path = restore_to + item_path[src_delta:]
                        self._restore_path_info( item_path, real_path, file_info_dict, callback )
            #else:
            #	item_path = snapshot_path_to[ len( root_snapshot_path_to ) : ]
            #	real_path = restore_to + item_path[src_delta:]
            #	self._restore_path_info( item_path, real_path, file_info_dict, callback )

            all_dirs.reverse()
            for item_path in all_dirs:
                real_path = restore_to + item_path[src_delta:]
                self._restore_path_info( item_path, real_path, file_info_dict, callback )

    def get_snapshots_list( self, sort_reverse = True, profile_id = None, version = None ):
        '''Returns a list with the snapshot_ids of all snapshots in the snapshots folder'''
        biglist = []

        if profile_id is None:
            profile_id = self.config.get_current_profile()

        snapshots_path = self.config.get_snapshots_full_path( profile_id, version )
        
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
        path = self.get_snapshot_path( snapshot_id, use_mode = ['ssh'] )
        #cmd = "chmod -R u+rwx \"%s\"" %  path
        cmd = self.cmd_ssh( 'find \"%s\" -type d -exec chmod u+wx \"{}\" %s' % (path, self.config.find_suffix()), quote = True ) #Debian patch
        self._execute( cmd )
        cmd = self.cmd_ssh( "rm -rf \"%s\"" % path )
        self._execute( cmd )

    def copy_snapshot( self, snapshot_id, new_folder ):
        '''Copies a known snapshot to a new location'''
        current.path = self.get_snapshot_path( snapshot_id )
        #need to implement hardlinking to existing folder -> cp newest snapshot folder, rsync -aEAXHv --delete to this folder
        self._execute( "find \"%s\" -type d -exec chmod u+wx {} %s" % (snapshot_current_path, self.config.find_suffix()) )
        cmd = "cp -dRl \"%s\"* \"%s\"" % ( current_path, new_folder )
        logger.info( '%s is copied to folder %s' %( snapshot_id, new_folder ) )
        self._execute( cmd )
        self._execute( "find \"%s\" \"%s\" -type d -exec chmod u-w {} %s" % ( snapshot_current_path, new_folder, self.config.find_suffix() ) )

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

    def update_snapshots_location( self ):
        '''Updates to location: backintime/machine/user/profile_id'''
        if self.has_old_snapshots():
            logger.info( 'Snapshot location update flag detected' )
            logger.warning( 'Snapshot location needs update' ) 
            profiles = self.config.get_profiles()

            answer_change = self.config.question_handler( _('Back In Time changed its backup format.\n\nYour old snapshots can be moved according to this new format. OK?') )
            #print answer_change
            if answer_change == True:
                logger.info( 'Update snapshot locations' )
                #print len( profiles )
                
                if len( profiles ) == 1:
                    logger.info( 'Only 1 profile found' )
                    answer_same = True
                elif len( profiles ) > 1:
                    answer_same = self.config.question_handler( _('%s profiles found. \n\nThe new backup format supports storage of different users and profiles on the same location. Do you want the same location for both profiles? \n\n(The program will still be able to discriminate between them)') % len( profiles ) )
                else:
                    logger.warning( 'No profiles are found!' )
                    self.config.notify_error( _( 'No profiles are found. Will have to update to profiles first, please restart Back In Time' ) )
                    logger.info( 'Config version is %s' % str( self.get_int_value( 'config.version', 1 ) ) )
                    
                    if self.config.get_int_value( 'config.version', 1 ) > 1:
                        self.config.set_int_value( 'config.version', 2 )
                        logger.info( 'Config version set to 2' )
                        return False
                    
                # Moving old snapshots per profile_id
                #print answer_same
                profile_id = profiles[0]
                #print profile_id
                #old_folder = self.get_snapshots_path( profile_id )
                #print old_folder
                main_folder = self.config.get_snapshots_path( profile_id )
                old_snapshots_paths=[]
                counter = 0
                success = []
                
                for profile_id in profiles:
                    #print counter
                    old_snapshots_paths.append( self.config.get_snapshots_path( profile_id ) )
                    #print old_snapshots_paths
                    old_folder = os.path.join( self.config.get_snapshots_path( profile_id ), 'backintime' )
                    #print old_folder
                    if profile_id != "1" and answer_same == True:
                        #print 'profile_id != 1, answer = True'
                        self.config.set_snapshots_path( main_folder, profile_id )
                        logger.info( 'Folder of profile %s is set to %s' %( profile_id, main_folder ) )
                    else:
                        self.config.set_snapshots_path( self.config.get_snapshots_path( profile_id ), profile_id )
                        logger.info( 'Folder of profile %s is set to %s' %( profile_id, main_folder ) )
                    new_folder = self.config.get_snapshots_full_path( profile_id )
                    #print new_folder
                    #snapshots_to_move = tools.get_snapshots_list_in_folder( old_folder )
                    #print snapshots_to_move

                    output = tools.move_snapshots_folder( old_folder, new_folder )

                    snapshots_left = tools.get_snapshots_list_in_folder( old_folder )
                    if output == True:
                        success.append( True )
                        if len( snapshots_left ) == 0:
                            logger.info( 'Update was successful. Snapshots of profile %s are moved to their new location' % profile_id )
                        else:
                            logger.warning( 'Not all snapshots are removed from the original folder!' )
                            logger.info( 'The following snapshots are still present: %s' % snapshots_left )
                            logger.info( 'You could move them manually or leave them where they are now' )
                    else:
                        logger.warning( '%s: are not moved to their new location!' %snapshots_left )
                        
                        answer_unsuccessful = self.config.question_handler( _('%(snapshots_left)s\nof profile %(profile_id)s are not moved to their new location\nDo you want to proceed?\n(Back In Time will be able to continue taking snapshots, however the remaining snapshots will not be considered for automatic removal)\n\nIf not Back In Time will restore former settings for this profile, however cannot continue taking snapshots' %{ 'snapshots_left' : snapshots_left, 'profile_id' : profile_id } ) )
                        if answer_unsuccessful == True:
                            success.append( True )
                        else:
                            success.append( False )
                            # restore
                            logger.info( 'Restore former settings' )
                            self.config.set_snapshots_path( old_snapshots_paths[counter], profile_id )
                            #print self.get_snapshots_path( profile_id )
                            self.config.error_handler( _('Former settings of profile %s are restored.\nBack In Time cannot continue taking new snapshots.\n\nYou can manually move the snapshots, \nif you are done restart Back In Time to proceed' %profile_id ) )
                    
                    counter = counter + 1
                
                #print success
                overall_success = True
                for item in success:
                    if item == False:
                        overall_success = False	
                if overall_success == True:
                    #self.set_update_other_folders( False )
                    #print self.get_update_other_folders()
                    logger.info( 'Back In Time will be able to make new snapshots again!' )
                    self.config.error_handler( _('Update was successful!\n\nBack In Time will continue taking snapshots again as scheduled' ) )

            elif answer_change == False:
                logger.info( 'Move refused by user' )
                logger.warning( 'Old snapshots are not taken into account by smart-remove' )
                answer_continue = self.config.question_handler( _('Are you sure you do not want to move your old snapshots?\n\n\nIf you do, you will not see these questions again next time, Back In Time will continue making snapshots again, but smart-remove cannot take your old snapshots into account any longer!\n\nIf you do not, you will be asked again next time you start Back In Time.') )
                if answer_continue == True:
                    #self.set_update_other_folders( False )
                    for profile_id in profiles:
                        old_folder = self.config.get_snapshots_path( profile_id )
                        self.config.set_snapshots_path( old_folder, profile_id )
                        logger.info( 'Folder of profile %s is set to %s' %( profile_id, self.get_snapshots_path( profile_id ) ) )
                    
                    logger.info( 'Back In Time will be able to make new snapshots again!' )
                    self.config.error_handler( _('Back In Time will continue taking snapshots again as scheduled' ) )
                else: 
                    self.config.error_handler( _( 'Back In Time still cannot continue taking new snapshots.\nRestart Back In Time to see the questions again' ) )
            else:
                return False
        
    def has_old_snapshots( self ):
        return len( self.get_snapshots_list( False, None, 3 ) ) > 0

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
        #elif self.config.get_update_other_folders() == True:
        elif self.has_old_snapshots():
            logger.info( 'The application needs to change the backup format. Start the GUI to proceed. (As long as you do not you will not be able to make new snapshots!)' )
            logger.warning( 'Backup not performed' )
        else:
            instance = applicationinstance.ApplicationInstance( self.config.get_take_snapshot_instance_file(), False )
            if not instance.check():
                logger.warning( 'A backup is already running' )
                self.plugin_manager.on_error( 2 ) #a backup is already running
            else:
                ret_error = False

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
                include_folders = self.config.get_include()

                if len( include_folders ) <= 0:
                    logger.info( 'Nothing to do' )
                else:
                    self.plugin_manager.on_process_begins() #take snapshot process begin
                    logger.info( "on process begins" )
                    self.set_take_snapshot_message( 0, '...' )
                    self.new_take_snapshot_log( now )
                    profile_id = self.config.get_current_profile()
                    logger.info( "Profile_id: %s" % profile_id )
                    
                    if not self.config.can_backup( profile_id ):
                        if self.plugin_manager.has_gui_plugins() and self.config.is_notify_enabled():
                            self.set_take_snapshot_message( 1, 
                                    _('Can\'t find snapshots folder.\nIf it is on a removable drive please plug it.' ) +
                                    '\n' +
                                    gettext.ngettext( 'Waiting %s second.', 'Waiting %s seconds.', 30 ) % 30,
                                    30 )
                            for counter in xrange( 30, 0, -1 ):
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
                            ret_val, ret_error = self._take_snapshot( snapshot_id, now, include_folders )

                        if not ret_val:
                            self._execute( "rm -rf \"%s\"" % snapshot_path )

                            if ret_error:
                                logger.error( 'Failed to take snapshot !!!' )
                                self.set_take_snapshot_message( 1, _('Failed to take snapshot %s !!!') % now.strftime( '%x %H:%M:%S' ) )
                                os.system( 'sleep 2' )
                            else:
                                logger.warning( "No new snapshot" )
                        else:
                            ret_error = False
                    
                        if not ret_error:
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

                if not ret_error:
                    self.clear_take_snapshot_message()

                instance.exit_application()
                logger.info( 'Unlock' )

        if sleep:
            os.system( 'sleep 2' ) #max 1 backup / second

        return ret_val

    def _exec_rsync_callback( self, line, params ):
        self.set_take_snapshot_message( 0, _('Take snapshot') + " (rsync: %s)" % line )

        if line.endswith( ')' ):
            if line.startswith( 'rsync:' ):
                if not line.startswith( 'rsync: chgrp ' ) and not line.startswith( 'rsync: chown ' ):
                    params[0] = True
                    self.set_take_snapshot_message( 1, 'Error: ' + line )

        if len(line) >= 13:
            if line.startswith( 'BACKINTIME: ' ):
                if line[12] != '.' and line[12:14] != 'cd':
                    params[1] = True
                    self.append_to_take_snapshot_log( '[C] ' + line[ 12 : ], 2 )

    def _exec_rsync_compare_callback( self, line, params ):
        #self.set_take_snapshot_message( 0, _('Compare with snapshot %s') % params[0] )

        if len(line) >= 13:
            if line.startswith( 'BACKINTIME: ' ):
                if line[12] != '.':
                    params[1] = True
                    self.append_to_take_snapshot_log( '[C] ' + line[ 12 : ], 2 )

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

    #	all_include_folders = self.config.get_include()
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
            user = self.get_user_name(info.st_uid)
            group = self.get_group_name(info.st_gid)
            self._save_path_info_line( fileinfo, path, [ info.st_mode, user, group ] )
        except:
            pass

    def _take_snapshot( self, snapshot_id, now, include_folders ): # ignore_folders, dict, force ):
        self.set_take_snapshot_message( 0, _('...') )

        new_snapshot_id = 'new_snapshot'

        def snapshot_path(**kwargs):
            return self.get_snapshot_path( snapshot_id, **kwargs )

        def new_snapshot_path(**kwargs):
            return self.get_snapshot_path( new_snapshot_id, **kwargs )

        def new_snapshot_path_to(**kwargs):
            return self.get_snapshot_path_to( new_snapshot_id, **kwargs )

        def prev_snapshot_path_to(**kwargs):
            return self.get_snapshot_path_to( prev_snapshot_id, **kwargs )

        #find
        find_suffix = self.config.find_suffix()
        
        if os.path.exists( new_snapshot_path() ):
            #self._execute( "find \"%s\" -type d -exec chmod +w {} \;" % new_snapshot_path )
            #self._execute( "chmod -R u+rwx \"%s\"" %  new_snapshot_path )
            self._execute( "find \"%s\" -type d -exec chmod u+wx {} %s" % (new_snapshot_path(), find_suffix) ) #Debian patch
            self._execute( "rm -rf \"%s\"" % new_snapshot_path() )
        
            if os.path.exists( new_snapshot_path() ):
                logger.error( "Can't remove folder: %s" % new_snapshot_path() )
                self.set_take_snapshot_message( 1, _('Can\'t remove folder: %s') % new_snapshot_path() )
                os.system( 'sleep 2' ) #max 1 backup / second
                return [ False, True ]
        
        #create exclude patterns string
        items = []
        for exclude in self.config.get_exclude():
            self._append_item_to_list( "--exclude=\"%s\"" % exclude, items )
        #for folder in ignore_folders:
        #	self._append_item_to_list( "--exclude=\"%s\"" % folder, items )
        rsync_exclude = ' '.join( items )

        #create include patterns list
        items = []
        items2 = []
        for include_folder in include_folders:
            folder = include_folder[0]

            if folder == "/":	# If / is selected as included folder it should be changed to ""
                #folder = ""	# because an extra / is added below. Patch thanks to Martin Hoefling
                self._append_item_to_list( "--include=\"/\"" , items2 )
                self._append_item_to_list( "--include=\"/**\"" , items2 )
                continue

            if include_folder[1] == 0:
                self._append_item_to_list( "--include=\"%s/**\"" % folder, items2 )
            else:
                self._append_item_to_list( "--include=\"%s\"" % folder, items2 )
                folder = os.path.split( folder )[0]

            while True:
                self._append_item_to_list( "--include=\"%s/\"" % folder, items )
                folder = os.path.split( folder )[0]
                if len( folder) <= 1:
                    break

        rsync_include = ' '.join( items )
        rsync_include2 = ' '.join( items2 )

        #check previous backup
        #should only contain the personal snapshots
        check_for_changes = self.config.check_for_changes()

        #full rsync
        full_rsync = self.config.full_rsync()
        
        #rsync prefix & suffix
        rsync_prefix = tools.get_rsync_prefix( self.config, not full_rsync ) # 'rsync -aEAXH '
        rsync_exclude_backup_directory = " --exclude=\"%s\" --exclude=\"%s\" --exclude=\"%s\" " % \
                ( self.config.get_snapshots_path(), self.config._LOCAL_DATA_FOLDER,  \
                  self.config.MOUNT_ROOT )
        #rsync_suffix = ' --chmod=Fa-w,Da-w --delete ' + rsync_exclude_backup_directory  + rsync_include + ' ' + rsync_exclude + ' ' + rsync_include2 + ' --exclude=\"*\" / '
        rsync_suffix = ' --chmod=Du+wx ' + rsync_exclude_backup_directory  + rsync_include + ' ' + rsync_exclude + ' ' + rsync_include2 + ' --exclude=\"*\" / '

        #update dict
        #if not force:
        #	for folder in include_folders:
        #		dict[ folder ] = now
        #
        #	self._set_last_snapshot_info( dict )

        prev_snapshot_id = ''
        snapshots = self.get_snapshots_list()
        if len( snapshots ) == 0:
            snapshots = self.get_snapshots_and_other_list()

        # When there is no snapshots it takes the last snapshot from the other folders
        # It should delete the excluded folders then
        rsync_prefix = rsync_prefix + ' --delete --delete-excluded '
        
        if len( snapshots ) > 0:
            prev_snapshot_id = snapshots[0]

            if not full_rsync:
                changed = True
                if check_for_changes:
                    prev_snapshot_name = self.get_snapshot_display_id( prev_snapshot_id )
                    self.set_take_snapshot_message( 0, _('Compare with snapshot %s') % prev_snapshot_name )
                    logger.info( "Compare with old snapshot: %s" % prev_snapshot_id )
                    
                    cmd  = rsync_prefix + ' -i --dry-run --out-format="BACKINTIME: %i %n%L"' + rsync_suffix 
                    cmd += self.rsync_remote_path( prev_snapshot_path_to(use_mode = ['ssh']) )
                    params = [ prev_snapshot_path_to(), False ]
                    #try_cmd = self._execute_output( cmd, self._exec_rsync_compare_callback, prev_snapshot_name )
                    self.append_to_take_snapshot_log( '[I] ' + cmd, 3 )
                    self._execute( cmd, self._exec_rsync_compare_callback, params )
                    changed = params[1]

                    #changed = False

                    #for line in try_cmd.split( '\n' ):
                    #	if len( line ) < 1:
                    #		continue

                    #	if line[0] != '.':
                    #		changed = True
                    #		break

                    if not changed:
                        logger.info( "Nothing changed, no back needed" )
                        return [ False, False ]

            if not self._create_directory( new_snapshot_path_to() ):
                return [ False, True ]
            
            if not full_rsync:
                self.set_take_snapshot_message( 0, _('Create hard-links') )
                logger.info( "Create hard-links" )
                
                # When schedule per included folders is enabled this did not work (cp -alb iso cp -al?)
                # This resulted in a complete rsync for the whole snapshot consuming time and space
                # The ignored folders were copied afterwards. To solve this, the whole last snapshot is now hardlinked
                # and rsync is called only for the folders that should be synced (without --delete-excluded).  
                #if force or len( ignore_folders ) == 0:

                #make source snapshot folders rw to allow cp -al
                self._execute( self.cmd_ssh('find \"%s\" -type d -exec chmod u+wx \"{}\" %s' % (prev_snapshot_path_to(use_mode = ['ssh']), find_suffix), quote = True) ) #Debian patch

                #clone snapshot
                cmd = self.cmd_ssh( "cp -aRl \"%s\"* \"%s\"" % ( prev_snapshot_path_to(use_mode = ['ssh']), new_snapshot_path_to(use_mode = ['ssh']) ) )
                self.append_to_take_snapshot_log( '[I] ' + cmd, 3 )
                cmd_ret_val = self._execute( cmd )
                self.append_to_take_snapshot_log( "[I] returns: %s" % cmd_ret_val, 3 )

                #make source snapshot folders read-only
                self._execute( self.cmd_ssh( 'find \"%s\" -type d -exec chmod a-w \"{}\" %s' % (prev_snapshot_path_to(use_mode = ['ssh']), find_suffix), quote = True) ) #Debian patch

                #make snapshot items rw to allow xopy xattr
                self._execute( self.cmd_ssh( "chmod -R a+w \"%s\"" % new_snapshot_path(use_mode = ['ssh']) ) )

                #else:
                #	for folder in include_folders:
                #		prev_path = self.get_snapshot_path_to( prev_snapshot_id, folder )
                #		new_path = self.get_snapshot_path_to( new_snapshot_id, folder )
                #		tools.make_dirs( new_path )
                #		cmd = "cp -alb \"%s\"* \"%s\"" % ( prev_path, new_path )
                #		self._execute( cmd )
        else:
            if not self._create_directory( new_snapshot_path_to() ):
                return [ False, True ]

        #sync changed folders
        logger.info( "Call rsync to take the snapshot" )
        cmd = rsync_prefix + ' -v ' + rsync_suffix 
        cmd += self.rsync_remote_path( new_snapshot_path_to(use_mode = ['ssh']) )

        self.set_take_snapshot_message( 0, _('Take snapshot') )

        if full_rsync:
            if len( prev_snapshot_id ) > 0:
                #prev_snapshot_folder = self.get_snapshot_path_to( prev_snapshot_id )
                #prev_snapshot_folder_ssh = self.get_snapshot_path_to_ssh( prev_snapshot_id )
                #if ssh:
                #	cmd = cmd + " --link-dest=\"%s\"" % prev_snapshot_folder_ssh
                #else:
                #	cmd = cmd + " --link-dest=\"%s\"" % prev_snapshot_folder
                cmd = cmd + " --link-dest=\"../../%s/backup\"" % prev_snapshot_id

            cmd = cmd + ' -i --out-format="BACKINTIME: %i %n%L"'
            print "A: %s" % cmd

        params = [False, False]
        self.append_to_take_snapshot_log( '[I] ' + cmd, 3 )
        self._execute( cmd + ' 2>&1', self._exec_rsync_callback, params )

        has_errors = False
        if params[0]:
            if not self.config.continue_on_errors():
                self._execute( self.cmd_ssh( 'find \"%s\" -type d -exec chmod u+wx \"{}\" %s' % (new_snapshot_path(use_mode = ['ssh']), find_suffix), quote = True) ) #Debian patch
                self._execute( self.cmd_ssh( "rm -rf \"%s\"" % new_snapshot_path(use_mode = ['ssh']) ) )

                if not full_rsync:
                    #fix previous snapshot: make read-only again
                    if len( prev_snapshot_id ) > 0:
                        self._execute( self.cmd_ssh("chmod -R a-w \"%s\"" % prev_snapshot_path_to(use_mode = ['ssh']) ) )

                return [ False, True ]

            has_errors = True
            self._execute( "touch \"%s\"" % self.get_snapshot_failed_path( new_snapshot_id ) )

        if full_rsync:
            if not params[1]:
                self._execute( self.cmd_ssh( 'find \"%s\" -type d -exec chmod u+wx \"{}\" %s' % (new_snapshot_path(use_mode = ['ssh']), find_suffix), quote = True) ) #Debian patch
                self._execute( self.cmd_ssh( "rm -rf \"%s\"" % new_snapshot_path(use_mode = ['ssh']) ) )

                logger.info( "Nothing changed, no back needed" )
                return [ False, False ]
                

        #backup config file
        logger.info( 'Save config file' )
        self.set_take_snapshot_message( 0, _('Save config file ...') )
        self._execute( 'cp %s %s' % (self.config._LOCAL_CONFIG_PATH, new_snapshot_path_to() + '..') )
        
        if not full_rsync or self.config.get_snapshots_mode() == 'ssh':
            #save permissions for sync folders
            logger.info( 'Save permissions' )
            self.set_take_snapshot_message( 0, _('Save permission ...') )

            fileinfo = bz2.BZ2File( self.get_snapshot_fileinfo_path( new_snapshot_id ), 'w' )
            path_to_explore = self.get_snapshot_path_to( new_snapshot_id ).rstrip( '/' )
            fileinfo_dict = {}

            permission_done = False
            if self.config.get_snapshots_mode() == 'ssh':
                path_to_explore_ssh = new_snapshot_path_to(use_mode = ['ssh']).rstrip( '/' )
                cmd = self.cmd_ssh(['find', path_to_explore_ssh, '-name', '\*', '-print'], module = 'subprocess')
                
                find = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                output = find.communicate()[0]
                if find.returncode:
                    logger.warning('Save permission over ssh failed. Retry normal methode')
                else:
                    for line in output.split('\n'):
                        if not len(line) == 0:
                            item_path = line[ len( path_to_explore_ssh ) : ]
                            fileinfo_dict[item_path] = 1
                            self._save_path_info( fileinfo, item_path )
                    permission_done = True
                    
            if not permission_done:
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
        user = self.config.get_user()
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
        
        #copy take snapshot log
        try:
            logfile = open( self.config.get_take_snapshot_log_file(), 'r' )
            logdata = logfile.read()
            logfile.close()

            logfile = bz2.BZ2File( self.get_snapshot_log_path( new_snapshot_id ), 'w' )
            logfile.write( logdata )
            logfile.close()
        except:
            pass

        #rename snapshot
        os.system( self.cmd_ssh( "mv \"%s\" \"%s\"" % ( new_snapshot_path(use_mode = ['ssh']), snapshot_path(use_mode = ['ssh']) ) ) )

        if not os.path.exists( snapshot_path() ):
            logger.error( "Can't rename %s to %s" % ( new_snapshot_path(), snapshot_path() ) )
            self.set_take_snapshot_message( 1, _('Can\'t rename %(new_path)s to %(path)s') % { 'new_path' : new_snapshot_path(), 'path' : snapshot_path() } )
            os.system( 'sleep 2' ) #max 1 backup / second
            return [ False, True ]

        if not full_rsync:
            #make new snapshot read-only
            self._execute( self.cmd_ssh( "chmod -R a-w \"%s\"" % snapshot_path(use_mode = ['ssh']) ) )

        return [ True, has_errors ]

    def _smart_remove_keep_all_( self, snapshots, keep_snapshots, min_date, max_date ):
        min_id = self.get_snapshot_id( min_date )
        max_id = self.get_snapshot_id( max_date )

        logger.info( "[smart remove] keep all >= %s and < %s" % ( min_id, max_id ) )

        for snapshot_id in snapshots:
            if snapshot_id >= min_id and snapshot_id < max_id:
                if snapshot_id not in keep_snapshots:
                    keep_snapshots.append( snapshot_id )

        return keep_snapshots

    def _smart_remove_keep_first_( self, snapshots, keep_snapshots, min_date, max_date ):
        min_id = self.get_snapshot_id( min_date )
        max_id = self.get_snapshot_id( max_date )

        logger.info( "[smart remove] keep first >= %s and < %s" % ( min_id, max_id ) )

        for snapshot_id in snapshots:
            if snapshot_id >= min_id and snapshot_id < max_id:
                if snapshot_id not in keep_snapshots:
                    keep_snapshots.append( snapshot_id )
                break

        return keep_snapshots

    def inc_month( self, date ):
        y = date.year
        m = date.month + 1
        if m > 12:
            m = 1
            y = y + 1
        return datetime.date( y, m, 1 )

    def dec_month( self, date ):
        y = date.year
        m = date.month - 1
        if m < 1:
            m = 12
            y = y - 1
        return datetime.date( y, m, 1 )

    def smart_remove( self, now_full, keep_all, keep_one_per_day, keep_one_per_week, keep_one_per_month ):
        snapshots = self.get_snapshots_list()
        logger.info( "[smart remove] considered: %s" % snapshots )
        if len( snapshots ) <= 1:
            logger.info( "[smart remove] There is only one snapshots, so keep it" )
            return

        if now_full is None:
            now_full = datetime.datetime.today()

        now = now_full.date() 

        #keep the last snapshot
        keep_snapshots = [ snapshots[0] ]

        #keep all for the last keep_all days
        if keep_all > 0:
            keep_snapshots = self._smart_remove_keep_all_( snapshots, keep_snapshots, now - datetime.timedelta( days=keep_all-1), now + datetime.timedelta(days=1) )

        #keep one per days for the last keep_one_per_day days
        if keep_one_per_day > 0:
            d = now
            for i in xrange( 0, keep_one_per_day ):
                keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, d, d + datetime.timedelta(days=1) )
                d = d - datetime.timedelta(days=1)

        #keep one per week for the last keep_one_per_week weeks
        if keep_one_per_week > 0:
            d = now - datetime.timedelta( days = now.weekday() + 1 )
            for i in xrange( 0, keep_one_per_week ):
                keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, d, d + datetime.timedelta(days=8) )
                d = d - datetime.timedelta(days=7)

        #keep one per month for the last keep_one_per_month months
        if keep_one_per_month > 0:
            d1 = datetime.date( now.year, now.month, 1 )
            d2 = self.inc_month( d1 )
            for i in xrange( 0, keep_one_per_month ):
                keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, d1, d2 )
                d2 = d1
                d1 = self.dec_month(d1)

        #keep one per year for all years
        first_year = int(snapshots[-1][ : 4])
        for i in xrange( first_year, now.year+1 ):
            keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, datetime.date(i,1,1), datetime.date(i+1,1,1) )

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
        smart_remove, keep_all, keep_one_per_day, keep_one_per_week, keep_one_per_month = self.config.get_smart_remove()
        if smart_remove:
            self.set_take_snapshot_message( 0, _('Smart remove') )
            self.smart_remove( now, keep_all, keep_one_per_day, keep_one_per_week, keep_one_per_month )

        #try to keep min free space
        if self.config.is_min_free_space_enabled():
            self.set_take_snapshot_message( 0, _('Try to keep min free space') )

            min_free_space = self.config.get_min_free_space_in_mb()

            logger.info( "Keep min free disk space: %s Mb" % min_free_space )

            snapshots = self.get_snapshots_list( False )

            while True:
                if len( snapshots ) <= 1:
                    break

                if self.config.get_snapshots_mode() == 'ssh':
                    snapshots_path_ssh = self.config.get_snapshots_path_ssh()
                    if len(snapshots_path_ssh) == 0:
                        snapshots_path_ssh = './'
                    cmd = self.cmd_ssh(['df', snapshots_path_ssh], module = 'subprocess')
                    
                    df = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                    output = df.communicate()[0]
                    try:
                        lines = output.split('\n')
                        cols = lines[1].split()
                        free_space = int(cols[3]) / 1024
                    except IndexError:
                        logger.warning("could not get free disk space")
                        break
                    
                else:
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
                line = tools.temp_failure_retry( pipe.readline )
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

    #def _execute_output( self, cmd, callback = None, user_data = None ):
    #	output = ''

    #	pipe = os.popen( cmd, 'r' )
    #	
    #	while True:
    #		line = tools.temp_failure_retry( pipe.readline )
    #		if len( line ) == 0:
    #			break
    #		output = output + line
    #		if not callback is None:
    #			callback( line.strip(), user_data )

    #	ret_val = pipe.close()
    #	if ret_val is None:
    #		ret_val = 0

    #	if ret_val != 0:
    #		logger.warning( "Command \"%s\" returns %s" % ( cmd, ret_val ) )
    #	else:
    #		logger.info( "Command \"%s\" returns %s" % ( cmd, ret_val ) )

    #	return output
    
    def filter_for(self, base_snapshot_id, base_path, snapshots_list, list_diff_only  = False, flag_deep_check = False):
        "return a list of available snapshots (including 'now'), eventually filtered for uniqueness"
        snapshots_filtered = []

        base_full_path = self.get_snapshot_path_to( base_snapshot_id, base_path )
        if not os.path.lexists( base_full_path ):
            return []

        all_snapshots_list = [ '/' ]
        all_snapshots_list.extend( snapshots_list )

        #links
        if os.path.islink( base_full_path ):
            targets = []

            for snapshot_id in all_snapshots_list:
                path = self.get_snapshot_path_to( snapshot_id, base_path )

                if os.path.lexists( path ) and os.path.islink( path ):
                    if list_diff_only:
                        target = os.readlink( path )
                        if target in targets:
                            continue
                        targets.append( target )
                    snapshots_filtered.append(snapshot_id)

            return snapshots_filtered

        #directories
        if os.path.isdir( base_full_path ):
            for snapshot_id in all_snapshots_list:
                path = self.get_snapshot_path_to( snapshot_id, base_path )

                if os.path.exists( path ) and not os.path.islink( path ) and os.path.isdir( path ):
                    snapshots_filtered.append(snapshot_id)

            return snapshots_filtered

        #files
        if not list_diff_only:
            for snapshot_id in all_snapshots_list:
                path = self.get_snapshot_path_to( snapshot_id, base_path )

                if os.path.exists( path ) and not os.path.islink( path ) and os.path.isfile( path ):
                    snapshots_filtered.append(snapshot_id)

            return snapshots_filtered

        # check for duplicates
        uniqueness = tools.UniquenessSet(flag_deep_check, follow_symlink = False)
        for snapshot_id in all_snapshots_list:
            path = self.get_snapshot_path_to( snapshot_id, base_path )
            if os.path.exists( path ) and not os.path.islink( path ) and os.path.isfile( path ) and uniqueness.check_for(path):  
                snapshots_filtered.append(snapshot_id)

        return snapshots_filtered

    def cmd_ssh(self, cmd, quote = False, module = 'os.system'):
        if self.config.get_snapshots_mode() == 'ssh':
            (ssh_host, ssh_port, ssh_user, ssh_path, ssh_cipher) = self.config.get_ssh_host_port_user_path_cipher()
            if module == 'os.system':
                if ssh_cipher == 'default':
                    ssh_cipher_suffix = ''
                else:
                    ssh_cipher_suffix = '-c %s' % ssh_cipher
                
                if quote:
                    cmd = '\'%s\'' % cmd
                    
                return 'ssh -p %s %s %s@%s %s' % ( str(ssh_port), ssh_cipher_suffix, ssh_user, ssh_host, cmd )

            elif module == 'subprocess':
                suffix = ['ssh', '-p', str(ssh_port)]
                if not ssh_cipher == 'default':
                    suffix += ['-c', ssh_cipher]
                suffix += ['%s@%s' % (ssh_user, ssh_host)]
                if quote:
                    suffix += ['\'']
                    cmd += ['\'']
                return suffix + cmd
                
        else:
            return cmd

    def rsync_remote_path(self, path):
        if self.config.get_snapshots_mode() == 'ssh':
            user = self.config.get_ssh_user()
            host = self.config.get_ssh_host()
            return '\'%s@%s:"%s"\'' % (user, host, path)
        else:
            return '"%s"' % path

if __name__ == "__main__":
    config = config.Config()
    snapshots = Snapshots( config )
    snapshots.take_snapshot()

