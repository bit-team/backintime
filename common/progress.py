# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import re
import configfile
from config import Config
import logger

# Parsing rsync --info=progress2 output. Option "--humand-readable" need to be
# set.
# Examples:
# 517.38K  26%   14.46MB/s    0:02:36
# 497.84M   4% -449.39kB/s   ??:??:??
# 10,86G  99% 10115,73GB/s    0:00:00 (xfr#326, to-chk=0/388)
# 517.38K  26%   14.46MB/s    0:00:53 (xfr#53, ir-chk=169/452)
# Ask regex101.com to understand details about that pattern.
REX_RSYNC_PROGRESS = re.compile(
    # trash at start
    r'.*?'
    # bytes sent
    r'(\d*(?:[,\.]?\d+)*(?:[KkMGT](?:i?B)?|B)?)\s+'
    # percent done
    r'(\d+)%\s+'
    # speed
    r'(-?\d+(?:[,\.]\d+)*(?:[KkMGT](?:i?B)?|B)/s)\s+'
    # estimated time (or elapsed time, see next group)
    r'([\d\?]+:[\d\?]{2}:[\d\?]{2})'
    # optional suffix, e.g. (xfr#53, to-chk=169/542)
    r'(?:\s+\(xfr#\d+, (to|ir)-chk=\d+/\d+\))?'
)


class ProgressFile(configfile.ConfigFile):

    # ???
    RSYNC = 50

    def __init__(self, cfg, filename=None):
        super(ProgressFile, self).__init__()
        self.config = cfg
        self.filename = filename

        if self.filename is None:
            self.filename = self.config.takeSnapshotProgressFile()

    def save(self):
        return super(ProgressFile, self).save(self.filename)

    def load(self):
        return super(ProgressFile, self).load(self.filename)

    def fileReadable(self):
        return os.access(self.filename, os.R_OK)


def parse_rsync_progress(line: str) -> dict | None:
    """Parse an rsync progress line.

    Only the first line is parsed. Any content after a new line is silently
    ignored without raising an exception.

    Args:
        line: A progress line caught from rsync's stdout.

    Returns:
        A dictionary with results or `None` in case of problems.
    """
    matched = REX_RSYNC_PROGRESS.match(line)

    if not matched:
        return None

    # In case of "to-chk" the timefield is rejected because it can not clearly
    # be interpreted.
    eta = '??:??:??' if matched.group(5) == 'to' else matched.group(4)

    return {
        'sent': matched.group(1),
        'percent': int(matched.group(2)),
        'speed': matched.group(3),
        'eta': eta,
    }


def write_to_progress_file(progress_info: dict,
                           cfg: Config):
    """
    Dev note (2026-11, buhtz): 'Config' will be gone soon.
    """

    pg = ProgressFile(cfg)

    try:
        pg.setIntValue('status', pg.RSYNC)  # ???
        pg.setStrValue('sent', progress_info['sent'])
        pg.setIntValue('percent', progress_info['percent'])
        pg.setStrValue('speed', progress_info['speed'])
        pg.setStrValue('eta', progress_info['eta'])

    except KeyError as exc:
        logger.error(
            'Unexpected error while writing rsync progress info to progress '
            f'file "{pg.filename}". Progress info: {progress_info}. '
            f'Exception: {exc}'
        )
        pass

    else:
        pg.save()
