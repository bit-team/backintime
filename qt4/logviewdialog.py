#    Back In Time
#    Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import gettext

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import qt4tools
import snapshots
import encfstools
import snapshotlog
import tools

_=gettext.gettext


class LogViewDialog(QDialog):
    def __init__(self, parent, sid = None, systray = False):
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

        w = self.config.intValue('qt4.logview.width', 800)
        h = self.config.intValue('qt4.logview.height', 500)
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

        #profiles
        self.lblProfile = QLabel(_('Profile:'), self)
        layout.addWidget(self.lblProfile)

        self.comboProfiles = qt4tools.ProfileCombo(self)
        layout.addWidget(self.comboProfiles, 1)
        self.comboProfiles.currentIndexChanged.connect(self.profileChanged)

        #snapshots
        self.lblSnapshots = QLabel(_('Snapshots') + ':', self)
        layout.addWidget(self.lblSnapshots)
        self.comboSnapshots = qt4tools.SnapshotCombo(self)
        layout.addWidget(self.comboSnapshots, 1)
        self.comboSnapshots.currentIndexChanged.connect(self.comboSnapshotsChanged)

        if self.sid is None:
            self.lblSnapshots.hide()
            self.comboSnapshots.hide()
        if self.sid or systray:
            self.lblProfile.hide()
            self.comboProfiles.hide()

        #filter
        layout.addWidget(QLabel(_('Filter:')))

        self.comboFilter = QComboBox(self)
        layout.addWidget(self.comboFilter, 1)
        self.comboFilter.currentIndexChanged.connect(self.comboFilterChanged)

        self.comboFilter.addItem(_('All'), 0)
        self.comboFilter.addItem(' + '.join((_('Errors'), _('Changes'))), 4)
        self.comboFilter.setCurrentIndex(self.comboFilter.count() - 1)
        self.comboFilter.addItem(_('Errors'), 1)
        self.comboFilter.addItem(_('Changes'), 2)
        self.comboFilter.addItem(_('Informations'), 3)

        #text view
        self.txtLogView = QPlainTextEdit(self)
        self.txtLogView.setFont(QFont('Monospace'))
        self.txtLogView.setReadOnly(True)
        self.txtLogView.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.mainLayout.addWidget(self.txtLogView)

        #
        self.mainLayout.addWidget(QLabel(_('[E] Error, [I] Information, [C] Change')))

        #decode path
        self.cbDecode = QCheckBox(_('decode paths'), self)
        self.cbDecode.stateChanged.connect(self.cbDecodeChanged)
        self.mainLayout.addWidget(self.cbDecode)

        #buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        self.mainLayout.addWidget(buttonBox)
        buttonBox.rejected.connect(self.close)

        self.updateSnapshots()
        self.updateDecode()
        self.updateProfiles()

        # watch for changes in log file
        self.watcher = QFileSystemWatcher(self)
        if self.sid is None:
            # only watch if we show the last log
            log = self.config.takeSnapshotLogFile(self.comboProfiles.currentProfileID())
            self.watcher.addPath(log)
        self.watcher.fileChanged.connect(self.updateLog)

    def cbDecodeChanged(self):
        if self.cbDecode.isChecked():
            self.decode = encfstools.Decode(self.config)
        else:
            if not self.decode is None:
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

    def updateLog(self, watchPath = None):
        if not self.enableUpdate:
            return

        mode = self.comboFilter.itemData(self.comboFilter.currentIndex())

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
        self.config.setIntValue('qt4.logview.width', self.width())
        self.config.setIntValue('qt4.logview.height', self.height())
        event.accept()
