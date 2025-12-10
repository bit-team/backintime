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
    class HeaderItem(QTreeWidgetItem):
        def __init__(self, name: str):
            super().__init__()
            # self.setText(0, name)
            self.setData(0, Qt.ItemDataRole.UserRole, name)

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

        def __hash__(self):
            return hash(self.data(0, Qt.ItemDataRole.UserRole))

        def __eq__(self, other):
            if isinstance(other, type(self)):
                return self.data(0, Qt.ItemDataRole.UserRole) \
                    == other.data(0, Qt.ItemDataRole.UserRole)

            return False

    class EntryItem(QTreeWidgetItem):
        def __init__(self):
            super().__init__()
            self.setFlags(Qt.ItemFlag.ItemIsEnabled)

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

            header = self.HeaderItem(section_name)
            self.addTopLevelItem(header)
            wdg, checkbox = self._create_checkbox_widget(section_name, 0)
            self.setItemWidget(header, 0, wdg)

            # register the new header
            self._entries[header] = []

            for col_one, col_two in entries:
                self._add_entry_item(col_one, col_two, header)

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

    def _add_entry_item(self, col_one: str, col_two: str, header):
        item = self.EntryItem()
        self.addTopLevelItem(item)

        # register the entry
        self._entries[header].append(item)

        # 1st column
        item.setData(0, Qt.ItemDataRole.UserRole, col_one)

        # checkbox widget
        wdg, checkbox = self._create_checkbox_widget(col_one, 2)
        self.setItemWidget(item, 0, wdg)

        # forward checkbox → item.setCheckState()
        checkbox.stateChanged.connect(
            partial(self._on_child_checkbox_changed, item=item)
        )

        # 2nd column
        item.setText(1, col_two)


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
        for child in self._entries[item]:
            wdg = self.itemWidget(child, 0)
            if wdg:
                cb = wdg.findChild(QCheckBox)
                if cb:
                    cb.setChecked(checked)

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
