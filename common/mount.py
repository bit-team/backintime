#    Copyright (C) 2012-2016 Germar Reitze, Taylor Raack
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
import subprocess
import json
import gettext
from zlib import crc32
from time import sleep

import config
import logger
import tools
import password
from exceptions import MountException, HashCollision

_=gettext.gettext

class Mount(object):
    def __init__(self, cfg = None, profile_id = None, tmp_mount = False, parent = None, read_only = True):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()

        self.profile_id = profile_id
        if self.profile_id is None:
            self.profile_id = self.config.get_current_profile()

        self.tmp_mount = tmp_mount
        self.parent = parent
        self.read_only = read_only

        if self.config.get_password_use_cache(self.profile_id):
            pw_cache = password.Password_Cache(self.config)
            action = None
            running = pw_cache.status()
            if not running:
                logger.debug('pw-cache is not running', self)
                action = 'start'
            if running and not pw_cache.check_version():
                logger.debug('pw-cache is running but is an old version', self)
                action = 'restart'
            bit = tools.which('backintime')
            if not action is None and len(bit):
                cmd = [bit, 'pw-cache', action]
                logger.debug('Call command: %s'
                             %' '.join(cmd), self)
                proc = subprocess.Popen(cmd,
                                        stdout = open(os.devnull, 'w'),
                                        stderr = open(os.devnull, 'w'))
                if proc.returncode:
                    logger.error('Failed to %s pw-cache: %s'
                                 %(action, proc.returncode),
                                 self)
                    pass

    def mount(self, mode = None, check = True, plugins = True, **kwargs):
        if plugins:
            self.config.PLUGIN_MANAGER.load_plugins(cfg = self.config)
            self.config.PLUGIN_MANAGER.do_mount()
        if mode is None:
            mode = self.config.get_snapshots_mode(self.profile_id)

        if self.config.SNAPSHOT_MODES[mode][0] is None:
            #mode doesn't need to mount
            return 'local'
        else:
            while True:
                try:
                    mounttools = self.config.SNAPSHOT_MODES[mode][0]
                    tools = mounttools(cfg = self.config, profile_id = self.profile_id,
                                       tmp_mount = self.tmp_mount, mode = mode,
                                       parent = self.parent, read_only = self.read_only, **kwargs)
                    return tools.mount(check = check)
                except HashCollision as ex:
                    logger.warning(str(ex), self)
                    del tools
                    check = False
                    continue
                break

    def umount(self, hash_id = None, plugins = True):
        if plugins:
            self.config.PLUGIN_MANAGER.load_plugins(cfg = self.config)
            self.config.PLUGIN_MANAGER.do_unmount()
        if hash_id is None:
            hash_id = self.config.current_hash_id
        if hash_id == 'local':
            #mode doesn't need to umount
            return
        else:
            umount_info = os.path.join(self.config._LOCAL_MOUNT_ROOT, hash_id, 'umount')
            with open(umount_info, 'r') as f:
                data_string = f.read()
                f.close()
            kwargs = json.loads(data_string)
            mode = kwargs.pop('mode')
            mounttools = self.config.SNAPSHOT_MODES[mode][0]
            tools = mounttools(cfg = self.config, profile_id = self.profile_id,
                               tmp_mount = self.tmp_mount, mode = mode,
                               hash_id = hash_id, parent = self.parent, **kwargs)
            tools.umount()

    def pre_mount_check(self, mode = None, first_run = False, **kwargs):
        """
        called by SettingsDialog.save_profile() to check
        if settings are correct before saving
        """
        if mode is None:
            mode = self.config.get_snapshots_mode(self.profile_id)

        if self.config.SNAPSHOT_MODES[mode][0] is None:
            #mode doesn't need to mount
            return True
        else:
            mounttools = self.config.SNAPSHOT_MODES[mode][0]
            tools = mounttools(cfg = self.config, profile_id = self.profile_id,
                               tmp_mount = self.tmp_mount, mode = mode,
                               parent = self.parent, read_only = self.read_only, **kwargs)
            return tools.pre_mount_check(first_run)

    def remount(self, new_profile_id, mode = None, hash_id = None, **kwargs):
        """
        mode            <= new profile
        kwargs          <= new profile
        hash_id         <= old profile
        self.profile_id <= old profile
        """
        if mode is None:
            mode = self.config.get_snapshots_mode(new_profile_id)
        if hash_id is None:
            hash_id = self.config.current_hash_id

        if self.config.SNAPSHOT_MODES[mode][0] is None:
            #new profile don't need to mount.
            self.umount(hash_id = hash_id, plugins = False)
            return 'local'

        if hash_id == 'local':
            #old profile don't need to umount.
            self.profile_id = new_profile_id
            return self.mount(mode = mode, plugins = False, **kwargs)

        mounttools = self.config.SNAPSHOT_MODES[mode][0]
        tools = mounttools(cfg = self.config, profile_id = new_profile_id,
                           tmp_mount = self.tmp_mount, mode = mode,
                           parent = self.parent, read_only = self.read_only, **kwargs)
        if tools.compare_remount(hash_id):
            #profiles uses the same settings. just swap the symlinks
            tools.remove_symlink(profile_id = self.profile_id)
            tools.set_symlink(profile_id = new_profile_id, hash_id = hash_id)
            return hash_id
        else:
            #profiles are different. we need to umount and mount again
            self.umount(hash_id = hash_id, plugins = False)
            self.profile_id = new_profile_id
            return self.mount(mode = mode, plugins = False, **kwargs)

class MountControl(object):
    def __init__(self):
        self.local_host = self.config.get_host()
        self.local_user = self.config.get_user()
        self.pid = self.config.get_pid()

    def set_default_args(self):
        #self.destination should contain all arguments that are nessesary for mount.
        args = list(self.all_kwargs.keys())
        self.destination = '%s:' % self.all_kwargs['mode']
        args.remove('mode')
        args.sort()
        for arg in args:
            self.destination += ' %s' % self.all_kwargs[arg]

        #unique id for every different mount settings. Similar settings even in
        #different profiles will generate the same hash_id and so share the same
        #mountpoint
        if self.hash_id is None:
            self.hash_id = self.hash(self.destination)

        self.mount_root = self.config._LOCAL_MOUNT_ROOT
        self.snapshots_path = self.config.get_snapshots_path(profile_id = self.profile_id, mode = self.mode, tmp_mount = self.tmp_mount)

        self.hash_id_path = self.get_hash_id_path()
        self.mountpoint = self.get_mountpoint()
        self.lock_path = self.get_lock_path()
        self.umount_info = self.get_umount_info()

    def mount(self, check = True):
        self.create_mountstructure()
        self.mountprocess_lock_acquire()
        try:
            if self.is_mounted():
                if not self.compare_umount_info():
                    #We probably have a hash collision
                    self.config.increment_hash_collision()
                    raise HashCollision( _('Hash collision occurred in hash_id %s. Incrementing global value hash_collision and try again.') % self.hash_id)
                logger.info('Mountpoint %s is already mounted' %self.mountpoint, self)
            else:
                if check:
                    self.pre_mount_check()
                self._mount()
                self.post_mount_check()
                logger.info('mount %s on %s'
                            %(self.log_command, self.mountpoint),
                            self)
                self.write_umount_info()
        except Exception:
            raise
        else:
            self.set_mount_lock()
            self.set_symlink()
        finally:
            self.mountprocess_lock_release()
        return self.hash_id

    def umount(self):
        self.mountprocess_lock_acquire()
        try:
            if not os.path.isdir(self.hash_id_path):
                logger.info('Mountpoint %s does not exist.' % self.hash_id_path, self)
            else:
                if not self.is_mounted():
                    logger.info('Mountpoint %s is not mounted' % self.hash_id_path, self)
                else:
                    if self.check_mount_lock():
                        logger.info('Mountpoint %s still in use. Keep mounted' % self.mountpoint, self)
                    else:
                        self.pre_umount_check()
                        self._umount()
                        self.post_umount_check()
                        if os.listdir(self.mountpoint):
                            logger.warning('Mountpoint %s not empty after unmount' %self.mountpoint, self)
                        else:
                            logger.info('unmount %s from %s'
                                        %(self.log_command, self.mountpoint),
                                        self)
        except Exception:
            raise
        else:
            self.del_mount_lock()
            self.remove_symlink()
        finally:
            self.mountprocess_lock_release()

    def is_mounted(self):
        """
        return True if path is is already mounted
        """
        if os.path.ismount(self.mountpoint):
            return True
        else:
            if os.listdir(self.mountpoint):
                raise MountException( _('mountpoint %s not empty.') % self.mountpoint)
            return False

    def create_mountstructure(self):
        """
        folder structure in ~/.local/share/backintime/mnt/::

            <pid>.lock              <=  mountprocess lock that will prevent
                                        different processes modifying mountpoints
                                        at one time
            <hash_id>/              <=  will be shared by all profiles with the
                                        same mount settings
                      mountpoint/   <=  real mountpoint
                      umount        <=  json file with all nessesary args
                                        for unmount
                      locks/        <=  for each process you have a
                                        <pid>.lock file
            <profile id>_<pid>/     <=  sym-link to the right path. return by
                                        config.get_snapshots_path
                                        (can be ../mnt/<hash_id>/mount_point
                                        for ssh or
                                        ../mnt/<hash_id>/<HOST>/<SHARE> for
                                        fusesmb ...)
            tmp_<profile id>_<pid>/ <=  sym-link for testing mountpoints in
                                        settingsdialog
        
        """
        self.mkdir(self.mount_root, 0o700)
        self.mkdir(self.hash_id_path, 0o700)
        self.mkdir(self.mountpoint, 0o700)
        self.mkdir(self.lock_path, 0o700)

    def mkdir(self, path, mode = 0o777, force_chmod = False):
        if not os.path.isdir(path):
            os.mkdir(path, mode)
            if force_chmod:
                #hack: debian and ubuntu won't set go+w on mkdir in tmp
                os.chmod(path, mode)

    def mountprocess_lock_acquire(self, timeout = 60):
        """
        block while an other process is mounting or unmounting
        """
        lock_path = self.mount_root
        lock_suffix = '.lock'
        lock = os.path.join(lock_path, self.pid + lock_suffix)
        count = 0
        while self.check_locks(lock_path, lock_suffix):
            count += 1
            if count == timeout:
                raise MountException( _('Mountprocess lock timeout') )
            sleep(1)

        logger.debug('Acquire mountprocess lock %s'
                     %lock, self)
        with open(lock, 'w') as f:
            f.write(self.pid)

    def mountprocess_lock_release(self):
        lock_path = self.mount_root
        lock_suffix = '.lock'
        lock = os.path.join(lock_path, self.pid + lock_suffix)
        logger.debug('Release mountprocess lock %s'
                     %lock, self)
        if os.path.exists(lock):
            os.remove(lock)

    def set_mount_lock(self):
        """
        lock mount for this process
        """
        if self.tmp_mount:
            lock_suffix = '.tmp.lock'
        else:
            lock_suffix = '.lock'
        lock = os.path.join(self.lock_path, self.pid + lock_suffix)
        logger.debug('Set mount lock %s'
                     %lock, self)
        with open(lock, 'w') as f:
            f.write(self.pid)

    def check_mount_lock(self):
        """
        return True if mount is locked by other processes
        """
        lock_suffix = '.lock'
        return self.check_locks(self.lock_path, lock_suffix)

    def del_mount_lock(self):
        """
        remove mount lock for this process
        """
        if self.tmp_mount:
            lock_suffix = '.tmp.lock'
        else:
            lock_suffix = '.lock'
        lock = os.path.join(self.lock_path, self.pid + lock_suffix)
        if os.path.exists(lock):
            logger.debug('Remove mount lock %s'
                         %lock, self)
            os.remove(lock)

    def check_process_alive(self, pid):
        """
        check if process is still alive
        """
        if os.path.exists(os.path.join('/proc', pid)):
            return True
        return False

    def check_locks(self, path, lock_suffix):
        """
        return True if there are active locks
        """
        for f in os.listdir(path):
            if not f[-len(lock_suffix):] == lock_suffix:
                continue
            is_tmp = False
            if os.path.basename(f)[-len(lock_suffix)-len('.tmp'):-len(lock_suffix)] == '.tmp':
                is_tmp = True
            if is_tmp:
                lock_pid = os.path.basename(f)[:-len('.tmp')-len(lock_suffix)]
            else:
                lock_pid = os.path.basename(f)[:-len(lock_suffix)]
            if lock_pid == self.pid:
                if is_tmp == self.tmp_mount:
                    continue
            if self.check_process_alive(lock_pid):
                return True
            else:
                logger.debug('Remove old and invalid lock %s'
                             %f, self)
                #clean up
                os.remove(os.path.join(path, f))
                for symlink in os.listdir(self.mount_root):
                    if symlink.endswith('_%s' % lock_pid):
                        os.remove(os.path.join(self.mount_root, symlink))
        return False

    def setattr_kwargs(self, arg, default, store = True, **kwargs):
        """
        if kwargs[arg] exist set self.<arg> to kwargs[arg]
        else set self.<arg> to default which should be the value from config
        """
        if arg in kwargs:
            value = kwargs[arg]
        else:
            value = default
        setattr(self, arg, value)
        if store:
            #make dictionary with all used args for umount
            self.all_kwargs[arg] = value

    def write_umount_info(self):
        """
        dump dictionary self.all_kwargs to umount_info file
        """
        data_string = json.dumps(self.all_kwargs)
        with open(self.umount_info, 'w') as f:
            f.write(data_string)
            f.close

    def read_umount_info(self, umount_info = None):
        """
        load dictionary kwargs from umount_info file
        """
        if umount_info is None:
            umount_info = self.umount_info
        with open(umount_info, 'r') as f:
            data_string = f.read()
            f.close()
        return json.loads(data_string)

    def compare_umount_info(self, umount_info = None):
        """
        just in case of hash collisions in <hash_id> we compare self.all_kwargs
        with the old saved in umount_info file.
        return True if both are identical
        """
        #run self.all_kwargs through json first
        current_kwargs = json.loads(json.dumps(self.all_kwargs))
        saved_kwargs = self.read_umount_info(umount_info)
        if not len(current_kwargs) == len(saved_kwargs):
            return False
        for arg in list(current_kwargs.keys()):
            if not arg in list(saved_kwargs.keys()):
                return False
            if not current_kwargs[arg] == saved_kwargs[arg]:
                return False
        return True

    def compare_remount(self, old_hash_id):
        """
        return True if profiles are identiacal and we don't need to remount
        """
        if old_hash_id == self.hash_id:
            return self.compare_umount_info(self.get_umount_info(old_hash_id))
        return False

    def set_symlink(self, profile_id = None, hash_id = None, tmp_mount = None):
        if not self.symlink:
            return
        if profile_id is None:
            profile_id = self.profile_id
        if hash_id is None:
            hash_id = self.hash_id
        if tmp_mount is None:
            tmp_mount = self.tmp_mount
        dst = self.config.get_snapshots_path(profile_id = profile_id, mode = self.mode, tmp_mount = tmp_mount)
        mountpoint = self.get_mountpoint(hash_id)
        if self.symlink_subfolder is None:
            src = mountpoint
        else:
            src = os.path.join(mountpoint, self.symlink_subfolder)
        if os.path.exists(dst):
            os.remove(dst)
        os.symlink(src, dst)

    def remove_symlink(self, profile_id = None, tmp_mount = None):
        if not self.symlink:
            return
        if profile_id is None:
            profile_id = self.profile_id
        if tmp_mount is None:
            tmp_mount = self.tmp_mount
        os.remove(self.config.get_snapshots_path(profile_id = profile_id, mode = self.mode, tmp_mount = tmp_mount))

    def hash(self, s):
        """
        return a hex crc32 hash of s
        """
        return('%X' % (crc32(s.encode()) & 0xFFFFFFFF))

    def get_hash_id_path(self, hash_id = None):
        if hash_id is None:
            hash_id = self.hash_id
        return os.path.join(self.mount_root, self.hash_id)

    def get_mountpoint(self, hash_id = None):
        return os.path.join(self.get_hash_id_path(hash_id), 'mountpoint')

    def get_lock_path(self, hash_id = None):
        return os.path.join(self.get_hash_id_path(hash_id), 'locks')

    def get_umount_info(self, hash_id = None):
        return os.path.join(self.get_hash_id_path(hash_id), 'umount')
