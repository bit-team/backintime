#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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

"""This module provides the configuration of Back In Time."""

import os
import sys
import datetime
import gettext
import socket
import random
import shlex
try:
    import pwd
except ImportError:
    import getpass
    pwd = None

import tools
import configfile
import logger
import sshtools
import encfstools
import password
import pluginmanager
from exceptions import PermissionDeniedByPolicy, InvalidChar, InvalidCmd, LimitExceeded

_ = gettext.gettext

gettext.bindtextdomain('backintime', os.path.join(tools.sharePath(), 'locale'))
gettext.textdomain('backintime')


class Config(configfile.ConfigFileWithProfiles):
    """Represent the configuration of Back In Time.

    This class provides high level operations on the configuration and some
    additional information. It also handles the cronfile.
    """

    APP_NAME = 'Back In Time'
    """Display name of the application."""

    VERSION = '1.3.2'
    """Version string of the application."""

    COPYRIGHT = 'Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, ' \
                'Richard Bailey, Germar Reitze'

    CONFIG_VERSION = 6
    """Latest or highest possible version of Backin Time's config file."""

    NONE = 0
    AT_EVERY_BOOT = 1
    _5_MIN = 2
    _10_MIN = 4
    _30_MIN = 7
    HOUR = 10
    _1_HOUR = 10
    _2_HOURS = 12
    _4_HOURS = 14
    _6_HOURS = 16
    _12_HOURS = 18
    CUSTOM_HOUR = 19
    DAY = 20
    REPEATEDLY = 25
    UDEV = 27
    WEEK = 30
    MONTH = 40
    YEAR = 80

    DISK_UNIT_MB = 10
    DISK_UNIT_GB = 20

    SCHEDULE_MODES = {
                NONE: _('Disabled'),
                AT_EVERY_BOOT: _('At every boot/reboot'),
                _5_MIN: _('Every 5 minutes'),
                _10_MIN: _('Every 10 minutes'),
                _30_MIN: _('Every 30 minutes'),
                _1_HOUR: _('Every hour'),
                _2_HOURS: _('Every 2 hours'),
                _4_HOURS: _('Every 4 hours'),
                _6_HOURS: _('Every 6 hours'),
                _12_HOURS: _('Every 12 hours'),
                CUSTOM_HOUR: _('Custom Hours'),
                DAY: _('Every Day'),
                REPEATEDLY: _('Repeatedly (anacron)'),
                UDEV: _('When drive get connected (udev)'),
                WEEK: _('Every Week'),
                MONTH: _('Every Month'),
                YEAR: _('Every Year')
                }

    REMOVE_OLD_BACKUP_UNITS = {
                DAY: _('Day(s)'),
                WEEK: _('Week(s)'),
                YEAR: _('Year(s)')
                }

    REPEATEDLY_UNITS = {
                HOUR: _('Hour(s)'),
                DAY: _('Day(s)'),
                WEEK: _('Week(s)'),
                MONTH: _('Month(s)')
                }

    MIN_FREE_SPACE_UNITS = {DISK_UNIT_MB: 'MiB', DISK_UNIT_GB: 'GiB' }

    DEFAULT_EXCLUDE = [
        '.gvfs', '.cache/*', '.thumbnails*',
        '.local/share/[Tt]rash*', '*.backup*', '*~',
        '.dropbox*', '/proc/*', '/sys/*', '/dev/*',
        '/run/*', '/etc/mtab', '/var/cache/apt/archives/*.deb',
        'lost+found/*', '/tmp/*', '/var/tmp/*',
        '/var/backups/*', '.Private'
    ]

    DEFAULT_RUN_NICE_FROM_CRON = True
    DEFAULT_RUN_NICE_ON_REMOTE = False
    DEFAULT_RUN_IONICE_FROM_CRON = True
    DEFAULT_RUN_IONICE_FROM_USER = False
    DEFAULT_RUN_IONICE_ON_REMOTE = False
    DEFAULT_RUN_NOCACHE_ON_LOCAL = False
    DEFAULT_RUN_NOCACHE_ON_REMOTE = False
    DEFAULT_SSH_PREFIX = 'PATH=/opt/bin:/opt/sbin:\$PATH'
    DEFAULT_REDIRECT_STDOUT_IN_CRON = True
    DEFAULT_REDIRECT_STDERR_IN_CRON = False

    exp = _(' EXPERIMENTAL!')
    SNAPSHOT_MODES = {
        # 'mode': (
        #    <mounttools>,
        #    'ComboBox Text',
        #    need_pw|lbl_pw_1,
        #    need_2_pw|lbl_pw_2
        #),
        'local': (
            None,
            _('Local'),
            False,
            False
        ),
        'ssh': (
            sshtools.SSH,
            _('SSH'),
            _('SSH private key'),
            False
        ),
        'local_encfs': (
            encfstools.EncFS_mount,
            _('Local encrypted'),
            _('Encryption'),
            False
        ),
        'ssh_encfs': (
            encfstools.EncFS_SSH,
            _('SSH encrypted'),
            _('SSH private key'),
            _('Encryption'))
    }

    SSH_CIPHERS = {
        'default': _('Default'),
        'aes128-ctr': _('AES128-CTR'),
        'aes192-ctr': _('AES192-CTR'),
        'aes256-ctr': _('AES256-CTR'),
        'arcfour256': _('ARCFOUR256'),
        'arcfour128': _('ARCFOUR128'),
        'aes128-cbc': _('AES128-CBC'),
        '3des-cbc': _('3DES-CBC'),
        'blowfish-cbc': _('Blowfish-CBC'),
        'cast128-cbc': _('Cast128-CBC'),
        'aes192-cbc': _('AES192-CBC'),
        'aes256-cbc': _('AES256-CBC'),
        'arcfour': _('ARCFOUR')
    }

    ENCODE = encfstools.Bounce()
    PLUGIN_MANAGER = pluginmanager.PluginManager()

    _instance = None
    _buhtz = []

    @classmethod
    def instance(cls):
        """Provide the singleton instance of that class."""

        # Provide the instance if it exists
        if cls._instance:
            return cls._instance

        # But don't created implicite when needed.
        raise Exception(f'No instance of class "{cls}" exists. '
                        'Create an instance first.')

    def __init__(self, config_path=None, data_path=None):
        """
        """

        # # DEBUG
        # Config._buhtz.append('config.Config.__init__(config_path='
        #       f'{config_path}, data_path={data_path})')
        # import inspect
        # Config._buhtz.append(inspect.stack()[1])

        # Exception when an instance exists
        if __class__._instance:
            raise Exception(
                f'Instance of class "{self.__class__.__name__}" still exists!'
                f' Use "{self.__class__.__name__}.instance()" to access it.')

        # Remember the instance as the one and only singleton
        __class__._instance = self

        configfile.ConfigFileWithProfiles.__init__(self, _('Main profile'))

        self._APP_PATH = tools.backintimePath()

        self._DOC_PATH = os.path.join(
            tools.sharePath(), 'doc', 'backintime-common')

        if os.path.exists(os.path.join(self._APP_PATH, 'LICENSE')):
            self._DOC_PATH = self._APP_PATH

        self._GLOBAL_CONFIG_PATH = '/etc/backintime/config'

        HOME_FOLDER = os.path.expanduser('~')
        DATA_FOLDER = '.local/share'
        CONFIG_FOLDER = '.config'
        BIT_FOLDER = 'backintime'

        self._DEFAULT_LOCAL_DATA_FOLDER \
            = os.path.join(HOME_FOLDER, DATA_FOLDER, BIT_FOLDER)

        self._LOCAL_CONFIG_FOLDER \
            = os.path.join(HOME_FOLDER, CONFIG_FOLDER, BIT_FOLDER)

        self._MOUNT_ROOT \
            = os.path.join(DATA_FOLDER, BIT_FOLDER, 'mnt')

        if data_path:
            self.DATA_FOLDER_ROOT = data_path
            self._LOCAL_DATA_FOLDER \
                = os.path.join(data_path, DATA_FOLDER, BIT_FOLDER)
            self._LOCAL_MOUNT_ROOT \
                = os.path.join(data_path, self._MOUNT_ROOT)

        else:
            self.DATA_FOLDER_ROOT = HOME_FOLDER
            self._LOCAL_DATA_FOLDER = self._DEFAULT_LOCAL_DATA_FOLDER
            self._LOCAL_MOUNT_ROOT \
                = os.path.join(HOME_FOLDER, self._MOUNT_ROOT)

        tools.makeDirs(self._LOCAL_CONFIG_FOLDER)
        tools.makeDirs(self._LOCAL_DATA_FOLDER)
        tools.makeDirs(self._LOCAL_MOUNT_ROOT)

        self._DEFAULT_CONFIG_PATH \
            = os.path.join(self._LOCAL_CONFIG_FOLDER, 'config')

        if config_path is None:
            self._LOCAL_CONFIG_PATH = self._DEFAULT_CONFIG_PATH

        else:
            self._LOCAL_CONFIG_PATH = os.path.abspath(config_path)
            self._LOCAL_CONFIG_FOLDER \
                = os.path.dirname(self._LOCAL_CONFIG_PATH)

        old_path = os.path.join(self._LOCAL_CONFIG_FOLDER, 'config2')

        if os.path.exists(old_path):

            if os.path.exists(self._LOCAL_CONFIG_PATH):
                os.remove(old_path)

            else:
                os.rename(old_path, self._LOCAL_CONFIG_PATH)

        # Load global config file
        self.load(self._GLOBAL_CONFIG_PATH)

        # Append local config file
        self.append(self._LOCAL_CONFIG_PATH)

        # Get the version of the config file
        # or assume the highest config version if it isn't set.
        currentConfigVersion \
            = self.intValue('config.version', self.CONFIG_VERSION)

        if currentConfigVersion < self.CONFIG_VERSION:
            # config.version value wasn't stored since BiT version 0.9.99.22
            # until version 1.2.0 because of a bug. So we can't really tell
            # which version the config is. But most likely it is version > 4
            if currentConfigVersion < 4:
                # update from BackInTime version < 1.0 is deprecated
                logger.error(
                    "config.version is < 4. This config was made with "
                    "BackInTime version < 1.0. This version ({}) doesn't "
                    "support upgrading config from version < 1.0 anymore. "
                    "Please use BackInTime version <= 1.1.12 to upgrade the "
                    "config to a more recent version.".format(self.VERSION))
                # TODO: add popup warning
                sys.exit(2)

            if currentConfigVersion < 5:
                logger.info("Update to config version 5: "
                            "other snapshot locations", self)
                profiles = self.profiles()

                for profile_id in profiles:
                    # change include
                    old_values = self.includeV4(profile_id)
                    values = []

                    for value in old_values:
                        values.append((value, 0))

                    self.setInclude(values, profile_id)

                    # change exclude
                    old_values = self.excludeV4(profile_id)
                    self.setExclude(old_values, profile_id)

                    # remove keys
                    self.removeProfileKey(
                        'snapshots.include_folders', profile_id)
                    self.removeProfileKey(
                        'snapshots.exclude_patterns', profile_id)

            if currentConfigVersion < 6:
                # DEBUG
                print(self.dict)
                logger.info('Update to config version 6', self)

                # remap some keys
                for profile in self.profiles():
                    # make a 'schedule' domain for everything relatingi schedules
                    self.remapProfileKey(
                        'snapshots.automatic_backup_anacron_period',
                        'schedule.repeatedly.period',
                        profile)
                    self.remapProfileKey(
                        'snapshots.automatic_backup_anacron_unit',
                        'schedule.repeatedly.unit',
                        profile)
                    self.remapProfileKey('snapshots.automatic_backup_day',
                                         'schedule.day',
                                         profile)
                    self.remapProfileKey('snapshots.automatic_backup_mode',
                                         'schedule.mode',
                                         profile)
                    self.remapProfileKey('snapshots.automatic_backup_time',
                                         'schedule.time',
                                         profile)
                    self.remapProfileKey('snapshots.automatic_backup_weekday',
                                         'schedule.weekday',
                                         profile)
                    self.remapProfileKey('snapshots.custom_backup_time',
                                         'schedule.custom_time',
                                         profile)

                    # we don't have 'full rsync mode' anymore
                    self.remapProfileKey(
                        'snapshots.full_rsync'
                        '.take_snapshot_regardless_of_changes',
                        'snapshots.take_snapshot_regardless_of_changes',
                        profile)
                # remap 'qt4' keys
                self.remapKeyRegex(r'qt4', 'qt')

                # remove old gnome and kde keys
                self.removeKeysStartsWith('gnome')
                self.removeKeysStartsWith('kde')

            self.save()

        self.current_hash_id = 'local'
        self.pw = None
        self.forceUseChecksum = False
        self.xWindowId = None
        self.inhibitCookie = None
        self.setupUdev = tools.SetupUdev()

    def save(self):
        """
        """
        self.setIntValue('config.version', self.CONFIG_VERSION)
        return super(Config, self).save(self._LOCAL_CONFIG_PATH)

    def checkConfig(self):
        """
        """
        profiles = self.profiles()

        for profile_id in profiles:
            profile_name = self.profileName(profile_id)
            snapshots_path = self.snapshotsPath(profile_id)
            logger.debug('Check profile %s' % profile_name, self)

            # check snapshots path
            if not snapshots_path:
                self.notifyError(
                    _('Profile: "%s"') % profile_name \
                    + '\n' + _('Snapshots folder is not valid !'))

                return False

            # check include
            include_list = self.include(profile_id)

            if not include_list:
                self.notifyError(
                    _('Profile: "%s"') % profile_name + '\n' \
                    + _('You must select at least one folder to backup !'))

                return False

            snapshots_path2 = snapshots_path + '/'

            for item in include_list:

                if item[1] != 0:
                    continue

                path = item[0]

                if path == snapshots_path:
                    self.notifyError(
                        _('Profile: "%s"') % profile_name \
                        + '\n' + _('You can\'t include backup folder !'))

                    return False

                if len(path) >= len(snapshots_path2):

                    if path[: len(snapshots_path2)] == snapshots_path2:

                        self.notifyError(
                            _('Profile: "%s"') %  self.currentProfile() \
                            + '\n' \
                            + _('You can\'t include a backup sub-folder !'))

                        return False

        return True

    def user(self):
        """
        portable way to get username
        cc by-sa 3.0      http://stackoverflow.com/a/19865396/1139841
        author: techtonik http://stackoverflow.com/users/239247/techtonik
        """
        if pwd:
            return pwd.getpwuid(os.geteuid()).pw_name
        else:
            return getpass.getuser()

    def pid(self):
        return str(os.getpid())

    def host(self):
        return socket.gethostname()

    def snapshotsPath(self, profile_id=None, mode=None, tmp_mount=False):

        if mode is None:
            mode = self.snapshotsMode(profile_id)

        if self.SNAPSHOT_MODES[mode][0] == None:
            # no mount needed
            # ?Where to save snapshots in mode 'local'.
            # This path must contain a
            # ?folderstructure like
            # 'backintime/<HOST>/<USER>/<PROFILE_ID>';absolute path
            return self.profileStrValue('snapshots.path', '', profile_id)

        else:
            # mode need to be mounted; return mountpoint
            symlink = self.snapshotsSymlink(
                profile_id=profile_id,
                tmp_mount=tmp_mount)

            return os.path.join(self._LOCAL_MOUNT_ROOT, symlink)

    def snapshotsFullPath(self, profile_id=None):
        """
        Returns the full path for the snapshots: .../backintime/machine/user/profile_id/
        """
        host, user, profile = self.hostUserProfile(profile_id)

        return os.path.join(
            self.snapshotsPath(profile_id), 'backintime', host, user, profile)

    def setSnapshotsPath(self, value, profile_id=None, mode=None):
        """
        Sets the snapshot path to value, initializes, and checks it
        """
        if not value:
            return False

        if profile_id == None:
            profile_id = self.currentProfile()

        if mode is None:
            mode = self.snapshotsMode(profile_id)

        if not os.path.isdir(value):
            self.notifyError(_('%s is not a folder !') % value)

            return False

        # Initialize the snapshots folder
        logger.debug("Check snapshot folder: %s" % value, self)

        host, user, profile = self.hostUserProfile(profile_id)

        if not all((host, user, profile)):
            self.notifyError(_('Host/User/Profile-ID must not be empty!'))

            return False

        full_path = os.path.join(value, 'backintime', host, user, profile)

        if not os.path.isdir(full_path):
            logger.debug("Create folder: %s" % full_path, self)
            tools.makeDirs(full_path)

            if not os.path.isdir(full_path):
                self.notifyError(
                    _('Can\'t write to: %s\nAre you sure you '
                      'have write access ?' % value))

                return False

            for p in (os.path.join(value, 'backintime'),
                      os.path.join(value, 'backintime', host)):
                try:
                    os.chmod(p, 0o777)
                except PermissionError as e:
                    msg = "Failed to change permissions world "\
                          "writeable for '{}': {}"
                    logger.warning(msg.format(p, str(e)), self)

        # Test filesystem
        fs = tools.filesystem(full_path)

        if fs == 'vfat':
            self.notifyError(
                _("Destination filesystem for '%(path)s' is formatted with "
                  "FAT which doesn't support hard-links. "
                  "Please use a native Linux filesystem.") % {'path': value})

            return False

        elif fs == 'cifs' and not self.copyLinks():
            self.notifyError(
                _("Destination filsystem for '%(path)s' is a SMB mounted "
                  "share. Please make sure the remote SMB server supports "
                  "symlinks or activate '%(copyLinks)s' in "
                  "'%(expertOptions)s'.") % {
                      'path': value,
                      'copyLinks': _('Copy links (dereference '
                                     'symbolic links)'),
                      'expertOptions': _('Expert Options')
                  })

        elif fs == 'fuse.sshfs' and mode not in ('ssh', 'ssh_encfs'):
            self.notifyError(
                _("Destination filesystem for '%(path)s is a sshfs mounted "
                  "share. sshfs doesn't support hard-links. Please use mode "
                  "'SSH' instead.") % {'path': value})

            return False

        # Test write access for the folder
        check_path = os.path.join(full_path, 'check')
        tools.makeDirs(check_path)

        if not os.path.isdir(check_path):
            self.notifyError(
                _('Can\'t write to: %s\nAre you sure you '
                  'have write access ?' % full_path))

            return False

        os.rmdir(check_path)

        if self.SNAPSHOT_MODES[mode][0] is None:
            self.setProfileStrValue('snapshots.path', value, profile_id)

        return True

    def snapshotsMode(self, profile_id=None):
        # ?Use mode (or backend) for this snapshot. Look at 'man backintime'
        # ?section 'Modes'.;local|local_encfs|ssh|ssh_encfs

        return self.profileStrValue('snapshots.mode', 'local', profile_id)

    def setSnapshotsMode(self, value, profile_id=None):
        self.setProfileStrValue('snapshots.mode', value, profile_id)

    def snapshotsSymlink(self, profile_id=None, tmp_mount=False):
        if profile_id is None:
            profile_id = self.current_profile_id

        symlink = '%s_%s' % (profile_id, self.pid())

        if tmp_mount:
            symlink = 'tmp_%s' % symlink

        return symlink

    def setCurrentHashId(self, hash_id):
        self.current_hash_id = hash_id

    def hashCollision(self):
        # ?Internal value used to prevent hash
        # collisions on mountpoints. Do not change this.
        return self.intValue('global.hash_collision', 0)

    def incrementHashCollision(self):
        value = self.hashCollision() + 1
        self.setIntValue('global.hash_collision', value)

    # SSH
    def sshSnapshotsPath(self, profile_id=None):
        # ?Snapshot path on remote host. If the path is
        # relative (no leading '/')
        # ?it will start from remote Users homedir.
        # An empty path will be replaced
        # ?with './'.;absolute or relative path
        return self.profileStrValue('snapshots.ssh.path', '', profile_id)

    def sshSnapshotsFullPath(self, profile_id=None):
        """Returns the full path for the
        snapshots: .../backintime/machine/user/profile_id/
        """

        path = self.sshSnapshotsPath(profile_id)

        if not path:
            path = './'

        host, user, profile = self.hostUserProfile(profile_id)

        return os.path.join(path, 'backintime', host, user, profile)

    def setSshSnapshotsPath(self, value, profile_id=None):
        self.setProfileStrValue('snapshots.ssh.path', value, profile_id)

        return True

    def sshHost(self, profile_id=None):
        # ?Remote host used for mode 'ssh' and 'ssh_encfs'.;IP or domain address

        return self.profileStrValue('snapshots.ssh.host', '', profile_id)

    def setSshHost(self, value, profile_id=None):
        self.setProfileStrValue('snapshots.ssh.host', value, profile_id)

    def sshPort(self, profile_id=None):
        # ?SSH Port on remote host.;0-65535
        return self.profileIntValue('snapshots.ssh.port', '22', profile_id)

    def setSshPort(self, value, profile_id=None):
        self.setProfileIntValue('snapshots.ssh.port', value, profile_id)

    def sshCipher(self, profile_id=None):
        # ?Cipher that is used for encrypting the SSH tunnel.
        # Depending on the environment (network bandwidth, cpu and hdd
        # performance) a different
        # ?cipher might be faster.;default | aes192-cbc | aes256-cbc
        # | aes128-ctr | aes192-ctr | aes256-ctr | arcfour | arcfour256
        # | arcfour128 | aes128-cbc | 3des-cbc | blowfish-cbc | cast128-cbc
        return self.profileStrValue(
            'snapshots.ssh.cipher', 'default', profile_id)

    def setSshCipher(self, value, profile_id=None):
        self.setProfileStrValue('snapshots.ssh.cipher', value, profile_id)

    def sshUser(self, profile_id=None):
        # ?Remote SSH user;;local users name
        return self.profileStrValue(
            'snapshots.ssh.user', self.user(), profile_id)

    def setSshUser(self, value, profile_id=None):
        self.setProfileStrValue('snapshots.ssh.user', value, profile_id)

    def sshHostUserPortPathCipher(self, profile_id=None):
        host = self.sshHost(profile_id)
        port = self.sshPort(profile_id)
        user = self.sshUser(profile_id)
        path = self.sshSnapshotsPath(profile_id)
        cipher = self.sshCipher(profile_id)

        if not path:
            path = './'

        return (host, port, user, path, cipher)

    def sshPrivateKeyFile(self, profile_id=None):
        ssh = self.sshPrivateKeyFolder()
        default = ''
        for f in ['id_dsa', 'id_rsa', 'identity']:
            private_key = os.path.join(ssh, f)
            if os.path.isfile(private_key):
                default = private_key
                break
        #?Private key file used for password-less authentication on remote host.
        #?;absolute path to private key file;~/.ssh/id_dsa
        f = self.profileStrValue('snapshots.ssh.private_key_file', default, profile_id)
        if f:
            return f
        return default

    def sshPrivateKeyFolder(self):
        return os.path.join(os.path.expanduser('~'), '.ssh')

    def setSshPrivateKeyFile(self, value, profile_id=None):
        self.setProfileStrValue('snapshots.ssh.private_key_file', value, profile_id)

    def sshMaxArgLength(self, profile_id=None):
        #?Maximum argument length of commands run on remote host. This can be tested
        #?with 'python3 /usr/share/backintime/common/sshMaxArg.py USER@HOST'.\n
        #?0 = unlimited;0, >700
        value = self.profileIntValue('snapshots.ssh.max_arg_length', 0, profile_id)
        if value and value < 700:
            raise ValueError('SSH max arg length %s is to low to run commands' % value)
        return value

    def setSshMaxArgLength(self, value, profile_id=None):
        self.setProfileIntValue('snapshots.ssh.max_arg_length', value, profile_id)

    def sshCheckCommands(self, profile_id=None):
        #?Check if all commands (used during takeSnapshot) work like expected
        #?on the remote host.
        return self.profileBoolValue('snapshots.ssh.check_commands', True, profile_id)

    def setSshCheckCommands(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.ssh.check_commands', value, profile_id)

    def sshCheckPingHost(self, profile_id=None):
        #?Check if the remote host is available before trying to mount.
        return self.profileBoolValue('snapshots.ssh.check_ping', True, profile_id)

    def setSshCheckPingHost(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.ssh.check_ping', value, profile_id)

    def sshDefaultArgs(self, profile_id=None):
        """
        Default arguments used for ``ssh`` and ``sshfs`` commands.

        Returns:
            list:   arguments for ssh
        """
        # keep connection alive
        args  = ['-o', 'ServerAliveInterval=240']
        # disable ssh banner
        args += ['-o', 'LogLevel=Error']
        # specifying key file here allows to override for potentially
        # conflicting .ssh/config key entry
        args += ['-o', 'IdentityFile={}'.format(self.sshPrivateKeyFile(profile_id))]
        return args

    def sshCommand(self,
                   cmd=None,
                   custom_args=None,
                   port=True,
                   cipher=True,
                   user_host=True,
                   ionice=True,
                   nice=True,
                   quote=False,
                   prefix=True,
                   profile_id=None):
        """
        Return SSH command with all arguments.

        Args:
            cmd (list):         command that should run on remote host
            custom_args (list): additional arguments paste to the command
            port (bool):        use port from config
            cipher (bool):      use cipher from config
            user_host (bool):   use user@host from config
            ionice (bool):      use ionice if configured
            nice (bool):        use nice if configured
            quote (bool):       quote remote command
            prefix (bool):      use prefix from config before remote command
            profile_id (str):   profile ID that should  be used in config

        Returns:
            list:               ssh command with chosen arguments
        """
        assert cmd is None or isinstance(cmd, list), "cmd '{}' is not list instance".format(cmd)
        assert custom_args is None or isinstance(custom_args, list), "custom_args '{}' is not list instance".format(custom_args)
        ssh  = ['ssh']
        ssh += self.sshDefaultArgs(profile_id)
        # remote port
        if port:
            ssh += ['-p', str(self.sshPort(profile_id))]
        # cipher used to transfer data
        c = self.sshCipher(profile_id)
        if cipher and c != 'default':
            ssh += ['-o', 'Ciphers={}'.format(c)]
        # custom arguments
        if custom_args:
            ssh += custom_args
        # user@host
        if user_host:
            ssh.append('{}@{}'.format(self.sshUser(profile_id),
                                      self.sshHost(profile_id)))
        # quote the command running on remote host
        if quote and cmd:
            ssh.append("'")
        # run 'ionice' on remote host
        if ionice and self.ioniceOnRemote(profile_id) and cmd:
            ssh += ['ionice', '-c2', '-n7']
        # run 'nice' on remote host
        if nice and self.niceOnRemote(profile_id) and cmd:
            ssh += ['nice', '-n19']
        # run prefix on remote host
        if prefix and cmd and self.sshPrefixEnabled(profile_id):
            ssh += self.sshPrefixCmd(profile_id, cmd_type = list)
        # add the command
        if cmd:
            ssh += cmd
        # close quote
        if quote and cmd:
            ssh.append("'")

        return ssh

    # ENCFS
    def localEncfsPath(self, profile_id=None):
        #?Where to save snapshots in mode 'local_encfs'.;absolute path
        return self.profileStrValue('snapshots.local_encfs.path', '', profile_id)

    def setLocalEncfsPath(self, value, profile_id=None):
        self.setProfileStrValue('snapshots.local_encfs.path', value, profile_id)

    def passwordSave(self, profile_id=None, mode=None):
        if mode is None:
            mode = self.snapshotsMode(profile_id)
        #?Save password to system keyring (gnome-keyring or kwallet).
        #?<MODE> must be the same as \fIprofile<N>.snapshots.mode\fR
        return self.profileBoolValue('snapshots.%s.password.save' % mode, False, profile_id)

    def setPasswordSave(self, value, profile_id=None, mode=None):
        if mode is None:
            mode = self.snapshotsMode(profile_id)
        self.setProfileBoolValue('snapshots.%s.password.save' % mode, value, profile_id)

    def passwordUseCache(self, profile_id=None, mode=None):
        if mode is None:
            mode = self.snapshotsMode(profile_id)
        default = not tools.checkHomeEncrypt()
        #?Cache password in RAM so it can be read by cronjobs.
        #?Security issue: root might be able to read that password, too.
        #?<MODE> must be the same as \fIprofile<N>.snapshots.mode\fR;;true if home is not encrypted
        return self.profileBoolValue('snapshots.%s.password.use_cache' % mode, default, profile_id)

    def setPasswordUseCache(self, value, profile_id=None, mode=None):
        if mode is None:
            mode = self.snapshotsMode(profile_id)
        self.setProfileBoolValue('snapshots.%s.password.use_cache' % mode, value, profile_id)

    def password(self, parent=None, profile_id=None, mode=None, pw_id=1, only_from_keyring=False):
        if self.pw is None:
            self.pw = password.Password(self)
        if profile_id is None:
            profile_id = self.currentProfile()
        if mode is None:
            mode = self.snapshotsMode(profile_id)
        return self.pw.password(parent, profile_id, mode, pw_id, only_from_keyring)

    def setPassword(self, password, profile_id=None, mode=None, pw_id=1):
        if self.pw is None:
            self.pw = password.Password(self)
        if profile_id is None:
            profile_id = self.currentProfile()
        if mode is None:
            mode = self.snapshotsMode(profile_id)
        self.pw.setPassword(password, profile_id, mode, pw_id)

    def modeNeedPassword(self, mode, pw_id=1):
        need_pw = self.SNAPSHOT_MODES[mode][pw_id + 1]
        if need_pw is False:
            return False
        return True

    def keyringServiceName(self, profile_id=None, mode=None, pw_id=1):
        if mode is None:
            mode = self.snapshotsMode(profile_id)
        if pw_id > 1:
            return 'backintime/%s_%s' % (mode, pw_id)
        return 'backintime/%s' % mode

    def keyringUserName(self, profile_id=None):
        if profile_id is None:
            profile_id = self.currentProfile()
        return 'profile_id_%s' % profile_id

    def hostUserProfileDefault(self, profile_id=None):
        host = socket.gethostname()
        user = self.user()
        profile = profile_id
        if profile is None:
            profile = self.currentProfile()

        return (host, user, profile)

    def hostUserProfile(self, profile_id=None):
        default_host, default_user, default_profile = self.hostUserProfileDefault(profile_id)
        #?Set Host for snapshot path;;local hostname
        host = self.profileStrValue('snapshots.path.host', default_host, profile_id)

        #?Set User for snapshot path;;local username
        user = self.profileStrValue('snapshots.path.user', default_user, profile_id)

        #?Set Profile-ID for snapshot path;1-99999;current Profile-ID
        profile = self.profileStrValue('snapshots.path.profile', default_profile, profile_id)

        return (host, user, profile)

    def setHostUserProfile(self, host, user, profile, profile_id=None):
        self.setProfileStrValue('snapshots.path.host', host, profile_id)
        self.setProfileStrValue('snapshots.path.user', user, profile_id)
        self.setProfileStrValue('snapshots.path.profile', profile, profile_id)

    def includeV4(self, profile_id=None):
        #?!ignore this in manpage
        value = self.profileStrValue('snapshots.include_folders', '', profile_id)
        if not value:
            return []

        paths = []

        for item in value.split(':'):
            fields = item.split('|')

            path = os.path.expanduser(fields[0])
            path = os.path.abspath(path)
            paths.append(path)

        return paths

    def include(self, profile_id=None):
        #?Include this file or folder. <I> must be a counter starting with 1;absolute path::
        #?Specify if \fIprofile<N>.snapshots.include.<I>.value\fR is a folder (0) or a file (1).;0|1;0
        return self.profileListValue('snapshots.include', ('str:value', 'int:type'), [], profile_id)

    def setInclude(self, values, profile_id=None):
        self.setProfileListValue('snapshots.include', ('str:value', 'int:type'), values, profile_id)

    def excludeV4(self, profile_id=None):
        """
        Gets the exclude patterns: conf version 4
        """
        #?!ignore this in manpage
        value = self.profileStrValue('snapshots.exclude_patterns', '.gvfs:.cache*:[Cc]ache*:.thumbnails*:[Tt]rash*:*.backup*:*~', profile_id)
        if not value:
            return []
        return value.split(':')

    def exclude(self, profile_id=None):
        """
        Gets the exclude patterns
        """
        #?Exclude this file or folder. <I> must be a counter
        #?starting with 1;file, folder or pattern (relative or absolute)
        return self.profileListValue('snapshots.exclude', 'str:value', self.DEFAULT_EXCLUDE, profile_id)

    def setExclude(self, values, profile_id=None):
        self.setProfileListValue('snapshots.exclude', 'str:value', values, profile_id)

    def excludeBySizeEnabled(self, profile_id=None):
        #?Enable exclude files by size.
        return self.profileBoolValue('snapshots.exclude.bysize.enabled', False, profile_id)

    def excludeBySize(self, profile_id=None):
        #?Exclude files bigger than value in MiB.
        #?With 'Full rsync mode' disabled this will only affect new files
        #?because for rsync this is a transfer option, not an exclude option.
        #?So big files that has been backed up before will remain in snapshots
        #?even if they had changed.
        return self.profileIntValue('snapshots.exclude.bysize.value', 500, profile_id)

    def setExcludeBySize(self, enabled, value, profile_id=None):
        self.setProfileBoolValue('snapshots.exclude.bysize.enabled', enabled, profile_id)
        self.setProfileIntValue('snapshots.exclude.bysize.value', value, profile_id)

    def tag(self, profile_id=None):
        #?!ignore this in manpage
        return self.profileStrValue('snapshots.tag', str(random.randint(100, 999)), profile_id)

    def scheduleMode(self, profile_id=None):
        #?Which schedule used for crontab. The crontab entry will be
        #?generated with 'backintime check-config'.\n
        #? 0 = Disabled\n 1 = at every boot\n 2 = every 5 minute\n
        #? 4 = every 10 minute\n 7 = every 30 minute\n10 = every hour\n
        #?12 = every 2 hours\n14 = every 4 hours\n16 = every 6 hours\n
        #?18 = every 12 hours\n19 = custom defined hours\n20 = every day\n
        #?25 = daily anacron\n27 = when drive get connected\n30 = every week\n
        #?40 = every month\n80 = every year
        #?;0|1|2|4|7|10|12|14|16|18|19|20|25|27|30|40|80;0
        return self.profileIntValue('schedule.mode', self.NONE, profile_id)

    def setScheduleMode(self, value, profile_id=None):
        self.setProfileIntValue('schedule.mode', value, profile_id)

    def scheduleTime(self, profile_id=None):
        #?What time the cronjob should run? Only valid for
        #?\fIprofile<N>.schedule.mode\fR >= 20;0-24
        return self.profileIntValue('schedule.time', 0, profile_id)

    def setScheduleTime(self, value, profile_id=None):
        self.setProfileIntValue('schedule.time', value, profile_id)

    def scheduleDay(self, profile_id=None):
        #?Which day of month the cronjob should run? Only valid for
        #?\fIprofile<N>.schedule.mode\fR >= 40;1-28
        return self.profileIntValue('schedule.day', 1, profile_id)

    def setScheduleDay(self, value, profile_id=None):
        self.setProfileIntValue('schedule.day', value, profile_id)

    def scheduleWeekday(self, profile_id=None):
        #?Which day of week the cronjob should run? Only valid for
        #?\fIprofile<N>.schedule.mode\fR = 30;1 = monday \- 7 = sunday
        return self.profileIntValue('schedule.weekday', 7, profile_id)

    def setScheduleWeekday(self, value, profile_id=None):
        self.setProfileIntValue('schedule.weekday', value, profile_id)

    def customBackupTime(self, profile_id=None):
        #?Custom hours for cronjob. Only valid for
        #?\fIprofile<N>.schedule.mode\fR = 19
        #?;comma separated int (8,12,18,23) or */3;8,12,18,23
        return self.profileStrValue('schedule.custom_time', '8,12,18,23', profile_id)

    def setCustomBackupTime(self, value, profile_id=None):
        self.setProfileStrValue('schedule.custom_time', value, profile_id)

    def scheduleRepeatedPeriod(self, profile_id=None):
        #?How many units to wait between new snapshots with anacron? Only valid
        #?for \fIprofile<N>.schedule.mode\fR = 25|27
        return self.profileIntValue('schedule.repeatedly.period', 1, profile_id)

    def setScheduleRepeatedPeriod(self, value, profile_id=None):
        self.setProfileIntValue('schedule.repeatedly.period', value, profile_id)

    def scheduleRepeatedUnit(self, profile_id=None):
        #?Units to wait between new snapshots with anacron.\n
        #?10 = hours\n20 = days\n30 = weeks\n40 = months\n
        #?Only valid for \fIprofile<N>.schedule.mode\fR = 25|27;
        #?10|20|30|40;20
        return self.profileIntValue('schedule.repeatedly.unit', self.DAY, profile_id)

    def setScheduleRepeatedUnit(self, value, profile_id=None):
        self.setProfileIntValue('schedule.repeatedly.unit', value, profile_id)

    def removeOldSnapshots(self, profile_id=None):
                #?Remove all snapshots older than value + unit
        return (self.profileBoolValue('snapshots.remove_old_snapshots.enabled', True, profile_id),
                #?Snapshots older than this times units will be removed
                self.profileIntValue('snapshots.remove_old_snapshots.value', 10, profile_id),
                #?20 = days\n30 = weeks\n80 = years;20|30|80;80
                self.profileIntValue('snapshots.remove_old_snapshots.unit', self.YEAR, profile_id))

    def keepOnlyOneSnapshot(self, profile_id=None):
        #?NOT YET IMPLEMENTED. Remove all snapshots but one.
        return self.profileBoolValue('snapshots.keep_only_one_snapshot.enabled', False, profile_id)

    def setKeepOnlyOneSnapshot(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.keep_only_one_snapshot.enabled', value, profile_id)

    def removeOldSnapshotsEnabled(self, profile_id=None):
        return self.profileBoolValue('snapshots.remove_old_snapshots.enabled', True, profile_id)

    def removeOldSnapshotsDate(self, profile_id=None):
        enabled, value, unit = self.removeOldSnapshots(profile_id)
        if not enabled:
            return datetime.date(1, 1, 1)

        if unit == self.DAY:
            date = datetime.date.today()
            date = date - datetime.timedelta(days = value)
            return date

        if unit == self.WEEK:
            date = datetime.date.today()
            date = date - datetime.timedelta(days = date.weekday() + 7 * value)
            return date

        if unit == self.YEAR:
            date = datetime.date.today()
            return date.replace(day = 1, year = date.year - value)

        return datetime.date(1, 1, 1)

    def setRemoveOldSnapshots(self, enabled, value, unit, profile_id=None):
        self.setProfileBoolValue('snapshots.remove_old_snapshots.enabled', enabled, profile_id)
        self.setProfileIntValue('snapshots.remove_old_snapshots.value', value, profile_id)
        self.setProfileIntValue('snapshots.remove_old_snapshots.unit', unit, profile_id)

    def minFreeSpace(self, profile_id=None):
                #?Remove snapshots until \fIprofile<N>.snapshots.min_free_space.value\fR
                #?free space is reached.
        return (self.profileBoolValue('snapshots.min_free_space.enabled', True, profile_id),
                #?Keep at least value + unit free space.;1-99999
                self.profileIntValue('snapshots.min_free_space.value', 1, profile_id),
                #?10 = MB\n20 = GB;10|20;20
                self.profileIntValue('snapshots.min_free_space.unit', self.DISK_UNIT_GB, profile_id))

    def minFreeSpaceEnabled(self, profile_id=None):
        return self.profileBoolValue('snapshots.min_free_space.enabled', True, profile_id)

    def minFreeSpaceMib(self, profile_id=None):
        enabled, value, unit = self.minFreeSpace(profile_id)
        if not enabled:
            return 0

        if self.DISK_UNIT_MB == unit:
            return value

        value *= 1024 #Gb
        if self.DISK_UNIT_GB == unit:
            return value

        return 0

    def setMinFreeSpace(self, enabled, value, unit, profile_id=None):
        self.setProfileBoolValue('snapshots.min_free_space.enabled', enabled, profile_id)
        self.setProfileIntValue('snapshots.min_free_space.value', value, profile_id)
        self.setProfileIntValue('snapshots.min_free_space.unit', unit, profile_id)

    def minFreeInodes(self, profile_id=None):
        #?Keep at least value % free inodes.;1-15
        return self.profileIntValue('snapshots.min_free_inodes.value', 2, profile_id)

    def minFreeInodesEnabled(self, profile_id=None):
        #?Remove snapshots until \fIprofile<N>.snapshots.min_free_inodes.value\fR
        #?free inodes in % is reached.
        return self.profileBoolValue('snapshots.min_free_inodes.enabled', True, profile_id)

    def setMinFreeInodes(self, enabled, value, profile_id=None):
        self.setProfileBoolValue('snapshots.min_free_inodes.enabled', enabled, profile_id)
        self.setProfileIntValue('snapshots.min_free_inodes.value', value, profile_id)

    def dontRemoveNamedSnapshots(self, profile_id=None):
        #?Keep snapshots with names during smart_remove.
        return self.profileBoolValue('snapshots.dont_remove_named_snapshots', True, profile_id)

    def setDontRemoveNamedSnapshots(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.dont_remove_named_snapshots', value, profile_id)

    def smartRemove(self, profile_id=None):
                #?Run smart_remove to clean up old snapshots after a new snapshot was created.
        return (self.profileBoolValue('snapshots.smart_remove', False, profile_id),
                #?Keep all snapshots for X days.
                self.profileIntValue('snapshots.smart_remove.keep_all', 2, profile_id),
                #?Keep one snapshot per day for X days.
                self.profileIntValue('snapshots.smart_remove.keep_one_per_day', 7, profile_id),
                #?Keep one snapshot per week for X weeks.
                self.profileIntValue('snapshots.smart_remove.keep_one_per_week', 4, profile_id),
                #?Keep one snapshot per month for X month.
                self.profileIntValue('snapshots.smart_remove.keep_one_per_month', 24, profile_id))

    def setSmartRemove(self,
                       value,
                       keep_all,
                       keep_one_per_day,
                       keep_one_per_week,
                       keep_one_per_month,
                       profile_id=None):
        self.setProfileBoolValue('snapshots.smart_remove', value, profile_id)
        self.setProfileIntValue('snapshots.smart_remove.keep_all', keep_all, profile_id)
        self.setProfileIntValue('snapshots.smart_remove.keep_one_per_day', keep_one_per_day, profile_id)
        self.setProfileIntValue('snapshots.smart_remove.keep_one_per_week', keep_one_per_week, profile_id)
        self.setProfileIntValue('snapshots.smart_remove.keep_one_per_month', keep_one_per_month, profile_id)

    def smartRemoveRunRemoteInBackground(self, profile_id=None):
        #?If using mode SSH or SSH-encrypted, run smart_remove in background on remote machine
        return self.profileBoolValue('snapshots.smart_remove.run_remote_in_background', False, profile_id)

    def setSmartRemoveRunRemoteInBackground(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.smart_remove.run_remote_in_background', value, profile_id)

    def notify(self, profile_id=None):
        #?Display notifications (errors, warnings) through libnotify.
        return self.profileBoolValue('snapshots.notify.enabled', True, profile_id)

    def setNotify(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.notify.enabled', value, profile_id)

    def backupOnRestore(self, profile_id=None):
        #?Rename existing files before restore into FILE.backup.YYYYMMDD
        return self.profileBoolValue('snapshots.backup_on_restore.enabled', True, profile_id)

    def setBackupOnRestore(self, value, profile_id = None):
        self.setProfileBoolValue('snapshots.backup_on_restore.enabled', value, profile_id)

    def niceOnCron(self, profile_id=None):
        #?Run cronjobs with 'nice \-n19'. This will give BackInTime the
        #?lowest CPU priority to not interrupt any other working process.
        return self.profileBoolValue('snapshots.cron.nice', self.DEFAULT_RUN_NICE_FROM_CRON, profile_id)

    def setNiceOnCron(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.cron.nice', value, profile_id)

    def ioniceOnCron(self, profile_id=None):
        #?Run cronjobs with 'ionice \-c2 \-n7'. This will give BackInTime the
        #?lowest IO bandwidth priority to not interrupt any other working process.
        return self.profileBoolValue('snapshots.cron.ionice', self.DEFAULT_RUN_IONICE_FROM_CRON, profile_id)

    def setIoniceOnCron(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.cron.ionice', value, profile_id)

    def ioniceOnUser(self, profile_id=None):
        #?Run BackInTime with 'ionice \-c2 \-n7' when taking a manual snapshot.
        #?This will give BackInTime the lowest IO bandwidth priority to not
        #?interrupt any other working process.
        return self.profileBoolValue('snapshots.user_backup.ionice', self.DEFAULT_RUN_IONICE_FROM_USER, profile_id)

    def setIoniceOnUser(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.user_backup.ionice', value, profile_id)

    def niceOnRemote(self, profile_id=None):
        #?Run rsync and other commands on remote host with 'nice \-n19'
        return self.profileBoolValue('snapshots.ssh.nice', self.DEFAULT_RUN_NICE_ON_REMOTE, profile_id)

    def setNiceOnRemote(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.ssh.nice', value, profile_id)

    def ioniceOnRemote(self, profile_id=None):
        #?Run rsync and other commands on remote host with 'ionice \-c2 \-n7'
        return self.profileBoolValue('snapshots.ssh.ionice', self.DEFAULT_RUN_IONICE_ON_REMOTE, profile_id)

    def setIoniceOnRemote(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.ssh.ionice', value, profile_id)

    def nocacheOnLocal(self, profile_id=None):
        #?Run rsync on local machine with 'nocache'.
        #?This will prevent files from being cached in memory.
        return self.profileBoolValue('snapshots.local.nocache', self.DEFAULT_RUN_NOCACHE_ON_LOCAL, profile_id)

    def setNocacheOnLocal(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.local.nocache', value, profile_id)

    def nocacheOnRemote(self, profile_id=None):
        #?Run rsync on remote host with 'nocache'.
        #?This will prevent files from being cached in memory.
        return self.profileBoolValue('snapshots.ssh.nocache', self.DEFAULT_RUN_NOCACHE_ON_REMOTE, profile_id)

    def setNocacheOnRemote(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.ssh.nocache', value, profile_id)

    def redirectStdoutInCron(self, profile_id=None):
        #?redirect stdout to /dev/null in cronjobs
        return self.profileBoolValue('snapshots.cron.redirect_stdout', self.DEFAULT_REDIRECT_STDOUT_IN_CRON, profile_id)

    def redirectStderrInCron(self, profile_id=None):
        #?redirect stderr to /dev/null in cronjobs;;self.DEFAULT_REDIRECT_STDERR_IN_CRON
        if self.isConfigured(profile_id):
            default = True
        else:
            default = self.DEFAULT_REDIRECT_STDERR_IN_CRON
        return self.profileBoolValue('snapshots.cron.redirect_stderr', default, profile_id)

    def setRedirectStdoutInCron(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.cron.redirect_stdout', value, profile_id)

    def setRedirectStderrInCron(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.cron.redirect_stderr', value, profile_id)

    def bwlimitEnabled(self, profile_id=None):
        #?Limit rsync bandwidth usage over network. Use this with mode SSH.
        #?For mode Local you should rather use ionice.
        return self.profileBoolValue('snapshots.bwlimit.enabled', False, profile_id)

    def bwlimit(self, profile_id=None):
        #?Bandwidth limit in KB/sec.
        return self.profileIntValue('snapshots.bwlimit.value', 3000, profile_id)

    def setBwlimit(self, enabled, value, profile_id=None):
        self.setProfileBoolValue('snapshots.bwlimit.enabled', enabled, profile_id)
        self.setProfileIntValue('snapshots.bwlimit.value', value, profile_id)

    def noSnapshotOnBattery(self, profile_id=None):
        #?Don't take snapshots if the Computer runs on battery.
        return self.profileBoolValue('snapshots.no_on_battery', False, profile_id)

    def setNoSnapshotOnBattery(self, value, profile_id=None):
        self.setProfileBoolValue('snapshots.no_on_battery', value, profile_id)

    def preserveAcl(self, profile_id=None):
        #?Preserve ACL. The  source  and  destination  systems must have
        #?compatible ACL entries for this option to work properly.
        return self.profileBoolValue('snapshots.preserve_acl', False, profile_id)

    def setPreserveAcl(self, value, profile_id=None):
        return self.setProfileBoolValue('snapshots.preserve_acl', value, profile_id)

    def preserveXattr(self, profile_id=None):
        #?Preserve extended attributes (xattr).
        return self.profileBoolValue('snapshots.preserve_xattr', False, profile_id)

    def setPreserveXattr(self, value, profile_id=None):
        return self.setProfileBoolValue('snapshots.preserve_xattr', value, profile_id)

    def copyUnsafeLinks(self, profile_id=None):
        #?This tells rsync to copy the referent of symbolic links that point
        #?outside the copied tree.  Absolute symlinks are also treated like
        #?ordinary files.
        return self.profileBoolValue('snapshots.copy_unsafe_links', False, profile_id)

    def setCopyUnsafeLinks(self, value, profile_id=None):
        return self.setProfileBoolValue('snapshots.copy_unsafe_links', value, profile_id)

    def copyLinks(self, profile_id=None):
        #?When  symlinks  are  encountered, the item that they point to
        #?(the reference) is copied, rather than the symlink.
        return self.profileBoolValue('snapshots.copy_links', False, profile_id)

    def setCopyLinks(self, value, profile_id=None):
        return self.setProfileBoolValue('snapshots.copy_links', value, profile_id)

    def rsyncOptionsEnabled(self, profile_id=None):
        #?Past additional options to rsync
        return self.profileBoolValue('snapshots.rsync_options.enabled', False, profile_id)

    def rsyncOptions(self, profile_id=None):
        #?rsync options. Options must be quoted e.g. \-\-exclude-from="/path/to/my exclude file"
        return self.profileStrValue('snapshots.rsync_options.value', '', profile_id)

    def setRsyncOptions(self, enabled, value, profile_id=None):
        self.setProfileBoolValue('snapshots.rsync_options.enabled', enabled, profile_id)
        self.setProfileStrValue('snapshots.rsync_options.value', value, profile_id)

    def sshPrefixEnabled(self, profile_id=None):
        #?Add prefix to every command which run through SSH on remote host.
        return self.profileBoolValue('snapshots.ssh.prefix.enabled', False, profile_id)

    def sshPrefix(self, profile_id=None):
        #?Prefix to run before every command on remote host. Variables need to be escaped with \\$FOO.
        #?This doesn't touch rsync. So to add a prefix for rsync use
        #?\fIprofile<N>.snapshots.rsync_options.value\fR with
        #?--rsync-path="FOO=bar:\\$FOO /usr/bin/rsync"
        return self.profileStrValue('snapshots.ssh.prefix.value', self.DEFAULT_SSH_PREFIX, profile_id)

    def setSshPrefix(self, enabled, value, profile_id=None):
        self.setProfileBoolValue('snapshots.ssh.prefix.enabled', enabled, profile_id)
        self.setProfileStrValue('snapshots.ssh.prefix.value', value, profile_id)

    def sshPrefixCmd(self, profile_id=None, cmd_type=str):
        if cmd_type == list:
            if self.sshPrefixEnabled(profile_id):
                return shlex.split(self.sshPrefix(profile_id))
            else:
                return []
        if cmd_type == str:
            if self.sshPrefixEnabled(profile_id):
                return self.sshPrefix(profile_id).strip() + ' '
            else:
                return ''

    def continueOnErrors(self, profile_id = None):
        # Continue on errors. This will keep incomplete snapshots rather than
        # deleting and start over again.
        return self.profileBoolValue(
            'snapshots.continue_on_errors', True, profile_id)

    def setContinueOnErrors(self, value, profile_id=None):
        return self.setProfileBoolValue(
            'snapshots.continue_on_errors', value, profile_id)

    def useChecksum(self, profile_id=None):
        # Use checksum to detect changes rather than size + time.
        return self.profileBoolValue(
            'snapshots.use_checksum', False, profile_id)

    def setUseChecksum(self, value, profile_id=None):
        return self.setProfileBoolValue(
            'snapshots.use_checksum', value, profile_id)

    def logLevel(self, profile_id=None):
        # Log level used during takeSnapshot.
        # \n1 = Error\n2 = Changes\n3 = Info;1-3
        return self.profileIntValue(
            'snapshots.log_level', 3, profile_id)

    def setLogLevel(self, value, profile_id=None):
        return self.setProfileIntValue(
            'snapshots.log_level', value, profile_id)

    def takeSnapshotRegardlessOfChanges(self, profile_id=None):
        #?Create a new snapshot regardless if there were changes or not.
        return self.profileBoolValue(
            'snapshots.take_snapshot_regardless_of_changes',
            False,
            profile_id)

    def setTakeSnapshotRegardlessOfChanges(self, value, profile_id=None):
        return self.setProfileBoolValue(
            'snapshots.take_snapshot_regardless_of_changes',
            value,
            profile_id)

    def userCallbackNoLogging(self, profile_id=None):
        """
        Do not catch std{out|err} from user-callback script.
        The script will only write to current TTY.
        Default is to catch std{out|err} and write it to
        syslog and TTY again.
        """
        return self.profileBoolValue('user_callback.no_logging', False, profile_id)

    def globalFlock(self):
        """Prevent multiple snapshots (from different profiles or users)
        to be run at the same time
        """
        return self.boolValue('global.use_flock', False)

    def setGlobalFlock(self, value):
        self.setBoolValue('global.use_flock', value)

    def appPath(self):
        return self._APP_PATH

    def docPath(self):
        return self._DOC_PATH

    def appInstanceFile(self):
        return os.path.join(self._LOCAL_DATA_FOLDER, 'app.lock')

    def fileId(self, profile_id=None):
        if profile_id is None:
            profile_id = self.currentProfile()
        if profile_id == '1':
            return ''
        return profile_id

    def takeSnapshotLogFile(self, profile_id=None):
        return os.path.join(
            self._LOCAL_DATA_FOLDER,
            "takesnapshot_%s.log" % self.fileId(profile_id))

    def takeSnapshotMessageFile(self, profile_id=None):
        return os.path.join(
            self._LOCAL_DATA_FOLDER,
            "worker%s.message" % self.fileId(profile_id))

    def takeSnapshotProgressFile(self, profile_id=None):
        return os.path.join(
            self._LOCAL_DATA_FOLDER,
            "worker%s.progress" % self.fileId(profile_id))

    def takeSnapshotInstanceFile(self, profile_id=None):
        return os.path.join(
            self._LOCAL_DATA_FOLDER,
            "worker%s.lock" % self.fileId(profile_id))

    def takeSnapshotUserCallback(self):
        return os.path.join(self._LOCAL_CONFIG_FOLDER, "user-callback")

    def passwordCacheFolder(self):
        return os.path.join(self._LOCAL_DATA_FOLDER, "password_cache")

    def passwordCachePid(self):
        return os.path.join(self.passwordCacheFolder(), "PID")

    def passwordCacheFifo(self):
        return os.path.join(self.passwordCacheFolder(), "FIFO")

    def passwordCacheInfo(self):
        return os.path.join(self.passwordCacheFolder(), "info")

    def cronEnvFile(self):
        return os.path.join(self._LOCAL_DATA_FOLDER, "cron_env")

    def anacrontab(self, suffix=''):
        """
        Deprecated since 1.1. Just keep this to delete old anacrontab files
        """
        return os.path.join(self._LOCAL_CONFIG_FOLDER, 'anacrontab' + suffix)

    def anacrontabFiles(self):
        """
        list existing old anacrontab files
        """
        dirname, basename = os.path.split(self.anacrontab())
        for f in os.listdir(dirname):
            if f.startswith(basename):
                yield os.path.join(dirname, f)

    def anacronSpool(self):
        return os.path.join(self._LOCAL_DATA_FOLDER, 'anacron')

    def anacronSpoolFile(self, profile_id=None):
        return os.path.join(self.anacronSpool(), self.anacronJobIdentify(profile_id))

    def anacronJobIdentify(self, profile_id=None):
        if not profile_id:
            profile_id = self.currentProfile()
        profile_name = self.profileName(profile_id)
        return profile_id + '_' + profile_name.replace(' ', '_')

    def udevRulesPath(self):
        return os.path.join('/etc/udev/rules.d', '99-backintime-%s.rules' % self.user())

    def restoreLogFile(self, profile_id=None):
        return os.path.join(self._LOCAL_DATA_FOLDER, "restore_%s.log" % self.fileId(profile_id))

    def restoreInstanceFile(self, profile_id=None):
        return os.path.join(self._LOCAL_DATA_FOLDER, "restore%s.lock" % self.fileId(profile_id))

    def lastSnapshotSymlink(self, profile_id=None):
        return os.path.join(self.snapshotsFullPath(profile_id), 'last_snapshot')

    def encfsconfigBackupFolder(self, profile_id=None):
        return os.path.join(self._LOCAL_DATA_FOLDER, 'encfsconfig_backup_%s' % self.fileId(profile_id))

    def license(self):
        return tools.readFile(os.path.join(self.docPath(), 'LICENSE'), '')

    def translations(self):
        return tools.readFile(os.path.join(self.docPath(), 'TRANSLATIONS'), '')

    def authors(self):
        return tools.readFile(os.path.join(self.docPath(), 'AUTHORS'), '')

    def changelog(self):
        for i in ('CHANGES', 'changelog'):
            f = os.path.join(self.docPath(), i)
            clog = tools.readFile(f, '')
            if clog:
                return clog
        return ''

    def preparePath(self, path):
        if len(path) > 1:
            if path[-1] == os.sep:
                path = path[: -1]
        return path

    def isConfigured(self, profile_id=None):
        """
        Checks if the program is configured
        """
        return bool(self.snapshotsPath(profile_id) and self.include(profile_id))

    def canBackup(self, profile_id=None):
        """
        Checks if snapshots_path exists
        """
        if not self.isConfigured(profile_id):
            return False

        if not os.path.isdir(self.snapshotsFullPath(profile_id)):
            logger.error("%s does not exist"
                         %self.snapshotsFullPath(profile_id),
                         self)
            return False

        return True

    def backupScheduled(self, profile_id=None):
        """
        check if profile is supposed to be run this time
        """
        if self.scheduleMode(profile_id) not in (self.REPEATEDLY, self.UDEV):
            return True

        #if crontab wasn't updated since upgrading BIT to version without anacron
        #we are most likely started by anacron and should run this task without asking.
        if list(self.anacrontabFiles()):
            return True

        last_time = tools.readTimeStamp(self.anacronSpoolFile(profile_id))
        if not last_time:
            return True

        value = self.scheduleRepeatedPeriod(profile_id)
        unit = self.scheduleRepeatedUnit(profile_id)

        return self.olderThan(last_time, value, unit)

    def olderThan(self, time, value, unit):
        """
        return True if time is older than months, weeks, days or hours
        """
        assert isinstance(time, datetime.datetime), 'time is not datetime.datetime type: %s' % time

        now = datetime.datetime.now()

        if unit <= self.HOUR:
            return time < now - datetime.timedelta(hours = value)
        elif unit <= self.DAY:
            return time.date() <= now.date() - datetime.timedelta(days = value)
        elif unit <= self.WEEK:
            return time.date() < now.date() \
                                 - datetime.timedelta(days = now.date().weekday()) \
                                 - datetime.timedelta(weeks = value - 1)
        elif unit <= self.MONTH:
            firstDay = now.date() - datetime.timedelta(days = now.date().day + 1)
            for i in range(value - 1):
                if firstDay.month == 1:
                    firstDay = firstDay.replace(month = 12, year = firstDay.year - 1)
                else:
                    firstDay = firstDay.replace(month = firstDay.month - 1)
            return time.date() < firstDay
        else:
            return True

    SYSTEM_ENTRY_MESSAGE = "#Back In Time system entry, this will " \
                           "be edited by the gui:"

    def setupCron(self):
        for f in self.anacrontabFiles():
            logger.debug("Clearing anacrontab %s"
                         %f, self)
            os.remove(f)
        self.setupUdev.clean()

        oldCrontab = tools.readCrontab()

        strippedCrontab = self.removeOldCrontab(oldCrontab)
        newCrontab = self.createNewCrontab(strippedCrontab)
        if not isinstance(newCrontab, (list, tuple)):
            return newCrontab

        #save Udev rules
        try:
            if self.setupUdev.isReady and self.setupUdev.save():
                logger.debug('Udev rules added successfully', self)
        except PermissionDeniedByPolicy as e:
            logger.error(str(e), self)
            self.notifyError(str(e))
            return False

        if not newCrontab == oldCrontab:
            if not tools.checkCommand('crontab'):
                if self.scheduleMode() is self.NONE:
                    return True
                else:
                    logger.error('crontab not found.', self)
                    self.notifyError(_('Can\'t find crontab.\nAre you sure cron is installed ?\n'
                                        'If not you should disable all automatic backups.'))
                    return False
            if not tools.writeCrontab(newCrontab):
                self.notifyError(_('Failed to write new crontab.'))
                return False
        else:
            logger.debug("Crontab didn't change. Skip writing.")
        return True

    def removeOldCrontab(self, crontab):
        #We have to check if the self.SYSTEM_ENTRY_MESSAGE is in use,
        #if not then the entries are most likely from Back In Time 0.9.26
        #or earlier.
        if not self.SYSTEM_ENTRY_MESSAGE in crontab:
            #Then the system entry message has not yet been used in this crontab
            #therefore we assume all entries are system entries and clear them all.
            #This is the old behaviour
            logger.debug("Clearing all Back In Time entries", self)
            return [x for x in crontab if not 'backintime' in x]
        else:
            #clear all line peers which have a SYSTEM_ENTRY_MESSAGE followed by
            #one backintime command line
            logger.debug("Clearing system Back In Time entries", self)
            delLines = []
            for i, line in enumerate(crontab):
                if self.SYSTEM_ENTRY_MESSAGE in line and \
                    len(crontab) > i + 1 and        \
                    'backintime' in crontab[i + 1]:
                        delLines.extend((i, i + 1))
            return [line for i, line in enumerate(crontab) if i not in delLines]

    def createNewCrontab(self, oldCrontab):
        newCrontab = oldCrontab[:]
        if not tools.checkCommand('backintime'):
            logger.error("Command 'backintime' not found", self)
            return newCrontab
        for profile_id in self.profiles():
            cronLine = self.cronLine(profile_id)
            if not isinstance(cronLine, str):
                return cronLine
            if cronLine:
                newCrontab.append(self.SYSTEM_ENTRY_MESSAGE)
                newCrontab.append(cronLine.replace('{cmd}', self.cronCmd(profile_id)))

        if newCrontab == oldCrontab:
            # Leave one self.SYSTEM_ENTRY_MESSAGE in to prevent deleting of manual
            # entries if there is no automatic entry.
            newCrontab.append(self.SYSTEM_ENTRY_MESSAGE)
            newCrontab.append("#Please don't delete these two lines, or all custom backintime "
                              "entries are going to be deleted next time you call the gui options!")
        return newCrontab

    def cronLine(self, profile_id):
        """Dev note: Today are easier third party packages to handle this.
        """
        cron_line = ''
        profile_name = self.profileName(profile_id)
        backup_mode = self.scheduleMode(profile_id)
        logger.debug("Profile: %s | Automatic backup: %s"
                     % (profile_name, self.SCHEDULE_MODES[backup_mode]),
                     self)

        if self.NONE == backup_mode:
            return cron_line

        hour = self.scheduleTime(profile_id) // 100
        minute = self.scheduleTime(profile_id) % 100
        day = self.scheduleDay(profile_id)
        weekday = self.scheduleWeekday(profile_id)

        if self.AT_EVERY_BOOT == backup_mode:
            cron_line = '@reboot {cmd}'

        elif self._5_MIN == backup_mode:
            cron_line = '*/5 * * * * {cmd}'

        elif self._10_MIN == backup_mode:
            cron_line = '*/10 * * * * {cmd}'

        elif self._30_MIN == backup_mode:
            cron_line = '*/30 * * * * {cmd}'

        elif self._1_HOUR == backup_mode:
            cron_line = '0 * * * * {cmd}'

        elif self._2_HOURS == backup_mode:
            cron_line = '0 */2 * * * {cmd}'

        elif self._4_HOURS == backup_mode:
            cron_line = '0 */4 * * * {cmd}'

        elif self._6_HOURS == backup_mode:
            cron_line = '0 */6 * * * {cmd}'

        elif self._12_HOURS == backup_mode:
            cron_line = '0 */12 * * * {cmd}'

        elif self.CUSTOM_HOUR == backup_mode:
            cron_line = '0 ' + self.customBackupTime(profile_id) + ' * * * {cmd}'

        elif self.DAY == backup_mode:
            cron_line = '%s %s * * * {cmd}' % (minute, hour)

        elif self.REPEATEDLY == backup_mode:
            if self.scheduleRepeatedUnit(profile_id) <= self.DAY:
                cron_line = '*/15 * * * * {cmd}'
            else:
                cron_line = '0 * * * * {cmd}'

        elif self.UDEV == backup_mode:

            if not self.setupUdev.isReady:

                logger.error(
                    "Failed to install Udev rule for profile %s. DBus "
                    "Service 'net.launchpad.backintime.serviceHelper' "
                    "not available" % profile_id, self)

                self.notifyError(
                    _('Could not install Udev rule for '
                      'profile %(profile_id)s. DBus Service'
                      ' \'%(dbus_interface)s\' wasn\'t available')
                    % {'profile_id': profile_id,
                       'dbus_interface': 'net.launchpad.backintime.'
                                         'serviceHelper'})

            mode = self.snapshotsMode(profile_id)

            if mode == 'local':
                dest_path = self.snapshotsFullPath(profile_id)

            elif mode == 'local_encfs':
                dest_path = self.localEncfsPath(profile_id)

            else:
                logger.error(
                    'Schedule udev doesn\'t work with mode %s' % mode, self)
                self.notifyError(
                    _('Schedule udev doesn\'t work with mode %s') % mode)

                return False

            uuid = tools.uuidFromPath(dest_path)

            if uuid is None:
                # try using cached uuid
                # ?Devices uuid used to automatically set up udev rule
                # if the drive is not connected.
                uuid = self.profileStrValue(
                    'snapshots.path.uuid', '', profile_id)

                if not uuid:
                    logger.error(
                        'Couldn\'t find UUID for "%s"' % dest_path, self)
                    self.notifyError(
                        _('Couldn\'t find UUID for "%s"') % dest_path)

                    return False

            else:
                # cache uuid in config
                self.setProfileStrValue(
                    'snapshots.path.uuid', uuid, profile_id)

            try:
                self.setupUdev.addRule(self.cronCmd(profile_id), uuid)

            except (InvalidChar, InvalidCmd, LimitExceeded) as e:
                logger.error(str(e), self)
                self.notifyError(str(e))

                return False

        elif self.WEEK == backup_mode:
            cron_line = '%s %s * * %s {cmd}' % (minute, hour, weekday)

        elif self.MONTH == backup_mode:
            cron_line = '%s %s %s * * {cmd}' % (minute, hour, day)

        elif self.YEAR == backup_mode:
            cron_line = '%s %s 1 1 * {cmd}' % (minute, hour)

        return cron_line

    def cronCmd(self, profile_id):
        """
        """
        if not tools.checkCommand('backintime'):
            logger.error("Command 'backintime' not found", self)

            return

        cmd = tools.which('backintime') + ' '

        if profile_id != '1':
            cmd += '--profile-id %s ' % profile_id

        if not self._LOCAL_CONFIG_PATH is self._DEFAULT_CONFIG_PATH:
            cmd += '--config %s ' % self._LOCAL_CONFIG_PATH

        if logger.DEBUG:
            cmd += '--debug '

        cmd += 'backup-job'

        if self.redirectStdoutInCron(profile_id):
            cmd += ' >/dev/null'

        if self.redirectStderrInCron(profile_id):

            if self.redirectStdoutInCron(profile_id):
                cmd += ' 2>&1'

            else:
                cmd += ' 2>/dev/null'

        if self.ioniceOnCron(profile_id) and tools.checkCommand('ionice'):
            cmd = tools.which('ionice') + ' -c2 -n7 ' + cmd

        if self.niceOnCron(profile_id) and tools.checkCommand('nice'):
            cmd = tools.which('nice') + ' -n19 ' + cmd

        return cmd

# I don't get it why we need a __main__ here. It is a module never run allone.
# if __name__ == '__main__':
#     config = Config()
#     print("snapshots path = %s" % config.snapshotsFullPath())
