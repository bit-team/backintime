#    Copyright (C) 2012-2022 Germar Reitze
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

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication, QMessageBox, QInputDialog, QLineEdit,\
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QScrollArea
import qttools


def askPasswordDialog(parent, title, prompt, language_code, timeout):
    if parent is None:
        app = qttools.createQApplication()
        translator = qttools.initiate_translator(language_code)
        app.installTranslator(translator)

    import icon
    dialog = QInputDialog()

    timer = QTimer()
    if not timeout is None:
        timer.timeout.connect(dialog.reject)
        timer.setInterval(timeout * 1000)
        timer.start()

    dialog.setWindowIcon(icon.BIT_LOGO)
    dialog.setWindowTitle(title)
    dialog.setLabelText(prompt)
    dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
    QApplication.processEvents()

    ret = dialog.exec()

    timer.stop()
    if ret:
        password = dialog.textValue()
    else:
        password = ''
    del dialog

    return password


def info(text, title=None, widget_to_center_on=None):
    """Show a modal information message box.

    The message box is centered on the primary screen if
    ``widget_to_center_on`` is not given.

    Args:
        text(str): The information text central to the dialog.
        title(str): Title of the message box dialog.
        widget_to_center_on(QWidget): Center the message box on that widget.
    """
    QMessageBox.information(
        widget_to_center_on,
        title if title else ngettext('Information', 'Information', 1),
        text)


def warning(text, title=None, widget_to_center_on=None):
    """Show a modal warning message box.

    The message box is centered on the primary screen if
    ``widget_to_center_on`` is not given.

    Args:
        text(str): The warning message central to the dialog.
        title(str): Title of the message box dialog.
        widget_to_center_on(QWidget): Center the message box on that widget.
    """
    QMessageBox.warning(
        widget_to_center_on,
        title if title else _('Warning'),
        text)


def critical(parent, msg):
    return QMessageBox.critical(
        parent,
        _('Error'),
        msg,
        buttons=QMessageBox.StandardButton.Ok,
        defaultButton=QMessageBox.StandardButton.Ok)


def warningYesNo(parent, msg):
    return QMessageBox.question(
        parent,
        _('Question'),
        msg,
        buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        defaultButton=QMessageBox.StandardButton.No)


def warningYesNoOptions(parent, msg, options = ()):

    # Create a dialog
    dlg = QDialog(parent)
    dlg.setWindowTitle(_('Question'))
    layout = QVBoxLayout()
    dlg.setLayout(layout)

    # Initial message
    label = QLabel(msg)
    layout.addWidget(label)

    # Add optional elements
    for opt in options:
        layout.addWidget(opt['widget'])

    # Button box
    buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No)
    buttonBox.button(QDialogButtonBox.StandardButton.No).setDefault(True)
    layout.addWidget(buttonBox)
    buttonBox.accepted.connect(dlg.accept)
    buttonBox.rejected.connect(dlg.reject)

    # Show and ask user for the answer
    ret = dlg.exec()

    return (
        ret,
        {
            opt['id']:opt['retFunc']()
            for opt in options
            if opt['retFunc'] is not None
        }
    )


def showInfo(parent, title, msg):
    """Show extended information dialog with framed and scrollable text area.

    Dev info (buhtz, 2024): That function is deprecated. Use `info()` instead.
    """
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    vlayout = QVBoxLayout(dlg)
    label = QLabel(msg)
    label.setTextInteractionFlags(
        Qt.TextInteractionFlag.LinksAccessibleByMouse)
    label.setOpenExternalLinks(True)

    scroll_area = QScrollArea()
    scroll_area.setWidget(label)

    buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    buttonBox.accepted.connect(dlg.accept)

    vlayout.addWidget(scroll_area)
    vlayout.addWidget(buttonBox)

    return dlg.exec()
