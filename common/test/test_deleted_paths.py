# SPDX-FileCopyrightText: © 2026 Back In Time Team
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests for the detection of deleted files (issue #136).

With ``--link-dest`` rsync does not hard-link a file that was deleted from
the source and prints nothing about it. If that is the only change the
backup used to be dropped as "nothing changed".

Only temporary directories are used. Tests running a real rsync are skipped
if rsync is not available.
"""
import bz2
import glob
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import tools
tools.initiate_translation(None)
import snapshots  # noqa: E402

RSYNC_AVAILABLE = shutil.which('rsync') is not None

# The rsync arguments used by Snapshots.takeSnapshot() (without SSH).
BACKUP_ARGS = [
    'rsync', '--recursive', '--times', '--devices', '--specials',
    '--hard-links', '--human-readable', '-s', '--links', '--perms',
    '--executability', '--group', '--owner', '-v', '-i',
    '--out-format=BACKINTIME: %i %n%L', '--delete', '--delete-excluded',
]


class _FakeSnapshot:
    """Just enough of SID and NewSnapshot for the deletion check."""

    def __init__(self, backup_dir):
        self._backup_dir = backup_dir

    def pathBackup(self, *_args, **_kwargs):  # noqa: N802 (like SID)
        return str(self._backup_dir)


def _snapshots_instance():
    """A Snapshots instance without its (heavy) constructor."""
    sn = snapshots.Snapshots.__new__(snapshots.Snapshots)
    sn.snapshotLog = mock.MagicMock()
    sn.setTakeSnapshotMessage = mock.MagicMock()
    sn.config = mock.MagicMock()
    sn.config.takeSnapshotRegardlessOfChanges.return_value = False
    return sn


def _tree_state(root):
    """Everything that would change if a snapshot would be modified."""
    state = {}

    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            st = os.lstat(path)
            state[os.path.relpath(path, root)] = (
                st.st_mode, st.st_size, st.st_mtime_ns, st.st_ino, st.st_nlink)

    return state


class DeletedPathsCommand(unittest.TestCase):
    """The comparison must never be able to change a snapshot."""

    def setUp(self):
        self.cmd = snapshots.Snapshots._deleted_paths_command(
            '/mnt/snaps/prev/backup', '/mnt/snaps/new_snapshot/backup')

    def test_is_a_dry_run(self):
        self.assertIn('--dry-run', self.cmd)

    def test_nothing_can_be_deleted_or_removed(self):
        """No option that deletes anything, not even with --dry-run lost."""
        for arg in self.cmd:
            with self.subTest(arg=arg):
                self.assertFalse(arg.startswith('--delete'))
                self.assertFalse(arg.startswith('--remove'))
                self.assertNotEqual(arg, '--del')

    def test_previous_snapshot_is_the_source(self):
        """Previous snapshot is read only (source), the new one is the
        destination, each with a trailing slash."""
        self.assertEqual(self.cmd[-2], '/mnt/snaps/prev/backup/')
        self.assertEqual(self.cmd[-1], '/mnt/snaps/new_snapshot/backup/')

    def test_reports_only_missing_items(self):
        self.assertIn('--ignore-existing', self.cmd)


class ParseCreatedItem(unittest.TestCase):
    """Itemize lines of items rsync would create."""

    def test_created_items(self):
        for line, path in (
                ('>f+++++++++ foo', 'foo'),
                ('>f+++++++++ sub/dir/foo bar.txt', 'sub/dir/foo bar.txt'),
                ('cd+++++++++ sub/dir/', 'sub/dir/'),
                ('cL+++++++++ link -> target', 'link -> target'),
                ('cD+++++++++ dev/null', 'dev/null'),
                ('cS+++++++++ run/socket', 'run/socket'),
                ('>f+++++++++ ünïcode ✓.txt', 'ünïcode ✓.txt'),
        ):
            with self.subTest(line=line):
                self.assertEqual(
                    snapshots.Snapshots._parse_created_item(line), path)

    def test_other_lines(self):
        """Changes of existing items and messages are not deletions."""
        for line in (
                '',
                '>f.st...... changed.txt',
                '.d..t...... dir/',
                '>f..t...... touched.txt',
                'rsync: [sender] opendir "/x" failed: Permission denied (13)',
                'sending incremental file list',
        ):
            with self.subTest(line=line):
                self.assertIsNone(
                    snapshots.Snapshots._parse_created_item(line))


class _RsyncSnapshotsTestCase(unittest.TestCase):
    """Real snapshot trees made with the rsync arguments used by BIT."""

    @classmethod
    def setUpClass(cls):
        if not RSYNC_AVAILABLE:
            raise unittest.SkipTest('rsync is not available')

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        self.src = os.path.join(self.root, 'src')
        self.snaps = os.path.join(self.root, 'snaps')
        os.makedirs(self.src)
        os.makedirs(self.snaps)

    def write(self, rel_path, content='x'):
        path = os.path.join(self.src, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(content)

    def take(self, name, link_dest=None, extra=()):
        """Make snapshot ``name`` like takeSnapshot() does.

        Returns:
            (list): The lines rsync printed.
        """
        backup_dir = os.path.join(self.snaps, name, 'backup')
        os.makedirs(backup_dir)

        cmd = list(BACKUP_ARGS) + list(extra)

        if link_dest:
            cmd.append(f'--link-dest=../../{link_dest}/backup')

        cmd.extend([self.src + '/', backup_dir + '/'])

        out = subprocess.run(
            cmd, check=True, capture_output=True, text=True).stdout

        return out.splitlines()

    def snapshot(self, name):
        return _FakeSnapshot(os.path.join(self.snaps, name, 'backup'))


class FindDeletedPaths(_RsyncSnapshotsTestCase):
    """Snapshots._find_deleted_paths() with real rsync and real trees."""

    def setUp(self):
        super().setUp()
        self.sn = _snapshots_instance()

    def find(self, prev='s1', new='s2'):
        return self.sn._find_deleted_paths(
            self.snapshot(prev), self.snapshot(new))

    def test_deleted_file_directory_and_symlink(self):
        self.write('keep.txt')
        self.write('gone.txt')
        self.write('with space.txt')
        self.write('ünïcode.txt')
        self.write('dir/inner.txt')
        os.symlink('keep.txt', os.path.join(self.src, 'link'))
        self.take('s1')

        os.remove(os.path.join(self.src, 'gone.txt'))
        os.remove(os.path.join(self.src, 'with space.txt'))
        os.remove(os.path.join(self.src, 'ünïcode.txt'))
        os.remove(os.path.join(self.src, 'link'))
        shutil.rmtree(os.path.join(self.src, 'dir'))
        self.take('s2', link_dest='s1')

        self.assertEqual(
            set(self.find()),
            {'gone.txt', 'with space.txt', 'ünïcode.txt', 'link -> keep.txt',
             'dir/', 'dir/inner.txt'})

    def test_nothing_deleted(self):
        self.write('same.txt')
        self.write('edit.txt', 'one')
        self.write('mode.txt')
        self.take('s1')

        self.write('edit.txt', 'two and longer')
        os.chmod(os.path.join(self.src, 'mode.txt'), 0o600)
        self.take('s2', link_dest='s1')

        self.assertEqual(self.find(), [])

    def test_new_file_is_not_a_deletion(self):
        self.write('old.txt')
        self.take('s1')
        self.write('new.txt')
        self.take('s2', link_dest='s1')

        self.assertEqual(self.find(), [])

    def test_newly_excluded_file_counts_as_deleted(self):
        """Documented behavior: A file that is missing only because a new
        exclude pattern was added is treated like a deleted one. The new
        snapshot content really differs from the previous one."""
        self.write('keep.txt')
        self.write('secret.txt')
        self.take('s1')

        self.take('s2', link_dest='s1', extra=['--exclude=secret.txt'])

        self.assertEqual(self.find(), ['secret.txt'])

    def test_comparison_modifies_nothing(self):
        """Neither snapshot changes: not content, mode, times or inodes."""
        self.write('keep.txt')
        self.write('gone.txt')
        self.write('dir/inner.txt')
        os.chmod(os.path.join(self.src, 'keep.txt'), 0o444)
        self.take('s1')
        os.remove(os.path.join(self.src, 'gone.txt'))
        shutil.rmtree(os.path.join(self.src, 'dir'))
        self.take('s2', link_dest='s1')

        prev_before = _tree_state(self.snapshot('s1')._backup_dir)
        new_before = _tree_state(self.snapshot('s2')._backup_dir)

        self.assertTrue(self.find())

        self.assertEqual(
            _tree_state(self.snapshot('s1')._backup_dir), prev_before)
        self.assertEqual(
            _tree_state(self.snapshot('s2')._backup_dir), new_before)

    def test_missing_directory_means_check_failed(self):
        self.write('keep.txt')
        self.take('s1')
        with mock.patch.object(snapshots.logger, 'warning') as warn:
            self.assertIsNone(self.sn._find_deleted_paths(
                self.snapshot('s1'),
                _FakeSnapshot(os.path.join(self.snaps, 'missing', 'backup'))))

        warn.assert_called_once()

    def test_rsync_error_means_check_failed(self):
        """E.g. exit code 23 (partial transfer) is not a result."""
        self.write('keep.txt')
        self.take('s1')
        self.take('s2', link_dest='s1')

        class FailingExecute:
            def __init__(self, cmd, **_kwargs):
                self.printable_cmd = ' '.join(cmd)

            def run(self):
                return 23

        with mock.patch.object(snapshots.tools, 'Execute', FailingExecute), \
                mock.patch.object(snapshots.logger, 'warning') as warn:
            self.assertIsNone(self.find())

        self.assertIn('exit code: 23', warn.call_args[0][0])

    def test_rsync_not_startable_means_check_failed(self):
        self.write('keep.txt')
        self.take('s1')
        self.take('s2', link_dest='s1')

        class MissingBinaryExecute:
            def __init__(self, cmd, **_kwargs):
                self.printable_cmd = ' '.join(cmd)

            def run(self):
                raise FileNotFoundError('rsync')

        with mock.patch.object(
                snapshots.tools, 'Execute', MissingBinaryExecute), \
                mock.patch.object(snapshots.logger, 'warning') as warn:
            self.assertIsNone(self.find())

        warn.assert_called_once()


class CheckForDeletions(unittest.TestCase):
    """Decision, logging and fail-safe behavior."""

    def setUp(self):
        self.sn = _snapshots_instance()
        self.prev = _FakeSnapshot('/prev/backup')
        self.new = _FakeSnapshot('/new/backup')

    def check(self, found):
        with mock.patch.object(
                self.sn, '_find_deleted_paths', return_value=found):
            return self.sn._check_for_deletions(self.prev, self.new)

    def test_deleted_paths_are_changes_and_logged(self):
        self.assertTrue(self.check(['gone.txt', 'dir/', 'dir/inner.txt']))

        self.assertEqual(
            self.sn.snapshotLog.append.call_args_list,
            [mock.call('[C] *deleting   gone.txt', 2),
             mock.call('[C] *deleting   dir/', 2),
             mock.call('[C] *deleting   dir/inner.txt', 2)])

    def test_nothing_deleted_is_no_change(self):
        self.assertFalse(self.check([]))
        self.sn.snapshotLog.append.assert_not_called()

    def test_failed_check_keeps_snapshot_and_warns(self):
        """Never report "nothing changed" if it could not be checked."""
        with mock.patch.object(snapshots.logger, 'warning') as warn:
            self.assertTrue(self.check(None))

        self.assertIn('could not be completed', warn.call_args[0][0])

        # Visible for the user in the log of the backup
        (message, level), _kwargs = self.sn.snapshotLog.append.call_args
        self.assertTrue(message.startswith('[E] '))
        self.assertEqual(level, 1)


class ChangesIncludingDeletions(unittest.TestCase):
    """When the check runs and when not (partial failures)."""

    def setUp(self):
        self.sn = _snapshots_instance()
        self.prev = _FakeSnapshot('/prev/backup')
        self.new = _FakeSnapshot('/new/backup')
        patcher = mock.patch.object(
            self.sn, '_check_for_deletions', return_value=True)
        self.check = patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, has_changes=False, prev='default', exit_code=0,
             has_errors=False):
        if prev == 'default':
            prev = self.prev

        return self.sn._changes_including_deletions(
            has_changes, prev, self.new, exit_code, has_errors)

    def test_clean_run_without_changes_asks_the_check(self):
        self.assertTrue(self.call())
        self.check.assert_called_once_with(self.prev, self.new)

        self.check.return_value = False
        self.assertFalse(self.call())

    def test_changes_reported_by_rsync_need_no_check(self):
        self.assertTrue(self.call(has_changes=True))
        self.check.assert_not_called()

    def test_first_snapshot_has_nothing_to_compare(self):
        self.assertFalse(self.call(prev=None))
        self.check.assert_not_called()

    def test_no_check_after_partial_transfer_or_failure(self):
        """Missing files can not be told apart from deleted ones."""
        for exit_code in (1, 12, 23, 24, 30, -9, -15):
            with self.subTest(exit_code=exit_code):
                self.assertFalse(self.call(exit_code=exit_code))

        self.check.assert_not_called()

    def test_no_check_if_errors_were_detected(self):
        self.assertFalse(self.call(has_errors=True))
        self.check.assert_not_called()

    def test_no_check_if_snapshot_is_taken_anyway(self):
        self.sn.config.takeSnapshotRegardlessOfChanges.return_value = True
        self.assertFalse(self.call())
        self.check.assert_not_called()


class ReportedFailure136(_RsyncSnapshotsTestCase):
    """The reported failure end to end, with real rsync and BIT's parser."""

    def setUp(self):
        super().setUp()
        self.sn = _snapshots_instance()

    def changes_reported_by_rsync(self, lines):
        """Feed rsync's output to the real parser like takeSnapshot() does.

        Returns:
            (list): ``[error, changes]``
        """
        params = [False, False]

        for line in lines:
            self.sn.rsyncCallback(line, params)

        return params

    def test_deletion_only_is_not_dropped_anymore(self):
        self.write('foo')
        self.write('bar')
        self.write('baz')
        self.take('s1')
        os.remove(os.path.join(self.src, 'baz'))

        lines = self.take('new_snapshot', link_dest='s1')
        error, changes = self.changes_reported_by_rsync(lines)

        # The root cause: rsync reports nothing about the deleted file
        self.assertFalse(error)
        self.assertFalse(changes)
        self.assertFalse(os.path.exists(
            os.path.join(self.snaps, 'new_snapshot', 'backup', 'baz')))

        # The fix: the snapshot is kept and the deletion is logged
        self.assertTrue(self.sn._changes_including_deletions(
            changes, self.snapshot('s1'), self.snapshot('new_snapshot'),
            0, False))
        self.sn.snapshotLog.append.assert_called_once_with(
            '[C] *deleting   baz', 2)

    def test_nothing_changed_is_still_dropped(self):
        """No regression: An unchanged source creates no new snapshot."""
        self.write('foo')
        self.write('bar')
        self.take('s1')

        lines = self.take('new_snapshot', link_dest='s1')
        error, changes = self.changes_reported_by_rsync(lines)

        self.assertFalse(self.sn._changes_including_deletions(
            changes, self.snapshot('s1'), self.snapshot('new_snapshot'),
            0, error))
        self.sn.snapshotLog.append.assert_not_called()

    def test_first_snapshot_is_not_compared(self):
        self.write('foo')
        lines = self.take('new_snapshot')
        error, changes = self.changes_reported_by_rsync(lines)

        self.assertTrue(changes)

        with mock.patch.object(self.sn, '_find_deleted_paths') as find:
            self.assertTrue(self.sn._changes_including_deletions(
                changes, None, self.snapshot('new_snapshot'), 0, error))

        find.assert_not_called()


def _sid(root, name):
    """A real SID below the temporary ``root`` with its directory created."""
    cfg = mock.MagicMock()
    cfg.currentProfile.return_value = '1'
    cfg.tag.return_value = '123'
    cfg.hostUserProfile.return_value = ('host', 'user', '1')

    sid = snapshots.SID(name, cfg, pathlib.Path(root))
    os.makedirs(sid.path())

    return sid


def _write_file_info(sid, paths):
    """Write ``fileinfo.bz2`` of ``sid`` containing ``paths`` (bytes)."""
    info = snapshots.FileInfoDict()

    for path in paths:
        info[path] = (33188, b'user', b'group')

    sid.fileInfo = info


class FileInfoPaths(unittest.TestCase):
    """SID.file_info_paths(): the paths of fileinfo.bz2 without a big dict."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sid = _sid(self._tmp.name, '20260101-000000-123')

    def test_same_paths_as_the_dict(self):
        _write_file_info(self.sid, [b'/a', b'/dir', b'/dir/with space'])

        self.assertEqual(
            set(self.sid.file_info_paths()), set(self.sid.fileInfo.keys()))
        self.assertIn(b'/dir/with space', set(self.sid.file_info_paths()))

    def test_missing_file(self):
        self.assertEqual(list(self.sid.file_info_paths()), [])

    def test_malformed_lines_are_ignored(self):
        with bz2.BZ2File(self.sid.path(snapshots.SID.FILEINFO), 'wb') as f:
            f.write(b'33188 user group /ok\n'
                    b'no slash at all\n'
                    b'two fields /bad\n'
                    b'\n')

        self.assertEqual(list(self.sid.file_info_paths()), [b'/ok'])


class LogDeletedPathsFromFileInfo(unittest.TestCase):
    """Deleted files are logged for snapshots kept because of other changes.

    The comparison uses ``fileinfo.bz2`` of both snapshots.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sn = _snapshots_instance()
        self.prev = _sid(self._tmp.name, '20260101-000000-123')
        self.new = _sid(self._tmp.name, '20260102-000000-123')

    def log(self):
        self.sn._log_deleted_paths_from_file_info(self.prev, self.new)

    def test_deleted_paths_are_logged(self):
        _write_file_info(
            self.prev, [b'/keep', b'/gone', b'/dir', b'/dir/inner'])
        _write_file_info(self.new, [b'/keep', b'/added'])

        self.log()

        self.assertEqual(
            self.sn.snapshotLog.append.call_args_list,
            [mock.call('[C] *deleting   gone', 2),
             mock.call('[C] *deleting   dir', 2),
             mock.call('[C] *deleting   dir/inner', 2)])

    def test_nothing_deleted(self):
        _write_file_info(self.prev, [b'/keep'])
        _write_file_info(self.new, [b'/keep', b'/added'])

        self.log()

        self.sn.snapshotLog.append.assert_not_called()

    def test_missing_new_fileinfo_is_not_mass_deletion(self):
        """Without information about the new snapshot nothing is known."""
        _write_file_info(self.prev, [b'/keep', b'/other'])

        self.log()

        self.sn.snapshotLog.append.assert_not_called()

    def test_missing_previous_fileinfo(self):
        _write_file_info(self.new, [b'/keep'])

        self.log()

        self.sn.snapshotLog.append.assert_not_called()

    def test_unreadable_fileinfo_never_stops_the_backup(self):
        _write_file_info(self.new, [b'/keep'])

        with open(self.prev.path(snapshots.SID.FILEINFO), 'wb') as f:
            f.write(b'this is not a bz2 file')

        with mock.patch.object(snapshots.logger, 'warning') as warn:
            self.log()

        warn.assert_called_once()
        self.sn.snapshotLog.append.assert_not_called()

    def test_not_utf8_path(self):
        _write_file_info(self.prev, [b'/keep', b'/bad-\xff-name'])
        _write_file_info(self.new, [b'/keep'])

        self.log()

        (message, level), _kwargs = self.sn.snapshotLog.append.call_args
        self.assertTrue(message.startswith('[C] *deleting   bad-'))
        self.assertEqual(level, 2)


class LogDeletionsOfChangedSnapshot(unittest.TestCase):
    """When deleted files are logged for a snapshot with other changes."""

    def setUp(self):
        self.sn = _snapshots_instance()
        self.prev = _FakeSnapshot('/prev/backup')
        self.new = _FakeSnapshot('/new/backup')
        patcher = mock.patch.object(
            self.sn, '_log_deleted_paths_from_file_info')
        self.log = patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, reported=True, prev='default', exit_code=0,
             has_errors=False):
        if prev == 'default':
            prev = self.prev

        return self.sn._log_deletions_of_changed_snapshot(
            reported, prev, self.new, exit_code, has_errors)

    def test_clean_run_with_changes_logs(self):
        self.assertTrue(self.call())
        self.log.assert_called_once_with(self.prev, self.new)

    def test_nothing_reported_by_rsync(self):
        """Then the check for deletions did already log them."""
        self.assertFalse(self.call(reported=False))
        self.log.assert_not_called()

    def test_first_snapshot_has_nothing_to_compare(self):
        self.assertFalse(self.call(prev=None))
        self.log.assert_not_called()

    def test_not_after_partial_transfer_or_failure(self):
        """Missing files can not be told apart from deleted ones."""
        for exit_code in (1, 12, 23, 24, 30, -9, -15):
            with self.subTest(exit_code=exit_code):
                self.assertFalse(self.call(exit_code=exit_code))

        self.log.assert_not_called()

    def test_not_if_errors_were_detected(self):
        self.assertFalse(self.call(has_errors=True))
        self.log.assert_not_called()


CONFIG = """config.version=6
profile1.name=Test
profile1.snapshots.mode=local
profile1.snapshots.path={dest}
profile1.snapshots.include.1.type=0
profile1.snapshots.include.1.value={src}
profile1.snapshots.include.size=1
profile1.snapshots.notify.enabled=false
profile1.snapshots.no_on_battery=false
profile1.snapshots.remove_old_snapshots.enabled=false
profile1.snapshots.smart_remove=false
"""

# Stands in for rsync. Kills the calling process (backintime) when the check
# for deleted files is started and runs the real rsync in all other cases.
KILLING_RSYNC = """#!/bin/sh
case "$*" in
    *--ignore-existing*) kill -9 $PPID; exit 9;;
esac
exec {rsync} "$@"
"""

COMMON_DIR = pathlib.Path(__file__).resolve().parent.parent


@unittest.skipUnless(RSYNC_AVAILABLE, 'rsync is not available')
class BackupCommandEndToEnd(unittest.TestCase):
    """The reported failure through the real command line.

    Runs ``backintime backup`` (and so Snapshots.takeSnapshot()) for a local
    profile. Everything, including HOME, is in a temporary directory. Each
    backup takes a few seconds because the command pauses between steps.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = pathlib.Path(self._tmp.name) / 'home'
        self.src = self.home / 'src'
        self.dest = self.home / 'dest'
        self.config = self.home / '.config' / 'backintime' / 'config'
        self.bin = pathlib.Path(self._tmp.name) / 'bin'

        for directory in (self.src / 'dir', self.dest, self.config.parent):
            directory.mkdir(parents=True)

        self.config.write_text(
            CONFIG.format(src=self.src, dest=self.dest), encoding='utf-8')

        for name in ('foo', 'bar', 'baz', 'dir/inner'):
            (self.src / name).write_text(name, encoding='utf-8')

    def backup(self, path=None):
        env = {
            'HOME': str(self.home),
            'XDG_DATA_HOME': str(self.home / '.local' / 'share'),
            'XDG_CONFIG_HOME': str(self.home / '.config'),
            'PATH': path or os.environ['PATH'],
            'LANG': 'C',
            'PYTHONDONTWRITEBYTECODE': '1',
        }

        return subprocess.run(
            [sys.executable, str(COMMON_DIR / 'backintime.py'),
             '--config', str(self.config), 'backup'],
            env=env, cwd=self._tmp.name, capture_output=True, text=True,
            timeout=180, check=False)

    def profile_dir(self):
        found = glob.glob(str(self.dest / 'backintime' / '*' / '*' / '1'))

        return pathlib.Path(found[0]) if found else None

    def snapshots(self):
        profile = self.profile_dir()

        if profile is None:
            return []

        return sorted(p.name for p in profile.iterdir()
                      if re.match(r'^\d{8}-\d{6}', p.name))

    def files_of(self, snapshot):
        backup = self.profile_dir() / snapshot / 'backup'

        return {str(p.relative_to(backup))
                for p in backup.rglob('*') if p.is_file()}

    def log_of(self, snapshot):
        log = self.profile_dir() / snapshot / 'takesnapshot.log.bz2'

        with bz2.open(log, 'rt', encoding='utf-8') as handle:
            return handle.read()

    def delete(self, name):
        path = self.src / name

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    def test_deletions_are_detected_and_logged(self):
        self.assertEqual(self.backup().returncode, 0)
        self.assertEqual(len(self.snapshots()), 1)

        # No regression: nothing changed, no new snapshot
        self.assertEqual(self.backup().returncode, 0)
        self.assertEqual(len(self.snapshots()), 1)

        # The reported failure: deletions are the only change
        self.delete('baz')
        self.delete('dir')
        self.assertEqual(self.backup().returncode, 0)
        snaps = self.snapshots()
        self.assertEqual(len(snaps), 2)
        self.assertEqual(
            {name for name in self.files_of(snaps[-1])
             if name.endswith(('foo', 'bar', 'baz', 'inner'))},
            {name for name in self.files_of(snaps[-1])
             if name.endswith(('foo', 'bar'))})
        log = self.log_of(snaps[-1])
        self.assertRegex(log, r'\[C\] \*deleting {3}\S*/src/baz\n')
        self.assertRegex(log, r'\[C\] \*deleting {3}\S*/src/dir/inner\n')

        # Another change besides the deletion: deletions are logged as well
        self.delete('bar')
        (self.src / 'new').write_text('new', encoding='utf-8')
        self.assertEqual(self.backup().returncode, 0)
        snaps = self.snapshots()
        self.assertEqual(len(snaps), 3)
        log = self.log_of(snaps[-1])
        self.assertRegex(log, r'\[C\] \*deleting {3}\S*/src/bar\n')
        self.assertNotIn('/src/baz', log)

    def test_interrupted_check_is_recovered(self):
        """The process is killed while the deletion check runs.

        Nothing visible is left behind. The next backup finishes the job and
        the deletion is not lost.
        """
        self.assertEqual(self.backup().returncode, 0)
        self.assertEqual(len(self.snapshots()), 1)

        self.delete('baz')

        self.bin.mkdir()
        shim = self.bin / 'rsync'
        shim.write_text(
            KILLING_RSYNC.format(rsync=shutil.which('rsync')),
            encoding='utf-8')
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR)

        killed = self.backup(path=f'{self.bin}{os.pathsep}'
                                  f'{os.environ["PATH"]}')
        self.assertLess(killed.returncode, 0)  # killed by a signal

        # No finished snapshot, only the unfinished one for the next run
        self.assertEqual(len(self.snapshots()), 1)
        self.assertTrue((self.profile_dir() / 'new_snapshot').is_dir())

        self.assertEqual(self.backup().returncode, 0)
        snaps = self.snapshots()
        self.assertEqual(len(snaps), 2)
        self.assertFalse((self.profile_dir() / 'new_snapshot').exists())
        self.assertFalse(
            any(name.endswith('baz') for name in self.files_of(snaps[-1])))
        self.assertRegex(
            self.log_of(snaps[-1]), r'\[C\] \*deleting {3}\S*/src/baz\n')


if __name__ == '__main__':
    unittest.main()
