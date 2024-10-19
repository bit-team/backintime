# SPDX-FileCopyrightText: © 2023 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module about UserMessageDialog"""
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (QDialog,
                             QLayout,
                             QVBoxLayout,
                             QDialogButtonBox,
                             QLabel,
                             QToolTip,
                             QWidget)


class UserMessageDialog(QDialog):
    """Present a large messages to the users with extra features.

    Different from QMessageBox this dialog is intended to display large amount
    of text. The dialog is able to wrap the text while being resized.
    Hyperlinks in this text do display their URL as tooltip.

    HTML tags supported because of Qt rich text feature. Text between Newline
    characters ``\n`` will be converted into ``<p>`` paragraphs.

    """

    def __init__(self, parent: QWidget, title: str, full_label: str):
        super().__init__(parent)
        # screen_width = QApplication.primaryScreen().size().width()
        # min_width = 300 if screen_width <= 1080 else 450
        self.setMinimumWidth(400)

        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)

        # Wrap paragraphs in <p> tags.
        if '\n' in full_label:
            result = ''
            for t in full_label.split('\n'):
                result = f'{result}<p>{t}</p>'

        else:
            result = full_label

        widget = QLabel(result, self)
        widget.setWordWrap(True)
        widget.setOpenExternalLinks(True)
        widget.linkHovered.connect(self.slot_link_hovered)

        button = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(widget)
        layout.addWidget(button)

        self._fix_size()

    def _fix_size(self):
        """The dialog is resized so it fits the content of the QLabel.

        Credits: https://stackoverflow.com/a/77012305/4865723
        """
        best = QLayout.closestAcceptableSize(self, QSize(self.width(), 1))

        if self.height() < best.height():
            self.resize(best)

    def resizeEvent(self, event):  # pylint: disable=invalid-name
        """See `_fixSize()`  for details."""
        super().resizeEvent(event)

        if event.oldSize().width() != event.size().width():
            QTimer.singleShot(0, self._fix_size)

        elif event.spontaneous():
            self._fix_size()

    def slot_link_hovered(self, url):
        """Show URL in tooltip without anoing http-protocol prefixf."""
        QToolTip.showText(QCursor.pos(), url.replace('https://', ''))
