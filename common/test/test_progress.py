# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
# pylint: disable=missing-class-docstring
"""Tests for rsync progress parsing.

Note: Issue #2640 revealed that rsync 3.5.0 and 3.5.2 use different unit
suffixes in progress output, e.g. GB/MB/s versus GiB/MiB/s. This tests
cover this difference.
"""
import unittest
import progress


class RsyncParsingGeneral(unittest.TestCase):
    """Test parsing of rsync progress output."""

    def test_decimal_units(self):
        """Decimal unit suffixes like in rsync 3.5.0."""
        result = progress.parse_rsync_progress(
            '1.63GB  13%  4.54MB/s  0:05:58'
        )

        self.assertEqual(
            result,
            {
                'sent': '1.63GB',
                'percent': 13,
                'speed': '4.54MB/s',
                'eta': '0:05:58',
            },
        )

    def test_binary_units(self):
        """Binary unit suffixes like rsync 3.5.2."""
        result = progress.parse_rsync_progress(
            '1.63GiB  13%  4.54MiB/s  0:05:58'
        )

        self.assertEqual(
            result,
            {
                'sent': '1.63GiB',
                'percent': 13,
                'speed': '4.54MiB/s',
                'eta': '0:05:58',
            },
        )

    def test_kilobyte_units(self):
        """Small units."""
        result = progress.parse_rsync_progress(
            '517.38K  13%  14.46MB/s  0:05:58'
        )

        self.assertEqual(
            result,
            {
                'sent': '517.38K',
                'percent': 13,
                'speed': '14.46MB/s',
                'eta': '0:05:58',
            }
        )

    def test_decimal_dot_and_comma(self):
        """Rsync use decimal and thousand separators based on the local"""

        # Rsync (3.5) does not use a thousand separator in the speed field.
        result = progress.parse_rsync_progress(
            '12.345.678,86G  99% 10115,73GB/s    0:03:12'
        )

        self.assertEqual(
            result,
            {
                'sent': '12.345.678,86G',
                'percent': 99,
                'speed': '10115,73GB/s',
                'eta': '0:03:12',
            },
        )

        # Switch dot and comma
        result = progress.parse_rsync_progress(
            '12,345,678.86G  99% 10115.73GB/s    0:03:12'
        )

        self.assertEqual(
            result,
            {
                'sent': '12,345,678.86G',
                'percent': 99,
                'speed': '10115.73GB/s',
                'eta': '0:03:12',
            },
        )

    def test_number_formats(self):
        """Different number formats and units."""
        test_data = [
            # (sent, speed)
            ('0B', '0B/s'),
            ('123B', '123B/s'),
            ('1.5kB', '2.5kB/s'),
            ('1,5MB', '2,5MB/s'),
            ('1.5GiB', '2.5GiB/s'),
            ('1.5TB', '2.5GB/s'),
        ]

        for sent, speed in test_data:
            with self.subTest(sent=sent, speed=speed):
                result = progress.parse_rsync_progress(
                    f'{sent}  10%  {speed}  0:10:00'
                )

                self.assertIsNotNone(result)
                self.assertEqual(result['sent'], sent)
                self.assertEqual(result['speed'], speed)

    def test_eta_formats(self):
        """Different ETA formats"""
        test_data = [
            '0:00:01',
            '12:34:56',
            '?:??:??',
            '00:00:00',
        ]

        for eta in test_data:
            with self.subTest(eta=eta):
                result = progress.parse_rsync_progress(
                    f'1.5GB  10%  2MB/s  {eta}'
                )

                self.assertIsNotNone(result)
                self.assertEqual(result['eta'], eta)

    def test_whitespace_before_and_after(self):
        """Some blanks at beginning and end of input string"""
        result = progress.parse_rsync_progress(
            '     1.63GB  13%  4.54MB/s  0:05:58    '
        )

        self.assertEqual(
            result,
            {
                'sent': '1.63GB',
                'percent': 13,
                'speed': '4.54MB/s',
                'eta': '0:05:58',
            },
        )

    def test_negative_speed(self):
        """Negative transfer speed."""
        result = progress.parse_rsync_progress(
            '1.63GB  13%  -449.39kB/s  0:05:58'
        )

        self.assertEqual(result['speed'], '-449.39kB/s')

    def test_eta_unknown(self):
        """Unknown ETA."""
        result = progress.parse_rsync_progress(
            '1.63GB  13%  4.54MB/s  ??:??:??'
        )

        self.assertEqual(result['eta'], '??:??:??')


class NewlinesAndUnparsable(unittest.TestCase):
    def test_empty_line(self):
        """Return None for an empty line."""
        self.assertIsNone(progress.parse_rsync_progress(''))

    def test_non_progress_line(self):
        """No parsable content result in None"""
        self.assertIsNone(
            progress.parse_rsync_progress('sending incremental file list')
        )

    def test_first_line_only(self):
        """Parse the first line and ignore subsequent lines."""
        result = progress.parse_rsync_progress(
            '1.63GB  13%  4.54MB/s  0:05:58\n'
            '2.00GB  20%  5.00MB/s  0:04:00'
        )

        self.assertEqual(result['sent'], '1.63GB')

    def test_ignore_second_line_even_if_parsable(self):
        """Second line is ignored even if it contain parsable content"""
        result = progress.parse_rsync_progress(
            'sending incremental file list\n'
            '1.63GB  13%  4.54MB/s  0:05:58'
        )

        self.assertIsNone(result)

    def test_trailing_newline(self):
        """Newline at the end"""
        result = progress.parse_rsync_progress(
            '1.63GB  13%  4.54MB/s  0:05:58\n'
        )

        self.assertEqual(result['sent'], '1.63GB')


class EtaOrElapsed(unittest.TestCase):
    """Test interpretation of the time field.

    https://github.com/RsyncProject/rsync/issues/1204
    """

    def test_eta_no_suffix(self):
        """No xfr suffix means ETA"""
        result = progress.parse_rsync_progress(
            '1.63GB  13%  4.54MB/s  0:05:58'
        )

        self.assertEqual(result['eta'], '0:05:58')

    def test_eta_ir_chk_suffix(self):
        """xfr suffix with ir-chk"""
        result = progress.parse_rsync_progress(
            '517.38K  26%   14.46MB/s    0:00:53 (xfr#53, ir-chk=169/452)'
        )

        self.assertEqual(result['eta'], '0:00:53')

    def test_no_eta_to_chk_suffix(self):
        """Reject time field in case of xfr suffix with to-chk"""
        result = progress.parse_rsync_progress(
            '10,86G  99% 10115,73GB/s    1:23:45 (xfr#326, to-chk=0/388)'
        )

        self.assertEqual(
            result,
            {
                'sent': '10,86G',
                'percent': 99,
                'speed': '10115,73GB/s',
                'eta': '??:??:??'
            },
        )
