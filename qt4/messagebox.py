#    Copyright (C) 2012-2014 Germar Reitze
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

import sys
import gettext
from PyQt4.QtCore import QTimer, SIGNAL
from PyQt4.QtGui import QApplication, QMessageBox, QInputDialog, QLineEdit

_ = gettext.gettext

def ask_password_dialog(parent, title, prompt, timeout = None):
    if parent is None:
        qapp = QApplication(sys.argv)

    import icon
    dialog = QInputDialog()

    timer = QTimer()
    if not timeout is None:
        dialog.connect(timer, SIGNAL("timeout()"), dialog.reject)
        timer.setInterval(timeout * 1000)
        timer.start()

    dialog.setWindowIcon(icon.BIT_LOGO)
    dialog.setWindowTitle(title)
    dialog.setLabelText(prompt)
    dialog.setTextEchoMode(QLineEdit.Password)
    QApplication.processEvents()

    ret = dialog.exec_()

    timer.stop()
    if ret:
        password = dialog.textValue()
    else:
        password = ''
    del(dialog)

    if parent is None:
        qapp.exit(0)
    return(password)

def critical(parent, msg):
    return QMessageBox.critical(parent, _('Error'),
                                msg,
                                buttons = QMessageBox.Ok,
                                defaultButton = QMessageBox.Ok )

def warningYesNo(parent, msg):
    return QMessageBox.question(parent, _('Question'), msg,
                                buttons = QMessageBox.Yes | QMessageBox.No,
                                defaultButton = QMessageBox.No )
