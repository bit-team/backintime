# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module with a widget combining a spinbox and a combobox."""
from typing import Any
from PyQt6.QtWidgets import QSpinBox, QWidget, QHBoxLayout
from manageprofiles.combobox import BitComboBox


class SpinBoxWithUnit(QWidget):
    """A combination of a `QspinBox` and `BitComboBox` (`QComboBox`).
    """

    def __init__(self,
                 parent: QWidget,
                 range_min_max: tuple[int, int],
                 content_dict: dict):
        """
        Args:
            parent: The parent widget.
            range_min_max: ...
            content_dict: The dictionary values used to display entries in the
                combo box and the keys used as data.
        """
        super().__init__(parent=parent)

        layout = QHBoxLayout(self)

        self._spin = QSpinBox(self)
        self._spin.setRange(*range_min_max)
        layout.addWidget(self._spin)

        self._combo = BitComboBox(self, content_dict)
        layout.addWidget(self._combo)

    @property
    def data_and_unit(self) -> tuple[int, Any]:
        """Data linked to the current selected entry."""
        return (self._spin.value(), self._combo.current_data)

    def select_unit(self, data: Any):
        """Select a unit entry in the combo box by its underlying data."""
        self._combo.select_by_data(data)

    def unit(self) -> Any:
        return self._combo.current_data

    def value(self) -> int:
        """Get value of spin box."""
        return self._spin.value()

    def set_value(self, val: int) -> None:
        """Set value of spin box."""
        self._spin.setValue(val)
