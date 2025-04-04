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
import subprocess
from pathlib import Path
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
import logger
import bitbase
import tools
import backintime
import messagebox
import qttools

_HREF_LICENSES_DIR = 'LICENSES-dir'
_HREF_SPDX_GPL = 'spdx-gplv2'


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

        left_box.addWidget(self._create_logo_widget(),
                           alignment=Qt.AlignmentFlag.AlignHCenter)

        left_box.addWidget(self._create_license())
        left_box.addStretch(1)
        left_box.addWidget(self._project_buttons())

        top_right = QHBoxLayout()
        top_right.addWidget(self._create_name_info())

        right_box.addLayout(top_right)
        right_box.addStretch(1)
        right_box.addWidget(self._create_ok_button())

    def _create_license(self):
        license = QLabel(
            '<p>The application is released under '
            f'<a href="{_HREF_SPDX_GPL}">'
            'GNU General Public License v2.0 or later (GPL-2.0-or-later)'
            '</a>.</p>'
            '<p>Refere to the '
            f'<a href="{_HREF_LICENSES_DIR}">LICENSES directory</a> '
            'for details on obtaining '
            'license and copyright information for each file using '
            'using SPDX metadata.</p>')
        license.setWordWrap(True)
        license.setOpenExternalLinks(False)
        license.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction)
        license.setAlignment(Qt.AlignmentFlag.AlignCenter)

        license.linkActivated.connect(self._slot_license_link_acivated)

        return license

    def _slot_license_link_acivated(self, link):
        if link == _HREF_LICENSES_DIR:
            fp = self._license_directory()

            if fp:
                subprocess.run(['xdg-open', str(fp)], check=True)
                return

            msg = 'Unable to find LICENSES directory. Please contact the ' \
                  'Back In Time team and report a bug.'
            messagebox.critical(msg)
            logger.critical(msg)

        elif link == _HREF_SPDX_GPL:
            qttools.open_url(bitbase.URL_GPL_TWO)
            return

        logger.critical(f'Unknown link "{link}". Please open a bug report.')

    def _license_directory(self):
        """Determine the license folder."""
        for pkg in ('backintime-qt', 'backintime-common', 'backintime'):
            for path in (Path('/usr/share/licenses'), Path('/usr/share/doc')):

                fp = path / pkg / 'LICENSES'
                if fp.is_dir():
                    return fp

        return None

    def _project_buttons(self):
        wdg = QWidget(self)
        hbox = QHBoxLayout()
        wdg.setLayout(hbox)
        hbox.addStretch(1)
        layout = QVBoxLayout()
        hbox.addLayout(layout, 2)
        hbox.addStretch(1)

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

        return wdg

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

        # Experiment. This comment might appear on Weblate at context info.
        # Does it?
        name = QLabel(_('Back In Time'))
        name.setFrameStyle(QFrame.Shape.Box| QFrame.Shadow.Sunken)
        name.setLineWidth(3)
        font = name.font()
        font.setPointSizeF(font.pointSizeF() * 4)
        font.setBold(True)
        name.setFont(font)

        # hbox = QHBoxLayout()
        # hbox.addStretch(1)
        # hbox.addWidget(name, 0)
        # hbox.addStretch(1)

        wdg = QWidget(self)
        vbox = QVBoxLayout(wdg)

        vbox.addWidget(name, alignment=Qt.AlignmentFlag.AlignHCenter)
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
            path=Path(__file__).parent.parent,
            hash_length=8)

        try:
            branch, hash = info['branch'], info['hash']
        except TypeError:
            return None

        return QLabel(f'<strong>Git</strong>: branch {branch} | hash {hash}')

    def _msgbox_authors(self):
        file_path = Path(tools.docPath()) / 'AUTHORS'
        content = self._read_about_content(file_path)

        return messagebox.showInfo(self, _('Authors'), content)

    def _msgbox_translations(self):
        file_path = Path(tools.docPath()) / 'TRANSLATIONS'
        content = self._read_about_content(file_path)

        return messagebox.showInfo(self, _('Translations'), content)

    def _msgbox_license(self):
        file_path = Path(tools.docPath()) / 'LICENSE'
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
