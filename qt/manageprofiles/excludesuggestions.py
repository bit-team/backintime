# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The widget ..."""
from __future__ import annotations
from PyQt6.QtWidgets import (QDialog,
                             QDialogButtonBox,
                             QVBoxLayout,
                             QPushButton)
import bitbase
from manageprofiles.sectionedchecklist import SectionedCheckList
import qttools

EXCLUDE_SUGGESTIONS: dict[str, tuple[list[str, str, bool], ...]]
"""
Commonly used exclude patterns grouped by category.

Example:

    {
        'Group name': (
            ('file', 'File, by default selected', True),
            ('directory', 'Directory, not selected by default', False),
            ('pattern', 'Pattern, not selected by default', False),
        )
    }
"""
EXCLUDE_SUGGESTIONS = {
    _('Editor & Office temporary files'): (
        ['*~', _('Emacs backup files'), False],
        ['#*#', _('Emacs autosave files'), True],
        ['*.swp', _('Vim swap files'), True],
        ['~$*', _('Microsoft Office temporary files'), True],
        [
            '.~lock.*#',
            _('LibreOffice & other OpenDocument Editors lock files'),
            True
        ],
    ),
    _('Thumbnails & Temporary Pictures'): (
        [
            '.thumbnails*',
            _("Thumbnail cache on GNU/Linux and other unixoid OS'es"),
            True
         ],
        ['Thumbs.db', _('Thumbnail database on Windows'), False],
        ['.DS_Store', _('Metadata directory on MacOS'), False],
    ),
    _('Application-specific locks'): (
        # Discord files. See also: https://github.com/bit-team/backintime
        # /issues/1555#issuecomment-1787230708
        ['SingletonLock', _('Discord application lock file'), False],
        ['SingletonCookie', _('Discord session lock file'), False],
        # Mozilla file. See also: https://github.com/bit-team/backintime
        # /issues/1555#issuecomment-1787111063
        ['lock', _('Mozilla Firefox & Thunderbird lock file'), False],
    ),
    _('Caches & Temporary directories'): (
        ['.cache/*', _('User application cache'), True],
        ['/tmp/*', _('System temporary directory'), bitbase.IS_IN_ROOT_MODE],
        [
            '/var/tmp/*',
            _('System temporary directory'),
            bitbase.IS_IN_ROOT_MODE
        ],
        [
            '/var/cache/apt/archives/*.deb',
            _('Package cache for Debian(-based) GNU/Linux distributions'),
            bitbase.IS_IN_ROOT_MODE
        ],
    ),
    _('System runtime directories'): (
        [
            '/proc/*',
            _('Kernel and process information'),
            bitbase.IS_IN_ROOT_MODE
        ],
        [
            '/sys/*',
            _('Device and other hardware information (sysfs interface)'),
            bitbase.IS_IN_ROOT_MODE
        ],
        ['/dev/*', _('Device nodes'), bitbase.IS_IN_ROOT_MODE],
        ['/run/*', _('Runtime system files'), bitbase.IS_IN_ROOT_MODE],
    ),
    _('Other non-persistent'): (
        [
            '/etc/mtab',
            _('List of currently mounted filesystems'),
            bitbase.IS_IN_ROOT_MODE
        ],
        ['/swapfile', _('System swap file (virtual memory)'), True],
        ['.gvfs', _('GNOME virtual file system mount point'), True],
        ['lost+found/*', _('Recovered filesystem objects'), True],
    ),
    _('Miscellaneous'): (
        [
            'System Volume Information',
            _('Metadata directory on Microsoft Windows'),
            False
        ],
        ['.local/share/[Tt]rash*', _('User recycle bin'), True],
        ['/var/backups/*', _('System backup files'), bitbase.IS_IN_ROOT_MODE],
    ),
}


class ExcludeSuggestionsDialog(QDialog):
    """A dialog suggesting entries for the exclude list.

    Args:
        content: See `bitbase.EXCLUDE_SUGGESTIONS` for example format.
    """

    def __init__(self, parent: QDialog, content: dict):
        super().__init__(parent)
        self.setWindowTitle(_('Exclude Suggetions'))

        layout = QVBoxLayout()
        self.setLayout(layout)

        txt = _('Select commonly used items to add to backup exclusions.')
        layout.addWidget(qttools.create_info_label(txt))

        self._wdg_list = SectionedCheckList(self, 2)
        layout.addWidget(self._wdg_list)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        btn_default = QPushButton(_('Default'))
        btn_default.setToolTip(_('Reset to predefined selection'))
        btn_default.clicked.connect(self._slot_reset_default)
        btn_box.addButton(btn_default, QDialogButtonBox.ButtonRole.ActionRole)

        layout.addWidget(btn_box)

        self._wdg_list.add_content(content)

    def _slot_reset_default(self):
        self._wdg_list.clear()
        self._wdg_list.add_content(EXCLUDE_SUGGESTIONS)

    def get_checked_and_unchecked(self) -> tuple[list[str], list[str]]:
        """Return two lists of checked and unchecked excludes."""
        return self._wdg_list.get_entry_stings_separated_by_state()
