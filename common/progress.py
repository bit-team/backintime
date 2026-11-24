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

# rsync --info=progress2 output
# search for:     517.38K  26%   14.46MB/s    0:02:36
# or:             497.84M   4% -449.39kB/s   ??:??:??
# but filter out: 517.38K  26%   14.46MB/s    0:00:53 (xfr#53, to-chk=169/452)
#                 because this shows current run time
REX_RSYNC_PROGRESS = re.compile(
    # trash at start
    r'.*?'
    # bytes sent
    r'(\d*[,\.]?\d+(?:[KkMGT](?:i?B)?|B)?)\s+'
    # percent done
    r'(\d*)%\s+'
    # speed
    r'(-?\d*[,\.]?\d*(?:[KkMGT](?:i?B)?|B)/s)\s+'
    # estimated time of arrival
    r'([\d\?]+:[\d\?]{2}:[\d\?]{2})'
    # trash at the end
    r'(.*$)'
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

    If multiple lines (strings with newline) are given no errors is raised,
    only the first line is considered and the rest will be lost silently.

    Args:
        line: A progress line catched from rsync's stdout.

    Returns:
        A dictionary with results or `None` in case of problems.
    """
    matched = REX_RSYNC_PROGRESS.match(line)

    if not matched:
        return None

    return {
        'sent': matched.group(1),
        'percent': int(matched.group(2)),
        'speed': matched.group(3),
        'eta': matched.group(4),
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
