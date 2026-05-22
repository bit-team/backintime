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
from bitbase import URL_ENCRYPT_TRANSITION


class _EncfsWarningBase(QMessageBox):
    """Base clase for Warning boxes in context of EncFS decprecation.
    """
    # pylint: disable=too-few-public-methods

    def __init__(self,
                 text,
                 informative_text,
                 button_label=None,
                 title=_('Warning'),
                 icon=QMessageBox.Icon.Warning):
        super().__init__()

        self.setWindowTitle(title)
        self.setIcon(icon)
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


class EncfsFinalRemoval(_EncfsWarningBase):
    """Info box about the final removal of EncFS"""
    # pylint: disable=too-few-public-methods

    def __init__(self, path):

        text = (
            '<p>All EncFS-based backup profiles were '
            'removed from the active '
            'configuration because <strong><span style="color: red;">EncFS is no '
            'longer supported</span></strong> by Back In Time.</p>'
        )

        informative_text = (
            '<p>A <strong>backup</strong> of the previous configuration '
            'containing the removed profiles was created at:'
            f'<br><verbatim>{path}</verbatim></p>'
            '<p>Back In Time now uses <strong>gocryptfs</strong> for '
            'encrypted backup profiles. Automatic migration from EncFS to '
            'gocryptfs is not feasible and the removed profiles must be '
            'recreated manually.</p>'
            '<p>For more <strong>information</strong> and '
            '<strong>support</strong>, see this '
            f'<a href="{URL_ENCRYPT_TRANSITION}">support article</a>.</p>'
        )

        super().__init__(
            text=text,
            informative_text=informative_text,
            button_label='Got it',
            title='EncFS Profiles Removed',
            icon=QMessageBox.Icon.Critical
        )
