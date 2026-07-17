# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Configuration handling and logic.

This module and its `Config` class contain the application logic handling the
configuration of Back In Time. The handling of the configuration file itself
is separated in the module :py:mod:`configfile`.

Development notes:
    Some of the methods have code comments starting with `#? ` instead of
    `# `. These special comments are used to generate the manpage
    `backintime-config`. The script `create-manpage-backintime-config.py`
    parses this module for that.
"""
import os
import datetime
# import socket
import random
import getpass
import shlex
from pathlib import Path
# Workaround: Mostly relevant on TravisCI but not exclusively.
# While unittesting and without regular invocation of BIT the GNU gettext
# class-based API isn't setup yet.
# The bigger problem with config.py is that it do use translatable strings.
# Strings like this do not belong into a config file or its context.
try:
    _('Warning')
except NameError:
    _ = lambda val: val

import bitbase
import tools
# import configfile
import encode
import logger
import password
import pluginmanager
import schedule
import core_events
from storagesize import StorageSize
from exceptions import PermissionDeniedByPolicy
from konfig import Konfig
from mount import MountManager


class Config:  # (configfile.ConfigFileWithProfiles):
    APP_NAME = bitbase.APP_NAME

    # Version was introduced with 72fc490 in Sept. 2016 by Germar
    CONFIG_VERSION = 6
    """Latest or highest possible version of Back in Time's config file."""

    NONE = bitbase.ScheduleMode.DISABLED
    AT_EVERY_BOOT = bitbase.ScheduleMode.AT_EVERY_BOOT
    _5_MIN = bitbase.ScheduleMode.MINUTES_5
    _10_MIN = bitbase.ScheduleMode.MINUTES_10
    _30_MIN = bitbase.ScheduleMode.MINUTES_30
    HOUR = bitbase.ScheduleMode.HOUR
    _1_HOUR = bitbase.ScheduleMode.HOUR_1
    _2_HOURS = bitbase.ScheduleMode.HOURS_2
    _4_HOURS = bitbase.ScheduleMode.HOURS_4
    _6_HOURS = bitbase.ScheduleMode.HOURS_6
    _12_HOURS = bitbase.ScheduleMode.HOURS_12
    CUSTOM_HOUR = bitbase.ScheduleMode.CUSTOM_HOUR
    DAY = bitbase.ScheduleMode.DAY
    REPEATEDLY = bitbase.ScheduleMode.REPEATEDLY
    UDEV = bitbase.ScheduleMode.UDEV
    WEEK = bitbase.ScheduleMode.WEEK
    MONTH = bitbase.ScheduleMode.MONTH
    YEAR = bitbase.ScheduleMode.YEAR

    HOURLY_BACKUPS = bitbase.HOURLY_BACKUPS

    DEFAULT_RUN_NICE_FROM_CRON = True
    DEFAULT_RUN_NICE_ON_REMOTE = False
    DEFAULT_RUN_IONICE_FROM_CRON = True
    DEFAULT_RUN_IONICE_FROM_USER = False
    DEFAULT_RUN_IONICE_ON_REMOTE = False
    DEFAULT_RUN_NOCACHE_ON_LOCAL = False
    DEFAULT_RUN_NOCACHE_ON_REMOTE = False
    DEFAULT_SSH_PREFIX = 'PATH=/opt/bin:/opt/sbin:\\$PATH'
    DEFAULT_REDIRECT_STDOUT_IN_CRON = True
    DEFAULT_REDIRECT_STDERR_IN_CRON = False
    DEFAULT_OFFSET = 0

    ENCODE = encode.Bounce()
    # Deprecated. See issue #2424
    PLUGIN_MANAGER = pluginmanager.PluginManager()

    def __init__(self, config_path=None, data_path=None):
        """Back In Time configuration (and much more then this).

        Args:
            config_path (str): Full path to the config file
                (default: `~/.config/backintime/config`).
            data_path (str): It is $XDG_DATA_HOME (default: `~/.local/share`).
        """
        # Note: The main profiles name here is translated using the systems
        # current locale because the language code in the config file wasn't
        # read yet.
        # configfile.ConfigFileWithProfiles.__init__(self, _('Main profile'))

        # self._unsaved_profiles = []

        # HOME_FOLDER = os.path.expanduser('~')
        # DATA_FOLDER = '.local/share'
        # CONFIG_FOLDER = '.config'
        # BIT_FOLDER = 'backintime'
        # self._DEFAULT_LOCAL_DATA_FOLDER = os.path.join(HOME_FOLDER, DATA_FOLDER, BIT_FOLDER)
        # self._LOCAL_CONFIG_FOLDER = os.path.join(HOME_FOLDER, CONFIG_FOLDER, BIT_FOLDER)
        # self._MOUNT_ROOT = os.path.join(DATA_FOLDER, BIT_FOLDER, 'mnt')
        self._MOUNT_ROOT = bitbase.XDG_DATA_HOME / bitbase.BINARY_NAME_BASE / 'mnt'
        self._MOUNT_ROOT = str(self._MOUNT_ROOT)
        self._LOCAL_MOUNT_ROOT = self._MOUNT_ROOT
        self._LOCAL_DATA_FOLDER = str(bitbase.BIT_DATA_HOME)

        # if data_path:
        #     # Deprecated: --share-path was removed
        #     self.DATA_FOLDER_ROOT = data_path
        #     self._LOCAL_DATA_FOLDER = os.path.join(data_path, DATA_FOLDER, BIT_FOLDER)
        #     self._LOCAL_MOUNT_ROOT = os.path.join(data_path, self._MOUNT_ROOT)
        # else:
        #     self.DATA_FOLDER_ROOT = HOME_FOLDER
        #     self._LOCAL_DATA_FOLDER = self._DEFAULT_LOCAL_DATA_FOLDER
        #     self._LOCAL_MOUNT_ROOT = os.path.join(HOME_FOLDER, self._MOUNT_ROOT)

        # tools.makeDirs(self._LOCAL_CONFIG_FOLDER)
        # tools.makeDirs(self._LOCAL_DATA_FOLDER)
        # tools.makeDirs(self._LOCAL_MOUNT_ROOT)

        # self._DEFAULT_CONFIG_PATH = os.path.join(
        #     self._LOCAL_CONFIG_FOLDER, bitbase.FILENAME_CONFIG
        # )

        # if config_path is None:
        #     self._LOCAL_CONFIG_PATH = self._DEFAULT_CONFIG_PATH
        # else:
        #     self._LOCAL_CONFIG_PATH = os.path.abspath(config_path)
        #     self._LOCAL_CONFIG_FOLDER = os.path.dirname(self._LOCAL_CONFIG_PATH)

        # # Append local config file
        # self.append(self._LOCAL_CONFIG_PATH)

        self.current_hash_id = 'local'
        self.pw = None
        # self.forceUseChecksum = False
        self.setupUdev = tools.SetupUdev()

        self.current_profile_id = None

        language_used = tools.initiate_translation(self.language())

        # Development note (2023-08 by buhtz):
        # Not the best location for a variable like this.
        self.language_used = language_used
        """ISO-639 language code of the used language. See
        `tools._determine_current_used_language_code()` for details."""

        # Workaround: Maybe into bitbase?
        self.default_profile_name = _('Main profile')

        # Workaround
        self.setCurrentProfile('1', True)

        self.SNAPSHOT_MODES = {
            # mode: (
            #     <mounttools>,
            #     'ComboBox Text',
            #     need_pw|lbl_pw_1,
            #     need_2_pw|lbl_pw_2
            # ),
            'local': (
                None,
                _('Local'),
                False,
                False
            ),
            'local_gocryptfs': (
                None,  # gocryptfstools.GocryptfsMount,
                _('Local (encrypted)'),
                _('Encryption'),
                False
            ),
            'ssh': (
                None,  # sshtools.SSH,
                _('SSH'),
                _('SSH private key'),
                False
            ),
            'ssh_gocryptfs': (
                None,
                _('SSH (encrypted)'),
                _('SSH private key'),
                _('Encryption')
            ),
        }

    def the_dict(self) -> dict:
        """Workaround to access the raw dictionary defined in ConfigFile. See
        #1923"""
        # return self.dict
        return Konfig()._conf

    def currentProfile(self) -> str:
        return str(self.current_profile_id)

    def profiles(self) -> list[str]:
        """Workaround, return list of profile_ids as strings."""
        return [str(pid) for pid in Konfig().profile_ids]

    def profileName(self, profile_id=None) -> str:
        """Workaround"""
        p = self.get_profile(profile_id)
        return p.name

    def get_profile(self, profile_id):
        """Workaround"""
        real_konfig = Konfig()
        return real_konfig.profile(
            int(profile_id) if profile_id else self.current_profile_id
        )

    def setCurrentProfile(self, profile_id, silent: bool = False):
        """
        Change the current profile.

        Args:
            profile_id (str, int):  valid profile ID

        Returns:
            bool:                   ``True`` if successful
        """
        if isinstance(profile_id, int):
            profile_id = str(profile_id)

        if self.current_profile_id == profile_id:
            return True

        p = Konfig().profile(int(profile_id))
        self.current_profile_id = p.profile_id

        logger.changeProfile(p.profile_id, p.name)
        if not silent:
            logger.info(
                f'Profile switched: {p.name}({p.profile_id})',
                self
            )

        return True

    def setCurrentProfileByName(self, name):
        """
        Change the current profile by a given name.

        Args:
            name (str): valid profile name

        Returns:
            bool: ``True`` if successful
        """

        p = Konfig().profile(name)
        return self.setCurrentProfile(p.profile_id)

    def get_diff_cmd_and_params(self, default_cmd, default_params):
        # cmd = self.the_dict().get('qt.diff.cmd', default_cmd)
        # params = self.the_dict().get('qt.diff.params', default_params)
        # return (cmd, params)
        return Konfig().diff_cmd_and_params

    def set_diff_cmd_and_params(self, cmd, params):
        # self.the_dict()['qt.diff.cmd'] = cmd
        # self.the_dict()['qt.diff.params'] = params
        Konfig().diff_cmd_and_params = (cmd, params)

    def save(self):
        # self._unsaved_profiles = []
        # self.setIntValue('config.version', self.CONFIG_VERSION)
        # return super().save(self._LOCAL_CONFIG_PATH)
        return Konfig().save(bitbase.context['--config'])

    def is_profile_unsaved(self, profile_id: str) -> bool:
        return Konfig().is_profile_unsaved(int(profile_id))

    def is_current_profile_unsaved(self) -> bool:
        return self.is_profile_unsaved(self.currentProfile())

    def checkConfig(self, profile_id=None):
        """Dev note (2026-06, buhtz): Would say this method
        should go into its own class. e.g. CheckConfigAgent
        Who executes it? Not only by "check-config" CLI command I think.

        WEITER
        """
        if profile_id:
            profiles = [self.get_profile(profile_id)]
        else:
            real_konfig = Konfig()
            profiles = list(real_konfig.iter_profiles())

        for one_profile in profiles:
            logger.debug(f'Check {one_profile}')
            profile_id = one_profile.profile_id

            profile_name = one_profile.name
            mount_manager = MountManager.create(self)
            mount_path = mount_manager.path
            # snapshots_path = one_profile.snapshots_path

            # check the backups mountpoint (formerly known as "snapshot_path")
            if not mount_path:
                core_events.event_error.notify(
                    '{}\n{}'.format(
                        _('Profile: "{name}"').format(name=profile_name),
                        # Don't like this error message!
                        _('Backup directory is not valid.')
                    )
                )
                return False

            # check include
            include_list = self.include(profile_id)

            if not include_list:
                core_events.event_error.notify(
                    '{}\n{}'.format(
                        _('Profile: "{name}"').format(name=profile_name),
                        _('At least one directory must be selected '
                          'for backup.')
                    )
                )

                return False

            # ???
            snapshots_path2 = str(mount_path)
            if snapshots_path2[-1] != '/':
                snapshots_path2 = snapshots_path2 + '/'

            for item in include_list:
                if item[1] != 0:
                    continue

                path = item[0]
                if path == str(mount_path):
                    core_events.event_error.notify(
                        '{}\n{}\n{}'.format(
                            _('Profile: "{name}"').format(name=profile_name),
                            _('Directory: {path}').format(path=path),
                            _('This directory cannot be included in the '
                              'backup as it is part of the backup '
                              'destination itself.')
                        )
                    )

                    return False

                if len(path) >= len(snapshots_path2):
                    if path[: len(snapshots_path2)] == snapshots_path2:
                        core_events.event_error.notify(
                            '{}\n{}\n{}'.format(
                                _('Profile: "{name}"').format(
                                    name=profile_name),
                                _('Directory: {path}').format(path=path),
                                _('This directory cannot be included in the '
                                'backup as it is part of the backup '
                                'destination itself.')
                            )
                        )

                        return False

            # check warn free space
            if (self.warnFreeSpaceEnabled(profile_id)
                and self.minFreeSpaceEnabled(profile_id)):

                warn = self.warnFreeSpace(profile_id)
                _enabled, min_free = self.minFreeSpaceAsStorageSize(profile_id)

                if warn < min_free:
                    core_events.event_error.notify(
                        '{}\n{}\n\n{}\n{}'.format(
                            _('Profile: "{name}"').format(name=profile_name),
                            _('There is a conflict between two settings.'),
                            _('The value for "Remove oldest backup if the '
                              'free space is less than" ({val_one}) must be '
                              'less than or equal the threshold for "Warn if '
                              'free disk space falls below" ({val_two}).'
                              ).format(val_one=min_free, val_two=warn),
                            _('Please adjust the settings so that the backup '
                              'removal limit is not higher than the '
                              'warning limit.')
                        ))
                    return False

        return True

    # def host(self):
    #     return socket.gethostname()

    def get_snapshots_mountpoint(self, profile_id=None, mode=None, tmp_mount=False):
        """Return the profiles snapshot path in form of a mount point.

        Dev note (buhtz, 2026-03): Might become useless.
        """

        # # DEBUG
        # import traceback
        # traceback.print_stack(limit=12)
        # logger.debug(f'{profile_id=} {mode=} {tmp_mount=}', self)

        if profile_id is None:
            profile_id = self.currentProfile()

        if mode is None:
            mode = self.snapshotsMode(profile_id)

        if mode == 'local':
            return self.get_snapshots_path(profile_id)

        # ???
        symlink = f'{profile_id}_{os.getpid()}'
        if tmp_mount:
            symlink = f'tmp_{symlink}'

        return os.path.join(self._LOCAL_MOUNT_ROOT, symlink)

    def get_backup_destination_path(self, profile_id) -> Path:
        """Return the path depending on the backe mode of the profile.
        """

        mode = self.snapshotsMode(profile_id)

        if mode == 'local':
            return Path(self.get_snapshots_path(profile_id))

        if mode == 'local_gocryptfs':
            return Path(self.localGocryptfsPath(profile_id))

        raise RuntimeError(f'Unknown mode "{mode}"')

    def snapshotsPath(self, profile_id=None, mode=None, tmp_mount=False):
        """Return the snapshot path (backup destination) as a mount point.

        That method is a surrogate for `self.get_snapshots_mountpoint()`.
        """
        return self.get_snapshots_mountpoint(
            profile_id=profile_id,
            mode=mode,
            tmp_mount=tmp_mount)

    def snapshotsFullPath(self, profile_id=None):
        """
        Returns the full path for the snapshots: .../backintime/machine/user/profile_id/
        """
        host, user, profile = self.hostUserProfile(profile_id)
        return os.path.join(self.snapshotsPath(profile_id), 'backintime', host, user, profile)

    def get_snapshots_path(self, profile_id):
        """Return the value of the snapshot path (backup destination) field."""
        # return self.profileStrValue('snapshots.path', '', profile_id)
        p = self.get_profile(profile_id)
        return p.snapshots_path

    def set_snapshots_path(self, value, profile_id=None):
        """Sets the snapshot path to value."""
        # if profile_id is None:
        #     profile_id = self.currentProfile()

        # self.setProfileStrValue('snapshots.path', value, profile_id)
        p = self.get_profile(profile_id)
        p.snapshots_path = value

    def snapshotsMode(self, profile_id=None):
        #? Use mode (or backend) for this snapshot. Look at 'man backintime'
        #? section 'Modes'.;local|ssh|ssh_gocryptfs|local_gocryptfs
        # return self.profileStrValue('snapshots.mode', 'local', profile_id)
        return self.get_profile(profile_id).mode

    def setSnapshotsMode(self, value, profile_id = None):
        p = self.get_profile(profile_id)
        p.mode = value

    def systray(self) -> str:
        #?Color of systray icon.;auto,dark,light
        # return self.strValue('global.systray', 'auto')
        return Konfig().systray

    def set_systray(self, value: str) -> None:
        # self.setStrValue('global.systray', value)
        k = Konfig()
        k.systray = value

    def language(self) -> str:
        #?Language code (ISO 639) used to translate the user interface.
        #?If empty the operating systems current local is used. If 'en' the
        #?translation is not active and the original English source strings
        #?are used. It is the same if the value is unknown.
        # return self.strValue('global.language', '')
        return Konfig().language

    def setLanguage(self, language: str):
        # self.setStrValue('global.language', language if language else '')
        k = Konfig()
        k.language = language

    # SSH
    def sshSnapshotsPath(self, profile_id = None):
        #?Snapshot path on remote host. If the path is relative (no leading '/')
        #?it will start from remote Users homedir. An empty path will be replaced
        #?with './'.;absolute or relative path
        # return self.profileStrValue('snapshots.ssh.path', '', profile_id)
        p = self.get_profile(profile_id)
        return p.ssh_snapshots_path

    def sshSnapshotsFullPath(self, profile_id = None):
        """
        Returns the full path for the snapshots: .../backintime/machine/user/profile_id/
        """
        path = self.sshSnapshotsPath(profile_id)
        if not path:
            path = './'
        host, user, profile = self.hostUserProfile(profile_id)
        return os.path.join(path, 'backintime', host, user, profile)

    def setSshSnapshotsPath(self, value, profile_id = None):
        # self.setProfileStrValue('snapshots.ssh.path', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_snapshots_path = value

    def sshHost(self, profile_id = None):
        #?Remote host used for mode 'ssh' and 'ssh_gocryptfs'.;IP or domain address
        # return self.profileStrValue('snapshots.ssh.host', '', profile_id)
        return self.get_profile(profile_id).ssh_host

    def setSshHost(self, value, profile_id = None):
        # self.setProfileStrValue('snapshots.ssh.host', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_host = value

    def sshPort(self, profile_id = None):
        #?SSH Port on remote host.;0-65535
        # return self.profileIntValue('snapshots.ssh.port', '22', profile_id)
        return self.get_profile(profile_id).ssh_port

    def setSshPort(self, value, profile_id = None):
        # self.setProfileIntValue('snapshots.ssh.port', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_port = value

    def sshUser(self, profile_id = None):
        #?Remote SSH user;;local users name
        # return self.profileStrValue('snapshots.ssh.user', getpass.getuser(), profile_id)
        return self.get_profile(profile_id).ssh_user

    def setSshUser(self, value, profile_id = None):
        # self.setProfileStrValue('snapshots.ssh.user', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_user = value

    def sshPrivateKeyFile(self, profile_id=None) -> None | bool | str:
        """The field can have three states:
        1. Field does not exists: Fresh profile. Provide a default value.
        2. Field exist but is empty: Using keys is disabled.
        3. Field has a path:
        """
        # val = self.profileStrValue('snapshots.ssh.private_key_file', None, profile_id)

        # # Using keys is disabled
        # if val == '':
        #     return False

        # return val
        p = self.get_profile(profile_id)
        return p.ssh_private_key_file

    def sshPrivateKeyFile_enabled(self, profile_id=None):
        # return self.sshPrivateKeyFile(profile_id) is not False
        p = self.get_profile(profile_id)
        return p.ssh_private_key_file is not None

    def setSshPrivateKeyFile(self, value, profile_id=None):
        # self.setProfileStrValue('snapshots.ssh.private_key_file', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_private_key_file = value

    def sshProxyHost(self, profile_id=None):
        #?Proxy host used to connect to remote host.;;IP or domain address
        # return self.profileStrValue('snapshots.ssh.proxy_host', '', profile_id)
        p = self.get_profile(profile_id)
        return p.ssh_proxy_host

    def setSshProxyHost(self, value, profile_id=None):
        # self.setProfileStrValue('snapshots.ssh.proxy_host', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_proxy_host = value

    def sshProxyPort(self, profile_id=None):
        #?Proxy host port used to connect to remote host.;0-65535
        # return self.profileIntValue('snapshots.ssh.proxy_host_port', '22', profile_id)
        p = self.get_profile(profile_id)
        return p.ssh_proxy_port

    def setSshProxyPort(self, value, profile_id = None):
        # self.setProfileIntValue('snapshots.ssh.proxy_host_port', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_proxy_port = value

    def sshProxyUser(self, profile_id=None):
        #?Remote SSH user;;the local users name
        # return self.profileStrValue('snapshots.ssh.proxy_user', getpass.getuser(), profile_id)
        p = self.get_profile(profile_id)
        return p.ssh_proxy_user

    def setSshProxyUser(self, value, profile_id=None):
        # self.setProfileStrValue('snapshots.ssh.proxy_user', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_proxy_user = value

    def sshMaxArgLength(self, profile_id = None):
        #?Maximum command length of commands run on remote host. This can be tested
        #?for all ssh profiles in the configuration
        #?with 'python3 /usr/share/backintime/common/ssh_max_arg.py LENGTH'.\n
        #?0 = unlimited;0, >700

        # See #2532 about sshMaxArgs() removal.
        # value = self.profileIntValue('snapshots.ssh.max_arg_length', 0, profile_id)
        p = self.get_profile(profile_id)
        value = p.ssh_max_arg_length
        if value and value < 700:
            raise ValueError(
                f'SSH max arg length {value} is too low to run commands'
            )
        return value

    def setSshMaxArgLength(self, value, profile_id = None):
        # self.setProfileIntValue('snapshots.ssh.max_arg_length', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_max_arg_length = value

    def sshCheckCommands(self, profile_id = None):
        #?Check if all commands (used during takeSnapshot) work like expected
        #?on the remote host.
        # return self.profileBoolValue('snapshots.ssh.check_commands', True, profile_id)
        p = self.get_profile(profile_id)
        return p.ssh_check_commands

    def setSshCheckCommands(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.ssh.check_commands', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_check_commands = value

    def sshCheckPingHost(self, profile_id = None):
        #?Check if the remote host is available before trying to mount.
        # return self.profileBoolValue('snapshots.ssh.check_ping', True, profile_id)
        p = self.get_profile(profile_id)
        return p.ssh_check_ping_host

    def setSshCheckPingHost(self, value, profile_id=None):
        # self.setProfileBoolValue('snapshots.ssh.check_ping', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_check_ping_host = value

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
        if self.sshPrivateKeyFile_enabled(profile_id):
            key_file = self.sshPrivateKeyFile(profile_id)
            if key_file:
                args += ['-o', f'IdentityFile={key_file}']

        return args

    def sshCommand(self,
                   cmd=None,
                   custom_args=None,
                   port=True,
                   cipher=True,  # not functional anymore. #2491
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
        # Refactor: Use of assert is discouraged in productive code.
        # Raise Exceptions instead.
        assert cmd is None or isinstance(cmd, list), "cmd '{}' is not list instance".format(cmd)
        assert custom_args is None or isinstance(custom_args, list), "custom_args '{}' is not list instance".format(custom_args)

        ssh = ['ssh']
        ssh += self.sshDefaultArgs(profile_id)

        # Proxy (aka Jump host)
        if self.sshProxyHost(profile_id):
            ssh += ['-J', '{}@{}:{}'.format(
                self.sshProxyUser(profile_id),
                self.sshProxyHost(profile_id),
                self.sshProxyPort(profile_id)
            )]

        # remote port
        if port:
            ssh += ['-p', str(self.sshPort(profile_id))]

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
            ssh += self.sshPrefixCmd(profile_id, cmd_type=type(cmd))

        # add the command
        if cmd:
            ssh += cmd

        # close quote
        if quote and cmd:
            ssh.append("'")

        logger.debug(f'SSH command: {ssh}', self)

        return ssh

    # gocryptfs
    def localGocryptfsPath(self, profile_id):
        #?Where to save snapshots in mode 'local_gocryptfs'.;absolute path
        # return self.profileStrValue('snapshots.local_gocryptfs.path', '', profile_id)
        p = self.get_profile(profile_id)
        return p.local_gocryptfs_path

    def setLocalGocryptfsPath(self, value, profile_id):
        # self.setProfileStrValue('snapshots.local_gocryptfs.path', value, profile_id)
        p = self.get_profile(profile_id)
        p.local_gocryptfs_path = value

    def _mode_not_profile(self, profile_id, mode):
        # Why is there an extra "mode" argument in this methods signature?
        # Doesn't the profile itself defines the mode?
        if mode is None:
            return

        p = self.get_profile(profile_id)
        if p.mode != mode:
            raise RuntimeError(
                'Unexpected situation. Open an issue and report '
                'steps to reproduce the situation! '
                f'{profile_id=} -> {mode=} != {p.mode=}'
            )

    def passwordSave(self, profile_id = None, mode = None):
        # if mode is None:
        #     mode = self.snapshotsMode(profile_id)
        # self._mode_not_profile(profile_id, mode)
        #?Save password to system keyring (gnome-keyring or kwallet).
        #?<MODE> must be the same as \fIprofile<N>.snapshots.mode\fR
        # return self.profileBoolValue('snapshots.%s.password.save' % mode, False, profile_id)

        p = self.get_profile(profile_id)
        return p.password_save

    def setPasswordSave(self, value, profile_id = None, mode = None):
        # if mode is None:
        #     mode = self.snapshotsMode(profile_id)
        # self._mode_not_profile(profile_id, mode)
        # self.setProfileBoolValue('snapshots.%s.password.save' % mode, value, profile_id)
        p = self.get_profile(profile_id)
        p.password_save = value

    def passwordUseCache(self, profile_id = None, mode = None):
        # if mode is None:
        #     mode = self.snapshotsMode(profile_id)
        # self._mode_not_profile(profile_id, mode)
        #?Cache password in RAM so it can be read by cronjobs.
        #?Security issue: root might be able to read that password, too.
        #?<MODE> must be the same as \fIprofile<N>.snapshots.mode\fR;;true
        # return self.profileBoolValue('snapshots.%s.password.use_cache' % mode, True, profile_id)
        p = self.get_profile(profile_id)
        return p.password_use_cache

    def setPasswordUseCache(self, value, profile_id = None, mode = None):
        # if mode is None:
        #     mode = self.snapshotsMode(profile_id)
        # self._mode_not_profile(profile_id, mode)
        # self.setProfileBoolValue('snapshots.%s.password.use_cache' % mode, value, profile_id)
        p = self.get_profile(profile_id)
        p.password_use_cache = value

    def password(self,
                 parent=None,
                 profile_id=None,
                 mode=None,
                 pw_id=1,
                 only_from_keyring=False):
        """Dev note (2026-06, buhtz): This password stuff is an ugly mess.
        I am working on it, hoping not to break something.
        """
        if self.pw is None:
            self.pw = password.Password(self)

        # if profile_id is None:
        #     profile_id = self.currentProfile()
        p = self.get_profile(profile_id)

        # self._mode_not_profile(profile_id, mode)

        # if mode is None:
        #     mode = self.snapshotsMode(profile_id)

        return self.pw.password(
            parent=parent,
            profile_id=p.profile_id,
            mode=mode if mode else p.mode,
            pw_id=pw_id,
            only_from_keyring=only_from_keyring
        )

    def get_encryption_password(self):
        """Dirty workaround, because the meaning of password1 and password2
        depends on the mode used and differs.
        """
        mode = self.snapshotsMode()

        if 'gocryptfs' not in mode:
            raise RuntimeError(f'{mode} has no encryption password')

        # get the password container
        if self.pw is None:
            self.pw = password.Password(self)

        # local encryption
        if mode == 'local_gocryptfs':
            pw_id = 1
        elif mode == 'ssh_gocryptfs':
            pw_id = 2
        else:
            raise RuntimeError(f'Unexpected situation. {mode=}')

        return self.pw.password(
            parent=None,
            profile_id=self.currentProfile(),
            mode=mode,
            pw_id=pw_id,
            only_from_keyring=False
        )

    def setPassword(self, password_value, profile_id=None, mode=None, pw_id=1):
        if self.pw is None:
            self.pw = password.Password(self)

        if profile_id is None:
            profile_id = self.currentProfile()

        # self._mode_not_profile(profile_id, mode)

        if mode is None:
            mode = self.snapshotsMode(profile_id)

        self.pw.setPassword(password_value, profile_id, mode, pw_id)

    def modeNeedPassword(self, mode, pw_id = 1):
        need_pw = self.SNAPSHOT_MODES[mode][pw_id + 1]
        if need_pw is False:
            return False
        return True

    def keyringServiceName(self, profile_id = None, mode = None, pw_id = 1):
        if mode is None:
            mode = self.snapshotsMode(profile_id)
        if pw_id > 1:
            return 'backintime/%s_%s' % (mode, pw_id)
        return 'backintime/%s' % mode

    def keyringUserName(self, profile_id = None):
        if profile_id is None:
            profile_id = self.currentProfile()
        return 'profile_id_%s' % profile_id

    # def hostUserProfileDefault(self, profile_id=None):
    #     host = socket.gethostname()
    #     user = getpass.getuser()
    #     profile = profile_id
    #     if profile is None:
    #         profile = self.currentProfile()

    #     return (host, user, profile)

    def hostUserProfile(self, profile_id = None):
        # default_host, default_user, default_profile = self.hostUserProfileDefault(profile_id)
        p = self.get_profile(profile_id)
        # #?Set Host for snapshot path;;local hostname
        # host = self.profileStrValue('snapshots.path.host', default_host, profile_id)
        # #?Set User for snapshot path;;local username
        # user = self.profileStrValue('snapshots.path.user', default_user, profile_id)
        # #?Set Profile-ID for snapshot path;1-99999;current Profile-ID
        # profile = self.profileStrValue('snapshots.path.profile', default_profile, profile_id)

        # return (host, user, profile)
        return (
            p.snapshots_path_host,
            p.snapshots_path_user,
            str(p.snapshots_path_profile)
        )

    def setHostUserProfile(self, host, user, profile, profile_id = None):
        # self.setProfileStrValue('snapshots.path.host', host, profile_id)
        # self.setProfileStrValue('snapshots.path.user', user, profile_id)
        # self.setProfileStrValue('snapshots.path.profile', profile, profile_id)
        p = self.get_profile(profile_id)
        p.snapshots_path_host = host
        p.snapshots_path_user = user
        p.snapshots_path_profile = profile

    def include(self, profile_id=None):
        #?Include this file or folder. <I> must be a counter starting with 1;absolute path::
        #?Specify if \fIprofile<N>.snapshots.include.<I>.value\fR is a folder (0) or a file (1).;0|1;0
        # return self.profileListValue(
        #     key='snapshots.include',
        #     type_key=('str:value', 'int:type'), default=[],
        #     profile_id=profile_id
        # )
        return self.get_profile(profile_id).include


    def setInclude(self, values, profile_id = None):
        # self.setProfileListValue('snapshots.include', ('str:value', 'int:type'), values, profile_id)
        self.get_profile(profile_id).include = values

    def exclude(self, profile_id = None):
        """
        Gets the exclude patterns
        """
        #?Exclude this file or folder. <I> must be a counter
        #?starting with 1;file, folder or pattern (relative or absolute)
        # return self.profileListValue('snapshots.exclude', 'str:value', [], profile_id)
        p = self.get_profile(profile_id)
        return p.exclude

    def setExclude(self, values, profile_id = None):
        # self.setProfileListValue('snapshots.exclude', 'str:value', values, profile_id)
        p = self.get_profile(profile_id)
        p.exclude = values

    def excludeBySizeEnabled(self, profile_id = None):
        #?Enable exclude files by size.
        # return self.profileBoolValue('snapshots.exclude.bysize.enabled', False, profile_id)
        p = self.get_profile(profile_id)
        return p.exclude_by_size_enabled

    def excludeBySize(self, profile_id = None):
        #?Exclude files bigger than value in MiB.
        #?With 'Full rsync mode' disabled this will only affect new files
        #?because for rsync this is a transfer option, not an exclude option.
        #?So big files that has been backed up before will remain in snapshots
        #?even if they had changed.
        # return self.profileIntValue('snapshots.exclude.bysize.value', 500, profile_id)
        p = self.get_profile(profile_id)
        return p.exclude_by_size_enabled

    def setExcludeBySize(self, enabled, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.exclude.bysize.enabled', enabled, profile_id)
        # self.setProfileIntValue('snapshots.exclude.bysize.value', value, profile_id)
        p = self.get_profile(profile_id)
        p.exclude_by_size = value
        p.exclude_by_size_enabled = enabled

    def tag(self, profile_id = None):
        #?!ignore this in manpage
        # return self.profileStrValue('snapshots.tag', str(random.randint(100, 999)), profile_id)

        return str(random.randint(100, 999))

    def scheduleMode(self, profile_id = None):
        #?Which schedule used for crontab. The crontab entry will be
        #?generated with 'backintime check-config'.\n
        #? 0 = Disabled\n 1 = at every boot\n 2 = every 5 minute\n
        #? 4 = every 10 minute\n 7 = every 30 minute\n10 = every hour\n
        #?12 = every 2 hours\n14 = every 4 hours\n16 = every 6 hours\n
        #?18 = every 12 hours\n19 = custom defined hours\n20 = every day\n
        #?25 = daily anacron\n27 = when drive get connected\n30 = every week\n
        #?40 = every month\n80 = every year
        #?;0|1|2|4|7|10|12|14|16|18|19|20|25|27|30|40|80;0
        # value = self.profileIntValue('schedule.mode', Config.NONE.value, profile_id)
        # return bitbase.ScheduleMode(value)
        p = self.get_profile(profile_id)
        return p.schedule_mode

    def setScheduleMode(self, value, profile_id = None):
        if isinstance(value, bitbase.ScheduleMode):
            value = value.value
        # self.setProfileIntValue('schedule.mode', value, profile_id)
        p = self.get_profile(profile_id)
        p.schedule_mode = value

    def schedule_offset(self, profile_id = None):
        # return self.profileIntValue('schedule.offset', Config.DEFAULT_OFFSET, profile_id)
        p = self.get_profile(profile_id)
        return p.schedule_offset

    def set_schedule_offset(self, value, profile_id = None):
        # self.setProfileIntValue('schedule.offset', value, profile_id)
        p = self.get_profile(profile_id)
        p.schedule_offset = value

    def scheduleDebug(self, profile_id = None):
        #?Enable debug output to system log for schedule mode.
        # return self.profileBoolValue('schedule.debug', False, profile_id)
        p = self.get_profile(profile_id)
        return p.schedule_debug

    def setScheduleDebug(self, value, profile_id = None):
        # self.setProfileBoolValue('schedule.debug', value, profile_id)
        p = self.get_profile(profile_id)
        p.schedule_debug = value

    def scheduleTime(self, profile_id = None):
        #?Position-coded number with the format "hhmm" to specify the hour
        #?and minute the cronjob should start (eg. 2015 means a quarter
        #?past 8pm). Leading zeros can be omitted (eg. 30 = 0030).
        #?Only valid for
        #?\fIprofile<N>.schedule.mode\fR = 20 (daily), 30 (weekly),
        #?40 (monthly) and 80 (yearly);0-2400
        # return self.profileIntValue('schedule.time', 0, profile_id)
        p = self.get_profile(profile_id)
        return p.schedule_time

    def scheduleHourMinute(self, profile_id: str = None
                                  ) -> tuple[int, int]:
        the_time = self.scheduleTime(profile_id)
        return (the_time // 100, the_time % 100)

    def setScheduleTime(self, value, profile_id = None):
        # self.setProfileIntValue('schedule.time', value, profile_id)
        p = self.get_profile(profile_id)
        p.schedule_time = value

    def scheduleDay(self, profile_id = None):
        #?Which day of month the cronjob should run? Only valid for
        #?\fIprofile<N>.schedule.mode\fR >= 40;1-28
        # return self.profileIntValue('schedule.day', 1, profile_id)
        p = self.get_profile(profile_id)
        return p.schedule_day

    def setScheduleDay(self, value, profile_id = None):
        # self.setProfileIntValue('schedule.day', value, profile_id)
        p = self.get_profile(profile_id)
        p.schedule_day = value

    def scheduleWeekday(self, profile_id = None):
        #?Which day of week the cronjob should run? Only valid for
        #?\fIprofile<N>.schedule.mode\fR = 30;1 = monday \- 7 = sunday
        # return self.profileIntValue('schedule.weekday', 7, profile_id)
        p = self.get_profile(profile_id)
        return p.schedule_weekday

    def setScheduleWeekday(self, value, profile_id = None):
        # self.setProfileIntValue('schedule.weekday', value, profile_id)
        p = self.get_profile(profile_id)
        p.schedule_weekday = value

    def customBackupTime(self, profile_id = None):
        #?Custom hours for cronjob. Only valid for
        #?\fIprofile<N>.schedule.mode\fR = 19
        #?;comma separated int (8,12,18,23) or */3;8,12,18,23
        # return self.profileStrValue('schedule.custom_time', '8,12,18,23', profile_id)
        p = self.get_profile(profile_id)
        return p.custom_backup_time

    def setCustomBackupTime(self, value, profile_id = None):
        # self.setProfileStrValue('schedule.custom_time', value, profile_id)
        p = self.get_profile(profile_id)
        p.custom_backup_time = value

    def scheduleRepeatedPeriod(self, profile_id = None):
        #?How many units to wait between new snapshots with anacron? Only valid
        #?for \fIprofile<N>.schedule.mode\fR = 25|27
        # return self.profileIntValue('schedule.repeatedly.period', 1, profile_id)
        p = self.get_profile(profile_id)
        return p.schedule_repeated_period

    def setScheduleRepeatedPeriod(self, value, profile_id = None):
        # self.setProfileIntValue('schedule.repeatedly.period', value, profile_id)
        p = self.get_profile(profile_id)
        p.schedule_repeated_period = value

    def scheduleRepeatedUnit(self, profile_id = None):
        #?Units to wait between new snapshots with anacron.\n
        #?10 = hours\n20 = days\n30 = weeks\n40 = months\n
        #?Only valid for \fIprofile<N>.schedule.mode\fR = 25|27;
        #?10|20|30|40;20
        # value = self.profileIntValue('schedule.repeatedly.unit', bitbase.TimeUnit.DAY.value, profile_id)
        p = self.get_profile(profile_id)
        return p.schedule_repeated_unit

    def setScheduleRepeatedUnit(self, value, profile_id = None):
        # if isinstance(value, bitbase.TimeUnit):
        #     value = value.value
        if not isinstance(value, bitbase.TimeUnit):
            value = bitbase.TimeUnit(value)
        # self.setProfileIntValue('schedule.repeatedly.unit', value, profile_id)
        p = self.get_profile(profile_id)
        p.schedule_repeated_unit = value

    def removeOldSnapshots(self, profile_id = None):
                #?Remove all snapshots older than value + unit
        # return (
        #     self.profileBoolValue(
        #         'snapshots.remove_old_snapshots.enabled', True, profile_id
        #     ),
        #     #?Snapshots older than this times units will be removed
        #     self.profileIntValue(
        #         'snapshots.remove_old_snapshots.value', 10, profile_id
        #     ),
        #     #?20 = days\n30 = weeks\n80 = years;20|30|80;80
        #     bitbase.TimeUnit(self.profileIntValue(
        #         'snapshots.remove_old_snapshots.unit',
        #         bitbase.TimeUnit.YEAR,
        #         profile_id
        #     ))
        # )
        p = self.get_profile(profile_id)
        return (
            p.remove_old_snapshots_enabled,
            p.remove_old_snapshots_value,
            p.remove_old_snapshots_unit
        )

    # def keepOnlyOneSnapshot(self, profile_id = None):
    #     #?NOT YET IMPLEMENTED. Remove all snapshots but one.
    #     return self.profileBoolValue('snapshots.keep_only_one_snapshot.enabled', False, profile_id)

    # def setKeepOnlyOneSnapshot(self, value, profile_id = None):
    #     self.setProfileBoolValue('snapshots.keep_only_one_snapshot.enabled', value, profile_id)

    def removeOldSnapshotsEnabled(self, profile_id = None):
        # return self.profileBoolValue('snapshots.remove_old_snapshots.enabled', True, profile_id)
        p = self.get_profile(profile_id)
        return p.remove_old_snapshots_enabled

    def removeOldSnapshotsDate(self, profile_id=None):
        enabled, value, unit = self.removeOldSnapshots(profile_id)
        if not enabled:
            return datetime.date(1, 1, 1)

        return _remove_old_snapshots_date(value, unit)

    def setRemoveOldSnapshots(self, enabled, value, unit, profile_id=None):
        # self.setProfileBoolValue(
        #     'snapshots.remove_old_snapshots.enabled', enabled, profile_id)
        # self.setProfileIntValue('snapshots.remove_old_snapshots.value', value, profile_id)
        # self.setProfileIntValue('snapshots.remove_old_snapshots.unit', unit, profile_id)
        p = self.get_profile(profile_id)
        p.remove_old_snapshots_enabled = enabled
        p.remove_old_snapshots_value = value
        p.remove_old_snapshots_unit = bitbase.TimeUnit(unit)

    def warnFreeSpaceEnabled(self, profile_id=None):
        p = self.get_profile(profile_id)
        return p.warn_free_space_enabled

    def warnFreeSpace(self, profile_id=None) -> StorageSize:
        p = self.get_profile(profile_id)
        return p.warn_free_space

    def setWarnFreeSpaceDisabled(self, profile_id=None):
        p = self.get_profile(profile_id)
        p.set_warn_free_space_disabled()

    def setWarnFreeSpace(self, value: StorageSize, profile_id=None):
        p = self.get_profile(profile_id)
        p.warn_free_space = value

    def minFreeSpace(self, profile_id = None):
                #?Remove snapshots until \fIprofile<N>.snapshots.min_free_space.value\fR
                #?free space is reached.

        # return (
        #     self.profileBoolValue('snapshots.min_free_space.enabled', True, profile_id),
        #     #?Keep at least value + unit free space.;1-99999
        #     self.profileIntValue('snapshots.min_free_space.value', 1, profile_id),
        #     #?10 = MB\n20 = GB;10|20;20
        #     SizeUnit(self.profileIntValue('snapshots.min_free_space.unit', SizeUnit.GIB, profile_id))
        # )
        p = self.get_profile(profile_id)
        size = p.min_free_space
        return (
            p.min_free_space_enabled,
            size.value(),
            size.unit.value
        )


    def minFreeSpaceAsStorageSize(self, profile_id = None):
        # enabled, value, unit = self.minFreeSpace(profile_id)
        p = self.get_profile(profile_id)
        return (
            p.min_free_space_enabled,
            p.min_free_space
        )

    def minFreeSpaceEnabled(self, profile_id = None):
        # return self.profileBoolValue('snapshots.min_free_space.enabled', False, profile_id)
        p = self.get_profile(profile_id)
        return p.min_free_space_enabled

    def setMinFreeSpace(self, enabled, value, unit, profile_id = None):
        # self.setProfileBoolValue('snapshots.min_free_space.enabled', enabled, profile_id)
        # self.setProfileIntValue('snapshots.min_free_space.value', value, profile_id)
        # self.setProfileIntValue('snapshots.min_free_space.unit', unit, profile_id)
        raise RuntimeError('Use setMinFreeSpaceWithStorageSize()')

    def setMinFreeSpaceWithStorageSize(self, enabled, value: StorageSize, profile_id = None):
        # self.setMinFreeSpace(
        #     enabled=enabled,
        #     value=value.value(),
        #     unit=value.unit.value,
        #     profile_id=profile_id
        # )
        p = self.get_profile(profile_id)
        p.set_min_free_space_enabled(enabled)
        p.min_free_space = value

    def minFreeInodes(self, profile_id = None):
        #?Keep at least value % free inodes.;1-15
        # return self.profileIntValue('snapshots.min_free_inodes.value', 2, profile_id)
        p = self.get_profile(profile_id)
        return p.min_free_inodes_value

    def minFreeInodesEnabled(self, profile_id = None):
        #?Remove snapshots until \fIprofile<N>.snapshots.min_free_inodes.value\fR
        #?free inodes in % is reached.
        # return self.profileBoolValue('snapshots.min_free_inodes.enabled', False, profile_id)
        p = self.get_profile(profile_id)
        return p.min_free_inodes_enabled

    def setMinFreeInodes(self, enabled, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.min_free_inodes.enabled', enabled, profile_id)
        # self.setProfileIntValue('snapshots.min_free_inodes.value', value, profile_id)
        p = self.get_profile(profile_id)
        p.min_free_inodes_enabled = enabled
        p.min_free_inodes_value = value

    def dontRemoveNamedSnapshots(self, profile_id = None):
        #?Keep snapshots with names during smart_remove.
        # return self.profileBoolValue('snapshots.dont_remove_named_snapshots', True, profile_id)
        p = self.get_profile(profile_id)
        return p.dont_remove_named_snapshots

    def setDontRemoveNamedSnapshots(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.dont_remove_named_snapshots', value, profile_id)
        p = self.get_profile(profile_id)
        p.dont_remove_named_snapshots = value

    def smartRemove(self, profile_id = None):
                #?Run smart_remove to clean up old snapshots after a new snapshot was created.
        # return (self.profileBoolValue('snapshots.smart_remove', False, profile_id),
        #         #?Keep all snapshots for X days.
        #         self.profileIntValue('snapshots.smart_remove.keep_all', 2, profile_id),
        #         #?Keep one snapshot per day for X days.
        #         self.profileIntValue('snapshots.smart_remove.keep_one_per_day', 7, profile_id),
        #         #?Keep one snapshot per week for X weeks.
        #         self.profileIntValue('snapshots.smart_remove.keep_one_per_week', 4, profile_id),
        #         #?Keep one snapshot per month for X month.
        #         self.profileIntValue('snapshots.smart_remove.keep_one_per_month', 24, profile_id))
        p = self.get_profile(profile_id)
        return (
            p.smart_remove,
            p.smart_remove_keep_all,
            p.smart_remove_keep_one_per_day,
            p.smart_remove_keep_one_per_week,
            p.smart_remove_keep_one_per_month
        )

    def setSmartRemove(self,
                       value,
                       keep_all,
                       keep_one_per_day,
                       keep_one_per_week,
                       keep_one_per_month,
                       profile_id = None):
        # self.setProfileBoolValue('snapshots.smart_remove', value, profile_id)
        # self.setProfileIntValue('snapshots.smart_remove.keep_all', keep_all, profile_id)
        # self.setProfileIntValue('snapshots.smart_remove.keep_one_per_day', keep_one_per_day, profile_id)
        # self.setProfileIntValue('snapshots.smart_remove.keep_one_per_week', keep_one_per_week, profile_id)
        # self.setProfileIntValue('snapshots.smart_remove.keep_one_per_month', keep_one_per_month, profile_id)
        p = self.get_profile(profile_id)
        p.smart_remove = value
        p.smart_remove_keep_all = keep_all
        p.smart_remove_keep_one_per_day = keep_one_per_day
        p.smart_remove_keep_one_per_week = keep_one_per_week
        p.smart_remove_keep_one_per_month = keep_one_per_month

    def smartRemoveRunRemoteInBackground(self, profile_id = None):
        #?If using mode SSH or SSH-encrypted, run smart_remove in background on remote machine
        # return self.profileBoolValue('snapshots.smart_remove.run_remote_in_background', False, profile_id)
        p = self.get_profile(profile_id)
        return p.smart_remove_run_remote_in_background

    def setSmartRemoveRunRemoteInBackground(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.smart_remove.run_remote_in_background', value, profile_id)
        p = self.get_profile(profile_id)
        p.smart_remove_run_remote_in_background = value

    def notify(self, profile_id = None):
        #?Display notifications (errors, warnings) through libnotify.
        # return self.profileBoolValue('snapshots.notify.enabled', True, profile_id)
        p = self.get_profile(profile_id)
        return p.notify

    def setNotify(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.notify.enabled', value, profile_id)
        p = self.get_profile(profile_id)
        p.notify = value

    def backupOnRestore(self, profile_id = None):
        #?Rename existing files before restore into FILE.backup.YYYYMMDD
        # return self.profileBoolValue('snapshots.backup_on_restore.enabled', True, profile_id)
        p = self.get_profile(profile_id)
        return p.backup_on_restore

    def setBackupOnRestore(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.backup_on_restore.enabled', value, profile_id)
        p = self.get_profile(profile_id)
        p.backup_on_restore = value

    def niceOnCron(self, profile_id = None):
        #?Run cronjobs with 'nice \-n19'. This will give BackInTime the
        #?lowest CPU priority to not interrupt any other working process.
        # return self.profileBoolValue('snapshots.cron.nice', self.DEFAULT_RUN_NICE_FROM_CRON, profile_id)
        p = self.get_profile(profile_id)
        return p.ionice_on_cron

    def setNiceOnCron(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.cron.nice', value, profile_id)
        p = self.get_profile(profile_id)
        p.ionice_on_cron = value

    def ioniceOnCron(self, profile_id = None):
        #?Run cronjobs with 'ionice \-c2 \-n7'. This will give BackInTime the
        #?lowest IO bandwidth priority to not interrupt any other working process.
        # return self.profileBoolValue('snapshots.cron.ionice', self.DEFAULT_RUN_IONICE_FROM_CRON, profile_id)
        p = self.get_profile(profile_id)
        return p.ionice_on_cron

    def setIoniceOnCron(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.cron.ionice', value, profile_id)
        p = self.get_profile(profile_id)
        p.ionice_on_cron = value

    def ioniceOnUser(self, profile_id = None):
        #?Run BackInTime with 'ionice \-c2 \-n7' when taking a manual snapshot.
        #?This will give BackInTime the lowest IO bandwidth priority to not
        #?interrupt any other working process.
        # return self.profileBoolValue('snapshots.user_backup.ionice', self.DEFAULT_RUN_IONICE_FROM_USER, profile_id)
        p = self.get_profile(profile_id)
        return p.ionice_on_user

    def setIoniceOnUser(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.user_backup.ionice', value, profile_id)
        p = self.get_profile(profile_id)
        p.ionice_on_user = value

    def niceOnRemote(self, profile_id = None):
        #?Run rsync and other commands on remote host with 'nice \-n19'
        # return self.profileBoolValue('snapshots.ssh.nice', self.DEFAULT_RUN_NICE_ON_REMOTE, profile_id)
        p = self.get_profile(profile_id)
        return p.nice_on_remote

    def setNiceOnRemote(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.ssh.nice', value, profile_id)
        p = self.get_profile(profile_id)
        p.nice_on_remote = value

    def ioniceOnRemote(self, profile_id = None):
        #?Run rsync and other commands on remote host with 'ionice \-c2 \-n7'
        # return self.profileBoolValue('snapshots.ssh.ionice', self.DEFAULT_RUN_IONICE_ON_REMOTE, profile_id)
        p = self.get_profile(profile_id)
        return p.ionice_on_remote

    def setIoniceOnRemote(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.ssh.ionice', value, profile_id)
        p = self.get_profile(profile_id)
        p.ionice_on_remote = value

    def nocacheOnLocal(self, profile_id = None):
        #?Run rsync on local machine with 'nocache'.
        #?This will prevent files from being cached in memory.
        # return self.profileBoolValue('snapshots.local.nocache', self.DEFAULT_RUN_NOCACHE_ON_LOCAL, profile_id)
        p = self.get_profile(profile_id)
        return p.nocache_on_local

    def setNocacheOnLocal(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.local.nocache', value, profile_id)
        p = self.get_profile(profile_id)
        p.nocache_on_local = value

    def nocacheOnRemote(self, profile_id = None):
        #?Run rsync on remote host with 'nocache'.
        #?This will prevent files from being cached in memory.
        # return self.profileBoolValue('snapshots.ssh.nocache', self.DEFAULT_RUN_NOCACHE_ON_REMOTE, profile_id)
        p = self.get_profile(profile_id)
        return p.nocache_on_remote

    def setNocacheOnRemote(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.ssh.nocache', value, profile_id)
        p = self.get_profile(profile_id)
        p.nocache_on_remote = value

    def redirectStdoutInCron(self, profile_id = None):
        #?redirect stdout to /dev/null in cronjobs
        # return self.profileBoolValue('snapshots.cron.redirect_stdout', self.DEFAULT_REDIRECT_STDOUT_IN_CRON, profile_id)
        p = self.get_profile(profile_id)
        return p.redirect_stdout_in_cron

    def redirectStderrInCron(self, profile_id = None):
        #?redirect stderr to /dev/null in cronjobs;;self.DEFAULT_REDIRECT_STDERR_IN_CRON
        # if self.isConfigured(profile_id):
        #     default = True
        # else:
        #     default = self.DEFAULT_REDIRECT_STDERR_IN_CRON
        # return self.profileBoolValue('snapshots.cron.redirect_stderr', default, profile_id)
        p = self.get_profile(profile_id)
        return p.redirect_stderr_in_cron

    def setRedirectStdoutInCron(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.cron.redirect_stdout', value, profile_id)
        p = self.get_profile(profile_id)
        p.redirect_stdout_in_cron = value

    def setRedirectStderrInCron(self, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.cron.redirect_stderr', value, profile_id)
        p = self.get_profile(profile_id)
        p.redirect_stderr_in_cron = value

    def bwlimitEnabled(self, profile_id = None):
        #?Limit rsync bandwidth usage over network. Use this with mode SSH.
        #?For mode Local you should rather use ionice.
        # return self.profileBoolValue('snapshots.bwlimit.enabled', False, profile_id)
        p = self.get_profile(profile_id)
        return p.bw_limit_enabled

    def bwlimit(self, profile_id = None):
        #?Bandwidth limit in KB/sec.
        # return self.profileIntValue('snapshots.bwlimit.value', 3000, profile_id)
        p = self.get_profile(profile_id)
        return p.bw_limit

    def setBwlimit(self, enabled, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.bwlimit.enabled', enabled, profile_id)
        # self.setProfileIntValue('snapshots.bwlimit.value', value, profile_id)
        p = self.get_profile(profile_id)
        p.bw_limit_enabled = enabled
        p.bw_limit = value

    def noSnapshotOnBattery(self, profile_id = None):
        #?Don't take snapshots if the Computer runs on battery.
        # return self.profileBoolValue('snapshots.no_on_battery', False, profile_id)
        p = self.get_profile(profile_id)
        return p.no_backup_on_battery

    def setNoSnapshotOnBattery(self, value, profile_id=None):
        # self.setProfileBoolValue('snapshots.no_on_battery', value, profile_id)
        p = self.get_profile(profile_id)
        p.no_backup_on_battery = value

    # --- WEITER WEITER WEITER
    def preserveAcl(self, profile_id=None):
        #?Preserve ACL. The  source  and  destination  systems must have
        #?compatible ACL entries for this option to work properly.
        # return self.profileBoolValue('snapshots.preserve_acl', False, profile_id)
        p = self.get_profile(profile_id)
        return p.preserve_acl

    def setPreserveAcl(self, value, profile_id = None):
        # return self.setProfileBoolValue('snapshots.preserve_acl', value, profile_id)
        p = self.get_profile(profile_id)
        p.preserve_acl = value

    def preserveXattr(self, profile_id = None):
        #?Preserve extended attributes (xattr).
        # return self.profileBoolValue('snapshots.preserve_xattr', False, profile_id)
        p = self.get_profile(profile_id)
        return p.preserve_xattr

    def setPreserveXattr(self, value, profile_id = None):
        # return self.setProfileBoolValue('snapshots.preserve_xattr', value, profile_id)
        p = self.get_profile(profile_id)
        p.preserve_xattr = value

    def copyUnsafeLinks(self, profile_id = None):
        #?This tells rsync to copy the referent of symbolic links that point
        #?outside the copied tree.  Absolute symlinks are also treated like
        #?ordinary files.
        # return self.profileBoolValue('snapshots.copy_unsafe_links', False, profile_id)
        p = self.get_profile(profile_id)
        return p.copy_unsafe_links

    def setCopyUnsafeLinks(self, value, profile_id = None):
        # return self.setProfileBoolValue('snapshots.copy_unsafe_links', value, profile_id)
        p = self.get_profile(profile_id)
        p.copy_unsafe_links = value

    def copyLinks(self, profile_id=None):
        #?When symlinks are encountered, the item that they point to
        #?(the reference) is copied, rather than the symlink.
        # return self.profileBoolValue('snapshots.copy_links', False, profile_id)
        p = self.get_profile(profile_id)
        return p.copy_links

    def setCopyLinks(self, value, profile_id = None):
        # return self.setProfileBoolValue('snapshots.copy_links', value, profile_id)
        p = self.get_profile(profile_id)
        p.copy_links = value

    def oneFileSystem(self, profile_id = None):
        #?Use rsync's "--one-file-system" to avoid crossing filesystem
        #?boundaries when recursing.
        # return self.profileBoolValue('snapshots.one_file_system', False, profile_id)
        p = self.get_profile(profile_id)
        return p.one_file_system

    def setOneFileSystem(self, value, profile_id = None):
        # return self.setProfileBoolValue('snapshots.one_file_system', value, profile_id)
        p = self.get_profile(profile_id)
        p.one_file_system = value

    def rsyncOptionsEnabled(self, profile_id = None):
        #?Past additional options to rsync
        # return self.profileBoolValue('snapshots.rsync_options.enabled', False, profile_id)
        p = self.get_profile(profile_id)
        return p.rsync_options_enabled

    def rsyncOptions(self, profile_id = None):
        #?rsync options. Options must be quoted e.g. \-\-exclude-from="/path/to/my exclude file"
        # return self.profileStrValue('snapshots.rsync_options.value', '', profile_id)
        p = self.get_profile(profile_id)
        return p.rsync_options

    def setRsyncOptions(self, enabled, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.rsync_options.enabled', enabled, profile_id)
        # self.setProfileStrValue('snapshots.rsync_options.value', value, profile_id)
        p = self.get_profile(profile_id)
        p.rsync_options = value
        p.rsync_options_enabled = enabled

    def sshPrefixEnabled(self, profile_id = None):
        #?Add prefix to every command which run through SSH on remote host.
        # return self.profileBoolValue('snapshots.ssh.prefix.enabled', False, profile_id)
        p = self.get_profile(profile_id)
        return p.ssh_prefix_enabled

    def sshPrefix(self, profile_id=None):
        #?Prefix to run before every command on remote host. Variables need to be escaped with \\$FOO.
        #?This doesn't touch rsync. So to add a prefix for rsync use
        #?\fIprofile<N>.snapshots.rsync_options.value\fR with
        #?--rsync-path="FOO=bar:\\$FOO /usr/bin/rsync"
        # return self.profileStrValue('snapshots.ssh.prefix.value', self.DEFAULT_SSH_PREFIX, profile_id)
        p = self.get_profile(profile_id)
        return p.ssh_prefix

    def setSshPrefix(self, enabled, value, profile_id = None):
        # self.setProfileBoolValue('snapshots.ssh.prefix.enabled', enabled, profile_id)
        # self.setProfileStrValue('snapshots.ssh.prefix.value', value, profile_id)
        p = self.get_profile(profile_id)
        p.ssh_prefix = value
        p.ssh_prefix_enabled = enabled

    def sshPrefixCmd(self, profile_id=None, cmd_type=str):
        """Return the config value of sshPrefix if enabled.

        Dev note by buhtz (2024-04): Good opportunity to refactor. To much
        implicit behavior in it.
        """
        if cmd_type == list:
            if self.sshPrefixEnabled(profile_id):
                return shlex.split(self.sshPrefix(profile_id))

            return []

        if cmd_type == str:
            if self.sshPrefixEnabled(profile_id):
                return self.sshPrefix(profile_id).strip() + ' '

            return ''

        raise TypeError(f'Unable to handle type {cmd_type}.')

    def continueOnErrors(self, profile_id = None):
        #?Continue on errors. This will keep incomplete snapshots rather than
        #?deleting and start over again.
        # return self.profileBoolValue('snapshots.continue_on_errors', True, profile_id)
        p = self.get_profile(profile_id)
        return p.continue_on_errors

    def setContinueOnErrors(self, value, profile_id = None):
        # return self.setProfileBoolValue('snapshots.continue_on_errors', value, profile_id)
        p = self.get_profile(profile_id)
        p.continue_on_errors = value

    def useChecksum(self, profile_id = None):
        #?Use checksum to detect changes rather than size + time.
        # return self.profileBoolValue('snapshots.use_checksum', False, profile_id)
        p = self.get_profile(profile_id)
        return p.use_checksum

    def setUseChecksum(self, value, profile_id = None):
        # return self.setProfileBoolValue('snapshots.use_checksum', value, profile_id)
        p = self.get_profile(profile_id)
        p.use_checksum = value

    def logLevel(self, profile_id = None):
        #?Log level used during takeSnapshot.\n1 = Error\n2 = Changes\n3 = Info;1-3
        # return self.profileIntValue('snapshots.log_level', 3, profile_id)
        p = self.get_profile(profile_id)
        return p.log_level

    def setLogLevel(self, value, profile_id = None):
        # return self.setProfileIntValue('snapshots.log_level', value, profile_id)
        p = self.get_profile(profile_id)
        p.log_level = value

    def takeSnapshotRegardlessOfChanges(self, profile_id = None):
        #?Create a new snapshot regardless if there were changes or not.
        # return self.profileBoolValue('snapshots.take_snapshot_regardless_of_changes', False, profile_id)
        p = self.get_profile(profile_id)
        return p.take_snapshot_regardless_of_changes

    def setTakeSnapshotRegardlessOfChanges(self, value, profile_id = None):
        # return self.setProfileBoolValue('snapshots.take_snapshot_regardless_of_changes', value, profile_id)
        p = self.get_profile(profile_id)
        p.take_snapshot_regardless_of_changes = value

    def globalFlock(self):
        #?Prevent multiple snapshots (from different profiles or users) to be run at the same time
        # return self.boolValue('global.use_flock', False)
        k = Konfig()
        return k.global_flock

    def setGlobalFlock(self, value):
        # self.setBoolValue('global.use_flock', value)
        k = Konfig()
        k.global_flock = value

    # def appInstanceFile(self):
    #     return os.path.join(self._LOCAL_DATA_FOLDER, 'app.lock')

    def fileId(self, profile_id=None):
        if profile_id is None:
            profile_id = self.currentProfile()

        if profile_id == '1':
            return ''

        return profile_id

    def takeSnapshotLogFile(self, profile_id=None):
        return os.path.join(self._LOCAL_DATA_FOLDER,
                            "takesnapshot_%s.log" % self.fileId(profile_id))

    def takeSnapshotMessageFile(self, profile_id=None):
        return os.path.join(self._LOCAL_DATA_FOLDER,
                            "worker%s.message" % self.fileId(profile_id))

    def takeSnapshotProgressFile(self, profile_id=None):
        return os.path.join(self._LOCAL_DATA_FOLDER,
                            "worker%s.progress" % self.fileId(profile_id))

    def takeSnapshotInstanceFile(self, profile_id=None):
        return os.path.join(
            self._LOCAL_DATA_FOLDER,
            "worker%s.lock" % self.fileId(profile_id))

    def takeSnapshotUserCallback(self):
        # return os.path.join(self._LOCAL_CONFIG_FOLDER, "user-callback")
        return str(bitbase.DEFAULT_CONFIG_FILE_PATH.parent / 'user-callback')

    def passwordCacheFolder(self):
        return os.path.join(self._LOCAL_DATA_FOLDER, "password_cache")

    def passwordCachePid(self):
        return os.path.join(self.passwordCacheFolder(), "PID")

    def passwordCacheFifo(self):
        return os.path.join(self.passwordCacheFolder(), "FIFO")

    def cronEnvFile(self):
        return os.path.join(self._LOCAL_DATA_FOLDER, "cron_env")

    def anacronSpool(self):
        # ~/.local/share/backintime/anacron
        return os.path.join(self._LOCAL_DATA_FOLDER, 'anacron')

    def anacronSpoolFile(self, profile_id=None):
        """Return the timestamp file related to the current profile.

        Despite the methods name anacron is not involved. But the anacron
        behavior is imitated by Back In Time. This timestamp files are an
        element of this behavior.
        """
        # ~/.local/share/backintime/anacron/1_Main_profile
        return os.path.join(self.anacronSpool(),
                            self.anacronJobIdentify(profile_id))

    def anacronJobIdentify(self, profile_id=None):
        if not profile_id:
            profile_id = self.currentProfile()

        profile_name = self.profileName(profile_id)

        # "Main profile" -> "1_Main_profile"
        return profile_id + '_' + profile_name.replace(' ', '_')

    def udevRulesPath(self):
        return os.path.join(
            '/etc/udev/rules.d',
            '99-backintime-%s.rules' % getpass.getuser()
        )

    def restoreLogFile(self, profile_id=None):
        return os.path.join(
            self._LOCAL_DATA_FOLDER,
            "restore_%s.log" % self.fileId(profile_id)
        )

    def restoreInstanceFile(self, profile_id=None):
        return os.path.join(
            self._LOCAL_DATA_FOLDER,
            "restore%s.lock" % self.fileId(profile_id))

    def lastSnapshotSymlink(self, profile_id = None):
        return os.path.join(self.snapshotsFullPath(profile_id), bitbase.DIR_NAME_LAST_SNAPSHOT)

    def isConfigured(self, profile_id=None) -> bool:
        """Checks if the program is configured.

        It is assumed as configured if a snapshot path (backup destination)
        and include files/directories (backup source) are given.

        Dev note (2026-06, buhtz): I don't see much value in this. Today the
        GUI initiates enough check and validations before storing new or
        modified profile.
        """
        p = self.get_profile(profile_id)
        profile_id = str(p.profile_id)

        path = self.snapshotsPath(profile_id)
        includes = self.include(profile_id)

        if bool(path and includes):
            return True

        logger.debug(f'Profile ({profile_id=}) is not configured because '
                     f'backup path is "{bool(path)}" and/or includes '
                     f'are "{bool(includes)}".', self)

        return False

    def backupScheduled(self, profile_id = None):
        """Check if the profile is supposed to be run this time.

        Returns:
            (bool): The answer.
        """
        if self.scheduleMode(profile_id) not in (
                bitbase.ScheduleMode.REPEATEDLY,
                bitbase.ScheduleMode.UDEV):
            return True

        last_time = tools.readTimeStamp(self.anacronSpoolFile(profile_id))
        if not last_time:
            return True

        return tools.crossed_at_least_units(
            start=last_time,
            end=datetime.datetime.now(),
            value=self.scheduleRepeatedPeriod(profile_id),
            unit=self.scheduleRepeatedUnit(profile_id)
        )

    def setup_automation(self):
        """Update schedule and event base automated backup job execution.

        This affects crontab and udev rules.
        """
        self._setup_schedule_based_automation()
        self._setup_event_based_automation()

    def _setup_event_based_automation(self):
        """Update udev rules for event based automated profiles."""
        self.setupUdev.clean()

        profile_ids = self.profile_ids_automated_via_udev_evnts()

        if not len(profile_ids):
            return

        for pid in profile_ids:
            backup_mode = self.snapshotsMode(pid)
            if backup_mode == 'local':
                dest_path = self.snapshotsFullPath(pid)
            elif backup_mode == 'local_gocryptfs':
                dest_path = self.localGocryptfsPath(pid)
            else:
                logger.error(
                    f"Udev scheduling doesn't work with mode {backup_mode}",
                    self)
                core_events.event_error.notify(_(
                    "Udev schedule doesn't work with mode {mode}")
                    .format(mode=backup_mode))
                return

            # Add rule
            schedule.add_udev_rule(
                pid=pid,
                udev_setup=self.setupUdev,
                dest_path=dest_path,
                exec_command=self._cron_cmd(pid)
            )

        # Save Udev rules
        try:
            if self.setupUdev.isReady and self.setupUdev.save():
                logger.debug('Udev rules added successfully', self)

        except PermissionDeniedByPolicy as err:
            logger.error(str(err), self)
            core_events.event_error.notify(str(err))
            return False

    def _setup_schedule_based_automation(self):
        """Update the current users crontab file based on profile settings.

        The crontab files is read, all entries related to Back In Time are
        removed and after it added again for each profile based on the profile
        settings. The difference between a backintime related entry created
        by Back In Time itself or by the user manually is determined by a
        comment before each entry. See :data:`schedule._MARKER` and
        :func:`schedule.remove_bit_from_crontab()` for details.

        Returns:
            bool: ``True`` if successful or ``False`` on errors.
        """

        # Lines of current users crontab file
        org_crontab_lines = schedule.read_crontab()

        # Remove all auto-generated BIT entries from crontab
        crontab_lines = schedule.remove_bit_from_crontab(org_crontab_lines)

        # Add a new entry to existing crontab content based on the current
        # snapshot profile and its schedule settings.
        crontab_lines = schedule.append_bit_to_crontab(
            crontab_lines,
            self.profiles_cron_lines())

        # Crontab modified?
        if crontab_lines == org_crontab_lines:
            return

        if schedule.write_crontab(crontab_lines) is False:
            logger.error('Failed to write new crontab.')
            core_events.event_error.notify(
                _('Failed to write new crontab.')
            )
            return

        if not schedule.is_cron_running():
            logger.error(
                'Cron is not running despite the crontab command being '
                'available. Scheduled backup jobs will not run.')
            core_events.event_error.notify(_(
                'Cron is not running, even though the crontab command is '
                'available. Scheduled backup jobs will not run. '
                'Cron might be installed but not enabled. Try running the two '
                'commands "systemctl enable cron" and '
                '"systemctl start cron", or consult the support channels of '
                'the currently used GNU/Linux distribution for assistance.'
            ))

    def profile_ids_automated_via_cron_schedule(self):
        """Return list of profile ids configured to time based automation
        using cron rules."""
        return list(filter(
            lambda pid: bitbase.ScheduleMode(self.scheduleMode(pid))
            not in (bitbase.ScheduleMode.DISABLED,
                    bitbase.ScheduleMode.UDEV),
            self.profiles()
        ))

    def profile_ids_automated_via_udev_evnts(self):
        """Return list of profile ids configured to event based automation
        using udev."""

        return list(filter(
            lambda pid: bitbase.ScheduleMode(self.scheduleMode(pid))
            == bitbase.ScheduleMode.UDEV,
            self.profiles()
        ))

    def profiles_cron_lines(self):
        """Return a list of crontab lines for each of the existing profiles.

        Return:
            list: The list of crontab lines.
        """
        profile_ids = self.profile_ids_automated_via_cron_schedule()
        return [self._cron_line(pid) for pid in profile_ids]

    def _cron_line(self, profile_id) -> str:
        """Return a cron line for the specified profile.

        Returns:
            `None` in case of errors or profile is not configured for
            scheduling.
        """
        schedule_mode = self.scheduleMode(profile_id)
        schedule_mode = bitbase.ScheduleMode(schedule_mode)

        hour, minute = self.scheduleHourMinute(profile_id)
        day = self.scheduleDay(profile_id)
        weekday = self.scheduleWeekday(profile_id)
        offset = str(self.schedule_offset(profile_id))

        return schedule.create_cron_line(
            schedule_mode=schedule_mode,
            cron_command=self._cron_cmd(profile_id),
            hour=hour,
            minute=minute,
            day=day,
            weekday=weekday,
            offset=offset,
            custom_backup_time=self.customBackupTime(profile_id),
            repeat_unit=bitbase.TimeUnit(
                self.scheduleRepeatedUnit(profile_id)),
            pid=profile_id
        )

    def _cron_cmd(self, profile_id):
        """Generates the command used in the crontab file based on the settings
        for the current profile.

        Returns:
            str: The crontab line.
        """

        # Get full path of the Back In Time binary
        cmd = tools.which('backintime') + ' '

        # The "--profile-id" argument is used only for profiles different from
        # first profile
        if profile_id != '1':
            cmd += '--profile %s ' % profile_id

        # User defined path to config file
        fp_config = bitbase.context['--config']
        if fp_config != bitbase.DEFAULT_CONFIG_FILE_PATH:
            cmd += f'--config {fp_config} '

        # Enable debug output
        if self.scheduleDebug(profile_id):
            cmd += '--debug '

        # command
        cmd += 'backup --background'

        # Redirect stdout to nirvana
        if self.redirectStdoutInCron(profile_id):
            cmd += ' >/dev/null'

        # Redirect stderr ...
        if self.redirectStderrInCron(profile_id):

            if self.redirectStdoutInCron(profile_id):
                # ... to stdout
                cmd += ' 2>&1'
            else:
                # ... to nirvana
                cmd += ' 2>/dev/null'

        # IO priority: low (-n7) in "best effort" class (-c2)
        if self.ioniceOnCron(profile_id) and tools.checkCommand('ionice'):
            cmd = tools.which('ionice') + ' -c2 -n7 ' + cmd

        # CPU priority: very low
        if self.niceOnCron(profile_id) and tools.checkCommand('nice'):
            cmd = tools.which('nice') + ' -n19 ' + cmd

        return cmd

    def addProfile(self, name: str) -> str | None:
        p = Konfig().new_profile(name)
        return str(p.profile_id)


def _remove_old_snapshots_date(value, unit):
    """Dev note (buhtz, 2025-01): The function exist to decople that code from
    Config class and make it testable to investigate its behavior.

    See issue #1943 for further reading.
    """
    if unit == Config.DAY:
        date = datetime.date.today()
        date = date - datetime.timedelta(days=value)
        return date

    if unit == Config.WEEK:
        date = datetime.date.today()
        # Always beginning (Monday) of the week
        date = date - datetime.timedelta(days=date.weekday() + 7 * value)
        return date

    if unit == Config.YEAR:
        date = datetime.date.today()
        return date.replace(day=1, year=date.year - value)

    return datetime.date(1, 1, 1)
