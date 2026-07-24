# SPDX-FileCopyrightText: © 2016-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Handling log files specific for each backup (aka snapshot).
"""
import os
import re
from collections.abc import Iterator
import logger
import snapshots
import tools


class LogFilter:  # pylint: disable=too-few-public-methods
    """
    A Filter for snapshot logs which will both decode log lines and filter them
    for the requested ``mode``.

    Args:
        mode (int): which filter should be used. Possible values:
            :py:data:`NO_FILTER`,
            :py:data:`ERROR`,
            :py:data:`CHANGES`,
            :py:data:`INFORMATION` or
            :py:data:`ERROR_AND_CHANGES`
        decode (Decode): instance used for decoding lines or ``None``
    """

    # Dev note: Better use an enumeration
    NO_FILTER = 0
    ERROR = 1
    CHANGES = 2
    INFORMATION = 3
    ERROR_AND_CHANGES = 4
    RSYNC_TRANSFER_FAILURES = 5

    # Regular expressions used for filtering log file lines.
    # RegExp syntax see: https://docs.python.org/3.10/library/
    # re.html#regular-expression-syntax
    # (?:...) = the matched substring cannot be retrieved in a
    # group (non-capturing)
    REGEX = {
        None: None,
        NO_FILTER: None,
        ERROR: re.compile(r'^(?:\[E\]|[^\[])'),
        CHANGES: re.compile(r'^(?:\[C\]|[^\[])'),
        INFORMATION: re.compile(r'^(?:\[I\]|[^\[])'),
        ERROR_AND_CHANGES: re.compile(r'^(?:\[E\]|\[C\]|[^\[])'),
        RSYNC_TRANSFER_FAILURES: re.compile(
             # All links to rsync's source reference the commit 2f9b963
             # from Jun 27, 2023 (most-recent commit on "master" as at Jan
             # 28, 2024)
             # base-ref: https://github.com/WayneD/rsync/blob/2f9b963a
             r'.*(?:'
             r'Invalid cross-device link'  # not directly contained in rsync's
                                           # source code but may be caught and
                                           # passed through as-is
             r'|symlink has no referent'  # flist.c#L1281
             r'|readlink_stat\(.?\) failed'  # flist.c#L1294
             r'|link_stat .* failed'  # flist.c#L1810
             r'|receive_sums failed'  # sender.c#L347
             r'|send_files failed to open'  # sender.c#L361
             r'|fstat failed'  # sender.c#L373
             r'|read errors mapping'  # sender.c#L435
             r'|change_dir .* failed'  # main.c#L749, #L807, #L827, #L1161
             r'|skipping overly long name'    # flist.c#L1247
             r'|skipping file with bogus \(zero\) st_mode'  # flist.c#L1300
             r'|skipping symlink with 0-length value'  # flist.c#L1569
             r'|cannot convert filename'  # flist.c#L748, #L1599
             r'|cannot convert symlink data for'  # flist.c#L1144, #L1613
             r'|opendir .* failed'  # flist.c#L1842
             r'|filename overflows max-path len by'  # flist.c#L1868
             r'|cannot send file with empty name in'  # flist.c#L1876
             r'|readdir\(.*\)'  # flist.c#L1888
             # exclude.c#L817
             r'|cannot add local filter rules in long-named directory'
             r'|failed to re-read xattr'  # xattrs.c#L662
             r'|Skipping sender remove of destination file'  # sender.c#L152
             r'|Skipping sender remove for changed file'  # sender.c#L161
             r'|could not make way for'  # delete.c#L220
             r'|system says the ACL I packed is invalid'  # acls.c#L435
             r'|recv_acl_access: value out of range'  # acls.c#L689
             r'|recv_acl_index: .* ACL index'  # acls.c#L739
             r'|Create time value of .* truncated on receiver'  # flist.c#L858
             r'|FATAL I/O ERROR: dying to avoid a \-\-delete'  # flist.c#L2005
             r'|IO error encountered'  # generator.c#L295
             r'|some files/attrs were not transferred'  # log.c#L97
             r'|temporary filename too long'  # receiver.c#L138
             r'|No batched update for'  # receiver.c#L456
             r'|recv_files: .* is a directory'  # receiver.c#L805
             r'|no ftruncate for over-long pre-alloc'  # util1.c#L438
             r'|daemon refused to receive'  # generator.c#L1270
             r'|get_xattr_data: lgetxattr'  # xattrs.c#L199, #L215
             # r').*'  # no need to match the remainder of the line
             r')'
             )}

    def __init__(self, mode=0, decode=None):
        self.regex = self.REGEX[mode]
        self.decode = decode
        self.header = self._header()

    def _header(self) -> str:
        if not self.decode:
            return ''

        header = (
            '### This log has been decoded with automatic search pattern\n'
            '### If some paths are not decoded you can manually decode '
            'them with:\n'
            '### \'backintime --quiet '
        )

        # if int(self.decode.config.currentProfile()) > 1:
        header = header + f'--profile {self.decode.config.profileName()}'

        header = header + '--decode <path>\'\n\n'

        return header

    def filter(self, line: str) -> str | None:
        """Filter and decode ``line`` with predefined ``mode`` and
        ``decode`` instance.

        Args:
            line: log line read from disk

        Returns:
            Decoded ``line`` or ``None`` if the line was filtered.
        """
        if not line:
            # keep empty lines
            return line

        if self.regex and not self.regex.match(line):
            return None

        if self.decode:
            return self.decode.log(line)

        return line


class SnapshotLog:
    """
    Read and write Snapshot log to
    "~/.local/share/backintime/takesnapshot_<N>.log".
    Where <N> is the profile ID ``profile``.

    Args:
        cfg (config.Config): current config
        profile (int): profile that should be used to identify the log
    """

    NONE = 0
    ERRORS = 1
    CHANGES_AND_ERRORS = 2
    ALL = 3

    def __init__(self, cfg, profile=None):
        # pylint: disable-next=invalid-name
        self.logFile = None

        self.config = cfg

        if profile:
            self.profile = profile
        else:
            self.profile = cfg.currentProfile()

        # pylint: disable-next=invalid-name
        self.logLevel = cfg.logLevel()
        # pylint: disable-next=invalid-name
        self.logFileName = cfg.takeSnapshotLogFile(self.profile)

        self.timer = tools.Alarm(self.flush, overwrite=False)

    def __del__(self):
        if self.logFile:
            self.logFile.close()

    def get(self,
            mode: int = None,
            decode=None,
            skipLines: int = 0  # pylint: disable=invalid-name # noqa: N803
            ) -> Iterator[str]:

        """Read the log, filter and decode it and yield its lines.

        Args:
            mode: Mode used for filtering. See `snapshotlog.LogFilter`
            decode (Decode): Instance used for decoding lines.
            skipLines: Number of lines to skip before yielding. This is used
                to append only new lines to LogView.

        Yields:
            Filtered and decoded log lines.
        """
        # pylint: disable-next=invalid-name
        logFilter = LogFilter(mode, decode)  # noqa: N806
        count = logFilter.header.count('\n')

        try:
            with open(self.logFileName, mode='rt', encoding='utf-8') as f:

                if logFilter.header and not skipLines:
                    yield logFilter.header

                for line in f.readlines():
                    line = logFilter.filter(line.rstrip('\n'))

                    if line is not None:
                        count += 1

                        if count <= skipLines:
                            continue

                        yield line

        except Exception as exc:  # pylint: disable=broad-exception-caught
            msg = (
                f'Failed to get take_snapshot log from {self.logFile}:',
                str(exc)
            )
            logger.debug(' '.join(msg), self)

            for line in msg:  # pylint: disable=use-yield-from
                # Why???
                yield line

    def new(self, date, mounted_path):
        """
        Create a new log file or - if the last new_snapshot can be continued -
        add a note to the current log.

        Args:
            date (datetime.datetime):   current date
        """
        if snapshots.NewSnapshot(self.config, mounted_path).saveToContinue:
            msg = "Last backup did not complete but can be resumed.\n\n"
            msg += "======== Continue backup (profile %s): %s ========\n"

        else:
            if os.path.exists(self.logFileName):
                if self.logFile:
                    self.logFile.close()
                    self.logFile = None
                os.remove(self.logFileName)
            msg = "========== Create backup (profile %s): %s ==========\n"

        self.append(msg % (self.profile, date.strftime('%c')), 1)

    def append(self, msg, level):
        """
        Append ``msg`` to the log if ``level`` is lower than configured log
        level.

        Args:
            msg (str): message line that should be added to the log
            level (int): verbosity level of current line. msg will only be
               added to log if level is lower than configured
               log level :py:func:`config.Config.logLevel`.
               Possible Values:
               :py:data:`SnapshotLog.ERRORS`,
               :py:data:`SnapshotLog.CHANGES_AND_ERRORS` or
               :py:data:`SnapshotLog.ALL`
        """
        if level > self.logLevel:
            return

        if not self.logFile:
            # pylint: disable-next=consider-using-with
            self.logFile = open(self.logFileName, mode='at', encoding='utf-8')

        self.logFile.write(msg + '\n')
        self.timer.start(5)  # flush the log output buffer after 5 seconds

    def flush(self):
        """
        Write the in-memory buffer of the log output into the log file.
        """
        if self.logFile:
            try:
                # Dev note: flush() does not necessarily write the file’s data
                # to disk. Use flush() followed by os.fsync() to ensure this
                # behavior.
                # https://docs.python.org/2/library/stdtypes.html#file.flush
                self.logFile.flush()

            except RuntimeError:
                # Fixes #1003 (RTE reentrant call inside io.BufferedWriter)
                # This RTE will not be logged since this would be another
                # reentrant call
                pass
