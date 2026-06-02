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
from inhibitsuspend import InhibitSuspend
import messagebox


class RestoreDialog(QDialog):
    """A dialog showing a live log of a restore process."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, parent, sid, what, where='', **kwargs):
        super().__init__(parent)
        self.resize(600, 500)

        self.config = parent.config
        self.snapshots = parent.snapshots
        self.sid = sid
        self.what = what
        self.where = where
        self.kwargs = kwargs

        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415

        self._log_file = Path(self.config.restoreLogFile())
        if self._log_file.exists():
            self._log_file.unlink()

        self.setWindowIcon(icon.RESTORE_DIALOG)
        self.setWindowTitle(_('Restore'))

        self._main_layout = QVBoxLayout(self)

        self._txt_log_view = QPlainTextEdit(self)
        self._txt_log_view.setReadOnly(True)
        self._txt_log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._txt_log_view.setMaximumBlockCount(100000)
        self._main_layout.addWidget(self._txt_log_view)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_show_log = button_box.addButton(
            _('Show full Log'), QDialogButtonBox.ButtonRole.ActionRole)
        self._main_layout.addWidget(button_box)
        self._btn_close = button_box.button(
            QDialogButtonBox.StandardButton.Close)
        self._btn_close.setEnabled(False)
        button_box.rejected.connect(self.close)
        btn_show_log.clicked.connect(self._slot_show_log)

        # restore in separate thread
        self.thread = RestoreThread(self)
        self.thread.finished.connect(self._slot_thread_finished)

        # refresh log every 200ms
        self._refesh_timer = QTimer(self)
        self._refesh_timer.setInterval(200)
        self._refesh_timer.setSingleShot(False)
        self._refesh_timer.timeout.connect(self._slot_refresh_log)

    def _slot_show_log(self):
        if not self._log_file.exists():
            messagebox.critical(
                self,
                f'Log file ("{self._log_file}") not found.')
            return

        QDesktopServices.openUrl(QUrl(str(self._log_file)))

    def _slot_refresh_log(self):
        """
        get new log from thread
        """
        new_log = self.thread.buffer[:]
        size = len(new_log)
        if size:
            self.thread.mutex.lock()
            self.thread.buffer = self.thread.buffer[size:]
            self.thread.mutex.unlock()
            self._txt_log_view.appendPlainText(new_log.rstrip('\n'))

    def exec(self):
        """Show dialog and run underlying threads"""
        self.show()
        self._refesh_timer.start()
        self.thread.start()
        super().exec()
        self._refesh_timer.stop()
        self.thread.wait()

    def _slot_thread_finished(self):
        self._btn_close.setEnabled(True)

    def closeEvent(self, event):
        """
        intercept close event to prevent cancelling restoration early
        this provides protection against upper corner x as well as
        alt-f4 key presses
        """
        # Check if close button is enabled to avoid using new variable
        # Could add a boolean to __init__ for easier readability
        if not self._btn_close.isEnabled():
            messagebox.critical(
                self,
                _("A critical process is currently running. Window "
                  "cannot be closed until restoration is finished.")
            )
            event.ignore()
        else:
            event.accept()

class RestoreThread(QThread):
    """
    run restore in a separate Thread to prevent GUI freeze and speed up restore
    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.log = parent._log_file.open('wt', encoding='utf-8')
        self.mutex = QMutex()
        self.buffer = ''

    def run(self):
        """Run the thread"""
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
