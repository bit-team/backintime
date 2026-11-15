# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Message box warning about EncFS deprecation.

See #1734 and #1735 for details
"""
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QLabel, QToolTip, QMessageBox
from bitbase import URL_ENCRYPT_TRANSITION, URL_GOCRYPT_MIGRATION


class _EncfsWarningBase(QMessageBox):
    """Base clase for Warning boxes in context of EncFS decprecation.
    """
    # pylint: disable=too-few-public-methods

    def __init__(self, text, informative_text, button_label=None):
        super().__init__()

        self.setWindowTitle(_('Warning'))
        self.setIcon(QMessageBox.Icon.Warning)
        self.setText(text)
        self.setInformativeText(informative_text)

        # Set link tooltips (via hovering) on the QLabels
        for label in self.findChildren(QLabel):
            label.linkHovered.connect(
                lambda url: QToolTip.showText(
                    QCursor.pos(), url.replace('https://', '')))

        if button_label:
            self.setStandardButtons(QMessageBox.StandardButton.Ok)
            ok_button = self.button(QMessageBox.StandardButton.Ok)
            ok_button.setText(button_label)


class EncfsExistsWarning(_EncfsWarningBase):
    """Warning box when encrypted profiles exists.
    """
    # pylint: disable=too-few-public-methods

    def __init__(self, profiles):

        whitepaper = f'<a href="{URL_ENCRYPT_TRANSITION}">' \
            + 'whitepaper' + '</a>'

        text = (
            '<p><span style="color: red;"><strong>Encrypted profiles using '
            'EncFS are no longer supported.</strong></span></p>'
            '<p>EncFS is considered insecure and receives no further '
            'updates.</p>'
            '<p>Creation of new EncFS backup profiles is not possible. '
            'Existing EncFS profiles are still displayed and supported for '
            'now, but EncFS support will be <strong>completely removed'
            '</strong> in a future release (expected around 2027).</p>'
            f'For more information, see the {whitepaper}. This dialog is '
            'available at any time via the help menu.'
        )

        profiles = '<ul>' \
            + ''.join(f'<li>{profile}</li>' for profile in profiles) \
            + '</ul>'

        info_paragraphs = (
            'The following profile(s) use encryption with EncFS:',
            profiles,
        )

        informative_text = ''.join(
            [f'<p>{par}</p>' for par in info_paragraphs])

        super().__init__(text, informative_text, 'Got it')


class GocryptfsExistsWarning(_EncfsWarningBase):
    """Warning box when gocryptfs encrypted profiles exists.
    """
    # pylint: disable=too-few-public-methods

    def __init__(self, profiles):
        further_info = f'<a href="{URL_GOCRYPT_MIGRATION}">'
        further_info += 'further information</a>'

        profiles = '<ul>' \
            + ''.join(f'<li>{profile}</li>' for profile in profiles) \
            + '</ul>'

        info_paragraphs = (
            'The following profile(s) use local encryption with gocryptfs:',
            profiles,
        )

        informative_text = ''.join(
            [f'<p>{par}</p>' for par in info_paragraphs])

        text = (
            '<p><span style="color: red;"><strong>Existing '
            'gocryptfs-encrypted profiles will no longer work in '
            'Back In Time 2.0.0.</strong></span></p>'
            '<p>The current implementation of local encrypted backups '
            '(using gocryptfs forward mounts), introduced in version 1.6, '
            'will be replaced by a new implementation in version 2.0.0.</p>'
            '<p>In version 1.7, existing gocryptfs-encrypted profiles '
            'can still be loaded and used, but new ones cannot be '
            'created.</p>'
            '<p><span style="color: red;">Support for these profiles '
            'will be <strong>completely removed</strong> in version '
            '2.0.0. <strong>No automatic migration will be '
            'offered.</strong></span> Full support for gocryptfs-encrypted '
            'backups will return with the new implementation in version '
            '2.0.0.</p>'
            '<p>Gocryptfs-encrypted profiles created with version 1.6 '
            'will not be compatible with later versions.</p>'
            f'<p>See {further_info}. '
            'This dialog is available at any time via the help menu.</p>'
        )

        super().__init__(text, informative_text, 'Got it')
