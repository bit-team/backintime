# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""A dialog containing a QTextBrowser"""
from PyQt6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout
from PyQt6.QtGui import (QFontDatabase,
                         QGuiApplication,
                         QIcon,
                         QTextCursor)
from PyQt6.QtCore import QRegularExpression, QTimer


class TextDialog(QDialog):
    """A dialog containing a QTextBrowser capable of markdown and plain text

    Dev note: Consider joining the center-resize-feature with
    RestoreConfigDialog.
    """
    # pylint: disable=too-few-public-methods
    DEFAULT_WIDTH_FRACTION = 0.5
    DEFAULT_HEIGHT_FRACTION = 0.75

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def __init__(self,  # noqa: PLR0913
                 content: str,
                 markdown: bool = False,
                 html: bool = False,
                 scroll_to: str = None,
                 title: str = '',
                 icon: QIcon = None,
                 width_fraction: float = DEFAULT_WIDTH_FRACTION,
                 height_fraction: float = DEFAULT_HEIGHT_FRACTION):
        """
        Args:
            width_fraction: Fraction of screen width (0.0 to 1.0)
            height_fraction: Fraction of screen height (0.0 to 1.0)
        """
        super().__init__()
        self.setWindowTitle(title)

        self._scroll_to_pattern = scroll_to
        self._markdown = markdown
        self._html = html
        self._resize_tries = -1
        self._height_fraction = height_fraction
        self._width_fraction = width_fraction

        if icon:
            self.setWindowIcon(icon)

        self._browser = QTextBrowser()
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self._browser.setFont(font)

        layout = QVBoxLayout(self)
        layout.addWidget(self._browser)

        self.set_content(content)

    @property
    def width_fraction(self) -> float:
        """Fraction of screen width"""
        return self._width_fraction

    @property
    def browser_widget(self) -> QTextBrowser:
        """The primary widget"""
        return self._browser

    def set_content(self, content: str):
        """Set content to the primary widget.
        """
        if self._markdown:
            self._browser.setMarkdown(content)
        elif self._html:
            self._browser.setHtml(content)
        else:
            self._browser.setPlainText(content)

        # See _resize_to_full_height() for details.
        self._resize_tries = 10
        QTimer.singleShot(1, self._center_and_resize)

    def _center_and_resize(self) -> None:
        """Center the dialog and resize it to fractions of the screen size.
        """
        # pylint: disable=duplicate-code

        # Determine the height of the dialog's title bar and border. This
        # value is unknown or incorrect until the dialg is fully drawn.
        # That is the reason why we use this workaround.
        deco_height = self.frameGeometry().height() - self.geometry().height()
        if deco_height == 0 and self._resize_tries > 0:
            self._resize_tries -= 1
            QTimer.singleShot(1, self._center_and_resize)
            return

        handle = self.windowHandle()
        screen = handle.screen() if handle else QGuiApplication.primaryScreen()
        geom = screen.availableGeometry()

        new_width = int(geom.width() * self._width_fraction)
        new_height = int((geom.height() - deco_height) * self._height_fraction)

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

        self._scroll_to()

    def _scroll_to(self):
        if self._scroll_to_pattern is None:
            return

        cursor = self._browser.document().find(
            QRegularExpression(self._scroll_to_pattern),
            QTextCursor()
        )

        if cursor.isNull():
            return

        # Sets the cursor to the text position.
        self._browser.setTextCursor(cursor)
        # Scroll until the selected text is visible.
        self._browser.ensureCursorVisible()

        # The selected text appears at the end of the widget not at the top.
        # This adjusts the position accordingly via scrolling one page up.
        scrollbar = self._browser.verticalScrollBar()
        cursor_rect = self._browser.cursorRect(cursor)
        margin = 10
        new_value = scrollbar.value() + cursor_rect.top() - margin
        new_value = max(
            scrollbar.minimum(), min(scrollbar.maximum(), new_value))
        scrollbar.setValue(new_value)
