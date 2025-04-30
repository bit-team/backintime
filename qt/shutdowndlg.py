# SPDX-FileCopyrightText: © 2025 Huaide Jiang
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module about showing a confirmation dialog before shutting down."""
import gettext
from PyQt6.QtWidgets import (QDialog,
                             QLabel,
                             QPushButton,
                             QVBoxLayout,
                             QHBoxLayout)
from PyQt6.QtCore import QTimer, Qt


class ConfirmShutdownDlg(QDialog):
    """A dialog ask for confirmation to shutdown the system and assuming
    confirmation after finish a countdown."""

    def __init__(self, countdown: int):
        super().__init__()
        self.countdown = countdown

        # Initialize UI components
        self.setWindowTitle(_('Countdown to Shutdown'))
        self.label1 = QLabel(_('The backup has finished.'), self)
        self.label2 = QLabel('', self)
        self._update_countdown()

        # Center the label texts
        self.label1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cancel_button = QPushButton(_('Cancel Shutdown'), self)
        self.shutdown_button = QPushButton(_('Shutdown Now'), self)
        self.cancel_button.clicked.connect(self._cancel_shutdown)

        # Immediately accept on shutdown now
        self.shutdown_button.clicked.connect(self.accept)

        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.label1, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.label2, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.shutdown_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initialize timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_countdown)
        self.timer.start(1000)

    def _update_countdown(self):
        self.countdown -= 1

        if self.countdown <= 0:
            self.timer.stop()
            self.accept()

        self.label2.setText(gettext.ngettext(
            'The system will shut down in {n} second.',
            'The system will shut down in {n} seconds.',
            self.countdown).format(n=self.countdown))

    def _cancel_shutdown(self):
        self.timer.stop()
        self.reject()


def get_shutdown_confirmation(countdown: int = 31) -> bool:
    """Ask user to confirm the shutdown while running a countdown.

    Args:
        countdown: Countdown in seconds.

    Returns:
        Confirm shutdown if user has not answered, or users answer.
    """
    dialog = ConfirmShutdownDlg(countdown)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted
