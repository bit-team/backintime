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
- Show only issues
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

    The status includes details about the last successful backup, the last
    run, backup mode, and relevant paths. It can be formatted as a
    human-readable string or JSON.

    Args:
        cfg: Configuration object.
        all_status: Status for all profiles.
        issues: If True, only profiles with issues are shown.
        json: If True, output is in JSON format.
    """

    def __init__(self,
                 cfg: config.Config,
                 all_status: bool = True,
                 issues: bool = False,
                 format_json: bool = False):

        self.cfg = cfg
        self.issues = issues
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
            with open(_status_file_path(), 'r', encoding='utf-8') as f:
                self.status = json.load(f)

        except FileNotFoundError:
            logger.warning('Status file not found, creating new file.')
            self._create_status_file()

        except json.JSONDecodeError:
            logger.warning('Error reading status file, creating new file.')
            self._create_status_file()

    def _write_status_file(self):
        """
        Write the current status dictionary to the backup status file.
        """
        try:
            with open(_status_file_path(), 'w', encoding='utf-8') as f:
                json.dump(self.status, f, indent=2)

        except (OSError, TypeError) as exc:
            logger.error(f'Error writing status file: {exc}')

    def _create_status_file(self):
        """
        Create a status dictionary for all profiles and save it disk.
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
                last_log_ts = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                # use the timestamp from the last log file
                last_log = self.cfg.takeSnapshotLogFile(profile_id)
                last_log_ts = _date_of(last_log)

            status = {
                'Last Run': str(last_log_ts) if last_log_ts else None
            }

            # Get the timestamp for most recent backup (w or w/out errors)
            last_backup = snapshots.lastSnapshot(self.cfg)
            last_backup_ts = last_backup.date if last_backup else None

            # Get the timestamp for the last successful backup (no errors)
            last_success = next(
                (backup for backup in snapshots.listSnapshots(self.cfg)
                    if not backup.failed), None
            )
            last_success_ts = last_success.date if last_success else None

            # If timestamps for most recent and last successful backup
            # are the same, then the last backup was successful.
            if last_backup and last_success_ts == last_backup_ts:
                profile_status = "Success"
            else:
                profile_status = "Errors"

            # If there has been a backup, add its status and timestamp
            if last_backup_ts:
                status['Last Backup'] = {
                    'Status': profile_status,
                    'Completed At': str(last_backup_ts)
                }

            # If last backup was with errors, add the last successful
            # backup timestamp
            if last_success_ts != last_backup_ts:
                status['Last Full Backup'] = str(
                    last_success_ts
                ) if last_success_ts else None

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
                    'Last Run': 'Unknown',
                    'Note': 'Connect the drive to get status for this '
                            f'profile (id={profile_id})'
                }
            )

        finally:
            if ssh:
                ssh.umount()

        self.cfg.setCurrentProfile(original_profile_id)

        return status

    def _get_formatted_status(self) -> str:
        """
        Format the backup status data for output based on the instance's
        CLI-related flags (`self.json`, `self.profile_id`, `self.issues`).

        The output can be:
        - Human-readable text if `self.json` is False (default).
        - JSON-formatted string if `self.json` is True.

        Filtering:
        - If `self.profile_id` is set, only the status for that profile is
            included.
        - If `self.issues` is True, only profiles with errors in their last
            backup (or no successful backup) are included.

        If a list of statuses will be returned, some keys ('Backup mode' and
        'Paths') are omitted to keep the output more clear.

        Returns:
            str:
                        A formatted string of the status data, either in
                        human-readable format or as JSON.
        """
        def profile_filter(key):
            """Returns true if the current profile should be printed, either
            because no profile is specified, the issues flag is set,
            or the profile name matches the key."""

            return self.all_status or self.issues \
                or self.cfg.profileName() == key

        def issues_filter(key):
            """Returns true if --issues flag is not set or it is set and
            either no backup exists or last backup for profile has errors."""

            return (not self.issues
                    or not self.status[key].get('Last Backup')
                    or self.status[key]['Last Backup'].get(
                        'Status') == 'Errors')

        def remove_keys(dic, keys):
            """Helper function to remove specified keys from a dict."""

            if isinstance(dic, dict):
                return {
                    key: remove_keys(value, keys) for key, value in dic.items()
                    if (not self.all_status and not self.issues) or key
                    not in keys
                }

            return dic

        # Fields to remove if returning list of statuses
        keys_to_remove = ['Backup mode', 'Paths']

        result = {
            key: remove_keys(value, keys_to_remove)
            for key, value in self.status.items()
            if profile_filter(key) and issues_filter(key)
        }

        if self.json:
            return json.dumps(result, indent=2)

        return _human(result)


def _date_of(filename: str) -> str:
    """Return the modified date of a file (or None if file doesn't exist)."""
    file_path = Path(filename)

    try:
        timestamp = file_path.stat().st_mtime

    except FileNotFoundError:
        return None

    timestamp_ts = datetime.fromtimestamp(timestamp)

    return timestamp_ts.strftime("%Y-%m-%d %H:%M:%S")


def _longest_key(dic: dict, depth: int = 0) -> int:
    """
    Find the length of the longest key in a nested dictionary
    to assist with formatting for human-readable output.

    Args:
        dic (dict):
                        Dictionary to search.
        depth (int):
                        Current recursion depth, used internally.
                        Should not be set manually.

    Returns:
        int:
                        Length of the longest key.
    """
    max_len = max(map(len, dic.keys()), default=0) if depth > 0 else 0

    for value in dic.values():
        if isinstance(value, dict):
            max_len = max(
                max_len,
                _longest_key(value, depth=depth + 1)
            )

    return max_len


def _human(dic: dict, indent: int = 0, width: int = None) -> str:
    """
    Return a human-readable string representation of a nested dictionary.

    Args:
        dic (dict):
                        Dictionary to format.
        indent (int):
                        Indentation level, used internally for recursion.
                        Should not be set manually.
        width (int):
                        Key width for alignment, calculated automatically
                        during recursion.
                        Should not be set manually.

    Returns:
        str:
                        Formatted string.
    """
    human = []
    singly_nested = 2
    # doubly_nested = 4

    if width is None:
        width = _longest_key(dic)

    for key, value in dic.items():
        if isinstance(value, dict):
            if indent == 0 and human:
                human.append('')

            human.append(f"{' ' * indent}{key}:")
            human.append(
                _human(value, indent=indent + 2, width=width)
            )

        elif indent == singly_nested:
            human.append(f"{' ' * indent}{key:{width + 2}}: {value}")

        else:
            human.append(f"{' ' * indent}{key:{width}}: {value}")

    return '\n'.join(human)


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
