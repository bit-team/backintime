# Back In Time
# Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey,
# Germar Reitze
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QDialog,
                             QLabel,
                             QPlainTextEdit,
                             QVBoxLayout,
                             QHBoxLayout,
                             QComboBox,
                             QDialogButtonBox,
                             QCheckBox,
                             )
from PyQt6.QtCore import QFileSystemWatcher
import qttools
import snapshots
import encfstools
import snapshotlog
import tools


class LogViewDialog(QDialog):
    def __init__(self, parent, sid=None, systray=False):
        """
        Instantiate a snapshot log file viewer

        Args:
            parent:
            sid (:py:class:`SID`): snapshot ID whose log file shall be shown
                                   (``None`` = show last log)
            systray (bool): TODO Show log from systray icon or from App (boolean)
        """
        if systray:
            super(LogViewDialog, self).__init__()
        else:
            super(LogViewDialog, self).__init__(parent)

        self.config = parent.config
        self.snapshots = parent.snapshots
        self.mainWindow = parent
        self.sid = sid
        self.enableUpdate = False
        self.decode = None

        w = self.config.intValue('qt.logview.width', 800)
        h = self.config.intValue('qt.logview.height', 500)
        self.resize(w, h)

        import icon
        self.setWindowIcon(icon.VIEW_SNAPSHOT_LOG)
        if self.sid is None:
            self.setWindowTitle(_('Last Log View'))
        else:
            self.setWindowTitle(_('Snapshot Log View'))

        self.mainLayout = QVBoxLayout(self)

        layout = QHBoxLayout()
        self.mainLayout.addLayout(layout)

        # profiles
        self.lblProfile = QLabel(_('Profile:'), self)
        layout.addWidget(self.lblProfile)

        self.comboProfiles = qttools.ProfileCombo(self)
        layout.addWidget(self.comboProfiles, 1)
        self.comboProfiles.currentIndexChanged.connect(self.profileChanged)

        # snapshots
        self.lblSnapshots = QLabel(_('Snapshots:'), self)
        layout.addWidget(self.lblSnapshots)
        self.comboSnapshots = qttools.SnapshotCombo(self)
        layout.addWidget(self.comboSnapshots, 1)
        self.comboSnapshots.currentIndexChanged.connect(self.comboSnapshotsChanged)

        if self.sid is None:
            self.lblSnapshots.hide()
            self.comboSnapshots.hide()

        if self.sid or systray:
            self.lblProfile.hide()
            self.comboProfiles.hide()

        # filter
        layout.addWidget(QLabel(_('Filter:'), self))

        self.comboFilter = QComboBox(self)
        layout.addWidget(self.comboFilter, 1)
        self.comboFilter.currentIndexChanged.connect(self.comboFilterChanged)

        self.comboFilter.addItem(_('All'), snapshotlog.LogFilter.NO_FILTER)

        # Note about ngettext plural forms: n=102 means "Other" in Arabic and
        # "Few" in Polish.
        # Research in translation community indicate this as the best fit to
        # the meaning of "all".
        self.comboFilter.addItem(' + '.join((_('Errors'), _('Changes'))), snapshotlog.LogFilter.ERROR_AND_CHANGES)
        self.comboFilter.setCurrentIndex(self.comboFilter.count() - 1)
        self.comboFilter.addItem(_('Errors'), snapshotlog.LogFilter.ERROR)
        self.comboFilter.addItem(_('Changes'), snapshotlog.LogFilter.CHANGES)
        self.comboFilter.addItem(ngettext('Information', 'Information', 2),
                                 snapshotlog.LogFilter.INFORMATION)
        self.comboFilter.addItem(_('rsync transfer failures (experimental)'), snapshotlog.LogFilter.RSYNC_TRANSFER_FAILURES)

        # text view
        self.txtLogView = QPlainTextEdit(self)
        self.txtLogView.setFont(QFont('Monospace'))
        self.txtLogView.setReadOnly(True)
        self.txtLogView.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.mainLayout.addWidget(self.txtLogView)

        #
        self.mainLayout.addWidget(
            QLabel(_('[E] Error, [I] Information, [C] Change')))

        # decode path
        self.cbDecode = QCheckBox(_('decode paths'), self)
        self.cbDecode.stateChanged.connect(self.cbDecodeChanged)
        self.mainLayout.addWidget(self.cbDecode)

        # buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.mainLayout.addWidget(buttonBox)
        buttonBox.rejected.connect(self.close)

        self.updateSnapshots()
        self.updateDecode()
        self.updateProfiles()

        # watch for changes in log file
        self.watcher = QFileSystemWatcher(self)
        if self.sid is None:
            # only watch if we show the last log
            log = self.config.takeSnapshotLogFile(
                self.comboProfiles.currentProfileID())
            self.watcher.addPath(log)
        # passes the path to the changed file to updateLog()
        self.watcher.fileChanged.connect(self.updateLog)

    def cbDecodeChanged(self):
        if self.cbDecode.isChecked():
            if not self.decode:
                self.decode = encfstools.Decode(self.config)

        else:
            if self.decode is not None:
                self.decode.close()
            self.decode = None

        self.updateLog()

    def profileChanged(self, index):
        if not self.enableUpdate:
            return
        profile_id = self.comboProfiles.currentProfileID()
        self.mainWindow.comboProfiles.setCurrentProfileID(profile_id)
        self.mainWindow.comboProfileChanged(None)

        self.updateDecode()
        self.updateLog()

    def comboSnapshotsChanged(self, index):
        if not self.enableUpdate:
            return
        self.sid = self.comboSnapshots.currentSnapshotID()
        self.updateLog()

    def comboFilterChanged(self, index):
        self.updateLog()

    def updateProfiles(self):
        current_profile_id = self.config.currentProfile()

        self.comboProfiles.clear()

        profiles = self.config.profilesSortedByName()
        for profile_id in profiles:
            self.comboProfiles.addProfileID(profile_id)
            if profile_id == current_profile_id:
                self.comboProfiles.setCurrentProfileID(profile_id)

        self.enableUpdate = True
        self.updateLog()

        if len(profiles) <= 1:
            self.lblProfile.setVisible(False)
            self.comboProfiles.setVisible(False)

    def updateSnapshots(self):
        if self.sid:
            self.comboSnapshots.clear()
            for sid in snapshots.iterSnapshots(self.config):
                self.comboSnapshots.addSnapshotID(sid)
                if sid == self.sid:
                    self.comboSnapshots.setCurrentSnapshotID(sid)

    def updateDecode(self):
        if self.config.snapshotsMode() == 'ssh_encfs':
            self.cbDecode.show()
        else:
            self.cbDecode.hide()
            if self.cbDecode.isChecked():
                self.cbDecode.setChecked(False)

    def updateLog(self, watchPath=None):
        """
        Show the log file of the current snapshot in the GUI

        Args:
            watchPath: FQN to a log file (as string) whose changes are watched
                       via ``QFileSystemWatcher``. In case of changes
                       this function is called with the log file
                       and only the new lines in the log file are appended
                       to the log file widget in the GUI
                       Use ``None`` if a complete log file shall be shown
                       at once.
        """
        if not self.enableUpdate:
            return

        mode = self.comboFilter.itemData(self.comboFilter.currentIndex())

        # TODO This expressions is hard to understand (watchPath is not a boolean!)
        if watchPath and self.sid is None:
            # remove path from watch to prevent multiple updates at the same time
            self.watcher.removePath(watchPath)
            # append only new lines to txtLogView
            log = snapshotlog.SnapshotLog(self.config, self.comboProfiles.currentProfileID())
            for line in log.get(mode = mode,
                                decode = self.decode,
                                skipLines = self.txtLogView.document().lineCount() - 1):
                self.txtLogView.appendPlainText(line)

            # re-add path to watch after 5sec delay
            alarm = tools.Alarm(callback = lambda: self.watcher.addPath(watchPath),
                                overwrite = False)
            alarm.start(5)

        elif self.sid is None:
            log = snapshotlog.SnapshotLog(self.config, self.comboProfiles.currentProfileID())
            self.txtLogView.setPlainText('\n'.join(log.get(mode = mode, decode = self.decode)))
        else:
            self.txtLogView.setPlainText('\n'.join(self.sid.log(mode, decode = self.decode)))

    def closeEvent(self, event):
        self.config.setIntValue('qt.logview.width', self.width())
        self.config.setIntValue('qt.logview.height', self.height())
        event.accept()
