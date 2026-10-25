# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""This modul is a work in progress and tries to replicate the behavior from
snapshots.Snapshot.backup() and snapshots.Snapshot.takeBackup()

Current approach is to make it work with local_gocryptfs profile only.
"""
from __future__ import annotations
import datetime
from contextlib import contextmanager
import logger
import password
import schedule
import tools
from applicationinstance import ApplicationInstance
from ._base import ERROR, SUCCESS
from bitbase import SCHEDULE_MODES_HANDLED_BY_CRON, ScheduleMode
from flock import GlobalFlock
from inhibitsuspend import InhibitSuspend
from konfig import Konfig
from mount import MountError
from neo import BackupDestination, BackupSources
from pluginmanager import PluginManager
from profilecontext import ProfileContext
from snapshots import Snapshots

# pylint: disable=duplicate-code
try:
    _('Warning')
except NameError:
    def _(val):
        return val


@contextmanager
def _application_instance_lock(instance: ApplicationInstance):
    """An interim helper until ApplicationInstance is refactored"""

    instance.startApplication()

    try:
        yield

    finally:
        # Dev note (buhtz, 2026-10):
        # The original code (before 2.0.0) from snapshots.py module contained
        # a 2-second sleep at the end of the backup routine. It was already
        # introduced in the first commit (055ef3c) in 2008, with the
        # comment "max 1 backup / second". Its original purpose is unknown.
        # Possible reasons include avoiding timing issues with consecutive
        # backup runs, process termination, or lock-file handling.
        # The current implementation of lock file handling should cover all
        # conflicting cases such a sleep might prevent.
        # I see no real reason to keep this enabled, because. But let's see.
        # time.sleep(2)

        instance.exitApplication()


class TakeBackup:
    """The backup operation.

    The instance holds and coordinates all resources needed to take a backup.
    """

    def __init__(self,
                 snapshots_instance: Snapshots,
                 plugin_manager: PluginManager,
                 force_backup: bool):
        """
        Args:
            snapshots_parent: A workaround.
        """
        # Logical representation of the backup source
        self._source = None

        # Logical representation of the backup destination
        self._destination = None

        self.plugin_manager = plugin_manager
        self.plugin_manager.load(snapshots_instance)

        # TODO: Create the instance yourself
        self.messenger = snapshots_instance.backup_messenger
        self.messenger.clear_files()

        self.backup_log = snapshots_instance.snapshotLog

        # TODO: Need to get rid of that. This can overwrite some precondition
        # checks.
        self._force = force_backup

        self._backup_instance = None

    def proceed(self) -> bool:
        """The entry point to run/start the backup"""

        # Check some preconditions
        if not self._force and not self._backup_is_allowed():
            return False

        # Backup or restore already running?
        if self._backup_already_running() or self._restore_already_running():
            return False

        profile = ProfileContext().profile

        # TODO
        if profile.mode != 'local_gocryptfs':
            raise NotImplementedError

        # Warn about unknown power status if useful
        if profile.no_backup_on_battery and not tools.powerStatusAvailable():
            logger.warning(
                'Option "'
                + _('Disable backups when on battery')
                + '" is enabled but battery power status is not available.'
            )

        # Lock mechanism indicating that this application and profile is
        # running, no matter what it is doing. The lock is specific to the
        # current profile.
        with _application_instance_lock(self._backup_instance):

            # Global flock to block backups from other profiles or users
            # (and run them serialized). The argument "disabled" is a
            # workaround (#1751) that should be removed/refactored after
            # this method ("backup()") is refactored.
            with GlobalFlock(disable=not Konfig().global_flock):

                # inhibit suspend mode while backup
                with InhibitSuspend():

                    self._prepare_endpoints()
                    self._warn_about_free_space_at_destination()
                    self._warn_about_include_entries_missing_in_source()

                    result = self._run_backup()

        return result

    def _backup_already_running(self) -> bool:
        ctx = ProfileContext()
        self._backup_instance = ApplicationInstance(
            pidFile=str(ctx.take_backup_instance_file_path),
            autoExit=False,
            flock=True
        )

        if self._backup_instance.is_another_instance_running():
            logger.warning(
                'A backup process is already running. The PID of the running '
                f'backup is stored in {self._backup_instance.pidFile}. '
                'Consider deleting the PID file if there is actually no '
                'backup process running.'
            )
            self.plugin_manager.error(2)

            return True

        return False

    def _restore_already_running(self) -> bool:
        ctx = ProfileContext()
        instance = ApplicationInstance(
            pidFile=str(ctx.restore_instance_file_path),
            autoExit=False
        )

        if instance.is_another_instance_running():
            logger.warning(
                'A restore process is already running. Backup has been '
                'stopped. The PID of the running restore is stored in '
                f'{instance.pidFile}. Consider deleting the PID file '
                'if there is actually no restore process running.'
            )

            return True

        return False

    def _backup_is_allowed(self) -> bool:
        profile = ProfileContext().profile

        # Backup on battery allowed?
        if profile.no_backup_on_battery and tools.onBattery():
            self.messenger.set_info(_('Deferring backup while on battery'))
            logger.info('Deferring backup while on battery')
            return False

        # Scheduling
        if (
                profile.schedule_mode != ScheduleMode.DISABLED
                and not self._backup_is_scheduled()
        ):
            logger.info(
                f'Profile "{profile}" is not scheduled to run now.'
            )
            return False

        return True

    def _backup_is_scheduled(self) -> bool:
        profile = ProfileContext().profile

        if profile.schedule_mode in SCHEDULE_MODES_HANDLED_BY_CRON:
            return True

        if profile.schedule_mode in (ScheduleMode.REPEATEDLY,
                                     ScheduleMode.UDEV):
            timestamp_fp = schedule.get_anacron_spoolfile_path(profile)
            last_time = tools.readTimeStamp(str(timestamp_fp))

            if not last_time:
                return True

            return tools.crossed_at_least_units(
                start=last_time,
                end=datetime.datetime.now(),
                value=profile.schedule_repeated_period,
                unit=profile.schedule_repeated_unit
            )

        # Failsafe
        raise RuntimeError(
            f'Unexpected schedule mode {profile.schedule_mode} in {profile}'
        )

    def _prepare_endpoints(self):
        profile = ProfileContext().profile

        self._destination = BackupDestination(
            path=profile.local_gocryptfs_path,
            gocrypt_password=self._get_encryption_password()
        )

        if not self._destination.is_initialized():
            raise MountError(
                'Destination not initialized. Can not take backup',
                _(
                    'Can not take the backup because the destination is not '
                    'initialized.'
                )
            )

        # Reverse (encrypting) mount of the source dir

        # Note: Because of how rsync handels include/excludes the file
        # systems root "/" is treated as the source of the backup.

        self._source = BackupSources(
            include_paths=profile.includes_as_path,
            dest=self._destination
        )

    def _warn_about_free_space_at_destination(self):
        # User wished to be warned?
        profile = ProfileContext().profile

        if not profile.warn_free_space_enabled:
            return

        free = self._destination.get_free_space()

        # Unable to determine free space
        if free is None:
            return

        # Enough free space
        if free >= profile.warn_free_space:
            return

        msg = (
            f'Only {free} free space available on the destination, which is '
            f'below the configured threshold of {profile.warn_free_space}. '
            'The backup will proceed anyway.'
        )
        logger.warning(msg)
        self.messenger.set_error(msg)

    def _warn_about_include_entries_missing_in_source(self):
        """Log a warning if include list entries are missing in the backup
        source.

        If one or more entries can not be found in the backup source a
        warning message is logged.
        """
        missing_entries = self._source.get_include_paths_missing_in_source()

        if not missing_entries:
            return

        msg = _(
            'The following entries from the include list have no '
            'corresponding file or directory in the backup source:'
        )
        # Dev note (buhtz, 2025-03): To my research there is no elegant
        # solution to this problem.
        # Take care to keep this string consistent with the previous "msg"
        msg_untranslated = (
            'The following entries from the include list have no '
            'corresponding file or directory in the backup source:'
        )
        msg_suffix = ' "' + '", "'.join(missing_entries) + '"'

        self.messenger.set_error(msg + msg_suffix)
        logger.warning(msg_untranslated + msg_suffix)

    def _get_encryption_password(self):
        """Dirty workaround, taken from `Config`.

        Keep in mind that meaning of password1 and password2
        depends on the used mode and differs.
        """
        profile = ProfileContext().profile
        mode = profile.mode

        # TODO
        if mode != 'local_gocryptfs':
            raise NotImplementedError

        if 'gocryptfs' not in mode:
            raise RuntimeError(f'{mode} has no encryption password')

        password_provider = password.Password()

        # local encryption
        if mode == 'local_gocryptfs':
            pw_id = 1
        elif mode == 'ssh_gocryptfs':
            pw_id = 2
        else:
            raise RuntimeError(f'Unexpected situation. {mode=}')

        return password_provider.password(
            parent=None,
            profile_id=str(profile.profile_id),
            mode=mode,
            pw_id=pw_id,
            only_from_keyring=False
        )

    def _run_backup(self):
        ok = self.plugin_manager.processBegin()

        if not ok:
            logger.warning('A plugin prevented the backup')
            return ERROR

        dt_now = datetime.datetime.now()

        self.messenger.set_info('…')
        self.backup_log.new(
            date=dt_now,
            mounted_path=self._destination
        )

        return SUCCESS
