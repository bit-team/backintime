#	Back In Time
#	Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze, Taylor Raack
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
import tools
import encfstools
import mount
import progress
import bcolors
import snapshotlog
from applicationinstance import ApplicationInstance
from exceptions import MountException, LastSnapshotSymlink

_ = gettext.gettext


class Snapshots:
    """
    Collection of take-snapshot and restore commands.

    Args:
        cfg (config.Config): current config
    """
    SNAPSHOT_VERSION = 3
    GLOBAL_FLOCK = '/tmp/backintime.lock'

    def __init__(self, cfg = None):
        """
        """
        # This raises an exception if no config is loaded
        self.config = config.Config.instance()

        # IMHO this class shouldn't be responsible to
        # invoke loading a config file (buhtz)
        # if self.config is None:
        #    self.config = config.Config()

        self.snapshotLog = snapshotlog.SnapshotLog(self.config)

        self.clearIdCache()
        self.clearNameCache()

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

        self.lastBusyCheck = datetime.datetime(1,1,1)
        self.flock = None
        self.restorePermissionFailed = False

    #TODO: make own class for takeSnapshotMessage
    def clearTakeSnapshotMessage(self):
        files = (self.config.takeSnapshotMessageFile(), \
                 self.config.takeSnapshotProgressFile())
        for f in files:
            if os.path.exists(f):
                os.remove(f)

    #TODO: make own class for takeSnapshotMessage
    def takeSnapshotMessage(self):
        wait = datetime.datetime.now() - datetime.timedelta(seconds = 5)
        if self.lastBusyCheck < wait:
            self.lastBusyCheck = datetime.datetime.now()
            if not self.busy():
                self.clearTakeSnapshotMessage()
                return None

        if not os.path.exists(self.config.takeSnapshotMessageFile()):
            return None
        try:
            with open(self.config.takeSnapshotMessageFile(), 'rt') as f:
                items = f.read().split('\n')
        except Exception as e:
            logger.debug('Failed to get takeSnapshot message from %s: %s'
                         %(self.config.takeSnapshotMessageFile(), str(e)),
                         self)
            return None

        if len(items) < 2:
            return None

        mid = 0
        try:
            mid = int(items[0])
        except Exception as e:
            logger.debug('Failed extract message ID from %s: %s'
                         %(items[0], str(e)),
                         self)

        del items[0]
        message = '\n'.join(items)

        return(mid, message)

    #TODO: make own class for takeSnapshotMessage
    def setTakeSnapshotMessage(self, type_id, message, timeout = -1):
        data = str(type_id) + '\n' + message

        try:
            with open(self.config.takeSnapshotMessageFile(), 'wt') as f:
                f.write(data)
        except Exception as e:
            logger.debug('Failed to set takeSnapshot message to %s: %s'
                         %(self.config.takeSnapshotMessageFile(), str(e)),
                         self)

        if 1 == type_id:
            self.snapshotLog.append('[E] ' + message, 1)
        else:
            self.snapshotLog.append('[I] '  + message, 3)

        try:
            profile_id =self.config.currentProfile()
            profile_name = self.config.profileName(profile_id)
            self.config.PLUGIN_MANAGER.message(profile_id, profile_name, type_id, message, timeout)
        except Exception as e:
            logger.debug('Failed to send message to plugins: %s'
                         %str(e),
                         self)

    def busy(self):
        instance = ApplicationInstance(self.config.takeSnapshotInstanceFile(), False)
        return instance.busy()

    def pid(self):
        instance = ApplicationInstance(self.config.takeSnapshotInstanceFile(), False)
        return instance.readPidFile()[0]

    def clearNameCache(self):
        """
        Reset the cache for user and group names.
        """
        self.userCache = {}
        self.groupCache = {}

    def clearIdCache(self):
        """
        Reset the cache for UIDs and GIDs.
        """
        self.uidCache = {}
        self.gidCache = {}

    def uid(self, name, callback = None, backup = None):
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

        if name in self.uidCache:
            return self.uidCache[name]
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
                    self.restorePermissionFailed = True
                    msg = 'Failed to get UID for %s: %s' %(name, str(e))
                    logger.error(msg, self)
                    if callback:
                        callback(msg)

            self.uidCache[name] = uid
            return uid

    def gid(self, name, callback = None, backup = None):
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

        if name in self.gidCache:
            return self.gidCache[name]
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
                    self.restorePermissionFailed = True
                    msg = 'Failed to get GID for %s: %s' %(name, str(e))
                    logger.error(msg, self)
                    if callback:
                        callback(msg)

            self.gidCache[name] = gid
            return gid

    def userName(self, uid):
        """
        Get the username for the given uid.
        uid->name will be cached to speed up subsequent requests.

        Args:
            uid (int):  User identifier (UID) to search for

        Returns:
            str:        name of the user with UID uid or '-' if not found
        """
        if uid in self.userCache:
            return self.userCache[uid]
        else:
            name = '-'
            try:
                name = pwd.getpwuid(uid).pw_name
            except Exception as e:
                logger.debug('Failed to get user name for UID %s: %s'
                             %(uid, str(e)),
                             self)

            self.userCache[uid] = name
            return name

    def groupName(self, gid):
        """
        Get the groupname for the given gid.
        gid->name will be cached to speed up subsequent requests.

        Args:
            gid (int):  Group identifier (GID) to search for

        Returns:
            str:        name of the Group with GID gid or '.' if not found
        """
        if gid in self.groupCache:
            return self.groupCache[gid]
        else:
            name = '-'
            try:
                name = grp.getgrgid(gid).gr_name
            except Exception as e:
                logger.debug('Failed to get group name for GID %s: %s'
                             %(gid, str(e)),
                             self)

            self.groupCache[gid] = name
            return name

    def restoreCallback(self, callback, ok, msg):
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
                self.restorePermissionFailed = True
            callback(msg)

    def restorePermission(self, key_path, path, fileInfoDict, callback = None):
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
        uid = self.uid(info[1], callback)
        gid = self.gid(info[2], callback)

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
                    os.chown(path, uid, gid)
                    ok = True
                except:
                    pass
                self.restoreCallback(callback, ok, "chown %s %s : %s" % (path.decode(errors = 'ignore'), uid, gid))
                st = os.stat(path)

            #if restore uid/gid failed try to restore at least gid
            if not ok and gid != st.st_gid:
                try:
                    os.chown(path, -1, gid)
                    ok = True
                except:
                    pass
                self.restoreCallback(callback, ok, "chgrp %s %s" % (path.decode(errors = 'ignore'), gid))
                st = os.stat(path)

        #restore perms
        ok = False
        if info[0] != st.st_mode:
            try:
                os.chmod(path, info[0])
                ok = True
            except:
                pass
            self.restoreCallback(callback, ok, "chmod %s %04o" % (path.decode(errors = 'ignore'), info[0]))

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
        instance = ApplicationInstance(self.config.restoreInstanceFile(), False, flock = True)
        if instance.check():
            instance.startApplication()
        else:
            logger.warning('Restore is already running', self)
            return

        if restore_to.endswith('/'):
            restore_to = restore_to[: -1]

        if not isinstance(paths, (list, tuple)):
            paths = (paths,)

        logger.info("Restore: %s to: %s"
                    %(', '.join(paths), restore_to),
                    self)

        info = sid.info

        cmd_prefix = tools.rsyncPrefix(self.config, no_perms = False, use_mode = ['ssh'])
        cmd_prefix.extend(('-R', '-v'))
        if backup:
            cmd_prefix.extend(('--backup', '--suffix=%s' %self.backupSuffix()))
        if delete:
            cmd_prefix.append('--delete')
            cmd_prefix.append('--filter=protect %s' % self.config.snapshotsPath())
            cmd_prefix.append('--filter=protect %s' % self.config._LOCAL_DATA_FOLDER)
            cmd_prefix.append('--filter=protect %s' % self.config._MOUNT_ROOT)
        if only_new:
            cmd_prefix.append('--update')

        restored_paths = []
        for path in paths:
            tools.makeDirs(os.path.dirname(path))
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

            cmd.append(self.rsyncRemotePath('%s.%s' %(src_base, src_path), use_mode = ['ssh']))
            cmd.append('%s/' %restore_to)
            proc = tools.Execute(cmd,
                                 callback = callback,
                                 filters = (self.filterRsyncProgress,),
                                 parent = self)
            self.restoreCallback(callback, True, proc.printable_cmd)
            proc.run()
            self.restoreCallback(callback, True, ' ')
            restored_paths.append((path, src_delta))
        try:
            os.remove(self.config.takeSnapshotProgressFile())
        except Exception as e:
            logger.debug('Failed to remove snapshot progress file %s: %s'
                         %(self.config.takeSnapshotProgressFile(), str(e)),
                         self)

        #restore permissions
        logger.info('Restore permissions', self)
        self.restoreCallback(callback, True, ' ')
        self.restoreCallback(callback, True, _("Restore permissions:"))
        self.restorePermissionFailed = False
        fileInfoDict = sid.fileInfo

        #cache uids/gids
        for uid, name in info.listValue('user', ('int:uid', 'str:name')):
            self.uid(name.encode(), callback = callback, backup = uid)
        for gid, name in info.listValue('group', ('int:gid', 'str:name')):
            self.gid(name.encode(), callback = callback, backup = gid)

        if fileInfoDict:
            all_dirs = [] #restore dir permissions after all files are done
            for path, src_delta in restored_paths:
                #explore items
                snapshot_path_to = sid.pathBackup(path).rstrip('/')
                root_snapshot_path_to = sid.pathBackup().rstrip('/')
                #use bytes instead of string from here
                if isinstance(path, str):
                    path = path.encode()
                if isinstance(restore_to, str):
                    restore_to = restore_to.encode()

                if not restore_to:
                    path_items = path.strip(b'/').split(b'/')
                    curr_path = b'/'
                    for path_item in path_items:
                        curr_path = os.path.join(curr_path, path_item)
                        if curr_path not in all_dirs:
                            all_dirs.append(curr_path)
                else:
                    if path not in all_dirs:
                        all_dirs.append(path)

                if os.path.isdir(snapshot_path_to) and not os.path.islink(snapshot_path_to):
                    head = len(root_snapshot_path_to.encode())
                    for explore_path, dirs, files in os.walk(snapshot_path_to.encode()):
                        for item in dirs:
                            item_path = os.path.join(explore_path, item)[head:]
                            if item_path not in all_dirs:
                                all_dirs.append(item_path)

                        for item in files:
                            item_path = os.path.join(explore_path, item)[head:]
                            real_path = restore_to + item_path[src_delta:]
                            self.restorePermission(item_path, real_path, fileInfoDict, callback)

            all_dirs.reverse()
            for item_path in all_dirs:
                real_path = restore_to + item_path[src_delta:]
                self.restorePermission(item_path, real_path, fileInfoDict, callback)

            self.restoreCallback(callback, True, '')
            if self.restorePermissionFailed:
                status = _('FAILED')
            else:
                status = _('Done')
            self.restoreCallback(callback, True, _("Restore permissions:") + ' ' + status)

        instance.exitApplication()

    def backupSuffix(self):
        """
        Get suffix for backup files.

        Returns:
            str:    backup suffix in form of '.backup.YYYYMMDD'
        """
        return '.backup.' + datetime.date.today().strftime('%Y%m%d')

    def remove(self, sid):
        """
        Remove snapshot ``sid``.

        Args:
            sid (SID):              snapshot to remove
        """
        if isinstance(sid, RootSnapshot):
            return
        rsync = tools.rsyncRemove(self.config)
        with TemporaryDirectory() as d:
            rsync.append(d + os.sep)
            rsync.append(self.rsyncRemotePath(sid.path(use_mode = ['ssh', 'ssh_encfs'])))
            tools.Execute(rsync).run()
            shutil.rmtree(sid.path())

    def backup(self, force = False):
        """
        Wrapper for :py:func:`takeSnapshot` which will prepair and clean up
        things for the main :py:func:`takeSnapshot` method. This will check
        that no other snapshots are running at the same time, there is nothing
        prohibing a new snapshot (e.g. on battery) and the profile is configured
        correctly. This will also mount and unmount remote destinations.

        Args:
            force (bool):   force taking a new snapshot even if the profile is
                            not scheduled or the machine is running on battery

        Returns:
            bool:           ``True`` if there was an error
        """
        ret_val, ret_error = False, True
        sleep = True

        self.config.PLUGIN_MANAGER.load(self)

        if not self.config.isConfigured():
            logger.warning('Not configured', self)
            self.config.PLUGIN_MANAGER.error(1) #not configured
        elif not force and self.config.noSnapshotOnBattery() and tools.onBattery():
            self.setTakeSnapshotMessage(0, _('Deferring backup while on battery'))
            logger.info('Deferring backup while on battery', self)
            logger.warning('Backup not performed', self)
            ret_error = False
        elif not force and not self.config.backupScheduled():
            logger.info('Profile "%s" is not scheduled to run now.'
                        %self.config.profileName(), self)
            ret_error = False
        else:
            instance = ApplicationInstance(self.config.takeSnapshotInstanceFile(), False, flock = True)
            restore_instance = ApplicationInstance(self.config.restoreInstanceFile(), False)
            if not instance.check():
                logger.warning('A backup is already running.  The pid of the \
already running backup is in file %s.  Maybe delete it' % instance.pidFile , self )
                self.config.PLUGIN_MANAGER.error(2) #a backup is already running
            elif not restore_instance.check():
                logger.warning('Restore is still running. Stop backup until \
restore is done. The pid of the already running restore is in %s.  Maybe delete it'\
                               % restore_instance.pidFile, self)
            else:
                if self.config.noSnapshotOnBattery () and not tools.powerStatusAvailable():
                    logger.warning('Backups disabled on battery but power status is not available', self)

                instance.startApplication()
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
                    instance.exitApplication()
                    logger.info('Unlock', self)
                    time.sleep(2)
                    return True
                else:
                    self.config.setCurrentHashId(hash_id)

                include_folders = self.config.include()

                if not include_folders:
                    logger.info('Nothing to do', self)
                elif not self.config.PLUGIN_MANAGER.processBegin():
                    logger.info('A plugin prevented the backup', self)
                else:
                    #take snapshot process begin
                    self.setTakeSnapshotMessage(0, '...')
                    self.snapshotLog.new(now)
                    profile_id = self.config.currentProfile()
                    profile_name = self.config.profileName()
                    logger.info("Take a new snapshot. Profile: %s %s"
                                %(profile_id, profile_name), self)

                    if not self.config.canBackup(profile_id):
                        if self.config.PLUGIN_MANAGER.hasGuiPlugins and self.config.notify():
                            self.setTakeSnapshotMessage(1,
                                    _('Can\'t find snapshots folder.\nIf it is on a removable drive please plug it.') +
                                    '\n' +
                                    gettext.ngettext('Waiting %s second.', 'Waiting %s seconds.', 30) % 30,
                                    30)
                        for counter in range(30, 0, -1):
                            time.sleep(1)
                            if self.config.canBackup():
                                break

                    if not self.config.canBackup(profile_id):
                        logger.warning('Can\'t find snapshots folder!', self)
                        self.config.PLUGIN_MANAGER.error(3) #Can't find snapshots directory (is it on a removable drive ?)
                    else:
                        ret_error = False
                        sid = SID(now, self.config)

                        if sid.exists():
                            logger.warning("Snapshot path \"%s\" already exists" %sid.path(), self)
                            self.config.PLUGIN_MANAGER.error(4, sid) #This snapshots already exists
                        else:
                            try:
                                ret_val, ret_error = self.takeSnapshot(sid, now, include_folders)
                            except:
                                new = NewSnapshot(self.config)
                                if new.exists():
                                    new.saveToContinue = False
                                    new.failed = True
                                raise

                        if not ret_val:
                            self.remove(sid)

                            if ret_error:
                                logger.error('Failed to take snapshot !!!', self)
                                self.setTakeSnapshotMessage(1, _('Failed to take snapshot %s !!!') % sid.displayID)
                                time.sleep(2)
                            else:
                                logger.warning("No new snapshot", self)
                        else:
                            ret_error = False

                        if not ret_error:
                            self.freeSpace(now)
                            self.setTakeSnapshotMessage(0, _('Finalizing'))

                    time.sleep(2)
                    sleep = False

                    if ret_val:
                        self.config.PLUGIN_MANAGER.newSnapshot(sid, sid.path()) #new snapshot

                    self.config.PLUGIN_MANAGER.processEnd() #take snapshot process end

                if sleep:
                    time.sleep(2)
                    sleep = False

                if not ret_error:
                    self.clearTakeSnapshotMessage()

                #unmount
                try:
                    mount.Mount(cfg = self.config).umount(self.config.current_hash_id)
                except MountException as ex:
                    logger.error(str(ex), self)

                instance.exitApplication()
                self.flockRelease()
                logger.info('Unlock', self)

        if sleep:
            time.sleep(2) #max 1 backup / second

        #release inhibit suspend
        if self.config.inhibitCookie:
            self.config.inhibitCookie = tools.unInhibitSuspend(*self.config.inhibitCookie)

        return ret_error

    def filterRsyncProgress(self, line):
        """
        Filter rsync's stdout for progress informations and store them in
        '~/.local/share/backintime/worker<N>.progress' file.

        Args:
            line (str): stdout line from rsync

        Returns:
            str:        ``line`` if it had no progress infos. ``None`` if
                        ``line`` was a progress
        """
        ret = []
        for l in line.split('\n'):
            m = self.reRsyncProgress.match(l)
            if m:
                # if m.group(5).strip():
                #     return
                pg = progress.ProgressFile(self.config)
                pg.setIntValue('status', pg.RSYNC)
                pg.setStrValue('sent', m.group(1))
                pg.setIntValue('percent', int(m.group(2)))
                pg.setStrValue('speed', m.group(3))
                #pg.setStrValue('eta', m.group(4))
                pg.save()
                del(pg)
            else:
                ret.append(l)
        return '\n'.join(ret)

    def rsyncCallback(self, line, params):
        """
        Parse rsync's stdout, send it to takeSnapshotMessage and
        takeSnapshotLog. Also check if there has been changes or errors in
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

        self.setTakeSnapshotMessage(0, _('Take snapshot') + " (rsync: %s)" % line)

        if line.endswith(')'):
            if line.startswith('rsync:'):
                if not line.startswith('rsync: chgrp ') and not line.startswith('rsync: chown '):
                    params[0] = True
                    self.setTakeSnapshotMessage(1, 'Error: ' + line)

        if len(line) >= 13:
            if line.startswith('BACKINTIME: '):
                if line[12] != '.' and line[12:14] != 'cd':
                    params[1] = True
                    self.snapshotLog.append('[C] ' + line[12:], 2)

    def makeDirs(self, path):
        """
        Wrapper for :py:func:`tools.makeDirs()`. Create directories ``path``
        recursive and return success. If not successful send error-message to
        log.

        Args:
            path (str): fullpath to directories that should be created

        Returns:
            bool:       ``True`` if successful
        """
        if not tools.makeDirs(path):
            logger.error("Can't create folder: %s" % path, self)
            self.setTakeSnapshotMessage(1, _('Can\'t create folder: %s') % path)
            time.sleep(2) #max 1 backup / second
            return False
        return True

    def backupConfig(self, sid):
        """
        Backup the config file to the snapshot and to the backup root if backup
        is encrypted.

        Args:
            sid (SID):  snapshot in which the config should be stored
        """
        logger.info('Save config file', self)
        self.setTakeSnapshotMessage(0, _('Saving config file...'))
        with open(self.config._LOCAL_CONFIG_PATH, 'rb') as src:
            with open(sid.path('config'), 'wb') as dst1:
                dst1.write(src.read())
            if self.config.snapshotsMode() == 'local_encfs':
                src.seek(0)
                with open(os.path.join(self.config.localEncfsPath(), 'config'), 'wb') as dst2:
                    dst2.write(src.read())
            elif self.config.snapshotsMode() == 'ssh_encfs':
                cmd = tools.rsyncPrefix(self.config, no_perms = False)
                cmd.append(self.config._LOCAL_CONFIG_PATH)
                cmd.append(self.rsyncRemotePath(self.config.sshSnapshotsPath()))
                tools.Execute(cmd, parent = self).run()

    def backupInfo(self, sid):
        """
        Save infos about the snapshot into the 'info' file.

        Args:
            sid (SID):  snapshot that should get an info file
        """
        logger.info("Create info file", self)
        machine = self.config.host()
        user = self.config.user()
        profile_id = self.config.currentProfile()
        i = configfile.ConfigFile()
        i.setIntValue('snapshot_version', self.SNAPSHOT_VERSION)
        i.setStrValue('snapshot_date', sid.withoutTag)
        i.setStrValue('snapshot_machine', machine)
        i.setStrValue('snapshot_user', user)
        i.setIntValue('snapshot_profile_id', profile_id)
        i.setIntValue('snapshot_tag', sid.tag)
        i.setListValue('user', ('int:uid', 'str:name'), list(self.userCache.items()))
        i.setListValue('group', ('int:gid', 'str:name'), list(self.groupCache.items()))
        i.setStrValue('filesystem_mounts', json.dumps(tools.filesystemMountInfo()))
        sid.info = i

    def backupPermissions(self, sid):
        """
        Save permissions (owner, group, read-, write- and executable)
        for all files in Snapshot ``sid`` into snapshots fileInfoDict.

        Args:
            sid (SID):  snapshot that should be scanned
        """
        logger.info('Save permissions', self)
        self.setTakeSnapshotMessage(0, _('Saving permissions...'))

        fileInfoDict = FileInfoDict()
        if self.config.snapshotsMode() == 'ssh_encfs':
            decode = encfstools.Decode(self.config, False)
        else:
            decode = encfstools.Bounce()

        # backup permissions of /
        # bugfix for https://github.com/bit-team/backintime/issues/708
        self.backupPermissionsCallback(b'/', (fileInfoDict, decode))

        rsync = ['rsync', '--dry-run', '-r', '--out-format=%n']
        rsync.extend(tools.rsyncSshArgs(self.config))
        rsync.append(self.rsyncRemotePath(sid.pathBackup(use_mode = ['ssh', 'ssh_encfs'])) + os.sep)
        with TemporaryDirectory() as d:
            rsync.append(d + os.sep)
            proc = tools.Execute(rsync,
                                 callback = self.backupPermissionsCallback,
                                 user_data = (fileInfoDict, decode),
                                 parent = self,
                                 conv_str = False,
                                 join_stderr = False)
            proc.run()

        sid.fileInfo = fileInfoDict

    def backupPermissionsCallback(self, line, user_data):
        """
        Rsync callback for :py:func:`Snapshots.backupPermissions`.

        Args:
            line(bytes):        output from rsync command
            user_data (tuple):  two item tuple of (:py:class:`FileInfoDict`,
                                :py:class:`encfstools.Decode`)
        """
        fileInfoDict, decode = user_data
        self.collectPermission(fileInfoDict, b'/' + decode.path(line).rstrip(b'/'))

    def collectPermission(self, fileinfo, path):
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
            user = self.userName(info.st_uid).encode('utf-8', 'replace')
            group = self.groupName(info.st_gid).encode('utf-8', 'replace')
            fileinfo[path] = (mode, user, group)

    def takeSnapshot(self, sid, now, include_folders):
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
        self.setTakeSnapshotMessage(0, _('...'))

        new_snapshot = NewSnapshot(self.config)
        encode = self.config.ENCODE
        params = [False, False] # [error, changes]

        if new_snapshot.exists() and new_snapshot.saveToContinue:
            logger.info("Found leftover '%s' which can be continued." %new_snapshot.displayID, self)
            self.setTakeSnapshotMessage(0, _("Found leftover '%s' which can be continued.") %new_snapshot.displayID)
            #fix permissions
            for file in os.listdir(new_snapshot.path()):
                file = os.path.join(new_snapshot.path(), file)
                mode = os.stat(file).st_mode
                try:
                    os.chmod(file, mode | stat.S_IWUSR)
                except PermissionError:
                    pass
            # search previous log for changes and set params
            params[1] = new_snapshot.hasChanges
        elif new_snapshot.exists() and not new_snapshot.saveToContinue:
            logger.info("Remove leftover '%s' folder from last run" %new_snapshot.displayID)
            self.setTakeSnapshotMessage(0, _("Removing leftover '%s' folder from last run") %new_snapshot.displayID)
            self.remove(new_snapshot)

            if os.path.exists(new_snapshot.path()):
                logger.error("Can't remove folder: %s" % new_snapshot.path(), self)
                self.setTakeSnapshotMessage(1, _('Can\'t remove folder: %s') % new_snapshot.path())
                time.sleep(2) #max 1 backup / second
                return [False, True]

        if not new_snapshot.saveToContinue and not new_snapshot.makeDirs():
            return [False, True]

        prev_sid = None
        snapshots = listSnapshots(self.config)
        if snapshots:
            prev_sid = snapshots[0]

        #rsync prefix & suffix
        rsync_prefix = tools.rsyncPrefix(self.config, no_perms = False)
        if self.config.excludeBySizeEnabled():
            rsync_prefix.append('--max-size=%sM' %self.config.excludeBySize())
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
        cmd.append(self.rsyncRemotePath(new_snapshot.pathBackup(use_mode = ['ssh', 'ssh_encfs'])))

        self.setTakeSnapshotMessage(0, _('Taking snapshot'))

        #run rsync
        proc = tools.Execute(cmd,
                             callback = self.rsyncCallback,
                             user_data = params,
                             filters = (self.filterRsyncProgress,),
                             parent = self)
        self.snapshotLog.append('[I] ' + proc.printable_cmd, 3)
        proc.run()

        #cleanup
        try:
            os.remove(self.config.takeSnapshotProgressFile())
        except Exception as e:
            logger.debug('Failed to remove snapshot progress file %s: %s'
                         %(self.config.takeSnapshotProgressFile(), str(e)),
                         self)

        #handle errors
        has_errors = False
        # params[0] -> error
        if params[0]:
            if not self.config.continueOnErrors():
                self.remove(new_snapshot)
                return [False, True]

            has_errors = True
            new_snapshot.failed = True

        # params[1] -> changes
        if not params[1] and not self.config.takeSnapshotRegardlessOfChanges():
            self.remove(new_snapshot)
            logger.info("Nothing changed, no new snapshot necessary", self)
            self.snapshotLog.append('[I] ' + _('Nothing changed, no new snapshot necessary'), 3)
            if prev_sid:
                prev_sid.setLastChecked()
            if not has_errors and not list(self.config.anacrontabFiles()):
                tools.writeTimeStamp(self.config.anacronSpoolFile())
            return [False, False]

        self.backupConfig(new_snapshot)
        self.backupPermissions(new_snapshot)

        #copy snapshot log
        try:
            self.snapshotLog.flush()
            with open(self.snapshotLog.logFileName, 'rb') as logfile:
                new_snapshot.setLog(logfile.read())
        except Exception as e:
            logger.debug('Failed to write takeSnapshot log %s into compressed file %s: %s'
                         %(self.config.takeSnapshotLogFile(), new_snapshot.path(SID.LOG), str(e)),
                         self)

        new_snapshot.saveToContinue = False
        #rename snapshot
        os.rename(new_snapshot.path(), sid.path())

        if not sid.exists():
            logger.error("Can't rename %s to %s" % (new_snapshot.path(), sid.path()), self)
            self.setTakeSnapshotMessage(1, _('Can\'t rename %(new_path)s to %(path)s')
                                                 %{'new_path': new_snapshot.path(),
                                                   'path': sid.path()})
            time.sleep(2) #max 1 backup / second
            return [False, True]

        self.backupInfo(sid)

        if not has_errors and not list(self.config.anacrontabFiles()):
            tools.writeTimeStamp(self.config.anacronSpoolFile())

        #create last_snapshot symlink
        self.createLastSnapshotSymlink(sid)

        return [True, has_errors]

    def smartRemoveKeepAll(self,
                           snapshots,
                           min_date,
                           max_date):
        """
        Return all snapshots between ``min_date`` and ``max_date``.

        Args:
            snapshots (list):           full list of :py:class:`SID` objects
            min_date (datetime.date):   minimum date for snapshots to keep
            max_date (datetime.date):   maximum date for snapshots to keep

        Returns:
            set:                        set of snapshots that should be keept
        """
        min_id = SID(min_date, self.config)
        max_id = SID(max_date, self.config)

        logger.debug("Keep all >= %s and < %s" %(min_id, max_id), self)

        return set([sid for sid in snapshots if sid >= min_id and sid < max_id])

    def smartRemoveKeepFirst(self,
                             snapshots,
                             min_date,
                             max_date,
                             keep_healthy = False):
        """
        Return only the first snapshot between ``min_date`` and ``max_date``.

        Args:
            snapshots (list):           full list of :py:class:`SID` objects
            min_date (datetime.date):   minimum date for snapshots to keep
            max_date (datetime.date):   maximum date for snapshots to keep
            keep_healthy (bool):        return the first healthy snapshot (not
                                        marked as failed) instead of the first
                                        at all. If all snapshots failed this
                                        will again return the very first
                                        snapshot

        Returns:
            set:                        set of snapshots that should be keept
        """
        min_id = SID(min_date, self.config)
        max_id = SID(max_date, self.config)

        logger.debug("Keep first >= %s and < %s" %(min_id, max_id), self)

        for sid in snapshots:
            # try to keep the first healty snapshot
            if keep_healthy and sid.failed:
                logger.debug("Do not keep failed snapshot %s" %sid, self)
                continue
            if sid >= min_id and sid < max_id:
                return set([sid])
        # if all snapshots failed return the first snapshot
        # no matter if it has errors
        if keep_healthy:
            return self.smartRemoveKeepFirst(snapshots,
                                             min_date,
                                             max_date,
                                             keep_healthy = False)
        return set()

    def incMonth(self, date):
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
        return datetime.date(y, m, 1)

    def decMonth(self, date):
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
        return datetime.date(y, m, 1)

    def smartRemoveList(self,
                        now_full,
                        keep_all,
                        keep_one_per_day,
                        keep_one_per_week,
                        keep_one_per_month):
        """
        Get a list of old snapshots that should be removed based on configurable
        intervals.

        Args:
            now_full (datetime.datetime):   date and time when takeSnapshot was
                                            started
            keep_all (int):                 keep all snapshots for the
                                            last ``keep_all`` days
            keep_one_per_day (int):         keep one snapshot per day for the
                                            last ``keep_one_per_day`` days
            keep_one_per_week (int):        keep one snapshot per week for the
                                            last ``keep_one_per_week`` weeks
            keep_one_per_month (int):       keep one snapshot per month for the
                                            last ``keep_one_per_month`` months

        Returns:
            list:                           snapshots that should be removed
        """
        snapshots = listSnapshots(self.config)
        logger.debug("Considered: %s" %snapshots, self)
        if len(snapshots) <= 1:
            logger.debug("There is only one snapshots, so keep it", self)
            return

        if now_full is None:
            now_full = datetime.datetime.today()

        now = now_full.date()

        #keep the last snapshot
        keep = set([snapshots[0]])

        #keep all for the last keep_all days
        if keep_all > 0:
            keep |= self.smartRemoveKeepAll(snapshots,
                                            now - datetime.timedelta(days=keep_all-1),
                                            now + datetime.timedelta(days=1))

        #keep one per day for the last keep_one_per_day days
        if keep_one_per_day > 0:
            d = now
            for i in range(0, keep_one_per_day):
                keep |= self.smartRemoveKeepFirst(snapshots,
                                                  d,
                                                  d + datetime.timedelta(days=1),
                                                  keep_healthy = True)
                d -= datetime.timedelta(days=1)

        #keep one per week for the last keep_one_per_week weeks
        if keep_one_per_week > 0:
            d = now - datetime.timedelta(days = now.weekday() + 1)
            for i in range(0, keep_one_per_week):
                keep |= self.smartRemoveKeepFirst(snapshots,
                                                  d,
                                                  d + datetime.timedelta(days=8),
                                                  keep_healthy = True)
                d -= datetime.timedelta(days=7)

        #keep one per month for the last keep_one_per_month months
        if keep_one_per_month > 0:
            d1 = datetime.date(now.year, now.month, 1)
            d2 = self.incMonth(d1)
            for i in range(0, keep_one_per_month):
                keep |= self.smartRemoveKeepFirst(snapshots, d1, d2,
                                                  keep_healthy = True)
                d2 = d1
                d1 = self.decMonth(d1)

        #keep one per year for all years
        first_year = int(snapshots[-1].sid[ : 4])
        for i in range(first_year, now.year+1):
            keep |= self.smartRemoveKeepFirst(snapshots,
                                              datetime.date(i,1,1),
                                              datetime.date(i+1,1,1),
                                              keep_healthy = True)

        logger.debug("Keep snapshots: %s" %keep, self)

        del_snapshots = []
        for sid in snapshots:
            if sid in keep:
                continue

            if self.config.dontRemoveNamedSnapshots():
                if sid.name:
                    logger.debug("Keep snapshot: %s, it has a name" %sid, self)
                    continue

            del_snapshots.append(sid)
        return del_snapshots

    def smartRemove(self, del_snapshots, log = None):
        """
        Remove multiple snapshots either with
        :py:func:`Snapshots.remove` or in background on the remote host
        if mode is `ssh` or `ssh_encfs` and smart-remove in background is
        activated.

        Args:
            del_snapshots (list):   list of :py:class:`SID` that should be removed
            log (method):           callable method that will handle progress log
        """
        if not del_snapshots:
            return

        if not log:
            log = lambda x: self.setTakeSnapshotMessage(0, x)

        if self.config.snapshotsMode() in ['ssh', 'ssh_encfs'] and self.config.smartRemoveRunRemoteInBackground():
            logger.info('[smart remove] remove snapshots in background: %s'
                        %del_snapshots, self)
            lckFile = os.path.normpath(os.path.join(del_snapshots[0].path(use_mode = ['ssh', 'ssh_encfs']), os.pardir, 'smartremove.lck'))

            maxLength = self.config.sshMaxArgLength()
            if not maxLength:
                import sshMaxArg
                user_host = '%s@%s' %(self.config.sshUser(), self.config.sshHost())
                maxLength = sshMaxArg.maxArgLength(self.config)
                self.config.setSshMaxArgLength(maxLength)
                self.config.save()
                sshMaxArg.reportResult(user_host, maxLength)

            additionalChars = len(self.config.sshPrefixCmd(cmd_type = str))

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
                remote = self.rsyncRemotePath(sid.path(use_mode = ['ssh', 'ssh_encfs']), use_mode = [], quote = '\\\"')
                rsync = ' '.join(tools.rsyncRemove(self.config, run_local = False))
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
                tools.Execute(self.config.sshCommand([cmd,],
                                                     quote = False,
                                                     nice = False,
                                                     ionice = False)).run()
        else:
            logger.info("[smart remove] remove snapshots: %s"
                        %del_snapshots, self)
            for i, sid in enumerate(del_snapshots, 1):
                log(_('Smart remove') + ' %s/%s' %(i, len(del_snapshots)))
                self.remove(sid)

    def freeSpace(self, now):
        """
        Remove old snapshots on based on different rules (only if enabled).
        First rule is to remove snapshots older than X years. Next will call
        :py:func:`smartRemove` to remove snapshots based on
        configurable intervals. Third rule is to remove the oldest snapshot
        until there is enough free space. Last rule will remove the oldest
        snapshot until there are enough free inodes.

        'last_snapshot' symlink will be fixed when done.

        Args:
            now (datetime.datetime):    date and time when takeSnapshot was
                                        started
        """
        snapshots = listSnapshots(self.config, reverse = False)
        if not snapshots:
            logger.debug('No snapshots. Skip freeSpace', self)
            return

        last_snapshot = snapshots[-1]

        #remove old backups
        if self.config.removeOldSnapshotsEnabled():
            self.setTakeSnapshotMessage(0, _('Removing old snapshots'))

            oldBackupId = SID(self.config.removeOldSnapshotsDate(), self.config)
            logger.debug("Remove snapshots older than: {}".format(oldBackupId.withoutTag), self)

            while True:
                if len(snapshots) <= 1:
                    break
                if snapshots[0] >= oldBackupId:
                    break

                if self.config.dontRemoveNamedSnapshots():
                    if snapshots[0].name:
                        del snapshots[0]
                        continue

                msg = 'Remove snapshot {} because it is older than {}'
                logger.debug(msg.format(snapshots[0].withoutTag, oldBackupId.withoutTag), self)
                self.remove(snapshots[0])
                del snapshots[0]

        #smart remove
        enabled, keep_all, keep_one_per_day, keep_one_per_week, keep_one_per_month = self.config.smartRemove()
        if enabled:
            self.setTakeSnapshotMessage(0, _('Smart remove'))
            del_snapshots = self.smartRemoveList(now,
                                                 keep_all,
                                                 keep_one_per_day,
                                                 keep_one_per_week,
                                                 keep_one_per_month)
            self.smartRemove(del_snapshots)

        #try to keep min free space
        if self.config.minFreeSpaceEnabled():
            self.setTakeSnapshotMessage(0, _('Trying to keep min free space'))

            minFreeSpace = self.config.minFreeSpaceMib()

            logger.debug("Keep min free disk space: {} MiB".format(minFreeSpace), self)

            snapshots = listSnapshots(self.config, reverse = False)

            while True:
                if len(snapshots) <= 1:
                    break

                free_space = self.statFreeSpaceLocal(self.config.snapshotsFullPath())

                if free_space is None:
                    free_space = self.statFreeSpaceSsh()

                if free_space is None:
                    logger.warning('Failed to get free space. Skipping', self)
                    break

                if free_space >= minFreeSpace:
                    break

                if self.config.dontRemoveNamedSnapshots():
                    if snapshots[0].name:
                        del snapshots[0]
                        continue

                msg = "free disk space: {} MiB. Remove snapshot {}"
                logger.debug(msg.format(free_space, snapshots[0].withoutTag), self)
                self.remove(snapshots[0])
                del snapshots[0]

        #try to keep free inodes
        if self.config.minFreeInodesEnabled():
            minFreeInodes = self.config.minFreeInodes()
            self.setTakeSnapshotMessage(0, _('Trying to keep min %d%% free inodes') % minFreeInodes)
            logger.debug("Keep min {}%% free inodes".format(minFreeInodes), self)

            snapshots = listSnapshots(self.config, reverse = False)

            while True:
                if len(snapshots) <= 1:
                    break

                try:
                    info = os.statvfs(self.config.snapshotsPath())
                    free_inodes = info.f_favail
                    max_inodes  = info.f_files
                except Exception as e:
                    logger.debug('Failed to get free inodes for snapshot path %s: %s'
                                 %(self.config.snapshotsPath(), str(e)),
                                 self)
                    break

                if free_inodes >= max_inodes * (minFreeInodes / 100.0):
                    break

                if self.config.dontRemoveNamedSnapshots():
                    if snapshots[0].name:
                        del snapshots[0]
                        continue

                logger.debug("free inodes: %.2f%%. Remove snapshot %s"
                            %((100.0 / max_inodes * free_inodes), snapshots[0].withoutTag),
                            self)
                self.remove(snapshots[0])
                del snapshots[0]

        #set correct last snapshot again
        if last_snapshot is not snapshots[-1]:
            self.createLastSnapshotSymlink(snapshots[-1])

    def statFreeSpaceLocal(self, path):
        """
        Get free space on filsystem containing ``path`` in MiB using
        :py:func:`os.statvfs()`. Depending on remote SFTP server this might fail
        on sshfs mounted shares.

        Args:
            path (str): full path

        Returns:
            int         free space in MiB
        """
        try:
            info = os.statvfs(path)
            if info.f_blocks != info.f_bavail:
                return info.f_frsize * info.f_bavail // (1024 * 1024)
        except Exception as e:
            logger.debug('Failed to get free space for %s: %s'
                         %(path, str(e)),
                         self)
        logger.warning('Failed to stat snapshot path', self)

    def statFreeSpaceSsh(self):
        """
        Get free space on remote filsystem in MiB. This will call ``df`` on
        remote host and parse its output.

        Returns:
            int         free space in MiB
        """
        if self.config.snapshotsMode() not in ('ssh', 'ssh_encfs'):
            return None

        snapshots_path_ssh = self.config.sshSnapshotsFullPath()
        if not len(snapshots_path_ssh):
            snapshots_path_ssh = './'
        cmd = self.config.sshCommand(['df', snapshots_path_ssh],
                                     nice = False,
                                     ionice = False)

        df = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        output = df.communicate()[0]
        #Filesystem     1K-blocks      Used Available Use% Mounted on
        #/tmp           127266564 115596412   5182296  96% /
        #                                     ^^^^^^^
        for line in output.split(b'\n'):
            m = re.match(b'^.*?\s+\d+\s+\d+\s+(\d+)\s+\d+%', line, re.M)
            if m:
                return int(int(m.group(1)) / 1024)
        logger.warning('Failed to get free space on remote', self)

    def filter(self,
               base_sid,
               base_path,
               snapshotsList,
               list_diff_only  = False,
               flag_deep_check = False,
               list_equal_to = ''):
        """
        Filter snapshots from ``snapshotsList`` based on whether ``base_path``
        file is included and optional if the snapshot is unique or equal to
        ``list_equal_to``.

        Args:
            base_sid (SID):         snapshot ID that contained the original
                                    file ``base_path``
            base_path (str):        path to file on root filesystem.
            snapshotsList (list):  List of :py:class:`SID` objects that should
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
        snapshotsFiltered = []

        base_full_path = base_sid.pathBackup(base_path)
        if not os.path.lexists(base_full_path):
            return []

        allSnapshotsList = [RootSnapshot(self.config)]
        allSnapshotsList.extend(snapshotsList)

        #links
        if os.path.islink(base_full_path):
            targets = []

            for sid in allSnapshotsList:
                path = sid.pathBackup(base_path)

                if os.path.lexists(path) and os.path.islink(path):
                    if list_diff_only:
                        target = os.readlink(path)
                        if target in targets:
                            continue
                        targets.append(target)
                    snapshotsFiltered.append(sid)

            return snapshotsFiltered

        #directories
        if os.path.isdir(base_full_path):
            for sid in allSnapshotsList:
                path = sid.pathBackup(base_path)

                if os.path.exists(path) and not os.path.islink(path) and os.path.isdir(path):
                    snapshotsFiltered.append(sid)

            return snapshotsFiltered

        #files
        if not list_diff_only and not list_equal_to:
            for sid in allSnapshotsList:
                path = sid.pathBackup(base_path)

                if os.path.exists(path) and not os.path.islink(path) and os.path.isfile(path):
                    snapshotsFiltered.append(sid)

            return snapshotsFiltered

        # check for duplicates
        uniqueness = tools.UniquenessSet(flag_deep_check, follow_symlink = False, list_equal_to = list_equal_to)
        for sid in allSnapshotsList:
            path = sid.pathBackup(base_path)
            if os.path.exists(path) and not os.path.islink(path) and os.path.isfile(path) and uniqueness.check(path):
                snapshotsFiltered.append(sid)

        return snapshotsFiltered

    #TODO: move this to config.Config
    def rsyncRemotePath(self, path, use_mode = ['ssh', 'ssh_encfs'], quote = '"'):
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
        mode = self.config.snapshotsMode()
        if mode in ['ssh', 'ssh_encfs'] and mode in use_mode:
            user = self.config.sshUser()
            host = tools.escapeIPv6Address(self.config.sshHost())
            return '%(u)s@%(h)s:%(q)s%(p)s%(q)s' %{'u': user,
                                                   'h': host,
                                                   'q': quote,
                                                   'p': path}
        else:
            return path

    def deletePath(self, sid, path):
        """
        Delete ``path`` and all files and folder inside in snapshot ``sid``.

        Args:
            sid (SID):  snapshot ID in which ``path`` should be deleted
            path (str): path to delete
        """
        def errorHandler(fn, path, excinfo):
            """
            Error handler for :py:func:`deletePath`. This will fix permissions
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
            shutil.rmtree(full_path, onerror = errorHandler)
        else:
            st = os.stat(full_path)
            os.chmod(full_path, st.st_mode | stat.S_IWUSR)
            os.remove(full_path)
        os.chmod(dirname, dir_st.st_mode)

    def createLastSnapshotSymlink(self, sid):
        """
        Create symlink 'last_snapshot' to snapshot ``sid``

        Args:
            sid (SID):  snapshot that should be linked.

        Returns:
            bool:       ``True`` if successful
        """
        if sid is None:
            return
        symlink = self.config.lastSnapshotSymlink()
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
        Block :py:func:`backup` from other profiles or users
        and run them serialized
        """
        if self.config.globalFlock():
            logger.debug('Set flock %s' %self.GLOBAL_FLOCK, self)
            self.flock = open(self.GLOBAL_FLOCK, 'w')
            fcntl.flock(self.flock, fcntl.LOCK_EX)
            #make it rw by all if that's not already done.
            perms = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | \
                    stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
            s = os.fstat(self.flock.fileno())
            if not s.st_mode & perms == perms:
                logger.debug('Set flock permissions %s' %self.GLOBAL_FLOCK, self)
                os.fchmod(self.flock.fileno(), perms)

    def flockRelease(self):
        """
        Release lock so other snapshots can continue
        """
        if self.flock:
            logger.debug('Release flock %s' %self.GLOBAL_FLOCK, self)
            fcntl.fcntl(self.flock, fcntl.LOCK_UN)
            self.flock.close()
        self.flock = None

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
        ret.extend(['--exclude=' + i for i in (encode.exclude(self.config.snapshotsPath()),
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
            excludeFolders = self.config.exclude()

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
            includeFolders = self.config.include()

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
                folder = os.path.split(folder)[0]

            while True:
                if len(folder) <= 1:
                    break
                items1.add('--include={}/'.format(folder))
                folder = os.path.split(folder)[0]

        return (items1, items2)

class FileInfoDict(dict):
    """
    A :py:class:`dict` that maps a path (as :py:class:`bytes`) to a
    tuple (:py:class:`int`, :py:class:`bytes`, :py:class:`bytes`).
    """
    def __init__(self):
        # default permissions for /
        # only used if fileinfo.bz2 does not contain a value for /
        # when it was created with version <= 1.1.12
        # bugfix for https://github.com/bit-team/backintime/issues/708
        self[b'/'] = (16877, b'root', b'root')

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
        self.profileID = cfg.currentProfile()
        self.isRoot = False

        if isinstance(date, datetime.datetime):
            self.sid = '-'.join((date.strftime('%Y%m%d-%H%M%S'), self.config.tag(self.profileID)))
            self.date = date
        elif isinstance(date, datetime.date):
            self.sid = '-'.join((date.strftime('%Y%m%d-000000'), self.config.tag(self.profileID)))
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

    def __hash__(self):
        return hash(self.sid + self.profileID)

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
        current_mode = self.config.snapshotsMode(self.profileID)
        if 'ssh' in use_mode and current_mode == 'ssh':
            return os.path.join(self.config.sshSnapshotsFullPath(self.profileID),
                                self.sid, *path)
        if 'ssh_encfs' in use_mode and current_mode == 'ssh_encfs':
            ret = os.path.join(self.config.sshSnapshotsFullPath(self.profileID),
                               self.sid, *path)
            return self.config.ENCODE.remote(ret)
        return os.path.join(self.config.snapshotsFullPath(self.profileID),
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
        if not os.path.isdir(self.config.snapshotsFullPath(self.profileID)):
            logger.error('Snapshots path {} doesn\'t exist. Unable to make dirs for snapshot ID {}'.format(
                         self.config.snapshotsFullPath(self.profileID), self.sid),
                         self)
            return False

        return tools.makeDirs(self.pathBackup(*path))

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

        self.makeWritable()
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
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getatime(info)))
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
            self.makeWritable()
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
        except (FileNotFoundError, PermissionError) as e:
            logger.error('Failed to load {} from snapshot {}: {}'.format(
                         self.FILEINFO, self.sid, str(e)),
                         self)
        return d

    @fileInfo.setter
    def fileInfo(self, d):
        assert isinstance(d, FileInfoDict), 'd is not FileInfoDict type: {}'.format(d)
        try:
            with bz2.BZ2File(self.path(self.FILEINFO), 'wb') as f:
                for path, info in d.items():
                    f.write(b' '.join((str(info[0]).encode('utf-8', 'replace'),
                                       info[1],
                                       info[2],
                                       path))
                                       + b'\n')
        except PermissionError as e:
            logger.error('Failed to write {}: {}'.format(self.FILEINFO, str(e)))

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
            with bz2.BZ2File(logFile, 'rb') as f:
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

    def makeWritable(self):
        """
        Make the snapshot path writable so we can change files inside

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
        self.profileID = cfg.currentProfile()
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
            try:
                with open(flag, 'wt') as f:
                    pass
            except Exception as e:
                logger.error("Failed to set 'save_to_continue' flag: %s" %str(e))
        elif os.path.exists(flag):
            try:
                os.remove(flag)
            except Exception as e:
                logger.error("Failed to remove 'save_to_continue' flag: %s" %str(e))

    @property
    def hasChanges(self):
        """
        Check if there where changes in previous sessions.

        Returns:
            bool:   ``True`` if there where changes
        """
        log = snapshotlog.SnapshotLog(self.config, self.profileID)
        c = re.compile(r'^\[C\] ')
        for line in log.get(mode = snapshotlog.LogFilter.CHANGES):
            if c.match(line):
                return True
        return False

class RootSnapshot(GenericNonSnapshot):
    """
    Snapshot ID for the filesystem root folder ('/')

    Args:
        cfg (config.Config):    current config
    """
    def __init__(self, cfg):
        self.config = cfg
        self.profileID = cfg.currentProfile()
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
        current_mode = self.config.snapshotsMode(self.profileID)
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
    path = cfg.snapshotsFullPath()
    if not os.path.exists(path):
        return None
    for item in os.listdir(path):
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

#commented out when implementing config.Config as a singleton

# commented out when implementing config.Config as a singleton
# if __name__ == '__main__':
#     config = config.Config()
#     snapshots = Snapshots(config)
#     snapshots.backup()
