# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
from pathlib import Path


class FlockContext:
    """
    """
    def __init__(self, filenname: str, folder: Path = None):
        # default
        if folder is None:
            folder = Path(Path.cwd().root) / 'run' / 'lock'

            # out-dated default
            if not folder.exists():
                folder = Path(Path.cwd().root) / 'var' / 'lock'


        # Script start
        self.script_name = pathlib.Path(the_file)
        self.console_log_level=console_log_level

        if self.script_name.is_absolute():
            self.script_name = self.script_name.relative_to(pathlib.Path.cwd())

    def __enter__(self):
        # Logging
        buhtzology.setup_logging(
            console_level=self.console_log_level,
            file_level=logging.DEBUG)

        self._message_start()
        self._message_version_infos()

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._message_finish()
