# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The widget ..."""
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

            font = self.font(0)
            font.setBold(True)
            self.setFont(0, font)

            palette = QApplication.instance().palette()
            self.setForeground(
                0, palette.color(QPalette.ColorRole.PlaceholderText))
            self.setBackground(
                0, palette.color(QPalette.ColorRole.Light))

            # self.setFlags(
            #     Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            self.setFlags(Qt.ItemFlag.ItemIsEnabled)
            #self.setCheckState(0, Qt.CheckState.Unchecked)

    class EntryItem(ItemWithCheckbox):
        def __init__(self, tree: QTreeWidget, columns: list[str]):
            super().__init__(tree, columns, 2)

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
                entry = self.EntryItem(self, [col_one, col_two])
                self._entries[header].append(entry)

                # forward checkbox → item.setCheckState()
                entry.checkbox.stateChanged.connect(
                    partial(self._on_child_checkbox_changed, item=entry)
                )

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

    def _on_child_checkbox_changed(self, state, item):
        header = self._find_header(item)
        if not header:
            return
        # prüfen, ob alle Kinder gecheckt sind
        children = self._entries[header]
        all_checked = all(
            self.itemWidget(c, 0).findChild(QCheckBox).isChecked()
            for c in children
        )
        any_checked = any(
            self.itemWidget(c, 0).findChild(QCheckBox).isChecked()
            for c in children
        )

        if all_checked:
            header.setCheckState(0, Qt.CheckState.Checked)
        elif any_checked:
            header.setCheckState(0, Qt.CheckState.PartiallyChecked)
        else:
            header.setCheckState(0, Qt.CheckState.Unchecked)

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
