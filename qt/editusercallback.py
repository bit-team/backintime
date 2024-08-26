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
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
import os
import datetime
import copy
import re
import getpass
from PyQt6.QtGui import (QIcon,
                         QFont,
                         QPalette,
                         QBrush,
                         QColor,
                         QCursor,
                         QFileSystemModel)
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QGridLayout,
                             QDialogButtonBox,
                             QMessageBox,
                             QInputDialog,
                             QGroupBox,
                             QScrollArea,
                             QFrame,
                             QWidget,
                             QTabWidget,
                             QComboBox,
                             QLabel,
                             QPushButton,
                             QToolButton,
                             QLineEdit,
                             QSpinBox,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QAbstractItemView,
                             QHeaderView,
                             QCheckBox,
                             QMenu,
                             QProgressBar,
                             QPlainTextEdit,
                             QToolTip)
from PyQt6.QtCore import (Qt,
                          QDir,
                          QSortFilterProxyModel,
                          QThread,
                          pyqtSignal)

import config
import tools
import qttools
import mount
import messagebox
import snapshots
import sshtools
import logger
import encfsmsgbox
from manageprofiles import schedulewidget
from exceptions import MountException, NoPubKeyLogin, KnownHost
from bitbase import URL_ENCRYPT_TRANSITION
import qttools


class EditUserCallback(QDialog):
    def __init__(self, parent):
        super(EditUserCallback, self).__init__(parent)
        self.config = parent.config
        self.script = self.config.takeSnapshotUserCallback()

        import icon
        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(self.script)
        self.resize(800, 500)

        layout = QVBoxLayout(self)
        self.edit = QPlainTextEdit(self)

        try:
            with open(self.script, 'rt') as f:
                self.edit.setPlainText(f.read())

        except IOError:
            pass

        layout.addWidget(self.edit)

        btnBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self)

        btnBox.accepted.connect(self.accept)
        btnBox.rejected.connect(self.reject)
        layout.addWidget(btnBox)

    def checkScript(self, script):
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
        if not self.checkScript(self.edit.toPlainText()):
            return

        with open(self.script, 'wt') as f:
            f.write(self.edit.toPlainText())

        os.chmod(self.script, 0o755)

        super(EditUserCallback, self).accept()
