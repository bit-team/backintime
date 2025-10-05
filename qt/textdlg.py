# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""A dialog containing a QTextBrowser"""
from PyQt6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout
from PyQt6.QtGui import QGuiApplication, QFontDatabase, QIcon
from PyQt6.QtCore import QTimer


class TextDialog(QDialog):
    """A dialog containing a QTextBrowser capable of markdown and plain text
    """

    def __init__(self,
                 content: str,
                 markdown: bool = True,
                 title: str = '',
                 icon: QIcon = None):
        super().__init__()
        self.setWindowTitle(title)

        if icon:
            self.setWindowIcon(icon)

        browser = QTextBrowser()
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        browser.setFont(font)

        layout = QVBoxLayout(self)
        layout.addWidget(browser)

        if markdown:
            browser.setMarkdown(content)
        else:
            browser.setPlainText(content)

        # See _resize_to_full_height() for details.
        self._resize_tries = 10
        QTimer.singleShot(1, lambda: self._center_and_resize(0.5, 0.75))

    def _center_and_resize(self,
                           width_fraction: float,
                           height_fraction: float) -> None:
        """Center the dialog and resize it to fractions of the screen size.

        Args:
            width_fraction: Fraction of screen width (0.0 to 1.0)
            height_fraction: Fraction of screen height (0.0 to 1.0)
        """
        screen = QGuiApplication.screenAt(self.pos())
        geom = screen.availableGeometry()

        # Determine the height of the dialog's title bar and border. This
        # value is unknown or incorrect until the dialg is fully drawn.
        # That is the reason why we use this workaround.
        deco_height = self.frameGeometry().height() - self.geometry().height()
        if deco_height == 0 and self._resize_tries > 0:
            self._resize_tries -= 1
            QTimer.singleShot(
                1,
                lambda: self._center_and_resize(
                    width_fraction, height_fraction)
            )
            return

        new_width = int(geom.width() * width_fraction)
        new_height = int((geom.height() - deco_height) * height_fraction)

        self.move(
            # center horizontal
            geom.center().x() - (new_width // 2),
            # center vertical
            geom.center().y() - (new_height // 2)
        )
        self.resize(
            # desired width
            new_width,
            # desired height (incl. window decoration) on available screen
            new_height)
