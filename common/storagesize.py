# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Model offers the StorageSize class.

Dev note (buhtz, 2025-06): Don't utilize functools.total_ordering decorator for
the StorageSize class. There are performance issues.
"""
from __future__ import annotations
from enum import Enum


class SizeUnit(Enum):
    """Unit to describe storage size."""
    B = 0
    # KIB = 5
    MIB = 10
    GIB = 20
    # TIB = 30

    def __str__(self):
        return {
            self.B: 'Byte',
            self.MIB: 'MiB',
            self.GIB: 'GiB',
        }[self]


class StorageSize:
    """Describe the size of an object in a data storage.

    The object can be free or used space on disc, file size, etc. The value
    is stored internally in Bytes.
    """
    _FACTORS = {
        SizeUnit.B: 0,
        SizeUnit.MIB: 2,
        SizeUnit.GIB: 3,
    }

    def __init__(self, value: int, unit: SizeUnit = SizeUnit.B):

        # Original value in Bytes
        self._bytes = None
        # Unit used to represent the value (e.g. in strings)
        self._unit = unit

        self.set_value(value)

    def __repr__(self) -> str:
        return f'({self._bytes}, {self._unit}) ' \
            f'<{self.__class__.__module__}.' \
            f'{self.__class__.__qualname__} obj at {hex(id(self))}>'

    def __str__(self) -> str:
        value = self.value(self.unit)
        return f'{value:n} {self.unit}'

    @property
    def unit(self) -> SizeUnit:
        """The size unit used."""
        return self._unit

    @unit.setter
    def unit(self, unit: SizeUnit):
        self._unit = unit

    @property
    def byte(self) -> int:
        """Value in Bytes."""
        return self.value(SizeUnit.B)

    @property
    def mebibyte(self) -> int:
        """Value in Mebibytes rounded to nearest integer."""
        return self.value(SizeUnit.MIB)

    @property
    def gibibyte(self) -> int:
        """Value in Gibiytes rounded to nearest integer."""
        return self.value(SizeUnit.GIB)

    def as_unit(self, unit: SizeUnit) -> str:
        """String representation according the given size unit."""
        su = StorageSize(self._bytes, self._unit)
        su.unit = unit
        return str(su)

    def set_value(self, value: int):
        """Set the value based on the current size unit.
        """
        self._bytes = StorageSize.value_to_bytes(value, self.unit)

    def value(self, unit: SizeUnit = None, decimal_places: int = 0
              ) -> int | float:
        """Return the value in specified unit.

        Rounding to nearest integer by default using Python `round()`."""
        if unit is None:
            unit = self.unit

        fx = StorageSize._FACTORS[unit]

        value = round(self._bytes / (1024**fx), decimal_places)

        return int(value) if decimal_places == 0 else value

    @staticmethod
    def value_to_bytes(value: int, unit: SizeUnit):
        """Convert value in given size unit into bytes."""
        fx = StorageSize._FACTORS[unit]
        return value * (1024**fx)

    def __add__(self, other: StorageSize | int) -> StorageSize:
        """Add two storage values together.

        The original size unit is preserved. If `other` is of type `int` the
        current size unit is assumed.
        """
        if isinstance(other, int):
            other = StorageSize(other, self.unit)
            return self + other

        return StorageSize(self._bytes + other._bytes, self.unit)

    def __sub__(self, other: StorageSize | int) -> StorageSize:
        if isinstance(other, int):
            other = StorageSize(other, self.unit)
            return self - other

        return StorageSize(self._bytes - other._bytes, self.unit)

    def __eq__(self, other: StorageSize | int) -> bool:
        """Comparing the size, ignoring the unit.

        The internal byte values are compared.
        """
        if isinstance(other, int):
            other = StorageSize(other, self.unit)
            return self == other

        return self._bytes == other._bytes

    def __hash__(self) -> int:
        return hash(self._bytes)

    def __ne__(self, other: StorageSize | int) -> bool:
        """Not equal"""
        return not self == other

    def __gt__(self, other: StorageSize | int) -> bool:
        """Greater than."""
        if isinstance(other, int):
            other = StorageSize(other, self.unit)
            return self > other

        return self._bytes > other._bytes

    def __lt__(self, other: StorageSize | int) -> bool:
        """Less than."""
        if isinstance(other, int):
            other = StorageSize(other, self.unit)
            return self < other

        return self._bytes < other._bytes

    def __le__(self, other: StorageSize | int) -> bool:
        """Less or equal than."""
        return self < other or self == other

    def __ge__(self, other: StorageSize | int) -> bool:
        """Greater or equal"""
        return self > other or self == other
