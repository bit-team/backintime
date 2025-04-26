# SPDX-FileCopyrightText: © 2025 Huaide Jiang
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.

from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout
from PyQt6.QtCore import QTimer
import os

def show_shutdown_warning(countdown=30):
    """
    Show a warning window with 30 seconds countdown
    """
    if not os.environ.get('DISPLAY'):
        return True  # No GUI

    app = QApplication.instance()
    if not app:
        app = QApplication([])

    class ShutdownWarningDialog(QDialog):
        def __init__(self, countdown):
            super().__init__()
            self.countdown = countdown
            self.initUI()
            self.startCountdown()

        def initUI(self):
            self.setWindowTitle("Back In Time - Shutdown Warning")
            self.setFixedSize(300, 150)
            self.label = QLabel(f"System will shutdown in {self.countdown} seconds", self)
            self.cancel_button = QPushButton("cancel shutdown", self)
            self.cancel_button.clicked.connect(self.cancelShutdown)
            layout = QVBoxLayout()
            layout.addWidget(self.label)
            layout.addWidget(self.cancel_button)
            self.setLayout(layout)

        def startCountdown(self):
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.updateCountdown)
            self.timer.start(1000)

        def updateCountdown(self):
            self.countdown -= 1
            self.label.setText(f"System will shutdown in {self.countdown} seconds")
            if self.countdown <= 0:
                self.timer.stop()
                self.accept()

        def cancelShutdown(self):
            self.timer.stop()
            self.reject()

    dialog = ShutdownWarningDialog(countdown)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted