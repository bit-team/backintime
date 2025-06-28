# SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module with widgets regarding SSH Key file selection"""
# from pathlib import Path
from typing import Callable
from pathlib import Path
from functools import partial
from collections import deque
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QButtonGroup,
                             QHBoxLayout,
                             QRadioButton,
                             QVBoxLayout,
                             QWidget)
from PyQt6.QtGui import QColor, QPalette
import sshtools
import qttools
from manageprofiles.combobox import BitComboBox


class SshKeyCombo(BitComboBox):
    """Combo box to select SSH key files.

        # The keys are the underlying 'userData'.
        fill = {
            10: 'Hour',
            20: 'Day',
            30: 'Week',
            40: 'Month'
        }
        combo = BitComboBox(parent, fill)

    """

    ACT_ID_SELECT_FILE = 1
    ACT_ID_GENERATE_PAIR = 2

    def __init__(self,
                 parent: QWidget,
                 select_key_handler: Callable,
                 generate_pair_handler: Callable):
        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415

        # key file entries
        key_files = sshtools.get_private_ssh_key_files()
        content_dict = {
            fp: (
                fp.name,
                SshKeyCombo._key_tooltip(fp),
                icon.ENCRYPT
            )
            for fp in key_files
        }

        # select another key file
        content_dict[self.ACT_ID_SELECT_FILE] = (
            _('<Select another file…>'),
            _('Create a new SSH key without passphrase.'),
            icon.FOLDER
        )

        # generate key files
        content_dict[self.ACT_ID_GENERATE_PAIR] = (
            _('<Generate new key-pair…>'),
            _('Choose an existing private key file from somewhere else.'),
            icon.ADD
        )

        super().__init__(
            parent=parent,
            content_dict=content_dict
        )

        self._handlers = {
            self.ACT_ID_SELECT_FILE: select_key_handler,
            self.ACT_ID_GENERATE_PAIR: generate_pair_handler
        }

        self.currentIndexChanged.connect(self._on_selection_changed)

        self._original_style = None

    @staticmethod
    def _key_tooltip(path: Path) -> str:
        return _('Full path: {path}').format(path=str(path))

    def _on_selection_changed(self, _idx):
        data = self.current_data

        try:
            handler = self._handlers[data]
        except KeyError:
            return

        handler()

    def add_and_select(self, key_path: Path):
        """Add a new entry and select it after that."""
        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415

        with qttools.block_signals(self):

            # still exists?
            if self.has_data(key_path):
                self.select_by_data(key_path)

            else:
                self.insertItem(
                    0, icon.ENCRYPT, key_path.name, userData=key_path)
                self.setItemData(
                    0,
                    SshKeyCombo._key_tooltip(key_path),
                    Qt.ItemDataRole.ToolTipRole)
                self.setCurrentIndex(0)

        self._fade_background()

    def _fade_background(self, duration_ms=1200, steps=30):
        palette = self.palette()
        high = palette.color(QPalette.ColorRole.Highlight)
        base = palette.color(QPalette.ColorRole.Base)

        # Helper vars for color interpolation
        diff_r = high.red() - base.red()
        diff_g = high.green() - base.green()
        diff_b = high.blue() - base.blue()

        colors = []
        # base -> high
        for curr_step in range(steps//2):
            colors.append(QColor(
                base.red() + diff_r * curr_step // steps,
                base.green() + diff_g * curr_step // steps,
                base.blue() + diff_b * curr_step // steps))

        # Helper vars for color interpolation
        diff_r = base.red() - high.red()
        diff_g = base.green() - high.green()
        diff_b = base.blue() - high.blue()

        # high -> base
        for curr_step in range(steps//2, steps):
            colors.append(QColor(
                high.red() + diff_r * curr_step // steps,
                high.green() + diff_g * curr_step // steps,
                high.blue() + diff_b * curr_step // steps))

        colors.append(None)
        colors = deque(colors)

        interval = duration_ms // steps
        self._original_style = self.styleSheet()

        def update_color(col):
            if col is None:
                self.setStyleSheet(self._original_style)
                return

            self.setStyleSheet(
                f'QComboBox {{ background-color: {col.name()}; }}')

            QTimer.singleShot(
                interval, partial(update_color, colors.popleft()))

        update_color(colors.popleft())


class SshKeySelector(QWidget):
    """Main widget for selecting or generating key files"""

    def __init__(self,
                 parent: QWidget,
                 select_key_handler: Callable,
                 generate_pair_handler: Callable):
        super().__init__(parent=parent)

        # radio: key selector
        self.radio_key = QRadioButton(_('Private key:'))
        self.selector = SshKeyCombo(
            self, select_key_handler, generate_pair_handler)

        # radio: no key
        self.radio_no = QRadioButton(_('Use system SSH configuration'))
        tooltip = _(
            'Leaves the key file unselected. SSH connections will rely '
            'on the system’s existing client configuration '
            '(e.g., ~/.ssh/config).')
        qttools.set_wrapped_tooltip(self.radio_no, tooltip)

        # button group
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.radio_no)
        self.btn_group.addButton(self.radio_key)

        # layout
        row_key = QHBoxLayout()
        row_key.addWidget(self.radio_key, stretch=0)
        row_key.addWidget(self.selector, stretch=1)
        row_no = QHBoxLayout()
        row_no.addWidget(self.radio_no)
        layout = QVBoxLayout()
        layout.addLayout(row_no)
        layout.addLayout(row_key)
        # zero margins
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # events
        self.btn_group.buttonClicked.connect(self._slot_clicked)

        # default state
        self.radio_no.setChecked(True)
        self._slot_clicked(self.radio_no)

    def _slot_clicked(self, button):
        self.selector.setEnabled(button == self.radio_key)

    def add_and_select_key(self, key_path: Path):
        """Enable the drop down widget and add and select a new entry to it."""
        self.selector.add_and_select(key_path)
        self.radio_key.setChecked(True)

    def set_key(self, key_path: Path | None) -> None:
        """Select an existing key based on its path.

        If not enabled this will also enable the drop down. If path is ``None``
        the drop down widget is disabled."""
        if key_path:
            self.selector.select_by_data(key_path)
            self.radio_key.setChecked(True)
            self.btn_group.buttonClicked.emit(self.radio_key)
        else:
            self.radio_no.setChecked(True)
            self.btn_group.buttonClicked.emit(self.radio_no)

    def get_key(self) -> Path | None:
        """Return the path of the current selected key or ``None`` if the
        drop down widget is disabled."""
        if self.radio_no.isChecked():
            return None

        if isinstance(self.selector.current_data, Path):
            return self.selector.current_data

        return None
