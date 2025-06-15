# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
# pylint: disable=missing-class-docstring
"""Tests about the languages module."""
import unittest
import languages


class Completeness(unittest.TestCase):
    def test_key_types(self):
        """Language codes as strings"""
        sut = set(type(k) for k in languages.completeness)

        self.assertEqual(len(sut), 1)

        sut = sut.pop()

        self.assertIs(sut, str)

    def test_value_types(self):
        """Completeness as integers"""
        sut = set(type(v) for v in languages.completeness.values())

        self.assertEqual(len(sut), 1)

        sut = sut.pop()

        self.assertIs(sut, int)
