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
import os
import re
from PyQt6.QtWidgets import (QDialog,
                             QDialogButtonBox,
                             QPlainTextEdit,
                             QVBoxLayout
                             )
from PyQt6.QtCore import QSize, QTimer
import tools
import logger
from statedata import StateData


class EditUserCallback(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.config = parent.config
        self.script = self.config.takeSnapshotUserCallback()

        import icon
        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(self.script)

        state_data = StateData()

        # restore position and size
        try:
            self.move(*state_data.user_callback_edit_coords)
            self.resize(*state_data.user_callback_edit_dims)
        except KeyError:
            # Double the default size
            QTimer.singleShot(5, self._double_size)

        layout = QVBoxLayout(self)
        self.edit = QPlainTextEdit(self)

        try:
            with open(self.script, 'rt') as f:
                self.edit.setPlainText(f.read())

        except IOError:
            pass

        layout.addWidget(self.edit)

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

    def _warn_if_no_shebang(self, script):
        m = re.match(r'^#!(/[\w/-]+)\n', script)

        if not m:
            logger.error(
                'user-callback script has no shebang (#!/bin/sh) line.')
            self.config.errorHandler(
                'user-callback script has no shebang (#!/bin/sh) line.')

            return False

        if not tools.checkCommand(m.group(1)):
            logger.error('Shebang in user-callback script is not executable.')
            self.config.errorHandle(
                'Shebang in user-callback script is not executable.')

            return False

        return True

    def accept(self):
        if not self._warn_if_no_shebang(self.edit.toPlainText()):
            return

        with open(self.script, 'wt') as f:
            f.write(self.edit.toPlainText())

        # make it executable
        os.chmod(self.script, 0o755)

        super().accept()

    def _slot_finished(self):
        """The dialog is closed"""
        state_data = StateData()
        state_data.user_callback_edit_coords = (self.x(), self.y())
        state_data.user_callback_edit_dims = (self.width(), self.height())
