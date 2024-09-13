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
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""The widget to setup scheduling backup jobs."""
import datetime
from PyQt6.QtWidgets import (QHBoxLayout,
                             QFormLayout,
                             QGroupBox,
                             QWidget,
                             QLabel,
                             QLineEdit,
                             QSpinBox,
                             QCheckBox)
import config
import tools
import qttools
import combobox


class ScheduleWidget(QGroupBox):
    """Widget about schedule snapshots.

    That widget is used in the 'General' tab of the 'Manage profiles' dialog.
    """
    def __init__(self, parent):
        super().__init__(title=_('Schedule'), parent=parent)

        main_layout = QFormLayout(self)

        def _create_form_entry(label: str, widget: QWidget = None) -> int:
            """Helper to create a row with a label and widget in the form
            layout.

            The returned index is used later to toggle visibility of that
            row.
            """
            if widget:
                main_layout.addRow(label, widget)
            else:
                lbl = QLabel(label)
                lbl.setWordWrap(True)
                main_layout.addRow(lbl)

            return main_layout.rowCount() - 1

        # Schedule modes
        self._combo_schedule_mode = self._schedule_mode_combobox()
        main_layout.addRow(self._combo_schedule_mode)

        # Day
        self._combo_day = self._day_combobox()
        self._rowidx_day = _create_form_entry(_('Day:'), self._combo_day)

        # Weekday
        self._combo_weekday = self._weekday_combobox()
        self._rowidx_weekday = _create_form_entry(
            _('Weekday:'), self._combo_weekday)

        # Time (formerly known as Hour)
        self._combo_time = self._time_combobox()
        self._rowidx_time = _create_form_entry(
            _('Time:'), self._combo_time)

        # HourS
        self._edit_cronpattern = QLineEdit(self)
        self._rowidx_cronpattern = _create_form_entry(
            _('Hours:'), self._edit_cronpattern)

        # Udev
        self._rowidx_udev = _create_form_entry(
            _('Run Back In Time as soon as the drive is connected (only once'
              ' every X days). You will be prompted for your sudo password.'))

        # Repeatedly (like anacron)
        self._rowidx_repeated = _create_form_entry(
            _('Run Back In Time repeatedly. This is useful if the computer '
              'is not running regularly.'))

        # Repeatedly - Every (value) (units)
        self._spin_period = QSpinBox(self)
        self._spin_period.setSingleStep(1)
        self._spin_period.setRange(1, 10000)
        self._combo_repeated_unit = self._repeated_unit_combobox()
        hlayout = QHBoxLayout()
        hlayout.addWidget(self._spin_period)
        hlayout.addWidget(self._combo_repeated_unit)
        hlayout.addStretch()
        self._rowidx_period = _create_form_entry(_('Every:'), hlayout)

        # Debug logging
        self._check_debug = QCheckBox(self)
        self._check_debug.setText(_('Enable logging of debug messages'))
        qttools.set_wrapped_tooltip(
            self._check_debug,
            [
                _('Writes debug-level messages into the system log via '
                  '"--debug".'),
                _('Caution: Only use this temporarily for diagnostics, as it '
                  'generates a large amount of output.')
            ]
        )
        self._rowidx_debug = main_layout.rowCount()
        main_layout.addRow(self._check_debug)

        # Signal
        self._combo_schedule_mode.currentIndexChanged.connect(
            self._slot_schedule_mode_changed)
        self._slot_schedule_mode_changed(None)

    def _schedule_mode_combobox(self) -> combobox.BitComboBox:
        """Create the the combobox for schedule mode.

        Returns:
            BitComboBox: The widget.
        """

        # Regular schedule modes for that combo box
        schedule_modes = {
            config.Config.NONE: _('Disabled'),
            config.Config.AT_EVERY_BOOT: _('At every boot/reboot'),
            config.Config._5_MIN: ngettext(
                'Every {n} minute', 'Every {n} minutes', 5).format(n=5),
            config.Config._10_MIN: ngettext(
                'Every {n} minute', 'Every {n} minutes', 10).format(n=10),
            config.Config._30_MIN: ngettext(
                'Every {n} minute', 'Every {n} minutes', 30).format(n=30),
            config.Config._1_HOUR: ngettext(
                'Every hour', 'Every {n} hours', 1).format(n=1),
            config.Config._2_HOURS: ngettext(
                'Every {n} hour', 'Every {n} hours', 2).format(n=2),
            config.Config._4_HOURS: ngettext(
                'Every {n} hour', 'Every {n} hours', 4).format(n=4),
            config.Config._6_HOURS: ngettext(
                'Every {n} hour', 'Every {n} hours', 6).format(n=6),
            config.Config._12_HOURS: ngettext(
                'Every {n} hour', 'Every {n} hours', 12).format(n=12),
            config.Config.CUSTOM_HOUR: _('Custom hours'),
            config.Config.DAY: _('Every day'),
            config.Config.REPEATEDLY: _('Repeatedly (anacron)'),
            config.Config.UDEV: _('When drive gets connected (udev)'),
            config.Config.WEEK: _('Every week'),
            config.Config.MONTH: _('Every month'),
            config.Config.YEAR: _('Every year')
        }

        return combobox.BitComboBox(self, schedule_modes)

    def _time_combobox(self) -> combobox.BitComboBox:
        """Combobox with time/hours (e.g. 03:00).

        Returns:
            BitComboBox: The widget.
        """

        # Dev note (buhtz): strftime is needed because of localization
        # {0: '00:00', 100: '01:00', ..., 2200: '22:00', 2300: '23:00'}
        times = {
            val*100: datetime.time(val, 0).strftime('%H:%M')
            for val in range(0, 24)
        }
        return combobox.BitComboBox(self, times)

    def _day_combobox(self) -> combobox.BitComboBox:
        """Combobox with day number in the month.

        Returns:
            BitComboBox: The widget.
        """
        days = {day: str(day) for day in range(1, 29)}
        return combobox.BitComboBox(self, days)

    def _weekday_combobox(self) -> combobox.BitComboBox:
        """Combobox with name of the weekday.

        Returns:
            BitComboBox: The widget.
        """
        sunday = datetime.date(2011, 11, 6)
        weekdays = {
            day: (sunday + datetime.timedelta(days=day)).strftime('%A')
            for day in range(1, 8)
        }
        return combobox.BitComboBox(self, weekdays)

    def _repeated_unit_combobox(self):
        """Combobox for "Every ..." schedule mode to select the units to use.

        Returns:
            BitComboBox: The widget.
        """
        repeatedly_units = {
            config.Config.HOUR: _('Hour(s)'),
            config.Config.DAY: _('Day(s)'),
            config.Config.WEEK: _('Week(s)'),
            config.Config.MONTH: _('Month(s)')
        }

        return combobox.BitComboBox(self, repeatedly_units)

    def _slot_schedule_mode_changed(self, _idx):
        """Handle value changed events for schedule mode combobox."""
        self._set_child_visibilities(self._combo_schedule_mode.current_data)

    def _set_child_visibilities(self, backup_mode_id: int):
        """Modify the visibility of child widgets (addressed by their index in
        the form layout) based on the selected schedule mode.
        """
        layout = self.layout()

        layout.setRowVisible(
            self._rowidx_cronpattern,
            backup_mode_id == config.Config.CUSTOM_HOUR)

        layout.setRowVisible(
            self._rowidx_weekday,
            backup_mode_id == config.Config.WEEK)

        layout.setRowVisible(
            self._rowidx_day,
            backup_mode_id == config.Config.MONTH)

        layout.setRowVisible(
            self._rowidx_time,
            backup_mode_id >= config.Config.DAY)

        vis = config.Config.REPEATEDLY <= backup_mode_id <= config.Config.UDEV
        layout.setRowVisible(
            self._rowidx_period,
            vis)

        if vis is True:
            layout.setRowVisible(self._rowidx_time, False)

        layout.setRowVisible(
            self._rowidx_repeated,
            backup_mode_id == config.Config.REPEATEDLY)

        layout.setRowVisible(
            self._rowidx_udev,
            backup_mode_id == config.Config.UDEV)

    def load_values(self, cfg: config.Config):
        """Set the values of the widgets regarding the current config."""

        self._combo_schedule_mode.select_by_data(cfg.scheduleMode())

        self._combo_time.select_by_data(cfg.scheduleTime())
        self._combo_day.select_by_data(cfg.scheduleDay())
        self._combo_weekday.select_by_data(cfg.scheduleWeekday())

        self._edit_cronpattern.setText(cfg.customBackupTime())

        self._spin_period.setValue(cfg.scheduleRepeatedPeriod())
        self._combo_repeated_unit.select_by_data(cfg.scheduleRepeatedUnit())

        self._check_debug.setChecked(cfg.scheduleDebug())

        self._slot_schedule_mode_changed(
            self._combo_schedule_mode.currentIndex())

    def store_values(self, cfg: config.Config) -> bool:
        """Store the widgets values in the config instance.

        Args:
            cfg: The configuration data instance.

        Returns:
            bool: Success or not.
        """

        if self._combo_schedule_mode.current_data == cfg.CUSTOM_HOUR:
            # Dev note (buhtz, 2024-05): IMHO checkCronPattern() is not needed
            # because the "crontab" command itself will validate this. See
            # schedule.write_crontab().
            # We just need to take care to catch an the error in the GUI
            # and report it to the user.
            # An alternative solution would be a GUI element where the user
            # is not able to input an invalid value. See #1449 about redesign
            # the schedule section in the Manage Profiles dialog.
            if not tools.checkCronPattern(self._edit_cronpattern.text()):

                cfg.errorHandler(
                    _('Custom hours can only be a comma separated list of '
                      'hours (e.g. 8,12,18,23) or */3 for periodic '
                      'backups every 3 hours.')
                )

                return False

        cfg.setScheduleMode(self._combo_schedule_mode.current_data)
        cfg.setScheduleTime(self._combo_time.current_data)
        cfg.setScheduleWeekday(self._combo_weekday.current_data)
        cfg.setScheduleDay(self._combo_day.current_data)
        cfg.setCustomBackupTime(self._edit_cronpattern.text())
        cfg.setScheduleRepeatedPeriod(self._spin_period.value())
        cfg.setScheduleRepeatedUnit(self._combo_repeated_unit.current_data)
        cfg.setScheduleDebug(self._check_debug.isChecked())

        return True
