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
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QLabel,
                             QCheckBox)
import tools
import qttools
from manageprofiles import combobox


class AutoRemoveTab(QDialog):
    """The 'Auto-remove' tab in the Manage Profiles dialog."""

    def __init__(self, parent):
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        layoutWidget = QWidget(self)
        layout = QGridLayout(layoutWidget)

        # older than
        self.cbRemoveOlder = QCheckBox(_('Older than:'), self)
        layout.addWidget(self.cbRemoveOlder, 0, 0)
        self.cbRemoveOlder.stateChanged.connect(self.updateRemoveOlder)

        self.spbRemoveOlder = QSpinBox(self)
        self.spbRemoveOlder.setRange(1, 1000)
        layout.addWidget(self.spbRemoveOlder, 0, 1)

        self.comboRemoveOlderUnit = QComboBox(self)
        layout.addWidget(self.comboRemoveOlderUnit, 0, 2)

        REMOVE_OLD_BACKUP_UNITS = {
            config.Config.DAY: _('Day(s)'),
            config.Config.WEEK: _('Week(s)'),
            config.Config.YEAR: _('Year(s)')}

        self.fillCombo(self.comboRemoveOlderUnit, REMOVE_OLD_BACKUP_UNITS)

        # free space less than
        enabled, value, unit = self.config.minFreeSpace()

        self.cbFreeSpace = QCheckBox(
            _('If free space is less than:'), self)
        layout.addWidget(self.cbFreeSpace, 1, 0)
        self.cbFreeSpace.stateChanged.connect(self.updateFreeSpace)

        self.spbFreeSpace = QSpinBox(self)
        self.spbFreeSpace.setRange(1, 1000)
        layout.addWidget(self.spbFreeSpace, 1, 1)

        self.comboFreeSpaceUnit = QComboBox(self)
        layout.addWidget(self.comboFreeSpaceUnit, 1, 2)
        MIN_FREE_SPACE_UNITS = {
            config.Config.DISK_UNIT_MB: 'MiB',
            config.Config.DISK_UNIT_GB: 'GiB'
        }

        self.fillCombo(self.comboFreeSpaceUnit,
                       MIN_FREE_SPACE_UNITS)

        # min free inodes
        self.cbFreeInodes = QCheckBox(
            _('If free inodes is less than:'), self)
        layout.addWidget(self.cbFreeInodes, 2, 0)

        self.spbFreeInodes = QSpinBox(self)
        self.spbFreeInodes.setSuffix(' %')
        self.spbFreeInodes.setSingleStep(1)
        self.spbFreeInodes.setRange(0, 15)
        layout.addWidget(self.spbFreeInodes, 2, 1)

        enabled = lambda state: self.spbFreeInodes.setEnabled(state)
        enabled(False)
        self.cbFreeInodes.stateChanged.connect(enabled)

        # smart remove
        self.cbSmartRemove = QCheckBox(_('Smart removal:'), self)
        layout.addWidget(self.cbSmartRemove, 3, 0)

        widget = QWidget(self)
        widget.setContentsMargins(25, 0, 0, 0)
        layout.addWidget(widget, 4, 0, 1, 3)

        smlayout = QGridLayout(widget)

        self.cbSmartRemoveRunRemoteInBackground = QCheckBox(
            '{} {}!'.format(
                _('Run in background on remote host.'),
                _('EXPERIMENTAL')
            ),
            self)
        smlayout.addWidget(self.cbSmartRemoveRunRemoteInBackground, 0, 0, 1, 3)

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

        enabled = lambda state: [smlayout.itemAt(x).widget().setEnabled(state) for x in range(smlayout.count())]
        enabled(False)
        self.cbSmartRemove.stateChanged.connect(enabled)

        # don't remove named snapshots
        self.cbDontRemoveNamedSnapshots \
            = QCheckBox(_("Don't remove named snapshots."), self)
        layout.addWidget(self.cbDontRemoveNamedSnapshots, 5, 0, 1, 3)

        #
        layout.addWidget(QWidget(self), 6, 0)
        layout.setRowStretch(6, 2)
        scrollArea.setWidget(layoutWidget)
        scrollArea.setWidgetResizable(True)


        tab_layout.addStretch()

    @property
    def config(self) -> config.Config:
        return self._parent_dialog.config

    def load_values(self):
        pass

    def store_values(self):
        pass

    def _combo_log_level(self):
        fill = {
            0: _('None'),
            1: _('Errors'),
            2: _('Changes') + ' & ' + _('Errors'),
            3: _('All'),
        }
        return combobox.BitComboBox(self, fill)
