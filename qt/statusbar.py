# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""A module offering a status bar widget
"""
import os
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
import qttools

_PROGRESS_BAR_WIDTH_FX = 10
_UNIT_MULTIPLIER = 1024


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

        # Disk space info label
        self._disk_space = QLabel(container)
        self._disk_space.setWordWrap(False)
        self._disk_space.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        self._disk_space.setVisible(False)

        # Layout
        if self._root:
            layout.addWidget(self._root)
        layout.addWidget(self._status, stretch=_PROGRESS_BAR_WIDTH_FX-1)
        layout.addWidget(self._disk_space)
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

        if qttools.in_dark_mode(root):
            # dark red & white
            bg_color = '#aa0000'
            text_color = '#ffffff'
        else:
            # light pink & dark red
            bg_color = '#ffdddd'
            text_color = '#aa0000'

        palette = root.palette()
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

    def set_disk_space_info(self, path: str) -> None:
        """Set the backup disk space information."""
        if not path:
            self._disk_space.setVisible(False)
            return

        try:
            statvfs = os.statvfs(path)

            free = statvfs.f_frsize
            if bitbase.IS_IN_ROOT_MODE:
                free *= statvfs.f_bfree
            else:
                free *= statvfs.f_bavail

            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if free < _UNIT_MULTIPLIER:
                    break
                free /= _UNIT_MULTIPLIER

            formatted = f"{free:.1f} {unit}"
            self._disk_space.setText(_('Free space: ') + formatted)
            self._disk_space.setVisible(True)

        except OSError:
            self._disk_space.setVisible(False)

    def hide_disk_space_info(self) -> None:
        """Hide the disk space information."""
        self._disk_space.setVisible(False)
