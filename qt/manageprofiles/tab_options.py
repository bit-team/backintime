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
from manageprofiles import combobox


class OptionsTab(QDialog):
    """The 'Options' tab in the Manage Profiles dialog."""

    def __init__(self, parent):
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        # layoutWidget = QWidget(self)
        # layout = QVBoxLayout(layoutWidget)

        self.cbNotify = QCheckBox(_('Enable notifications'), self)
        tab_layout.addWidget(self.cbNotify)

        self.cbNoSnapshotOnBattery \
            = QCheckBox(_('Disable snapshots when on battery'), self)
        tab_layout.addWidget(self.cbNoSnapshotOnBattery)

        if not tools.powerStatusAvailable():
            self.cbNoSnapshotOnBattery.setEnabled(False)
            self.cbNoSnapshotOnBattery.setToolTip(
                _('Power status not available from system'))

        self.cbGlobalFlock = QCheckBox(_('Run only one snapshot at a time'))
        tab_layout.addWidget(self.cbGlobalFlock)
        qttools.set_wrapped_tooltip(
            self.cbGlobalFlock,
            _('Other snapshots will be blocked until the current snapshot '
              'is done. This is a global option. So it will affect all '
              'profiles for this user. But you need to activate this for all '
              'other users, too.')
        )

        self.cbBackupOnRestore = QCheckBox(
            _('Backup replaced files on restore'), self)
        tab_layout.addWidget(self.cbBackupOnRestore)
        qttools.set_wrapped_tooltip(
            self.cbBackupOnRestore,
            _("Newer versions of files will be renamed with trailing {suffix} "
              "before restoring. If you don't need them anymore you can "
              "remove them with {cmd}").format(
                  suffix=self._parent_dialog.snapshots.backupSuffix(),
                  cmd='find ./ -name "*{suffix}" -delete'.format(
                      suffix=self._parent_dialog.snapshots.backupSuffix()
                  )
              )
        )

        self.cbContinueOnErrors = QCheckBox(
            _('Continue on errors (keep incomplete snapshots)'), self)
        tab_layout.addWidget(self.cbContinueOnErrors)

        self.cbUseChecksum = QCheckBox(
            _('Use checksum to detect changes'), self)
        tab_layout.addWidget(self.cbUseChecksum)

        self.cbTakeSnapshotRegardlessOfChanges = QCheckBox(
            _('Take a new snapshot whether there were changes or not.'))
        tab_layout.addWidget(self.cbTakeSnapshotRegardlessOfChanges)

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
        self.config.setLogLevel(
            self.comboLogLevel.itemData(self.comboLogLevel.currentIndex()))

    def _combo_log_level(self):
        fill = {
            0: _('None'),
            1: _('Errors'),
            2: _('Changes') + ' & ' + _('Errors'),
            3: _('All'),
        }
        return combobox.BitComboBox(self, fill)
