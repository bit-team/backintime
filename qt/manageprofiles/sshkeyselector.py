# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module with widgets regarding SSH Key file selection"""
# from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QButtonGroup,
                             QHBoxLayout,
                             QRadioButton,
                             QVBoxLayout,
                             QWidget)
import qttools
from manageprofiles.combobox import BitComboBox


class SshKeyCombo(BitComboBox):
    """Combo box to select SSH key files.

        # The keys are the underlying 'userData'.
        fill = {
            10: 'Hour',
            20: 'Day',
            30: 'Week',
            40: 'Month'
        }
        combo = BitComboBox(parent, fill)

    """

    def __init__(self, parent: QWidget):
        content_dict = {
            'onekey': 'foo',
            'twokey': 'bar'
        }

        super().__init__(parent=parent, content_dict=content_dict)
        role = Qt.ItemDataRole.ToolTipRole
        self.setItemData(0, 'das ist foo', role)
        self.setItemData(1, 'das ist bar', role)


class SshKeySelector(QWidget):
    """Main widget for selecting or generating key files"""
    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)

        # radio: key selector
        self.radio_key = QRadioButton(_('Private key:'))
        self.selector = SshKeyCombo(self)

        # radio: no key
        self.radio_no = QRadioButton(_('Use system SSH configuration'))
        tooltip = _(
            'Leaves the key file unselected. SSH connections will rely '
            'on the system’s existing client configuration '
            '(e.g., ~/.ssh/config).')
        qttools.set_wrapped_tooltip(self.radio_no, tooltip)

        # button group
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.radio_key)
        self.btn_group.addButton(self.radio_no)

        # layout
        row_key = QHBoxLayout()
        row_key.addWidget(self.radio_key, stretch=0)
        row_key.addWidget(self.selector, stretch=1)
        row_no = QHBoxLayout()
        row_no.addWidget(self.radio_no)
        layout = QVBoxLayout()
        layout.addLayout(row_key)
        layout.addLayout(row_no)
        self.setLayout(layout)
