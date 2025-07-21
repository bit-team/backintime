# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Constants and logic related to license and copyright information.

That module is separated from bitbase.py because it contain translatable
strings but bitbase is not able to provide it."""
from pathlib import Path
import bitbase

COPYRIGHT = 'Copyright © 2008-2024 ' \
            'Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze\n' \
            'Copyright © 2022 ' \
            'Christian Buhtz, Michael Büker, Jürgen Altfeld'


URL_GPL_TWO = 'https://spdx.org/licenses/GPL-2.0-or-later.html'


def get_gpl_short_text(href: str = None) -> str:
    """Short description of primary license.

    The string is used in the AboutDialog and when using --license on shell.

    Dev note (buhtz, 2025-03): That string is untranslated on purpose.
    It is legally relevant, and no one should be given the opportunity
    to change the string—whether intentionally or accidentally.
    """

    gpl = 'GNU General Public License v2.0 or later (GPL-2.0-or-later)'

    if href:
        gpl = f'<a href="{href}">{gpl}</a>'

    return f'The application is released under {gpl}.'


TXT_LICENSES = _(
    'All licenses used in this project are located in the {dir_link} '
    'directory. To extract per-file license and copyright information '
    'using SPDX metadata, refer to {readme_link}.')


def _determine_licenses_dir() -> str | None:
    for pkg in (bitbase.PACKAGE_NAME_GUI,
                bitbase.PACKAGE_NAME_CLI,
                bitbase.BINARY_NAME_GUI,
                bitbase.BINARY_NAME_CLI,
                bitbase.BINARY_NAME_BASE):
        for path in (Path('/usr/share/doc'), Path('/usr/share/licenses')):

            fp = path / pkg / 'LICENSES'
            if fp.is_dir():
                return fp

    return None


DIR_LICENSES = _determine_licenses_dir()
