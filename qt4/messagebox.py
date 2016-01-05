#    Copyright (C) 2012-2016 Germar Reitze
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
from PyQt4.QtCore import QTimer, SIGNAL, Qt
from PyQt4.QtGui import QApplication, QMessageBox, QInputDialog, QLineEdit,\
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QScrollArea
import qt4tools

_ = gettext.gettext

def ask_password_dialog(parent, title, prompt, timeout = None):
    if parent is None:
        qt4tools.create_qapplication()

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

def warningYesNoOptions(parent, msg, options = ()):
    dlg = QDialog(parent)
    dlg.setWindowTitle(_('Question'))
    layout = QVBoxLayout()
    dlg.setLayout(layout)
    label = QLabel(msg)
    layout.addWidget(label)

    for opt in options:
        layout.addWidget(opt['widget'])

    buttonBox = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
    buttonBox.button(QDialogButtonBox.No).setDefault(True)
    layout.addWidget(buttonBox)
    dlg.connect(buttonBox, SIGNAL('accepted()'), dlg.accept)
    dlg.connect(buttonBox, SIGNAL('rejected()'), dlg.reject)
    ret = dlg.exec_()
    return (ret, {opt['id']:opt['retFunc']() for opt in options})

def show_info(parent, title, msg):
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    vlayout = QVBoxLayout(dlg)
    label = QLabel(msg)
    label.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
    label.setOpenExternalLinks(True)

    scroll_area = QScrollArea()
    scroll_area.setWidget(label)

    button_box = QDialogButtonBox(QDialogButtonBox.Ok)
    dlg.connect(button_box, SIGNAL('accepted()'), dlg.accept)

    vlayout.addWidget(scroll_area)
    vlayout.addWidget(button_box)
    return dlg.exec_()
