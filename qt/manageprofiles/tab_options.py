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
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QLabel,
                             QCheckBox)
import config
import tools
import qttools
from bitbase import DiskSizeUnit
from event import Event
from manageprofiles import combobox
from manageprofiles.statebindcheckbox import StateBindCheckBox
from manageprofiles.spinboxunit import SpinBoxWithUnit


class OptionsTab(QDialog):
    """The 'Options' tab in the Manage Profiles dialog."""

    def __init__(self, parent):
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        self.cbNotify = QCheckBox(_('Enable notifications'), self)
        tab_layout.addWidget(self.cbNotify)

        self.cbNoSnapshotOnBattery \
            = QCheckBox(_('Disable backups when on battery'), self)
        tab_layout.addWidget(self.cbNoSnapshotOnBattery)

        if not tools.powerStatusAvailable():
            self.cbNoSnapshotOnBattery.setEnabled(False)
            self.cbNoSnapshotOnBattery.setToolTip(
                _('Power status not available from system'))

        self.cbGlobalFlock = QCheckBox(_('Run only one backup at a time'))
        tab_layout.addWidget(self.cbGlobalFlock)
        qttools.set_wrapped_tooltip(
            self.cbGlobalFlock,
            _('Other backups will be blocked until the current backup is '
              'completed. This is a global setting, meaning it will affect '
              'all profiles for this user. However, it must also be '
              'activated for all other users.')
        )

        self.cbBackupOnRestore = QCheckBox(
            _('Backup replaced files on restore'), self)
        tab_layout.addWidget(self.cbBackupOnRestore)
        qttools.set_wrapped_tooltip(
            self.cbBackupOnRestore,
            [
                _("Before restoring, newer versions of files will be renamed "
                  "with the appended {suffix}. These files can be removed "
                  "with the following command:").format(
                      suffix=self._parent_dialog.snapshots.backupSuffix()),
                'find ./ -name "*{suffix}" -delete'.format(
                    suffix=self._parent_dialog.snapshots.backupSuffix())
            ]
        )

        self.cbContinueOnErrors = QCheckBox(
            _('Continue on errors (keep incomplete backups)'), self)
        tab_layout.addWidget(self.cbContinueOnErrors)

        self.cbUseChecksum = QCheckBox(
            _('Use checksum to detect changes'), self)
        tab_layout.addWidget(self.cbUseChecksum)

        self.cbTakeSnapshotRegardlessOfChanges = QCheckBox(
            _('Create a new backup whether there were changes or not.'))
        tab_layout.addWidget(self.cbTakeSnapshotRegardlessOfChanges)

        # warn free space
        hlayout = QHBoxLayout()
        tab_layout.addLayout(hlayout)

        self.suWarnFreeSpace = SpinBoxWithUnit(
            self,
            (1, 9999999),
            {unit: str(unit) for unit in DiskSizeUnit}
        )

        self.cbWarnFreeSpace = StateBindCheckBox(
            _('Warn if the free disk space falls below'), self)
        self.cbWarnFreeSpace.bind(self.suWarnFreeSpace)
        hlayout.addWidget(self.cbWarnFreeSpace)
        hlayout.addWidget(self.suWarnFreeSpace)

        tooltip = [
            _('Shows a warning when free space on the backup destination disk '
              'is less than the specified value.'),
            _('If the Remove & Retention policy is enabled and old backups '
              'are removed based on available free space, this value cannot '
              'be lower than the value set in the policy.')
        ]
        qttools.set_wrapped_tooltip(self.suWarnFreeSpace, tooltip)
        qttools.set_wrapped_tooltip(self.cbWarnFreeSpace, tooltip)

        # Event: Notify observers if "remove less free space" value has changed
        self.event_warn_free_space_value_changed = Event()
        self.suWarnFreeSpace.spin.valueChanged.connect(
            lambda value:
            self.event_warn_free_space_value_changed.notify(value)
        )

        # log level
        hlayout = QHBoxLayout()
        tab_layout.addLayout(hlayout)

        hlayout.addWidget(QLabel(_('Log Level:'), self))

        self.comboLogLevel = self._combo_log_level()
        hlayout.addWidget(self.comboLogLevel)
        hlayout.addStretch()

        #
        tab_layout.addStretch()

    @property
    def config(self) -> config.Config:
        return self._parent_dialog.config

    def load_values(self):
        self.cbNotify.setChecked(self.config.notify())
        self.cbNoSnapshotOnBattery.setChecked(
            self.config.noSnapshotOnBattery())
        self.cbGlobalFlock.setChecked(self.config.globalFlock())
        self.cbBackupOnRestore.setChecked(self.config.backupOnRestore())
        self.cbContinueOnErrors.setChecked(self.config.continueOnErrors())
        self.cbUseChecksum.setChecked(self.config.useChecksum())
        self.cbTakeSnapshotRegardlessOfChanges.setChecked(
            self.config.takeSnapshotRegardlessOfChanges())
        value, unit = self.config.warnFreeSpace()
        self.cbWarnFreeSpace.setChecked(self.config.warnFreeSpaceEnabled())
        self.suWarnFreeSpace.set_value(value)
        self.suWarnFreeSpace.select_unit(unit)
        self.comboLogLevel.select_by_data(self.config.logLevel())

    def store_values(self):
        self.config.setNotify(self.cbNotify.isChecked())
        self.config.setNoSnapshotOnBattery(
            self.cbNoSnapshotOnBattery.isChecked())
        self.config.setGlobalFlock(self.cbGlobalFlock.isChecked())
        self.config.setBackupOnRestore(self.cbBackupOnRestore.isChecked())
        self.config.setContinueOnErrors(self.cbContinueOnErrors.isChecked())
        self.config.setUseChecksum(self.cbUseChecksum.isChecked())
        self.config.setTakeSnapshotRegardlessOfChanges(
            self.cbTakeSnapshotRegardlessOfChanges.isChecked())
        if self.suWarnFreeSpace.isEnabled():
            self.config.setWarnFreeSpace(
                self.suWarnFreeSpace.value(),
                self.suWarnFreeSpace.unit())
        else:
            self.config.setWarnFreeSpaceDisabled()

        self.config.setLogLevel(
            self.comboLogLevel.itemData(self.comboLogLevel.currentIndex()))

    def remove_free_space_value_changed(self, value):
        """Event handler in case the value of 'Remove if less than X free
        space' in 'Remove & Retention' tab was modified.

        That value can not be lower than 'Warn on free space' value.
        """
        warn_val = self.suWarnFreeSpace.value()

        if warn_val < value:
            self.suWarnFreeSpace.set_value(value)

    def _combo_log_level(self):
        fill = {
            0: _('None'),
            1: _('Errors'),
            2: _('Changes') + ' & ' + _('Errors'),
            3: _('All'),
        }
        return combobox.BitComboBox(self, fill)
