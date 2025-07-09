# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (QApplication,
                             QDialog,
                             QDialogButtonBox,
                             QInputDialog,
                             QLabel,
                             QLineEdit,
                             QMessageBox,
                             QVBoxLayout,
                             QWidget)
import qttools


def askPasswordDialog(parent, title, prompt, language_code, timeout):
    """Dev note (2025-07, buhtz): Replace with extern use of zenity, yat,
    kdialog

    e.g.
    zenity --entry --title="foo" --text="text" --hide-text
    yad --entry --title="foo" --text="text" --hide-text
    kdialog --password "enter password"
    """
    if parent is None:
        app = qttools.createQApplication()
        translator = qttools.initiate_translator(language_code)
        app.installTranslator(translator)

    import icon
    dialog = QInputDialog()

    timer = QTimer()

    if timeout is not None:
        timer.timeout.connect(dialog.reject)
        timer.setInterval(timeout * 1000)
        timer.start()

    dialog.setWindowIcon(icon.BIT_LOGO)
    dialog.setWindowTitle(title)
    dialog.setLabelText(prompt)
    dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
    QApplication.processEvents()

    result = dialog.exec()

    timer.stop()

    password = dialog.textValue() if result else ''

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


def warning(text: str,
            title: str = None,
            widget_to_center_on: QWidget = None,
            as_question: bool = False) -> bool | None:
    """Show a modal warning message box.

    The message box is centered on the primary screen if
    ``widget_to_center_on`` is not given.

    Args:
        text: The warning message central to the dialog.
        title: Title of the message box dialog (default: 'Warning').
        widget_to_center_on: Center the message box on that widget.
        as_question: Use Yes and No buttons.
    """
    buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No \
        if as_question else QMessageBox.StandardButton.Ok

    answer = QMessageBox.warning(
        widget_to_center_on,
        title if title else _('Warning'),
        text,
        buttons
    )

    return answer == QMessageBox.StandardButton.Yes


def question(text, title=None, widget_to_center_on=None) -> bool:
    """Show a modal question message box.

    The message box is centered on the primary screen if
    ``widget_to_center_on`` is not given.

    Args:
        text(str): The question central to the dialog.
        title(str): Title of the message box dialog (default: 'Question').
        widget_to_center_on(QWidget): Center the message box on that widget.

    Return:
        bool: ``True`` if the answer was "Yes", otherwise ``False``.
    """
    answer = QMessageBox.question(
        widget_to_center_on,
        title if title else _('Question'),
        text)

    return answer == QMessageBox.StandardButton.Yes


def critical(parent, msg):
    return QMessageBox.critical(
        parent,
        _('Error'),
        msg,
        buttons=QMessageBox.StandardButton.Ok,
        defaultButton=QMessageBox.StandardButton.Ok)


def warningYesNoOptions(parent, msg, options=()):

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
    buttonBox = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Yes
        | QDialogButtonBox.StandardButton.No)
    buttonBox.button(QDialogButtonBox.StandardButton.No).setDefault(True)
    layout.addWidget(buttonBox)
    buttonBox.accepted.connect(dlg.accept)
    buttonBox.rejected.connect(dlg.reject)

    # Show and ask user for the answer
    ret = dlg.exec()

    return (
        ret,
        {
            opt['id']: opt['retFunc']() for opt in options
            if opt['retFunc'] is not None
        }
    )
