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
"""A module offering a status bar widget
"""
from PyQt6.QtWidgets import (QFrame,
                             QHBoxLayout,
                             QLabel,
                             QMainWindow,
                             QProgressBar,
                             QSizePolicy,
                             QStatusBar,
                             QWidget,
                             )
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QPalette, QColor
import bitbase

_DARK_MODE_THRESHOLD = 128
_PROGRESS_BAR_WIDTH_FX = 10


class StatusBar(QStatusBar):
    """A status bar widget"""

    def __init__(self, main_window: QMainWindow):
        super().__init__(parent=main_window)

        self.main_window = main_window

        # Root mode indicator
        self._root = self._root_mode_indicator()

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

        # Progress bar
        self._progress = QProgressBar(container)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)

        # Layout
        if self._root:
            layout.addWidget(self._root)
        layout.addWidget(self._status, stretch=_PROGRESS_BAR_WIDTH_FX-1)
        layout.addStretch(0)
        layout.addWidget(self._progress, stretch=1)
        self.addPermanentWidget(container, 1)
        container.resizeEvent = self._on_resize

    def _on_resize(self, event: QEvent) -> None:
        """Set the status label with in pixels, but relative.

        The width is a fraction of the statusbar full width, considering the
        width of the progressbar, which is also defined by a fraction.
        """
        width = self._status.parentWidget().width()
        width = width * (1 - (1 / _PROGRESS_BAR_WIDTH_FX))
        self._status.setMaximumWidth(int(width))
        event.accept()

    def _root_mode_indicator(self) -> QLabel:
        if not bitbase.IS_IN_ROOT_MODE:
            return None

        root = QLabel(_('Root mode'))
        root.setToolTip(_(
            'Back In Time is currently running with root '
            'privileges (full system access)'))
        root.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)

        font = root.font()
        font.setBold(True)
        root.setFont(font)

        palette = root.palette()
        is_dark_mode = palette.color(
            QPalette.ColorRole.Window).value() < _DARK_MODE_THRESHOLD

        if is_dark_mode:
            # dark red & white
            bg_color = '#aa0000'
            text_color = '#ffffff'
        else:
            # light pink & dark red
            bg_color = '#ffdddd'
            text_color = '#aa0000'

        palette.setColor(QPalette.ColorRole.Window, QColor(bg_color))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(text_color))

        root.setAutoFillBackground(True)
        root.setPalette(palette)

        return root

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
