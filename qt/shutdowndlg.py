# SPDX-FileCopyrightText: © 2025 Huaide Jiang
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
""" Module about showing a warning dialog before shutting down """
import gettext
from PyQt6.QtWidgets import (QDialog,
                             QLabel,
                             QPushButton,
                             QVBoxLayout,
                             QHBoxLayout)
from PyQt6.QtCore import QTimer, Qt


class ShutdownWarningDlg(QDialog):
    """A UI class for a shutting down window."""
    def __init__(self, countdown):
        super().__init__()
        self.countdown = countdown

        # Initialize UI components
        self.setWindowTitle(_('Countdown to Shutdown'))
        self.label = QLabel('', self)
        self.update_countdown()
        # Center the label text
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cancel_button = QPushButton(_('Cancel Shutdown'), self)
        self.shutdown_button = QPushButton(_('Shutdown Now'), self)
        self.cancel_button.clicked.connect(self.cancel_shutdown)
        # Immediately accept on shutdown now
        self.shutdown_button.clicked.connect(self.accept)

        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.shutdown_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initialize timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)

    def update_countdown(self):
        """Update the countdown in the UI."""
        self.countdown -= 1
        self.label.setText(gettext.ngettext(
            'Backup completed successfully.\n' +
            'The system will shut down in {n} second.',
            'Backup completed successfully.\n' +
            'The system will shut down in {n} seconds.',
            self.countdown).format(n=self.countdown))
        if self.countdown <= 0:
            self.timer.stop()
            self.accept()

    def cancel_shutdown(self):
        """Cancel the shutdown process."""
        self.timer.stop()
        self.reject()


def show_shutdown_warning(countdown=31):
    """
    Show a warning window with 30 seconds countdown
    """
    dialog = ShutdownWarningDlg(countdown)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted
