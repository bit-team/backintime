#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""A widget combinging the two rsync options --copy-links and
--copy-unsafe-links.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
import qttools


class CopySymlinksWidget(QWidget):
    """Mimic the logic of rsyncs copy-links and copy-unsafe-links setting.

    The widget contains two radio buttons that are enabled by an overall
    checkbox.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Main checkbox
        self._checkbox = QCheckBox(_('Copy symbolic links as files'), self)
        self._checkbox.stateChanged.connect(self._slot_checkbox_changed)
        qttools.set_wrapped_tooltip(
            self._checkbox,
            [
                _('Copy symbolic links as real files or directories in the '
                  'backup. Select whether all links or only those '
                  'pointing outside the source are copied.'),
                _('This option may increase backup size.'),
                _('Disabled by default.')
            ]
        )
        main_layout.addWidget(self._checkbox)

        radio_layout = QHBoxLayout()
        main_layout.addLayout(radio_layout)

        # --copy-links
        self._rb_all = QRadioButton(_('All'), self)
        qttools.set_wrapped_tooltip(
            self._rb_all,
            [
                _('All symbolic links are replaced with real files or '
                  'directories they point to. This increases backup '
                  'size and may store the same files multiple times.'),
                _("Uses 'rsync --copy-links'."),
            ]
        )

        # --copy-unsafe-links
        self._rb_external = QRadioButton(_('Only external'), self)
        qttools.set_wrapped_tooltip(
            self._rb_external,
            [
                _('Only links pointing outside the backup source are copied '
                  'as files. This increases backup size and may store the '
                  'same files multiple times.'),
                _("Uses 'rsync --copy-unsafe-links'.")
            ]
        )

        self._rb_group = QButtonGroup(self)
        self._rb_group.addButton(self._rb_all)
        self._rb_group.addButton(self._rb_external)

        radio_layout.addWidget(self._rb_all)
        radio_layout.addWidget(self._rb_external)
        radio_layout.addStretch(1)

        # Indent radio buttons based on checkbox size
        cb_width = self._checkbox.style().pixelMetric(
            self._checkbox.style().PixelMetric.PM_IndicatorWidth
        )
        radio_layout.setContentsMargins(cb_width*2, 0, 0, 0)

        # Disable by default
        self._disable()

    @property
    def all_links(self) -> bool:
        """--copy-links"""
        return self._rb_all.isChecked()

    @property
    def only_external_links(self) -> bool:
        """--copy-unsafe-links"""
        return self._rb_external.isChecked()

    def set_values(self, all_links: bool, only_external: bool):
        """Set the widgest values and state.

        Args:
            all_links: Related to --copy-links
            only_external: Related to --copy-unsafe-links

        The logic of two rsyncs is preserved. Also the enabled state is
        considered.
        """
        # Disable the whole widget
        if not any((all_links, only_external)):
            self._checkbox.setChecked(False)
            self._disable()
            return

        # Set checkbox
        self._checkbox.setChecked(True)

        if all_links:
            self._rb_all.setChecked(True)
            return

        if only_external:
            self._rb_external.setChecked(True)

    def _slot_checkbox_changed(self, state: int):
        if Qt.CheckState(state) == Qt.CheckState.Checked:
            self._enable()
        else:
            self._disable()

    def _enable(self):
        self._rb_all.setEnabled(True)
        self._rb_all.setChecked(False)
        self._rb_external.setEnabled(True)
        self._rb_external.setChecked(True)

    def _disable(self):
        self._rb_group.setExclusive(False)

        self._rb_all.setChecked(False)
        self._rb_all.setEnabled(False)

        self._rb_external.setChecked(False)
        self._rb_external.setEnabled(False)

        self._rb_group.setExclusive(True)
