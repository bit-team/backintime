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
                             QGridLayout,
                             QVBoxLayout,
                             QGroupBox,
                             QLabel,
                             QSpinBox,
                             QCheckBox)
import config
import qttools
from manageprofiles.combobox import BitComboBox
from manageprofiles.statebindcheckbox import StateBindCheckBox


class AutoRemoveTab(QDialog):
    """The 'Auto-remove' tab in the Manage Profiles dialog."""

    def __init__(self, parent):
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        # older than
        self.spbRemoveOlder = QSpinBox(self)
        self.spbRemoveOlder.setRange(1, 1000)

        REMOVE_OLD_BACKUP_UNITS = {
            config.Config.DAY: _('Day(s)'),
            config.Config.WEEK: _('Week(s)'),
            config.Config.YEAR: _('Year(s)')
        }
        self.comboRemoveOlderUnit = BitComboBox(self, REMOVE_OLD_BACKUP_UNITS)

        self.cbRemoveOlder = StateBindCheckBox(_('Older than:'), self)
        self.cbRemoveOlder.bind(self.spbRemoveOlder)
        self.cbRemoveOlder.bind(self.comboRemoveOlderUnit)

        # free space less than
        enabled, value, unit = self.config.minFreeSpace()

        self.spbFreeSpace = QSpinBox(self)
        self.spbFreeSpace.setRange(1, 1000)

        MIN_FREE_SPACE_UNITS = {
            config.Config.DISK_UNIT_MB: 'MiB',
            config.Config.DISK_UNIT_GB: 'GiB'
        }
        self.comboFreeSpaceUnit = BitComboBox(self, MIN_FREE_SPACE_UNITS)

        self.cbFreeSpace = StateBindCheckBox(_('If free space is less than:'), self)
        self.cbFreeSpace.bind(self.spbFreeSpace)
        self.cbFreeSpace.bind(self.comboFreeSpaceUnit)

        # min free inodes
        self.cbFreeInodes = QCheckBox(_('If free inodes is less than:'), self)

        self.spbFreeInodes = QSpinBox(self)
        self.spbFreeInodes.setSuffix(' %')
        self.spbFreeInodes.setSingleStep(1)
        self.spbFreeInodes.setRange(0, 15)

        enabled = lambda state: self.spbFreeInodes.setEnabled(state)
        enabled(False)
        self.cbFreeInodes.stateChanged.connect(enabled)

        grid = QGridLayout()
        tab_layout.addLayout(grid)
        grid.addWidget(self.cbRemoveOlder, 0, 0)
        grid.addWidget(self.spbRemoveOlder, 0, 1)
        grid.addWidget(self.comboRemoveOlderUnit, 0, 2)
        grid.addWidget(self.cbFreeSpace, 1, 0)
        grid.addWidget(self.spbFreeSpace, 1, 1)
        grid.addWidget(self.comboFreeSpaceUnit, 1, 2)
        grid.addWidget(self.cbFreeInodes, 2, 0)
        grid.addWidget(self.spbFreeInodes, 2, 1)
        grid.setColumnStretch(3, 1)

        tab_layout.addSpacing(tab_layout.spacing()*2)

        # Smart removal: checkable GroupBox
        self.cbSmartRemove = QGroupBox(_('Smart removal:'), self)
        self.cbSmartRemove.setCheckable(True)
        smlayout = QGridLayout()
        smlayout.setColumnStretch(3, 1)
        self.cbSmartRemove.setLayout(smlayout)
        tab_layout.addWidget(self.cbSmartRemove)

        # Smart removal: the items...
        self.cbSmartRemoveRunRemoteInBackground = QCheckBox(
                _('Run in background on remote host.'), self)
        qttools.set_wrapped_tooltip(
            self.cbSmartRemoveRunRemoteInBackground,
            (
                _('The smart remove procedure will run directly on the remote '
                  'machine, not locally. The commands "bash", "screen", and '
                  '"flock" must be installed and available on the '
                  'remote machine.'),
                _('If selected, Back In Time will first test the '
                  'remote machine.')
            )
        )
        smlayout.addWidget(self.cbSmartRemoveRunRemoteInBackground, 0, 0, 1, 2)

        smlayout.addWidget(
            QLabel(_('Keep all snapshots for the last'), self), 1, 0)
        self.spbKeepAll = QSpinBox(self)
        self.spbKeepAll.setRange(1, 10000)
        smlayout.addWidget(self.spbKeepAll, 1, 1)
        smlayout.addWidget(QLabel(_('day(s).'), self), 1, 2)

        smlayout.addWidget(
            QLabel(_('Keep one snapshot per day for the last'), self), 2, 0)
        self.spbKeepOnePerDay = QSpinBox(self)
        self.spbKeepOnePerDay.setRange(1, 10000)
        smlayout.addWidget(self.spbKeepOnePerDay, 2, 1)
        smlayout.addWidget(QLabel(_('day(s).'), self), 2, 2)

        smlayout.addWidget(
            QLabel(_('Keep one snapshot per week for the last'), self), 3, 0)
        self.spbKeepOnePerWeek = QSpinBox(self)
        self.spbKeepOnePerWeek.setRange(1, 10000)
        smlayout.addWidget(self.spbKeepOnePerWeek, 3, 1)
        smlayout.addWidget(QLabel(_('week(s).'), self), 3, 2)

        smlayout.addWidget(
            QLabel(_('Keep one snapshot per month for the last'), self), 4, 0)
        self.spbKeepOnePerMonth = QSpinBox(self)
        self.spbKeepOnePerMonth.setRange(1, 1000)
        smlayout.addWidget(self.spbKeepOnePerMonth, 4, 1)
        smlayout.addWidget(QLabel(_('month(s).'), self), 4, 2)

        smlayout.addWidget(
            QLabel(_('Keep one snapshot per year for all years.'), self),
            5, 0, 1, 3)

        # don't remove named snapshots
        self.cbDontRemoveNamedSnapshots \
            = QCheckBox(_('Keep named snapshots.'), self)
        self.cbDontRemoveNamedSnapshots.setToolTip(
            _('Snapshots that, in addition to the usual timestamp, have been '
              'given a name will not be deleted.'))
        tab_layout.addWidget(self.cbDontRemoveNamedSnapshots)

        tab_layout.addStretch()

    @property
    def config(self) -> config.Config:
        return self._parent_dialog.config

    def load_values(self):
        # remove old snapshots
        enabled, value, unit = self.config.removeOldSnapshots()
        self.cbRemoveOlder.setChecked(enabled)
        self.spbRemoveOlder.setValue(value)
        self.comboRemoveOlderUnit.select_by_data(unit)

        # min free space
        enabled, value, unit = self.config.minFreeSpace()
        self.cbFreeSpace.setChecked(enabled)
        self.spbFreeSpace.setValue(value)
        self.comboFreeSpaceUnit.select_by_data(unit)

        # min free inodes
        self.cbFreeInodes.setChecked(self.config.minFreeInodesEnabled())
        self.spbFreeInodes.setValue(self.config.minFreeInodes())

        # smart remove
        smart_remove, keep_all, keep_one_per_day, keep_one_per_week, \
            keep_one_per_month = self.config.smartRemove()
        self.cbSmartRemove.setChecked(smart_remove)
        self.spbKeepAll.setValue(keep_all)
        self.spbKeepOnePerDay.setValue(keep_one_per_day)
        self.spbKeepOnePerWeek.setValue(keep_one_per_week)
        self.spbKeepOnePerMonth.setValue(keep_one_per_month)
        self.cbSmartRemoveRunRemoteInBackground.setChecked(
            self.config.smartRemoveRunRemoteInBackground())

        # don't remove named snapshots
        self.cbDontRemoveNamedSnapshots.setChecked(
            self.config.dontRemoveNamedSnapshots())

    def store_values(self):
        self.config.setRemoveOldSnapshots(
            self.cbRemoveOlder.isChecked(),
            self.spbRemoveOlder.value(),
            self.comboRemoveOlderUnit.current_data
        )

        self.config.setMinFreeSpace(
            self.cbFreeSpace.isChecked(),
            self.spbFreeSpace.value(),
            self.comboFreeSpaceUnit.current_data)

        self.config.setMinFreeInodes(
            self.cbFreeInodes.isChecked(),
            self.spbFreeInodes.value())

        self.config.setDontRemoveNamedSnapshots(
            self.cbDontRemoveNamedSnapshots.isChecked())

        self.config.setSmartRemove(
            self.cbSmartRemove.isChecked(),
            self.spbKeepAll.value(),
            self.spbKeepOnePerDay.value(),
            self.spbKeepOnePerWeek.value(),
            self.spbKeepOnePerMonth.value())

        self.config.setSmartRemoveRunRemoteInBackground(
            self.cbSmartRemoveRunRemoteInBackground.isChecked())

    def update_items_state(self, enabled):
        self.cbSmartRemoveRunRemoteInBackground.setVisible(enabled)
