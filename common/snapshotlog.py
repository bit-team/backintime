# Back In Time
# Copyright (C) 2016-2019 Germar Reitze
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
import gettext

import logger
import snapshots
import tools

_=gettext.gettext


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
            self.header = _('### This log has been decoded with automatic search pattern\n'\
                            '### If some paths are not decoded you can manually decode them with:\n')
            self.header +=  '### \'backintime --quiet '
            if int(decode.config.currentProfile()) > 1:
                self.header +=  '--profile "%s" ' %decode.config.profileName()
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
            int:        size of the file in bytes, ``None`` if no size was found.
        """

        has_size = False
        original_line = str(line)
        size = 0
        if line.startswith("[C]") and line.endswith("bytes]"):
            has_size = True
            start = line.find("[", 3)+1
            end = line.find(" bytes]")
            import humanfriendly
            size = int(line[start:end])
            size_hr = " ["+humanfriendly.format_size(size)+"]"
            line = line[0:start-2]

        if not line:
            #keep empty lines
            return line, None
        if self.regex and not self.regex.match(line):
            return None, None
        if self.decode:
            ret = self.decode.log(line)
            if has_size:
                ret = ret + size_hr
            return ret, size
        else:
            if has_size:
                return line + size_hr, size
            return original_line, None

class SnapshotLog(object):
    """
    Read and write Snapshot log to "~/.local/share/backintime/takesnapshot_<N>.log".
    Where <N> is the profile ID ``profile``.

    Args:
        cfg (config.Config):    current config
        profile (int):          profile that should be used to indentify the log
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

    def get(self, mode = None, decode = None, skipLines = 0, sort = 0):
        """
        Read the log, filter and decode it and yield its lines.

        Args:
            mode (int):                 Mode used for filtering. Take a look at
                                        :py:class:`snapshotlog.LogFilter`
            decode (encfstools.Decode): instance used for decoding lines or ``None``
            skipLines (int):            skip ``n`` lines before yielding lines.
                                        This is used to append only new lines
                                        to LogView
            sort (int):                 0 for no sorting, -1 for ascending filesizes,
                                        1 for descending filesizes

        Yields:
            str:                        filtered and decoded log lines
        """
        logFilter = LogFilter(mode, decode)
        count = logFilter.header.count('\n')
        result = []
        order = []
        try:
            with open(self.logFileName, 'rt') as f:
                if logFilter.header and not skipLines:
                    result.append(logFilter.header)
                for line in f.readlines():
                    line, size = logFilter.filter(line.rstrip('\n'))
                    if size is None:
                        size = 0
                    if not line is None:
                        count += 1
                        if count <= skipLines:
                            continue
                        order.append((size, line))

                if sort < 0:
                    order = sorted(order)
                elif sort > 0:
                    order = sorted(order, reverse=True)
                for i in order:
                    result.append(i[1])
        except Exception as e:
            msg = ('Failed to get take_snapshot log from {}:'.format(self.logFile), str(e))
            logger.debug(' '.join(msg), self)
            for line in msg:
                result.append(line)
        for i in result:
            yield i

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
                            Posible Values:
                            :py:data:`SnapshotLog.ERRORS`,
                            :py:data:`SnapshotLog.CHANGES_AND_ERRORS` or
                            :py:data:`SnapshotLog.ALL`
        """
        if level > self.logLevel:
            return
        if not self.logFile:
            self.logFile = open(self.logFileName, 'at')
        self.logFile.write(msg + '\n')
        self.timer.start(5)

    def flush(self):
        """
        Force write log to file.
        """
        if self.logFile:
            self.logFile.flush()
