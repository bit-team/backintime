#	Back In Time
#	Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze, Taylor Raack
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


import json
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
from tempfile import TemporaryDirectory

import config
import configfile
import logger
import applicationinstance
import tools
import encfstools
import mount
import progress
import bcolors
import snapshotlog
from exceptions import MountException, LastSnapshotSymlink

_=gettext.gettext


class Snapshots:
    """
    Collection of take-snapshot and restore commands.

    Args:
        cfg (config.Config): current config
    """
    SNAPSHOT_VERSION = 3
    GLOBAL_FLOCK = '/tmp/backintime.lock'

    def __init__( self, cfg = None ):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()
        self.snapshotLog = snapshotlog.SnapshotLog(self.config)

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
        self.restore_permission_failed = False

    #TODO: make own class for takeSnapshotMessage
    def clear_take_snapshot_message( self ):
        files = (self.config.get_take_snapshot_message_file(), \
                 self.config.get_take_snapshot_progress_file() )
        for f in files:
            if os.path.exists(f):
                os.remove(f)

    #TODO: make own class for takeSnapshotMessage
    def get_take_snapshot_message( self ):
        wait = datetime.datetime.now() - datetime.timedelta(seconds = 30)
        if self.last_check_snapshot_runnig < wait:
            self.last_check_snapshot_runnig = datetime.datetime.now()
            if not self.is_busy():
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

        del items[0]
        message = '\n'.join( items )

        return( mid, message )

    #TODO: make own class for takeSnapshotMessage
    def set_take_snapshot_message( self, type_id, message, timeout = -1 ):
        data = str(type_id) + '\n' + message

        try:
            with open( self.config.get_take_snapshot_message_file(), 'wt' ) as f:
                f.write( data )
        except Exception as e:
            logger.debug('Failed to set take_snapshot message to %s: %s'
                         %(self.config.get_take_snapshot_message_file(), str(e)),
                         self)

        if 1 == type_id:
            self.snapshotLog.append('[E] ' + message, 1)
        else:
            self.snapshotLog.append('[I] '  + message, 3)

        try:
            profile_id =self.config.get_current_profile()
            profile_name = self.config.get_profile_name( profile_id )
            self.config.PLUGIN_MANAGER.on_message( profile_id, profile_name, type_id, message, timeout )
        except Exception as e:
            logger.debug('Failed to send message to plugins: %s'
                         %str(e),
                         self)

    def is_busy( self ):
        instance = applicationinstance.ApplicationInstance( self.config.get_take_snapshot_instance_file(), False )
        return not instance.check()

    def clear_uid_gid_names_cache(self):
        """
        Reset the cache for user and group names.
        """
        self.user_cache = {}
        self.group_cache = {}

    def clear_uid_gid_cache(self):
        """
        Reset the cache for UIDs and GIDs.
        """
        self.uid_cache = {}
        self.gid_cache = {}

    def get_uid(self, name, callback = None, backup = None):
        """
        Get the User identifier (UID) for the user in ``name``.
        name->uid will be cached to speed up subsequent requests.

        Args:
            name (:py:class:`str`, :py:class:`bytes`):
                                username to search for
            callback (method):  callable which will handle a given message
            backup (int):       UID wich will be used if the username is unknown
                                on this machine

        Returns:
            int:                UID of the user in name or -1 if not found
        """
        if isinstance(name, bytes):
            name = name.decode()

        if name in self.uid_cache:
            return self.uid_cache[name]
        else:
            uid = -1
            try:
                uid = pwd.getpwnam(name).pw_uid
            except Exception as e:
                if backup:
                    uid = backup
                    msg = "UID for '%s' is not available on this system. Using UID %s from snapshot." %(name, backup)
                    logger.info(msg, self)
                    if callback is not None:
                        callback(msg)
                else:
                    self.restore_permission_failed = True
                    msg = 'Failed to get UID for %s: %s' %(name, str(e))
                    logger.error(msg, self)
                    if callback:
                        callback(msg)

            self.uid_cache[name] = uid
            return uid

    def get_gid(self, name, callback = None, backup = None):
        """
        Get the Group identifier (GID) for the group in ``name``.
        name->gid will be cached to speed up subsequent requests.

        Args:
            name (:py:class:`str`, :py:class:`bytes`):
                                groupname to search for
            callback (method):  callable which will handle a given message
            backup (int):       GID wich will be used if the groupname is unknown
                                on this machine

        Returns:
            int:                GID of the group in name or -1 if not found
        """
        if isinstance(name, bytes):
            name = name.decode()

        if name in self.gid_cache:
            return self.gid_cache[name]
        else:
            gid = -1
            try:
                gid = grp.getgrnam(name).gr_gid
            except Exception as e:
                if backup is not None:
                    gid = backup
                    msg = "GID for '%s' is not available on this system. Using GID %s from snapshot." %(name, backup)
                    logger.info(msg, self)
                    if callback:
                        callback(msg)
                else:
                    self.restore_permission_failed = True
                    msg = 'Failed to get GID for %s: %s' %(name, str(e))
                    logger.error(msg, self)
                    if callback:
                        callback(msg)

            self.gid_cache[name] = gid
            return gid

    def get_user_name( self, uid ):
        """
        Get the username for the given uid.
        uid->name will be cached to speed up subsequent requests.

        Args:
            uid (int):  User identifier (UID) to search for

        Returns:
            str:        name of the user with UID uid or '-' if not found
        """
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

            self.user_cache[uid] = name
            return name

    def get_group_name( self, gid ):
        """
        Get the groupname for the given gid.
        gid->name will be cached to speed up subsequent requests.

        Args:
            gid (int):  Group identifier (GID) to search for

        Returns:
            str:        name of the Group with GID gid or '.' if not found
        """
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

            self.group_cache[gid] = name
            return name

    def restore_callback( self, callback, ok, msg ):
        """
        Format messages thrown by restore depending on whether they where
        successful or failed.

        Args:
            callback (method):  callable instance which will handle the message
            ok (bool):          ``True`` if the logged action was successful
                                or ``False`` if it failed
            msg (str):          message that should be send to callback
        """
        if not callback is None:
            if not ok:
                msg = msg + " : " + _("FAILED")
                self.restore_permission_failed = True
            callback( msg )

    def _restore_path_info( self, key_path, path, fileInfoDict, callback = None ):
        """
        Restore permissions (owner, group and mode). If permissions are
        already identical with the new ones just skip. Otherwise try to
        'chown' to new owner and new group. If that fails (most probably because
        we are not running as root and normal user has no rights to change
        ownership of files) try to at least 'chgrp' to the new group. Finally
        'chmod' the new mode.

        Args:
            key_path (bytes):       original path during backup.
                                    Same as in fileInfoDict.
            path (bytes):           current path of file that should be changed.
            fileInfoDict (FileInfoDict):    FileInfoDict
        """
        assert isinstance(key_path, bytes), 'key_path is not bytes type: %s' % key_path
        assert isinstance(path, bytes), 'path is not bytes type: %s' % path
        assert isinstance(fileInfoDict, FileInfoDict), 'fileInfoDict is not FileInfoDict type: %s' % fileInfoDict
        if key_path not in fileInfoDict or not os.path.exists(path):
            return
        info = fileInfoDict[key_path]

        #restore uid/gid
        uid = self.get_uid(info[1], callback)
        gid = self.get_gid(info[2], callback)

        #current file stats
        st = os.stat(path)

        # logger.debug('%(path)s: uid %(target_uid)s/%(cur_uid)s, gid %(target_gid)s/%(cur_gid)s, mod %(target_mod)s/%(cur_mod)s'
        #              %{'path': path.decode(),
        #                'target_uid': uid,
        #                'cur_uid': st.st_uid,
        #                'target_gid': gid,
        #                'cur_gid': st.st_gid,
        #                'target_mod': info[0],
        #                'cur_mod': st.st_mode
        #                })

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

    def restore(self,
                sid,
                paths,
                callback = None,
                restore_to = '',
                delete = False,
                backup = True,
                only_new = False):
        """
        Restore one or more files from snapshot ``sid`` to either original
        or a different destination. Restore is done with rsync. If available
        permissions will be restored from ``fileinfo.bz2``.

        Args:
            sid (SID):                  snapshot from whom to restore
            paths (:py:class:`list`, :py:class:`tuple` or :py:class:`str`):
                                        single path (str) or multiple
                                        paths (list, tuple) that should be
                                        restored. For every path this will run
                                        a new rsync process. Permissions will be
                                        restored for all paths in one run
            callback (method):          callable instance which will handle
                                        messages
            restore_to (str):           full path to restore to. If empty
                                        restore to original destiantion
            delete (bool):              delete newer files which are not in the
                                        snapshot
            backup (bool):              create backup files (\*.backup.YYYYMMDD)
                                        before changing or deleting local files.
            only_new (bool):            Only restore files which does not exist
                                        or are newer than those in destination.
                                        Using "rsync --update" option.
        """
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

        logger.info("Restore: %s to: %s"
                    %(', '.join(paths), restore_to),
                    self)

        info = sid.info

        cmd_prefix = tools.get_rsync_prefix(self.config, no_perms = False, use_mode = ['ssh'])
        cmd_prefix.extend(('-R', '-v'))
        if backup:
            cmd_prefix.extend(('--backup', '--suffix=%s' %self.backup_suffix()))
        if delete:
            cmd_prefix.append('--delete')
            cmd_prefix.append('--filter="protect %s"' % self.config.get_snapshots_path())
            cmd_prefix.append('--filter="protect %s"' % self.config._LOCAL_DATA_FOLDER)
            cmd_prefix.append('--filter="protect %s"' % self.config._MOUNT_ROOT)
        if only_new:
            cmd_prefix.append('--update')

        restored_paths = []
        for path in paths:
            tools.make_dirs(os.path.dirname(path))
            src_path = path
            src_delta = 0
            src_base = sid.pathBackup(use_mode = ['ssh'])
            if not src_base.endswith(os.sep):
                src_base += os.sep
            cmd = cmd_prefix[:]
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

            cmd.append(self.rsync_remote_path('%s.%s' %(src_base, src_path), use_mode = ['ssh']))
            cmd.append('%s/' %restore_to)
            proc = tools.Execute(cmd,
                                 callback = callback,
                                 filters = (self._filter_rsync_progress,),
                                 parent = self)
            self.restore_callback(callback, True, proc.printable_cmd)
            proc.run()
            self.restore_callback(callback, True, ' ')
            restored_paths.append((path, src_delta))
        try:
            os.remove(self.config.get_take_snapshot_progress_file())
        except Exception as e:
            logger.debug('Failed to remove snapshot progress file %s: %s'
                         %(self.config.get_take_snapshot_progress_file(), str(e)),
                         self)

        #restore permissions
        logger.info('Restore permissions', self)
        self.restore_callback( callback, True, ' ' )
        self.restore_callback( callback, True, _("Restore permissions:") )
        self.restore_permission_failed = False
        fileInfoDict = sid.fileInfo

        #cache uids/gids
        for uid, name in info.get_list_value('user', ('int:uid', 'str:name')):
            self.get_uid(name.encode(), callback = callback, backup = uid)
        for gid, name in info.get_list_value('group', ('int:gid', 'str:name')):
            self.get_gid(name.encode(), callback = callback, backup = gid)

        if fileInfoDict:
            all_dirs = [] #restore dir permissions after all files are done
            for path, src_delta in restored_paths:
                #explore items
                snapshot_path_to = sid.pathBackup(path).rstrip( '/' )
                root_snapshot_path_to = sid.pathBackup().rstrip( '/' )
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
                            self._restore_path_info( item_path, real_path, fileInfoDict, callback )

            all_dirs.reverse()
            for item_path in all_dirs:
                real_path = restore_to + item_path[src_delta:]
                self._restore_path_info( item_path, real_path, fileInfoDict, callback )

            self.restore_callback( callback, True, '')
            if self.restore_permission_failed:
                status = _('FAILED')
            else:
                status = _('Done')
            self.restore_callback( callback, True, _("Restore permissions:") + ' ' + status )

        instance.exit_application()

    def backup_suffix(self):
        """
        Get suffix for backup files.

        Returns:
            str:    backup suffix in form of '.backup.YYYYMMDD'
        """
        return '.backup.' + datetime.date.today().strftime( '%Y%m%d' )

    def remove_snapshot(self, sid):
        """
        Remove snapshot ``sid``.

        Args:
            sid (SID):              snapshot to remove
        """
        if isinstance(sid, RootSnapshot):
            return
        rsync = tools.get_rsync_remove(self.config)
        with TemporaryDirectory() as d:
            rsync.append(d + os.sep)
            rsync.append(self.rsync_remote_path(sid.path(use_mode = ['ssh', 'ssh_encfs'])))
            tools.Execute(rsync).run()
            os.rmdir(sid.path())

    def take_snapshot( self, force = False ):
        """
        Wrapper for :py:func:`_take_snapshot` which will prepair and clean up
        things for the main :py:func:`_take_snapshot` method. This will check
        that no other snapshots are running at the same time, there is nothing
        prohibing a new snapshot (e.g. on battery) and the profile is configured
        correctly. This will also mount and unmount remote destinations.

        Args:
            force (bool):   force taking a new snapshot even if the profile is
                            not scheduled or the machine is running on battery

        Returns:
            bool:           ``True`` if successful created a new snapshot
        """
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

                include_folders = self.config.get_include()

                if not include_folders:
                    logger.info('Nothing to do', self)
                elif not self.config.PLUGIN_MANAGER.on_process_begins():
                    logger.info('A plugin prevented the backup', self)
                else:
                    #take snapshot process begin
                    self.set_take_snapshot_message( 0, '...' )
                    self.snapshotLog.new(now)
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
                        sid = SID(now, self.config)

                        if sid.exists():
                            logger.warning("Snapshot path \"%s\" already exists" %sid.path(), self)
                            self.config.PLUGIN_MANAGER.on_error( 4, sid ) #This snapshots already exists
                        else:
                            ret_val, ret_error = self._take_snapshot( sid, now, include_folders )

                        if not ret_val:
                            self.remove_snapshot(sid)

                            if ret_error:
                                logger.error('Failed to take snapshot !!!', self)
                                self.set_take_snapshot_message( 1, _('Failed to take snapshot %s !!!') % sid.displayID )
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
                        self.config.PLUGIN_MANAGER.on_new_snapshot( sid, sid.path() ) #new snapshot

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
        """
        Filter rsync's stdout for progress informations and store them in
        '~/.local/share/backintime/worker<N>.progress' file.

        Args:
            line (str): stdout line from rsync

        Returns:
            str:        ``line`` if it had no progress infos. ``None`` if
                        ``line`` was a progress
        """
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
        """
        Parse rsync's stdout, send it to take_snapshot_message and
        take_snapshot_log. Also check if there has been changes or errors in
        current rsync.

        Args:
            line (str):     stdout line from rsync
            params (list):  list of two bool '[error, changes]'. Using siteefect
                            on changing list items will change original
                            list, too. If rsync reported an error ``params[0]``
                            will be set to ``True``. If rsync reported a changed
                            file ``params[1]`` will be set to ``True``
        """
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
                    self.snapshotLog.append('[C] ' + line[12:], 2)

    def make_dirs(self, path):
        """
        Wrapper for :py:func:`tools.make_dirs()`. Create directories ``path``
        recursive and return success. If not successful send error-message to
        log.

        Args:
            path (str): fullpath to directories that should be created

        Returns:
            bool:       ``True`` if successful
        """
        if not tools.make_dirs(path):
            logger.error("Can't create folder: %s" % path, self)
            self.set_take_snapshot_message(1, _('Can\'t create folder: %s') % path)
            time.sleep(2) #max 1 backup / second
            return False
        return True

    def save_config_file(self, sid):
        """
        Backup the config file to the snapshot.

        Args:
            sid (SID):  snapshot in which the config should be stored
        """
        logger.info('Save config file', self)
        self.set_take_snapshot_message( 0, _('Saving config file...') )
        with open(self.config._LOCAL_CONFIG_PATH, 'rb') as src:
            with open(sid.path('config'), 'wb') as dst:
                dst.write(src.read())

    def save_snapshot_info(self, sid):
        """
        Save infos about the snapshot into the 'info' file.

        Args:
            sid (SID):  snapshot that should get an info file
        """
        logger.info("Create info file", self)
        machine = self.config.get_host()
        user = self.config.get_user()
        profile_id = self.config.get_current_profile()
        i = configfile.ConfigFile()
        i.set_int_value('snapshot_version', self.SNAPSHOT_VERSION)
        i.set_str_value('snapshot_date', sid.withoutTag)
        i.set_str_value('snapshot_machine', machine)
        i.set_str_value('snapshot_user', user)
        i.set_int_value('snapshot_profile_id', profile_id)
        i.set_int_value('snapshot_tag', sid.tag)
        i.set_list_value('user', ('int:uid', 'str:name'), list(self.user_cache.items()))
        i.set_list_value('group', ('int:gid', 'str:name'), list(self.group_cache.items()))
        i.set_str_value('filesystem_mounts', json.dumps(tools.get_filesystem_mount_info()))
        sid.info = i

    def save_permissions(self, sid):
        """
        Save permissions (owner, group, read-, write- and executable)
        for all files in Snapshot ``sid`` into snapshots fileInfoDict.

        Args:
            sid (SID):  snapshot that should be scanned
        """
        logger.info('Save permissions', self)
        self.set_take_snapshot_message(0, _('Saving permissions...'))

        permission_done = False
        fileInfoDict = FileInfoDict()
        #use a different method for ssh profiles which is a lot faster
        if self.config.get_snapshots_mode() in ['ssh', 'ssh_encfs']:
            path_to_explore_ssh = sid.pathBackup(use_mode = ['ssh', 'ssh_encfs']).rstrip( '/' )
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
                    self._save_path_info(fileInfoDict, decode.remote(line.rstrip(b'\n'))[head:])

            output = find.communicate()[0]
            if find.returncode:
                self.set_take_snapshot_message(1, _('Save permission over ssh failed. Retry normal method'))
            else:
                for line in output.split(b'\n'):
                    if line:
                        self._save_path_info(fileInfoDict, decode.remote(line)[head:])
                permission_done = True

        #normal method for non ssh profiles or if the method above failed
        if not permission_done:
            path_to_explore = sid.pathBackup().rstrip('/').encode()
            head = len(path_to_explore)
            for path, dirs, files in os.walk( path_to_explore ):
                dirs.extend( files )
                for item in dirs:
                    item_path = os.path.join(path, item)[head:]
                    self._save_path_info(fileInfoDict, item_path)

        sid.fileInfo = fileInfoDict

    def _save_path_info(self, fileinfo, path):
        """
        Collect permission infos about ``path`` and store them into
        ``fileinfo``.

        Args:
            fileinfo (FileInfoDict):
                            dict of: {path: (permission, user, group)}
                            Using sideefect on changing dict item will change
                            original dict, too.
            path (bytes):   full path to file or folder
        """
        assert isinstance(path, bytes), 'path is not bytes type: %s' % path
        if path and os.path.exists(path):
            info = os.stat(path)
            mode = info.st_mode
            user = self.get_user_name(info.st_uid).encode('utf-8', 'replace')
            group = self.get_group_name(info.st_gid).encode('utf-8', 'replace')
            fileinfo[path] = (mode, user, group)

    def _take_snapshot(self, sid, now, include_folders):
        """
        This is the main backup routine. It will take a new snapshot and store
        permissions of included files and folders into ``fileinfo.bz2``.

        Args:
            sid (SID):                  snapshot ID which the new snapshot
                                        should get
            now (datetime.datetime):    date and time when this snapshot was
                                        started
            include_folders (list):     folders to include. list of
                                        tuples (item, int) where ``int`` is 0
                                        if ``item`` is a folder or 1 if ``item``
                                        is a file

        Returns:
            list:                       list of two bool
                                        (``ret_val``, ``ret_error``)
                                        where ``ret_val`` is ``True`` if a new
                                        snapshot has been created and
                                        ``ret_error`` is ``True`` if there was
                                        an error during taking the snapshot
        """
        self.set_take_snapshot_message( 0, _('...') )

        new_snapshot = NewSnapshot(self.config)
        encode = self.config.ENCODE

        if new_snapshot.exists() and new_snapshot.saveToContinue:
            logger.info("Found leftover '%s' which can be continued." %new_snapshot.displayID, self)
            self.set_take_snapshot_message(0, _("Found leftover '%s' which can be continued.") %new_snapshot.displayID)
            #fix permissions
            for file in os.listdir(new_snapshot.path()):
                file = os.path.join(new_snapshot.path(), file)
                mode = os.stat(file).st_mode
                os.chmod(file, mode | stat.S_IWUSR)
        elif new_snapshot.exists() and not new_snapshot.saveToContinue:
            logger.info("Remove leftover '%s' folder from last run" %new_snapshot.displayID)
            self.set_take_snapshot_message(0, _("Removing leftover '%s' folder from last run") %new_snapshot.displayID)
            self.remove_snapshot(new_snapshot)

            if os.path.exists(new_snapshot.path()):
                logger.error("Can't remove folder: %s" % new_snapshot.path(), self)
                self.set_take_snapshot_message( 1, _('Can\'t remove folder: %s') % new_snapshot.path())
                time.sleep(2) #max 1 backup / second
                return [ False, True ]

        if not new_snapshot.saveToContinue and not new_snapshot.makeDirs():
            return [ False, True ]

        prev_sid = None
        snapshots = listSnapshots(self.config)
        if snapshots:
            prev_sid = snapshots[0]

        #rsync prefix & suffix
        rsync_prefix = tools.get_rsync_prefix(self.config, no_perms = False)
        if self.config.exclude_by_size_enabled():
            rsync_prefix.append('--max-size=%sM' %self.config.exclude_by_size())
        rsync_suffix = self.rsyncSuffix(include_folders)

        # When there is no snapshots it takes the last snapshot from the other folders
        # It should delete the excluded folders then
        rsync_prefix.extend(('--delete', '--delete-excluded'))
        rsync_prefix.append('-v')
        rsync_prefix.extend(('-i', '--out-format=BACKINTIME: %i %n%L'))
        if prev_sid:
            link_dest = encode.path(os.path.join(prev_sid.sid, 'backup'))
            link_dest = os.path.join(os.pardir, os.pardir, link_dest)
            rsync_prefix.append('--link-dest=%s' %link_dest)

        #sync changed folders
        logger.info("Call rsync to take the snapshot", self)
        new_snapshot.saveToContinue = True
        cmd = rsync_prefix + rsync_suffix
        cmd.append(self.rsync_remote_path(new_snapshot.pathBackup(use_mode = ['ssh', 'ssh_encfs'])))

        self.set_take_snapshot_message(0, _('Taking snapshot'))

        #run rsync
        params = [False, False]
        proc = tools.Execute(cmd,
                             callback = self._exec_rsync_callback,
                             user_data = params,
                             filters = (self._filter_rsync_progress,),
                             parent = self)
        self.snapshotLog.append('[I] ' + proc.printable_cmd, 3)
        proc.run()

        #cleanup
        try:
            os.remove(self.config.get_take_snapshot_progress_file())
        except Exception as e:
            logger.debug('Failed to remove snapshot progress file %s: %s'
                         %(self.config.get_take_snapshot_progress_file(), str(e)),
                         self)

        #handle errors
        has_errors = False
        if params[0]:
            if not self.config.continue_on_errors():
                self.remove_snapshot(new_snapshot)
                return [ False, True ]

            has_errors = True
            new_snapshot.failed = True

        if not params[1] and not self.config.take_snapshot_regardless_of_changes():
            self.remove_snapshot(new_snapshot)
            logger.info("Nothing changed, no new snapshot necessary", self)
            self.snapshotLog.append('[I] ' + _('Nothing changed, no new snapshot necessary'), 3)
            if prev_sid:
                prev_sid.setLastChecked()
            return [ False, False ]

        self.save_config_file(new_snapshot)
        self.save_permissions(new_snapshot)

        #copy snapshot log
        try:
            self.snapshotLog.flush()
            with open(self.snapshotLog.logFileName, 'rb') as logfile:
                new_snapshot.setLog(logfile.read())
        except Exception as e:
            logger.debug('Failed to write take_snapshot log %s into compressed file %s: %s'
                         %(self.config.get_take_snapshot_log_file(), new_snapshot.path(SID.LOG), str(e)),
                         self)

        new_snapshot.saveToContinue = False
        #rename snapshot
        os.rename(new_snapshot.path(), sid.path())

        if not sid.exists():
            logger.error("Can't rename %s to %s" % (new_snapshot.path(), sid.path()), self)
            self.set_take_snapshot_message( 1, _('Can\'t rename %(new_path)s to %(path)s')
                                                 %{'new_path': new_snapshot.path(),
                                                   'path': sid.path()})
            time.sleep(2) #max 1 backup / second
            return [ False, True ]

        self.save_snapshot_info(sid)

        #create last_snapshot symlink
        self.create_last_snapshot_symlink(sid)

        return [ True, has_errors ]

    def _smart_remove_keep_all_(self,
                                snapshots,
                                keep_snapshots,
                                min_date,
                                max_date):
        """
        Add all snapshots between ``min_date`` and ``max_date`` to
        ``keep_snapshots``.

        Args:
            snapshots (list):           full list of :py:class:`SID` objects
            keep_snapshots (list):      list of previous for keep selected
                                        snapshots that should be extended
            min_date (datetime.date):   minimum date for snapshots to keep
            max_date (datetime.date):   maximum date for snapshots to keep

        Returns:
            list:                       extended list of snapshots that should
                                        be keept
        """
        #TODO: remove keep_snapshots and just return snapshots selected in here
        min_id = SID(min_date, self.config)
        max_id = SID(max_date, self.config)

        logger.debug("Keep all >= %s and < %s" %(min_id, max_id), self)

        for sid in snapshots:
            if sid >= min_id and sid < max_id:
                if sid not in keep_snapshots:
                    keep_snapshots.append( sid )

        return keep_snapshots

    def _smart_remove_keep_first_(self,
                                  snapshots,
                                  keep_snapshots,
                                  min_date,
                                  max_date):
        """
        Add only the first snapshot between ``min_date`` and ``max_date`` to
        ``keep_snapshots``.

        Args:
            snapshots (list):           full list of :py:class:`SID` objects
            keep_snapshots (list):      list of previous for keep selected
                                        snapshots that should be extended
            min_date (datetime.date):   minimum date for snapshots to keep
            max_date (datetime.date):   maximum date for snapshots to keep

        Returns:
            list:                       extended list of snapshots that should
                                        be keept
        """
        #TODO: remove keep_snapshots and just return snapshots selected in here
        min_id = SID(min_date, self.config)
        max_id = SID(max_date, self.config)

        logger.debug("Keep first >= %s and < %s" %(min_id, max_id), self)

        for sid in snapshots:
            if sid >= min_id and sid < max_id:
                if sid not in keep_snapshots:
                    keep_snapshots.append( sid )
                break

        return keep_snapshots

    def inc_month(self, date):
        """
        First day of next month of ``date`` with respect on new years. So if
        ``date`` is December this will return 1st of January next year.

        Args:
            date (datetime.date):   old date that should be increased

        Returns:
            datetime.date:          1st day of next month
        """
        y = date.year
        m = date.month + 1
        if m > 12:
            m = 1
            y = y + 1
        return datetime.date( y, m, 1 )

    def dec_month(self, date):
        """
        First day of previous month of ``date`` with respect on previous years.
        So if ``date`` is January this will return 1st of December previous
        year.

        Args:
            date (datetime.date):   old date that should be decreased

        Returns:
            datetime.date:          1st day of previous month
        """
        y = date.year
        m = date.month - 1
        if m < 1:
            m = 12
            y = y - 1
        return datetime.date( y, m, 1 )

    def smart_remove(self,
                     now_full,
                     keep_all,
                     keep_one_per_day,
                     keep_one_per_week,
                     keep_one_per_month):
        """
        Remove old snapshots based on configurable intervals.

        Args:
            now_full (datetime.datetime):   date and time when take_snapshot was
                                            started
            keep_all (int):                 keep all snapshots for the
                                            last ``keep_all`` days
            keep_one_per_day (int):         keep one snapshot per day for the
                                            last ``keep_one_per_day`` days
            keep_one_per_week (int):        keep one snapshot per week for the
                                            last ``keep_one_per_week`` weeks
            keep_one_per_month (int):       keep one snapshot per month for the
                                            last ``keep_one_per_month`` months
        """
        snapshots = listSnapshots(self.config)
        logger.debug("Considered: %s" %snapshots, self)
        if len( snapshots ) <= 1:
            logger.debug("There is only one snapshots, so keep it", self)
            return

        if now_full is None:
            now_full = datetime.datetime.today()

        now = now_full.date()

        #keep the last snapshot
        #TODO: use tools.OrderedSet for keep_snapshots and update it 'keep_snapshot |= self._smart_remove_keep_all_()'
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
        first_year = int(snapshots[-1].sid[ : 4])
        for i in range( first_year, now.year+1 ):
            keep_snapshots = self._smart_remove_keep_first_( snapshots, keep_snapshots, datetime.date(i,1,1), datetime.date(i+1,1,1) )

        logger.debug("Keep snapshots: %s" %keep_snapshots, self)

        del_snapshots = []
        for sid in snapshots:
            if sid in keep_snapshots:
                continue

            if self.config.get_dont_remove_named_snapshots():
                if sid.name:
                    logger.debug("Keep snapshot: %s, it has a name" %sid, self)
                    continue

            del_snapshots.append(sid)

        if not del_snapshots:
            return

        #TODO: move this to subprocess.Popen
        if self.config.get_snapshots_mode() in ['ssh', 'ssh_encfs'] and self.config.get_smart_remove_run_remote_in_background():
            logger.info('[smart remove] remove snapshots in background: %s'
                        %del_snapshots, self)
            lckFile = os.path.normpath(os.path.join(del_snapshots[0].path(use_mode = ['ssh', 'ssh_encfs']), os.pardir, 'smartremove.lck'))

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
            head += 'TMP=\$(mktemp -d); '                      #create temp dir used for delete files with rsync
            head += 'test -z \\\"\$TMP\\\" && exit 1; '        #make sure $TMP dir was created
            head += 'test -n \\\"\$(ls \$TMP)\\\" && exit 1; ' #make sure $TMP is empty
            if logger.DEBUG:
                head += 'logger -t \\\"backintime smart-remove [$BASHPID]\\\" \\\"start\\\"; '
            head += 'flock -x 9; '
            if logger.DEBUG:
                head += 'logger -t \\\"backintime smart-remove [$BASHPID]\\\" \\\"got exclusive flock\\\"; '

            tail = 'rmdir \$TMP) 9>\\\"%s\\\""' %lckFile

            cmds = []
            for sid in del_snapshots:
                remote = self.rsync_remote_path(sid.path(use_mode = ['ssh', 'ssh_encfs']), use_mode = [], quote = '\\\"')
                rsync = ' '.join(tools.get_rsync_remove(self.config, run_local = False))
                rsync += ' \\\"\$TMP/\\\" {}; '.format(remote)

                s = 'test -e \\\"%s\\\" && (' %sid.path(use_mode = ['ssh', 'ssh_encfs'])
                if logger.DEBUG:
                    s += 'logger -t \\\"backintime smart-remove [$BASHPID]\\\" '
                    s += '\\\"snapshot %s still exist\\\"; ' %sid
                    s += 'sleep 1; ' #add one second delay because otherwise you might not see serialized process with small snapshots
                s += rsync
                s += 'rmdir \\\"%s\\\"; ' %sid.path(use_mode = ['ssh', 'ssh_encfs'])
                if logger.DEBUG:
                    s += 'logger -t \\\"backintime smart-remove [$BASHPID]\\\" '
                    s += '\\\"snapshot %s remove done\\\"' %sid
                s += '); '
                cmds.append(s)

            for cmd in tools.splitCommands(cmds,
                                           head = head,
                                           tail = tail,
                                           maxLength = maxLength - additionalChars):
                tools.Execute(self.cmd_ssh(cmd, quote = True)).run()
        else:
            logger.info("[smart remove] remove snapshots: %s"
                        %del_snapshots, self)
            for i, sid in enumerate(del_snapshots, 1):
                self.set_take_snapshot_message( 0, _('Smart remove') + ' %s/%s' %(i, len(del_snapshots)) )
                self.remove_snapshot( sid )

    def _free_space(self, now):
        """
        Remove old snapshots on based on different rules (only if enabled).
        First rule is to remove snapshots older than X years. Next will call
        :py:func:`smart_remove` to remove snapshots based on
        configurable intervals. Third rule is to remove the oldest snapshot
        until there is enough free space. Last rule will remove the oldest
        snapshot until there are enough free inodes.

        'last_snapshot' symlink will be fixed when done.

        Args:
            now (datetime.datetime):    date and time when take_snapshot was
                                        started
        """
        snapshots = listSnapshots(self.config, reverse = False)
        last_snapshot = snapshots[-1]

        #remove old backups
        if self.config.is_remove_old_snapshots_enabled():
            self.set_take_snapshot_message( 0, _('Removing old snapshots') )

            old_backup_id = SID(self.config.get_remove_old_snapshots_date(), self.config)
            logger.info("Remove backups older than: %s"
                        %old_backup_id.withoutTag, self)

            while True:
                if len(snapshots) <= 1:
                    break
                if snapshots[0] >= old_backup_id:
                    break

                if self.config.get_dont_remove_named_snapshots():
                    if snapshots[0].name:
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
            self.set_take_snapshot_message( 0, _('Trying to keep min free space') )

            min_free_space = self.config.get_min_free_space_in_mb()

            logger.info("Keep min free disk space: %s MiB"
                        %min_free_space, self)

            snapshots = listSnapshots(self.config, reverse = False)

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
                    if snapshots[0].name:
                        del snapshots[0]
                        continue

                logger.info("free disk space: %s MiB" %free_space, self)
                self.remove_snapshot( snapshots[0] )
                del snapshots[0]

        #try to keep free inodes
        if self.config.min_free_inodes_enabled():
            min_free_inodes = self.config.min_free_inodes()
            self.set_take_snapshot_message( 0, _('Trying to keep min %d%% free inodes') % min_free_inodes )
            logger.info("Keep min %d%% free inodes" %min_free_inodes, self)

            snapshots = listSnapshots(self.config, reverse = False)

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
                    if snapshots[0].name:
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
        """
        Get free space on filsystem containing ``path`` in MiB using
        :py:func:`os.statvfs()`. Depending on remote SFTP server this might fail
        on sshfs mounted shares.

        Args:
            path (str): full path
        """
        try:
            info = os.statvfs(path)
            if info.f_blocks != info.f_bavail:
                return info.f_frsize * info.f_bavail // ( 1024 * 1024 )
        except Exception as e:
            logger.debug('Failed to get free space for %s: %s'
                         %(path, str(e)),
                         self)
        logger.warning('Failed to stat snapshot path', self)

    def _stat_free_space_ssh(self):
        """
        Get free space on remote filsystem in MiB. This will call ``df`` on
        remote host and parse its output.
        """
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

    def filter_for(self,
                   base_sid,
                   base_path,
                   snapshots_list,
                   list_diff_only  = False,
                   flag_deep_check = False,
                   list_equal_to = ''):
        """
        Filter snapshots from ``snapshots_list`` based on whether ``base_path``
        file is included and optional if the snapshot is unique or equal to
        ``list_equal_to``.

        Args:
            base_sid (SID):         snapshot ID that contained the original
                                    file ``base_path``
            base_path (str):        path to file on root filesystem.
            snapshots_list (list):  List of :py:class:`SID` objects that should
                                    be filtered
            list_diff_only (bool):  if ``True`` only return unique snapshots.
                                    Which means if a file is exactly the same in
                                    different snapshots only the first snapshot
                                    will be listed
            flag_deep_check (bool): use md5sum to check uniqueness of files.
                                    More acurate but slow
            list_equal_to (str):    full path to file. If not empty only return
                                    snapshots which have exactly the same file
                                    as this file
        Returns:
            list:                   filtered list of :py:class:`SID` objects
        """
        snapshots_filtered = []

        base_full_path = base_sid.pathBackup(base_path)
        if not os.path.lexists( base_full_path ):
            return []

        all_snapshots_list = [RootSnapshot(self.config)]
        all_snapshots_list.extend( snapshots_list )

        #links
        if os.path.islink( base_full_path ):
            targets = []

            for sid in all_snapshots_list:
                path = sid.pathBackup(base_path)

                if os.path.lexists( path ) and os.path.islink( path ):
                    if list_diff_only:
                        target = os.readlink( path )
                        if target in targets:
                            continue
                        targets.append( target )
                    snapshots_filtered.append(sid)

            return snapshots_filtered

        #directories
        if os.path.isdir( base_full_path ):
            for sid in all_snapshots_list:
                path = sid.pathBackup(base_path)

                if os.path.exists( path ) and not os.path.islink( path ) and os.path.isdir( path ):
                    snapshots_filtered.append(sid)

            return snapshots_filtered

        #files
        if not list_diff_only and not list_equal_to:
            for sid in all_snapshots_list:
                path = sid.pathBackup(base_path)

                if os.path.exists( path ) and not os.path.islink( path ) and os.path.isfile( path ):
                    snapshots_filtered.append(sid)

            return snapshots_filtered

        # check for duplicates
        uniqueness = tools.UniquenessSet(flag_deep_check, follow_symlink = False, list_equal_to = list_equal_to)
        for sid in all_snapshots_list:
            path = sid.pathBackup(base_path)
            if os.path.exists( path ) and not os.path.islink( path ) and os.path.isfile( path ) and uniqueness.check_for(path):
                snapshots_filtered.append(sid)

        return snapshots_filtered

    def cmd_ssh(self, cmd, quote = False, use_mode = ['ssh', 'ssh_encfs'] ):
        """
        Add ssh, nice and ionice command to ``cmd`` to run that command on
        remote host.

        Args:
            cmd (str):          command
            quote (bool):       wrap single tick (') quotemarks around ``cmd``
            use_mode (list):    list of modes in which the result should
                                change to ``ssh USER@HOST cmd`` instead of
                                just ``cmd``

        Returns:
            str:                command with or without ssh prefix based on
                                ``use_mode`` and current mode
        """
        mode = self.config.get_snapshots_mode()
        if mode in ['ssh', 'ssh_encfs'] and mode in use_mode:
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

    def rsync_remote_path(self, path, use_mode = ['ssh', 'ssh_encfs'], quote = ''):
        """
        Format the destination string for rsync depending on which profile is
        used.

        Args:
            path (str):         destination path
            use_mode (list):    list of modes in which the result should
                                change to ``user@host:path`` instead of
                                just ``path``
            quote (str):        use this to quote the path

        Returns:
            str:                quoted ``path`` like '"/foo"'
                                or if the current mode is using ssh and
                                current mode is in ``use_mode`` a combination
                                of user, host and ``path``
                                like ''user@host:"/foo"''
        """
        mode = self.config.get_snapshots_mode()
        if mode in ['ssh', 'ssh_encfs'] and mode in use_mode:
            user = self.config.get_ssh_user()
            host = self.config.get_ssh_host()
            return '%(u)s@%(h)s:%(q)s%(p)s%(q)s' %{'u': user,
                                                   'h': host,
                                                   'q': quote,
                                                   'p': path}
        else:
            return '%(q)s%(p)s%(q)s' %{'q': quote, 'p': path}

    def delete_path(self, sid, path):
        """
        Delete ``path`` and all files and folder inside in snapshot ``sid``.

        Args:
            sid (SID):  snapshot ID in which ``path`` should be deleted
            path (str): path to delete
        """
        def handle_error(fn, path, excinfo):
            """
            Error handler for :py:func:`delete_path`. This will fix permissions
            and try again to remove the file.

            Args:
                fn (method):    callable which failed before
                path (str):     file to delete
                excinfo:        NotImplemented
            """
            dirname = os.path.dirname(path)
            st = os.stat(dirname)
            os.chmod(dirname, st.st_mode | stat.S_IWUSR)
            st = os.stat(path)
            os.chmod(path, st.st_mode | stat.S_IWUSR)
            fn(path)

        full_path = sid.pathBackup(path)
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

    def create_last_snapshot_symlink(self, sid):
        """
        Create symlink 'last_snapshot' to snapshot ``sid``

        Args:
            sid (SID):  snapshot that should be linked.

        Returns:
            bool:       ``True`` if successful
        """
        if sid is None:
            return
        symlink = self.config.get_last_snapshot_symlink()
        try:
            if os.path.islink(symlink):
                if os.path.basename(os.path.realpath(symlink)) == sid.sid:
                    return True
                os.remove(symlink)
            if os.path.exists(symlink):
                logger.error('Could not remove symlink %s' %symlink, self)
                return False
            logger.debug('Create symlink %s => %s' %(symlink, sid), self)
            os.symlink(sid.sid, symlink)
            return True
        except Exception as e:
            logger.error('Failed to create symlink %s: %s' %(symlink, str(e)), self)
            return False

    def flockExclusive(self):
        """
        Block :py:func:`take_snapshot` from other profiles or users
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
        """
        Release lock so other snapshots can continue
        """
        if self.flock_file:
            logger.debug('Release flock %s' %self.GLOBAL_FLOCK, self)
            fcntl.fcntl(self.flock_file, fcntl.LOCK_UN)
            self.flock_file.close()
        self.flock_file = None

    def rsyncSuffix(self, includeFolders = None, excludeFolders = None):
        """
        Create suffixes for rsync.

        Args:
            includeFolders (list):  folders to include. list of tuples (item, int)
                                    Where ``int`` is ``0`` if ``item`` is a
                                    folder or ``1`` if ``item`` is a file
            excludeFolders (list):  list of folders to exclude

        Returns:
            list:                   rsync include and exclude options
        """
        #create exclude patterns string
        rsync_exclude = self.rsyncExclude(excludeFolders)

        #create include patterns list
        rsync_include, rsync_include2 = self.rsyncInclude(includeFolders)

        encode = self.config.ENCODE
        ret = ['--chmod=Du+wx']
        ret.extend(['--exclude=' + i for i in (encode.exclude(self.config.get_snapshots_path()),
                                               encode.exclude(self.config._LOCAL_DATA_FOLDER),
                                               encode.exclude(self.config._MOUNT_ROOT)
                                               )])
        # TODO: fix bug #561:
        # after rsync_exclude we need to explicite include files inside excluded
        # folders, recursive exclude folder-content again and finally add the
        # rest from rsync_include2
        ret.extend(rsync_include)
        ret.extend(rsync_exclude)
        ret.extend(rsync_include2)
        ret.append('--exclude=*')
        ret.append(encode.chroot)
        return ret

    def rsyncExclude(self, excludeFolders = None):
        """
        Format exclude list for rsync

        Args:
            excludeFolders (list):  list of folders to exclude

        Returns:
            OrderedSet:             rsync exclude options
        """
        items = tools.OrderedSet()
        encode = self.config.ENCODE
        if excludeFolders is None:
            excludeFolders = self.config.get_exclude()

        for exclude in excludeFolders:
            exclude = encode.exclude(exclude)
            if exclude is None:
                continue
            items.add('--exclude=' + exclude)
        return items

    def rsyncInclude(self, includeFolders = None):
        """
        Format include list for rsync. Returns a tuple of two include strings.
        First string need to come before exclude, second after exclude.

        Args:
            includeFolders (list):  folders to include. list of
                                    tuples (item, int) where ``int`` is ``0``
                                    if ``item`` is a folder or ``1`` if ``item``
                                    is a file

        Returns:
            tuple:                  two item tuple of
                                    ``(OrderedSet('include1 opions'),
                                    OrderedSet('include2 options'))``
        """
        items1 = tools.OrderedSet()
        items2 = tools.OrderedSet()
        encode = self.config.ENCODE
        if includeFolders is None:
            includeFolders = self.config.get_include()

        for include_folder in includeFolders:
            folder = include_folder[0]

            if folder == "/":	# If / is selected as included folder it should be changed to ""
                #folder = ""	# because an extra / is added below. Patch thanks to Martin Hoefling
                items2.add('--include=/')
                items2.add('--include=/**')
                continue

            folder = encode.include(folder)
            if include_folder[1] == 0:
                items2.add('--include={}/**'.format(folder))
            else:
                items2.add('--include={}'.format(folder))
                folder = os.path.split( folder )[0]

            while True:
                if len( folder) <= 1:
                    break
                items1.add('--include={}/'.format(folder))
                folder = os.path.split( folder )[0]

        return (items1, items2)

class FileInfoDict(dict):
    """
    A :py:class:`dict` that maps a path (as :py:class:`bytes`) to a
    tuple (:py:class:`int`, :py:class:`bytes`, :py:class:`bytes`).
    """
    def __setitem__(self, key, value):
        assert isinstance(key, bytes), "key '{}' is not bytes instance".format(key)
        assert isinstance(value, tuple), "value '{}' is not tuple instance".format(value)
        assert len(value) == 3, "value '{}' does not have 3 items".format(value)
        assert isinstance(value[0], int), "first value '{}' is not int instance".format(value[0])
        assert isinstance(value[1], bytes), "second value '{}' is not bytes instance".format(value[1])
        assert isinstance(value[2], bytes), "third value '{}' is not bytes instance".format(value[2])
        super(FileInfoDict, self).__setitem__(key, value)

class SID(object):
    """
    Snapshot ID object used to gather all information for a snapshot

    Args:
        date (:py:class:`str`, :py:class:`datetime.date` or :py:class:`datetime.datetime`):
                                used for creating this snapshot. str must be in
                                snapshot ID format (e.g 20151218-173512-123)
        cfg (config.Config):    current config

    Raises:
        ValueError:             if ``date`` is :py:class:`str` instance and
                                doesn't match the snapshot ID format
                                (20151218-173512-123 or 20151218-173512)
        TypeError:              if ``date`` is not :py:class:`str`,
                                :py:class:`datetime.date` or
                                :py:class:`datetime.datetime` type
    """
    __cValidSID = re.compile(r'^\d{8}-\d{6}(?:-\d{3})?$')

    INFO     = 'info'
    NAME     = 'name'
    FAILED   = 'failed'
    FILEINFO = 'fileinfo.bz2'
    LOG      = 'takesnapshot.log.bz2'

    def __init__(self, date, cfg):
        self.config = cfg
        self.profileID = cfg.get_current_profile()
        self.isRoot = False

        if isinstance(date, datetime.datetime):
            self.sid = '-'.join((date.strftime('%Y%m%d-%H%M%S'), self.config.get_tag(self.profileID)))
            self.date = date
        elif isinstance(date, datetime.date):
            self.sid = '-'.join((date.strftime('%Y%m%d-000000'), self.config.get_tag(self.profileID)))
            self.date = datetime.datetime.combine(date, datetime.datetime.min.time())
        elif isinstance(date, str):
            if self.__cValidSID.match(date):
                self.sid = date
                self.date = datetime.datetime(*self.split())
            elif date == 'last_snapshot':
                raise LastSnapshotSymlink()
            else:
                raise ValueError("'date' must be in snapshot ID format (e.g 20151218-173512-123)")
        else:
            raise TypeError("'date' must be an instance of str, datetime.date or datetime.datetime")

    def __repr__(self):
        return self.sid

    def __eq__(self, other):
        """
        Compare snapshots based on self.sid

        Args:
            other (:py:class:`SID`, :py:class:`str`):
                        an other :py:class:`SID` or str instance

        Returns:
            bool:       ``True`` if other is equal
        """
        if isinstance(other, SID):
            return self.sid == other.sid and self.profileID == other.profileID
        elif isinstance(other, str):
            return self.sid == other
        else:
            return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        """
        Sort snapshots (alphabetical order) based on self.sid

        Args:
            other (:py:class:`SID`, :py:class:`str`):
                        an other :py:class:`SID` or str instance

        Returns:
            bool:       ``True`` if other is lower
        """
        if isinstance(other, SID):
            return self.sid < other.sid
        elif isinstance(other, str) and self.__cValidSID.match(other):
            return self.sid < other
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, SID):
            return self.sid <= other.sid
        elif isinstance(other, str) and self.__cValidSID.match(other):
            return self.sid <= other
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, SID):
            return self.sid > other.sid
        elif isinstance(other, str) and self.__cValidSID.match(other):
            return self.sid > other
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, SID):
            return self.sid >= other.sid
        elif isinstance(other, str) and self.__cValidSID.match(other):
            return self.sid >= other
        else:
            return NotImplemented

    def split(self):
        """
        Split self.sid into a tuple of int's
        with Year, Month, Day, Hour, Minute, Second

        Returns:
            tuple:  tuple of 6 int
        """
        def split(s, e):
            return int(self.sid[s:e])
        return (split(0, 4), split(4, 6), split(6, 8), split(9, 11), split(11, 13), split(13, 15))

    @property
    def displayID(self):
        """
        Snapshot ID in a user-readable format:
        YYYY-MM-DD HH:MM:SS

        Returns:
            str:    formated sID
        """
        return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*self.split())

    @property
    def displayName(self):
        """
        Combination of displayID, name and error indicator (if any)

        Returns:
            str:    name
        """
        ret = self.displayID
        name = self.name

        if name:
            ret += ' - {}'.format(name)

        if self.failed:
            ret += ' ({})'.format(_('WITH ERRORS !'))
        return ret

    @property
    def tag(self):
        """
        Snapshot ID's tag

        Returns:
            str:    tag (last three digits)
        """
        return self.sid[16:]

    @property
    def withoutTag(self):
        """
        Snapshot ID without tag

        Returns:
            str:    YYYYMMDD-HHMMSS
        """
        return self.sid[0:15]

    def path(self, *path, use_mode = []):
        """
        Current path of this snapshot automatically altered for
        remote/encrypted version of this path

        Args:
            *path (str):        one or more folder/files to join at the end of
                                the path.
            use_mode (list):    list of modes that should alter this path.
                                If the current mode is in this list, the path
                                will automatically altered for the
                                remote/encrypted version of this path.

        Returns:
            str:                full snapshot path
        """
        path = [i.strip(os.sep) for i in path]
        current_mode = self.config.get_snapshots_mode(self.profileID)
        if 'ssh' in use_mode and current_mode == 'ssh':
            return os.path.join(self.config.get_snapshots_full_path_ssh(self.profileID),
                                self.sid, *path)
        if 'ssh_encfs' in use_mode and current_mode == 'ssh_encfs':
            ret = os.path.join(self.config.get_snapshots_full_path_ssh(self.profileID),
                               self.sid, *path)
            return self.config.ENCODE.remote(ret)
        return os.path.join(self.config.get_snapshots_full_path(self.profileID),
                            self.sid, *path)

    def pathBackup(self, *path, **kwargs):
        """
        'backup' folder inside snapshots path

        Args:
            *path (str):        one or more folder/files to join at the end of
                                the path.
            use_mode (list):    list of modes that should alter this path.
                                If the current mode is in this list, the path
                                will automatically altered for the
                                remote/encrypted version of this path.

        Returns:
            str:                full snapshot path
        """
        return self.path('backup', *path, **kwargs)

    def makeDirs(self, *path):
        """
        Create snapshot directory

        Args:
            *path (str):    one or more folder/files to join at the end
                            of the path

        Returns:
            bool:           ``True`` if successful
        """
        if not os.path.isdir(self.config.get_snapshots_full_path(self.profileID)):
            logger.error('Snapshots path {} doesn\'t exist. Unable to make dirs for snapshot ID {}'.format(
                         self.config.get_snapshots_full_path(self.profileID), self.sid),
                         self)
            return False

        return tools.make_dirs(self.pathBackup(*path))

    def exists(self):
        """
        ``True`` if the snapshot folder and the "backup" folder inside exist

        Returns:
            bool:   ``True`` if exists
        """
        return os.path.isdir(self.path()) and os.path.isdir(self.pathBackup())

    def canOpenPath(self, path):
        """
        ``True`` if path is a file inside this snapshot

        Args:
            path (str): path from local filesystem (no snapshot path)

        Returns:
            bool:       ``True`` if file exists
        """
        fullPath = self.pathBackup(path)
        if not os.path.exists(fullPath):
            return False
        if not os.path.islink(fullPath):
            return True
        basePath = self.pathBackup()
        target = os.readlink(fullPath)
        target = os.path.join(os.path.abspath(os.path.dirname(fullPath)), target)
        return target.startswith(basePath)

    @property
    def name(self):
        """
        Name of this snapshot

        Args:
            name (str): new name of the snapshot

        Returns:
            str:        name of this snapshot
        """
        nameFile = self.path(self.NAME)
        if not os.path.isfile(nameFile):
            return ''
        try:
            with open(nameFile, 'rt') as f:
                return f.read()
        except Exception as e:
            logger.debug('Failed to get snapshot {} name: {}'.format(
                         self.sid, str(e)),
                         self)

    @name.setter
    def name(self, name):
        nameFile = self.path(self.NAME)

        self.makeWriteable()
        try:
            with open(nameFile, 'wt') as f:
                f.write(name)
        except Exception as e:
            logger.debug('Failed to set snapshot {} name: {}'.format(
                         self.sid, str(e)),
                         self)

    @property
    def lastChecked(self):
        """
        Date when snapshot has finished last time.
        This can be the end of creation of this snapshot or the last time when
        this snapshot was checked against source without changes.

        Returns:
            str:    date and time of last check (YYYY-MM-DD HH:MM:SS)
        """
        info = self.path(self.INFO)
        if os.path.exists(info):
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getatime(info)) )
        return self.displayID

    #using @property.setter would be confusing here as there is no value to give
    def setLastChecked(self):
        """
        Set info files atime to current time to indicate this snapshot was
        checked against source without changes right now.
        """
        info = self.path(self.INFO)
        if os.path.exists(info):
            os.utime(info, None)

    @property
    def failed(self):
        """
        This snapshot has failed

        Args:
            enable (bool): set or remove flag

        Returns:
            bool:           ``True`` if flag is set
        """
        failedFile = self.path(self.FAILED)
        return os.path.isfile(failedFile)

    @failed.setter
    def failed(self, enable):
        failedFile = self.path(self.FAILED)
        if enable:
            self.makeWriteable()
            try:
                with open(failedFile, 'wt') as f:
                    f.write('')
            except Exception as e:
                logger.debug('Failed to mark snapshot {} failed: {}'.format(
                             self.sid, str(e)),
                             self)
        elif os.path.exists(failedFile):
            os.remove(failedFile)

    @property
    def info(self):
        """
        Load/save "info" file which contains additional information
        about this snapshot (using configfile.ConfigFile)

        Args:
            i (configfile.ConfigFile):  info that should be saved.

        Returns:
            configfile.ConfigFile:  snapshots information
        """
        i = configfile.ConfigFile()
        i.load(self.path(self.INFO))
        return i

    @info.setter
    def info(self, i):
        assert isinstance(i, configfile.ConfigFile), 'i is not configfile.ConfigFile type: {}'.format(i)
        i.save(self.path(self.INFO))

    @property
    def fileInfo(self):
        """
        Load/save "fileinfo.bz2"

        Args:
            d (FileInfoDict): dict of: {path: (permission, user, group)}

        Returns:
            FileInfoDict:     dict of: {path: (permission, user, group)}
        """
        d = FileInfoDict()
        infoFile = self.path(self.FILEINFO)
        if not os.path.isfile(infoFile):
            return d

        try:
            with bz2.BZ2File(infoFile, 'rb') as fileinfo:
                for line in fileinfo:
                    line = line.strip(b'\n')
                    if not line:
                        continue
                    index = line.find(b'/')
                    if index < 0:
                        continue
                    f = line[index:]
                    if not f:
                        continue
                    info = line[:index].strip().split(b' ')
                    if len(info) == 3:
                        d[f] = (int(info[0]), info[1], info[2]) #perms, user, group
        except Exception as e:
            logger.debug('Failed to load fileinfo.bz2 from snapshot {}: {}'.format(
                         self.sid, str(e)),
                         self)
        return d

    @fileInfo.setter
    def fileInfo(self, d):
        assert isinstance(d, FileInfoDict), 'd is not FileInfoDict type: {}'.format(d)
        with bz2.BZ2File(self.path(self.FILEINFO), 'wb') as f:
            for path, info in d.items():
                f.write(b' '.join((str(info[0]).encode('utf-8', 'replace'),
                                   info[1],
                                   info[2],
                                   path))
                                   + b'\n')

    #TODO: use @property decorator
    def log(self, mode = None, decode = None):
        """
        Load log from "takesnapshot.log.bz2"

        Args:
            mode (int):                 Mode used for filtering. Take a look at
                                        :py:class:`snapshotlog.LogFilter`
            decode (encfstools.Decode): instance used for decoding lines or ``None``

        Yields:
            str:                        filtered and decoded log lines
        """
        logFile = self.path(self.LOG)
        logFilter = snapshotlog.LogFilter(mode, decode)
        try:
            with bz2.BZ2File(logFile, 'rb' ) as f:
                if logFilter.header:
                    yield logFilter.header
                for line in f.readlines():
                    line = logFilter.filter(line.decode('utf-8').rstrip('\n'))
                    if not line is None:
                        yield line
        except Exception as e:
            msg = ('Failed to get snapshot log from {}:'.format(logFile), str(e))
            logger.debug(' '.join(msg), self)
            for line in msg:
                yield line

    def setLog(self, log):
        """
        Write log to "takesnapshot.log.bz2"

        Args:
            log: full snapshot log
        """
        if isinstance(log, str):
            log = log.encode('utf-8', 'replace')
        logFile = self.path(self.LOG)
        try:
            with bz2.BZ2File(logFile, 'wb') as f:
                f.write(log)
        except Exception as e:
            logger.error('Failed to write log into compressed file {}: {}'.format(
                         logFile, str(e)),
                         self)

    def makeWriteable(self):
        """
        Make the snapshot path writeable so we can change files inside

        Returns:
            bool:   ``True`` if successful
        """
        path = self.path()
        rw = os.stat(path).st_mode | stat.S_IWUSR
        return os.chmod(path, rw)

class GenericNonSnapshot(SID):
    @property
    def displayID(self):
        return self.name

    @property
    def displayName(self):
        return self.name

    @property
    def tag(self):
        return self.name

    @property
    def withoutTag(self):
        return self.name

class NewSnapshot(GenericNonSnapshot):
    """
    Snapshot ID object for 'new_snapshot' folder

    Args:
        cfg (config.Config):    current config
    """

    NEWSNAPSHOT    = 'new_snapshot'
    SAVETOCONTINUE = 'save_to_continue'

    def __init__(self, cfg):
        self.config = cfg
        self.profileID = cfg.get_current_profile()
        self.isRoot = False

        self.sid = self.NEWSNAPSHOT
        self.date = datetime.datetime(1, 1, 1)

        self.__le__ = self.__lt__
        self.__ge__ = self.__gt__

    def __lt__(self, other):
        return False

    def __gt__(self, other):
        return True

    @property
    def name(self):
        """
        Name of this snapshot

        Returns:
            str:        name of this snapshot
        """
        return self.sid

    @property
    def saveToContinue(self):
        """
        Check if 'save_to_continue' flag is set

        Args:
            enable (bool): set or remove flag

        Returns:
            bool:           ``True`` if flag is set
        """
        return os.path.exists(self.path(self.SAVETOCONTINUE))

    @saveToContinue.setter
    def saveToContinue(self, enable):
        flag = self.path(self.SAVETOCONTINUE)
        if enable:
            with open(flag, 'wt') as f:
                pass
        elif os.path.exists(flag):
            os.remove(flag)

class RootSnapshot(GenericNonSnapshot):
    """
    Snapshot ID for the filesystem root folder ('/')

    Args:
        cfg (config.Config):    current config
    """
    def __init__(self, cfg):
        self.config = cfg
        self.profileID = cfg.get_current_profile()
        self.isRoot = True

        self.sid = '/'
        self.date = datetime.datetime(datetime.MAXYEAR, 12, 31)

        self.__le__ = self.__lt__
        self.__ge__ = self.__gt__

    def __lt__(self, other):
        return False

    def __gt__(self, other):
        return True

    @property
    def name(self):
        """
        Name of this snapshot

        Returns:
            str:        name of this snapshot
        """
        return _('Now')

    def path(self, *path, use_mode = []):
        """
        Current path of this snapshot automatically altered for
        remote/encrypted version of this path

        Args:
            *path (str):        one or more folder/files to join at the end of
                                the path.
            use_mode (list):    list of modes that should alter this path.
                                If the current mode is in this list, the path
                                will automatically altered for the
                                remote/encrypted version of this path.

        Returns:
            str:                full snapshot path
        """
        current_mode = self.config.get_snapshots_mode(self.profileID)
        if 'ssh_encfs' in use_mode and current_mode == 'ssh_encfs':
            if path:
                path = self.config.ENCODE.remote(os.path.join(*path))
            return os.path.join(self.config.ENCODE.chroot, path)
        else:
            return os.path.join(os.sep, *path)

def iterSnapshots(cfg, includeNewSnapshot = False):
    """
    Iterate over snapshots in current snapshot path. Use this in a 'for' loop
    for faster processing than list object

    Args:
        cfg (config.Config):        current config
        includeNewSnapshot (bool):  include a NewSnapshot instance if
                                    'new_snapshot' folder is available.

    Yields:
        SID:                        snapshot IDs
    """
    for item in os.listdir(cfg.get_snapshots_full_path()):
        if item == NewSnapshot.NEWSNAPSHOT:
            newSid = NewSnapshot(cfg)
            if newSid.exists() and includeNewSnapshot:
                yield newSid
            continue
        try:
            sid = SID(item, cfg)
            if sid.exists():
                yield sid
        except Exception as e:
            if not isinstance(e, LastSnapshotSymlink):
                logger.debug("'{}' is no snapshot ID: {}".format(item, str(e)))

def listSnapshots(cfg, includeNewSnapshot = False, reverse = True):
    """
    List of snapshots in current snapshot path.

    Args:
        cfg (config.Config):        current config (config.Config instance)
        includeNewSnapshot (bool):  include a NewSnapshot instance if
                                    'new_snapshot' folder is available
        reverse (bool):             sort reverse

    Returns:
        list:                       list of :py:class:`SID` objects
    """
    ret = list(iterSnapshots(cfg, includeNewSnapshot))
    ret.sort(reverse = reverse)
    return ret

def lastSnapshot(cfg):
    """
    Most recent snapshot.

    Args:
        cfg (config.Config):    current config (config.Config instance)

    Returns:
        SID:                    most recent snapshot ID
    """
    sids = listSnapshots(cfg)
    if sids:
        return sids[0]

if __name__ == '__main__':
    config = config.Config()
    snapshots = Snapshots( config )
    snapshots.take_snapshot()
