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
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QDialog,
                             QDialogButtonBox,
                             QFrame,
                             QHBoxLayout,
                             QLabel,
                             QPushButton,
                             QStyle,
                             QVBoxLayout,
                             QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
import logger
import bitbase
import bitlicense
import tools
import version
import messagebox
import qttools

_HREF_LICENSES_DIR = 'LICENSES-dir'
_HREF_LICENSES_MD = 'LICENSES-md'
_HREF_SPDX_GPL = 'spdx-gplv2'


class AboutDlg(QDialog):
    """The about dialog accessible from the Help menu in the main window."""

    def __init__(self, using_translation: bool, parent: QWidget = None):
        """Initialize and layout.

        Args:
            using_translation: Indicates if the current used language is a
                translated language or the source language (English).
        """
        super().__init__(parent)
        self.setWindowTitle(_('About Back In Time'))

        self.using_translation = using_translation

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
        right_box.addLayout(self._create_authors_etc())
        right_box.addStretch(1)
        right_box.addWidget(self._create_ok_button())

    def _create_authors_etc(self):

        def _set_label_props(label):
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignTop)
            label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setAutoFillBackground(True)
            label.setBackgroundRole(QPalette.ColorRole.Light)
            label.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
            label.setLineWidth(1)

        label_copyright = QLabel('<strong>' + _('Copyright:') + '</strong>')
        copyr = QLabel(bitlicense.COPYRIGHT)
        _set_label_props(copyr)

        label_authors = QLabel('<strong>' + _('Authors:') + '</strong>')
        authors = QLabel(self._get_authors())
        _set_label_props(authors)

        label_trans = QLabel('<strong>' + _('Translators:') + '</strong>')
        # Please add your name to the list of translators if you want to be
        # credited for the translations you have done.
        text_trans = _('translator-credits-placeholder')
        placeholder_string = 'translator-credits-placeholder'

        # String not translated, means no credits available.
        if text_trans == placeholder_string:
            text_trans = ''
            if self.using_translation:
                text_trans = '<p>' + _('Translator credits not available for '
                                       'current language.') + '</p>'

        else:
            text_trans = '<br>∘ '.join(text_trans.split('\n'))
            text_trans = '<p>∘ ' + text_trans + '</p>'

        text_link = '<a href="https://translate.codeberg.org/search/' \
            f'backintime/common/?q=+source%3A%3D{placeholder_string}">'
        text_link = text_link + _('this link') + '</a>'
        text_link = _(
            'Follow {thislink} to get translator credits for '
            'all languages.').format(thislink=text_link)

        text_more = '<br>∘ '.join(bitbase.TRANSLATION_CREDITS_MISC)
        text_more = \
            f'<p>Additional credits:<br>∘ {text_link}<br>∘ {text_more} </p>'

        trans = QLabel(text_trans + text_more)
        _set_label_props(trans)
        trans.setOpenExternalLinks(True)
        trans.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction)

        left = QVBoxLayout()
        left.addWidget(label_copyright)
        left.addWidget(copyr)
        left.addWidget(label_authors)
        left.addWidget(authors)

        right = QVBoxLayout()
        right.addWidget(label_trans, 0)
        right.addWidget(trans, 1)

        layout = QHBoxLayout()
        layout.addLayout(left)
        layout.addLayout(right)

        return layout

    def _create_license(self):
        # Dev note (buhtz, 2025-03): That string is untranslated on purpose.
        # It is legally relevant, and no one should be given the opportunity
        # to change the string—whether intentionally or accidentally.
        text_gpl = bitlicense.get_gpl_short_text(href=_HREF_SPDX_GPL)
        text_licenses = bitlicense.TXT_LICENSES.format(
                dir_link=f'<a href="{_HREF_LICENSES_DIR}">LICENSES</a>',
                readme_link=f'<a href="{_HREF_LICENSES_MD}">LICENSES.md</a>')

        gpl = QLabel(f'<p>{text_gpl}</p><p>{text_licenses}</p>')
        gpl.setWordWrap(True)
        gpl.setOpenExternalLinks(False)
        gpl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction)
        gpl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gpl.linkActivated.connect(self._slot_license_link_acivated)

        return gpl

    def _slot_license_link_acivated(self, link):
        if link in (_HREF_LICENSES_DIR, _HREF_LICENSES_MD):
            fp = bitlicense.DIR_LICENSES

            if link == _HREF_LICENSES_MD:
                fp = fp.parent / 'LICENSES.md'

            if fp:
                try:
                    subprocess.run(['xdg-open', str(fp)], check=True)
                except subprocess.CalledProcessError as exc:
                    logger.critical(str(exc))
                else:
                    return

            msg = f'Unable to find {fp}. Please contact the ' \
                  'Back In Time team and report a bug.'
            messagebox.critical(self, msg)
            logger.critical(msg)
            return

        if link == _HREF_SPDX_GPL:
            qttools.open_url(bitlicense.URL_GPL_TWO)
            return

        logger.critical(f'Unknown link "{link}". Please open a bug report.')

    def _get_authors(self):
        fp = Path('/usr/share/doc') / bitbase.PACKAGE_NAME_CLI / 'AUTHORS'

        if fp.is_file():
            return fp.read_text()

        logger.warning(f'Can not find file {fp}')

        # Running from source/git repo?
        fp = Path.cwd().parent / 'AUTHORS'
        if fp.is_file():
            return fp.read_text()

        logger.warning(f'Can not find file {fp}')

        return '(Can not find AUTHORS information file.)'

    def _project_buttons(self):
        wdg = QWidget(self)
        hbox = QHBoxLayout()
        wdg.setLayout(hbox)
        hbox.addStretch(1)
        layout = QVBoxLayout()
        hbox.addLayout(layout, 2)
        hbox.addStretch(1)

        website = QPushButton(_('Project website'))
        website.setToolTip(bitbase.URL_WEBSITE.replace('https://', ''))
        website.clicked.connect(
            lambda: qttools.open_url(bitbase.URL_WEBSITE))

        manual = QPushButton(_('User manual'))
        manual.setToolTip(_('Open user manual in browser (local if available '
                            'otherwise online)'))
        manual.clicked.connect(qttools.open_user_manual)

        layout.addWidget(website)
        layout.addWidget(manual)
        layout.addStretch(1)

        return wdg

    def _create_logo_widget(self):
        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415

        size = self.style().pixelMetric(
            QStyle.PixelMetric.PM_LargeIconSize)
        logo = icon.BIT_LOGO.pixmap(size*4)

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

        font = name.font()
        font.setPointSizeF(font.pointSizeF() * 3)
        font.setBold(True)
        name.setFont(font)

        wdg = QWidget(self)
        vbox = QVBoxLayout(wdg)

        vbox.addWidget(name, alignment=Qt.AlignmentFlag.AlignHCenter)
        vbox.addWidget(self._create_version_label())
        git = self._create_git_label()
        if git:
            vbox.addWidget(git)
        vbox.addStretch(1)

        return wdg

    def _create_version_label(self):
        return QLabel(
            _('{BOLD}Version{BOLDEND}: {version}').format(
                BOLD='<strong>',
                BOLDEND='</strong>',
                version=version.__version__)
        )

    def _create_git_label(self):
        info = tools.get_git_repository_info(
            # should be the repos root folder
            path=Path(__file__).parent.parent,
            hash_length=8)

        try:
            branch, githash = info['branch'], info['hash']
        except TypeError:
            return None

        return QLabel(
            f'<strong>Git</strong>: branch {branch} | hash {githash}')
