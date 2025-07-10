# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module offering a dialog to view log files.
"""
from PyQt6.QtWidgets import (QCheckBox,
                             QComboBox,
                             QDialog,
                             QDialogButtonBox,
                             QHBoxLayout,
                             QLabel,
                             QPlainTextEdit,
                             QVBoxLayout,
                             QWidget)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QFileSystemWatcher
import snapshots
import encfstools
import snapshotlog
import tools
import qttools
import qtsystrayicon
from statedata import StateData
from bitwidgets import SnapshotCombo, ProfileCombo


class LogViewDialog(QDialog):  # pylint: disable=too-many-instance-attributes
    """A log file viewer dialog"""
    def __init__(self,
                 parent: QWidget,
                 sid: snapshots.SID = None):
        """
        Args:
            parent: Parent widget.
            sid: Backup ID whose log file shall be shown. If ``None`` the last
                log is shown.
        """
        super().__init__(parent)

        self.config = parent.config
        # self.snapshots = parent.snapshots
        self._main_window = parent
        self.sid = sid
        self._enable_update = False  # ???
        self._decoder = None

        state_data = StateData()
        self.resize(*state_data.logview_dims)

        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415
        self.setWindowIcon(icon.VIEW_SNAPSHOT_LOG)
        self.setWindowTitle(
            _('Last Log View') if sid is None else _('Backup Log View'))

        main_layout = QVBoxLayout(self)

        layout = QHBoxLayout()
        main_layout.addLayout(layout)

        # profiles
        self._lbl_profile = QLabel(_('Profile:'), self)
        layout.addWidget(self._lbl_profile)

        self._combo_profiles = ProfileCombo(self)
        layout.addWidget(self._combo_profiles, 1)
        self._combo_profiles.currentIndexChanged.connect(
            self._slot_profile_changed)

        # No profile selector for specific log files or if started from systray
        if self.sid or isinstance(parent, qtsystrayicon.QtSysTrayIcon):
            self._lbl_profile.hide()
            self._combo_profiles.hide()

        # snapshots widget
        if self.sid:
            layout.addWidget(QLabel(_('Backups:'), self))
            self._combo_backups = SnapshotCombo(self)
            layout.addWidget(self._combo_backups, 1)
            self._combo_backups.currentIndexChanged.connect(
                self._slot_backups_changed)

        self._combo_filter = self._create_filter_widget()
        layout.addWidget(QLabel(_('Filter:'), self))
        layout.addWidget(self._combo_filter, 1)

        self._txt_log_view = self._create_text_log_view()
        main_layout.addWidget(self._txt_log_view)

        main_layout.addWidget(
            QLabel(_('[E] Error, [I] Information, [C] Change')))

        # decode path
        self._checkbox_decode = QCheckBox(_('decode paths'), self)
        self._checkbox_decode.stateChanged.connect(self._slot_decode_changed)
        main_layout.addWidget(self._checkbox_decode)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        main_layout.addWidget(btn_box)
        btn_box.rejected.connect(self.close)

        self._update_backups()
        self._update_decode()
        self._update_profiles()

        self.watcher = self._create_watcher()

    def _create_filter_widget(self) -> QComboBox:
        wdg = QComboBox(self)
        wdg.currentIndexChanged.connect(self._slot_filter_changed)

        wdg.addItem(_('All'), snapshotlog.LogFilter.NO_FILTER)

        # Note about ngettext plural forms: n=102 means "Other" in Arabic and
        # "Few" in Polish.
        # Research in translation community indicate this as the best fit to
        # the meaning of "all".
        wdg.addItem(' + '.join((_('Errors'), _('Changes'))),
                    snapshotlog.LogFilter.ERROR_AND_CHANGES)
        wdg.setCurrentIndex(wdg.count() - 1)
        wdg.addItem(_('Errors'), snapshotlog.LogFilter.ERROR)
        wdg.addItem(_('Changes'), snapshotlog.LogFilter.CHANGES)
        wdg.addItem(ngettext('Information', 'Information', 2),
                    snapshotlog.LogFilter.INFORMATION)
        wdg.addItem(_('rsync transfer failures (experimental)'),
                    snapshotlog.LogFilter.RSYNC_TRANSFER_FAILURES)

        return wdg

    def _create_text_log_view(self) -> QPlainTextEdit:
        wdg = QPlainTextEdit(self)
        wdg.setFont(QFont('Monospace'))
        wdg.setReadOnly(True)
        wdg.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        return wdg

    def _create_watcher(self) -> QFileSystemWatcher:
        """ Watch for changes in log file"""
        watcher = QFileSystemWatcher(self)

        if self.sid is None:
            # only watch if we show the last log
            log = self.config.takeSnapshotLogFile(
                self._combo_profiles.current_profile_id())

            watcher.addPath(log)

        # passes the path to the changed file
        watcher.fileChanged.connect(self._update_log)

        return watcher

    def _slot_decode_changed(self):
        if self._checkbox_decode.isChecked():
            if not self._decoder:
                self._decoder = encfstools.Decode(self.config)

        else:
            if self._decoder is not None:
                self._decoder.close()
            self._decoder = None

        self._update_log()

    def _slot_profile_changed(self, _idx):
        if not self._enable_update:
            return

        pid = self._combo_profiles.current_profile_id()
        self._main_window.comboProfiles.set_current_profile_id(pid)
        self._main_window.comboProfileChanged(None)

        self._update_decode()
        self._update_log()

    def _slot_backups_changed(self, _idx):
        if not self._enable_update:
            return

        self.sid = self._combo_backups.current_snapshot_id()
        self._update_log()

    def _slot_filter_changed(self, _idx):
        self._update_log()

    def _update_profiles(self):
        current_profile_id = self.config.currentProfile()

        self._combo_profiles.clear()

        qttools.update_combo_profiles(
            self.config, self._combo_profiles, current_profile_id)

        self._enable_update = True
        self._update_log()

        if len(self.config.profilesSortedByName()) <= 1:
            self._lbl_profile.setVisible(False)
            self._combo_profiles.setVisible(False)

    def _update_backups(self):
        if not self.sid:
            return

        self._combo_backups.clear()

        for sid in snapshots.iterSnapshots(self.config):
            self._combo_backups.add_snapshot_id(sid)

            if sid == self.sid:
                self._combo_backups.set_current_snapshot_id(sid)

    def _update_decode(self):
        if self.config.snapshotsMode() == 'ssh_encfs':
            self._checkbox_decode.show()
            return

        self._checkbox_decode.hide()
        self._checkbox_decode.setChecked(False)

    def _update_log(self, watched_path: str = None):
        """
        Show the log file of the current snapshot in the GUI

        Args:
            watched_path: Full path to a log file (as string) whose changes
                are watched via ``QFileSystemWatcher``. In case of changes
                this function is called with the log file and only the new
                lines in the log file are appended to the log file widget in
                the GUI. If ``None`` a complete log file will be shown at
                once.
        """
        if not self._enable_update:
            return

        mode = self._combo_filter.itemData(self._combo_filter.currentIndex())

        if watched_path and self.sid is None:
            # remove path from watch to prevent multiple updates at the same
            # time
            self.watcher.removePath(watched_path)

            # append only new lines to txtLogView
            log = snapshotlog.SnapshotLog(
                self.config, self._combo_profiles.current_profile_id())

            skip_n = self._txt_log_view.document().lineCount() - 1
            for line in log.get(mode=mode,
                                decode=self._decoder,
                                skipLines=skip_n):
                self._txt_log_view.appendPlainText(line)

            # re-add path to watch after 5sec delay
            alarm = tools.Alarm(
                callback=lambda: self.watcher.addPath(watched_path),
                overwrite=False)

            alarm.start(5)

            return

        if self.sid is None:
            log = snapshotlog.SnapshotLog(
                self.config, self._combo_profiles.current_profile_id())
            self._txt_log_view.setPlainText(
                '\n'.join(log.get(mode=mode, decode=self._decoder)))

            return

        self._txt_log_view.setPlainText(
            '\n'.join(self.sid.log(mode, decode=self._decoder)))

    def closeEvent(self, event):
        """Handle dialog closed event"""
        state_data = StateData()
        state_data.logview_dims = (self.width(), self.height())
        event.accept()
