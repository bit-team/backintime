# SPDX-FileCopyrightText: © 2025 Samuel Moore
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""
Tool for reporting the status of backup profiles.

This script supports command-line arguments to:
- Filter output by profile
- Return the status in JSON format

The status file is stored at:
$XDG_STATE_HOME/backintime-backup-status.json
(typically: ~/.local/state/backintime-backup-status.json).
"""
import json
import os
from pathlib import Path
from datetime import datetime
import config
import logger
import sshtools
from exceptions import MountException
import snapshots


class BackupStatus:
    """
    Reports the status of the most recent backup for all profiles.

    The status includes details about the last backup, the last
    run, backup mode, and relevant paths. It can be formatted as a
    human-readable string or JSON.

    Args:
        cfg: Configuration object.
        all_status: Status for all profiles.
        json: If True, output is in JSON format.
    """

    def __init__(self,
                 cfg: config.Config,
                 all_status: bool = True,
                 format_json: bool = False):

        self.cfg = cfg
        self.json = format_json
        self.all_status = all_status
        self.status = {}

    def get_status(self):
        """
        Get the formatted status of the backup profiles.

        Returns:
            str:
                        Human-readable or JSON-formatted string (depending
                        on self.json).
        """
        self._read_status_file()

        status = self.status.get(
            self.cfg.profileName(),
            None
        )

        if status is None or status['Last Run'] in [None, 'Unknown']:

            logger.warning(
                f'No status found for profile "{self.cfg.currentProfile()}". '
                'Trying to create new status entry.'
            )
            self.update_status()

        return self._get_formatted_status()

    def update_status(self, timestamp: datetime = None):
        """
        Update the status for the current profile, called after a backup
        attempt.

        If no status file exists, all profiles will be checked and
        the status file will be created. The selected profile will then
        be updated to ensure it is using the timestamp of the last
        backup attempt.

        Args:
            timestamp (datetime, optional):
                        Timestamp to use as the last run time.
        """
        profile_name = self.cfg.profileName()
        self._read_status_file()
        self.status[profile_name] = self._create_profile_status(timestamp)
        self._write_status_file()

    def _read_status_file(self):
        """
        Read the backup status file from disk and store the data in
        self.status. If the file does not exist or is invalid, create a new
        status file for all profiles.
        """
        try:
            with open(_status_file_path(), 'r', encoding='utf-8') as handle:
                self.status = json.load(handle)

        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.warning('Problems while reading status file. '
                           f'Creating new file. Error was {exc}')
            self._create_status_file()

    def _write_status_file(self):
        """
        Write the current status dictionary to the backup status file.
        """
        try:
            with open(_status_file_path(), 'w', encoding='utf-8') as handle:
                json.dump(self.status, handle)

        except (OSError, TypeError) as exc:
            logger.error(f'Error writing status file: {exc}')

    def _create_status_file(self):
        """
        Create a status dictionary for all profiles and save it to disk.
        Called when no backup status file exists.
        """

        for profile in self.cfg.profiles():
            profile_data = self._create_profile_status(profile_id=profile)
            self.status[self.cfg.profileName(profile)] = profile_data

        self._write_status_file()

    def _create_profile_status(self,
                               profile_id: str,
                               timestamp: datetime = None) -> dict:
        """
        Create a status entry for a single profile. Called for each profile by
        _create_status_file() when no backup status file exists or by
        update_status() when updating the status of a single profile after
        a backup attempt.

        Args:
            timestamp (datetime, optional):
                        Timestamp for the last run completed.

        Returns:
            dict:
                        Status data for the profile.
        """
        original_profile_id = self.cfg.currentProfile()
        self.cfg.setCurrentProfile(profile_id)

        try:
            ssh = None
            if self.cfg.snapshotsMode() in ('ssh', 'ssh_encfs'):
                logger.info('Connecting to: ' + self.cfg.profileName())
                ssh = sshtools.SSH(self.cfg)
                ssh.mount()

            # Get the last run timestamp
            if timestamp is not None:
                # If a timestamp is provided, use it for the last run
                last_log_ts = timestamp.strftime("%x %X")
            else:
                # use the timestamp from the last log file
                last_log = self.cfg.takeSnapshotLogFile(profile_id)
                last_log_ts = _date_of(last_log)

            status = {
                'Last Run': str(last_log_ts) if last_log_ts else None
            }

            # Get the timestamp for most recent backup
            last_backup = snapshots.lastSnapshot(self.cfg)
            last_backup_ts = last_backup.date.strftime("%x %X")\
                if last_backup else None

            # If there has been a backup, add its timestamp
            if last_backup_ts:
                status['Last Backup'] = str(last_backup_ts)

            # Add mode and paths to backup detail
            status.update({
                'Backup mode': self.cfg.snapshotsMode(),
                'Paths': {
                    'Backups': self.cfg.sshSnapshotsFullPath() if ssh
                    else self.cfg.snapshotsFullPath(),
                    'Log file': self.cfg.takeSnapshotLogFile(),
                }})

        except MountException:
            ssh = None
            logger.warning('Unable to establish connection with : '
                           f'{self.cfg.sshHost(profile_id=profile_id)}')
            status = (
                {
                    'Last Run': 'Connect the drive to get status',
                    'Last Backup': f'for this profile (id={profile_id})'
                }
            )

        finally:
            self.cfg.setCurrentProfile(original_profile_id)
            if ssh:
                ssh.umount()

        return status

    def _get_formatted_status(self) -> str:
        """
        Format the backup status data for output based on the instance's
        CLI-related flags (`self.json`, `self.profile_id`).

        The output can be:
        - Human-readable text if `self.json` is False (default).
        - JSON-formatted string if `self.json` is True.

        Filtering:
        - If `self.profile_id` is set, only the status for that profile is
            included.

        If a list of statuses will be returned, some keys ('Backup mode' and
        'Paths') are omitted to keep the output more clear.

        Returns:
            str:
                        A formatted string of the status data, either in
                        human-readable format or as JSON.
        """
        def profile_filter(key):
            """Returns true if the current profile should be printed, either
            because no profile is specified, or the profile name matches
            the key."""

            return self.all_status or self.cfg.profileName() == key

        def remove_keys(dic, keys):
            """Helper function to remove specified keys from a dict."""

            if isinstance(dic, dict):
                return {
                    key: remove_keys(value, keys) for key, value in dic.items()
                    if not self.all_status or key not in keys
                }

            return dic

        # Fields to remove if returning list of statuses
        keys_to_remove = ['Backup mode', 'Paths']

        result = {
            key: remove_keys(value, keys_to_remove)
            for key, value in self.status.items()
            if profile_filter(key)
        }

        if self.json:
            return json.dumps(result)

        return _human(result)


def _date_of(filename: str) -> str:
    """Return the modified date of a file (or None if file doesn't exist)."""
    file_path = Path(filename)

    try:
        timestamp = file_path.stat().st_mtime

    except FileNotFoundError:
        return None

    timestamp_ts = datetime.fromtimestamp(timestamp)

    return timestamp_ts.strftime("%x %X")


def _human(dic: dict) -> str:
    """
    Return a human-readable string representation of a nested dictionary.

    Args:
        dic (dict):
                        Dictionary to format.

    Returns:
        str:
                        Formatted string.
    """
    result = []

    for profile, info in dic.items():
        result.append(f"{profile}:")
        for label in ['Last Run', 'Last Backup', 'Backup mode', 'Paths']:
            value = info.get(label)
            if isinstance(value, dict):
                sub_items = [f"\n     {k:<9}: {v}" for k, v in value.items()]
                value = ''.join(sub_items)
            if label == 'Last Run' or value is not None:
                result.append(f"  {label:<12}: {value}")

    return '\n'.join(result)


def _status_file_path() -> Path:
    """
    Get the path to the status file based on XDG state home.

    Returns:
        Path: Path to the status file.
    """
    xdg_state = os.environ.get(
        'XDG_STATE_HOME',
        Path.home() / '.local' / 'state')

    return Path(xdg_state) / 'backintime-backup-status.json'
