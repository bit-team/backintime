# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The widget ..."""
from PyQt6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QWidget, QHBoxLayout, QCheckBox, QSpacerItem, QSizePolicy, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette
import sys


class SectionedCheckList(QTreeWidget):
    class HeaderItem(QTreeWidgetItem):
        def __init__(self, name: str):
            super().__init__()
            self.setText(0, name)
            font = self.font(0)
            font.setBold(True)
            self.setFont(0, font)
            palette = QApplication.instance().palette()
            self.setForeground(0, palette.color(QPalette.ColorRole.PlaceholderText))
            self.setBackground(0, palette.color(QPalette.ColorRole.Light))
            self.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            self.setCheckState(0, Qt.CheckState.Unchecked)

    class EntryItem(QTreeWidgetItem):
        pass

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        self.setExpandsOnDoubleClick(False)

        # 2nd column flexible
        self.header().setStretchLastSection(True)

    def add_content(self, content: dict):
        for section_name, entries in content.items():

            header = self.HeaderItem(section_name)
            self.addTopLevelItem(header)

            for col_one, col_two in entries:
                item = self.EntryItem()
                self.addTopLevelItem(item)

                # 1st column with checkbox
                wdg = QWidget()
                layout = QHBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                checkbox = QCheckBox()
                checkbox_size = checkbox.sizeHint().width()
                layout.addSpacerItem(QSpacerItem(
                    checkbox_size*2,
                    0,
                    QSizePolicy.Policy.Fixed,
                    QSizePolicy.Policy.Minimum))
                layout.addWidget(checkbox)
                label = QLabel(col_one)
                layout.addWidget(label)
                layout.addStretch()
                wdg.setLayout(layout)

                self.setItemWidget(item, 0, wdg)

                # 2nd column
                item.setText(1, col_two)

            self.resizeColumnToContents(0)


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
