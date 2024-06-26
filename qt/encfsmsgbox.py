# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""Message box warning about EncFS deprecation.

See #1734 and #1735 for details
"""
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QLabel, QToolTip, QMessageBox
from bitbase import URL_ENCRYPT_TRANSITION


class EncfsCreateWarning(QMessageBox):
    """Warning box when using EncFS encrypting while creating a new profile
    or modify an existing one.
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle(_('Warning'))
        self.setIcon(QMessageBox.Icon.Warning)
        self.setText(_('Support for EncFS will be discontinued in the '
                       'foreseeable future. It is not recommended use that '
                       'mode for a profile.'))
        self.setInformativeText(_(
            'A decision on a replacement for continued support of encrypted '
            'backups is still pending, depending on project resources and '
            'contributor availability. More details are available in this '
            '{url}.'
        ).format(url='<a href="{}">{}</a>'.format(
            URL_ENCRYPT_TRANSITION,
            _('whitepaper'))))

        # Set link tooltips (via hovering) on the QLabels
        for label in self.findChildren(QLabel):
            label.linkHovered.connect(
                lambda url: QToolTip.showText(
                    QCursor.pos(), url.replace('https://', ''))
        )
