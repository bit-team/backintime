# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module with a widget combining a spinbox and a combobox."""
from PyQt6.QtWidgets import QWidget
from event import Event
from storagesize import StorageSize, SizeUnit
from manageprofiles.spinboxunit import SpinBoxWithUnit


class StorageSizeWidget(SpinBoxWithUnit):
    """A combined widget for selected storage size values and their unit.
    """
    def __init__(self,
                 parent: QWidget,
                 range_min_max: tuple[int, int],
                 value: StorageSize = StorageSize(0, SizeUnit.MIB)):

        content_dict = {unit: str(unit) for unit in SizeUnit}
        del content_dict[SizeUnit.B]  # exclude Bytes

        super().__init__(
            parent=parent,
            range_min_max=range_min_max,
            content_dict=content_dict,
        )

        self._value = None
        self.set_storagesize(value)

        self._combo.currentIndexChanged.connect(self._on_unit_changed)
        self._spin.valueChanged.connect(self._on_spin_changed)

        self.event_value_changed = Event()

    def get_storagesize(self) -> StorageSize:
        """Current value as StorageSize object."""
        val, unit = self.data_and_unit

        return StorageSize(val, unit)

    def set_storagesize(self,
                        value: StorageSize,
                        dont_touch_unit: bool = False):
        """Set value using a StorageSize object."""
        if dont_touch_unit:
            # copy
            value = StorageSize(value.value(), value.unit)
            # Use widgets unit
            value.unit = self.unit()

        self.set_value(value.value())
        self.select_unit(value.unit)

        self._value = value

    def _on_spin_changed(self, val):
        self._value.set_value(val)

        # Notify observers
        self.event_value_changed.notify(self._value)

    def _on_unit_changed(self, _idx):
        with self.event_value_changed.keep_silent():
            self._value.unit = self.unit()
            self.set_value(self._value.value())
