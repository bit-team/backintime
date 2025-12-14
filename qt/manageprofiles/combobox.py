# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module with an improved combo box widget."""
from typing import Any
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QWidget


class BitComboBox(QComboBox):
    """Improved combo box.

    This widget can be filled (with content and data) just by a dictionary. It
    has the ability to select a specific entry based on its underlying
    `userData` instead of just the index.

    Example of a dictionary : ::

        # Values in the dictionary are the strings displayed in the combo box.
        # The keys are the underlying 'userData'.
        fill = {
            10: 'Hour',
            20: 'Day',
            30: 'Week',
            40: 'Month'
        }
        combo = BitComboBox(parent, fill)

    """

    def __init__(self, parent: QWidget, content_dict: dict):
        """
        Args:
            parent: The parent widget.
            content_dict: The dictionary values used to display entries in the
                combo box and the keys used as data.
        """
        super().__init__(parent=parent)

        self._content_dict = content_dict

        for data, entry in self._content_dict.items():

            label = entry
            tip = None
            ico = None

            if isinstance(label, (list, tuple)):
                tip = label[1]
                try:
                    ico = label[2]
                except IndexError:
                    pass
                label = label[0]

            if ico:
                self.addItem(ico, label, userData=data)
            else:
                self.addItem(label, userData=data)

            if tip is not None:
                self.setItemData(
                    self.count()-1, tip, Qt.ItemDataRole.ToolTipRole)

    @property
    def current_data(self) -> Any:
        """Data linked to the current selected entry."""
        return self.itemData(self.currentIndex())

    def _idx_by_data(self, data: Any) -> int:
        for idx in range(self.count()):
            if self.itemData(idx) == data:
                return idx

        raise ValueError('Unable to find combo box entry because data not '
                         f'found in it. Data is: {data} (type: {type(data)})')

    def enable_by_data(self, data: Any, enable: bool = True):
        """Enable or disable an entry based on its underlying data."""
        idx = self._idx_by_data(data)
        self.model().item(idx).setEnabled(enable)

    def select_by_data(self, data: Any):
        """Select an entry in the combo box by its underlying data.

        Raise: ???
        """
        self.setCurrentIndex(self._idx_by_data(data))

    def has_data(self, data: Any) -> bool:
        """Check if an entry with that data exists."""
        for idx in range(self.count()):
            if self.itemData(idx) == data:
                return True

        return False
