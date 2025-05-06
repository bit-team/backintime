# SPDX-FileCopyrightText: © 2025 Samuel Moore
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""
status.py

Provides tools for managing and reporting backup status for profiles
used by the Back In Time backup system.

Supports command-line arguments to filter output by profile, show only issues,
or return the status in JSON format.

Status file is stored at $XDG_STATE_HOME/backupstatus.json (typically:
~/.local/state/backupstatus.json).
"""
import json
import os
import pathlib
from pathlib import Path
from datetime import datetime
from time import sleep
import argparse
import config
import logger
import sshtools
from exceptions import MountException
import snapshots


class BackupStatus():
    """
    A context manager that tracks and provides the most recent backup status
    for all profiles.

    The status includes information about the last successful backup, the last
    run completed, snapshot mode, and relevant paths. It can be retrieved in
    either a human-readable or JSON-formatted string.

    Args:
        args (argparse.Namespace, optional):
                        Command line arguments when called from command line.

        cfg (config.Config):
                        Current configuration object.

    Command line options (via args):
        --profile <name> or --profile-id <id>:
                        Get the status of a specific profile.
        --issues:
                        Get the status of profiles with an unsuccessful
                        last run.
        --json:
                        Get the status as a JSON-formatted string.


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
        self.cfg = cfg
        self.status = {}

    def update_status(self):
        """
        Called after a backup run is complete. Updates the status for the
        current profile or all profiles if no status file exists.
        """
        # Log file sometimes doesn't save right away due to buffering, reducing
        # timer at snapshotlog line 242 would avoid the need to do this
        sleep(2)
        if snapshots.NewSnapshot(self.cfg).saveToContinue:
            print("save to continue")
        if self.status == {}:
            self._create_status_file()
        else:
            self.status[
                self.cfg.profileName(self.profile_id)
                ] = self._create_profile_status()

    def _get_status(self):
        """
        Get the status dict for the current profile.

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

        def issues_filter(key):
            """Returns true if --issues flag is set and last backup for profile
            has errors or no backup exists."""
            return (
                not self.issues or not self.status[key].get('Last Backup') or
                self.status[key]['Last Backup'].get('Status') == 'Errors'
                )

        def remove_keys(dic, keys):
            """Helper function to remove specified keys from a dict. """
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
            if (self.all_status or profile_filter(key)) and issues_filter(key)
        }

        if result and self.json:
            result = json.dumps(result, indent=2)
        else:
            result = self._human(result) + '\n\n'

        return result

    def _create_profile_status(self):
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

            last_log = self.cfg.takeSnapshotLogFile(self.profile_id)
            last_log_ts = self._date_of(last_log)

            last_backup = snapshots.lastSnapshot(self.cfg)
            last_backup_ts = last_backup.date if last_backup else None

            last_success = next(
                    (backup for backup in snapshots.listSnapshots(self.cfg)
                        if not backup.failed), None
                    )
            last_success_ts = last_success.date if last_success else None

            status = {'Last Run Completed': str(last_log_ts)}

            if last_backup and last_success_ts == last_backup_ts:
                profile_status = "Success"
            else:
                profile_status = "Errors"

            if last_backup_ts:
                status['Last Backup'] = {'Status': profile_status,
                                         'Completed At': str(last_backup_ts)}
            if last_success_ts != last_backup_ts:
                status['Last Full Backup'] = str(last_success_ts)

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

    def _create_status_file(self):
        """
        Get the backup status for all profiles. Called when no snapshot
        status file exists.
        """
        backup_id = self.profile_id

        for profile in self.cfg.profiles():
            self.profile_id = profile
            profile_data = self._create_profile_status()
            self.status.update(
                {self.cfg.profileName(self.profile_id): profile_data}
                )

        self.profile_id = backup_id

    def _date_of(self, filename):
        file_path = pathlib.Path(filename)
        try:
            timestamp = file_path.stat().st_mtime
            timestamp_ts = datetime.fromtimestamp(timestamp)
            return timestamp_ts.strftime("%Y-%m-%d %H:%M:%S")

        except FileNotFoundError:
            return None

    def _longest_key(self, dic, depth=0):
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
                            self._longest_key(value, depth=depth + 1)
                            )

        return max_len

    def _human(self, dic, indent=0, width=-1):
        """
        Return dict (dic) as a human readable formatted string.
        """
        human = []
        singly_nested = 2
        doubly_nested = 4
        if width == -1:
            width = self._longest_key(dic) + 1
        if indent == 0:
            human.append('')

        for key, value in dic.items():
            if indent != doubly_nested:
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

            elif indent == singly_nested:
                human.append(f"{' ' * indent}{key:{width + 2}}: {value}")

            else:
                human.append(f"{' ' * indent}{key:{width}}: {value}")

        return '\n'.join(human)

    def _file_path(self):
        xdg_state = os.environ.get('XDG_STATE_HOME', None)
        if xdg_state:
            xdg_state = Path(xdg_state)
        else:
            xdg_state = Path.home() / '.local' / 'state'

        return xdg_state / 'backupstatus.json'

    def __str__(self):
        if not self.status:
            self._create_status_file()

        return self._get_status()

    def __repr__(self):
        if not self.status:
            self._create_status_file()

        self.json = True
        return self._get_status()

    def __enter__(self):
        try:
            with open(self._file_path(), 'r', encoding='utf-8') as f:
                self.status = json.load(f)
        except FileNotFoundError:
            logger.warning('Status file not found, creating new file.')
            self._create_status_file()
        except json.JSONDecodeError:
            logger.warning('Error reading status file, creating new file.')
            self._create_status_file()
        return self

    def __exit__(self, exc_type, exc_value, _):
        if exc_type:
            logger.error(f"{exc_type.__name__}: {exc_value}")

        try:
            with open(self._file_path(), 'w', encoding="utf-8") as f:
                json.dump(self.status, f, indent=2)

        except (OSError, TypeError) as e:
            logger.error(f"Error writing status file: {e}")
