#!/usr/bin/env python3
from PyQt6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt
import sys
app = QApplication(sys.argv)

tree = QTreeWidget()
tree.setColumnCount(1)
tree.setHeaderHidden(True)

# Verhindern, dass Items einklappbar sind
tree.setItemsExpandable(False)
tree.setExpandsOnDoubleClick(False)
tree.setRootIsDecorated(True)  # wichtig, damit Kinder sichtbar bleiben
# tree.setStyleSheet("QTreeView::branch {background: transparent; border: none; image: none;}")
tree.setStyleSheet("""
QTreeView::branch {
    background: transparent;
    border: none;
    image: none;
}
QTreeWidget::item {
    margin-left: 0px;  /* Top-Level Items bündig */
}
""")
# tree.setIndentation(10)

# Gruppe 1
group1 = QTreeWidgetItem()
group1.setText(0, "Mozilla Dateien")
group1.setFlags(group1.flags() | Qt.ItemFlag.ItemIsUserCheckable)
group1.setCheckState(0, Qt.CheckState.Unchecked)

child1 = QTreeWidgetItem(group1)
child1.setText(0, "prefs.js")
child1.setFlags(child1.flags() | Qt.ItemFlag.ItemIsUserCheckable)
child1.setCheckState(0, Qt.CheckState.Unchecked)

child2 = QTreeWidgetItem(group1)
child2.setText(0, "extensions.json")
child2.setFlags(child2.flags() | Qt.ItemFlag.ItemIsUserCheckable)
child2.setCheckState(0, Qt.CheckState.Unchecked)

tree.addTopLevelItem(group1)

# Gruppe 2
group2 = QTreeWidgetItem()
group2.setText(0, "Linux Dateien")
group2.setFlags(group2.flags() | Qt.ItemFlag.ItemIsUserCheckable)
group2.setCheckState(0, Qt.CheckState.Unchecked)

child3 = QTreeWidgetItem(group2)
child3.setText(0, "config.cfg")
child3.setFlags(child3.flags() | Qt.ItemFlag.ItemIsUserCheckable)
child3.setCheckState(0, Qt.CheckState.Unchecked)

tree.addTopLevelItem(group2)

# Alle Gruppen permanent expandieren
for i in range(tree.topLevelItemCount()):
    tree.topLevelItem(i).setExpanded(True)

tree.show()
sys.exit(app.exec())
