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
from PyQt6.QtWidgets import (QCheckBox,
                             QDialog,
                             QGridLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QSpinBox,
                             QStyle,
                             QToolTip,
                             QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
import config
import qttools
from manageprofiles.statebindcheckbox import StateBindCheckBox
from manageprofiles.spinboxunit import SpinBoxWithUnit


class RemoveRetentionTab(QDialog):
    """The 'Remove & Retention' tab in the Manage Profiles dialog."""

    _STRETCH_FX = (1, )

    def __init__(self, parent):
        super().__init__(parent=parent)

        self._parent_dialog = parent

        # Vertical main layout
        # self._tab_layout = QVBoxLayout(self)
        self._tab_layout = QGridLayout()
        self.setLayout(self._tab_layout)

        # Keep most recent
        self._label_keep_most_recent()

        # Keep named backups
        self.cbDontRemoveNamedSnapshots = self._checkbox_keep_named()

        # ---
        self._tab_layout.addWidget(
            qttools.HLineWidget(),
            # fromRow
            self._tab_layout.rowCount(),
            # fromColumn
            0,
            # rowSpan,
            1,
            # columnSpan
            3)

        # Icon & Info label
        self._label_rule_execute_order()

        # ---
        self._tab_layout.addWidget(
            qttools.HLineWidget(),
            # fromRow
            self._tab_layout.rowCount(),
            # fromColumn
            0,
            # rowSpan,
            1,
            # columnSpan
            3)

        # Remove older than N years/months/days
        self._checkbox_remove_older, self._spinunit_remove_older \
            = self._remove_older_than()
        row = self._tab_layout.rowCount()
        self._tab_layout.addWidget(self._checkbox_remove_older, row, 0, 1, 2)
        self._tab_layout.addWidget(self._spinunit_remove_older, row, 2)

        # Retention policy
        self.cbSmartRemove, \
            self.cbSmartRemoveRunRemoteInBackground, \
            self.spbKeepAll, \
            self.spbKeepOnePerDay, \
            self.spbKeepOnePerWeek, \
            self.spbKeepOnePerMonth \
            = self._groupbox_retention_policy()

        # return spin_unit_space, spin_inodes
        self._checkbox_space, \
            self._spin_unit_space, \
            self._checkbox_inodes, \
            self._spin_inodes \
            = self._remove_free_space_inodes()

        self._tab_layout.setColumnStretch(0, 2)
        self._tab_layout.setColumnStretch(1, 1)
        self._tab_layout.setColumnStretch(2, 0)
        self._tab_layout.setRowStretch(self._tab_layout.rowCount(), 1)

    @property
    def config(self) -> config.Config:
        return self._parent_dialog.config

    def load_values(self):
        # don't remove named snapshots
        self.cbDontRemoveNamedSnapshots.setChecked(
            self.config.dontRemoveNamedSnapshots())

        # remove old snapshots
        enabled, value, unit = self.config.removeOldSnapshots()
        self._checkbox_remove_older.setChecked(enabled)
        self._spinunit_remove_older.set_value(value)
        self._spinunit_remove_older.select_unit(unit)

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

        # min free space
        enabled, value, unit = self.config.minFreeSpace()
        self._checkbox_space.setChecked(enabled)
        self._spin_unit_space.set_value(value)
        self._spin_unit_space.select_unit(unit)

        # min free inodes
        self._checkbox_inodes.setChecked(self.config.minFreeInodesEnabled())
        self._spin_inodes.setValue(self.config.minFreeInodes())

    def store_values(self):
        self.config.setRemoveOldSnapshots(
            self._checkbox_remove_older.isChecked(),
            self._spinunit_remove_older.value(),
            self._spinunit_remove_older.unit()
        )

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

        self.config.setMinFreeSpace(
            self._spin_unit_space.isEnabled(),
            self._spin_unit_space.value(),
            self._spin_unit_space.unit())

        self.config.setMinFreeInodes(
            self._spin_inodes.isEnabled(),
            self._spin_inodes.value())

    def update_items_state(self, enabled):
        self.cbSmartRemoveRunRemoteInBackground.setVisible(enabled)

    def _label_rule_execute_order(self) -> QWidget:
        # Icon
        icon = self.style().standardPixmap(
            QStyle.StandardPixmap.SP_MessageBoxInformation)
        icon = icon.scaled(
            icon.width()*2,
            icon.height()*2,
            Qt.AspectRatioMode.KeepAspectRatio)

        icon_label = QLabel(self)
        icon_label.setPixmap(icon)
        icon_label.setFixedSize(icon.size())

        # Info text
        txt = _(
            'The following rules are processed from top to bottom. Later rules '
            'override earlier ones and are not constrained by them. See the '
            '{manual} for details and examples.'
        ).format(
            manual='<a href="event:manual">{}</a>'.format(
                _('user manual')))
        txt_label = QLabel(txt)
        txt_label.setWordWrap(True)

        txt_label.linkActivated.connect(self.handle_link_activated)

        txt_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction)

        # Show URL in tooltip without anoing http-protocol prefix.
        txt_label.linkHovered.connect(
            lambda url: QToolTip.showText(
                # QCursor.pos(), url.replace('https://', ''))
                QCursor.pos(), _('Open user manual in browser.'))
        )

        wdg = QWidget()
        layout = QHBoxLayout(wdg)
        layout.addWidget(icon_label)
        layout.addWidget(txt_label)

        self._tab_layout.addWidget(wdg, self._tab_layout.rowCount(), 0, 1, 3)

    def handle_link_activated(self, link):
        qttools.open_user_manual()

    def _label_keep_most_recent(self) -> None:
        cb = QCheckBox(_('Keep the most recent snapshot.'), self)
        qttools.set_wrapped_tooltip(
            cb,
            (
                _('The last or freshest snapshot is kept under '
                  'all circumstances.'),
                _('That behavior cannot be changed.')
            )
        )

        # Always enabled
        cb.setChecked(True)
        cb.nextCheckState = lambda: None

        # fromRow, fromColumn spanning rowSpan rows and columnSpan
        self._tab_layout.addWidget(cb, self._tab_layout.rowCount(), 0, 1, 2)

    def _checkbox_keep_named(self) -> QCheckBox:
        cb = QCheckBox(_('Keep named snapshots.'), self)
        qttools.set_wrapped_tooltip(
            cb,
            _('Snapshots that have been given a name, in addition to the '
              'usual timestamp, will be retained under all circumstances '
              'and will not be removed.')
        )

        # fromRow, fromColumn spanning rowSpan rows and columnSpan
        self._tab_layout.addWidget(cb, self._tab_layout.rowCount(), 0, 1, 2)

        return cb

    def _remove_older_than(self) -> QWidget:
        # units
        units = {
            config.Config.DAY: _('Day(s)'),
            config.Config.WEEK: _('Week(s)'),
            config.Config.YEAR: _('Year(s)')
        }
        spin_unit = SpinBoxWithUnit(self, (1, 999), units)

        # checkbox
        checkbox = StateBindCheckBox(_('Remove snapshots older than'), self)
        checkbox.bind(spin_unit)

        # tooltip
        tip = (
            f'<strong>{units[config.Config.DAY]}</strong>: '
            + _('Full days. Current day ignored.'),
            f'<strong>{units[config.Config.WEEK]}</strong>: '
            + _('Calendar weeks with Monday as first day. '
                'Current week ignored.'),
            f'<strong>{units[config.Config.YEAR]}</strong>: '
            + _('12 months periods. Current months ignored.')
        )

        qttools.set_wrapped_tooltip(checkbox, tip)
        qttools.set_wrapped_tooltip(spin_unit, tip)

        return checkbox, spin_unit

    def _groupbox_retention_policy(self) -> tuple:
        layout = QGridLayout()
        # col, fx
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 0)

        checkbox_group = QGroupBox(_('Retention policy'), self)
        checkbox_group.setCheckable(True)
        checkbox_group.setLayout(layout)

        cb_in_background = QCheckBox(
            _('Run in background on remote host.'), self)
        qttools.set_wrapped_tooltip(
            cb_in_background,
            (_('The smart remove procedure will run directly on the remote '
               'machine, not locally. The commands "bash", "screen", and '
               '"flock" must be installed and available on the '
               'remote machine.'),
             _('If selected, Back In Time will first test the '
               'remote machine.')))
        layout.addWidget(cb_in_background, 0, 0, 1, 2)

        tip = _('The days are counted starting from today.')
        label = QLabel(_('Keep all snapshots for the last'), self)
        qttools.set_wrapped_tooltip(label, tip)
        layout.addWidget(label, 1, 0)
        all_last_days = QSpinBox(self)
        all_last_days.setRange(1, 999)
        all_last_days.setSuffix(' ' + _('day(s).'))
        qttools.set_wrapped_tooltip(all_last_days, tip)
        # all_last_days.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(all_last_days, 1, 1)

        # tip = same as the previous label
        label = QLabel(
            _('Keep the last snapshot for each day for the last'), self)
        qttools.set_wrapped_tooltip(label, tip)
        layout.addWidget(label, 2, 0)
        one_per_day = QSpinBox(self)
        one_per_day.setRange(1, 999)
        one_per_day.setSuffix(' ' + _('day(s).'))
        qttools.set_wrapped_tooltip(one_per_day, tip)
        # one_per_day.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(one_per_day, 2, 1)

        tip = _('The weeks are counted starting from the current running '
                'week. A week starts on Monday.')
        label = QLabel(
            _('Keep the last snapshot for each week for the last'), self)
        qttools.set_wrapped_tooltip(label, tip)
        layout.addWidget(label, 3, 0)
        one_per_week = QSpinBox(self)
        one_per_week.setRange(1, 999)
        one_per_week.setSuffix(' ' + _('week(s).'))
        qttools.set_wrapped_tooltip(one_per_week, tip)
        # one_per_week.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(one_per_week, 3, 1)

        tip = _('The months are counted as calendar months starting with '
                'the current months.')
        label = QLabel(
            _('Keep the last snapshot for each month for the last'), self)
        qttools.set_wrapped_tooltip(label, tip)
        layout.addWidget(label, 4, 0)
        one_per_month = QSpinBox(self)
        one_per_month.setRange(1, 999)
        one_per_month.setSuffix(' ' + _('month(s).'))
        qttools.set_wrapped_tooltip(one_per_month, tip)
        # one_per_month.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(one_per_month, 4, 1)

        tip = _('The years are counted as calendar years starting with '
                'the current year.')
        label = QLabel(_('Keep the last snapshot for each year for'), self)
        layout.addWidget(label, 5, 0)
        labeltwo = QLabel(_('all years.'), self)
        layout.addWidget(labeltwo, 5, 1)
        qttools.set_wrapped_tooltip([label, labeltwo], tip)

        self._tab_layout.addWidget(
            checkbox_group, self._tab_layout.rowCount(), 0, 1, 3)

        return (checkbox_group, cb_in_background, all_last_days, one_per_day,
                one_per_week, one_per_month)

    def _remove_free_space_inodes(self) -> tuple:
        # enabled, value, unit = self.config.minFreeSpace()

        # free space less than
        MIN_FREE_SPACE_UNITS = {
            config.Config.DISK_UNIT_MB: 'MiB',
            config.Config.DISK_UNIT_GB: 'GiB'
        }
        spin_unit_space = SpinBoxWithUnit(
            self, (1, 99999), MIN_FREE_SPACE_UNITS)

        checkbox_space = StateBindCheckBox(
            _('… the free space is less than'), self)
        checkbox_space.bind(spin_unit_space)

        # min free inodes
        checkbox_inodes = StateBindCheckBox(
            _('… the free inodes are less than'), self)

        spin_inodes = QSpinBox(self)
        spin_inodes.setSuffix(' %')
        spin_inodes.setRange(0, 15)

        checkbox_inodes.bind(spin_inodes)

        # layout
        groupbox = QGroupBox(_('Remove oldest snapshots if …'), self)
        grid = QGridLayout()
        groupbox.setLayout(grid)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.setColumnStretch(2, 0)

        # wdg, row, col
        grid.addWidget(checkbox_space, 0, 0, 1, 2)
        grid.addWidget(spin_unit_space, 0, 2)
        grid.addWidget(checkbox_inodes, 1, 0, 1, 2)
        grid.addWidget(spin_inodes, 1, 2)

        self._tab_layout.addWidget(
            groupbox,
            self._tab_layout.rowCount(),
            0, 1, 3
        )

        return checkbox_space, spin_unit_space, checkbox_inodes, spin_inodes
