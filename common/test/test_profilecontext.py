# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests for the profile context."""
# pylint: disable=missing-class-docstring
import unittest
import io
from konfig import Konfig
from profilecontext import ProfileContext
import singleton


class Basics(unittest.TestCase):
    def setUp(self):
        singleton.Singleton.remove_all_instances()

    def test_is_singleton(self):
        first = ProfileContext()
        second = ProfileContext()

        self.assertIs(first, second)

    def test_empty_context(self):
        """A fresh context has no profile."""
        context = ProfileContext()

        self.assertIsNone(context.profile)


class Switch(unittest.TestCase):
    def setUp(self):
        singleton.Singleton.remove_all_instances()

        konfig = Konfig()
        konfig.load(io.StringIO('\n'.join([
            'profile1.name=One',
            'profile3.name=Misc',
            'profile42.name=TheAnswer',
            'profile7.name=Magic',
        ])))

    def test_by_id(self):
        sut = ProfileContext()

        sut.switch(42)

        self.assertEqual(sut._profile_ref, 42)

    def test_by_profile(self):
        sut = ProfileContext()
        profile = Konfig().profile(42)

        sut.switch(profile)

        self.assertEqual(sut._profile_ref, 42)

    def test_clear_with_none(self):
        """Switching to None clears the selected profile."""
        sut = ProfileContext()

        sut.switch(7)
        sut.switch(None)

        self.assertIsNone(sut.profile)


class Unexisting(unittest.TestCase):
    def setUp(self):
        singleton.Singleton.remove_all_instances()

        konfig = Konfig()
        konfig.load(io.StringIO('\n'.join([
            'profile1.name=One',
            'profile3.name=Misc',
            'profile42.name=TheAnswer',
            'profile7.name=Magic',
        ])))

    def test_unexisting(self):
        """The context does not check existance"""
        sut = ProfileContext()
        sut.switch(321)

    def test_access_unexisting(self):
        """But access unexisting profile will fail"""
        sut = ProfileContext()
        sut.switch(321)

        profile = sut.profile
        name = profile.name
