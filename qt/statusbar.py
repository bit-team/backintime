# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""A modul offering a status bar widget
"""
from PyQt6.QtWidgets import (QHBoxLayout,
                             QLabel,
                             QMainWindow,
                             QProgressBar,
                             QSizePolicy,
                             QStatusBar,
                             QWidget,
                             )
from PyQt6.QtCore import QEvent

_PROGRESS_BAR_WIDTH_FX = 10


class StatusBar(QStatusBar):
    """A status bar widget"""

    def __init__(self, main_window: QMainWindow):
        super().__init__(parent=main_window)

        self.main_window = main_window

        # self._foo = QLabel('foobar')
        # self._foo.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken) #

        # A container widget give us more control about layout details
        container = QWidget(self)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)

        # Status text
        self._status = QLabel(container)
        self._status.setWordWrap(False)
        self._status.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # # DEBUG
        # self._status.setStyleSheet("background-color: yellow; color: black;")

        # Progress bar
        self._progress = QProgressBar(container)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        self._progress.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        # Layout
        # layout.addWidget(self._foo)
        layout.addWidget(self._status, stretch=_PROGRESS_BAR_WIDTH_FX-1)
        layout.addStretch(0)
        layout.addWidget(self._progress, stretch=1)
        self.addPermanentWidget(container, 1)
        container.resizeEvent = self._on_resize

        # self._foo.setVisible(False)

    def _on_resize(self, event: QEvent) -> None:
        """Set the status label with in pixels, but relative.

        The width is a fraction of the statusbar full width, considering the
        width of the progressbar, which is also defined by a fraction.
        """
        width = self._status.parentWidget().width()
        width = width * (1 - (1 / _PROGRESS_BAR_WIDTH_FX))
        self._status.setMaximumWidth(int(width))
        event.accept()

    def set_status_message(self, message: str) -> None:
        """Set status label text."""
        self._status.setText(message)

    def progress_show(self, show: bool = True) -> None:
        """Set progress bar widget visible."""
        self._progress.setVisible(show)

    def progress_hide(self) -> None:
        """Set progress bar widget unvisible."""
        self.progress_show(show=False)

    def set_progress_value(self, val: int) -> None:
        """Set numeric value of progress bar."""
        self._progress.setValue(val)
