# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import pathlib
import re
import json
import subprocess
import shutil
import textwrap
import signal
from contextlib import contextmanager
from tempfile import TemporaryDirectory
# We need to import common/tools.py
import qttools_path
qttools_path.registerBackintimePath('common')
# Workaround until the codebase is rectified/equalized.
import tools
tools.initiate_translation(None)
import qttools
import backintime
import bitbase
import config
import logger
import snapshots
import guiapplicationinstance
import mount
import progress
import encfsmsgbox
from inhibitsuspend import InhibitSuspend
from exceptions import MountException
from statedata import StateData
from PyQt6.QtGui import (QAction,
                         QActionGroup,
                         QShortcut,
                         QDesktopServices,
                         QPalette,
                         QIcon,
                         QFileSystemModel)
from PyQt6.QtWidgets import (QWidget,
                             QFrame,
                             QMainWindow,
                             QToolButton,
                             QLabel,
                             QLineEdit,
                             QCheckBox,
                             QListWidget,
                             QTreeView,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QAbstractItemView,
                             QStyledItemDelegate,
                             QVBoxLayout,
                             QStackedLayout,
                             QSplitter,
                             QGroupBox,
                             QMenu,
                             QToolBar,
                             QProgressBar,
                             QMessageBox,
                             QInputDialog,
                             QDialog,
                             QApplication,
                             )
from PyQt6.QtCore import (QDir,
                          QEvent,
                          QObject,
                          QPoint,
                          pyqtSlot,
                          pyqtSignal,
                          QSortFilterProxyModel,
                          Qt,
                          QTimer,
                          QThread,
                          QUrl)
import messagebox
import version

class StatusBar(QWidget):
    def __init__(self, main_window: QMainWindow):
        super().__init__()

        self.main_window = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.progressBar = QProgressBar(main_window)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setContentsMargins(0, 0, 0, 0)
        self.progressBar.setFixedHeight(5)
        self.progressBar.setVisible(False)

        self.progressBarDummy = QWidget()
        self.progressBarDummy.setContentsMargins(0, 0, 0, 0)
        self.progressBarDummy.setFixedHeight(5)

        self.status = QLabel(self)
        self.status.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.status)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.progressBarDummy)
