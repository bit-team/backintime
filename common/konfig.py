# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
# pylint: disable=too-many-lines,anomalous-backslash-in-string
"""Configuration mangament.
"""
from __future__ import annotations
import configparser
import getpass
import os
import socket
import re
from typing import Union, Any, Optional
from pathlib import Path
from io import StringIO, TextIOWrapper
import singleton
import logger
from bitbase import TimeUnit, StorageSizeUnit

# Workaround: Mostly relevant on TravisCI but not exclusively.
# While unittesting and without regular invocation of BIT the GNU gettext
# class-based API isn't setup yet.
# The bigger problem with config.py is that it do use translatable strings.
# Strings like this do not belong into a config file or its context.
try:
    _('Warning')
except NameError:
    def _(val):
        return val

# WORKAROUND
import tools  # <- get rid of that import asap
if tools.checkCommand('meld'):
    DIFF_CMD = 'meld'
elif tools.checkCommand('kompare'):
    DIFF_CMD = 'kompare'
else:
    DIFF_CMD = ''


class Profile:  # pylint: disable=too-many-public-methods
    """Manages access to profile-specific configuration data."""
    _DEFAULT_VALUES = {
        'name': _('Main profile'),  # A workaround we will get rid of soon
        'snapshots.mode': 'local',
        'snapshots.path.host': socket.gethostname(),
        'snapshots.path.user': getpass.getuser(),
        'snapshots.ssh.port': 22,
        'snapshots.ssh.cipher': 'default',
        'snapshots.ssh.user': getpass.getuser(),
        'snapshots.ssh.private_key_file': None,
        'snapshots.ssh.max_arg_length': 0,
        'snapshots.ssh.check_commands': True,
        'snapshots.ssh.check_ping': True,
        'snapshots.local_encfs.path': '',
        # This is fragil. Why not 'snapshots.password.save' ?
        'snapshots.local.password.save': False,
        'snapshots.ssh.password.save': False,
        'snapshots.local_gocryptfs.password.save': False,
        'snapshots.ssh_gocryptfs.password.save': False,
        # This is fragil. Why not 'snapshots.password.use_cache' ?
        'snapshots.local.password.use_cache': True,
        'snapshots.ssh.password.use_cache': True,
        'snapshots.local_gocryptfs.password.use_cache': True,
        'snapshots.ssh_gocryptfs.password.use_cache': True,
        'snapshots.include': [],
        'snapshots.exclude': [],
        'snapshots.exclude.bysize.enabled': False,
        'snapshots.exclude.bysize.value': 500,
        'schedule.mode': 0,
        'schedule.debug': False,
        'schedule.time': 0,
        'schedule.day': 1,
        'schedule.weekday': 7,
        'schedule.custom_time': '8,12,18,23',
        'schedule.repeatedly.period': 1,
        'schedule.repeatedly.unit': TimeUnit.DAY,
        'snapshots.remove_old_snapshots.enabled': True,
        'snapshots.remove_old_snapshots.value': 10,
        'snapshots.remove_old_snapshots.unit': TimeUnit.YEAR,
        'snapshots.min_free_space.enabled': True,
        'snapshots.min_free_space.value': 1,
        'snapshots.min_free_space.unit': StorageSizeUnit.GB,
        'snapshots.min_free_inodes.enabled': True,
        'snapshots.min_free_inodes.value': 2,
        'snapshots.warn_free_space.value': 0,
        'snapshots.warn_free_space.unit': SizeUnit.MIB,
        'snapshots.dont_remove_named_snapshots': True,
        'snapshots.smart_remove': False,
        'snapshots.smart_remove.keep_all': 2,
        'snapshots.smart_remove.keep_one_per_day': 7,
        'snapshots.smart_remove.keep_one_per_week': 4,
        'snapshots.smart_remove.keep_one_per_month': 24,
        'snapshots.smart_remove.run_remote_in_background': False,
        'snapshots.notify.enabled': True,
        'snapshots.backup_on_restore.enabled': True,
        'snapshots.cron.nice': True,
        'snapshots.cron.ionice': True,
        'snapshots.user_backup.ionice': False,
        'snapshots.ssh.nice': False,
        'snapshots.ssh.ionice': False,
        'snapshots.local.nocache': False,
        'snapshots.ssh.nocache': False,
        'snapshots.cron.redirect_stdout': True,
        'snapshots.cron.redirect_stderr': False,
        'snapshots.bwlimit.enabled': False,
        'snapshots.bwlimit.value': 3000,
        'snapshots.no_on_battery': False,
        'snapshots.preserve_acl': False,
        'snapshots.preserve_xattr': False,
        'snapshots.copy_unsafe_links': False,
        'snapshots.copy_links': False,
        'snapshots.one_file_system': False,
        'snapshots.rsync_options.enabled': False,
        'snapshots.ssh.prefix.enabled': False,
        # Config.DEFAULT_SSH_PREFIX
        'snapshots.ssh.prefix.value': 'PATH=/opt/bin:/opt/sbin:\\$PATH',
        'snapshots.continue_on_errors': True,
        'snapshots.use_checksum': False,
        'snapshots.log_level': 3,
        'snapshots.take_snapshot_regardless_of_changes': False,
        'global.use_flock': False,
    }

    def __init__(self, profile_id: int, config: Konfig):
        self._config = config
        self._prefix = f'profile{profile_id}'

    def __getitem__(self, key: str) -> Any:
        """Select a field of the profiles config by its name as a string and
        return its value.

        For example `self['field.name']` will return the value of field
        `profile<N>.field.name`.

        Return: The value of the config field if present. Otherwise a default
        value taken from `self._DEFAULT_VALUES`.

        Raises:
            KeyError if the field or its default value is unknown.
        """
        try:
            return self._config[f'{self._prefix}.{key}']

        except KeyError:
            return self._DEFAULT_VALUES[key]

    def __setitem__(self, key: str, val: Any) -> None:
        """Set the value of a field of the profiles config.

        For example `self['field.name'] = 7` will set the value `7` to the
        field `profile<N>.field.name`.

        Raises:
            KeyError if the field is unknown.
        """
        self._config[f'{self._prefix}.{key}'] = val

    def __delitem__(self, key: str) -> None:
        del self._config[f'{self._prefix}.{key}']

    @property
    def name(self) -> str:
        """The name of the profile"""
        result = self['name']

        # Workaround
        if result == self._DEFAULT_VALUES['name']:
            if self._prefix != 'profile1':
                raise RuntimeError(
                    f'Unexpected situation. {result=} {self._prefix=}'
                )

    @property
    def profile_id(self) -> int:
        return int(self._prefix.replace('profile', ''))

    def remove(self):
        """Remove the profile including all its keys and values.
        """

        my_keys = list(filter(
            lambda key: key.startswith(self._prefix),
            self._config.keys()
        ))

        for key in my_keys:
            del self._config[key]

    @property
    def mode(self) -> str:
        """Used mode (or backend) for this backup profile. Look at 'man
        backintime' section 'Modes'.

        {
            'values': 'local|local_encfs|ssh|ssh_encfs',
            'default': 'local',
        }
        """
        return self['snapshots.mode']

    @mode.setter
    def mode(self, val: str) -> None:
        self['snapshots.mode'] = val

    @property
    def snapshots_path(self) -> str:
        """Where to save snapshots in mode 'local'. This path must contain
        a folderstructure like 'backintime/<HOST>/<USER>/<PROFILE_ID>'.

        {
            'values': 'absolute path',
        }
        """
        # return self['snapshots.path']
        raise NotImplementedError(
            'see original in Config class. See also '
            'Config.snapshotsFullPath(self, profile_id = None)')

    @snapshots_path.setter
    def snapshots_path(self, path):
        raise NotImplementedError('see original in Config class.')

    @property
    def snapshots_path_host(self) -> str:
        """Set Host for snapshot path.

        { 'values': 'local hostname' }
        """
        return self['snapshots.path.host']

    @snapshots_path_host.setter
    def snapshots_path_host(self, value: str) -> None:
        self['snapshots.path.host'] = value

    @property
    def snapshots_path_user(self) -> str:
        """Set User for snapshot path.

        { 'values': 'local username' }
        """
        return self['snapshots.path.user']

    @snapshots_path_user.setter
    def snapshots_path_user(self, value: str) -> None:
        self['snapshots.path.user'] = value

    @property
    def snapshots_path_profile(self) -> str:
        """Set Profile-ID for backup path

        {
            'values': '1-99999',
            'default': 'current Profile-ID'
        }
        """
        try:
            return self['snapshots.path.profile']

        except KeyError:
            # Extract number from field prefix
            # e.g. "profile1" -> "1"
            return self.profile_id

    @snapshots_path_profile.setter
    def snapshots_path_profile(self, value: str) -> None:
        self['snapshots.path.profile'] = value

    @property
    def ssh_snapshots_path(self) -> str:
        """Snapshot path on remote host. If the path is relative (no
        leading '/') it will start from remote Users homedir. An empty path
        will be replaced with './'.

        {
            'values': 'absolute or relative path',
        }

        """
        return self['snapshots.ssh.path']

    @ssh_snapshots_path.setter
    def ssh_snapshots_path(self, path):
        self['snapshots.ssh.path'] = path

    @property
    def ssh_host(self) -> str:
        """Remote host used for mode 'ssh' and 'ssh_encfs'.

        {
            'values': 'IP or domain address',
        }
        """
        return self['snapshots.ssh.host']

    @ssh_host.setter
    def ssh_host(self, value: str) -> None:
        self['snapshots.ssh.host'] = value

    @property
    def ssh_port(self) -> int:
        """SSH Port on remote host.

        {
            'values': '0-65535',
            'default': 22,
        }
        """
        return self['snapshots.ssh.port']

    @ssh_port.setter
    def ssh_port(self, value: int) -> None:
        self['snapshots.ssh.port'] = value

    @property
    def ssh_user(self) -> str:
        """Remote SSH user.

        {
            'default': 'local users name',
            'values': 'text',
        }
        """
        return self['snapshots.ssh.user']

    @ssh_user.setter
    def ssh_user(self, value: str) -> None:
        self['snapshots.ssh.user'] = value

    @property
    def ssh_private_key_file(self) -> Path:
        """Private key file used for password-less authentication on remote
        host.

        {
            'values': 'absolute path to private key file',
            'default': None,
            'type': 'str'
        }

        """
        value = self['snapshots.ssh.private_key_file']
        if value:
            return Path(value)

        return value

    @ssh_private_key_file.setter
    def ssh_private_key_file(self, path: Path) -> None:
        self['snapshots.ssh.private_key_file'] = str(path) if path else None

    @property
    def ssh_proxy_host(self) -> str:
        """Proxy host (or jump host) used to connect to remote host.

        {
            'values': 'IP or domain address',
        }
        """
        return self['snapshots.ssh.proxy_host']

    @ssh_proxy_host.setter
    def ssh_proxy_host(self, value: str) -> None:
        self['snapshots.ssh.proxy_host'] = value

    @property
    def ssh_proxy_port(self) -> int:
        """Port of SSH proxy (jump) host used to connect to remote host.

        {
            'values': '0-65535',
            'default': 22,
        }
        """
        return self['snapshots.ssh.proxy_port']

    @ssh_proxy_port.setter
    def ssh_proxy_port(self, value: int) -> None:
        self['snapshots.ssh.proxy_port'] = value

    @property
    def ssh_proxy_user(self) -> str:
        """SSH user at proxy (jump) host.

        {
            'default': 'local users name',
            'values': 'text',
        }
        """
        return self['snapshots.ssh.proxy_user']

    @ssh_proxy_user.setter
    def ssh_proxy_user(self, value: str) -> None:
        self['snapshots.ssh.proxy_user'] = value

    @property
    def ssh_max_arg_length(self) -> int:
        """Maximum command length of commands run on remote host. This can
        be tested for all ssh profiles in the configuration with 'python3
        /usr/share/backintime/common/sshMaxArg.py LENGTH'. The value '0'
        means unlimited length.

        {
            'values': '0, >700',
        }
        """
        raise NotImplementedError('see org in Config')
        # return self['snapshots.ssh.max_arg_length']

    @ssh_max_arg_length.setter
    def ssh_max_arg_length(self, length: int) -> None:
        self['snapshots.ssh.max_arg_length'] = length

    @property
    def ssh_check_commands(self) -> bool:
        """Check if all commands (used during takeSnapshot) work like
        expected on the remote host.
        { 'values': 'true|false' }
        """

        # Deprecated. See issue #2509
        return self['snapshots.ssh.check_commands']

    @ssh_check_commands.setter
    def ssh_check_commands(self, value: bool) -> None:
        self['snapshots.ssh.check_commands'] = value

    @property
    def ssh_check_ping_host(self) -> bool:
        """Check if the remote host is available before trying to mount.
        { 'values': 'true|false' }
        """
        return self['snapshots.ssh.check_ping']

    @ssh_check_ping_host.setter
    def ssh_check_ping_host(self, value: bool) -> None:
        self['snapshots.ssh.check_ping'] = value

    @property
    def local_gocryptfs_path(self) -> Path:
        """Where to save snapshots in mode 'local_gocryptfs'.

        { 'values': 'absolute path' }
        """
        return self['snapshots.local_gocryptfs.path']

    @local_gocryptfs_path.setter
    def local_gocryptfs_path(self, path: Path):
        self['snapshots.local_gocryptfs.path'] = str(path)

    @property
    def password_save(self) -> bool:
        """Save password to system keyring (gnome-keyring or kwallet).
        { 'values': 'true|false' }
        """
        return self[f'snapshots.{self.mode}.password.save']

    @password_save.setter
    def password_save(self, value: bool) -> None:
        self[f'snapshots.{self.mode}.password.save'] = value

    @property
    def password_use_cache(self) -> None:
        """Cache password in RAM so it can be read by cronjobs.
        Security issue: root might be able to read that password, too.
        {
            'values': 'true|false',
            'default': 'see #1855'
        }
        """
        return self[f'snapshots.{self.mode}.password.use_cache']

    @password_use_cache.setter
    def password_use_cache(self, value: bool) -> None:
        self[f'snapshots.{self.mode}.password.use_cache'] = value

    def _generic_include_exclude_ids(self, inc_exc_str: str) -> tuple[int]:
        """Return two list of numeric IDs used for include and exclude values.

        The config file does have lines like this:

            profile1.snapshots.include.1.values
            profile1.snapshots.include.2.values
            profile1.snapshots.include.3.values
            ...
            profile1.snapshots.include.8.values

        or

            profile1.snapshots.exclude.1.values
            profile1.snapshots.exclude.2.values
            profile1.snapshots.exclude.3.values
            ...
            profile1.snapshots.exclude.8.values

        The numerical value between (in this example 1, 2, 3, 8) is extracted
        via regex.

        Return:
            A two item tuple, first with include IDs and second with exclude.
        """
        rex = re.compile(r'^'
                         + self._prefix
                         + r'.snapshots.'
                         + inc_exc_str
                         + r'.(\d+).value')

        ids = []

        # Ugly, I know. Handling of in/exclude will be rewritten soon. So no
        # need to fix this.
        for item in self._config._conf:  # pylint: disable=protected-access
            try:
                ids.append(int(rex.findall(item)[0]))
            except IndexError:
                pass

        return tuple(ids)

    def _get_include_ids(self) -> tuple[int]:
        """List of numeric IDs used for include values."""

        return self._generic_include_exclude_ids('include')

    def _get_exclude_ids(self) -> tuple[int]:
        """List of numeric IDs used for exclude values."""
        return self._generic_include_exclude_ids('exclude')

    @property
    def include(self) -> list[str, int]:  # pylint: disable=C0116
        # Man page docu is added manually. See
        # create-manpage-backintime-config.sh script.

        # ('name', 0|1)
        result = []

        for id_val in self._get_include_ids():
            result.append(
                (
                    self[f'snapshots.include.{id_val}.value'],
                    int(self[f'snapshots.include.{id_val}.type'])
                )
            )

        return result

    @include.setter
    def include(self, values: list[str, int]) -> None:
        # delete existing values
        for id_val in self._get_include_ids():
            del self[f'snapshots.include.{id_val}.value']
            del self[f'snapshots.include.{id_val}.type']

        for idx, val in enumerate(values, 1):
            self[f'snapshots.include.{idx}.value'] = val[0]
            self[f'snapshots.include.{idx}.type'] = str(val[1])

    @property
    def exclude(self) -> list[str]:  # pylint: disable=C0116
        # Man page docu is added manually. See
        # create-manpage-backintime-config.sh script.
        result = []

        for id_val in self._get_exclude_ids():
            result.append(self[f'snapshots.exclude.{id_val}.value'])

        return result

    @exclude.setter
    def exclude(self, values: list[str]) -> None:
        # delete existing values
        for id_val in self._get_exclude_ids():
            del self[f'snapshots.exclude.{id_val}.value']

        for idx, val in enumerate(values, 1):
            self[f'snapshots.exclude.{idx}.value'] = val

    @property
    def exclude_by_size_enabled(self) -> bool:
        """Enable exclude files by size."""
        return self['snapshots.exclude.bysize.enabled']

    @exclude_by_size_enabled.setter
    def exclude_by_size_enabled(self, value: bool) -> None:
        self['snapshots.exclude.bysize.enabled'] = value

    @property
    def exclude_by_size(self) -> int:
        """Exclude files bigger than value in MiB. With 'Full rsync mode'
        disabled this will only affect new files because for rsync this is a
        transfer option, not an exclude option. So big files that has been
        backed up before will remain in snapshots even if they had changed.
        """
        return self['snapshots.exclude.bysize.value']

    @exclude_by_size.setter
    def exclude_by_size(self, value):
        self['snapshots.exclude.bysize.value'] = value

    @property
    def schedule_mode(self) -> int:
        """Which schedule used for crontab. The crontab entry will be
        generated with 'backintime check-config'.\n
         0 = Disabled\n 1 = at every boot\n 2 = every 5 minute\n
         4 = every 10 minute\n 7 = every 30 minute\n10 = every hour\n
        12 = every 2 hours\n14 = every 4 hours\n16 = every 6 hours\n
        18 = every 12 hours\n19 = custom defined hours\n20 = every day\n
        25 = daily anacron\n27 = when drive get connected\n30 = every week\n
        40 = every month\n80 = every year

        {
            'values': '0|1|2|4|7|10|12|14|16|18|19|20|25|27|30|40|80'
        }
        """
        return self['schedule.mode']

    @schedule_mode.setter
    def schedule_mode(self, value: int) -> None:
        self['schedule.mode'] = value

    @property
    def schedule_debug(self) -> bool:
        """Enable debug output to system log for schedule mode."""
        return self['schedule.debug']

    @schedule_debug.setter
    def schedule_debug(self, value: bool) -> None:
        self['schedule.debug'] = value

    @property
    def schedule_time(self) -> int:
        """Position-coded number with the format "hhmm" to specify the hour
        and minute the cronjob should start (eg. 2015 means a quarter
        past 8pm). Leading zeros can be omitted (eg. 30 = 0030).
        Only valid for \\fIprofile<N>.schedule.mode\\fR = 20 (daily),
        30 (weekly), 40 (monthly) and 80 (yearly).
        { 'values': '0-2400' }
        """
        return self['schedule.time']

    @schedule_time.setter
    def schedule_time(self, value: int) -> None:
        self['schedule.time'] = value

    @property
    def schedule_day(self) -> int:
        """Which day of month the cronjob should run? Only valid for
        \\fIprofile<N>.schedule.mode\\fR >= 40.
        { 'values': '1-28' }
        """
        return self['schedule.day']

    @schedule_day.setter
    def schedule_day(self, value: int) -> None:
        self['schedule.day'] = value

    @property
    def schedule_weekday(self) -> int:
        """Which day of week the cronjob should run? Only valid for
        \\fIprofile<N>.schedule.mode\\fR = 30.
        { 'values': '1 (monday) to 7 (sunday)' }
        """
        return self['schedule.weekday']

    @schedule_weekday.setter
    def schedule_weekday(self, value: int) -> None:
        self['schedule.weekday'] = value

    @property
    def custom_backup_time(self) -> str:
        """Custom hours for cronjob. Only valid for
        \\fIprofile<N>.schedule.mode\\fR = 19
        { 'values': 'comma separated int (8,12,18,23) or */3;8,12,18,23' }
        """
        return self['schedule.custom_time']

    @custom_backup_time.setter
    def custom_backup_time(self, value: str) -> None:
        self['schedule.custom_time'] = value

    @property
    def schedule_repeated_period(self) -> int:
        """How many units to wait between new snapshots with anacron? Only
        valid for \\fIprofile<N>.schedule.mode\\fR = 25|27.
        """
        return self['schedule.repeatedly.period']

    @schedule_repeated_period.setter
    def schedule_repeated_period(self, value: int) -> None:
        self['schedule.repeatedly.period'] = value

    @property
    def schedule_repeated_unit(self) -> int:
        """Units to wait between new snapshots with anacron.\n
        10 = hours\n20 = days\n30 = weeks\n40 = months\n
        Only valid for \\fIprofile<N>.schedule.mode\\fR = 25|27;
        { 'values': '10|20|30|40' }
        """
        return self['schedule.repeatedly.unit']

    @schedule_repeated_unit.setter
    def schedule_repeated_unit(self, value: int) -> None:
        self['schedule.repeatedly.unit'] = value

    @property
    def remove_old_snapshots_enabled(self) -> bool:
        """Remove all snapshots older than value + unit.
        """
        return self['snapshots.remove_old_snapshots.enabled']

    @remove_old_snapshots_enabled.setter
    def remove_old_snapshots_enabled(self, enabled: bool) -> None:
        self['snapshots.remove_old_snapshots.enabled'] = enabled

    @property
    def remove_old_snapshots_value(self) -> int:
        """Snapshots older than this times units will be removed."""
        return self['snapshots.remove_old_snapshots.value']

    @remove_old_snapshots_value.setter
    def remove_old_snapshots_value(self, value: int) -> None:
        self['snapshots.remove_old_snapshots.value'] = value

    @property
    def remove_old_snapshots_unit(self) -> TimeUnit:
        """Time unit to use to calculate removing of old snapshots.
        20 = days; 30 = weeks; 80 = years
        {
            'values': '20|30|80'
        }
        """
        return self['snapshots.remove_old_snapshots.unit']

    @remove_old_snapshots_unit.setter
    def remove_old_snapshots_unit(self, unit: TimeUnit) -> None:
        self['snapshots.remove_old_snapshots.unit'] = unit

    @property
    def warn_free_space(self) -> StorageSize:
        """TODO"""
        value = self['snapshots.warn_free_space.value']
        unit = self['snapshots.warn_free_space.unit']
        return StorageSize(value, SizeUnit(unit))

    @warn_free_space.setter
    def warn_free_space(self, value: StorageSize) -> None:
        self['snapshots.warn_free_space.value'] = value.value()
        self['snapshots.warn_free_space.unit'] = value.unit.value

    @property
    def warn_free_space_enabled(self) -> bool:
        return self['snapshots.warn_free_space.value'] > 0

    def set_warn_free_space_disabled(self) -> None:
        self.warn_free_space = StorageSize(0, SizeUnit.MIB)

    @property
    def min_free_space(self) -> StorageSize:
        """Keep at least value + unit free space."""
        return StorageSize(
            self['snapshots.min_free_space.value'],
            self['snapshots.min_free_space.unit']
        )

    @min_free_space_value.setter
    def min_free_space(self, value: StorageSize) -> None:
        self['snapshots.min_free_space.value'] = value.value()
        self['snapshots.min_free_space.unit'] = value.unit.value

    @property
    def min_free_space_enabled(self) -> bool:
        """Remove snapshots until \\fIprofile<N>.snapshots.min_free_space.
        value\\fR free space is reached.
        """
        return self['snapshots.min_free_space.enabled'] == 'true'

    def set_min_free_space_enabled(self, enable: bool):
        value = 'true' if enable else 'false'
        self['snapshots.min_free_space.enabled'] = value

    @property
    def min_free_inodes_enabled(self) -> bool:
        """Remove snapshots until
        \\fIprofile<N>.snapshots.min_free_inodes.value\\fR
        free inodes in % is reached.
        """
        return self['snapshots.min_free_inodes.enabled']

    @min_free_inodes_enabled.setter
    def min_free_inodes_enabled(self, enable: bool) -> None:
        self['snapshots.min_free_inodes.enabled'] = enable

    @property
    def min_free_inodes_value(self) -> int:
        """Keep at least value % free inodes.
        { 'values': '1-15' }
        """
        return self['snapshots.min_free_inodes.value']

    @min_free_inodes_value.setter
    def min_free_inodes_value(self, value: int) -> None:
        self['snapshots.min_free_inodes.value'] = value

    @property
    def dont_remove_named_snapshots(self) -> bool:
        """Keep snapshots with names during smart_remove."""
        return self['snapshots.dont_remove_named_snapshots']

    @dont_remove_named_snapshots.setter
    def dont_remove_named_snapshots(self, value: bool) -> None:
        """Keep snapshots with names during smart_remove."""
        self['snapshots.dont_remove_named_snapshots'] = value

    @property
    def keep_named_snapshots(self) -> bool:
        """Keep snapshots with names during smart_remove."""
        return self.dont_remove_named_snapshots

    @keep_named_snapshots.setter
    def keep_named_snapshots(self, value: bool) -> None:
        self.dont_remove_named_snapshots = value

    @property
    def smart_remove(self) -> bool:
        """Run smart_remove to clean up old snapshots after a new snapshot was
        created."""
        return self['snapshots.smart_remove']

    @smart_remove.setter
    def smart_remove(self, enable: bool) -> None:
        self['snapshots.smart_remove'] = enable

    @property
    def smart_remove_keep_all(self) -> int:
        """Keep all snapshots for X days."""
        return self['snapshots.smart_remove.keep_all']

    @smart_remove_keep_all.setter
    def smart_remove_keep_all(self, days: int) -> None:
        self['snapshots.smart_remove.keep_all'] = days

    @property
    def smart_remove_keep_one_per_day(self) -> int:
        """Keep one snapshot per day for X days."""
        return self['snapshots.smart_remove.keep_one_per_day']

    @smart_remove_keep_one_per_day.setter
    def smart_remove_keep_one_per_day(self, days: int) -> None:
        self['snapshots.smart_remove.keep_one_per_day'] = days

    @property
    def smart_remove_keep_one_per_week(self) -> int:
        """Keep one snapshot per week for X weeks."""
        return self['snapshots.smart_remove.keep_one_per_week']

    @smart_remove_keep_one_per_week.setter
    def smart_remove_keep_one_per_week(self, weeks: int) -> None:
        self['snapshots.smart_remove.keep_one_per_week'] = weeks

    @property
    def smart_remove_keep_one_per_month(self) -> int:
        """Keep one snapshot per month for X months."""
        return self['snapshots.smart_remove.keep_one_per_month']

    @smart_remove_keep_one_per_month.setter
    def smart_remove_keep_one_per_month(self, months: int) -> None:
        self['snapshots.smart_remove.keep_one_per_month'] = months

    @property
    def smart_remove_run_remote_in_background(self) -> bool:
        """If using modes SSH or SSH-encrypted, run smart_remove in background
        on remote machine"""
        return self['snapshots.smart_remove.run_remote_in_background']

    @smart_remove_run_remote_in_background.setter
    def smart_remove_run_remote_in_background(self, enable: bool) -> None:
        self['snapshots.smart_remove.run_remote_in_background'] = enable

    @property
    def notify(self) -> bool:
        """Display notifications (errors, warnings) through libnotify or DBUS.
        """
        return self['snapshots.notify.enabled']

    @notify.setter
    def notify(self, enable: bool) -> None:
        self['snapshots.notify.enabled'] = enable

    @property
    def backup_on_restore(self) -> bool:
        """Rename existing files before restore into FILE.backup.YYYYMMDD"""
        return self['snapshots.backup_on_restore.enabled']

    @backup_on_restore.setter
    def backup_on_restore(self, enable: bool) -> None:
        self['snapshots.backup_on_restore.enabled'] = enable

    @property
    def nice_on_cron(self) -> bool:
        """Run cronjobs with nice-Value 19. This will give Back In Time the
        lowest CPU priority to not interrupt any other working process."""
        return self['snapshots.cron.nice']

    @nice_on_cron.setter
    def nice_on_cron(self, enable: bool) -> None:
        self['snapshots.cron.nice'] = enable

    @property
    def ionice_on_cron(self) -> bool:
        """Run cronjobs with 'ionice' and class 2 and level 7. This will give
        Back In Time the lowest IO bandwidth priority to not interrupt any
        other working process.
        """
        return self['snapshots.cron.ionice']

    @ionice_on_cron.setter
    def ionice_on_cron(self, enable: bool) -> None:
        self['snapshots.cron.ionice'] = enable

    @property
    def ionice_on_user(self) -> bool:
        """Run Back In Time with 'ionice' and class 2 and level 7 when taking
        a manual snapshot. This will give Back In Time the lowest IO bandwidth
        priority to not interrupt any other working process.
        """
        return self['snapshots.user_backup.ionice']

    @ionice_on_user.setter
    def ionice_on_user(self, enable: bool) -> None:
        self['snapshots.user_backup.ionice'] = enable

    @property
    def nice_on_remote(self) -> bool:
        """Run rsync and other commands on remote host with 'nice' value 19."""
        return self['snapshots.ssh.nice']

    @nice_on_remote.setter
    def nice_on_remote(self, enable: bool) -> None:
        self['snapshots.ssh.nice'] = enable

    @property
    def ionice_on_remote(self) -> bool:
        """Run rsync and other commands on remote host with
        'ionice' and class 2 and level 7."""
        return self['snapshots.ssh.ionice']

    @ionice_on_remote.setter
    def ionice_on_remote(self, enable: bool) -> None:
        self['snapshots.ssh.ionice'] = enable

    @property
    def nocache_on_local(self) -> bool:
        """Run rsync on local machine with 'nocache'.
        This will prevent files from being cached in memory."""
        return self['snapshots.local.nocache']

    @nocache_on_local.setter
    def nocache_on_local(self, enable: bool) -> None:
        self['snapshots.local.nocache'] = enable

    @property
    def nocache_on_remote(self) -> bool:
        """Run rsync on remote host with 'nocache'.
        This will prevent files from being cached in memory."""
        return self['snapshots.ssh.nocache']

    @nocache_on_remote.setter
    def nocache_on_remote(self, enable: bool) -> None:
        self['snapshots.ssh.nocache'] = enable

    @property
    def redirect_stdout_in_cron(self) -> bool:
        """Redirect stdout to /dev/null in cronjobs."""
        return self['snapshots.cron.redirect_stdout']

    @redirect_stdout_in_cron.setter
    def redirect_stdout_in_cron(self, enable: bool) -> None:
        self['snapshots.cron.redirect_stdout'] = enable

    @property
    def redirect_stderr_in_cron(self) -> bool:
        """Redirect stderr to /dev/null in cronjobs."""
        # Dev note (buhtz, 2024-09): Makes not much sense to me, to have a
        # depended default value here. Can't find something helpful in the git
        # logs about it.
        # if self.isConfigured(profile_id):
        #     default = True
        # else:
        #     default = self.DEFAULT_REDIRECT_STDERR_IN_CRON
        return self['snapshots.cron.redirect_stderr']

    @redirect_stderr_in_cron.setter
    def redirect_stderr_in_cron(self, enable: bool) -> None:
        self['snapshots.cron.redirect_stderr'] = enable

    @property
    def bw_limit_enabled(self) -> bool:
        """Limit rsync bandwidth usage over network. Use this with mode SSH.
        For mode Local you should rather use ionice."""
        return self['snapshots.bwlimit.enabled']

    @bw_limit_enabled.setter
    def bw_limit_enabled(self, enable: bool) -> None:
        self['snapshots.bwlimit.enabled'] = enable

    @property
    def bw_limit(self) -> int:
        """Bandwidth limit in KB/sec."""
        return self['snapshots.bwlimit.value']

    @bw_limit.setter
    def bw_limit(self, limit_kb_sec: int) -> None:
        self['snapshots.bwlimit.value'] = limit_kb_sec

    @property
    def no_snapshot_on_battery(self) -> bool:
        """Don't take snapshots if the Computer runs on battery."""
        return self['snapshots.no_on_battery']

    @no_snapshot_on_battery.setter
    def no_snapshot_on_battery(self, enable: bool) -> None:
        self['snapshots.no_on_battery'] = enable

    @property
    def preserve_alc(self) -> bool:
        """Preserve Access Control Lists (ACL). The source and destination
        systems must have compatible ACL entries for this option to work
        properly.
        """
        return self['snapshots.preserve_acl']

    @preserve_alc.setter
    def preserve_alc(self, preserve: bool) -> None:
        self['snapshots.preserve_acl'] = preserve

    @property
    def preserve_xattr(self) -> bool:
        """Preserve extended attributes (xattr)."""
        return self['snapshots.preserve_xattr']

    @preserve_xattr.setter
    def preserve_xattr(self, preserve: bool) -> None:
        """Preserve extended attributes (xattr)."""
        self['snapshots.preserve_xattr'] = preserve

    @property
    def copy_unsafe_links(self) -> bool:
        """This tells rsync to copy the referent of symbolic links that point
        outside the copied tree. Absolute symlinks are also treated like
        ordinary files."""
        return self['snapshots.copy_unsafe_links']

    @copy_unsafe_links.setter
    def copy_unsafe_links(self, enable: bool) -> None:
        self['snapshots.copy_unsafe_links'] = enable

    @property
    def copy_links(self) -> bool:
        """When symlinks are encountered, the item that they point to (the
        reference) is copied, rather than the symlink.
        """
        return self['snapshots.copy_links']

    @copy_links.setter
    def copy_links(self, enable: bool) -> None:
        self['snapshots.copy_links'] = enable

    @property
    def one_file_system(self) -> bool:
        """Use rsync's "--one-file-system" to avoid crossing filesystem
        boundaries when recursing.
        """
        return self['snapshots.one_file_system']

    @one_file_system.setter
    def one_file_system(self, enable: bool) -> None:
        self['snapshots.one_file_system'] = enable

    @property
    def rsync_options_enabled(self) -> bool:
        """Past additional options to rsync"""
        return self['snapshots.rsync_options.enabled']

    @rsync_options_enabled.setter
    def rsync_options_enabled(self, enable: bool) -> None:
        self['snapshots.rsync_options.enabled'] = enable

    @property
    def rsync_options(self) -> str:
        """Rsync options. Options must be quoted."""
        return self['snapshots.rsync_options.value']

    @rsync_options.setter
    def rsync_options(self, options: str) -> None:
        self['snapshots.rsync_options.value'] = options

    @property
    def ssh_prefix_enabled(self) -> bool:
        """Add prefix to every command which run through SSH on remote host."""
        return self['snapshots.ssh.prefix.enabled']

    @ssh_prefix_enabled.setter
    def ssh_prefix_enabled(self, enable: bool) -> None:
        self['snapshots.ssh.prefix.enabled'] = enable

    @property
    def ssh_prefix(self) -> str:
        """Prefix to run before every command on remote host. Variables need to
        be escaped with \\\\$FOO. This doesn't touch rsync. So to add a prefix
        for rsync use \\fIprofile<N>.snapshots.rsync_options.value\\fR with
        --rsync-path="FOO=bar:\\\\$FOO /usr/bin/rsync"
        """
        return self['snapshots.ssh.prefix.value']

    @ssh_prefix.setter
    def ssh_prefix(self, prefix: str) -> None:
        self['snapshots.ssh.prefix.value'] = prefix

    @property
    def continue_on_errors(self) -> bool:
        """Continue on errors. This will keep incomplete snapshots rather than
        deleting and start over again."""
        return self['snapshots.continue_on_errors']

    @continue_on_errors.setter
    def continue_on_errors(self, enable: bool) -> None:
        self['snapshots.continue_on_errors'] = enable

    @property
    def use_checksum(self) -> bool:
        """Use checksum to detect changes rather than size + time."""
        return self['snapshots.use_checksum']

    @use_checksum.setter
    def use_checksum(self, enable: bool) -> None:
        self['snapshots.use_checksum'] = enable

    @property
    def log_level(self) -> int:
        """Log level used during takeSnapshot.\n1 = Error\n2 = Changes\n3 =
        Info.
        { 'values': '1-3' }
        """
        return self['snapshots.log_level']

    @log_level.setter
    def log_level(self, level: int) -> None:
        self['snapshots.log_level'] = level

    @property
    def take_snapshot_regardless_of_changes(self) -> bool:
        """Create a new snapshot regardless if there were changes or not."""
        return self['snapshots.take_snapshot_regardless_of_changes']

    @take_snapshot_regardless_of_changes.setter
    def take_snapshot_regardless_of_changes(self, enable: bool) -> None:
        self['snapshots.take_snapshot_regardless_of_changes'] = enable


class Konfig(metaclass=singleton.Singleton):
    """Manage configuration data for Back In Time.

    Dev note:

        That class is a replacement for the `config.Config` class.
    """

    _DEFAULT_VALUES = {
        'global.language': '',
        'global.systray': 'auto',
        'global.use_flock': False,
        'internal.manual_starts_countdown': 10,
        'qt.diff.cmd': DIFF_CMD,
        'qt.diff.params': '%1 %2',
    }

    _DEFAULT_SECTION = 'bit'

    def __init__(self):
        """Constructor.

        Note: That method is executed only once because `Konfig` is a
        singleton.
        """
        self._conf = {}
        self._profiles = {}
        self._unsaved_profiles = []

    def __getitem__(self, key: str) -> Any:
        try:
            return self._conf[key]
        except KeyError:
            return self._DEFAULT_VALUES[key]

    def __setitem__(self, key: str, val: Any) -> None:
        self._conf[key] = val

    def __delitem__(self, key: str) -> None:
        self._config_parser.remove_option(self._DEFAULT_SECTION, key)

    def profile(self, name_or_id: Union[str, int]) -> Profile:
        """Return a `Profile` object related to the given name or id.

        Args:
            name_or_id: A name or an numeric id of a backup profile.

        Raises:
            KeyError: If no corresponding profile exists.
        """
        if isinstance(name_or_id, int):
            profile_id = name_or_id

        else:
            profile_id = self._profiles[name_or_id]

        return Profile(profile_id=profile_id, config=self)

    def has_profile(self, name_or_id: Union[str, int]) -> bool:
        """Check if the profile exists"""
        try:
            self.profile(name_or_id)
        except KeyError:
            return False

        return True

    @property
    def profile_names(self) -> list[str]:
        """List of profile names."""
        return list(self._profiles.keys())

    @property
    def profile_ids(self) -> list[int]:
        """List of numerical profile ids."""
        return list(self._profiles.values())

    def _profile_list(self) -> dict:
        """Create a dictionary of profile names and ids.

        Example: :: ..

            {
                'simple': 2,
                'lcoal-gocrypt': 3,
                'Main profile': 1
            }
        """
        # Names and IDs of profiles
        # Extract all relevant lines of format 'profile*.name=*'
        name_items = filter(
            lambda val:
                val[0].startswith('profile') and val[0].endswith('.name'),
            self._conf.items()
        )
        return {
            name: int(pid.replace('profile', '').replace('.name', ''))
            for pid, name in name_items
        }

    def iter_profiles(self):
        for pid in self.profile_ids():
            yield Profile(profile_id=pid, config=self)

    def new_profile(self, name: str) -> Profile:
        """Create and add a new profile and returns it.

        The name need to be unique, otherwise a ValueException is raised.

        Args:
            name: The name of the profile.

        Returns:
            The new created profile

        Raises:
            ValueError if the name is not unique.
        """
        if name in self.profile_names:
            raise ValueError(
                'Profile name need to be unique, but "{name}" already exists.'
            )

        new_pid = self._next_free_id()
        prefix = f'profile{new_pid}.'

        self[f'{prefix}name'] = name

        self._unsaved_profiles.append(new_pid)

        return self.profile(new_pid)

    def _next_free_id(self) -> int:
        """Compute the next free profile id.

        Returns:
            An unused and free id.
        """

        # Assumentions: Sorted, no negative values, no zero, no duplicates
        pids = self.profile_ids

        try:
            # contiguous sequence starting at 1?
            if len(pids) == pids[-1]:
                return pids[-1] + 1

            # find the gap
            free_pid = 1
            used = set(pids)
            while free_pid in used:
                free_pid = free_pid + 1

        except IndexError:
            return 1

        # gap found
        return free_pid

    def load(self, buffer_or_path: Union[Path, TextIOWrapper, StringIO]):
        """Load configuration from file like object.

        Args:
            buffer: A path object, an open text-file handle or a string
                buffer ready to read.
        """

        self._config_parser = configparser.ConfigParser(
            interpolation=None,
            defaults={'profile1.name': _('Main profile')})

        # raw content
        if isinstance(buffer_or_path, Path):
            content = buffer_or_path.read_text(encoding='utf-8')
        else:
            content = buffer_or_path.read()

        # Add section header to make it a real INI file
        self._config_parser.read_string(
            f'[{self._DEFAULT_SECTION}]\n{content}')

        # The one and only main section
        self._conf = self._config_parser[self._DEFAULT_SECTION]

        self._profiles = self._profile_list()

    def save(self, buffer: TextIOWrapper):
        """Store configuraton to the config file."""

        self._unsaved_profiles = []
        raise NotImplementedError('Prevent overwritting real config data.')

        # tmp_io_buffer = StringIO()
        # self._config_parser.write(tmp_io_buffer)
        # tmp_io_buffer.seek(0)

        # # Write to file without section header
        # # Discard unwanted first line
        # tmp_io_buffer.readline()
        # handle.write(tmp_io_buffer.read())

    def is_profile_unsaved(self, name_or_id: Union[str, int]) -> bool:
        p = self.profile(name_or_id)
        return p.profile_id in self._unsaved_profiles

    @property
    def diff_cmd_and_params(self) -> tuple[str, str]:
        """TODO"""
        return (self['qt.diff.cmd'], self['qt.diff.params'])

    @diff_cmd_and_params.setter
    def diff_cmd_and_params(self, value: tuple[str, str]) -> None:
        self['qt.diff.cmd'] = value[0]
        self['qt.diff.params'] = value[1]

    @property
    def language(self) -> str:
        """Language code (ISO 639) used to translate the user interface. If
        empty the operating systems current local is used. If 'en' the
        translation is not active and the original English source strings are
        used. It is the same if the value is unknown.
        {
            'values': 'ISO 639 language codes',
            'type': str
        }
        """
        return self['global.language']

    @language.setter
    def language(self, lang: str) -> None:
        self['global.language'] = lang

    @property
    def global_flock(self) -> bool:
        """Prevent multiple snapshots (from different profiles or users) to be
        run at the same time.
        {
            'values': 'true|false',
            'default': 'false',
            'type': bool
        }
        """
        return self['global.use_flock']

    @global_flock.setter
    def global_flock(self, value: bool) -> None:
        self['global.use_flock'] = value

    @property
    def systray(self) -> str:
        """Color of systray icon.;auto,dark,light
        {
            'values': 'auto|dark|light',
            'default': 'auto',
            'type': str
        }
        """
        return self['global.systray']

    @systray.setter
    def systray(self, color_mode: str) -> None:
        self['global.systray'] = color_mode

    @property
    def manual_starts_countdown(self) -> int:  # pylint: disable=C0116
        # Countdown value about how often the users started the Back In Time
        # GUI.

        # It is an internal variable not meant to be used or manipulated be the
        # users. At the end of the countown the
        # :py:class:`ApproachTranslatorDialog` is presented to the user.
        return self['internal.manual_starts_countdown']

    def decrement_manual_starts_countdown(self):
        """Counts down to -1.

        See `manual_starts_countdown()` for details.
        """
        val = self.manual_starts_countdown

        if val > -1:
            self['internal.manual_starts_countdown'] = val - 1



if __name__ == '__main__':
    # Empty in-memory config file
    # k = Konfig(StringIO())

    k = Konfig()
    print(k)
    print(f'{k._conf=}')  # pylint: disable=protected-access
    print(f'{k._profiles=}')  # pylint: disable=protected-access

    k.load(Path.home() / '.config' / 'backintime' / 'config')
    sys.exit()
    # Regular config file
    with config_file_path().open('r', encoding='utf-8') as handle:
        k = Konfig()
        k.load(handle)

    print(k)
    print(f'{k._conf=}')  # pylint: disable=protected-access
    print(f'{k._profiles=}')  # pylint: disable=protected-access

    print(f'{k.profile_names=}')
    print(f'{k.profile_ids=}')
    print(f'{k.hash_collision=}')
    print(f'{k.language=}')
    print(f'{k.global_flock=}')

    p = k.profile(2)
    print(f'{p.snapshots_mode=}')
    p.snapshots_mode = 'ssh'
    print(f'{p.snapshots_mode=}')
    print(f'{p.include=}')

    p = k.profile(8)
    print(f'{p.include=}')

    p = k.profile(9)
    print(f'{p.include=}')
    print(f'{p.exclude=}')

    p.include = [('foo', 0), ('bar', 1)]
    print(f'{p.include=}')
