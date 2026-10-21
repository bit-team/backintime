# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""
Code was extract from snapshots.py and is based on the takeSnapshotMessage()
mechanic. Regarding commit history this seems to be introduced by Oprea Dan
before 1.0.0.

This is an interim module. The mechanic will be replaced by improved
interprocess communication (see issue #2260).
"""
from __future__ import annotations
import os
import datetime
import logger
import bitbase
from applicationinstance import ApplicationInstance
from pluginmanager import PluginManager
from profilecontext import ProfileContext
from snapshotlog import SnapshotLog


class BackupMessenger:
    """The class encapsulates the original takeSnapshotMessage mechanism.
    """

    def __init__(self,
                 snapshot_log: SnapshotLog,
                 plugin_manager: PluginManager):
        """
        Args:
            worker_id: Used in file names. Recommend to use the profile id.
        """
        # TODO check if the ProfileContext is really used at this point.
        profile_ctx = ProfileContext()
        self._profile = profile_ctx.profile

        self.lastBusyCheck = datetime.datetime(1, 1, 1)

        self._msg_file = profile_ctx.message_file_path
        self._progress_file = profile_ctx.progress_file_path
        self._take_backup_instance_file = profile_ctx.app_instance_file_path

        self._snapshot_log = snapshot_log
        self._plugin_manager = plugin_manager

    def clear_files(self):
        """Delete message and progress file"""
        self._msg_file.unlink(missing_ok=True)
        self._progress_file.unlink(missing_ok=True)

    def _is_backup_instance_busy(self):
        """Was snapshots.Snapshot.busy()
        """
        instance = ApplicationInstance(
            str(self._take_backup_instance_file), False
        )
        return instance.busy()

    def get_message(self) -> tuple[int, str] | None:
        """Get the current message from the message file.

        Returns: The message type and its string or `None`.
        """
        # Dev note (buhtz): Not sure what happens here or why this is useful.
        wait = datetime.datetime.now() - datetime.timedelta(seconds=5)

        if self.lastBusyCheck < wait:
            self.lastBusyCheck = datetime.datetime.now()

            if not self._is_backup_instance_busy():
                self.clear_files()

                return None

        if not self._msg_file.exists():
            return None

        try:
            with self._msg_file.open(mode='rt', encoding='utf-8') as handle:
                items = handle.read().split('\n')

        # TODO (buhtz): Too broad exception
        except OSError as exc:
            logger.warning(
                'Failed to get takeSnapshot message from '
                f'{self._msg_file}: {str(exc)}'
            )

            return None

        if len(items) < 2:
            return None

        # "Message id": Type of the message.
        mid = 0

        try:
            mid = int(items[0])

        # TODO (buhtz): Too broad exception
        except Exception as exc:
            logger.debug('Failed to extract message ID from '
                         f'{items}: {str(exc)}', self)

        return (mid, '\n'.join(items[1:]))

    def set_message(self, type_id: int, message: str, timeout: int = -1):
        """Update the status message of the active snapshot creation job

        Write the status message into a message file to allow async
        processing for the GUI, plug-ins (like user-callback)
        and desktop notifications.

        Args:
            type_id: Simplified severity level of the status message:
                     0: INFO
                     1: ERROR
                     other values: defaults to INFO (may change in the future)
            message: status message string
            timeout: Requested maximum processing duration in plug-ins.
                     Default: -1 (no limit)
                     Called plug-ins must try to keep the timeout itself
                     (it is not enforced by the ``PluginManager``.
                     In fact currently all known plug-ins do
                     ignore the timeout value!
        """

        # self._msg_file
        # message_fn = self.config.takeSnapshotMessageFile()

        try:
            # Write message to file (and overwrites the previous one)
            with self._msg_file.open(mode='wt', encoding='utf-8') as handle:
                handle.write(f'{type_id}\n{message}')

        except OSError as exc:
            logger.warning(
                'Failed to set takeSnapshot message to '
                f'{self._msg_file}: {str(exc)}'
            )

        # Error message?
        if type_id == 1:
            self._snapshot_log.append(msg=f'[E] {message}', level=1)

        else:
            self._snapshot_log.append(msg=f'[I] {message}', level=3)

        try:
            self._plugin_manager.message(
                profile_id=str(self._profile.profile_id),
                profile_name=self._profile.name,
                level=type_id,
                message=message,
                timeout=timeout
            )

        except Exception as exc:
            logger.warning(f'Failed to send message to plugins: {str(exc)}')

    def set_info(self, message: str, timeout: int = -1):
        self.set_message(type_id=0, message=message, timeout=timeout)

    def set_error(self, message: str, timeout: int = -1):
        self.set_message(type_id=1, message=message, timeout=timeout)
