# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Based on code extracted from config.py
"""Check and validate the configuration.

The code was extracted and decoupled from config.py
"""
from typing import Optional
import logger
import core_events
from konfig import Konfig, Profile
from mount import MountManager


class CheckConfigAgent:  # pylint: disable=too-few-public-methods
    """An agent manage some checkups of the configuration."""
    def __init__(self, profile: Optional[Profile] = None):
        self._profiles = None

        # Ensure a list of profiles
        if profile:
            self._profiles = [profile]

        else:
            real_konfig = Konfig()
            self._profiles = list(real_konfig.iter_profiles())

    def _check_profile(self, profile: Profile):
        """Check the configuration of one profile"""
        logger.debug(f'Check {profile}')

        mount_manager = MountManager.create(self)
        mount_path = mount_manager.path
        # snapshots_path = one_profile.snapshots_path

        # check the backups mountpoint (formerly known as "snapshot_path")
        if not mount_path:
            core_events.event_error.notify(
                _('Profile: "{name}"').format(name=profile.name)
                + '\n'
                # Don't like this error message!
                + _('Backup directory is not valid.')
            )
            return False

        # check include
        if not profile.include:
            core_events.event_error.notify(
                _('Profile: "{name}"').format(name=profile.name)
                + '\n'
                + _('At least one directory must be selected for backup.')
            )

            return False

        # ???
        snapshots_path2 = str(mount_path)
        if snapshots_path2[-1] != '/':
            snapshots_path2 = snapshots_path2 + '/'

        for item in profile.include:
            if item[1] != 0:
                continue

            path = item[0]
            if path == str(mount_path):
                core_events.event_error.notify(
                    _('Profile: "{name}"').format(name=profile.name)
                    + '\n'
                    + _('Directory: {path}').format(path=path)
                    + '\n'
                    + _(
                        'This directory cannot be included in the '
                        'backup as it is part of the backup '
                        'destination itself.'
                    )
                )

                return False

            if len(path) >= len(snapshots_path2):
                if path[: len(snapshots_path2)] == snapshots_path2:
                    core_events.event_error.notify(
                        _('Profile: "{name}"').format(name=profile.name)
                        + '\n'
                        + _('Directory: {path}').format(path=path)
                        + '\n'
                        + _(
                            'This directory cannot be included in the '
                            'backup as it is part of the backup '
                            'destination itself.'
                        )
                    )

                    return False

        # check warn free space
        if profile.warn_free_space_enabled and profile.min_free_space_enabled:

            warn = profile.warn_free_space
            _enabled, min_free = profile.min_free_space

            if warn < min_free:
                core_events.event_error.notify(
                    _('Profile: "{name}"').format(name=profile.name)
                    + '\n'
                    + _('There is a conflict between two settings.')
                    + '\n\n'
                    + _(
                        'The value for "Remove oldest backup if the '
                        'free space is less than" ({val_one}) must be '
                        'less than or equal the threshold for "Warn if '
                        'free disk space falls below" ({val_two}).'
                    ).format(val_one=min_free, val_two=warn)
                    + '\n'
                    + _(
                        'Please adjust the settings so that the backup '
                        'removal limit is not higher than the '
                        'warning limit.'
                    )
                )
                return False

        return True

    def check(self):
        """Check the configuration of one or all profiles"""

        # each profile
        for one_profile in self._profiles:
            rc = self._check_profile(one_profile)

            if rc is False:
                return rc

        return True
