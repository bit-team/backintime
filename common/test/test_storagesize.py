# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
# pylint: disable=missing-function-docstring,missing-class-docstring
"""Test related to storagesize.py"""
import unittest
from storagesize import SizeUnit, StorageSize


class Basics(unittest.TestCase):
    """Basic behavior"""

    def test_set_value(self):
        sut = StorageSize(0)

        # pylint: disable=protected-access
        self.assertEqual(sut._bytes, 0)

        sut.set_value(1738)
        # pylint: disable=protected-access
        self.assertEqual(sut._bytes, 1738)

    def test_default_unit(self):
        sut = StorageSize(0)
        self.assertEqual(sut.unit, SizeUnit.B)

    def test_each_unit(self):
        for unit in SizeUnit:
            sut = StorageSize(0, unit)
            self.assertEqual(sut.unit, unit)

    def test_values_in_bytes(self):
        for value in [1, 20, 300, 456789123456]:
            sut = StorageSize(value)
            self.assertEqual(sut.value(SizeUnit.B), value)

    def test_value_default_unit(self):
        for unit in SizeUnit:
            sut = StorageSize(12, unit)
            self.assertEqual(sut.value(), 12)

    def test_byte_property(self):
        for value in [1, 20, 300, 456789123456]:
            sut = StorageSize(value)
            self.assertEqual(sut.byte, value)

    def test_str(self):
        sut = StorageSize(456789123456)
        self.assertEqual(str(sut), f'{456789123456:n} Byte')

        sut.unit = SizeUnit.MIB
        self.assertEqual(str(sut), f'{435628:n} MiB')

        sut.unit = SizeUnit.GIB
        self.assertEqual(str(sut), f'{425:n} GiB')

    def test_print(self):
        sut = StorageSize(456789123456)
        self.assertEqual(sut.as_unit(SizeUnit.B), f'{456789123456:n} Byte')
        self.assertEqual(sut.as_unit(SizeUnit.MIB), f'{435628:n} MiB')
        self.assertEqual(sut.as_unit(SizeUnit.GIB), f'{425:n} GiB')

    def test_repr(self):
        val = 456789123456
        sut = StorageSize(val)
        self.assertIn(f'{val}', repr(sut))
        self.assertIn(str(SizeUnit.B), repr(sut))

        sut.unit = SizeUnit.MIB
        self.assertIn(f'{val}', repr(sut))
        self.assertIn(str(SizeUnit.MIB), repr(sut))

        sut.unit = SizeUnit.GIB
        self.assertIn(f'{val}', repr(sut))
        self.assertIn(str(SizeUnit.GIB), repr(sut))

    def test_intern_always_bytes(self):
        sut = StorageSize(1024, SizeUnit.MIB)
        expected_bytes = 1024*(1024**2)
        expected_value = {
            SizeUnit.B: expected_bytes,
            SizeUnit.MIB: 1024,
            SizeUnit.GIB: 1
        }

        for unit in SizeUnit:
            sut.unit = unit
            # pylint: disable=protected-access
            self.assertEqual(sut._bytes, expected_bytes)
            self.assertEqual(sut.value(), expected_value[unit])


class Convert(unittest.TestCase):
    def test_as_mebibyte_via_value(self):
        # 1 KiB
        sut = StorageSize(1024)
        self.assertEqual(sut.value(SizeUnit.MIB), 0)

        # 1024 KiB / 1 MiB
        sut = StorageSize(1048576)
        self.assertEqual(sut.value(SizeUnit.MIB), 1)

        # 1024 MiB
        sut = StorageSize(1073741824)
        self.assertEqual(sut.value(SizeUnit.MIB), 1024)

    def test_mebibyte_property(self):
        # 1 KiB
        sut = StorageSize(1024)
        self.assertEqual(sut.mebibyte, 0)

        # 1024 KiB / 1 MiB
        sut = StorageSize(1048576)
        self.assertEqual(sut.mebibyte, 1)

        # 1024 MiB
        sut = StorageSize(1073741824)
        self.assertEqual(sut.mebibyte, 1024)

    def test_gibibyte_property(self):
        # 1 KiB
        sut = StorageSize(1024)
        self.assertEqual(sut.gibibyte, 0)

        # 1024 KiB / 1 MiB
        sut = StorageSize(1048576)
        self.assertEqual(sut.gibibyte, 0)

        # 1024 MiB
        sut = StorageSize(1073741824)
        self.assertEqual(sut.gibibyte, 1)

    def test_gibibyte_to(self):
        sut = StorageSize(1, SizeUnit.GIB)
        self.assertEqual(sut.value(SizeUnit.B), 1073741824)
        self.assertEqual(sut.mebibyte, 1024)
        self.assertEqual(sut.gibibyte, 1)

    def test_mebibyte_to(self):
        sut = StorageSize(1, SizeUnit.MIB)
        self.assertEqual(sut.value(SizeUnit.B), 1048576)
        self.assertEqual(sut.mebibyte, 1)
        self.assertEqual(sut.gibibyte, 0)


class Rounding(unittest.TestCase):
    """Rounding behavior"""
    def test_round_default(self):
        # 1.5 MiB + 30 KiB
        sut = StorageSize(1572864 + 30240)

        # Rounded (up) to nearest integer
        self.assertEqual(sut.mebibyte, 2)

        # 1 decimal place
        self.assertEqual(sut.value(SizeUnit.MIB, 1), 1.5)

        # 2 decimal places
        self.assertEqual(sut.value(SizeUnit.MIB, 2), 1.53)


class Addition(unittest.TestCase):
    def test_simple(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)
        sut = a + b

        self.assertEqual(sut.byte, 2048)

    def test_integer(self):
        a = StorageSize(1024, SizeUnit.B)
        b = 1024
        sut = a + b

        self.assertEqual(sut.byte, 2048)

    def test_unit_preserved(self):
        sut = StorageSize(1024, SizeUnit.B) + StorageSize(1024, SizeUnit.B)
        self.assertEqual(sut.unit, SizeUnit.B)

        sut = StorageSize(1024, SizeUnit.MIB) + StorageSize(1024, SizeUnit.B)
        self.assertEqual(sut.unit, SizeUnit.MIB)

        sut = StorageSize(1024, SizeUnit.GIB) + StorageSize(1024, SizeUnit.B)
        self.assertEqual(sut.unit, SizeUnit.GIB)

        sut = StorageSize(1024, SizeUnit.B) + StorageSize(1024, SizeUnit.GIB)
        self.assertEqual(sut.unit, SizeUnit.B)


class Subtraction(unittest.TestCase):
    def test_simple(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)
        sut = a - b

        self.assertEqual(sut.byte, 0)

        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(24, SizeUnit.B)
        sut = a - b

        self.assertEqual(sut.byte, 1000)

    def test_integer(self):
        a = StorageSize(1024, SizeUnit.B)
        b = 1000
        sut = a - b

        self.assertEqual(sut.byte, 24)


class Equal(unittest.TestCase):
    def test_equal(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)

        self.assertEqual(a, b)
        self.assertTrue(a == b)

    def test_not_equal(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(24, SizeUnit.B)

        self.assertNotEqual(a, b)
        self.assertFalse(a == b)

    def test_integer_equal(self):
        a = StorageSize(1024, SizeUnit.B)
        b = 1024

        self.assertEqual(a, b)
        self.assertTrue(a == b)

    def test_integer_not_equal(self):
        a = StorageSize(1024, SizeUnit.B)
        b = 1000

        self.assertNotEqual(a, b)
        self.assertFalse(a == b)

    def test_different_units(self):
        a = StorageSize(1, SizeUnit.MIB)
        b = StorageSize(1024 * 1024, SizeUnit.B)
        self.assertEqual(a, b)

        a = StorageSize(1024, SizeUnit.MIB)
        b = StorageSize(1, SizeUnit.GIB)
        self.assertEqual(a, b)


class Hash(unittest.TestCase):
    def test_same_object_same_hash(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)

        self.assertEqual(hash(a), hash(b))
        self.assertEqual(a, b)

    def test_same_object_same_hash_unit_irrelevant(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)
        b.unit = SizeUnit.GIB

        self.assertEqual(hash(a), hash(b))
        self.assertEqual(a, b)

    def test_different_objects_different_hash(self):
        a = StorageSize(1004, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)
        self.assertNotEqual(hash(a), hash(b))
        self.assertNotEqual(a, b)

    def test_hashable_in_set(self):
        a = StorageSize(1004, SizeUnit.B)
        s = {a}
        self.assertIn(a, s)

    def test_usable_as_dict_key(self):
        a = StorageSize(1004, SizeUnit.B)
        d = {a: "Foobar"}
        self.assertEqual(d[a], "Foobar")


class Greater(unittest.TestCase):
    def test_greater(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(500, SizeUnit.B)
        self.assertTrue(a > b)

    def test_not_greater(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)
        self.assertFalse(a > b)

    def test_greater_integer(self):
        a = StorageSize(1024, SizeUnit.B)
        b = 500
        self.assertTrue(a > b)

    def test_not_greater_integer(self):
        a = StorageSize(1024, SizeUnit.B)
        b = 1024
        self.assertFalse(a > b)

    def test_different_units(self):
        a = StorageSize(2, SizeUnit.MIB)
        b = StorageSize(1024 * 1024, SizeUnit.B)
        self.assertTrue(a > b)

        a = StorageSize(2000, SizeUnit.MIB)
        b = StorageSize(1, SizeUnit.GIB)
        self.assertTrue(a > b)


class Less(unittest.TestCase):
    def test_less(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(500, SizeUnit.B)
        self.assertTrue(b < a)

    def test_not_less(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)
        self.assertFalse(b < a)

    def test_less_integer(self):
        a = StorageSize(1024, SizeUnit.B)
        b = 500
        self.assertTrue(b < a)

    def test_not_less_integer(self):
        a = StorageSize(1024, SizeUnit.B)
        b = 1024
        self.assertFalse(b < a)

    def test_different_units(self):
        a = StorageSize(2, SizeUnit.MIB)
        b = StorageSize(1024 * 1024, SizeUnit.B)
        self.assertTrue(b < a)

        a = StorageSize(2000, SizeUnit.MIB)
        b = StorageSize(1, SizeUnit.GIB)
        self.assertTrue(b < a)


class LessGreaterOrEqual(unittest.TestCase):
    """Less or equal  (<=) and greater or equal (>=)"""
    def test_le_and_ge(self):
        a = StorageSize(1024, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)
        self.assertTrue(a >= b)
        self.assertTrue(a <= b)

        a = StorageSize(1025, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)
        self.assertTrue(a >= b)

        a = StorageSize(1023, SizeUnit.B)
        b = StorageSize(1024, SizeUnit.B)
        self.assertTrue(a <= b)

    def test_le_and_ge_integer(self):
        a = StorageSize(1024, SizeUnit.B)
        b = 1024
        self.assertTrue(a >= b)
        self.assertTrue(a <= b)

        a = StorageSize(1025, SizeUnit.B)
        b = 1024
        self.assertTrue(a >= b)

        a = StorageSize(1023, SizeUnit.B)
        b = 1024
        self.assertTrue(a <= b)

    def test_different_units(self):
        a = StorageSize(1, SizeUnit.MIB)
        b = StorageSize(1024 * 1024, SizeUnit.B)
        self.assertTrue(a >= b)
        self.assertTrue(b <= a)

        a = StorageSize(2, SizeUnit.MIB)
        b = StorageSize(1024 * 1024, SizeUnit.B)
        self.assertTrue(a >= b)
        self.assertTrue(b <= a)

        a = StorageSize(2048, SizeUnit.MIB)
        b = StorageSize(2, SizeUnit.GIB)
        self.assertTrue(a <= b)
        self.assertTrue(b >= a)

        a = StorageSize(1023, SizeUnit.MIB)
        b = StorageSize(1, SizeUnit.GIB)
        self.assertTrue(a <= b)
        self.assertTrue(b >= a)
