#!/usr/bin/env python3
from PyQt6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt
import sys

app = QApplication(sys.argv)

tree = QTreeWidget()
tree.setColumnCount(1)
tree.setHeaderHidden(True)
tree.setIndentation(0)

# Flache Liste: Gruppen und Kinder als normale Items
# Gruppe 1
group1 = QTreeWidgetItem()
group1.setText(0, "Mozilla Dateien")
group1.setFlags(group1.flags() | Qt.ItemFlag.ItemIsUserCheckable)
group1.setCheckState(0, Qt.CheckState.Unchecked)
tree.addTopLevelItem(group1)

child1 = QTreeWidgetItem()
child1.setText(0, "    prefs.js")  # Einrückung durch Leerzeichen
child1.setFlags(child1.flags() | Qt.ItemFlag.ItemIsUserCheckable)
child1.setCheckState(0, Qt.CheckState.Unchecked)
tree.addTopLevelItem(child1)

child2 = QTreeWidgetItem()
child2.setText(0, "    extensions.json")
child2.setFlags(child2.flags() | Qt.ItemFlag.ItemIsUserCheckable)
child2.setCheckState(0, Qt.CheckState.Unchecked)
tree.addTopLevelItem(child2)

# Gruppe 2
group2 = QTreeWidgetItem()
group2.setText(0, "Linux Dateien")
group2.setFlags(group2.flags() | Qt.ItemFlag.ItemIsUserCheckable)
group2.setCheckState(0, Qt.CheckState.Unchecked)
tree.addTopLevelItem(group2)

child3 = QTreeWidgetItem()
child3.setText(0, "    config.cfg")
child3.setFlags(child3.flags() | Qt.ItemFlag.ItemIsUserCheckable)
child3.setCheckState(0, Qt.CheckState.Unchecked)
tree.addTopLevelItem(child3)

tree.show()
sys.exit(app.exec())
