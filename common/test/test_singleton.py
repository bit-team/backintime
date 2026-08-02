# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""Tests about singleton module."""
# pylint: disable=missing-class-docstring,too-few-public-methods
import unittest
import singleton


class Basics(unittest.TestCase):
    class Foo(metaclass=singleton.Singleton):
        def __init__(self):
            self.value = 'Ogawa'

    class Bar(metaclass=singleton.Singleton):
        def __init__(self):
            self.value = 'Naomi'

    def setUp(self):
        singleton.Singleton.remove_all_instances()

    def test_twins(self):
        """Identical id and values."""
        a = self.Foo()
        b = self.Foo()

        self.assertEqual(id(a), id(b))
        self.assertEqual(a.value, b.value)

    def test_share_value(self):
        """Modify value"""
        a = self.Foo()
        b = self.Foo()
        a.value = 'foobar'

        self.assertEqual(a.value, 'foobar')
        self.assertEqual(a.value, b.value)

    def test_multi_class(self):
        """Two different singleton classes."""
        a = self.Foo()
        b = self.Foo()
        x = self.Bar()
        y = self.Bar()

        self.assertEqual(id(a), id(b))
        self.assertEqual(id(x), id(y))
        self.assertNotEqual(id(a), id(y))

        self.assertEqual(a.value, 'Ogawa')
        self.assertEqual(x.value, 'Naomi')

        a.value = 'who'
        self.assertEqual(b.value, 'who')
        self.assertEqual(x.value, 'Naomi')
        self.assertEqual(x.value, y.value)


class Clear(unittest.TestCase):
    class Foo(metaclass=singleton.Singleton):
        def __init__(self):
            self.value = 'Alf'

    class Bar(metaclass=singleton.Singleton):
        def __init__(self):
            self.value = 'Brian'

    def setUp(self):
        singleton.Singleton.remove_all_instances()

    def test_one(self):
        """Remove one instance"""
        # pylint: disable=protected-access
        sut = Clear.Foo()

        # Instance exists
        self.assertEqual(
            singleton.Singleton._instances,
            {Clear.Foo: sut}
        )

        singleton.Singleton.remove_instance(Clear.Foo)

        # No instance
        self.assertEqual(
            singleton.Singleton._instances,
            {}
        )

    def test_unexisting(self):
        """Exception on removing an unexisting instance"""
        # pylint: disable=protected-access
        # No instance
        self.assertEqual(
            singleton.Singleton._instances,
            {}
        )

        with self.assertRaises(TypeError):
            singleton.Singleton.remove_instance(Clear.Foo)

    def test_all(self):
        """Remove all instances"""
        # pylint: disable=protected-access
        sut_foo = Clear.Foo()
        sut_bar = Clear.Bar()

        # Two instance exists
        self.assertEqual(len(singleton.Singleton._instances), 2)

        singleton.Singleton.remove_all_instances()

        # No instance
        self.assertEqual(len(singleton.Singleton._instances), 0)

        new_foo = Clear.Foo()
        new_bar = Clear.Bar()

        self.assertIsNot(sut_foo, new_foo)
        self.assertIsNot(sut_bar, new_bar)

        self.assertEqual(new_foo.value, 'Alf')
        self.assertEqual(new_bar.value, 'Brian')

    def test_all_resets_instances(self):
        """Removed instances are recreated with clean state."""
        sut = Clear.Foo()
        sut.value = 'changed'

        singleton.Singleton.remove_all_instances()

        new_sut = Clear.Foo()

        self.assertIsNot(sut, new_sut)
        self.assertEqual(new_sut.value, 'Alf')
