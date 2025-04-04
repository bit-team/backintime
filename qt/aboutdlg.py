# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2025 Christian BUTHZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The About dialog."""
import re
import pathlib
from PyQt6.QtWidgets import (QDialog,
                             QDialogButtonBox,
                             QFrame,
                             QHBoxLayout,
                             QLabel,
                             QPushButton,
                             # QSizePolicy,
                             QStyle,
                             QVBoxLayout,
                             QWidget)
from PyQt6.QtCore import Qt  # , QSize
import bitbase
import tools
import backintime
import messagebox
import qttools


class AboutDlg(QDialog):
    """The about dialog accessible from the Help menu in the main window."""

    def __init__(self, parent=None):
        """Initialize and layout."""
        super().__init__(parent)
        self.setWindowTitle(_('About Back In Time'))

        main_hbox = QHBoxLayout(self)

        left_box = QVBoxLayout()
        right_box = QVBoxLayout()
        main_hbox.addLayout(left_box, 0)
        main_hbox.addLayout(right_box, 1)

        left_box.addWidget(self._create_logo_widget())
        left_box.addLayout(self._project_buttons())
        left_box.addStretch(1)

        top_right = QHBoxLayout()
        top_right.addWidget(self._create_name_info(), 0)
        top_right.addStretch(1)

        right_box.addLayout(top_right)
        right_box.addStretch(1)
        right_box.addWidget(self._create_ok_button())

        """
        The application is released under GNU General Public License v2.0 or
        later (GPL-2.0-or-later).  <https://spdx.org/licenses/GPL-2.0-or-later.html>.
        See LICENSES directory for further details and to find out how to
        obtain detailed per-file license and copyright information using SPDX
        meta data.
        """

    def _project_buttons(self):
        layout = QVBoxLayout()

        website = QPushButton(_('Website'))
        website.setToolTip(bitbase.URL_WEBSITE.replace('https://', ''))
        website.clicked.connect(qttools.open_website)

        manual = QPushButton(_('User manual'))
        manual.setToolTip(_('Open user manual in browser (local if available '
                            'otherwise online)'))
        manual.clicked.connect(qttools.open_user_manual)

        layout.addWidget(website)
        layout.addWidget(manual)
        layout.addStretch(1)

        hbox = QHBoxLayout(self)
        hbox.addStretch(1)
        hbox.addLayout(layout, 2)
        hbox.addStretch(1)

        return hbox

    def _create_logo_widget(self):
        import icon  # pylint: disable=import-outside-toplevel

        size = self.style().pixelMetric(
            QStyle.PixelMetric.PM_LargeIconSize)
        logo = icon.BIT_LOGO.pixmap(size*6)

        label = QLabel(self)
        label.setPixmap(logo)

        return label

    def _create_ok_button(self):
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        return button_box

    def _create_name_info(self):
        wdg = QWidget(self)
        vbox = QVBoxLayout(wdg)

        # Experiment. This comment might appear on Weblate at context info.
        # Does it?
        name = QLabel(_('Back In Time'))
        name.setFrameStyle(QFrame.Shape.Box| QFrame.Shadow.Sunken)
        name.setLineWidth(3)
        font = name.font()
        font.setPointSizeF(font.pointSizeF() * 4)
        font.setBold(True)
        name.setFont(font)

        vbox.addWidget(name)
        vbox.addWidget(self._create_version_label())
        git = self._create_git_label()
        if git:
            vbox.addWidget(git)
        vbox.addStretch(1)

        return wdg

    def _foobar(self):
        self.parent = parent
        self.config = parent.config

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

    def _create_version_label(self):
        return QLabel(
            _('{BOLD}Version{BOLDEND}: {version}').format(
                BOLD='<strong>',
                BOLDEND='</strong>',
                version=backintime.__version__)
        )

    def _create_git_label(self):
        info = tools.get_git_repository_info(
            # should be the repos root folder
            path=pathlib.Path(__file__).parent.parent,
            hash_length=8)

        try:
            branch, hash = info['branch'], info['hash']
        except TypeError:
            return None

        return QLabel(f'<strong>Git</strong>: branch {branch} | hash {hash}')

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
