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
"""Module offering RestoreDialog"""
from pathlib import Path
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QDialog,
                             QDialogButtonBox,
                             QPlainTextEdit,
                             QVBoxLayout)
from PyQt6.QtCore import QMutex, QThread, QTimer, QUrl
import messagebox
from inhibitsuspend import InhibitSuspend


class RestoreDialog(QDialog):
    """A dialog showing a live log of a restore process."""

    def __init__(self, parent, sid, what, where='', **kwargs):
        super(RestoreDialog, self).__init__(parent)
        self.resize(600, 500)

        self.config = parent.config
        self.snapshots = parent.snapshots
        self.sid = sid
        self.what = what
        self.where = where
        self.kwargs = kwargs
        import icon

        self.logFile = Path(self.config.restoreLogFile())
        if self.logFile.exists():
            self.logFile.unlink()

        self.setWindowIcon(icon.RESTORE_DIALOG)
        self.setWindowTitle(_('Restore'))

        self.mainLayout = QVBoxLayout(self)

        self.txtLogView = QPlainTextEdit(self)
        self.txtLogView.setReadOnly(True)
        self.txtLogView.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.txtLogView.setMaximumBlockCount(100000)
        self.mainLayout.addWidget(self.txtLogView)

        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        showLog = buttonBox.addButton(
            _('Show full Log'), QDialogButtonBox.ButtonRole.ActionRole)
        self.mainLayout.addWidget(buttonBox)
        self.btnClose = buttonBox.button(QDialogButtonBox.StandardButton.Close)
        self.btnClose.setEnabled(False)
        buttonBox.rejected.connect(self.close)
        showLog.clicked.connect(self._slot_show_log)

        # restore in separate thread
        self.thread = RestoreThread(self)
        self.thread.finished.connect(self.threadFinished)

        # refresh log every 200ms
        self.refreshTimer = QTimer(self)
        self.refreshTimer.setInterval(200)
        self.refreshTimer.setSingleShot(False)
        self.refreshTimer.timeout.connect(self.refreshLog)

    def _slot_show_log(self):
        if not self.logFile.exists():
            messagebox.critical(
                self,
                f'Log file ("{self.logFile}") not found.')
            return

        QDesktopServices.openUrl(QUrl(str(self.logFile)))

    def refreshLog(self):
        """
        get new log from thread
        """
        newLog = self.thread.buffer[:]
        size = len(newLog)
        if size:
            self.thread.mutex.lock()
            self.thread.buffer = self.thread.buffer[size:]
            self.thread.mutex.unlock()
            self.txtLogView.appendPlainText(newLog.rstrip('\n'))

    def exec(self):
        self.show()
        self.refreshTimer.start()
        self.thread.start()
        super(RestoreDialog, self).exec()
        self.refreshTimer.stop()
        self.thread.wait()

    def threadFinished(self):
        self.btnClose.setEnabled(True)


class RestoreThread(QThread):
    """
    run restore in a separate Thread to prevent GUI freeze and speed up restore
    """

    def __init__(self, parent):
        super(RestoreThread, self).__init__()
        self.parent = parent
        self.log = parent.logFile.open('wt')
        self.mutex = QMutex()
        self.buffer = ''

    def run(self):
        with InhibitSuspend(reason='restoring'):
            self.parent.snapshots.restore(
                self.parent.sid,
                self.parent.what,
                self.callback,
                self.parent.where,
                **self.parent.kwargs)

        self.log.close()

    def callback(self, line, *_args):
        """
        write into log file and provide thread save string for log window
        """
        line += '\n'
        self.log.write(line)
        self.mutex.lock()
        self.buffer += line
        self.mutex.unlock()
