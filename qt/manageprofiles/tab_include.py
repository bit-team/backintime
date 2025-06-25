# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raak
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2025 Devin Black
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The IncludeTab class for managing include paths"""
import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget,
                             QVBoxLayout,
                             QHBoxLayout,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QPushButton,
                             QHeaderView,
                             QAbstractItemView)
import qttools
from qttools import custom_sort_order


class IncludeTab(QWidget):
    """Tab for managing include files and directories."""
    def __init__(self, parent):
        super().__init__(parent=parent)

        self._parent_dialog = parent
        self.icon = parent.icon
        self.config = parent.config

        layout = QVBoxLayout(self)

        self.list_include = QTreeWidget(self)
        self.list_include.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.list_include.setRootIsDecorated(False)
        self.list_include.setHeaderLabels([
            _('Include files and directories'), 'Count'
        ])
        self.list_include.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.list_include.header().setSectionsClickable(True)
        self.list_include.header().setSortIndicatorShown(True)
        self.list_include.header().setSectionHidden(1, True)
        layout.addWidget(self.list_include)

        self.list_include_count = 0
        self.list_include_sort_loop = False
        self.list_include.header().sortIndicatorChanged.connect(
            self.include_custom_sort_order
        )

        buttons_layout = QHBoxLayout()
        layout.addLayout(buttons_layout)

        self.btn_include_file = QPushButton(self.icon.ADD, _('Add files'), self)
        buttons_layout.addWidget(self.btn_include_file)
        self.btn_include_file.clicked.connect(self.btn_include_file_clicked)

        self.btn_include_add = QPushButton(
            self.icon.ADD, _('Add directories'), self
        )
        buttons_layout.addWidget(self.btn_include_add)
        self.btn_include_add.clicked.connect(self.btn_include_add_clicked)

        self.btn_include_remove = QPushButton(
            self.icon.REMOVE, _('Remove'), self
        )
        buttons_layout.addWidget(self.btn_include_remove)
        self.btn_include_remove.clicked.connect(
            self.btn_include_remove_clicked
        )

    def load_values(self,profile_state):

        self.list_include.clear()
        for include in self.config.include():
            self.add_include(include)

        try:
            incl_sort = profile_state.include_sorting
            self.list_include.sortItems(
                incl_sort[0], Qt.SortOrder(incl_sort[1])
            )
        except KeyError:
            pass

    def store_values(self, profile_state):
        profile_state.include_sorting = (
            self.list_include.header().sortIndicatorSection(),
            self.list_include.header().sortIndicatorOrder().value
        )

        self.list_include.sortItems(1, Qt.SortOrder.AscendingOrder)

        include_list = []
        for index in range(self.list_include.topLevelItemCount()):
            item = self.list_include.topLevelItem(index)
            include_list.append(
                (item.text(0), item.data(0, Qt.ItemDataRole.UserRole))
            )

        self.config.setInclude(include_list)

    def add_include(self, data):
        """Add a file or directory to the list."""
        item = QTreeWidgetItem()
        icon = self.icon.FOLDER if data[1] == 0 else self.icon.FILE
        item.setIcon(0, icon)
        duplicates = self.list_include.findItems(
            data[0],
            Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive
        )
        if duplicates:
            self.list_include.setCurrentItem(duplicates[0])
            return
        item.setText(0, data[0])
        item.setData(0, Qt.ItemDataRole.UserRole, data[1])
        self.list_include_count += 1
        item.setText(1, str(self.list_include_count).zfill(6))
        item.setData(1, Qt.ItemDataRole.UserRole, self.list_include_count)
        self.list_include.addTopLevelItem(item)
        self.list_include.setCurrentItem(item)

    def btn_include_remove_clicked(self):
        """Handle removal of selected include entries."""
        for item in self.list_include.selectedItems():
            index = self.list_include.indexOfTopLevelItem(item)
            if index >= 0:
                self.list_include.takeTopLevelItem(index)
        if self.list_include.topLevelItemCount() > 0:
            self.list_include.setCurrentItem(self.list_include.topLevelItem(0))

    def btn_include_file_clicked(self):
        """Handle file-adding button click."""
        for path in qttools.getOpenFileNames(self, _('Include files')):
            if not path:
                continue
            if os.path.islink(path) and not (
                self._parent_dialog.cbCopyUnsafeLinks.isChecked() or
                self._parent_dialog.cbCopyLinks.isChecked()
            ):
                if self._parent_dialog._ask_include_symlinks_target(path):
                    path = os.path.realpath(path)
            path = self.config.preparePath(path)
            self.add_include((path, 1))

    def btn_include_add_clicked(self):
        """Handle directory-adding button click."""
        for path in qttools.getExistingDirectories(
            self, _('Include directories')
        ):
            if not path:
                continue
            if os.path.islink(path) and not (
                self._parent_dialog.cbCopyUnsafeLinks.isChecked() or
                self._parent_dialog.cbCopyLinks.isChecked()
            ):
                if self._parent_dialog._ask_include_symlinks_target(path):
                    path = os.path.realpath(path)
            path = self.config.preparePath(path)
            self.add_include((path, 0))

    def include_custom_sort_order(self, *args):
        """Trigger custom sort order when header is clicked."""
        self.list_include_sort_loop = custom_sort_order(
            self.list_include.header(), self.list_include_sort_loop, *args
        )
