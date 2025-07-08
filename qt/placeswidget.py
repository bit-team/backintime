# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2025 Samuel Moore
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys

if not os.getenv('DISPLAY', ''):
    os.putenv('DISPLAY', ':0.0')

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
import snapshotsdialog
import logviewdialog
import languagedialog
import messagebox
import version
from usermessagedialog import UserMessageDialog


class PlacesWidget(QTreeWidget):
    def __init__(self, parent: QWidget, config: config.Config):
        QTreeWidget.__init__(self, parent=parent)

        self.config = config
        self.parent = parent
        
        # Do not show controls for expanding and collapsing top-level items
        self.setRootIsDecorated(False)

        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.setHeaderLabel(_('Shortcuts'))

        self.header().setSectionsClickable(True)
        self.header().setSortIndicatorShown(True)
        self.header().setSectionHidden(1, True)

        # ???
        self.placesSortLoop = {self.config.currentProfile(): False}

        self.header().sortIndicatorChanged.connect(self._slot_sort)
        self.currentItemChanged.connect(self._slot_changed)

    def _slot_sort(self, newColumn, newOrder, force = False):
        pid = self.config.currentProfile()

        if newColumn == 0 and newOrder == Qt.SortOrder.AscendingOrder:

            if pid in self.placesSortLoop and self.placesSortLoop[pid]:
                newColumn, newOrder = 1, Qt.SortOrder.AscendingOrder
                self.header().setSortIndicator(newColumn, newOrder)
                self.placesSortLoop[pid] = False

            else:
                self.placesSortLoop[pid] = True

        self.do_update()

    def do_update(self):
        self.clear()

        # name, path, icon
        self.addPlace(_('Places'), '', '')
        self.addPlace(_('File System'), '/', 'computer')

        fp_home = pathlib.Path.home()
        self.addPlace(
            # Use full path in root mode ("/root") otherwise users name only
            str(fp_home) if bitbase.IS_IN_ROOT_MODE else fp_home.name,
            str(fp_home),
            'user-home')

        # "Now" or a specific snapshot selected?
        if self.parent.sid.isRoot:
            # Use snapshots profiles list of include files and folders
            include_entries = self.config.include()

        else:
            # Determine folders from the snapshot itself
            base = os.path.expanduser('~')
            if not os.path.isdir(self.parent.sid.pathBackup(base)):
                # Folder not mounted. We can skip for the next updatePlaces()
                return

            folders = [i.name for i in os.scandir(self.parent.sid.pathBackup(base)) if i.is_dir()]
            include_entries = [(os.path.join(base, f), 0) for f in folders]

        # Use folders only (if 2nd tuple entry is 0)
        only_folders = filter(lambda entry: entry[1] == 0, include_entries)
        include_folders = [item[0] for item in only_folders]

        if not include_folders:
            return

        if not self.header().sortIndicatorSection():
            indic = self.header().sortIndicatorOrder()
            reverse = True if indic == Qt.SortOrder.DescendingOrder else False
            include_folders = sorted(include_folders, reverse=reverse)

        self.addPlace(_('Backup directories'), '', '')

        for folder in include_folders:
            self.addPlace(folder, folder, 'document-save')

    def addPlace(self, name, path, icon):
        """
        Dev note (buhtz, 2024-01-14): Parts of that code are redundant with
        timeline.py::HeaderItem.__init__().
        """
        item = QTreeWidgetItem()

        item.setText(0, name)

        if icon:
            item.setIcon(0, QIcon.fromTheme(icon))

        item.setData(0, Qt.ItemDataRole.UserRole, path)

        if not path:
            item.setFont(0, qttools.fontBold(item.font(0)))

            # item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(
                0, self.palette().color(QPalette.ColorRole.PlaceholderText))
            item.setBackground(
                0, self.palette().color(QPalette.ColorRole.Window))

        self.addTopLevelItem(item)

        if path == self.parent.path:
            self.setCurrentItem(item)

        return item

    def _slot_changed(self, item, previous):
        if item is None:
            return

        path = str(item.data(0, Qt.ItemDataRole.UserRole))
        if not path:
            return

        if path == self.parent.path:
            return

        # ???
        self.parent.path = path
        self.parent.path_history.append(path)

        self.parent.updateFilesView(3)

    def set_sorting(self, sorting: tuple[int, int]) -> None:
        """Set sorting.

        Args:
            sorting: Two item tuple with column and order.
        """
        self.header().setSortIndicator(sorting[0], Qt.SortOrder(sorting[1]))

    def get_sorting(self) -> tuple[int, int]:
        """Current sorting column and order as a tuple."""
        return = (
            self.header().sortIndicatorSection(),
            self.header().sortIndicatorOrder().value
        )
