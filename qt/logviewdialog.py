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
                 parent: QWidget | qtsystrayicon.QtSysTrayIcon = None,
                 sid: snapshots.SID = None,
                 decode: bool = False):
        """
        Args:
            parent: Parent widget.
            sid: Backup ID whose log file shall be shown. If ``None`` the last
                log is shown.
        """
        super().__init__(parent if isinstance(parent, QWidget) else None)

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
        self._checkbox_decode.setChecked(decode)
        main_layout.addWidget(self._checkbox_decode)

        self._create_buttons(main_layout)

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

    def closeEvent(self, event):  # noqa: N802
        """Handle dialog closed event"""
        state_data = StateData()
        state_data.logview_dims = (self.width(), self.height())
        event.accept()

    def _create_buttons(self, main_layout):
        """Create Help and Close buttons"""
        btn_layout = QHBoxLayout()
        main_layout.addLayout(btn_layout)
        btn_layout.addStretch(1)

        self.help_window = HelpWindow()

        btn_box_help = QDialogButtonBox(QDialogButtonBox.StandardButton.Help)
        btn_layout.addWidget(btn_box_help)
        btn_box_help.helpRequested.connect(self.help_window.show)

        btn_box_close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_layout.addWidget(btn_box_close)
        btn_box_close.rejected.connect(self.close)


class HelpWindow(QDialog):
    """An rsync changes help dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('Rsync Changes Guide'))
        text = _("""
        The rsync list of changes follows this format:
        YXcstpoguax  path/to/file

        The update types that replace the Y are as follows:
          o  A < means that a file is being transferred to the remote host
             (sent).

          o  A > means that a file is being transferred to the local host
             (received).

          o  A c means that a local change/creation is occurring for the item
             (such as the creation of a directory or the changing of a
             symlink, etc.).

          o  A h means that the item is a hard link to another item (requires
             --hard-links).

          o  A . means that the item is not being updated (though it might
             have attributes that are being modified).

          o  A * means that the rest of the itemized-output area contains a
             message (e.g. "deleting").

        The file-types that replace the X are:
          o  f for a file

          o  d for a directory

          o  L for a symlink

          o  D for a device

          o  S for a special file (e.g. named sockets and fifos).

        The other letters in the string indicate if some attributes of the
        file have changed, as follows:
          o  "." - the attribute is unchanged.

          o  "+" - the file is newly created.

          o  " " - all the attributes are unchanged (all dots turn to spaces).

          o  "?" - the change is unknown (when the remote rsync is old).

          o  A letter indicates an attribute is being updated.

        The attribute that is associated with each letter is as follows:
          o  A c means either that a regular file has a different checksum
             (requires --checksum) or that a symlink, device, or special file
             has a changed value.  Note that if you are sending files to an
             rsync prior to 3.0.1, this change flag will be present only for
             checksum-differing regular files.

          o  A s means the size of a regular file is different and will be
             updated by the file transfer.

          o  A t means the modification time is different and is being updated
             to the sender's value (requires --times).  An alternate value of
             T means that the modification time will be set to the transfer
             time, which happens when a file/symlink/device is updated without
             --times and when a symlink is changed and the receiver can't set
             its time. (Note: when using an rsync 3.0.0 client, you might see
             the s flag combined with t instead of the proper T flag for
             this time-setting failure.)

          o  A p means the permissions are different and are being updated to
             the sender's value (requires --perms).

          o  An o means the owner is different and is being updated to the
             sender's value (requires --owner and super-user privileges).

          o  A g means the group is different and is being updated to the
             sender's value (requires --group and the authority to set the
             group).

          o  A u|n|b indicates the following information:
              o  u  means the access (use) time is different and is being
                 updated to the sender's value (requires --atimes)

              o  n means the create time (newness) is different and is being
                 updated to the sender's value (requires --crtimes)

              o  b means that both the access and create times are being
                 updated

          o  The a means that the ACL information is being changed.

          o  The x means that the extended attribute information is being
             changed.
        """)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(text, self))

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(btn_box)
        btn_box.rejected.connect(self.close)
