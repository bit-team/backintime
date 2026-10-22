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
from applicationinstance import ApplicationInstance
from bitbase import ScheduleMode, SCHEDULE_MODES_HANDLED_BY_CRON
from pluginmanager import PluginManager
from profilecontext import ProfileContext
import schedule
from snapshots import Snapshots
import datetime
import logger
import tools


class TakeBackup:
    def __init__(self,
                 snapshots_instance: Snapshots,
                 plugin_manager: PluginManager,
                 force_backup: bool):
        """
        Args:
            snapshots_parent: A workaround.
        """
        self.plugin_manager = plugin_manager
        self.plugin_manager.load(snapshots_instance)

        # TODO: Create the instance yourself
        self.messenger = snapshots_instance.backup_messenger
        self.messenger.clear_files()

        # TODO: Need to get rid of that. This can overwrite some precondition
        # checks.
        self._force = force_backup

    def proceed(self) -> bool:
        """The entry point to run/start the backup"""

        # Check some preconditions
        if not self._force and not self._backup_is_allowed():
            return False

        # Backup or restore already running?
        if self._backup_already_running() or self._restore_already_running():
            return False

        profile = ProfileContext().profile

        # Warn about unknown power status if useful
        if profile.no_backup_on_battery and not tools.powerStatusAvailable():
            logger.warning(
                'Option "'
                + _('Disable backups when on battery')
                + '" is enabled but battery power status is not available.'
            )

    def _backup_already_running(self) -> bool:
        ctx = ProfileContext()
        instance = ApplicationInstance(
            pidFile=str(ctx.take_backup_instance_file_path),
            autoExit=False,
            flock=True
        )

        if instance.is_another_instance_running():
            logger.warning(
                'A backup process is already running. The PID of the running '
                f'backup is stored in {instance.pidFile}. Consider deleting '
                'the PID file if there is actually no backup process running.'
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
        if profile.schedule_mode != ScheduleMode.DISABLED:
            if not self._backup_is_scheduled():
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
