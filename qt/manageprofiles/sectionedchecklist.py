# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The widget ..."""
from __future__ import annotations
from PyQt6.QtWidgets import (QApplication,
                             QCheckBox,
                             QHBoxLayout,
                             QLabel,
                             QSizePolicy,
                             QSpacerItem,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
import qttools


class SectionedCheckList(QTreeWidget):
    """A list widget with entries grouped and all entries checkable.

    Most of treewidgets default behavior is disabled, e.g. foldable tree and
    checkboxes. Customized checkbox widgets are used instead.
    """
    class ItemWithCheckbox(QTreeWidgetItem):
        """Base class for list entry with customized checkbox and a label.
        """
        def __init__(self,
                     tree: QTreeWidget,
                     columns: list[str],
                     indent_factor: int):
            super().__init__()

            self.label = None

            self.setFlags(Qt.ItemFlag.ItemIsEnabled)

            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)

            self.checkbox = QCheckBox()

            if indent_factor > 0:
                layout.addSpacerItem(QSpacerItem(
                    self.checkbox.sizeHint().width()*indent_factor,
                    0,
                    QSizePolicy.Policy.Fixed,
                    QSizePolicy.Policy.Minimum))
            layout.addWidget(self.checkbox)

            self.label = QLabel(columns[0])
            layout.addWidget(self.label)
            layout.addStretch()

            widget = QWidget()
            widget.setLayout(layout)

            self.setData(0, Qt.ItemDataRole.UserRole, columns[0])

            tree.addTopLevelItem(self)
            tree.setItemWidget(self, 0, widget)

            for idx, col in enumerate(columns[1:], 1):
                self.setText(idx, col)

        def __hash__(self):
            return hash(self.data(0, Qt.ItemDataRole.UserRole))

        def __eq__(self, other):
            if isinstance(other, type(self)):
                return self.data(0, Qt.ItemDataRole.UserRole) \
                    == other.data(0, Qt.ItemDataRole.UserRole)

            return False

    class HeaderItem(ItemWithCheckbox):
        """A group header.

        Its visual appearance is different from other entries. It also
        regulates the check state of its children.
        While creating this item it adds itself to the tree widget.

        Args:
            tree: The tree widget.
            name: Name of group.
            column_count: Number of columns in the tree widget.
        """
        def __init__(self, tree: QTreeWidget, name: str, column_count: int):
            super().__init__(tree, [name], 0)
            self._entries_checked = 0
            self._entries = []
            self._tree = tree
            self._set_color_and_font(column_count)
            self.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.checkbox.checkStateChanged.connect(
                self.on_header_state_changed)

        def _set_color_and_font(self, column_count: int):
            # bold font
            font = self.label.font()
            font.setBold(True)
            self.label.setFont(font)

            # 1st column fore-/background color
            self.label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
            self.label.setBackgroundRole(QPalette.ColorRole.Window)

            # other columns fore-/background color
            palette = QApplication.instance().palette()
            fg_color = palette.color(QPalette.ColorRole.PlaceholderText)
            bg_color = palette.color(QPalette.ColorRole.AlternateBase)
            for idx in range(column_count):
                self.setForeground(idx, fg_color)
                self.setBackground(idx, bg_color)

        def on_header_state_changed(self, state: int | Qt.CheckState):
            """Handle click on header item."""
            if state == Qt.CheckState.PartiallyChecked:
                return

            # Checked or unchecked
            self._entries_checked = 0 if state == Qt.CheckState.Unchecked \
                else len(self._entries)

            # Update children
            for entry in self._entries:
                with qttools.block_signals(entry.checkbox):
                    entry.checkbox.setCheckState(state)

        def on_entry_state_changed(self, state: int | Qt.CheckState):
            """Handle click on one of the groups entry items."""
            if state == Qt.CheckState.Checked:
                self._entries_checked += 1
            else:
                self._entries_checked -= 1

            self.update_state()

        def register_entry(self, entry: SectionedCheckList.EntryItem):
            """Register an entry to this group/header."""
            self._entries.append(entry)

        def update_state(self):
            """Update check state of the group.

            The state depends on the check state of its entries/children.
            """

            if len(self._entries) == self._entries_checked:
                state = Qt.CheckState.Checked
            elif self._entries_checked == 0:
                state = Qt.CheckState.Unchecked
            else:
                state = Qt.CheckState.PartiallyChecked

            self.checkbox.setCheckState(state)

    # pylint: disable-next=too-few-public-methods
    class EntryItem(ItemWithCheckbox):
        """Regular entry always as child of a group (``HeaderItem``).

        While creating this item it adds itself to the tree widget.

        Args:
            tree: The tree widget.
            header: The group as parent header item.
            columns: List of column content.
        """
        def __init__(self,
                     tree: QTreeWidget,
                     header: SectionedCheckList.HeaderItem,
                     columns: list[str]):
            super().__init__(tree, columns, 2)
            self._header = header

            self._header.register_entry(self)

            self.checkbox.checkStateChanged.connect(
                header.on_entry_state_changed)

    def __init__(self, parent: QWidget, column_count: int):
        super().__init__(parent)
        self.setColumnCount(column_count)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        self.setExpandsOnDoubleClick(False)
        self.header().setStretchLastSection(True)

        self.setSizeAdjustPolicy(
            QTreeWidget.SizeAdjustPolicy.AdjustToContents)

    def add_content(self, content: dict):
        """Fill the widget with content.

        See `bitbase.EXCLUDE_SUGGESTIONS` as an example.

        Args:
            content: Keys used as headers and values are list of tuples where
        the last entry indicates the check state.
        """
        for section_name, entries in content.items():

            header = self.HeaderItem(self, section_name, 2)

            # Last item indicates checked state
            for *cols, checked in entries:
                entry = self.EntryItem(
                    tree=self,
                    header=header,
                    columns=cols
                )
                if checked:
                    entry.checkbox.setCheckState(Qt.CheckState.Checked)

            header.update_state()

        for col in range(self.columnCount()):
            self.resizeColumnToContents(col)

    def get_all_entry_items(self) -> list[SectionedCheckList.EntryItem]:
        """Return a list of all entry items.

        The method assumps all items on top level.
        """
        result = []

        for idx in range(self.topLevelItemCount()):
            item = self.topLevelItem(idx)
            if isinstance(item, self.EntryItem):
                result.append(item)

        return result

    def get_all_entry_strings(self) -> list[str]:
        """The string content of each entry item.

        Techncially the text of the QLabel contained in the entry items first
        column is used.
        """
        result = []
        for item in self.get_all_entry_items():
            result.append(item.label.text())

        return result

    def get_all_checked_entry_strings(self) -> list[str]:
        """The string content of each checked entry item."""
        result = []
        for item in self.get_all_entry_items():
            if item.checkbox.isChecked():
                result.append(item.label.text())

        return result

    def get_entry_stings_separated_by_state(self
                                            ) -> tuple[list[str], list[str]]:
        """Return to list of strings with checked and unchecked entries."""

        checked, un = [], []

        for item in self.get_all_entry_items():
            if item.checkbox.isChecked():
                checked.append(item.label.text())
            else:
                un.append(item.label.text())

        return checked, un
