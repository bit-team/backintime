#	Back In Time
#	Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import bz2
import pwd
import grp
import subprocess
import shutil
import time
import re
import fcntl

import config
import configfile
import logger
import applicationinstance
import tools
import encfstools
import mount
import progress
import bcolors
from exceptions import MountException

_=gettext.gettext


class Snapshots:
    SNAPSHOT_VERSION = 3
    GLOBAL_FLOCK = '/tmp/backintime.lock'

    def __init__( self, cfg = None ):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()

        self.clear_uid_gid_cache()
        self.clear_uid_gid_names_cache()

        #rsync --info=progress2 output
        #search for:     517.38K  26%   14.46MB/s    0:02:36
        #or:             497.84M   4% -449.39kB/s   ??:??:??
        #but filter out: 517.38K  26%   14.46MB/s    0:00:53 (xfr#53, to-chk=169/452)
        #                because this shows current run time
        self.reRsyncProgress = re.compile(r'.*?'                            #trash at start
                                          r'(\d*[,\.]?\d+[KkMGT]?)\s+'      #bytes sent
                                          r'(\d*)%\s+'                      #percent done
                                          r'(-?\d*[,\.]?\d*[KkMGT]?B/s)\s+' #speed
                                          r'([\d\?]+:[\d\?]{2}:[\d\?]{2})'  #estimated time of arrival
                                          r'(.*$)')                         #trash at the end

        self.last_check_snapshot_runnig = datetime.datetime(1,1,1)
        self.flock_file = None

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
        name = ''
        if len( snapshot_id ) <= 1: #not a snapshot
            return name

        path = self.get_snapshot_path( snapshot_id )
        nameFile = os.path.join(path, 'name')
        if not os.path.isdir( path ):
            return name

        if not os.path.exists(nameFile):
            return name
        try:
            with open(nameFile, 'rt') as f:
                name = f.read()
        except Exception as e:
            logger.debug('Failed to get snapshot %s name: %s'
                         %(snapshot_id, str(e)),
                         self)

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
            with open( name_path, 'wt' ) as f:
                f.write( name )
        except Exception as e:
            logger.debug('Failed to set snapshot %s name: %s'
                         %(snapshot_id, str(e)),
                         self)
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
        for f in files:
            if os.path.exists(f):
                os.remove(f)

    def get_take_snapshot_message( self ):
        wait = datetime.datetime.now() - datetime.timedelta(seconds = 30)
        if self.last_check_snapshot_runnig < wait:
            self.last_check_snapshot_runnig = datetime.datetime.now()
            if not self.check_snapshot_alive():
                self.clear_take_snapshot_message()
                return None

        if not os.path.exists(self.config.get_take_snapshot_message_file()):
            return None
        try:
            with open(self.config.get_take_snapshot_message_file(), 'rt' ) as f:
                items = f.read().split( '\n' )
        except Exception as e:
            logger.debug('Failed to get take_snapshot message from %s: %s'
                         %(self.config.get_take_snapshot_message_file(), str(e)),
                         self)
            return None

        if len( items ) < 2:
            return None

        mid = 0
        try:
            mid = int( items[0] )
        except Exception as e:
            logger.debug('Failed extract message ID from %s: %s'
                         %(items[0], str(e)),
                         self)
            pass

        del items[0]
        message = '\n'.join( items )

        return( mid, message )

    def set_take_snapshot_message( self, type_id, message, timeout = -1 ):
        data = str(type_id) + '\n' + message

        try:
            with open( self.config.get_take_snapshot_message_file(), 'wt' ) as f:
                f.write( data )
        except Exception as e:
            logger.debug('Failed to set take_snapshot message to %s: %s'
                         %(self.config.get_take_snapshot_message_file(), str(e)),
                         self)
            pass

        if 1 == type_id:
            self.append_to_take_snapshot_log( '[E] ' + message, 1 )
        else:
            self.append_to_take_snapshot_log( '[I] '  + message, 3 )

        try:
            profile_id =self.config.get_current_profile()
            profile_name = self.config.get_profile_name( profile_id )
            self.config.PLUGIN_MANAGER.on_message( profile_id, profile_name, type_id, message, timeout )
        except Exception as e:
            logger.debug('Failed to send message to plugins: %s'
                         %str(e),
                         self)
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
            with bz2.BZ2File( self.get_snapshot_log_path( snapshot_id ), 'r' ) as f:
                data = f.read().decode()
            return self._filter_take_snapshot_log( data, mode, **kwargs )
        except Exception as e:
            logger.debug('Failed to get snapshot log from %s: %s'
                         %(self.get_snapshot_log_path(snapshot_id), str(e)),
                         self)
            return ''

    def get_take_snapshot_log( self, mode = 0, profile_id = None, **kwargs ):
        logFile = self.config.get_take_snapshot_log_file(profile_id)
        try:
            with open(logFile, 'rt') as f:
                data = f.read()
            return self._filter_take_snapshot_log( data, mode, **kwargs )
        except Exception as e:
            msg = ('Failed to get take_snapshot log from %s:' %logFile, str(e))
            logger.debug(' '.join(msg), self)
            return '\n'.join(msg)

    def new_take_snapshot_log( self, date ):
        os.system( "rm \"%s\"" % self.config.get_take_snapshot_log_file() )
        self.append_to_take_snapshot_log( "========== Take snapshot (profile %s): %s ==========\n" % ( self.config.get_current_profile(), date.strftime( '%c' ) ), 1 )

    def append_to_take_snapshot_log( self, message, level ):
        if level > self.config.log_level():
            return

        try:
            with open( self.config.get_take_snapshot_log_file(), 'at' ) as f:
                f.write( message + '\n' )
        except Exception as e:
            logger.debug('Failed to add message to take_snapshot log %s: %s'
                         %(self.config.get_take_snapshot_log_file(), str(e)),
                         self)
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

        file_info_dict = {}

        if 0 == version:
            return file_info_dict

        fileinfo_path = self.get_snapshot_fileinfo_path( snapshot_id )
        if not os.path.exists( fileinfo_path ):
            return file_info_dict

        with bz2.BZ2File( fileinfo_path, 'rb' ) as fileinfo:
            for line in fileinfo:
                if not line:
                    break

                line = line[ : -1 ]
                if not line:
                    continue

                index = line.find( b'/' )
                if index < 0:
                    continue

                f = line[ index: ]
                if not f:
                    continue

                info = line[ : index ].strip()
                info = info.split( b' ' )

                if len( info ) == 3:
                    file_info_dict[f] = (int(info[0]), info[1], info[2]) #perms, user, group

        return file_info_dict

    def clear_uid_gid_names_cache(self):
        self.user_cache = {}
        self.group_cache = {}

    def clear_uid_gid_cache(self):
        self.uid_cache = {}
        self.gid_cache = {}

    def get_uid( self, name ):
        if name in self.uid_cache:
            return self.uid_cache[name]
        else:
            uid = -1
            try:
                uid = pwd.getpwnam(name.decode()).pw_uid
            except Exception as e:
                logger.debug('Failed to get UID for %s: %s'
                             %(name, str(e)),
                             self)
                pass

            self.uid_cache[name] = uid
            return uid

    def get_gid( self, name ):
        if name in self.gid_cache:
            return self.gid_cache[name]
        else:
            gid = -1
            try:
                gid = grp.getgrnam(name.decode()).gr_gid
            except Exception as e:
                logger.debug('Failed to get GID for %s: %s'
                             %(name, str(e)),
                             self)
                pass

            self.gid_cache[name] = gid
            return gid

    def get_user_name( self, uid ):
        if uid in self.user_cache:
            return self.user_cache[uid]
        else:
            name = '-'
            try:
                name = pwd.getpwuid(uid).pw_name
            except Exception as e:
                logger.debug('Failed to get user name for UID %s: %s'
                             %(uid, str(e)),
                             self)
                pass

            self.user_cache[uid] = name
            return name

    def get_group_name( self, gid ):
        if gid in self.group_cache:
            return self.group_cache[gid]
        else:
            name = '-'
            try:
                name = grp.getgrgid(gid).gr_name
            except Exception as e:
                logger.debug('Failed to get group name for GID %s: %s'
                             %(gid, str(e)),
                             self)
                pass

            self.group_cache[gid] = name
            return name

    def restore_callback( self, callback, ok, msg ):
        if not callback is None:
            if not ok:
                msg = msg + " : " + _("FAILED")
            callback( msg )

    def _restore_path_info( self, key_path, path, file_info_dict, callback = None ):
        assert isinstance(key_path, bytes), 'key_path is not bytes type: %s' % key_path
        assert isinstance(path, bytes), 'path is not bytes type: %s' % path
        if key_path not in file_info_dict or not os.path.exists(path):
            return
        info = file_info_dict[key_path]

        #restore uid/gid
        uid = self.get_uid(info[1])
        gid = self.get_gid(info[2])

        #current file stats
        st = os.stat(path)

#         logger.debug('%(path)s: uid %(target_uid)s/%(cur_uid)s, gid %(target_gid)s/%(cur_gid)s, mod %(target_mod)s/%(cur_mod)s'
#                      %{'path': path.decode(),
#                        'target_uid': uid,
#                        'cur_uid': st.st_uid,
#                        'target_gid': gid,
#                        'cur_gid': st.st_gid,
#                        'target_mod': info[0],
#                        'cur_mod': st.st_mode
#                        })

        if uid != -1 or gid != -1:
            ok = False
            if uid != st.st_uid:
                try:
                    os.chown( path, uid, gid )
                    ok = True
                except:
                    pass
                self.restore_callback( callback, ok, "chown %s %s : %s" % ( path.decode(errors = 'ignore'), uid, gid ) )

            #if restore uid/gid failed try to restore at least gid
            if not ok and gid != st.st_gid:
                try:
                    os.chown( path, -1, gid )
                    ok = True
                except:
                    pass
                self.restore_callback( callback, ok, "chgrp %s %s" % ( path.decode(errors = 'ignore'), gid ) )

        #restore perms
        ok = False
        if info[0] != st.st_mode:
            try:
                os.chmod( path, info[0] )
                ok = True
            except:
                pass
            self.restore_callback( callback, ok, "chmod %s %04o" % ( path.decode(errors = 'ignore'), info[0] ) )

    def restore( self, snapshot_id, paths, callback = None, restore_to = '', delete = False, backup = False, no_backup = False):
        instance = applicationinstance.ApplicationInstance( self.config.get_restore_instance_file(), False, flock = True)
        if instance.check():
            instance.start_application()
        else:
            logger.warning('Restore is already running', self)
            return

        if restore_to.endswith('/'):
            restore_to = restore_to[ : -1 ]

        if not isinstance(paths, (list, tuple)):
            paths = (paths, )

        #full rsync
        full_rsync = self.config.full_rsync()

        logger.info("Restore: %s to: %s"
                    %(', '.join(paths), restore_to),
                    self)

        info_file = configfile.ConfigFile()
        info_file.load( self.get_snapshot_info_path( snapshot_id ) )

        cmd_suffix = tools.get_rsync_prefix( self.config, not full_rsync, use_modes = ['ssh'] )
        cmd_suffix += '-R -v '
        if not full_rsync:
            # During the rsync operation, directories must be rwx by the current
            # user. Files should be r and x (if executable) by the current user.
            cmd_suffix += '--chmod=Du=rwx,Fu=rX,go= '
        if backup or self.config.is_backup_on_restore_enabled() and not no_backup:
            cmd_suffix += "--backup --suffix=%s " % self.backup_suffix()
        if delete:
            cmd_suffix += '--delete '
            cmd_suffix += '--filter="protect %s" ' % self.config.get_snapshots_path()
            cmd_suffix += '--filter="protect %s" ' % self.config._LOCAL_DATA_FOLDER
            cmd_suffix += '--filter="protect %s" ' % self.config._MOUNT_ROOT

        restored_paths = []
        for path in paths:
            tools.make_dirs(os.path.dirname(path))
            src_path = path
            src_delta = 0
            src_base = self.get_snapshot_path_to( snapshot_id, use_mode = ['ssh'] )
            cmd = cmd_suffix
            if restore_to:
                items = os.path.split(src_path)
                aux = items[0].lstrip(os.sep)
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
            self._execute( cmd, callback, filters = (self._filter_rsync_progress, ))
            self.restore_callback(callback, True, ' ')
            restored_paths.append((path, src_delta))
        try:
            os.remove(self.config.get_take_snapshot_progress_file())
        except Exception as e:
            logger.debug('Failed to remove snapshot progress file %s: %s'
                         %(self.config.get_take_snapshot_progress_file(), str(e)),
                         self)
            pass

        if full_rsync and not self.config.get_snapshots_mode() in ['ssh', 'ssh_encfs']:
            instance.exit_application()
            return

        #restore permissions
        logger.info('Restore permissions', self)
        self.restore_callback( callback, True, ' ' )
        self.restore_callback( callback, True, _("Restore permissions:") )
        file_info_dict = self.load_fileinfo_dict( snapshot_id, info_file.get_int_value( 'snapshot_version' ) )
        if file_info_dict:
            all_dirs = [] #restore dir permissions after all files are done
            for path, src_delta in restored_paths:
                #explore items
                snapshot_path_to = self.get_snapshot_path_to( snapshot_id, path ).rstrip( '/' )
                root_snapshot_path_to = self.get_snapshot_path_to( snapshot_id ).rstrip( '/' )
                #use bytes instead of string from here
                if isinstance(path, str):
                    path = path.encode()
                if isinstance(restore_to, str):
                    restore_to = restore_to.encode()

                if not restore_to:
                    path_items = path.strip(b'/').split(b'/')
                    curr_path = b'/'
                    for path_item in path_items:
                        curr_path = os.path.join( curr_path, path_item )
                        if curr_path not in all_dirs:
                            all_dirs.append( curr_path )
                else:
                    if path not in all_dirs:
                        all_dirs.append(path)

                if os.path.isdir( snapshot_path_to ) and not os.path.islink( snapshot_path_to ):
                    head = len(root_snapshot_path_to.encode())
                    for explore_path, dirs, files in os.walk( snapshot_path_to.encode() ):
                        for item in dirs:
                            item_path = os.path.join( explore_path, item )[head:]
                            if item_path not in all_dirs:
                                all_dirs.append( item_path )

                        for item in files:
                            item_path = os.path.join( explore_path, item )[head:]
                            real_path = restore_to + item_path[src_delta:]
                            self._restore_path_info( item_path, real_path, file_info_dict, callback )

            all_dirs.reverse()
            for item_path in all_dirs:
                real_path = restore_to + item_path[src_delta:]
                self._restore_path_info( item_path, real_path, file_info_dict, callback )

            self.restore_callback( callback, True, '')
            self.restore_callback( callback, True, _("Restore permissions:") + ' ' + _('Done') )

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
        except Exception as e:
            logger.debug('Failed to get snapshots list: %s'
                         %str(e),
                         self)
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
        except Exception as e:
            logger.debug('Failed to get snapshots list: %s'
                         %str(e),
                         self)
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
                except Exception as e:
                    logger.debug('Failed to get folder list for %s: %s'
                                 %(folder, str(e)),
                                 self)
                    pass

                for member in folderlist:
                    if len( member ) != 15 and len( member ) != 19:
                        continue
                    if os.path.isdir( os.path.join( folder, member,  'backup' ) ):
                        list_.append( member )

        list_.sort( reverse = sort_reverse )
        return list_

    def remove_snapshot( self, snapshot_id, execute = True, quote = '\"'):
        if len( snapshot_id ) <= 1:
            return
        path = self.get_snapshot_path( snapshot_id, use_mode = ['ssh', 'ssh_encfs'] )
        find = 'find %(quote)s%(path)s%(quote)s -type d -exec chmod u+wx %(quote)s{}%(quote)s %(suffix)s' \
               % {'path': path, 'quote': quote, 'suffix': self.config.find_suffix()}
        rm = 'rm -rf %(quote)s%(path)s%(quote)s' % {'path': path, 'quote': quote}
        if execute:
            self._execute(self.cmd_ssh(find, quote = True))
            self._execute(self.cmd_ssh(rm))
        else:
            return((find, rm))

    def copy_snapshot( self, snapshot_id, new_folder ):
        '''Copies a known snapshot to a new location'''
        current_path = self.get_snapshot_path( snapshot_id )
        #need to implement hardlinking to existing folder -> cp newest snapshot folder, rsync -aEAXHv --delete to this folder
        self._execute( "find \"%s\" -type d -exec chmod u+wx {} %s" % (current_path, self.config.find_suffix()) )
        cmd = "cp -dRl \"%s\"* \"%s\"" % ( current_path, new_folder )
        logger.info('%s is copied to folder %s'
                    %(snapshot_id, new_folder),
                    self)
        self._execute( cmd )
        self._execute( "find \"%s\" \"%s\" -type d -exec chmod u-w {} %s" % (current_path, new_folder, self.config.find_suffix() ) )

    def update_snapshots_location( self ):
        '''Updates to location: backintime/machine/user/profile_id'''
        if self.has_old_snapshots():
            logger.info('Snapshot location update flag detected', self)
            logger.warning('Snapshot location needs update', self)
            profiles = self.config.get_profiles()

            answer_change = self.config.question_handler( _('Back In Time changed its backup format.\n\nYour old snapshots can be moved according to this new format. OK?') )
            if answer_change == True:
                logger.info('Update snapshot locations', self)

                if len( profiles ) == 1:
                    logger.info('Only 1 profile found', self)
                    answer_same = True
                elif len( profiles ) > 1:
                    answer_same = self.config.question_handler( _('%s profiles found. \n\nThe new backup format supports storage of different users and profiles on the same location. Do you want the same location for both profiles? \n\n(The program will still be able to discriminate between them)') % len( profiles ) )
                else:
                    logger.warning('No profiles found!', self)
                    self.config.notify_error( _( 'No profiles are found. Will have to update to profiles first, please restart Back In Time' ) )
                    logger.info('Config version is %s'
                                %str(self.get_int_value('config.version', 1)),
                                self)

                    if self.config.get_int_value( 'config.version', 1 ) > 1:
                        self.config.set_int_value( 'config.version', 2 )
                        logger.info('Config version set to 2', self)
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
                        logger.info('Folder of profile %s is set to %s'
                                    %(profile_id, main_folder),
                                    self)
                    else:
                        self.config.set_snapshots_path( self.config.get_snapshots_path( profile_id ), profile_id )
                        logger.info('Folder of profile %s is set to %s'
                                    %(profile_id, main_folder),
                                    self)
                    new_folder = self.config.get_snapshots_full_path( profile_id )

                    output = tools.move_snapshots_folder( old_folder, new_folder )

                    snapshots_left = tools.get_snapshots_list_in_folder( old_folder )
                    if output == True:
                        success.append( True )
                        if not snapshots_left:
                            logger.info('Update was successful. Snapshots of profile %s are moved to their new location'
                                        %profile_id, self)
                        else:
                            logger.warning('Not all snapshots are removed from the original folder!', self)
                            logger.info('The following snapshots are still present: %s' %snapshots_left, self)
                            logger.info('You could move them manually or leave them where they are now', self)
                    else:
                        logger.warning('%s: are not moved to their new location!' %snapshots_left, self)

                        answer_unsuccessful = self.config.question_handler( _('%(snapshots_left)s\nof profile %(profile_id)s are not moved to their new location\nDo you want to proceed?\n(Back In Time will be able to continue taking snapshots, however the remaining snapshots will not be considered for automatic removal)\n\nIf not Back In Time will restore former settings for this profile, however cannot continue taking snapshots' %{ 'snapshots_left' : snapshots_left, 'profile_id' : profile_id } ) )
                        if answer_unsuccessful == True:
                            success.append( True )
                        else:
                            success.append( False )
                            # restore
                            logger.info('Restore former settings', self)
                            self.config.set_snapshots_path( old_snapshots_paths[counter], profile_id )
                            self.config.error_handler( _('Former settings of profile %s are restored.\nBack In Time cannot continue taking new snapshots.\n\nYou can manually move the snapshots, \nif you are done restart Back In Time to proceed' %profile_id ) )

                    counter = counter + 1

                overall_success = True
                for item in success:
                    if item == False:
                        overall_success = False
                if overall_success == True:
                    logger.info('Back In Time will be able to make new snapshots again!', self)
                    self.config.error_handler( _('Update was successful!\n\nBack In Time will continue taking snapshots again as scheduled' ) )

            elif answer_change == False:
                logger.info('Move refused by user', self)
                logger.warning('Old snapshots are not taken into account by smart-remove', self)
                answer_continue = self.config.question_handler( _('Are you sure you do not want to move your old snapshots?\n\n\nIf you do, you will not see these questions again next time, Back In Time will continue making snapshots again, but smart-remove cannot take your old snapshots into account any longer!\n\nIf you do not, you will be asked again next time you start Back In Time.') )
                if answer_continue == True:
                    for profile_id in profiles:
                        old_folder = self.config.get_snapshots_path( profile_id )
                        self.config.set_snapshots_path( old_folder, profile_id )
                        logger.info('Folder of profile %s is set to %s'
                                    %(profile_id, self.get_snapshots_path(profile_id)),
                                    self)

                    logger.info('Back In Time will be able to make new snapshots again!', self)
                    self.config.error_handler( _('Back In Time will continue taking snapshots again as scheduled' ) )
                else:
                    self.config.error_handler( _( 'Back In Time still cannot continue taking new snapshots.\nRestart Back In Time to see the questions again' ) )
            else:
                return False

    def has_old_snapshots( self ):
        ret = len( self.get_snapshots_list( False, None, 3 ) ) > 0
        logger.debug('Found old snapshots: %s' %ret, self)
        return ret

    def take_snapshot( self, force = False ):
        ret_val, ret_error = False, True
        sleep = True

        self.config.PLUGIN_MANAGER.load_plugins( self )

        if not self.config.is_configured():
            logger.warning('Not configured', self)
            self.config.PLUGIN_MANAGER.on_error( 1 ) #not configured
        elif not force and self.config.is_no_on_battery_enabled() and tools.on_battery():
            self.set_take_snapshot_message(0, _('Deferring backup while on battery'))
            logger.info('Deferring backup while on battery', self)
            logger.warning('Backup not performed', self)
        elif self.has_old_snapshots():
            logger.info('The application needs to change the backup format. '
                        'Start the GUI to proceed. (As long as you do not you '
                        'will not be able to make new snapshots!)', self)
            logger.warning('Backup not performed', self)
        elif not force and not self.config.is_backup_scheduled():
            logger.info('Profile "%s" is not scheduled to run now.' 
                        %self.config.get_profile_name(), self)
        else:
            instance = applicationinstance.ApplicationInstance( self.config.get_take_snapshot_instance_file(), False, flock = True)
            restore_instance = applicationinstance.ApplicationInstance( self.config.get_restore_instance_file(), False )
            if not instance.check():
                logger.warning('A backup is already running', self)
                self.config.PLUGIN_MANAGER.on_error( 2 ) #a backup is already running
            elif not restore_instance.check():
                logger.warning('Restore is still running. Stop backup until restore is done.', self)
            else:
                if self.config.is_no_on_battery_enabled () and not tools.power_status_available():
                    logger.warning('Backups disabled on battery but power status is not available', self)

                instance.start_application()
                self.flockExclusive()
                logger.info('Lock', self)

                now = datetime.datetime.today()

                #inhibit suspend/hibernate during snapshot is running
                self.config.inhibitCookie = tools.inhibitSuspend(toplevel_xid = self.config.xWindowId)

                #mount
                try:
                    hash_id = mount.Mount(cfg = self.config).mount()
                except MountException as ex:
                    logger.error(str(ex), self)
                    instance.exit_application()
                    logger.info('Unlock', self)
                    time.sleep(2)
                    return False
                else:
                    self.config.set_current_hash_id(hash_id)

                #include_folders, ignore_folders, dict = self._get_backup_folders( now, force )
                include_folders = self.config.get_include()

                if not include_folders:
                    logger.info('Nothing to do', self)
                elif not self.config.PLUGIN_MANAGER.on_process_begins():
                    logger.info('A plugin prevented the backup', self)
                else:
                    #take snapshot process begin
                    self.set_take_snapshot_message( 0, '...' )
                    self.new_take_snapshot_log( now )
                    profile_id = self.config.get_current_profile()
                    profile_name = self.config.get_profile_name()
                    logger.info("Take a new snapshot. Profile: %s %s"
                                %(profile_id, profile_name), self)

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
                        logger.warning('Can\'t find snapshots folder!', self)
                        self.config.PLUGIN_MANAGER.on_error( 3 ) #Can't find snapshots directory (is it on a removable drive ?)
                    else:
                        ret_error = False
                        snapshot_id = self.get_snapshot_id( now )
                        snapshot_path = self.get_snapshot_path( snapshot_id )

                        if os.path.exists( snapshot_path ):
                            logger.warning("Snapshot path \"%s\" already exists" %snapshot_path, self)
                            self.config.PLUGIN_MANAGER.on_error( 4, snapshot_id ) #This snapshots already exists
                        else:
                            ret_val, ret_error = self._take_snapshot( snapshot_id, now, include_folders )

                        if not ret_val:
                            self._execute( "rm -rf \"%s\"" % snapshot_path )

                            if ret_error:
                                logger.error('Failed to take snapshot !!!', self)
                                self.set_take_snapshot_message( 1, _('Failed to take snapshot %s !!!') % now.strftime( '%x %H:%M:%S' ) )
                                time.sleep(2)
                            else:
                                logger.warning("No new snapshot", self)
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
                except MountException as ex:
                    logger.error(str(ex), self)

                instance.exit_application()
                self.flockRelease()
                logger.info('Unlock', self)

        if sleep:
            time.sleep(2) #max 1 backup / second

        if not ret_error and not list(self.config.anacrontab_files()):
            tools.writeTimeStamp(self.config.get_anacron_spool_file())

        #release inhibit suspend
        if self.config.inhibitCookie:
            self.config.inhibitCookie = tools.unInhibitSuspend(*self.config.inhibitCookie)

        return ret_val

    def _filter_rsync_progress(self, line):
        m = self.reRsyncProgress.match(line)
        if m:
            if m.group(5).strip():
                return
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
            logger.error("Can't create folder: %s" % folder, self)
            self.set_take_snapshot_message( 1, _('Can\'t create folder: %s') % folder )
            time.sleep(2) #max 1 backup / second
            return False

        return True

    def _save_path_info( self, fileinfo, path ):
        assert isinstance(path, bytes), 'path is not bytes type: %s' % path
        if path and os.path.exists(path):
            info = os.stat(path)
            mode = str(info.st_mode).encode('utf-8', 'replace')
            user = self.get_user_name(info.st_uid).encode('utf-8', 'replace')
            group = self.get_group_name(info.st_gid).encode('utf-8', 'replace')
            fileinfo.write(b' '.join((mode, user, group, path)) + b'\n' )

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
                logger.error("Can't remove folder: %s" % new_snapshot_path(), self )
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
                    logger.info("Compare with old snapshot: %s" % prev_snapshot_id, self)

                    cmd  = rsync_prefix + ' -i --dry-run --out-format="BACKINTIME: %i %n%L"' + rsync_suffix
                    cmd += self.rsync_remote_path( prev_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']) )
                    params = [ prev_snapshot_path_to(), False ]
                    self.append_to_take_snapshot_log( '[I] ' + cmd, 3 )
                    self._execute( cmd, self._exec_rsync_compare_callback, params )
                    changed = params[1]

                    if not changed:
                        logger.info("Nothing changed, no back needed", self)
                        self.append_to_take_snapshot_log( '[I] Nothing changed, no back needed', 3 )
                        self.set_snapshot_last_check(prev_snapshot_id)
                        return [ False, False ]

            if not self._create_directory( new_snapshot_path_to() ):
                return [ False, True ]

            if not full_rsync:
                self.set_take_snapshot_message( 0, _('Create hard-links') )
                logger.info("Create hard-links", self)

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
        logger.info("Call rsync to take the snapshot", self)
        cmd = rsync_prefix + ' -v ' + rsync_suffix
        cmd += self.rsync_remote_path( new_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']) )

        self.set_take_snapshot_message( 0, _('Take snapshot') )

        if full_rsync:
            if prev_snapshot_id:
                link_dest = encode.path( os.path.join(prev_snapshot_id, 'backup') )
                link_dest = os.path.join('..', '..', link_dest)
                cmd = cmd + " --link-dest=\"%s\"" % link_dest

        if full_rsync or not check_for_changes:
            cmd = cmd + ' -i --out-format="BACKINTIME: %i %n%L"'

        params = [False, False]
        self.append_to_take_snapshot_log( '[I] ' + cmd, 3 )
        self._execute( cmd + ' 2>&1', self._exec_rsync_callback, params, filters = (self._filter_rsync_progress, ))
        try:
            os.remove(self.config.get_take_snapshot_progress_file())
        except Exception as e:
            logger.debug('Failed to remove snapshot progress file %s: %s'
                         %(self.config.get_take_snapshot_progress_file(), str(e)),
                         self)
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
            if not params[1] and not self.config.take_snapshot_regardless_of_changes():
                self._execute( self.cmd_ssh( 'find \"%s\" -type d -exec chmod u+wx \"{}\" %s' % (new_snapshot_path(use_mode = ['ssh', 'ssh_encfs']), find_suffix), quote = True) ) #Debian patch
                self._execute( self.cmd_ssh( "rm -rf \"%s\"" % new_snapshot_path(use_mode = ['ssh', 'ssh_encfs']) ) )

                logger.info("Nothing changed, no back needed", self)
                self.append_to_take_snapshot_log( '[I] Nothing changed, no back needed', 3 )
                self.set_snapshot_last_check(prev_snapshot_id)
                return [ False, False ]


        #backup config file
        logger.info('Save config file', self)
        self.set_take_snapshot_message( 0, _('Save config file ...') )
        self._execute( 'cp "%s" "%s"' % (self.config._LOCAL_CONFIG_PATH, new_snapshot_path_to() + '..') )

        if not full_rsync or self.config.get_snapshots_mode() in ['ssh', 'ssh_encfs']:
            #save permissions for sync folders
            logger.info('Save permissions', self)
            self.set_take_snapshot_message( 0, _('Save permission ...') )

            with bz2.BZ2File( self.get_snapshot_fileinfo_path( new_snapshot_id ), 'wb' ) as fileinfo:

                permission_done = False
                if self.config.get_snapshots_mode() in ['ssh', 'ssh_encfs']:
                    path_to_explore_ssh = new_snapshot_path_to(use_mode = ['ssh', 'ssh_encfs']).rstrip( '/' )
                    cmd = self.cmd_ssh(['find', path_to_explore_ssh, '-print'])

                    if self.config.get_snapshots_mode() == 'ssh_encfs':
                        decode = encfstools.Decode(self.config, False)
                        path_to_explore_ssh = decode.remote(path_to_explore_ssh.encode())
                    else:
                        decode = encfstools.Bounce()
                    head = len( path_to_explore_ssh )

                    find = subprocess.Popen(cmd, stdout = subprocess.PIPE,
                                            stderr = subprocess.PIPE)

                    for line in find.stdout:
                        if line:
                            self._save_path_info(fileinfo, decode.remote(line.rstrip(b'\n'))[head:])

                    output = find.communicate()[0]
                    if find.returncode:
                        self.set_take_snapshot_message(1, _('Save permission over ssh failed. Retry normal method'))
                    else:
                        for line in output.split(b'\n'):
                            if line:
                                self._save_path_info(fileinfo, decode.remote(line)[head:])
                        permission_done = True

                if not permission_done:
                    path_to_explore = self.get_snapshot_path_to( new_snapshot_id ).rstrip( '/' ).encode()
                    for path, dirs, files in os.walk( path_to_explore ):
                        dirs.extend( files )
                        for item in dirs:
                            item_path = os.path.join( path, item )[ len( path_to_explore ) : ]
                            self._save_path_info( fileinfo, item_path )

        #create info file
        logger.info("Create info file", self)
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
        except Exception as e:
            logger.debug('Failed to write take_snapshot log %s into compressed file %s: %s'
                         %(self.config.get_take_snapshot_log_file(), self.get_snapshot_log_path(new_snapshot_id), str(e)),
                         self)
            pass

        #rename snapshot
        os.system( self.cmd_ssh( "mv \"%s\" \"%s\"" % ( new_snapshot_path(use_mode = ['ssh', 'ssh_encfs']), snapshot_path(use_mode = ['ssh', 'ssh_encfs']) ) ) )

        if not os.path.exists( snapshot_path() ):
            logger.error("Can't rename %s to %s" % (new_snapshot_path(), snapshot_path()), self)
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

        logger.debug("Keep all >= %s and < %s" %(min_id, max_id), self)

        for snapshot_id in snapshots:
            if snapshot_id >= min_id and snapshot_id < max_id:
                if snapshot_id not in keep_snapshots:
                    keep_snapshots.append( snapshot_id )

        return keep_snapshots

    def _smart_remove_keep_first_( self, snapshots, keep_snapshots, min_date, max_date ):
        min_id = self.get_snapshot_id( min_date )
        max_id = self.get_snapshot_id( max_date )

        logger.debug("Keep first >= %s and < %s" %(min_id, max_id), self)

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
        logger.debug("Considered: %s" %snapshots, self)
        if len( snapshots ) <= 1:
            logger.debug("There is only one snapshots, so keep it", self)
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

        logger.debug("Keep snapshots: %s" %keep_snapshots, self)

        del_snapshots = []
        for snapshot_id in snapshots:
            if snapshot_id in keep_snapshots:
                continue

            if self.config.get_dont_remove_named_snapshots():
                if self.get_snapshot_name( snapshot_id ):
                    logger.debug("Keep snapshot: %s, it has a name" %snapshot_id, self)
                    continue

            del_snapshots.append(snapshot_id)

        if not del_snapshots:
            return

        if self.config.get_snapshots_mode() in ['ssh', 'ssh_encfs'] and self.config.get_smart_remove_run_remote_in_background():
            logger.info('[smart remove] remove snapshots in background: %s'
                        %del_snapshots, self)
            lckFile = os.path.normpath(os.path.join(self.get_snapshot_path(del_snapshots[0], ['ssh', 'ssh_encfs']), os.pardir, 'smartremove.lck'))

            maxLength = self.config.ssh_max_arg_length()
            if not maxLength:
                import sshMaxArg
                user_host = '%s@%s' %(self.config.get_ssh_user(), self.config.get_ssh_host())
                maxLength = sshMaxArg.test_ssh_max_arg(user_host)
                self.config.set_ssh_max_arg_length(maxLength)
                self.config.save()
                sshMaxArg.reportResult(user_host, maxLength)

            additionalChars = len(self.config.ssh_prefix_cmd(cmd_type = str))

            head = 'screen -d -m bash -c "('
            if logger.DEBUG:
                head += 'logger -t \\\"backintime smart-remove [$BASHPID]\\\" \\\"start\\\"; '
            head += 'flock -x 9; '
            if logger.DEBUG:
                head += 'logger -t \\\"backintime smart-remove [$BASHPID]\\\" \\\"got exclusive flock\\\"; '

            tail = ') 9>\\\"%s\\\""' %lckFile

            cmds = []
            for sid in del_snapshots:
                find, rm = self.remove_snapshot(sid, execute = False, quote = '\\\"')
                s = 'test -e \\\"%s\\\" && (' %self.get_snapshot_path(sid, use_mode = ['ssh', 'ssh_encfs'])
                if logger.DEBUG:
                    s += 'logger -t \\\"backintime smart-remove [$BASHPID]\\\" '
                    s += '\\\"snapshot %s still exist\\\"; ' %sid
                    s += 'sleep 1; ' #add one second delay because otherwise you might not see serialized process with small snapshots
                s += '%s; ' %find
                if logger.DEBUG:
                    s += 'logger -t \\\"backintime smart-remove [$BASHPID]\\\" '
                    s += '\\\"snapshot %s change permission done\\\"; ' %sid
                s += '%s; ' %rm
                if logger.DEBUG:
                    s += 'logger -t \\\"backintime smart-remove [$BASHPID]\\\" '
                    s += '\\\"snapshot %s remove done\\\"' %sid
                s += '); '
                cmds.append(s)

            for cmd in tools.splitCommands(cmds,
                                           head = head,
                                           tail = tail,
                                           maxLength = maxLength,
                                           additionalChars = additionalChars):
                self._execute(self.cmd_ssh(cmd, quote = True))
        else:
            logger.info("[smart remove] remove snapshots: %s"
                        %del_snapshots, self)
            for i, snapshot_id in enumerate(del_snapshots, 1):
                self.set_take_snapshot_message( 0, _('Smart remove') + ' %s/%s' %(i, len(del_snapshots)) )
                self.remove_snapshot( snapshot_id )

    def _free_space( self, now ):
        snapshots = self.get_snapshots_list( False )
        last_snapshot = snapshots[-1]

        #remove old backups
        if self.config.is_remove_old_snapshots_enabled():
            self.set_take_snapshot_message( 0, _('Remove old snapshots') )

            old_backup_id = self.get_snapshot_id( self.config.get_remove_old_snapshots_date() )
            logger.info("Remove backups older than: %s"
                        %old_backup_id[0:15], self)

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

            logger.info("Keep min free disk space: %s Mb"
                        %min_free_space, self)

            snapshots = self.get_snapshots_list( False )

            while True:
                if len( snapshots ) <= 1:
                    break

                free_space = self._stat_free_space_local(self.config.get_snapshots_path())

                if free_space is None:
                    free_space = self._stat_free_space_ssh()

                if free_space is None:
                    logger.warning('Failed to get free space. Skipping', self)
                    break

                if free_space >= min_free_space:
                    break

                if self.config.get_dont_remove_named_snapshots():
                    if self.get_snapshot_name( snapshots[0] ):
                        del snapshots[0]
                        continue

                logger.info("free disk space: %s Mb" %free_space, self)
                self.remove_snapshot( snapshots[0] )
                del snapshots[0]

        #try to keep free inodes
        if self.config.min_free_inodes_enabled():
            min_free_inodes = self.config.min_free_inodes()
            self.set_take_snapshot_message( 0, _('Try to keep min %d%% free inodes') % min_free_inodes )
            logger.info("Keep min %d%% free inodes" %min_free_inodes, self)

            snapshots = self.get_snapshots_list( False )

            while True:
                if len( snapshots ) <= 1:
                    break

                try:
                    info = os.statvfs( self.config.get_snapshots_path() )
                    free_inodes = info.f_favail
                    max_inodes  = info.f_files
                except Exception as e:
                    logger.debug('Failed to get free inodes for snapshot path %s: %s'
                                 %(self.config.get_snapshots_path(), str(e)),
                                 self)
                    break

                if free_inodes >= max_inodes * (min_free_inodes / 100.0):
                    break

                if self.config.get_dont_remove_named_snapshots():
                    if self.get_snapshot_name( snapshots[0] ):
                        del snapshots[0]
                        continue

                logger.info("free inodes: %.2f%%"
                            %(100.0 / max_inodes * free_inodes),
                            self)
                self.remove_snapshot( snapshots[0] )
                del snapshots[0]

        #set correct last snapshot again
        if last_snapshot is not snapshots[-1]:
            self.create_last_snapshot_symlink(snapshots[-1])

    def _stat_free_space_local(self, path):
        try:
            info = os.statvfs(path)
            if info.f_blocks != info.f_bavail:
                return info.f_frsize * info.f_bavail // ( 1024 * 1024 )
        except Exception as e:
            logger.debug('Failed to get free space for %s: %s'
                         %(path, str(e)),
                         self)
            pass
        logger.warning('Failed to stat snapshot path', self)

    def _stat_free_space_ssh(self):
        if self.config.get_snapshots_mode() not in ('ssh', 'ssh_encfs'):
            return None

        snapshots_path_ssh = self.config.get_snapshots_path_ssh()
        if not len(snapshots_path_ssh):
            snapshots_path_ssh = './'
        cmd = self.cmd_ssh(['df', snapshots_path_ssh])
        
        df = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        output = df.communicate()[0]
        #Filesystem     1K-blocks      Used Available Use% Mounted on
        #/tmp           127266564 115596412   5182296  96% /
        #                                     ^^^^^^^
        for line in output.split(b'\n'):
            m = re.match(b'^.*?\s+\d+\s+\d+\s+(\d+)\s+\d+%', line, re.M)
            if m:
                return int(m.group(1)) / 1024
        logger.warning('Failed to get free space on remote', self)

    def _execute( self, cmd, callback = None, user_data = None, filters = () ):
        logger.debug("Call command \"%s\"" %cmd, self, 1)
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
                for f in filters:
                    line = f(line)
                if not line:
                    continue
                callback(line , user_data )

            ret_val = pipe.close()
            if ret_val is None:
                ret_val = 0

        if ret_val != 0:
            logger.warning("Command \"%s\" returns %s%s%s"
                           %(cmd, bcolors.WARNING, ret_val, bcolors.ENDC),
                           self, 1)
        else:
            logger.debug("Command \"%s...\" returns %s"
                         %(cmd[:min(16, len(cmd))], ret_val),
                         self, 1)

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
            ssh_private_key = self.config.get_ssh_private_key_file()

            if isinstance(cmd, str):
                if ssh_cipher == 'default':
                    ssh_cipher_suffix = ''
                else:
                    ssh_cipher_suffix = '-c %s' % ssh_cipher
                ssh_private_key = "-o IdentityFile=%s" % ssh_private_key

                if self.config.is_run_ionice_on_remote_enabled():
                    cmd = 'ionice -c2 -n7 ' + cmd

                if self.config.is_run_nice_on_remote_enabled():
                    cmd = 'nice -n 19 ' + cmd

                cmd = self.config.ssh_prefix_cmd(cmd_type = str) + cmd

                if quote:
                    cmd = '\'%s\'' % cmd

                return 'ssh -p %s -o ServerAliveInterval=240 %s %s %s@%s %s' \
                        % ( str(ssh_port), ssh_cipher_suffix, ssh_private_key,\
                        ssh_user, ssh_host, cmd )

            if isinstance(cmd, tuple):
                cmd = list(cmd)

            if isinstance(cmd, list):
                suffix = ['ssh', '-p', str(ssh_port)]
                suffix += ['-o', 'ServerAliveInterval=240']
                if not ssh_cipher == 'default':
                    suffix += ['-c', ssh_cipher]
                suffix += ['-o', 'IdentityFile=%s' % ssh_private_key]
                suffix += ['%s@%s' % (ssh_user, ssh_host)]

                if self.config.is_run_ionice_on_remote_enabled():
                    cmd = ['ionice', '-c2', '-n7'] + cmd

                if self.config.is_run_nice_on_remote_enabled():
                    cmd = ['nice', '-n 19'] + cmd

                cmd = self.config.ssh_prefix_cmd(cmd_type = list) + cmd

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
            dirname = os.path.dirname(path)
            if not os.access(dirname, os.W_OK):
                st = os.stat(dirname)
                os.chmod(dirname, st.st_mode | stat.S_IWUSR)
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
                logger.error('Could not remove symlink %s' %symlink, self)
                return False
            logger.debug('Create symlink %s => %s' %(symlink, snapshot_id), self)
            os.symlink(snapshot_id, symlink)
        except Exception as e:
            logger.error('Failed to create symlink %s: %s' %(symlink, str(e)), self)
            return False

    def flockExclusive(self):
        """block take_snapshots from other profiles or users
        and run them serialized
        """
        if self.config.use_global_flock():
            logger.debug('Set flock %s' %self.GLOBAL_FLOCK, self)
            self.flock_file = open(self.GLOBAL_FLOCK, 'w')
            fcntl.flock(self.flock_file, fcntl.LOCK_EX)
            #make it rw by all if that's not already done.
            perms = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | \
                    stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
            s = os.fstat(self.flock_file.fileno())
            if not s.st_mode & perms == perms:
                logger.debug('Set flock permissions %s' %self.GLOBAL_FLOCK, self)
                os.fchmod(self.flock_file.fileno(), perms)

    def flockRelease(self):
        """release lock so other snapshots can continue
        """
        if self.flock_file:
            logger.debug('Release flock %s' %self.GLOBAL_FLOCK, self)
            fcntl.fcntl(self.flock_file, fcntl.LOCK_UN)
            self.flock_file.close()
        self.flock_file = None

if __name__ == "__main__":
    config = config.Config()
    snapshots = Snapshots( config )
    snapshots.take_snapshot()
