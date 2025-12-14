# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raak
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module about the Options tab"""
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QLabel,
                             QCheckBox)
import config
import tools
from event import Event
import qttools
from manageprofiles import combobox
from manageprofiles.statebindcheckbox import StateBindCheckBox
from manageprofiles.storagesizewidget import StorageSizeWidget


class OptionsTab(QDialog):
    """The 'Options' tab in the Manage Profiles dialog."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, parent):
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        self._cb_notify = QCheckBox(_('Enable notifications'), self)
        tab_layout.addWidget(self._cb_notify)

        self._cb_no_backup_on_battery \
            = QCheckBox(_('Disable backups when on battery'), self)
        tab_layout.addWidget(self._cb_no_backup_on_battery)

        if not tools.powerStatusAvailable():
            self._cb_no_backup_on_battery.setEnabled(False)
            self._cb_no_backup_on_battery.setToolTip(
                _('Power status not available from system'))

        self._cb_one_backup_at_a_time \
            = QCheckBox(_('Run only one backup at a time'))
        tab_layout.addWidget(self._cb_one_backup_at_a_time)
        qttools.set_wrapped_tooltip(
            self._cb_one_backup_at_a_time,
            _('Other backups will be blocked until the current backup is '
              'completed. This is a global setting, meaning it will affect '
              'all profiles for this user. However, it must also be '
              'activated for all other users.')
        )

        self._cb_backup_on_restore = QCheckBox(
            _('Backup replaced files on restore'), self)
        tab_layout.addWidget(self._cb_backup_on_restore)
        backup_suffix = self._parent_dialog.snapshots.backupSuffix()
        qttools.set_wrapped_tooltip(
            self._cb_backup_on_restore,
            [
                _("Before restoring, newer versions of files will be renamed "
                  "with the appended {suffix}. These files can be removed "
                  "with the following command:").format(
                      suffix=backup_suffix),
                f'find ./ -name "*{backup_suffix}" -delete'
            ]
        )

        self._cb_continue_on_errors = QCheckBox(
            _('Continue on errors (keep incomplete backups)'), self)
        tab_layout.addWidget(self._cb_continue_on_errors)

        self._cb_use_checksum = QCheckBox(
            _('Use checksum to detect changes'), self)
        tab_layout.addWidget(self._cb_use_checksum)

        self._cb_backup_regard_changes = QCheckBox(
            _('Create a new backup whether there were changes or not.'))
        tab_layout.addWidget(self._cb_backup_regard_changes)

        # warn free space
        hlayout = QHBoxLayout()
        tab_layout.addLayout(hlayout)

        self._su_warn_free_space = StorageSizeWidget(self, (1, 9999999))
        self._cb_warn_free_space = StateBindCheckBox(
            _('Warn if the free disk space falls below'), self)
        self._cb_warn_free_space.bind(self._su_warn_free_space)
        hlayout.addWidget(self._cb_warn_free_space)
        hlayout.addWidget(self._su_warn_free_space)

        tooltip = [
            _('Shows a warning when free space on the backup destination disk '
              'is less than the specified value.'),
            _('If the Remove & Retention policy is enabled and old backups '
              'are removed based on available free space, this value cannot '
              'be lower than the value set in the policy.')
        ]
        qttools.set_wrapped_tooltip(self._su_warn_free_space, tooltip)
        qttools.set_wrapped_tooltip(self._cb_warn_free_space, tooltip)

        # Event: Notify observers if "remove less free space" value has changed
        self.event_warn_free_space_value_changed = Event()
        # pylint: disable=unnecessary-lambda
        self._su_warn_free_space.event_value_changed.register(
            lambda value:
            self.event_warn_free_space_value_changed.notify(value)
        )

        # log level
        hlayout = QHBoxLayout()
        tab_layout.addLayout(hlayout)

        hlayout.addWidget(QLabel(_('Log Level:'), self))

        self._combo_log_level = self._create_combo_log_level()
        hlayout.addWidget(self._combo_log_level)
        hlayout.addStretch()

        tab_layout.addStretch()

    @property
    def config(self) -> config.Config:
        """The config instance."""
        return self._parent_dialog.config

    def load_values(self):
        """Load config values into the GUI"""
        self._cb_notify.setChecked(self.config.notify())
        self._cb_no_backup_on_battery.setChecked(
            self.config.noSnapshotOnBattery())
        self._cb_one_backup_at_a_time.setChecked(self.config.globalFlock())
        self._cb_backup_on_restore.setChecked(self.config.backupOnRestore())
        self._cb_continue_on_errors.setChecked(self.config.continueOnErrors())
        self._cb_use_checksum.setChecked(self.config.useChecksum())
        self._cb_backup_regard_changes.setChecked(
            self.config.takeSnapshotRegardlessOfChanges())
        value = self.config.warnFreeSpace()
        self._cb_warn_free_space.setChecked(self.config.warnFreeSpaceEnabled())
        self._su_warn_free_space.set_storagesize(value)
        self._combo_log_level.select_by_data(self.config.logLevel())

    def store_values(self):
        """Store values from GUI into the config"""
        self.config.setNotify(self._cb_notify.isChecked())
        self.config.setNoSnapshotOnBattery(
            self._cb_no_backup_on_battery.isChecked())
        self.config.setGlobalFlock(self._cb_one_backup_at_a_time.isChecked())
        self.config.setBackupOnRestore(self._cb_backup_on_restore.isChecked())
        self.config.setContinueOnErrors(
            self._cb_continue_on_errors.isChecked())
        self.config.setUseChecksum(self._cb_use_checksum.isChecked())
        self.config.setTakeSnapshotRegardlessOfChanges(
            self._cb_backup_regard_changes.isChecked())
        if self._su_warn_free_space.isEnabled():
            self.config.setWarnFreeSpace(
                self._su_warn_free_space.get_storagesize())
        else:
            self.config.setWarnFreeSpaceDisabled()

        self.config.setLogLevel(self._combo_log_level.current_data)

    def remove_free_space_value_changed(self, value):
        """Event handler in case the value of 'Remove if less than X free
        space' in 'Remove & Retention' tab was modified.

        That value can not be lower than 'Warn on free space' value.
        """
        warn_val = self._su_warn_free_space.get_storagesize()

        if warn_val < value:
            self._su_warn_free_space.set_storagesize(
                value, dont_touch_unit=True)

    def _create_combo_log_level(self) -> combobox.BitComboBox:
        fill = {
            0: _('None'),
            1: _('Errors'),
            2: _('Changes') + ' & ' + _('Errors'),
            3: _('All'),
        }
        return combobox.BitComboBox(self, fill)
