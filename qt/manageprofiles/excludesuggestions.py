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
                             QDialog,
                             QDialogButtonBox,
                             QVBoxLayout,
                             QLabel,
                             QLayout,
                             QPushButton,
                             QSizePolicy,
                             QSpacerItem,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPalette
from manageprofiles.sectionedchecklist import SectionedCheckList
import bitbase
import qttools


class ExcludeSuggestionsDialog(QDialog):
    def __init__(self, parent: QDialog, content: dict):
        super().__init__(parent)
        self.setWindowTitle(_('Exclude Suggetions'))

        layout = QVBoxLayout()
        self.setLayout(layout)

        txt = _('Select commonly used items to add to backup exclusions.')
        layout.addWidget(qttools.create_info_label(txt))

        self._wdg_list = SectionedCheckList(self, 2)
        layout.addWidget(self._wdg_list)

        # yes/no buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        btn_default = QPushButton(_('Default'))
        btn_default.setToolTip(_('Reset to predefined selection'))
        btn_default.clicked.connect(lambda: print('RESET DEFAULT'))
        btn_box.addButton(btn_default, QDialogButtonBox.ButtonRole.ActionRole)

        layout.addWidget(btn_box)

        self._wdg_list.add_content(content)
