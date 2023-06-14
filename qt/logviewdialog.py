#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import qttools
import snapshots
import encfstools
import snapshotlog
import tools
import messagebox

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

        #profiles
        self.lblProfile = QLabel(_('Profile:'), self)
        layout.addWidget(self.lblProfile)

        self.comboProfiles = qttools.ProfileCombo(self)
        layout.addWidget(self.comboProfiles, 1)
        self.comboProfiles.currentIndexChanged.connect(self.profileChanged)

        #snapshots
        self.lblSnapshots = QLabel(_('Snapshots') + ':', self)
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

        self.txtLogView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.txtLogView.customContextMenuRequested.connect(self.contextMenuClicked)

    def cbDecodeChanged(self):
        if self.cbDecode.isChecked():
            if not self.decode:
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

    def contextMenuClicked(self, point):
        menu = QMenu()
        clipboard = qttools.createQApplication().clipboard()
        cursor = self.txtLogView.textCursor()

        btnCopy = menu.addAction(_('Copy'))
        btnCopy.triggered.connect(lambda: clipboard.setText(cursor.selectedText()))
        btnCopy.setEnabled(cursor.hasSelection())

        btnAddExclude = menu.addAction(_('Add to Exclude'))
        btnAddExclude.triggered.connect(self.btnAddExcludeClicked)
        btnAddExclude.setEnabled(cursor.hasSelection())

        btnDecode = menu.addAction(_('Decode'))
        btnDecode.triggered.connect(self.btnDecodeClicked)
        btnDecode.setEnabled(cursor.hasSelection())
        btnDecode.setVisible(self.config.snapshotsMode() == 'ssh_encfs')

        menu.exec_(self.txtLogView.mapToGlobal(point))

    def btnAddExcludeClicked(self):
        exclude = self.config.exclude()
        path = self.txtLogView.textCursor().selectedText().strip()
        if not path or path in exclude:
            return
        edit = QLineEdit(self)
        edit.setText(path)
        edit.setMinimumWidth(600)
        options = {'widget': edit, 'retFunc': edit.text, 'id': 'path'}
        confirm, opt = messagebox.warningYesNoOptions(self, _("Do you want to exclude this?"), (options, ))
        if not confirm:
            return
        exclude.append(opt['path'])
        self.config.setExclude(exclude)

    def btnDecodeClicked(self):
        if not self.decode:
            self.decode = encfstools.Decode(self.config)
        cursor = self.txtLogView.textCursor()
        selection = cursor.selectedText().strip()
        plain = self.decode.path(selection)
        cursor.insertText(plain)

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
        self.config.setIntValue('qt.logview.width', self.width())
        self.config.setIntValue('qt.logview.height', self.height())
        event.accept()
