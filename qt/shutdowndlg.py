# SPDX-FileCopyrightText: © 2025 Huaide Jiang
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
""" Module about showing a warning dialog before shutting down """
import os
from PyQt6.QtWidgets import (QApplication,
                             QDialog,
                             QLabel,
                             QPushButton,
                             QVBoxLayout)
from PyQt6.QtCore import QTimer


class ShutdownWarningDialog(QDialog):
    """A UI class for a shutting down window."""
    def __init__(self, countdown):
        super().__init__()
        self.countdown = countdown

        # Initialize UI components
        self.setWindowTitle("Back In Time - Shutdown Warning")
        self.setFixedSize(300, 150)
        self.label = QLabel(f"Shutdown in {self.countdown}s", self)
        self.cancel_button = QPushButton("Cancel Shutdown", self)
        self.cancel_button.clicked.connect(self.cancel_shutdown)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)

        # Initialize timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)

    def update_countdown(self):
        """Update the countdown in the UI."""
        self.countdown -= 1
        self.label.setText(f"Shutdown in {self.countdown}s")
        if self.countdown <= 0:
            self.timer.stop()
            self.accept()

    def cancel_shutdown(self):
        """Cancel the shutdown process."""
        self.timer.stop()
        self.reject()


def show_shutdown_warning(countdown=30):
    """
    Show a warning window with 30 seconds countdown
    """
    if not os.environ.get('DISPLAY'):
        return True  # No GUI

    app = QApplication.instance()
    if not app:
        app = QApplication([])

    dialog = ShutdownWarningDialog(countdown)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted
