# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""The About dialog."""
import re
import pathlib
from PyQt6.QtWidgets import (QLabel,
                             QVBoxLayout,
                             QHBoxLayout,
                             QDialog,
                             QDialogButtonBox)
from PyQt6.QtCore import Qt, QSize
import tools
import backintime
import messagebox


class AboutDlg(QDialog):
    """The about dialog accessible from the Help menu in the main window."""

    def __init__(self, parent=None):
        """Initialize and layout."""
        super().__init__(parent)

        self.parent = parent
        self.config = parent.config

        import icon  # pylint: disable=import-outside-toplevel

        self.setWindowTitle(_('About') + ' ' + self.config.APP_NAME)
        logo = QLabel('Icon')
        logo.setPixmap(icon.BIT_LOGO.pixmap(QSize(48, 48)))

        name = self._create_name_and_version_label()

        homepage = QLabel(
            self._to_a_href('https://github.com/bit-team/backintime'))
        homepage.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse)
        homepage.setOpenExternalLinks(True)

        bit_copyright = QLabel(self.config.COPYRIGHT + '\n')

        vlayout = QVBoxLayout(self)
        hlayout = QHBoxLayout()
        hlayout.addWidget(logo)
        hlayout.addWidget(name)
        hlayout.addStretch()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(homepage)
        vlayout.addWidget(bit_copyright)

        button_box_left = QDialogButtonBox(self)
        for label, slot in ((_('Authors'), self._msgbox_authors),
                            (_('Translations'), self._msgbox_translations),
                            (_('License'), self._msgbox_license)):
            btn = button_box_left.addButton(
                label, QDialogButtonBox.ButtonRole.ActionRole)
            btn.clicked.connect(slot)

        button_box_right = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box_right.accepted.connect(self.accept)

        hlayout = QHBoxLayout()
        hlayout.addWidget(button_box_left)
        hlayout.addWidget(button_box_right)
        vlayout.addLayout(hlayout)

    def _create_name_and_version_label(self):
        version = backintime.__version__
        info = tools.get_git_repository_info(
            # should be the repos root folder
            path=pathlib.Path(__file__).parent.parent,
            hash_length=8)
        try:
            git_version \
                = f" git branch '{info['branch']}' hash '{info['hash']}'"
        except TypeError:
            git_version = ''

        name = QLabel(
            f'<h1>{self.config.APP_NAME} {version}</h1>{git_version}')
        name.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        return name

    def _msgbox_authors(self):
        file_path = pathlib.Path(tools.docPath()) / 'AUTHORS'
        content = self._read_about_content(file_path)

        return messagebox.showInfo(self, _('Authors'), content)

    def _msgbox_translations(self):
        file_path = pathlib.Path(tools.docPath()) / 'TRANSLATIONS'
        content = self._read_about_content(file_path)

        return messagebox.showInfo(self, _('Translations'), content)

    def _msgbox_license(self):
        file_path = pathlib.Path(tools.docPath()) / 'LICENSE'
        content = self._read_about_content(file_path)

        return messagebox.showInfo(self, _('License'), content)

    def _read_about_content(self, file_path):
        content = file_path.read_text('utf-8')

        # Convert URLs and Email into <a href>
        content = re.sub(r'<(.*?)>', self._to_a_href, content)

        # HTML line breaks
        content = re.sub(r'\n', '<br>', content)

        return content

    def _to_a_href(self, m):
        """Create a HTML a-tag out of Website and EMail URIs.

        Args:
            m (str, re.Match): Match or string to convert.

        Examples:
            - 'https://foo.bar' becomes
              '<a href="https://foo.bar">https://foo.bar</a>'
            - 'foo@bar.com' becomes
             '<a href="mailto:foo@bar.com">foo@bar.com</a>'
        """
        try:
            raw_string = m.group(1)
        except AttributeError:
            raw_string = m

        if '@' in raw_string:
            return f'<a href="mailto:{raw_string}">{raw_string}</a>'

        return f'<a href="{raw_string}">{raw_string}</a>'
