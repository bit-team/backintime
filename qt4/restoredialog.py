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


import os
import gettext

import tools

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import qt4tools


_=gettext.gettext


def restore( parent, snapshot_id, what, where = '', **kwargs ):
    if where is None:
        where = qt4tools.getExistingDirectory( parent, _('Restore to ...') )
        if not where:
            return
        where = parent.config.prepare_path( where )

    rd = RestoreDialog(parent, snapshot_id, what, where, **kwargs)
    rd.exec()

class RestoreDialog( QDialog ):
    def __init__( self, parent, snapshot_id, what, where = '', **kwargs ):
        super(RestoreDialog, self).__init__(parent)
        self.resize( 600, 500 )

        self.config = parent.config
        self.current_profile = self.config.get_current_profile()
        self.snapshots = parent.snapshots
        self.snapshot_id = snapshot_id
        self.what = what
        self.where = where
        self.kwargs = kwargs
        import icon

        self.log_file = self.config.get_restore_log_file()
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

        self.setWindowIcon(icon.RESTORE_DIALOG)
        self.setWindowTitle( _( 'Restore' ) )

        self.main_layout = QVBoxLayout(self)

        #text view
        self.txt_log_view = QPlainTextEdit(self)
        self.txt_log_view.setReadOnly(True)
        self.txt_log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.txt_log_view.setMaximumBlockCount(100000)
        self.main_layout.addWidget(self.txt_log_view)

        #buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        showLog = button_box.addButton(_('Show full Log'), QDialogButtonBox.ActionRole)
        self.main_layout.addWidget(button_box)
        self.btn_close = button_box.button(QDialogButtonBox.Close)
        self.btn_close.setEnabled(False)
        button_box.rejected.connect(self.close)
        showLog.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.log_file)))

        #restore in separate thread
        self.thread = RestoreThread(self)
        self.thread.finished.connect(self.threadFinished)

        #refresh log every 200ms
        self.refreshTimer = QTimer(self)
        self.refreshTimer.setInterval(200)
        self.refreshTimer.setSingleShot(False)
        self.refreshTimer.timeout.connect(self.refreshLog)

    def refreshLog(self):
        """get new log from thread
        """
        newLog = self.thread.buffer[:]
        size = len(newLog)
        if size:
            self.thread.mutex.lock()
            self.thread.buffer = self.thread.buffer[size:]
            self.thread.mutex.unlock()
            self.txt_log_view.appendPlainText(newLog.rstrip('\n'))

    def exec(self):
        #inhibit suspend/hibernate during restore
        self.config.inhibitCookie = tools.inhibitSuspend(toplevel_xid = self.config.xWindowId, reason = 'restoring')
        self.show()
        self.refreshTimer.start()
        self.thread.start()
        super(RestoreDialog, self).exec()
        self.refreshTimer.stop()
        self.thread.wait()

    def threadFinished(self):
        self.btn_close.setEnabled(True)
        #release inhibit suspend
        if self.config.inhibitCookie:
            self.config.inhibitCookie = tools.unInhibitSuspend(*self.config.inhibitCookie)

class RestoreThread(QThread):
    """run restore in a separate Thread to prevent GUI freeze and speed up restore
    """
    def __init__(self, parent):
        super(RestoreThread, self).__init__()
        self.parent = parent
        self.log = open(parent.log_file, 'wt')
        self.mutex = QMutex()
        self.buffer = ''

    def run(self):
        self.parent.snapshots.restore(self.parent.snapshot_id, self.parent.what, self.callback, self.parent.where, **self.parent.kwargs)
        self.log.close()

    def callback(self, line, *args):
        """write into log file and provide thread save string for log window
        """
        line += '\n'
        self.log.write(line)
        self.mutex.lock()
        self.buffer += line
        self.mutex.unlock()
