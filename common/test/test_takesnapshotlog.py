# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Split from test_sid.py
"""Tests about takesnapshot.log.bz2 file related to snapshots.SID class"""
import stat
from pathlib import Path
from test import generic
import snapshots
import snapshotlog


class TakeSnapshotLog(generic.SnapshotsTestCase):
    """Tests regarding takesnapshot.log file"""

    def test_error_if_not_exist(self):
        """Log file does not exist"""
        sid_name = '20151219-010324-123'
        sid = snapshots.SID(sid_name, self.cfg)

        sid_path = Path(self.snapshotPath) / sid_name
        sid_path.mkdir(parents=True)

        result = '\n'.join(sid.log())

        self.assertTrue(result.startswith('Failed to get snapshot log from'))

    def test_content(self):
        """Write and read content"""
        sid_name = '20151219-010324-123'
        sid = snapshots.SID(sid_name, self.cfg)

        sid_path = Path(self.snapshotPath) / sid_name
        sid_path.mkdir(parents=True)

        log_path = sid_path / snapshots.SID.LOG

        self.assertFalse(log_path.exists())

        content = 'foo bar\nbaz'
        sid.setLog(content)

        self.assertTrue(log_path.exists())
        self.assertTrue(log_path.is_file())

        result = '\n'.join(sid.log())

        self.assertEqual(result, content)

    def test_log_filter(self):
        """Filter for changes"""
        sid_name = '20151219-010324-123'
        sid = snapshots.SID(sid_name, self.cfg)

        sid_path = Path(self.snapshotPath) / sid_name
        sid_path.mkdir(parents=True)

        # Content with info, changes and errors
        sid.setLog('foo bar\n[I] 123\n[C] baz\n[E] bla')

        # content filtered only for changes
        result = '\n'.join(sid.log(mode=snapshotlog.LogFilter.CHANGES))

        self.assertEqual(result, 'foo bar\n[C] baz')

    def test_write_binary(self):
        """Write binary but read as text"""
        sid_name = '20151219-010324-123'
        sid = snapshots.SID(sid_name, self.cfg)

        sid_path = Path(self.snapshotPath) / sid_name
        sid_path.mkdir(parents=True)

        content = b'foo bar\nbaz'

        sid.setLog(content)

        result = '\n'.join(sid.log())
        self.assertEqual(result, content.decode('utf-8'))

    def test_owner_only_permission(self):
        """Create log file with permissions only for the owner"""
        sid_name = '20151219-010324-123'
        sid = snapshots.SID(sid_name, self.cfg)

        sid_path = Path(self.snapshotPath) / sid_name
        sid_path.mkdir(parents=True)

        log_path = sid_path / snapshots.SID.LOG
        sid.setLog('foo bar')

        # Owner only permissions
        self.assertEqual(
            stat.filemode(log_path.stat().st_mode),
            '-rw-------'
        )
