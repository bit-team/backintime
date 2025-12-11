# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The widget ..."""
from __future__ import annotations
from functools import partial
from PyQt6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QWidget, QHBoxLayout, QCheckBox, QSpacerItem, QSizePolicy, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette
import sys


class SectionedCheckList(QTreeWidget):
    class ItemWithCheckbox(QTreeWidgetItem):
        def __init__(self,
                     tree: QTreeWidget,
                     columns: list[str],
                     indent_factor: int):
            super().__init__()

            self._label = None

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

            self._label = QLabel(columns[0])
            layout.addWidget(self._label)
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
        def __init__(self, tree: QTreeWidget, name: str):
            super().__init__(tree, [name], 0)

            self._entry_count = 0
            self._entries_checked = 0

            font = self.font(0)
            font.setBold(True)
            self.setFont(0, font)

            palette = QApplication.instance().palette()
            self.setForeground(
                0, palette.color(QPalette.ColorRole.PlaceholderText))
            self.setBackground(
                0, palette.color(QPalette.ColorRole.Light))

            self.setFlags(Qt.ItemFlag.ItemIsEnabled)

        def on_entry_state_changed(self, state):
            print(f'{self._label.text()=} | on_entry_state_changed() :: {state=}')

            if state == Qt.CheckState.Checked:
                self._entries_checked += 1
            else:
                self._entries_checked -= 1

            self.update_state()

        def increase_entry_count(self):
            self._entry_count += 1

        def update_state(self):
            print(f'{self._entry_count=} {self._entries_checked=}')

            if self._entry_count == self._entries_checked:
                state = Qt.CheckState.Checked
            elif self._entry_count == 0:
                state = Qt.CheckState.Unchecked
            else:
                state = Qt.CheckState.PartiallyChecked

            self.checkbox.setCheckState(state)

    class EntryItem(ItemWithCheckbox):
        def __init__(self,
                     tree: QTreeWidget,
                     header: SectionedCheckList.HeaderItem,
                     columns: list[str]):
            super().__init__(tree, columns, 2)
            self._header = header

            self._header.increase_entry_count()

            # self.checkbox.stateChanged.connect(self._on_state_changed)
            self.checkbox.checkStateChanged.connect(header.on_entry_state_changed)

        def _on_state_changed(self, state: int):
            print(f'_on_state_changed() :: {id(self)=} {type(state)=} {state=}')

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        self.setExpandsOnDoubleClick(False)
        self.header().setStretchLastSection(True)

        self.itemChanged.connect(self._on_item_changed)

        # map header with entries
        self._entries = {}

    def add_content(self, content: dict):
        for section_name, entries in content.items():

            header = self.HeaderItem(self, section_name)

            # register the new header
            self._entries[header] = []

            for col_one, col_two in entries:
                entry = self.EntryItem(
                    tree=self,
                    header=header,
                    columns=[col_one, col_two]
                )
                self._entries[header].append(entry)
                print(f'{self._entries=}')

            self.resizeColumnToContents(0)

    def _create_checkbox_widget(self, label_text: str, spacer_factor: int = 2):
        wdg = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        checkbox = QCheckBox()

        if spacer_factor > 0:
            layout.addSpacerItem(QSpacerItem(
                checkbox.sizeHint().width()*spacer_factor,
                0,
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Minimum))
        layout.addWidget(checkbox)
        label = QLabel(label_text)
        layout.addWidget(label)
        layout.addStretch()
        wdg.setLayout(layout)

        return wdg, checkbox

    def _on_item_changed(self, item, column):
        if column != 0 or not isinstance(item, self.HeaderItem):
            return

        checked = item.checkState(0) == Qt.CheckState.Checked
        try:
            for child in self._entries[item]:
                wdg = self.itemWidget(child, 0)
                if wdg:
                    cb = wdg.findChild(QCheckBox)
                    if cb:
                        cb.setChecked(checked)
        except KeyError:
            print('KeyError: {item=} {self._entries=}')
            pass

    def _find_header(self, child):
        for header, items in self._entries.items():
            if child in items:
                return header
        return None


if __name__ == '__main__':
    app = QApplication(sys.argv)
    tree = SectionedCheckList()
    groups = {
        "Mozilla Dateien": [("prefs.js", "Size 12 KB"), ("extensions.json", "Size 45 KB")],
        "Linux Dateien": [("config.cfg", "Size 3 KB")],
        "Misc": [("readme.txt gaaaaaanz lange mit vielen wörtern ENDE", "Size 1 KB"), ("todo.md", "Size 2 KB")]
    }
    tree.add_content(groups)

    tree.show()
    sys.exit(app.exec())
