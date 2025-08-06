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
"""Test about FileInfoDict class and files"""
import stat
from pathlib import Path
from test import generic
from unittest.mock import patch
import snapshots


class FileInfoTests(generic.SnapshotsTestCase):
    """Testinthe fileinfo.bz2 file"""
    def test_created_and_reloaded(self):
        """Create info file and reload it in a new SID instance"""
        # Create SID (backup/snapshot) and its directory
        sid_name = '20151219-010324-123'
        sid1 = snapshots.SID(sid_name, self.cfg)
        sid_path = Path(self.snapshotPath) / sid_name
        sid_path.mkdir(parents=True)

        info_file_fp = sid_path / snapshots.SID.FILEINFO

        fi_dict = snapshots.FileInfoDict()
        fi_dict[b'/tmp'] = (123, b'foo', b'bar')
        fi_dict[b'/tmp/foo'] = (456, b'asdf', b'qwer')
        sid1.fileInfo = fi_dict

        self.assertTrue(info_file_fp.is_file())

        # load fileInfo in a new snapshot
        sid2 = snapshots.SID(sid_name, self.cfg)
        self.assertDictEqual(sid2.fileInfo, fi_dict)

    @patch('logger.error')
    def test_read_error(self, mock_logger):
        """Error if info file is empty"""
        sid_name = '20151219-010324-123'
        sid = snapshots.SID(sid_name, self.cfg)
        sid_path = Path(self.snapshotPath) / sid_name
        sid_path.mkdir(parents=True)

        info_file_fp = Path(sid.path(snapshots.SID.FILEINFO))
        info_file_fp.touch()

        with generic.mockPermissions(info_file_fp):
            # file info is empty
            self.assertEqual(sid.fileInfo, snapshots.FileInfoDict())
            # error because it was empty
            self.assertTrue(mock_logger.called)

    @patch('logger.error')
    def test_write_error(self, mock_logger):
        """Error while writing info file"""
        sid_name = '20151219-010324-123'
        sid = snapshots.SID(sid_name, self.cfg)

        sid_path = Path(self.snapshotPath) / sid_name
        sid_path.mkdir(parents=True)

        info_file_fp = Path(sid.path(snapshots.SID.FILEINFO))
        info_file_fp.touch()

        with generic.mockPermissions(info_file_fp):
            fi_dict = snapshots.FileInfoDict()
            fi_dict[b'/tmp'] = (123, b'foo', b'bar')
            fi_dict[b'/tmp/foo'] = (456, b'asdf', b'qwer')

            sid.fileInfo = fi_dict

            self.assertTrue(mock_logger.called)

    def test_owner_only_permissions(self):
        """File permissions only to the owner"""
        # Create SID (backup/snapshot) and its directory
        sid_name = '20151219-010324-123'
        sid1 = snapshots.SID(sid_name, self.cfg)
        sid_path = Path(self.snapshotPath) / sid_name
        sid_path.mkdir(parents=True)

        info_file_fp = sid_path / snapshots.SID.FILEINFO
        info_file_fp.touch()

        fi_dict = snapshots.FileInfoDict()
        sid1.fileInfo = fi_dict

        # Owner only permissions
        self.assertEqual(
            stat.filemode(info_file_fp.stat().st_mode),
            '-rw-------'
        )
