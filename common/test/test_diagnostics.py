# SPDX-FileCopyrightText: © 2022 Christian Buhtz <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2022 Jürgen Altfeld (aryoda)
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Test related to diagnostics.py"""
import unittest
from unittest.mock import patch
import diagnostics


class General(unittest.TestCase):
    """Test about collecting diagnostic infos."""

    def test_content_minimal(self):
        """Minimal set of elements."""

        sut = diagnostics.collect_minimal_diagnostics()

        # 1st level keys
        self.assertCountEqual(sut.keys(), ['backintime', 'host-setup'])

        # 2nd level "backintime"
        self.assertCountEqual(
            sut['backintime'].keys(),
            ['name', 'version', 'running-as-root'])

        # 2nd level "host-setup"
        self.assertCountEqual(sut['host-setup'].keys(), ['OS'])

    @patch("diagnostics._get_qt_information")
    def test_some_content(self, mock_qt):
        """Some contained elements"""
        mock_qt.return_value = {}

        result = diagnostics.collect_diagnostics()

        # 1st level keys
        self.assertCountEqual(
            result.keys(),
            ['backintime', 'external-programs', 'host-setup', 'python-setup']
        )

        # 2nd level "backintime"
        minimal_keys = ['name', 'version', 'latest-config-version',
                        'started-from', 'running-as-root']
        for key in minimal_keys:
            self.assertIn(key, result['backintime'], key)

        # 2nd level "host-setup"
        minimal_keys = ['platform', 'system', 'locale', 'PATH']
        for key in minimal_keys:
            self.assertIn(key, result['host-setup'], key)

        # 2nd level "python-setup"
        self.assertIn('python', result['python-setup'], 'python')

        # 2nd level "external-programs"
        minimal_keys = [
            'rsync', 'shell', 'RSYNC_OLD_ARGS', 'RSYNC_PROTECT_ARGS',
            'coreutils']
        for key in minimal_keys:
            self.assertIn(key, result['external-programs'], key)

    def test_no_ressource_warning(self):
        """No ResourceWarning's.

        Using subprocess.Popen() often cause ResourceWarning's when not used
        as a context manaager.
        """

        # An AssertionError must be raised.
        # We expect NO ResourceWarnings, but Python has no assertNoWarns().
        # This raises AssertionError because no ResourceWarnings occur.
        with (
            self.assertRaises(AssertionError),
            self.assertWarns(ResourceWarning),
        ):
            diagnostics.collect_diagnostics()

    def test_no_extern_version(self):
        """Get version from not existing tool."""
        # pylint: disable=protected-access
        self.assertEqual(
            diagnostics._get_extern_versions(['fooXbar']),
            '(no fooXbar)'
        )

    def test_replace_user_path(self):
        """Replace users path."""
        d = {
            'foo': '/home/rsync',
            'bar': '~/rsync'
        }

        # pylint: disable=protected-access
        self.assertEqual(
            diagnostics._replace_username_paths(d, 'rsync'),
            {
                'foo': '/home/UsernameReplaced',
                'bar': '~/UsernameReplaced'
            }
        )

        # pylint: disable=protected-access
        self.assertEqual(
            diagnostics._replace_username_paths(d, 'user'),
            d
        )

    @patch('diagnostics._get_extern_versions')
    def test_coreutils_gnu(self, mock_extern):
        """Detect GNU coreutils from ls --version output."""
        mock_extern.return_value = (
            'ls (GNU coreutils) 9.4\n'
            'Copyright (C) 2024 Free Software Foundation, Inc.'
        )
        # pylint: disable=protected-access
        result = diagnostics._get_coreutils_info()
        self.assertEqual(result, 'ls (GNU coreutils) 9.4')

    @patch('diagnostics._get_extern_versions')
    def test_coreutils_busybox(self, mock_extern):
        """Detect BusyBox from ls --version output."""
        mock_extern.return_value = (
            'BusyBox v1.36.1 (2023-11-07 18:53:09 UTC) multi-call binary.'
        )
        # pylint: disable=protected-access
        result = diagnostics._get_coreutils_info()
        self.assertEqual(
            result,
            'BusyBox v1.36.1 (2023-11-07 18:53:09 UTC) multi-call binary.'
        )

    @patch('diagnostics._get_extern_versions')
    def test_coreutils_uutils(self, mock_extern):
        """Detect Rust/uutils coreutils from ls --version output."""
        mock_extern.return_value = (
            'ls 0.0.27\n'
            'uutils coreutils - MIT license'
        )
        # pylint: disable=protected-access
        result = diagnostics._get_coreutils_info()
        self.assertEqual(result, 'Rust/uutils coreutils - ls 0.0.27')


    @patch('diagnostics._get_extern_versions')
    def test_coreutils_unknown(self, mock_extern):
        """Handle unknown coreutils variant gracefully."""
        mock_extern.return_value = 'ls 1.2.3\nSome unknown implementation'
        # pylint: disable=protected-access
        result = diagnostics._get_coreutils_info()
        self.assertEqual(result, '(unknown coreutils) ls 1.2.3')
