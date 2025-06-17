# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raak
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Dialog to edit the user-callback script.
"""
import re
from pathlib import Path
from PyQt6.QtWidgets import (QDialog,
                             QDialogButtonBox,
                             QPlainTextEdit,
                             QVBoxLayout,
                             QWidget
                             )
from PyQt6.QtCore import QSize, QTimer
from PyQt6.QtGui import QFontDatabase
from bitbase import DEFAULT_CALLBACK
import messagebox
from statedata import StateData


class EditUserCallback(QDialog):
    """Dialog to edit the user-callback script."""

    def __init__(self, parent: QWidget, script_path: Path):
        super().__init__(parent)
        # self.config = parent.config
        self.script_fp = script_path

        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415

        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(
            _('User-callback: "{filename}"').format(
                filename=str(self.script_fp))
        )

        state_data = StateData()

        # restore position and size
        try:
            self.move(*state_data.user_callback_edit_coords)
            self.resize(*state_data.user_callback_edit_dims)
        except KeyError:
            # Double the default size
            QTimer.singleShot(5, self._double_size)

        layout = QVBoxLayout(self)

        self.edit_widget = QPlainTextEdit(self)
        self.edit_widget.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))

        script_text = ''

        try:
            with self.script_fp.open('rt', encoding='utf-8') as handle:
                script_text = handle.read()

        except FileNotFoundError:
            # Use default example script
            try:
                with DEFAULT_CALLBACK.open('rt', encoding='utf-8') as handle:
                    script_text = handle.read()
            except FileNotFoundError:
                pass

        self.edit_widget.setPlainText(script_text)

        layout.addWidget(self.edit_widget)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.finished.connect(self._slot_finished)

    def _double_size(self):
        current_size = self.size()
        self.resize(QSize(current_size.width()*2, current_size.height()*2))

    def _warn_if_no_shebang(self) -> bool:
        script_text = self.edit_widget.toPlainText()

        # Shebang in first line?
        has_shebang = bool(re.match(
            r'^#!/[\w/-]+(?:\s+[\w.-]+)*$',
            script_text.split('\n')[0]))

        if has_shebang is False:
            messagebox.warning(
                _('The user-callback script must include a '
                  'shebang on the first line (e.g. {example}).').format(
                      example='#!/bin/sh')
            )

        return has_shebang

    def accept(self):
        """OK pressed"""
        if not self._warn_if_no_shebang():
            return

        with self.script_fp.open('wt', encoding='utf-8') as handle:
            handle.write(self.edit_widget.toPlainText())

        # make it executable
        self.script_fp.chmod(0o755)

        super().accept()

    def _slot_finished(self):
        """The dialog is closed"""
        state_data = StateData()
        state_data.user_callback_edit_coords = (self.x(), self.y())
        state_data.user_callback_edit_dims = (self.width(), self.height())
