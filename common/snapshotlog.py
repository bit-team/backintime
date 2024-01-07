# Back In Time
# Copyright (C) 2016-2022 Germar Reitze
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import re

import logger
import snapshots
import tools


class LogFilter(object):
    """
    A Filter for snapshot logs which will both decode log lines and filter them
    for the requested ``mode``.

    Args:
        mode (int):                 which filter should be used.
                                    Possible values:
                                    :py:data:`NO_FILTER`,
                                    :py:data:`ERROR`,
                                    :py:data:`CHANGES`,
                                    :py:data:`INFORMATION` or
                                    :py:data:`ERROR_AND_CHANGES`
        decode (encfstools.Decode): instance used for decoding lines or ``None``
    """
    NO_FILTER =         0
    ERROR =             1
    CHANGES =           2
    INFORMATION =       3
    ERROR_AND_CHANGES = 4

    REGEX = {None:              None,
             NO_FILTER:         None,
             ERROR:             re.compile(r'^(?:\[E\]|[^\[])'),
             CHANGES:           re.compile(r'^(?:\[C\]|[^\[])'),
             INFORMATION:       re.compile(r'^(?:\[I\]|[^\[])'),
             ERROR_AND_CHANGES: re.compile(r'^(?:\[E\]|\[C\]|[^\[])')}

    def __init__(self, mode = 0, decode = None):
        self.regex = self.REGEX[mode]
        self.decode = decode

        if decode:
            self.header = (
                '### This log has been decoded with automatic search pattern\n'
                '### If some paths are not decoded you can manually decode '
                'them with:\n'
                '### \'backintime --quiet '
            )

            if int(decode.config.currentProfile()) > 1:
                self.header +=  '--profile "%s" ' % decode.config.profileName()
            self.header +=  '--decode <path>\'\n\n'

        else:
            self.header = ''

    def filter(self, line):
        """
        Filter and decode ``line`` with predefined ``mode`` and
        ``decode`` instance.

        Args:
            line (str): log line read from disk

        Returns:
            str:        decoded ``line`` or ``None`` if the line was filtered
        """
        if not line:
            #keep empty lines
            return line
        if self.regex and not self.regex.match(line):
            return
        if self.decode:
            return self.decode.log(line)
        else:
            return line

class SnapshotLog(object):
    """
    Read and write Snapshot log to "~/.local/share/backintime/takesnapshot_<N>.log".
    Where <N> is the profile ID ``profile``.

    Args:
        cfg (config.Config):    current config
        profile (int):          profile that should be used to identify the log
    """

    NONE                = 0
    ERRORS              = 1
    CHANGES_AND_ERRORS  = 2
    ALL                 = 3

    def __init__(self, cfg, profile = None):
        self.config = cfg
        if profile:
            self.profile = profile
        else:
            self.profile = cfg.currentProfile()
        self.logLevel = cfg.logLevel()
        self.logFileName = cfg.takeSnapshotLogFile(self.profile)
        self.logFile = None

        self.timer = tools.Alarm(self.flush, overwrite = False)

    def __del__(self):
        if self.logFile:
            self.logFile.close()

    def get(self, mode = None, decode = None, skipLines = 0):
        """
        Read the log, filter and decode it and yield its lines.

        Args:
            mode (int):                 Mode used for filtering. Take a look at
                                        :py:class:`snapshotlog.LogFilter`
            decode (encfstools.Decode): instance used for decoding lines or ``None``
            skipLines (int):            skip ``n`` lines before yielding lines.
                                        This is used to append only new lines
                                        to LogView

        Yields:
            str:                        filtered and decoded log lines
        """
        logFilter = LogFilter(mode, decode)
        count = logFilter.header.count('\n')
        try:
            with open(self.logFileName, 'rt') as f:
                if logFilter.header and not skipLines:
                    yield logFilter.header
                for line in f.readlines():
                    line = logFilter.filter(line.rstrip('\n'))
                    if not line is None:
                        count += 1
                        if count <= skipLines:
                            continue
                        yield line
        except Exception as e:
            msg = ('Failed to get take_snapshot log from {}:'.format(self.logFile), str(e))
            logger.debug(' '.join(msg), self)
            for line in msg:
                yield line

    def new(self, date):
        """
        Create a new log file or - if the last new_snapshot can be continued -
        add a note to the current log.

        Args:
            date (datetime.datetime):   current date
        """
        if snapshots.NewSnapshot(self.config).saveToContinue:
            msg  = "Last snapshot didn't finish but can be continued.\n\n"
            msg += "======== continue snapshot (profile %s): %s ========\n"
        else:
            if os.path.exists(self.logFileName):
                if self.logFile:
                    self.logFile.close()
                    self.logFile = None
                os.remove(self.logFileName)
            msg = "========== Take snapshot (profile %s): %s ==========\n"
        self.append(msg %(self.profile, date.strftime('%c')), 1)

    def append(self, msg, level):
        """
        Append ``msg`` to the log if ``level`` is lower than configured log level.

        Args:
            msg (str):      message line that should be added to the log
            level (int):    verbosity level of current line. msg will only be
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
            self.logFile = open(self.logFileName, 'at')
        self.logFile.write(msg + '\n')
        self.timer.start(5)  # flush the log output buffer after 5 seconds

    def flush(self):
        """
        Write the in-memory buffer of the log output into the log file.
        """
        if self.logFile:
            try:
                # TODO flush() does not necessarily write the file’s data to disk.
                #      Use flush() followed by os.fsync() to ensure this behavior.
                #      https://docs.python.org/2/library/stdtypes.html#file.flush
                self.logFile.flush()
            except RuntimeError as e:
                # Fixes #1003 (RTE reentrant call inside io.BufferedWriter)
                # This RTE will not be logged since this would be another reentrant call
                pass
