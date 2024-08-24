# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
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
            self.addItem(entry, userData=data)

    @property
    def current_data(self):
        return self.itemData(self.currentIndex())

    def select_by_data(self, data):
        """Select an entry in the combo box by its underlying data."""
        for idx in range(self.count()):
            if self.itemData(idx) == data:
                self.setCurrentIndex(idx)
                return

        raise ValueError('Unable to select combo box entry because data not '
                         f'found in it. Data is: {data} (type: {type(data)})')
