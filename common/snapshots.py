#	Back In Time
#	Copyright (C) 2008-2014 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import stat
import datetime
import gettext
import stat
import bz2
import pwd
import grp
import subprocess
import shutil
import time
import re

import config
import configfile
import logger
import applicationinstance
import tools
import encfstools
import mount
import progress

_=gettext.gettext


class Snapshots:
    SNAPSHOT_VERSION = 3

    def __init__( self, cfg = None ):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()

        self.clear_uid_gid_cache()
        self.clear_uid_gid_names_cache()

        #rsync --info=progress2 output
        #search for 517.38K  26%   14.46MB/s    0:02:36
        self.reRsyncProgress = re.compile(r'(\d*[,\.]?\d+[KkMGT]?)\s*(\d*)%\s*(\d*[,\.]?\d*[KkMGT]?B/s)\s*(\d+:\d{2}:\d{2})')

        self.last_check_snapshot_runnig = datetime.datetime(1,1,1)

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
        if 'ssh_encfs' in use_mode and current_mode == 'ssh_encfs':
            path = os.path.join( self.config.get_snapshots_full_path_ssh( profile_id ), self.get_snapshot_id( date ) )
            return self.config.ENCODE.remote(path)
        path = os.path.join( self.config.get_snapshots_full_path( profile_id ), self.get_snapshot_id( date ) )
        if os.path.exists( path ):
            return path
        other_folders = self.config.get_other_folders_paths()
        for folder in other_folders:
            path_other = os.path.join( folder, self.get_snapshot_id( date ) )
            if os.path.exists( path_other ):
                return path_other
        old_path = os.path.join( self.config.get_snapshots_full_path( profile_id ), self.get_snapshot_old_id( date ) )
        if os.path.exists( path ):
            return path
        other_folders = self.config.get_other_folders_paths()
        for folder in other_folders:
            path_other = os.path.join( folder, self.get_snapshot_old_id( date ) )
            if os.path.exists( path_other ):
                return path_other
        return path

    def get_snapshot_info_path( self, date ):
        return os.path.join( self.get_snapshot_path( date ), 'info' )

    def get_snapshot_fileinfo_path( self, date ):
        return os.path.join( self.get_snapshot_path( date ), 'fileinfo.bz2' )

    def get_snapshot_log_path( self, snapshot_id ):
        return os.path.join( self.get_snapshot_path( snapshot_id ), 'takesnapshot.log.bz2' )

    def get_snapshot_failed_path( self, snapshot_id ):
        return os.path.join( self.get_snapshot_path( snapshot_id ), 'failed' )

    def _get_snapshot_data_path( self, snapshot_id, use_mode = [] ):
        current_mode = self.config.get_snapshots_mode()
        if len( snapshot_id ) <= 1:
            return '/';
        path = 'backup'
        snapshot_path = self.get_snapshot_path( snapshot_id, use_mode )
        if 'ssh_encfs' in use_mode and current_mode == 'ssh_encfs':
            return os.path.join( snapshot_path, self.config.ENCODE.path(path) )
        return os.path.join( snapshot_path, path )

    def get_snapshot_path_to( self, snapshot_id, toPath = '/', use_mode = [] ):
        current_mode = self.config.get_snapshots_mode()
        snapshot_data_path = os.path.join( self._get_snapshot_data_path( snapshot_id, use_mode ) )
        if 'ssh_encfs' in use_mode and current_mode == 'ssh_encfs':
            enc_path = self.config.ENCODE.path( toPath[ 1 : ] )
            return os.path.join( snapshot_data_path, enc_path )
        return os.path.join( snapshot_data_path, toPath[ 1 : ] )

    def can_open_path( self, snapshot_id, full_path ):
        if not os.path.exists( full_path ):
            return False
        if not os.path.islink( full_path ):
            return True
        base_path = self.get_snapshot_path_to( snapshot_id )
        target = os.readlink( full_path )
        target = os.path.join( os.path.abspath( os.path.dirname( full_path ) ), target )
        return target.startswith( base_path )

    def get_snapshot_display_id( self, snapshot_id ):
        if len( snapshot_id ) <= 1:
            return _('Now')
        return "%s-%s-%s %s:%s:%s" % ( snapshot_id[ 0 : 4 ], snapshot_id[ 4 : 6 ], snapshot_id[ 6 : 8 ], snapshot_id[ 9 : 11 ], snapshot_id[ 11 : 13 ], snapshot_id[ 13 : 15 ]  )

    def get_snapshot_display_name( self, snapshot_id ):
        display_name = self.get_snapshot_display_id( snapshot_id )
        name = self.get_snapshot_name( snapshot_id )

        if name:
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
            with open( os.path.join( path, 'name' ), 'rt' ) as file:
                name = file.read()
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

        os.system( "chmod +w \"%s\"" % path )

        try:
            with open( name_path, 'wt' ) as file:
                file.write( name )
        except:
            pass

    def is_snapshot_failed( self, snapshot_id ):
        if len( snapshot_id ) <= 1: #not a snapshot
            return False

        path = self.get_snapshot_failed_path( snapshot_id )
        return os.path.isfile( path )

    def get_snapshot_last_check(self, snapshot_id):
        """return date when snapshot has finished last time.
        this can be the end of creation of this snapshot or the last time when
        this snapshot was checked against source without changes.
        """
        info = self.get_snapshot_info_path(snapshot_id)
        if os.path.exists(info):
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getatime(info)) )
        return self.get_snapshot_display_id(snapshot_id)

    def set_snapshot_last_check(self, snapshot_id):
        """set info files atime to current time to indicate this snapshot was
        checked against source without changes right now.
        """
        info = self.get_snapshot_info_path(snapshot_id)
        if os.path.exists(info):
            os.utime(info, None)

    def clear_take_snapshot_message( self ):
        files = (self.config.get_take_snapshot_message_file(), \
                 self.config.get_take_snapshot_progress_file() )
        for file in files:
            if os.path.exists(file):
                os.remove(file)

    def get_take_snapshot_message( self ):
        wait = datetime.datetime.now() - datetime.timedelta(seconds = 30)
        if self.last_check_snapshot_runnig < wait:
            self.last_check_snapshot_runnig = datetime.datetime.now()
            if not self.check_snapshot_alive():
                self.clear_take_snapshot_message()
                return None

        try:
            with open(self.config.get_take_snapshot_message_file(), 'rt' ) as file:
                items = file.read().split( '\n' )
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
            with open( self.config.get_take_snapshot_message_file(), 'wt' ) as file:
                file.write( data )
        except:
            pass

        if 1 == type_id:
            self.append_to_take_snapshot_log( '[E] ' + message, 1 )
        else:
            self.append_to_take_snapshot_log( '[I] '  + message, 3 )

        try:
            profile_id =self.config.get_current_profile()
            profile_name = self.config.get_profile_name( profile_id )
            self.config.PLUGIN_MANAGER.on_message( profile_id, profile_name, type_id, message, timeout )
        except:
            pass

    def check_snapshot_alive(self):
        pid_file = self.config.get_take_snapshot_instance_file()
        instance = applicationinstance.ApplicationInstance(pid_file, False)
        return not instance.check()

    def _filter_take_snapshot_log( self, log, mode , decode = None):
        decode_msg = _( '''### This log has been decoded with automatic search pattern
### If some paths are not decoded you can manually decode them with:\n''')
        decode_msg += '### \'backintime --quiet'
        profile_id = self.config.get_current_profile()
        if int(profile_id) > 1:
            decode_msg += ' --profile %s' % self.config.get_profile_name(profile_id)
        decode_msg += ' --decode <path>\'\n\n'
        if 0 == mode:
            if not decode is None:
                ret = decode_msg
                for line in log.split('\n'):
                    line = decode.log(line)
                    ret += line + '\n'
                return ret
            return log

        lines = log.split( '\n' )
        log = ''
        if not decode is None:
            log = decode_msg

        for line in lines:
            if line.startswith( '[' ):
                if mode == 1 and line[1] != 'E':
                    continue
                elif mode == 2 and line[1] != 'C':
                    continue
                elif mode == 3 and line[1] != 'I':
                    continue

            if not decode is None:
                line = decode.log(line)
            log = log + line + '\n'

        return log

    def get_snapshot_log( self, snapshot_id, mode = 0, profile_id = None , **kwargs ):
        try:
            with bz2.BZ2File( self.get_snapshot_log_path( snapshot_id ), 'r' ) as file:
                data = file.read().decode()
            return self._filter_take_snapshot_log( data, mode, **kwargs )
        except:
            return ''

    def get_take_snapshot_log( self, mode = 0, profile_id = None, **kwargs ):
        try:
            with open( self.config.get_take_snapshot_log_file( profile_id ), 'rt' ) as file:
                data = file.read()
            return self._filter_take_snapshot_log( data, mode, **kwargs )
        except:
            return ''

    def new_take_snapshot_log( self, date ):
        os.system( "rm \"%s\"" % self.config.get_take_snapshot_log_file() )
        self.append_to_take_snapshot_log( "========== Take snapshot (profile %s): %s ==========\n" % ( self.config.get_current_profile(), date.strftime( '%c' ) ), 1 )

    def append_to_take_snapshot_log( self, message, level ):
        if level > self.config.log_level():
            return

        try:
            with open( self.config.get_take_snapshot_log_file(), 'at' ) as file:
                file.write( message + '\n' )
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

        with bz2.BZ2File( fileinfo_path, 'r' ) as fileinfo:
            for line in fileinfo:
                line = line.decode()
                if not line:
                    break

                line = line[ : -1 ]
                if not line:
                    continue

                index = line.find( '/' )
                if index < 0:
                    continue

                file = line[ index: ]
                if not file:
                    continue

                info = line[ : index ].strip()
                info = info.split( ' ' )

                if len( info ) == 3:
                    dict[ file ] = [ int( info[0] ), info[1], info[2] ] #perms, user, group

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

    def restore( self, snapshot_id, path, callback = None, restore_to = '', delete = False ):
        instance = applicationinstance.ApplicationInstance( self.config.get_restore_instance_file(), False, flock = True)
        if instance.check():
            instance.start_application()
        else:
            logger.warning('Restore is already running')
            return

        #inhibit suspend/hibernate during restore
        self.config.inhibitCookie = tools.inhibitSuspend(toplevel_xid = self.config.xWindowId,
                                                         reason = 'restoring')

        if restore_to.endswith('/'):
            restore_to = restore_to[ : -1 ]

        #full rsync
        full_rsync = self.config.full_rsync()

        logger.info( "Restore: %s to: %s" % (path, restore_to) )

        info_file = configfile.ConfigFile()
        info_file.load( self.get_snapshot_info_path( snapshot_id ) )

        cmd = tools.get_rsync_prefix( self.config, not full_rsync, use_modes = ['ssh'] )
        cmd = cmd + '-R -v '
        if not full_rsync:
            # During the rsync operation, directories must be rwx by the current
            # user. Files should be r and x (if executable) by the current user.
            cmd += '--chmod=Du=rwx,Fu=rX,go= '
        if self.config.is_backup_on_restore_enabled():
            cmd = cmd + "--backup --suffix=%s " % self.backup_suffix()
        src_base = self.get_snapshot_path_to( snapshot_id, use_mode = ['ssh'] )
        if delete:
            cmd += '--delete '

        src_path = path
        src_delta = 0
        if restore_to:
            aux = src_path
            if aux.startswith('/'):
                aux = aux[1:]
            items = os.path.split(src_path)
            aux = items[0]
            if aux.startswith('/'):
                aux = aux[1:]
            #bugfix: restore system root ended in <src_base>//.<src_path>
            if aux:
                src_base = os.path.join(src_base, aux) + '/'
            src_path = '/' + items[1]
            if items[0] == '/':
                src_delta = 0
            else:
                src_delta = len(items[0])

        cmd += self.rsync_remote_path('%s.%s' %(src_base, src_path), use_modes = ['ssh'])
        cmd += ' "%s/"' % restore_to
        self.restore_callback( callback, True, cmd )
        self._execute( cmd, callback, filter = (self._filter_rsync_progress, ))
        try:
            os.remove(self.config.get_take_snapshot_progress_file())
        except:
            pass

        if full_rsync and not self.config.get_snapshots_mode() in ['ssh', 'ssh_encfs']:
            instance.exit_application()
            return

        #restore permissions
        logger.info( 'Restore permissions' )
        self.restore_callback( callback, True, '' )
        self.restore_callback( callback, True, _("Restore permissions:") )
        file_info_dict = self.load_fileinfo_dict( snapshot_id, info_file.get_int_value( 'snapshot_version' ) )
        if file_info_dict:
            #explore items
            snapshot_path_to = self.get_snapshot_path_to( snapshot_id, path ).rstrip( '/' )
            root_snapshot_path_to = self.get_snapshot_path_to( snapshot_id ).rstrip( '/' )
            all_dirs = [] #restore dir permissions after all files are done

            if not restore_to:
                path_items = path.strip( '/' ).split( '/' )
                curr_path = '/'
                for path_item in path_items:
                    curr_path = os.path.join( curr_path, path_item )
                    all_dirs.append( curr_path )
            else:
                    all_dirs.append(path)

            if os.path.isdir( snapshot_path_to ) and not os.path.islink( snapshot_path_to ):
                for explore_path, dirs, files in os.walk( snapshot_path_to ):
                    for item in dirs:
                        item_path = os.path.join( explore_path, item )[ len( root_snapshot_path_to ) : ]
                        all_dirs.append( item_path )

                    for item in files:
                        item_path = os.path.join( explore_path, item )[ len( root_snapshot_path_to ) : ]
                        real_path = restore_to + item_path[src_delta:]
                        self._restore_path_info( item_path, real_path, file_info_dict, callback )

            all_dirs.reverse()
            for item_path in all_dirs:
                real_path = restore_to + item_path[src_delta:]
                self._restore_path_info( item_path, real_path, file_info_dict, callback )

        #release inhibit suspend
        if self.config.inhibitCookie:
            tools.unInhibitSuspend(self.config.inhibitCookie)

        instance.exit_application()

    def backup_suffix(self):
        return '.backup.' + datetime.date.today().strftime( '%Y%m%d' )

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

        list_ = []

        for item in biglist:
            if len( item ) != 15 and len( item ) != 19:
                continue
            if os.path.isdir( os.path.join( snapshots_path, item, 'backup' ) ):
                list_.append( item )

        list_.sort( reverse = sort_reverse )

        return list_

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

        list_ = []

        for item in biglist:
            if len( item ) != 15 and len( item ) != 19:
                continue
            if os.path.isdir( os.path.join( snapshots_path, item, 'backup' ) ):
                list_.append( item )

        if snapshots_other_paths:
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
                        list_.append( member )

        list_.sort( reverse = sort_reverse )
        return list_

    def remove_snapshot( self, snapshot_id ):
        if len( snapshot_id ) <= 1:
            return
        path = self.get_snapshot_path( snapshot_id, use_mode = ['ssh', 'ssh_encfs'] )
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

    def update_snapshots_location( self ):
        '''Updates to location: backintime/machine/user/profile_id'''
        if self.has_old_snapshots():
            logger.info( 'Snapshot location update flag detected' )
            logger.warning( 'Snapshot location needs update' )
            profiles = self.config.get_profiles()

            answer_change = self.config.question_handler( _('Back In Time changed its backup format.\n\nYour old snapshots can be moved according to this new format. OK?') )
            if answer_change == True:
                logger.info( 'Update snapshot locations' )

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
                profile_id = profiles[0]
                main_folder = self.config.get_snapshots_path( profile_id )
                old_snapshots_paths=[]
                counter = 0
                success = []

                for profile_id in profiles:
                    old_snapshots_paths.append( self.config.get_snapshots_path( profile_id ) )
                    old_folder = os.path.join( self.config.get_snapshots_path( profile_id ), 'backintime' )
                    if profile_id != "1" and answer_same == True:
                        self.config.set_snapshots_path( main_folder, profile_id )
                        logger.info( 'Folder of profile %s is set to %s' %( profile_id, main_folder ) )
                    else:
                        self.config.set_snapshots_path( self.config.get_snapshots_path( profile_id ), profile_id )
                        logger.info( 'Folder of profile %s is set to %s' %( profile_id, main_folder ) )
                    new_folder = self.config.get_snapshots_full_path( profile_id )

                    output = tools.move_snapshots_folder( old_folder, new_folder )

                    snapshots_left = tools.get_snapshots_list_in_folder( old_folder )
                    if output == True:
                        success.append( True )
                        if not snapshots_left:
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
                            self.config.error_handler( _('Former settings of profile %s are restored.\nBack In Time cannot continue taking new snapshots.\n\nYou can manually move the snapshots, \nif you are done restart Back In Time to proceed' %profile_id ) )

                    counter = counter + 1

                overall_success = True
                for item in success:
                    if item == False:
                        overall_success = False
                if overall_success == True:
                    logger.info( 'Back In Time will be able to make new snapshots again!' )
                    self.config.error_handler( _('Update was successful!\n\nBack In Time will continue taking snapshots again as scheduled' ) )

            elif answer_change == False:
                logger.info( 'Move refused by user' )
                logger.warning( 'Old snapshots are not taken into account by smart-remove' )
                answer_continue = self.config.question_handler( _('Are you sure you do not want to move your old snapshots?\n\n\nIf you do, you will not see these questions again next time, Back In Time will continue making snapshots again, but smart-remove cannot take your old snapshots into account any longer!\n\nIf you do not, you will be asked again next time you start Back In Time.') )
                if answer_continue == True:
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
        ret_val, ret_error = False, True
        sleep = True

        self.config.PLUGIN_MANAGER.load_plugins( self )

        if not self.config.is_configured():
            logger.warning( 'Not configured' )
            self.config.PLUGIN_MANAGER.on_error( 1 ) #not configured
        elif not force and self.config.is_no_on_battery_enabled() and tools.on_battery():
            self.set_take_snapshot_message(0, _('Deferring backup while on battery'))
            logger.info( 'Deferring backup while on battery' )
            logger.warning( 'Backup not performed' )
        elif self.has_old_snapshots():
            logger.info( 'The application needs to change the backup format. Start the GUI to proceed. (As long as you do not you will not be able to make new snapshots!)' )
            logger.warning( 'Backup not performed' )
        elif not force and not self.config.is_backup_scheduled():
            logger.info('Profile "%s" is not scheduled to run now.' % self.config.get_profile_name())
        else:
            instance = applicationinstance.ApplicationInstance( self.config.get_take_snapshot_instance_file(), False, flock = True)
            restore_instance = applicationinstance.ApplicationInstance( self.config.get_restore_instance_file(), False )
            if not instance.check():
                logger.warning( 'A backup is already running' )
                self.config.PLUGIN_MANAGER.on_error( 2 ) #a backup is already running
            elif not restore_instance.check():
                logger.warning( 'Restore is still running. Stop backup until restore is done.' )
            else:
                if self.config.is_no_on_battery_enabled () and not tools.power_status_available():
                    logger.warning( 'Backups disabled on battery but power status is not available' )

                instance.start_application()
                logger.info( 'Lock' )

                now = datetime.datetime.today()

                #inhibit suspend/hibernate during snapshot is running
                self.config.inhibitCookie = tools.inhibitSuspend(toplevel_xid = self.config.xWindowId)

                #mount
                try:
                    hash_id = mount.Mount(cfg = self.config).mount()
                except mount.MountException as ex:
                    logger.error(str(ex))
                    instance.exit_application()
                    logger.info( 'Unlock' )
                    time.sleep(2)
                    return False
                else:
                    self.config.set_current_hash_id(hash_id)

                #include_folders, ignore_folders, dict = self._get_backup_folders( now, force )
                include_folders = self.config.get_include()

                if not include_folders:
                    logger.info( 'Nothing to do' )
                elif not self.config.PLUGIN_MANAGER.on_process_begins():
                    logger.info( 'A plugin prevented the backup' )
                else:
                    #take snapshot process begin
                    logger.info( "on process begins" )
                    self.set_take_snapshot_message( 0, '...' )
                    self.new_take_snapshot_log( now )
                    profile_id = self.config.get_current_profile()
                    logger.info( "Profile_id: %s" % profile_id )

                    if not self.config.can_backup( profile_id ):
                        if self.config.PLUGIN_MANAGER.has_gui_plugins() and self.config.is_notify_enabled():
                            self.set_take_snapshot_message( 1,
                                    _('Can\'t find snapshots folder.\nIf it is on a removable drive please plug it.' ) +
                                    '\n' +
                                    gettext.ngettext( 'Waiting %s second.', 'Waiting %s seconds.', 30 ) % 30,
                                    30 )
                        for counter in range( 30, 0, -1 ):
                            time.sleep(1)
                            if self.config.can_backup():
                                break

                    if not self.config.can_backup( profile_id ):
                        logger.warning( 'Can\'t find snapshots folder !' )
                        self.config.PLUGIN_MANAGER.on_error( 3 ) #Can't find snapshots directory (is it on a removable drive ?)
                    else:
                        ret_error = False
                        snapshot_id = self.get_snapshot_id( now )
                        snapshot_path = self.get_snapshot_path( snapshot_id )

                        if os.path.exists( snapshot_path ):
                            logger.warning( "Snapshot path \"%s\" already exists" % snapshot_path )
                            self.config.PLUGIN_MANAGER.on_error( 4, snapshot_id ) #This snapshots already exists
                        else:
                            ret_val, ret_error = self._take_snapshot( snapshot_id, now, include_folders )

                        if not ret_val:
                            self._execute( "rm -rf \"%s\"" % snapshot_path )

                            if ret_error:
                                logger.error( 'Failed to take snapshot !!!' )
                                self.set_take_snapshot_message( 1, _('Failed to take snapshot %s !!!') % now.strftime( '%x %H:%M:%S' ) )
                                time.sleep(2)
                            else:
                                logger.warning( "No new snapshot" )
                        else:
                            ret_error = False

                        if not ret_error:
                            self._free_space( now )
                            self.set_take_snapshot_message( 0, _('Finalizing') )

                    time.sleep(2)
                    sleep = False

                    if ret_val:
                        self.config.PLUGIN_MANAGER.on_new_snapshot( snapshot_id, snapshot_path ) #new snapshot

                    self.config.PLUGIN_MANAGER.on_process_ends() #take snapshot process end

                if sleep:
                    time.sleep(2)
                    sleep = False

                if not ret_error:
                    self.clear_take_snapshot_message()

                #unmount
                try:
                    mount.Mount(cfg = self.config).umount(self.config.current_hash_id)
                except mount.MountException as ex:
                    logger.error(str(ex))

                instance.exit_application()
                logger.info( 'Unlock' )

        if sleep:
            time.sleep(2) #max 1 backup / second

        if not ret_error and not list(self.config.anacrontab_files()):
            tools.writeTimeStamp(self.config.get_anacron_spool_file())

        #release inhibit suspend
        if self.config.inhibitCookie:
            tools.unInhibitSuspend(self.config.inhibitCookie)

        return ret_val

    def _filter_rsync_progress(self, line):
        m = self.reRsyncProgress.match(line)
        if m:
            pg = progress.ProgressFile(self.config)
            pg.set_int_value('status', pg.RSYNC)
            pg.set_str_value('sent', m.group(1) )
            pg.set_int_value('percent', int(m.group(2)) )
            pg.set_str_value('speed', m.group(3) )
            pg.set_str_value('eta', m.group(4) )
            pg.save()
            del(pg)
            return
        return line

    def _exec_rsync_callback( self, line, params ):
        if not line:
            return

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
        if len(line) >= 13:
            if line.startswith( 'BACKINTIME: ' ):
                if line[12] != '.':
                    params[1] = True
                    self.append_to_take_snapshot_log( '[C] ' + line[ 12 : ], 2 )

    def _append_item_to_list( self, item, list_ ):
        for list_item in list_:
            if item == list_item:
                return
        list_.append( item )

    def _is_auto_backup_needed( self, now, last, mode ):
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

    def _create_directory( self, folder ):
        tools.make_dirs( folder )

        if not os.path.exists( folder ):
            logger.error( "Can't create folder: %s" % folder )
            self.set_take_snapshot_message( 1, _('Can\'t create folder: %s') % folder )
            time.sleep(2) #max 1 backup / second
            return False

        return True

    def _save_path_info_line( self, fileinfo, path, info ):
        s = "{} {} {} {}\n".format(info[0], info[1], info[2], path)
        fileinfo.write(s.encode())

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
            self._execute( "find \"%s\" -type d -exec chmod u+wx {} %s" % (new_snapshot_path(), find_suffix) ) #Debian patch
            self._execute( "rm -rf \"%s\"" % new_snapshot_path() )

            if os.path.exists( new_snapshot_path() ):
                logger.error( "Can't remove folder: %s" % new_snapshot_path() )
                self.set_take_snapshot_message( 1, _('Can\'t remove folder: %s') % new_snapshot_path() )
                time.sleep(2) #max 1 backup / second
                return [ False, True ]

        #create exclude patterns string
        items = []
        encode = self.config.ENCODE
        for exclude in self.config.get_exclude():
            exclude = encode.exclude(exclude)
            if exclude is None:
                continue
            self._append_item_to_list( "--exclude=\"%s\"" % exclude, items )
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

            folder = encode.include(folder)
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
        rsync_prefix = tools.get_rsync_prefix( self.config, not full_rsync )
        if self.config.exclude_by_size_enabled():
            rsync_prefix += ' --max-size=%sM' % self.config.exclude_by_size()
        rsync_exclude_backup_directory = " --exclude=\"%s\" --exclude=\"%s\" --exclude=\"%s\" " % \
                ( encode.exclude( self.config.get_snapshots_path() ), \
                  encode.exclude( self.config._LOCAL_DATA_FOLDER ) ,  \
                  encode.exclude( self.config._MOUNT_ROOT ) )
        rsync_suffix = ' --chmod=Du+wx ' + rsync_exclude_backup_directory
        rsync_suffix += rsync_include + ' ' + rsync_exclude + ' ' + rsync_include2
        rsync_suffix += ' --exclude=\"*\" ' + encode.chroot + ' '

        prev_snapshot_id = ''
        snapshots = self.get_snapshots_list()
        if not snapshots:
            snapshots = self.get_snapshots_and_other_list()

        # When there is no snapshots it takes the last snapshot from the other folders
        # It should delete the excluded folders then
        rsync_prefix = rsync_prefix + ' --delete --delete-excluded '

        if snapshots:
            prev_snapshot_id = snapshots[0]

            if not full_rsync:
                changed = True
                if check_for_changes:
                    prev_snapshot_name = self.get_snapshot_display_id( prev_snapshot_id )
                    self.set_take_snapshot_message( 0, _('Compare with snapshot %s') % prev_snapshot_name )
                    logger.info( "Compare with old snapshot: %s" % prev_snapshot_id )

                    cmd  = rsync_prefix + ' -i --dry-run --out-format="BACKINTIME: %i %n%L"' + rsync_suffix
                    cmd += self.rsync_remote_path( prev_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']) )
                    params = [ prev_snapshot_path_to(), False ]
                    self.append_to_take_snapshot_log( '[I] ' + cmd, 3 )
                    self._execute( cmd, self._exec_rsync_compare_callback, params )
                    changed = params[1]

                    if not changed:
                        logger.info( "Nothing changed, no back needed" )
                        self.set_snapshot_last_check(prev_snapshot_id)
                        return [ False, False ]

            if not self._create_directory( new_snapshot_path_to() ):
                return [ False, True ]

            if not full_rsync:
                self.set_take_snapshot_message( 0, _('Create hard-links') )
                logger.info( "Create hard-links" )

                #make source snapshot folders rw to allow cp -al
                self._execute( self.cmd_ssh('find \"%s\" -type d -exec chmod u+wx \"{}\" %s' % (prev_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']), find_suffix), quote = True) ) #Debian patch

                #clone snapshot
                cmd = self.cmd_ssh( "cp -aRl \"%s\"* \"%s\"" % ( prev_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']), new_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']) ) )
                self.append_to_take_snapshot_log( '[I] ' + cmd, 3 )
                cmd_ret_val = self._execute( cmd )
                self.append_to_take_snapshot_log( "[I] returns: %s" % cmd_ret_val, 3 )

                #make source snapshot folders read-only
                self._execute( self.cmd_ssh( 'find \"%s\" -type d -exec chmod a-w \"{}\" %s' % (prev_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']), find_suffix), quote = True) ) #Debian patch

                #make snapshot items rw to allow xopy xattr
                self._execute( self.cmd_ssh( "chmod -R a+w \"%s\"" % new_snapshot_path(use_mode = ['ssh', 'ssh_encfs']) ) )

        else:
            if not self._create_directory( new_snapshot_path_to() ):
                return [ False, True ]

        #sync changed folders
        logger.info( "Call rsync to take the snapshot" )
        cmd = rsync_prefix + ' -v ' + rsync_suffix
        cmd += self.rsync_remote_path( new_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']) )

        self.set_take_snapshot_message( 0, _('Take snapshot') )

        if full_rsync:
            if prev_snapshot_id:
                link_dest = encode.path( os.path.join(prev_snapshot_id, 'backup') )
                link_dest = os.path.join('..', '..', link_dest)
                cmd = cmd + " --link-dest=\"%s\"" % link_dest

            cmd = cmd + ' -i --out-format="BACKINTIME: %i %n%L"'

        params = [False, False]
        self.append_to_take_snapshot_log( '[I] ' + cmd, 3 )
        self._execute( cmd + ' 2>&1', self._exec_rsync_callback, params, filter = (self._filter_rsync_progress, ))
        try:
            os.remove(self.config.get_take_snapshot_progress_file())
        except:
            pass

        has_errors = False
        if params[0]:
            if not self.config.continue_on_errors():
                self._execute( self.cmd_ssh( 'find \"%s\" -type d -exec chmod u+wx \"{}\" %s' % (new_snapshot_path(use_mode = ['ssh', 'ssh_encfs']), find_suffix), quote = True) ) #Debian patch
                self._execute( self.cmd_ssh( "rm -rf \"%s\"" % new_snapshot_path(use_mode = ['ssh', 'ssh_encfs']) ) )

                if not full_rsync:
                    #fix previous snapshot: make read-only again
                    if prev_snapshot_id:
                        self._execute( self.cmd_ssh("chmod -R a-w \"%s\"" % prev_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']) ) )

                return [ False, True ]

            has_errors = True
            self._execute( "touch \"%s\"" % self.get_snapshot_failed_path( new_snapshot_id ) )

        if full_rsync:
            if not params[1]:
                self._execute( self.cmd_ssh( 'find \"%s\" -type d -exec chmod u+wx \"{}\" %s' % (new_snapshot_path(use_mode = ['ssh', 'ssh_encfs']), find_suffix), quote = True) ) #Debian patch
                self._execute( self.cmd_ssh( "rm -rf \"%s\"" % new_snapshot_path(use_mode = ['ssh', 'ssh_encfs']) ) )

                logger.info( "Nothing changed, no back needed" )
                self.set_snapshot_last_check(prev_snapshot_id)
                return [ False, False ]


        #backup config file
        logger.info( 'Save config file' )
        self.set_take_snapshot_message( 0, _('Save config file ...') )
        self._execute( 'cp %s %s' % (self.config._LOCAL_CONFIG_PATH, new_snapshot_path_to() + '..') )

        if not full_rsync or self.config.get_snapshots_mode() in ['ssh', 'ssh_encfs']:
            #save permissions for sync folders
            logger.info( 'Save permissions' )
            self.set_take_snapshot_message( 0, _('Save permission ...') )

            with bz2.BZ2File( self.get_snapshot_fileinfo_path( new_snapshot_id ), 'wb' ) as fileinfo:
                path_to_explore = self.get_snapshot_path_to( new_snapshot_id ).rstrip( '/' )
                fileinfo_dict = {}

                permission_done = False
                if self.config.get_snapshots_mode() in ['ssh', 'ssh_encfs']:
                    path_to_explore_ssh = new_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']).rstrip( '/' )
                    cmd = self.cmd_ssh(['find', path_to_explore_ssh, '-name', '\*', '-print'])

                    find = subprocess.Popen(cmd, stdout = subprocess.PIPE,
                                            stderr = subprocess.PIPE,
                                            universal_newlines = True)
                    output = find.communicate()[0]
                    if find.returncode:
                        logger.warning('Save permission over ssh failed. Retry normal methode')
                    else:
                        if self.config.get_snapshots_mode() == 'ssh_encfs':
                            decode = encfstools.Decode(self.config)
                            path_to_explore_ssh = decode.remote(path_to_explore_ssh)
                        else:
                            decode = encfstools.Bounce()
                        for line in output.split('\n'):
                            if line:
                                line = decode.remote(line)
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

        #create info file
        logger.info( "Create info file" )
        machine = self.config.get_host()
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
            with open( self.config.get_take_snapshot_log_file(), 'rb' ) as logfile:
                with bz2.BZ2File( self.get_snapshot_log_path( new_snapshot_id ), 'wb' ) as logfile_bz2:
                    for line in logfile:
                        logfile_bz2.write(line)
        except:
            pass

        #rename snapshot
        os.system( self.cmd_ssh( "mv \"%s\" \"%s\"" % ( new_snapshot_path(use_mode = ['ssh', 'ssh_encfs']), snapshot_path(use_mode = ['ssh', 'ssh_encfs']) ) ) )

        if not os.path.exists( snapshot_path() ):
            logger.error( "Can't rename %s to %s" % ( new_snapshot_path(), snapshot_path() ) )
            self.set_take_snapshot_message( 1, _('Can\'t rename %(new_path)s to %(path)s') % { 'new_path' : new_snapshot_path(), 'path' : snapshot_path() } )
            time.sleep(2) #max 1 backup / second
            return [ False, True ]

        if not full_rsync:
            #make new snapshot read-only
            self._execute( self.cmd_ssh( "chmod -R a-w \"%s\"" % snapshot_path(use_mode = ['ssh', 'ssh_encfs']) ) )

        #create last_snapshot symlink
        self.create_last_snapshot_symlink(snapshot_id)

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
            for i in range( 0, keep_one_per_day ):
                keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, d, d + datetime.timedelta(days=1) )
                d = d - datetime.timedelta(days=1)

        #keep one per week for the last keep_one_per_week weeks
        if keep_one_per_week > 0:
            d = now - datetime.timedelta( days = now.weekday() + 1 )
            for i in range( 0, keep_one_per_week ):
                keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, d, d + datetime.timedelta(days=8) )
                d = d - datetime.timedelta(days=7)

        #keep one per month for the last keep_one_per_month months
        if keep_one_per_month > 0:
            d1 = datetime.date( now.year, now.month, 1 )
            d2 = self.inc_month( d1 )
            for i in range( 0, keep_one_per_month ):
                keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, d1, d2 )
                d2 = d1
                d1 = self.dec_month(d1)

        #keep one per year for all years
        first_year = int(snapshots[-1][ : 4])
        for i in range( first_year, now.year+1 ):
            keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, datetime.date(i,1,1), datetime.date(i+1,1,1) )

        logger.info( "[smart remove] keep snapshots: %s" % keep_snapshots )

        del_snapshots = []
        for snapshot_id in snapshots:
            if snapshot_id in keep_snapshots:
                continue

            if self.config.get_dont_remove_named_snapshots():
                if self.get_snapshot_name( snapshot_id ):
                    logger.info( "[smart remove] keep snapshot: %s, it has a name" % snapshot_id )
                    continue

            del_snapshots.append(snapshot_id)

        for i, snapshot_id in enumerate(del_snapshots, 1):
            self.set_take_snapshot_message( 0, _('Smart remove') + ' %s/%s' %(i, len(del_snapshots)) )
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
                    if self.get_snapshot_name( snapshots[0] ):
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

                info = os.statvfs( self.config.get_snapshots_path() )
                free_space = info.f_frsize * info.f_bavail // ( 1024 * 1024 )

                if free_space >= min_free_space:
                    break

                if self.config.get_dont_remove_named_snapshots():
                    if self.get_snapshot_name( snapshots[0] ):
                        del snapshots[0]
                        continue

                logger.info( "free disk space: %s Mb" % free_space )
                self.remove_snapshot( snapshots[0] )
                del snapshots[0]

        #try to keep free inodes
        if self.config.min_free_inodes_enabled():
            min_free_inodes = self.config.min_free_inodes()
            self.set_take_snapshot_message( 0, _('Try to keep min %d%% free inodes') % min_free_inodes )
            logger.info( "Keep min %d%% free inodes" % min_free_inodes )

            snapshots = self.get_snapshots_list( False )

            while True:
                if len( snapshots ) <= 1:
                    break

                info = os.statvfs( self.config.get_snapshots_path() )
                free_inodes = info.f_favail
                max_inodes  = info.f_files

                if free_inodes >= max_inodes * (min_free_inodes / 100.0):
                    break

                if self.config.get_dont_remove_named_snapshots():
                    if self.get_snapshot_name( snapshots[0] ):
                        del snapshots[0]
                        continue

                logger.info( "free inodes: %.2f%%" % (100.0 / max_inodes * free_inodes) )
                self.remove_snapshot( snapshots[0] )
                del snapshots[0]

    def _execute( self, cmd, callback = None, user_data = None, filter = () ):
        ret_val = 0

        if callback is None:
            ret_val = os.system( cmd )
        else:
            pipe = os.popen( cmd, 'r' )

            while True:
                line = tools.temp_failure_retry( pipe.readline )
                if not line:
                    break
                line = line.strip()
                for f in filter:
                    line = f(line)
                callback(line , user_data )

            ret_val = pipe.close()
            if ret_val is None:
                ret_val = 0

        if ret_val != 0:
            logger.warning( "Command \"%s\" returns %s" % ( cmd, ret_val ) )
        else:
            logger.info( "Command \"%s\" returns %s" % ( cmd, ret_val ) )

        return ret_val

    def filter_for(self, base_snapshot_id, base_path, snapshots_list, list_diff_only  = False, flag_deep_check = False, list_equal_to = False):
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
        if not list_diff_only and not list_equal_to:
            for snapshot_id in all_snapshots_list:
                path = self.get_snapshot_path_to( snapshot_id, base_path )

                if os.path.exists( path ) and not os.path.islink( path ) and os.path.isfile( path ):
                    snapshots_filtered.append(snapshot_id)

            return snapshots_filtered

        # check for duplicates
        uniqueness = tools.UniquenessSet(flag_deep_check, follow_symlink = False, list_equal_to = list_equal_to)
        for snapshot_id in all_snapshots_list:
            path = self.get_snapshot_path_to( snapshot_id, base_path )
            if os.path.exists( path ) and not os.path.islink( path ) and os.path.isfile( path ) and uniqueness.check_for(path):
                snapshots_filtered.append(snapshot_id)

        return snapshots_filtered

    def cmd_ssh(self, cmd, quote = False, use_modes = ['ssh', 'ssh_encfs'] ):
        mode = self.config.get_snapshots_mode()
        if mode in ['ssh', 'ssh_encfs'] and mode in use_modes:
            (ssh_host, ssh_port, ssh_user, ssh_path, ssh_cipher) = self.config.get_ssh_host_port_user_path_cipher()
            if isinstance(cmd, str):
                if ssh_cipher == 'default':
                    ssh_cipher_suffix = ''
                else:
                    ssh_cipher_suffix = '-c %s' % ssh_cipher

                if self.config.is_run_ionice_on_remote_enabled():
                    cmd = 'ionice -c2 -n7 ' + cmd

                if self.config.is_run_nice_on_remote_enabled():
                    cmd = 'nice -n 19 ' + cmd

                if quote:
                    cmd = '\'%s\'' % cmd

                return 'ssh -p %s -o ServerAliveInterval=240 %s %s@%s %s' \
                        % ( str(ssh_port), ssh_cipher_suffix, ssh_user, ssh_host, cmd )

            if isinstance(cmd, tuple):
                cmd = list(cmd)

            if isinstance(cmd, list):
                suffix = ['ssh', '-p', str(ssh_port)]
                suffix += ['-o', 'ServerAliveInterval=240']
                if not ssh_cipher == 'default':
                    suffix += ['-c', ssh_cipher]
                suffix += ['%s@%s' % (ssh_user, ssh_host)]

                if self.config.is_run_ionice_on_remote_enabled():
                    cmd = ['ionice', '-c2', '-n7'] + cmd

                if self.config.is_run_nice_on_remote_enabled():
                    cmd = ['nice', '-n 19'] + cmd

                if quote:
                    cmd = ['\''] + cmd + ['\'']
                return suffix + cmd

        else:
            return cmd

    def rsync_remote_path(self, path, use_modes = ['ssh', 'ssh_encfs'] ):
        mode = self.config.get_snapshots_mode()
        if mode in ['ssh', 'ssh_encfs'] and mode in use_modes:
            user = self.config.get_ssh_user()
            host = self.config.get_ssh_host()
            return '\'%s@%s:"%s"\'' % (user, host, path)
        else:
            return '"%s"' % path

    def delete_path(self, snapshot_id, path):
        def handle_error(fn, path, excinfo):
            dir = os.path.dirname(path)
            if not os.access(dir, os.W_OK):
                st = os.stat(dir)
                os.chmod(dir, st.st_mode | stat.S_IWUSR)
            st = os.stat(path)
            os.chmod(path, st.st_mode | stat.S_IWUSR)
            fn(path)

        full_path = self.get_snapshot_path_to(snapshot_id, path)
        dirname = os.path.dirname(full_path)
        dir_st = os.stat(dirname)
        os.chmod(dirname, dir_st.st_mode | stat.S_IWUSR)
        if os.path.isdir(full_path) and not os.path.islink(full_path):
            shutil.rmtree(full_path, onerror = handle_error)
        else:
            st = os.stat(full_path)
            os.chmod(full_path, st.st_mode | stat.S_IWUSR)
            os.remove(full_path)
        os.chmod(dirname, dir_st.st_mode)

    def create_last_snapshot_symlink(self, snapshot_id):
        symlink = self.config.get_last_snapshot_symlink()
        try:
            if os.path.islink(symlink):
                os.remove(symlink)
            if os.path.exists(symlink):
                return False
            os.symlink(snapshot_id, symlink)
        except:
            return False

if __name__ == "__main__":
    config = config.Config()
    snapshots = Snapshots( config )
    snapshots.take_snapshot()

