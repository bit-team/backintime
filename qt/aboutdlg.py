"""The About dialog."""
# Back In Time
# Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey,
# Germar Reitze
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
import re
import pathlib
from PyQt6.QtWidgets import (QLabel,
                             QVBoxLayout,
                             QHBoxLayout,
                             QDialog,
                             QDialogButtonBox)
from PyQt6.QtCore import Qt, QSize
import tools
import messagebox


class AboutDlg(QDialog):  # pylint: disable=too-few-public-methods
    """The about dialog accessible from the Help menu in the main window."""

    def __init__(self, parent=None):
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
        version = self.config.VERSION
        ref, hashid = tools.gitRevisionAndHash()
        git_version = f" git branch '{ref}' hash '{hashid}'" if ref else ''

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
        #

        try:
            raw_string = m.group(1)
        except AttributeError:
            raw_string = m

        if '@' in raw_string:
            return f'<a href="mailto:{raw_string}">{raw_string}</a>'

        return f'<a href="{raw_string}">{raw_string}</a>'
