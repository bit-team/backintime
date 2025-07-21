# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2025 Samuel Moore
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Split from app.py
"""Module offering the Places widget in the main window.
"""
import os
import pathlib
from PyQt6.QtWidgets import (
                             QAbstractItemView,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QWidget
                             )
from PyQt6.QtGui import QFont, QIcon, QPalette
from PyQt6.QtCore import Qt
import bitbase
import config


class PlacesWidget(QTreeWidget):
    """A tree widget used in the main window.

    It contain the file system root and current users home directory as entry
    points. It also contain all included backup directories as entries.
    """

    def __init__(self, parent: QWidget, cfg: config.Config):
        QTreeWidget.__init__(self, parent=parent)

        self.config = cfg
        self.parent = parent

        # Do not show controls for expanding and collapsing top-level items
        self.setRootIsDecorated(False)

        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.setHeaderLabel(_('Shortcuts'))

        self.header().setSectionsClickable(True)
        self.header().setSortIndicatorShown(True)
        self.header().setSectionHidden(1, True)

        self.header().sortIndicatorChanged.connect(self.do_update)
        self.currentItemChanged.connect(self._slot_changed)

    def do_update(self, _col: int = None, _order: Qt.SortOrder = None) -> None:
        """Update the places view"""
        self.clear()

        # name, path, icon
        self._add_place(_('Places'), '', '')
        self._add_place(_('File System'), '/', 'computer')

        fp_home = pathlib.Path.home()
        self._add_place(
            # Use full path in root mode ("/root") otherwise users name only
            str(fp_home) if bitbase.IS_IN_ROOT_MODE else fp_home.name,
            str(fp_home),
            'user-home')

        # "Now" or a specific snapshot selected?
        if self.parent.sid.isRoot:
            # Use snapshots profiles list of include files and folders
            include_entries = self.config.include()

        else:
            # Determine folders from the snapshot itself
            base = os.path.expanduser('~')
            if not os.path.isdir(self.parent.sid.pathBackup(base)):
                # Folder not mounted. We can skip for the next updatePlaces()
                return

            folders = [
                i.name
                for i
                in os.scandir(self.parent.sid.pathBackup(base))
                if i.is_dir()
            ]

            include_entries = [(os.path.join(base, f), 0) for f in folders]

        # Use folders only (if 2nd tuple entry is 0)
        only_folders = filter(lambda entry: entry[1] == 0, include_entries)
        include_folders = [item[0] for item in only_folders]

        if not include_folders:
            return

        if not self.header().sortIndicatorSection():
            indic = self.header().sortIndicatorOrder()
            reverse = indic == Qt.SortOrder.DescendingOrder
            include_folders = sorted(include_folders, reverse=reverse)

        self._add_place(_('Backup directories'), '', '')

        for folder in include_folders:
            self._add_place(folder, folder, 'document-save')

    def _add_place(self, name, path, icon):
        """
        Dev note (buhtz, 2024-01-14): Parts of that code are redundant with
        timeline.py::HeaderItem.__init__().
        """
        item = QTreeWidgetItem()

        item.setText(0, name)

        if icon:
            item.setIcon(0, QIcon.fromTheme(icon))

        item.setData(0, Qt.ItemDataRole.UserRole, path)

        if not path:
            font = item.font(0)
            font.setWeight(QFont.Weight.Bold)
            item.setFont(0, font)

            # item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(
                0, self.palette().color(QPalette.ColorRole.PlaceholderText))
            item.setBackground(
                0, self.palette().color(QPalette.ColorRole.Window))

        self.addTopLevelItem(item)

        if path == self.parent.path:
            self.setCurrentItem(item)

        return item

    def _slot_changed(self, item, _previous):
        if item is None:
            return

        path = str(item.data(0, Qt.ItemDataRole.UserRole))
        if not path:
            return

        if path == self.parent.path:
            return

        # ???
        self.parent.path = path
        self.parent.path_history.append(path)

        self.parent.updateFilesView(3)

    def get_sorting(self) -> tuple[int, int]:
        """Current sorting column and order as a tuple."""
        return (
            self.header().sortIndicatorSection(),
            self.header().sortIndicatorOrder().value
        )

    def set_sorting(self, sorting: tuple[int, int]) -> None:
        """Set sorting."""
        self.header().setSortIndicator(sorting[0], Qt.SortOrder(sorting[1]))
