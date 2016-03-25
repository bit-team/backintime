#    Copyright (C) 2012-2016 Germar Reitze
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
    """
    This is the high-level mount API. This will handle mount, umount, remount
    and checks on the low-level :py:class:`MountControl` subclass backends for
    BackInTime.

    If ``cfg`` is ``None`` this will load the default config. If ``profile_id``
    is ``None`` it will use
    :py:func:`configfile.ConfigFileWithProfiles.get_current_profile`.

    If the current profile uses Password-Cache and the Password-Cache is not
    running this will try to start it.

    Args:
        cfg (config.Config):    current config
        profile_id (str):       profile ID that should be used
        tmp_mount (bool):       if ``True`` mount to a temporary destination
        parent (QWidget):       parent widget for QDialogs or ``None`` if there
                                is no parent
    """
    def __init__(self,
                 cfg = None,
                 profile_id = None,
                 tmp_mount = False,
                 parent = None):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()

        self.profile_id = profile_id
        if self.profile_id is None:
            self.profile_id = self.config.get_current_profile()

        self.tmp_mount = tmp_mount
        self.parent = parent

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
                                        stdout = subprocess.DEVNULL,
                                        stderr = subprocess.DEVNULL)
                if proc.returncode:
                    logger.error('Failed to %s pw-cache: %s'
                                 %(action, proc.returncode),
                                 self)
                    pass

    def mount(self, mode = None, check = True, plugins = True, **kwargs):
        """
        High-level `mount`. Check if the selected ``mode`` need to be mounted,
        select the low-level backend and mount it.

        Args:
            mode (str):     mode to use. One of 'local', 'ssh', 'local_encfs' or
                            'ssh_encfs'
            check (bool):   if ``True`` run
                            :py:func:`MountControl.pre_mount_check` before
                            mounting
            plugins (bool): if ``True`` run
                            :py:func:`pluginmanager.PluginManager.do_mount`
                            before mount
            **kwargs:       keyword arguments paste to low-level
                            :py:class:`MountControl` subclass backend

        Returns:
            str:            Hash ID used as mountpoint

        Raises:
            exceptions.MountException:
                            if a check failed
            exceptions.HashCollision:
                            if Hash ID was used before but umount info wasn't
                            identical
        """
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
                    backend = mounttools(cfg = self.config,
                                         profile_id = self.profile_id,
                                         tmp_mount = self.tmp_mount,
                                         mode = mode,
                                         parent = self.parent,
                                         **kwargs)
                    return backend.mount(check = check)
                except HashCollision as ex:
                    logger.warning(str(ex), self)
                    del backend
                    check = False
                    continue
                break

    def umount(self, hash_id = None, plugins = True):
        """
        High-level `unmount`. Unmount the low-level backend. This will read
        unmount infos written next to the mountpoint identified by ``hash_id``
        and unmount it.

        Args:
            hash_id (bool): Hash ID used as mountpoint before that should get
                            unmounted
            plugins (bool): if ``True`` run
                            :py:func:`pluginmanager.PluginManager.do_unmount`
                            before unmount

        Raises:
            exceptions.MountException:
                            if a check failed
        """
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
            backend = mounttools(cfg = self.config,
                                 profile_id = self.profile_id,
                                 tmp_mount = self.tmp_mount,
                                 mode = mode,
                                 hash_id = hash_id,
                                 parent = self.parent,
                                 **kwargs)
            backend.umount()

    def pre_mount_check(self, mode = None, first_run = False, **kwargs):
        """
        High-level check. Run :py:func:`MountControl.pre_mount_check` to check
        if all conditions for :py:func:`Mount.mount` are set.

        Should be called with ``first_run = True`` to check if new settings are
        correct before saving them.

        Args:
            mode (str):         mode to use. One of 'local', 'ssh',
                                'local_encfs' or 'ssh_encfs'
            first_run (bool):   run intense checks that only need to run after
                                changing settings but not every time before
                                mounting
            **kwargs:           keyword arguments paste to low-level
                                :py:class:`MountControl` subclass backend

        Returns:
            bool:               ``True`` if all checks where okay

        Raises:
            exceptions.MountException:
                                if a check failed
        """
        if mode is None:
            mode = self.config.get_snapshots_mode(self.profile_id)

        if self.config.SNAPSHOT_MODES[mode][0] is None:
            #mode doesn't need to mount
            return True
        else:
            mounttools = self.config.SNAPSHOT_MODES[mode][0]
            backend = mounttools(cfg = self.config,
                                 profile_id = self.profile_id,
                                 tmp_mount = self.tmp_mount,
                                 mode = mode,
                                 parent = self.parent,
                                 **kwargs)
            return backend.pre_mount_check(first_run)

    def remount(self, new_profile_id, mode = None, hash_id = None, **kwargs):
        """
        High-level `remount`. Unmount the old profile presented by ``hash_id``
        and mount new profile ``new_profile_id`` with mode ``mode``. If old and
        new mounts are the same just add new symlinks and keep the mount.

        Args map to profiles::

            new_profile_id          <= new profile
            mode                    <= new profile
            kwargs                  <= new profile
            hash_id                 <= old profile
            self.profile_id         <= old profile

        Args:
            new_profile_id (str):   Profile ID that should get mounted
            mode (str):             mode to use for new mount. One of 'local',
                                    'ssh', 'local_encfs' or 'ssh_encfs'
            hash_id (str):          Hash ID used as mountpoint on the old mount,
                                    that should get unmounted
            **kwargs:               keyword arguments paste to low-level
                                    :py:class:`MountControl` subclass backend
                                    for the new mount

        Returns:
            str:                    Hash ID used as mountpoint

        Raises:
            exceptions.MountException:
                                    if a check failed
            exceptions.HashCollision:
                                    if Hash ID was used before but umount info
                                    wasn't identical
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
        backend = mounttools(cfg = self.config,
                             profile_id = new_profile_id,
                             tmp_mount = self.tmp_mount,
                             mode = mode,
                             parent = self.parent,
                             **kwargs)
        if backend.compare_remount(hash_id):
            #profiles uses the same settings. just swap the symlinks
            backend.remove_symlink(profile_id = self.profile_id)
            backend.set_symlink(profile_id = new_profile_id, hash_id = hash_id)
            return hash_id
        else:
            #profiles are different. we need to umount and mount again
            self.umount(hash_id = hash_id, plugins = False)
            self.profile_id = new_profile_id
            return self.mount(mode = mode, plugins = False, **kwargs)

class MountControl(object):
    """
    This is the low-level mount API. This should be subclassed by backends.

    Subclasses should have it's own ``__init__`` but **must** also call the
    inherited ``__init__``.

    You **must** overwrite methods:\n
        :py:func:`MountControl._mount`

    You **can** overwrite methods:\n
        :py:func:`MountControl._umount`\n
        :py:func:`MountControl.pre_mount_check`\n
        :py:func:`MountControl.post_mount_check`\n
        :py:func:`MountControl.pre_umount_check`\n
        :py:func:`MountControl.post_umount_check`

    These arguments **must** be defined in ``self`` namespace by
    subclassing ``__init__`` method:\n
        mountproc (str):        process used to mount\n
        log_command (str):      shortened form of mount command used in logs\n
        symlink_subfolder (str):mountpoint-subfolder which should be linked\n

    Args:
        cfg (config.Config):    current config
        profile_id (str):       profile ID that should be used
        hash_id (str):          ???
        tmp_mount (bool):       if ``True`` mount to a temporary destination
        parent (QWidget):       parent widget for QDialogs or ``None`` if there
                                is no parent
        symlink (bool):         if ``True`` set symlink to mountpoint
        mode (str):             one of ``local``, ``local_encfs``, ``ssh`` or
                                ``ssh_encfs``
        hash_collision (int):   global value used to prevent hash collisions on
                                mountpoints
        read_only (bool):       if ``True`` mount source read-only
    """

    CHECK_FUSE_GROUP = False

    def __init__(self,
                 cfg = None,
                 profile_id = None,
                 hash_id = None,
                 tmp_mount = False,
                 parent = None,
                 symlink = True,
                 *args,
                 **kwargs):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()

        self.profile_id = profile_id
        if self.profile_id is None:
            self.profile_id = self.config.get_current_profile()

        self.tmp_mount = tmp_mount
        self.hash_id = hash_id
        self.parent = parent
        self.symlink = symlink

        self.local_host = self.config.get_host()
        self.local_user = self.config.get_user()
        self.pid = self.config.get_pid()

        self.all_kwargs = {}

        self.setattr_kwargs('mode', self.config.get_snapshots_mode(self.profile_id), **kwargs)
        self.setattr_kwargs('hash_collision', self.config.get_hash_collision(), **kwargs)

    def set_default_args(self):
        """
        Set some arguments which are necessary for all backends.
        ``self.all_kwargs`` need to be filled through :py:func:`setattr_kwargs`
        before calling this.
        """
        #self.destination should contain all arguments that are nessesary for
        #mount.
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
        self.snapshots_path = self.config.get_snapshots_path(profile_id = self.profile_id,
                                                             mode = self.mode,
                                                             tmp_mount = self.tmp_mount)

        self.hash_id_path = self.get_hash_id_path()
        self.mountpoint = self.get_mountpoint()
        self.lock_path = self.get_lock_path()
        self.umount_info = self.get_umount_info()

    def mount(self, check = True):
        """
        Low-level `mount`. Set mountprocess lock and prepair mount, run checks
        and than call :py:func:`_mount` for the subclassed backend. Finally set
        mount lock and symlink and release mountprocess lock.

        Args:
            check (bool):   if ``True`` run :py:func:`pre_mount_check` before
                            mounting

        Returns:
            str:            Hash ID used as mountpoint

        Raises:
            exceptions.MountException:
                            if a check failed
            exceptions.HashCollision:
                            if Hash ID was used before but umount info wasn't
                            identical
        """
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
        """
        Low-level `umount`. Set mountprocess lock, run umount checks and call
        :py:func:`_umount` for the subclassed backend. Finally release
        mount lock, remove symlink and release mountprocess lock.

        Raises:
            exceptions.MountException:  if a check failed
        """
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

    def _mount(self):
        """
        Backend mount method. This **must** be overwritten in the backend which
        subclasses :py:class:`MountControl`.
        """
        raise NotImplementedError('_mount need to be overwritten in backend')

    def _umount(self):
        """
        Unmount with ``fusermount -u`` for fuse based backends. This **can** be
        overwritten by backends which subclasses :py:class:`MountControl`.

        Raises:
            exceptions.MountException:  if unmount failed
        """
        try:
            subprocess.check_call(['fusermount', '-u', self.mountpoint])
        except subprocess.CalledProcessError:
            raise MountException( _('Can\'t unmount %(proc)s from %(mountpoint)s')
                                  %{'proc': self.mountproc,
                                    'mountpoint': self.mountpoint})

    def pre_mount_check(self, first_run = False):
        """
        Check what ever conditions must be given for the mount to be done
        successful. This **can** be overwritten in backends which
        subclasses :py:class:`MountControl`.

        Returns:
            bool:       ``True`` if all checks where okay

        Raises:
            exceptions.MountException:
                        if backend can not mount

        Note:
            This can also be used to prepare things before running
            :py:func:`_mount`
        """
        return True

    def post_mount_check(self):
        """
        Check if the mount was successful. This **can** be overwritten in
        backends which subclasses :py:class:`MountControl`.

        Returns:
            bool:       ``True`` if all checks where okay

        Raises:
            exceptions.MountException:
                        if backend wasn't mount successful

        Note:
            This can also be used to clean up after running :py:func:`_mount`
        """
        return True

    def pre_umount_check(self):
        """
        Check if backend is safe to umount. This **can** be overwritten in
        backends which subclasses :py:class:`MountControl`.

        Returns:
            bool:       ``True`` if all checks where okay

        Raises:
            exceptions.MountException:
                        if backend can not umount

        Note:
            This can also be used to prepare things before running
            :py:func:`_umount`
        """
        return True

    def post_umount_check(self):
        """
        Check if unmount was successful. This **can** be overwritten in backends
        which subclasses :py:class:`MountControl`.

        Returns:
            bool:       ``True`` if all checks where okay

        Raises:
            exceptions.MountException:
                        if backend wasn't unmounted successful

        Note:
            This can also be used to clean up after running :py:func:`_umount`
        """
        return True

    def check_fuse(self):
        """
        Check if command in self.mountproc is installed and user is part of
        group ``fuse``.

        Raises:
            exceptions.MountException:  if either command is not available or
                                        user is not in group fuse
        """
        logger.debug('Check fuse', self)
        if not tools.check_command(self.mountproc):
            logger.debug('%s is missing' %self.mountproc, self)
            raise MountException( _('%(proc)s not found. Please install e.g. %(install_command)s')
                                  %{'proc': self.mountproc,
                                    'install_command': "'apt-get install %s'" %self.mountproc})
        if self.CHECK_FUSE_GROUP:
            user = self.config.get_user()
            try:
                fuse_grp_members = grp.getgrnam('fuse')[3]
            except KeyError:
                #group fuse doesn't exist. So most likely it isn't used by this distribution
                logger.debug("Group fuse doesn't exist. Skip test", self)
                return
            if not user in fuse_grp_members:
                logger.debug('User %s is not in group fuse' %user, self)
                raise MountException( _('%(user)s is not member of group \'fuse\'.\n '
                                        'Run \'sudo adduser %(user)s fuse\'. To apply '
                                        'changes logout and login again.\nLook at '
                                        '\'man backintime\' for further instructions.')
                                        % {'user': user})

    def is_mounted(self):
        """
        Check if the mountpoint is already mounted.

        Returns:
            bool:   ``True`` if mountpoint is mounted

        Raises:
            exceptions.MountException:
                    if mountpoint is not mounted but also not empty
        """
        if os.path.ismount(self.mountpoint):
            return True
        else:
            if os.listdir(self.mountpoint):
                raise MountException( _('mountpoint %s not empty.') % self.mountpoint)
            return False

    def create_mountstructure(self):
        """
        Create folders that are necessary for mounting.

        Folder structure in ~/.local/share/backintime/mnt/ (self.mount_root)::

            |\ <pid>.lock              <=  mountprocess lock that will prevent
            |                              different processes modifying
            |                              mountpoints at one time
            |
            |\ <hash_id>/              <=  ``self.hash_id_path``
            |            \                 will be shared by all profiles with
            |            |                 the same mount settings
            |            |
            |            |\ mountpoint/<=  ``self.mountpoint``
            |            |                 real mountpoint
            |            |
            |            |\ umount     <=  ``self.umount_info``
            |            |                 json file with all nessesary args
            |            |                 for unmount
            |            |
            |            \  locks/     <=  ``self.lock_path``
            |                              for each process you have a
            |                              ``<pid>.lock`` file
            |
            |\ <profile id>_<pid>/     <=  sym-link to the right path. return by
            |                              config.get_snapshots_path
            |                              (can be ../mnt/<hash_id>/mount_point
            |                              for ssh or
            |                              ../mnt/<hash_id>/<HOST>/<SHARE> for
            |                              fusesmb ...)
            |
            \ tmp_<profile id>_<pid>/ <=  sym-link for testing mountpoints in
                                          settingsdialog
        """
        tools.mkdir(self.mount_root, 0o700)
        tools.mkdir(self.hash_id_path, 0o700)
        tools.mkdir(self.mountpoint, 0o700)
        tools.mkdir(self.lock_path, 0o700)

    def mountprocess_lock_acquire(self, timeout = 60):
        """
        Create a short term lock only for blocking other processes changing
        mounts at the same time.

        Args:
            timeout (int):  wait ``timeout`` seconds before fail acquiring
                            the lock

        Raises:
            exceptions.MountException:
                            if timed out
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
        """
        Remove mountprocess lock.
        """
        lock_path = self.mount_root
        lock_suffix = '.lock'
        lock = os.path.join(lock_path, self.pid + lock_suffix)
        logger.debug('Release mountprocess lock %s'
                     %lock, self)
        if os.path.exists(lock):
            os.remove(lock)

    def set_mount_lock(self):
        """
        Create a lock for a mountpoint to prevent unmounting as long as this
        process is still running.
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
        Check for locks on the current mountpoint.

        Returns:
            bool:   ``True`` if there are any locks
        """
        lock_suffix = '.lock'
        return self.check_locks(self.lock_path, lock_suffix)

    def del_mount_lock(self):
        """
        Remove mountpoint lock for this process.
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

    def check_locks(self, path, lock_suffix):
        """
        Check if there are active locks ending with ``lock_suffix`` in ``path``.
        If the process owning the lock doesn't exist anymore this will remove
        the lock.

        Args:
            path (str):         full path to lock directory
            lock_suffix (str):  last part of locks name

        Returns:
            bool:               ``True`` if there are active locks in ``path``
        """
        for f in os.listdir(path):
            if not f[-len(lock_suffix):] == lock_suffix:
                continue
            is_tmp = os.path.basename(f)[-len(lock_suffix)-len('.tmp'):-len(lock_suffix)] == '.tmp'
            if is_tmp:
                lock_pid = os.path.basename(f)[:-len('.tmp')-len(lock_suffix)]
            else:
                lock_pid = os.path.basename(f)[:-len(lock_suffix)]
            if lock_pid == self.pid:
                if is_tmp == self.tmp_mount:
                    continue
            if tools.is_process_alive(int(lock_pid)):
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
        Set attribute ``arg`` in local namespace (self.arg). Also collect all
        args in ``self.all_kwargs`` which will be hashed later and used as
        mountpoint name and also be written as unmount_info.

        Args:
            arg (str):      argument name
            default:        default value used if ``arg`` is not in ``kwargs``
            store (bool):   if ``True`` add ``arg`` to ``self.all_kwargs``
            **kwargs:       arguments given on backend constructor
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
        Write content of ``self.all_kwargs`` to file
        ``~/.local/share/backintime/mnt/<hash_id>/umount``.
        This will be used to unmount the filesystem later.
        """
        data_string = json.dumps(self.all_kwargs)
        with open(self.umount_info, 'w') as f:
            f.write(data_string)
            f.close

    def read_umount_info(self, umount_info = None):
        """
        Read keyword arguments from file ``umount_info``.

        Args:
            umount_info (str):  full path to <hash_id>/umount file. If ``None``
                                current ``<hash_id>/umount`` file will be used

        Returns:
            dict:               previously written ``self.all_kwargs``
        """
        if umount_info is None:
            umount_info = self.umount_info
        with open(umount_info, 'r') as f:
            data_string = f.read()
            f.close()
        return json.loads(data_string)

    def compare_umount_info(self, umount_info = None):
        """
        Compare current ``self.all_kwargs`` with those from file ``umount_info``.

        This should prevent hash collisions of two different mounts.

        Args:
            umount_info (str):  full path to <hash_id>/umount file

        Returns:
            bool:               ``True`` if ``self.all_kwargs`` and ``kwargs``
                                read from ``umount_info`` file are identiacal
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
        Compare mount arguments between current and ``old_hash_id``. If they are
        identical we could reuse the mount and don't need to remount.

        Args:
            old_hash_id (str):  Hash ID of the old mountpoint

        Returns:
            bool:               True if the old mountpoint and current are
                                identiacal
        """
        if old_hash_id == self.hash_id:
            return self.compare_umount_info(self.get_umount_info(old_hash_id))
        return False

    def set_symlink(self, profile_id = None, hash_id = None, tmp_mount = None):
        """
        If ``self.symlink`` is ``True`` set symlink
        ``~/.local/share/backintime/mnt/<profile id>_<pid>``. Target will be
        either the mountpoint or a subfolder of the mountpoint if
        ``self.symlink_subfolder`` is set.

        Args:
            profile_id (str):   Profile ID that should be linked. If ``None``
                                use ``self.profile_id``
            hash_id (str):      Hash ID of mountpoint where this sysmlink should
                                point to. If ``None`` use ``self.hash_id``
            tmp_mount (bool):   Set a temporary symlink just for testing new
                                settings
        """
        if not self.symlink:
            return
        if profile_id is None:
            profile_id = self.profile_id
        if hash_id is None:
            hash_id = self.hash_id
        if tmp_mount is None:
            tmp_mount = self.tmp_mount
        dst = self.config.get_snapshots_path(profile_id = profile_id,
                                             mode = self.mode,
                                             tmp_mount = tmp_mount)
        mountpoint = self.get_mountpoint(hash_id)
        if self.symlink_subfolder is None:
            src = mountpoint
        else:
            src = os.path.join(mountpoint, self.symlink_subfolder)
        if os.path.exists(dst):
            os.remove(dst)
        os.symlink(src, dst)

    def remove_symlink(self, profile_id = None, tmp_mount = None):
        """
        Remove symlink ``~/.local/share/backintime/mnt/<profile id>_<pid>``

        Args:
            profile_id (str):   Profile ID for the symlink
            tmp_mount (bool):   Symlink is a temporary link for testing new
                                settings
        """
        if not self.symlink:
            return
        if profile_id is None:
            profile_id = self.profile_id
        if tmp_mount is None:
            tmp_mount = self.tmp_mount
        os.remove(self.config.get_snapshots_path(profile_id = profile_id,
                                                 mode = self.mode,
                                                 tmp_mount = tmp_mount))

    def hash(self, s):
        """
        Create a CRC32 hash of string ``s``.

        Args:
            s (str):    string that should be hashed

        Returns:
            str:        hash of string ``s``
        """
        return('%X' % (crc32(s.encode()) & 0xFFFFFFFF))

    def get_hash_id_path(self, hash_id = None):
        """
        Get path ``~/.local/share/backintime/mnt/<hash_id>``.

        Args:
            hash_id (str):  Unique identifier for a mountpoint. If ``None`` use
                            ``self.hash_id``

        Returns:
            str:            full path to ``<hash_id>``
        """
        if hash_id is None:
            hash_id = self.hash_id
        return os.path.join(self.mount_root, self.hash_id)

    def get_mountpoint(self, hash_id = None):
        """
        Get path ``~/.local/share/backintime/mnt/<hash_id>/mountpoint``.

        Args:
            hash_id (str):  Unique identifier for a mountpoint

        Returns:
            str:            full path to ``<hash_id>/mountpoint``
        """
        return os.path.join(self.get_hash_id_path(hash_id), 'mountpoint')

    def get_lock_path(self, hash_id = None):
        """
        Get path ``~/.local/share/backintime/mnt/<hash_id>/locks``.

        Args:
            hash_id (str):  Unique identifier for a mountpoint

        Returns:
            str:            full path to ``<hash_id>/locks```
        """
        return os.path.join(self.get_hash_id_path(hash_id), 'locks')

    def get_umount_info(self, hash_id = None):
        """
        Get path ``~/.local/share/backintime/mnt/<hash_id>/umount``.

        Args:
            hash_id (str):  Unique identifier for a mountpoint

        Returns:
            str:            full path to ``<hash_id>/umount```
        """
        return os.path.join(self.get_hash_id_path(hash_id), 'umount')
