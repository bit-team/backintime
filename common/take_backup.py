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
from backupmsg import BackupMessenger
from konfig import Konfig
from pluginmanager import PluginManager
from profilecontext import ProfileContext
from snapshots import Snapshots
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

    def _backup_is_allowed(self) -> bool:
        profile = ProfileContext().profile

        # Backup on battery allowed?
        if profile.no_backup_on_battery and tools.onBattery():
            if not self._force:
                self.messenger.set_info(_('Deferring backup while on battery'))
                logger.info('Deferring backup while on battery')
                logger.warning('Backup not performed')

                return False



        # etc

        return False

    def proceed(self) -> bool:
        """The entry point to run/start the backup"""
        if not self._backup_is_allowed():
            return False
