# SPDX-FileCopyrightText: © 2025 Samuel Moore
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import json
import os
import pathlib
from pathlib import Path
from datetime import datetime
from time import sleep
import config
import argparse
import logger
import sshtools
from exceptions import MountException
import snapshots


class BackupStatus():
    """
    A context manager that tracks and provides the most recent backup status
    for all profiles. The status is stored in a JSON file and can be
    retrieved in a human-readable format or as a JSON-formatted string.
    The status includes information about the last successful backup,
    the last run completed, and the backup mode and paths. The status is
    stored in a file located at $XDG_STATE_HOME/backupstatus.json.

    Command line options:
        --profile <name> or --profile-id <id>:
                        Get the status of a specific profile.
        --issues:
                        Get the status of profiles with an unsuccessful
                        last run.
        --json:
                        Get the status as a JSON-formatted string.
        --help:
                        Show the help message and exit.

    Args:
        args (argparse.Namespace, optional):
                        Command line arguments when called from command line.

        cfg (config.Config):
                        Current configuration object. Used when called from
                        an active session after backup.

    Returns:
        `__repr__`:
                returns a JSON string representation.
        `__str__`:
                returns a human-readable formatted string.
    """
    def __init__(
            self, args: argparse.Namespace = None, cfg: config.Config = None
            ):
        self.profile = args.profile if args else None
        self.profile_id = args.profile_id if args else None
        self.all_status = not (self.profile or self.profile_id)
        self.issues = args.issues if args else None
        self.json = args.json if args else None
        self.args = args
        self.cfg = cfg
        self.status = {}
        xdg_state = os.environ.get('XDG_STATE_HOME', None)
        if xdg_state:
            xdg_state = Path(xdg_state)
        else:
            xdg_state = Path.home() / '.local' / 'state'

        self.path = xdg_state / 'backupstatus.json'

        logger.debug(f'Backup status path: {self.path}')

    def updateStatus(self):
        """
        Add the most recent backup to the backup status object.
        """
        # Log file sometimes doesn't save right away due to buffering, reducing
        # timer at snapshotlog line 242 would avoid the need to do this
        sleep(2)
        if self.status == {}:
            self._createStatusFile()
        else:
            self.status[
                self.cfg.profileName(self.profile_id)
                ] = self._createProfileStatus()

    def _getStatus(self):
        """
        Get status of either selected profile, all profiles, or profiles
        with an unsuccessful last run. Removes certain keys if returning
        a list (no specific profile specified).

        Returns:
            json str: If self.json is True
                        returns the status as a JSON-formatted string
            str: If self.json is False
                        returns the status as a human-readable string
        """
        # Filter for specified profile if --profile or --profile-id flags used
        def profile_filter(key):
            return (
                self.profile == key or
                self.cfg.profileName(self.profile_id) == key
                )

        # Check if --issues flag used and if it is, only return profiles
        # without successful last backup
        def issues_filter(key):
            return (
                not self.issues or not self.status[key].get('Last Backup') or
                self.status[key]['Last Backup'].get('Status') == 'Errors'
                )

        # Fields to remove if returning list of statuses
        keys_to_remove = ['Backup mode', 'Paths']

        result = {
            key: self._removeKeys(value, keys_to_remove)
            for key, value in self.status.items()
            if (self.all_status or profile_filter(key)) and issues_filter(key)
        }

        if result and self.json:
            result = json.dumps(result, indent=2)
        else:
            result = self._human(result) + '\n\n'

        return result

    def _createProfileStatus(self):
        """
        Create status entry for profile specified by self.profile_id.
        """
        self.cfg.setCurrentProfile(self.profile_id)
        cfg = self.cfg
        profile = cfg.profileName(self.profile_id)

        try:
            ssh = None
            if cfg.snapshotsMode() in ('ssh', 'ssh_encfs'):
                logger.info('Connecting to: ' + profile)
                ssh = sshtools.SSH(cfg)
                ssh.mount()

            lastLog = self.cfg.takeSnapshotLogFile(self.profile_id)
            lastLogDT = self._dateOf(lastLog)

            lastBackup = snapshots.lastSnapshot(self.cfg)
            lastBackupDT = lastBackup.date if lastBackup else None

            lastSuccess = next(
                    (backup for backup in snapshots.listSnapshots(self.cfg)
                        if not backup.failed), None
                    )
            lastSuccessDT = lastSuccess.date if lastSuccess else None

            status = {'Last Run Completed': str(lastLogDT)}

            if lastBackup and lastSuccessDT == lastBackupDT:
                profileStatus = "Success"
            else:
                profileStatus = "Errors"
            if lastBackupDT:
                status['Last Backup'] = {'Status': profileStatus,
                                         'Completed At': str(lastBackupDT)}
            if lastSuccessDT != lastBackupDT:
                status['Last Full Backup'] = str(lastSuccessDT)

            # Add mode and paths to backup detail
            status.update({
                'Backup mode': self.cfg.snapshotsMode(),
                'Paths': {
                    'Backups': self.cfg.sshSnapshotsFullPath() if ssh
                    else self.cfg.snapshotsFullPath(),
                    'Log file': self.cfg.takeSnapshotLogFile(),
                }})

            return status

        except MountException:
            ssh = None
            logger.warning('Unable to establish connection with : ' +
                           cfg.sshHost(profile_id=cfg.current_profile_id))
            return ({
                'Last Run Completed': 'Not avaliable',
                    'Note': 'Connect the drive and get status for this ' +
                    f'profile to update (id={self.profile_id})'
                    })

        finally:
            if ssh:
                ssh.umount()

    def _createStatusFile(self):
        """
        Get the backup status for all profiles. Called when no snapshot
        status file exists.
        """
        backup_id = self.profile_id

        for profile in self.cfg.profiles():
            self.profile_id = profile
            profile_data = self._createProfileStatus()
            self.status.update(
                {self.cfg.profileName(self.profile_id): profile_data}
                )

        self.profile_id = backup_id

    def _dateOf(self, filename):
        filePath = pathlib.Path(filename)
        try:
            timestamp = filePath.stat().st_mtime
            timestampDT = datetime.fromtimestamp(timestamp)
            return timestampDT.strftime("%Y-%m-%d %H:%M:%S")

        except FileNotFoundError:
            return None

    def _removeKeys(self, dic, keys):
        """Recursively removes specified keys from a dict (dic). """
        if isinstance(dic, dict):
            return {
                key: self._removeKeys(value, keys)
                for key, value in dic.items()
                if not self.all_status or key not in keys
            }

        return dic

    def _longestKey(self, dic, depth=0):
        """
        Get the length of the longest key from a dict (dic) to assist
        with formatting the output.
        """
        if depth > 0:
            max_len = max(map(len, dic.keys()), default=0)
        else:
            max_len = 0

        for value in dic.values():
            if isinstance(value, dict):
                max_len = max(
                            max_len,
                            self._longestKey(value, depth=depth + 1)
                            )

        return max_len

    def _human(self, dic, indent=0, width=-1):
        """
        Return dict (dic) as a human readable formatted string.
        """
        human = []
        if width == -1:
            width = self._longestKey(dic) + 1
        if indent == 0:
            human.append('')

        for key, value in dic.items():
            if indent != 4:
                human.append('')

            if isinstance(value, dict):
                human.append(f"{' ' * indent}{key}:")
                human.append(
                    self._human(value, indent=indent + 2, width=width)
                    )

            elif isinstance(value, list):
                human.append(f"{' ' * indent}{key:{width}}: [")
                for item in value:
                    human.append(f"{' ' * (indent + 2)}[{item}],")
                human.append(f'{' ' * indent}]')

            else:
                if indent == 2:
                    human.append(f"{' ' * indent}{key:{width + 2}}: {value}")
                else:
                    human.append(f"{' ' * indent}{key:{width}}: {value}")

        return '\n'.join(human)

    def __str__(self):
        if not self.status:
            self._createStatusFile()

        return self._getStatus()

    def __repr__(self):
        if not self.status:
            self._createStatusFile()

        self.json = True
        return self._getStatus()

    def __enter__(self):
        try:
            with open(self.path, 'r') as f:
                self.status = json.load(f)
        except FileNotFoundError:
            logger.warning('Status file not found, creating new file.')
            self._createStatusFile()
        except json.JSONDecodeError:
            logger.warning('Error reading status file, creating new file.')
            self._createStatusFile()
        return self

    def __exit__(self, exc_type, exc_value, _):
        if exc_type:
            logger.error(f"{exc_type.__name__}: {exc_value}")

        try:
            with open(self.path, 'w', encoding="utf-8") as f:
                json.dump(self.status, f, indent=2)

        except (OSError, TypeError) as e:
            logger.error(f"Error writing status file: {e}")
