# SPDX-FileCopyrightText: © 2026 Back In Time Team
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests for the hint about missing read permissions (issue #2571)."""
import unittest
from unittest import mock
import snapshots
import tools
tools.initiate_translation(None)

PERMISSION_LINE = (
    'rsync: [sender] opendir "/media/user/USER_FILES/lost+found" failed: '
    'Permission denied (13)')


class RsyncCallbackPermission(unittest.TestCase):
    """Snapshots.rsyncCallback() on rsync permission errors."""

    def setUp(self):
        self.sn = snapshots.Snapshots.__new__(snapshots.Snapshots)
        self.sn.snapshotLog = mock.MagicMock()
        self.messages = []
        self.sn.setTakeSnapshotMessage = lambda type_id, msg: \
            self.messages.append((type_id, msg))

    def errors(self):
        return [msg for type_id, msg in self.messages if type_id == 1]

    def test_permission_denied_gets_hint(self):
        params = [False, False]

        self.sn.rsyncCallback(PERMISSION_LINE, params)

        self.assertTrue(params[0])
        errors = self.errors()
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0], 'Error: ' + PERMISSION_LINE)
        self.assertIn('permission', errors[1])
        self.assertIn('/media/user/USER_FILES/lost+found', errors[1])
        self.assertIn('Exclude', errors[1])

    def test_send_files_permission_denied(self):
        line = ('rsync: [sender] send_files failed to open "/a/b": '
                'Permission denied (13)')

        self.sn.rsyncCallback(line, [False, False])

        self.assertEqual(len(self.errors()), 2)

    def test_other_error_has_no_hint(self):
        line = ('rsync: [generator] link "/a" => "/b" failed: '
                'Invalid cross-device link (18)')
        params = [False, False]

        self.sn.rsyncCallback(line, params)

        self.assertTrue(params[0])
        self.assertEqual(self.errors(), ['Error: ' + line])

    def test_ordinary_line_has_no_error(self):
        params = [False, False]

        self.sn.rsyncCallback('some/file', params)

        self.assertEqual(self.errors(), [])
        self.assertEqual(params, [False, False])

    def test_ignored_chown_permission_line(self):
        """Existing behavior: chown/chgrp errors are not backup errors."""
        line = 'rsync: chown "/a" failed: Operation not permitted (1)'
        params = [False, False]

        self.sn.rsyncCallback(line, params)

        self.assertFalse(params[0])
        self.assertEqual(self.errors(), [])


class UnreadableIncludes(unittest.TestCase):
    """Snapshots._warn_unreadable_includes() before rsync is started."""

    def setUp(self):
        self.sn = snapshots.Snapshots.__new__(snapshots.Snapshots)
        self.sn.snapshotLog = mock.MagicMock()

    def check(self, readable, include, exists=True):
        with mock.patch('os.path.exists', return_value=exists), \
                mock.patch('os.access', return_value=readable), \
                mock.patch.object(snapshots.logger, 'warning'):
            return self.sn._warn_unreadable_includes(include)

    def test_unreadable_is_reported(self):
        result = self.check(False, [('/root/secret', 0)])

        self.assertEqual(result, ['/root/secret'])
        msg = self.sn.snapshotLog.append.call_args[0][0]
        self.assertIn('/root/secret', msg)

    def test_readable_is_silent(self):
        self.assertEqual(self.check(True, [('/home/user', 0)]), [])
        self.sn.snapshotLog.append.assert_not_called()

    def test_missing_path_is_not_reported(self):
        """A missing path is a different problem (not a permission one)."""
        self.assertEqual(
            self.check(False, [('/gone', 0)], exists=False), [])

    def test_empty_include_list(self):
        self.assertEqual(self.check(False, []), [])


if __name__ == '__main__':
    unittest.main()
