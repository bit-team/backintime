# SPDX-FileCopyrightText: © 2016 Germar Reitze
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
# File split from qttools.py.
"""Improved file dialog"""
from pathlib import Path
from PyQt6.QtGui import QShortcut
from PyQt6.QtCore import QDir
from PyQt6.QtWidgets import (QAbstractItemView,
                             QDialog,
                             QFileDialog,
                             QListView,
                             QTreeView,
                             QToolButton,
                             QWidget)


class FileDialog(QFileDialog):
    """Flexible non-native File dialog able to handle hidden files.

    It is a non-native dialog. An extra toggle button for hidden files is added
    including a shortcut Ctrl+H.
    """

    # PyLint bug: https://github.com/pylint-dev/pylint/issues/8675
    # pylint: disable-next=too-many-positional-arguments,too-many-arguments
    def __init__(self,  # noqa: PLR0913
                 parent: QWidget,
                 title: str,
                 show_hidden: bool = True,
                 allow_multiselection: bool = True,
                 dirs_only: bool = False,
                 start_dir: Path = None):
        super().__init__(
            parent=parent,
            caption=title,
            directory=str(start_dir) if start_dir else str(Path.cwd())
        )

        # Qt own dialog
        self.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        self._add_button_show_hidden()

        # Hidden files/dirs?
        if not show_hidden:
            self._slot_toggle_button_show_hidden()

        # setup behavior: single/multiple dirs/files
        if dirs_only:

            # Directories
            self.setOption(self.Option.ShowDirsOnly, dirs_only)
            self.setFileMode(self.FileMode.Directory)
            if allow_multiselection:
                # Workaround for selecting multiple directories adopted from
                # http://www.qtcentre.org/threads/
                # 34226-QFileDialog-select-multiple-directories?
                # p=158482#post158482
                for cls in (QListView, QTreeView):
                    self.findChildren(cls)[0].setSelectionMode(
                        QAbstractItemView.SelectionMode.ExtendedSelection)

        else:
            self.setFileMode(
                # Multiple files
                self.FileMode.ExistingFiles if allow_multiselection
                # Single files
                else self.FileMode.ExistingFile
            )

    def _add_button_show_hidden(self):
        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415
        grid = self.layout()  # dialogs main layout
        hbox = grid.itemAt(1)  # layout with the toolbar buttons

        btn = QToolButton(self)
        btn.setIcon(icon.SHOW_HIDDEN)
        btn.setToolTip(_('Show/hide hidden files and directories (Ctrl+H)'))
        btn.setCheckable(True)

        hbox.insertWidget(3, btn)

        btn.toggled.connect(self._slot_toggled_show_hidden)

        shortcut = QShortcut('Ctrl+H', self)
        shortcut.activated.connect(btn.toggle)

        # Sync button and filter: Show hidden by default
        self.setFilter(self.filter() | QDir.Filter.Hidden)
        btn.setChecked(True)

    def _slot_toggled_show_hidden(self, _enable: bool = None):
        # toggle the filter
        self.setFilter(self.filter() ^ QDir.Filter.Hidden)

    def result(self) -> str | list[str] | None:
        """Show the dialog and return the result.

        Returns:
            One name or list of names.  ``None`` in case the dialog was
            canceled.
        """
        if self.exec() != QDialog.DialogCode.Accepted:
            return None

        result = self.selectedFiles()

        return result[0] if len(result) == 1 else result
