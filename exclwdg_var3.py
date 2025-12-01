#!/usr/bin/env python3
from PyQt6.QtWidgets import (
    QApplication, QTreeWidget, QTreeWidgetItem,
    QWidget, QHBoxLayout, QCheckBox, QSpacerItem, QSizePolicy, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette
import sys

class FileHeaderItem(QTreeWidgetItem):
    def __init__(self, name):
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

class FileItem(QTreeWidgetItem):
    pass

app = QApplication(sys.argv)
tree = QTreeWidget()
tree.setColumnCount(2)
tree.setHeaderHidden(True)
tree.setRootIsDecorated(False)
tree.setItemsExpandable(False)
tree.setExpandsOnDoubleClick(False)
tree.header().setStretchLastSection(True)  # zweite Spalte flexibel

groups = {
    "Mozilla Dateien": [("prefs.js", "Size 12 KB"), ("extensions.json", "Size 45 KB")],
    "Linux Dateien": [("config.cfg", "Size 3 KB")],
    "Misc": [("readme.txt", "Size 1 KB"), ("todo.md", "Size 2 KB")]
}

for group_name, files in groups.items():
    # Header
    header = FileHeaderItem(group_name)
    tree.addTopLevelItem(header)
    for name, detail in files:
        item = FileItem()
        tree.addTopLevelItem(item)
        # erste Spalte: Checkbox + Text via Widget
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        checkbox = QCheckBox()
        checkbox_size = checkbox.sizeHint().width()
        layout.addSpacerItem(QSpacerItem(checkbox_size*2, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        layout.addWidget(checkbox)
        label = QLabel(name)
        layout.addWidget(label)
        layout.addStretch()
        widget.setLayout(layout)
        tree.setItemWidget(item, 0, widget)
        # zweite Spalte: Text
        item.setText(1, detail)

# flexible Spaltenbreite erst nach allen Items
tree.resizeColumnToContents(0)

tree.show()
sys.exit(app.exec())
