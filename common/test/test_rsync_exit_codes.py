# SPDX-FileCopyrightText: © 2026 Back In Time Team
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests for the description of rsync exit codes (issue #2037)."""
import unittest
from unittest import mock
import snapshots
import tools
tools.initiate_translation(None)

GENERIC = "See 'man rsync' for more details"


class RsyncExitCodeHint(unittest.TestCase):
    """Snapshots._rsync_exit_code_hint()"""

    def hint(self, code):
        return snapshots.Snapshots._rsync_exit_code_hint(code)

    def test_code_10_mentions_socket_and_storage(self):
        """The reported code: "Error in socket IO"."""
        text = self.hint(10)

        self.assertIn('socket', text)
        self.assertIn('storage space', text)

    def test_code_11_mentions_file_io(self):
        """Neighbor: the code rsync uses for a full local disk."""
        text = self.hint(11)

        self.assertIn('file I/O', text)
        self.assertIn('storage space', text)

    def test_other_documented_codes_are_described(self):
        for code in (12, 30):
            with self.subTest(code=code):
                self.assertNotEqual(self.hint(code), GENERIC)

    def test_unknown_codes_keep_generic_text(self):
        """No regression: Everything else is described as before."""
        for code in (1, 2, 5, 13, 20, 255):
            with self.subTest(code=code):
                self.assertEqual(self.hint(code), GENERIC)

    def test_descriptions_differ(self):
        texts = {self.hint(code) for code in (10, 11, 12, 30)}

        self.assertEqual(len(texts), 4)


class RsyncCallbackNoSpace(unittest.TestCase):
    """Snapshots.rsyncCallback() on a full destination."""

    def setUp(self):
        self.sn = snapshots.Snapshots.__new__(snapshots.Snapshots)
        self.sn.snapshotLog = mock.MagicMock()
        self.errors = []
        self.sn.setTakeSnapshotMessage = self.record

    def record(self, type_id, msg):
        if type_id == 1:
            self.errors.append(msg)

    def test_no_space_gets_hint(self):
        line = ('rsync: [receiver] write failed on "/mnt/b/f": '
                'No space left on device (28)')
        params = [False, False]

        self.sn.rsyncCallback(line, params)

        self.assertTrue(params[0])
        self.assertEqual(self.errors[0], 'Error: ' + line)
        self.assertIn('no storage space left', self.errors[-1])

    def test_other_error_has_no_space_hint(self):
        line = 'rsync: [sender] opendir "/a" failed: Permission denied (13)'

        self.sn.rsyncCallback(line, [False, False])

        self.assertFalse(
            any('storage space' in msg for msg in self.errors))

    def test_file_named_like_error_is_ignored(self):
        """A file path that only contains the text is no rsync error."""
        line = 'BACKINTIME: <f+++++++++ No space left on device'
        params = [False, False]

        self.sn.rsyncCallback(line, params)

        self.assertEqual(self.errors, [])


if __name__ == '__main__':
    unittest.main()
