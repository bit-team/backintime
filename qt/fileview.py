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
#
# Split from app.py
"""The file view widget in the main window."""
import os
import sys
import pathlib
import json
import threading
import shutil
import textwrap
import signal
from collections.abc import Generator
from contextlib import contextmanager
from tempfile import TemporaryDirectory
# We need to import common/tools.py
import qttools_path
qttools_path.register_backintime_path('common')
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
from filedialog import FileDialog
from textdlg import TextDialog
from PyQt6.QtGui import (QAction,
                         QActionGroup,
                         QDesktopServices,
                         QFileSystemModel,
                         QIcon,
                         QShortcut)
from PyQt6.QtWidgets import (QAbstractItemView,
                             QApplication,
                             QDialog,
                             QFrame,
                             QGroupBox,
                             QInputDialog,
                             QLabel,
                             QLineEdit,
                             QMainWindow,
                             QMenu,
                             QStyledItemDelegate,
                             QStackedLayout,
                             QSplitter,
                             QToolBar,
                             QToolButton,
                             QTreeView,
                             QVBoxLayout,
                             QWidget)
from PyQt6.QtCore import (QDir,
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
from confirmrestoredialog import ConfirmRestoreDialog
from editusercallback import EditUserCallback
from shutdownagent import ShutdownAgent
from manageprofiles import SettingsDialog
from restoredialog import RestoreDialog
from restoreconfigdialog import RestoreConfigDialog
from usermessagedialog import UserMessageDialog
from aboutdlg import AboutDlg
from timeline import TimeLine, SnapshotItem
from bitwidgets import ProfileCombo
from shutdowndlg import get_shutdown_confirmation
from statusbar import StatusBar
from placeswidget import PlacesWidget
from qtsystrayicon import QtSysTrayIcon

class ProxyModel(QSortFilterProxyModel):
    def __init__(self, parent, model):
        QSortFilterProxyModel.__init__(parent)
        self.filesViewProxyModel.setDynamicSortFilter(True)
        self.filesViewProxyModel.setSourceModel(model)


class FileModel(QFileSystemModel):
    def __init__(self, parent):
        QFileSystemModel.__init__(parent)
        self.setRootPath(QDir().rootPath())
        self.setReadOnly(True)
        self.setFilter(
            QDir.Filter.AllDirs |
            QDir.Filter.AllEntries |
            QDir.Filter.NoDotAndDotDot |
            QDir.Filter.Hidden
        )

        self.styled_item_delegate = QStyledItemDelegate(parent)
        self.setItemDelegate(self.styled_item_delegate)

    def set_sort(self, view: FilesView):
        self.sort(
            view.header().sortIndicatorSection(),
            view.header().sortIndicatorOrder()
        )



class FileView(QTreeView):
    """File view widget in the main window"""

    def __init__(self, window: QMainWindow)
        QTreeView.__init__(window)

        self._window = window

        # self.filesView = QTreeView(self)
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setItemsExpandable(False)
        self.setDragEnabled(False)
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)

        self.header().setSectionsClickable(True)
        self.header().setSectionsMovable(False)
        self.header().setSortIndicatorShown(True)

        # = model
        self.filesViewModel = FilesModel(self)

        # = proxy
        self.filesViewProxyModel = ProxyModel(self, self.filesViewModel)

        # setup sorting
        sortColumn, sortOrder = state_data.files_view_sorting
        self.header().setSortIndicator(sortColumn, Qt.SortOrder(sortOrder))
        self.header().sortIndicatorChanged.connect(self.filesViewModel.sort)
        self.filesViewModel.set_sort(self)

        self._context_menu = self._context_menu()

        # self._restore_visual_state()

        # self._try_to_mount()

        self.filesViewProxyModel.layoutChanged.connect(self.dirListerCompleted)

        # Dev note (buhtz, 2026-01): Don't use doubleClicked signal because
        # it won't catch desktops with single-click-as-double-click settings.
        self.activated.connect(self._slot_item_activated)

    def set_columns_width(self, widths: list[int]):
        for idx, width in enumerate(widths):
            self.header().resizeSection(idx, width)

    def get_columns_width(self) -> list[int]:
        return [
            self.header().sectionSize(idx)
            for idx
            in range(self.header().count())
        ]

    def get_sorting(self) -> tuple[int, int]:
        return (
            self.header().sortIndicatorSection(),
            self.header().sortIndicatorOrder().value
        )

    def _context_menu(self):
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested \
                      .connect(self._slot_context_menu)

        menu  = QMenu(self)
        menu.addAction(self.act_restore)
        menu.addAction(self.act_restore_to)
        menu.addAction(self.act_snapshots_dialog)
        menu.addSeparator()
        import icon
        self.btnAddInclude = menu.addAction(icon.ADD, _('Add to Include'))
        self.btnAddExclude = menu.addAction(icon.ADD, _('Add to Exclude'))
        # connect to parent or use (blind) Event class
        self.btnAddInclude.triggered.connect(self._slot_add_to_include)
        self.btnAddExclude.triggered.connect(self._slot_add_to_exclude)
        menu.addSeparator()
        menu.addAction(self.act_show_hidden)

        return menu

    # why pySlot? -> using Qts emit system -> change to own Event class
    @pyqtSlot(int)
    def updateFilesView(self,
                        changed_from,
                        selected_file=None,
                        _show_snapshots=False):
        """
        changed_from? WTF!
            0 - files view change directory,
            1 - files view,
            2 - time_line,
            3 - places
        """
        # update files view
        full_path = self.sid.pathBackup(self.path)

        if os.path.isdir(full_path):

            # proxy should know this by itself!
            if self.showHiddenFiles:
                self.filesViewProxyModel.setFilterRegularExpression(r'')

            else:
                self.filesViewProxyModel.setFilterRegularExpression(r'^[^\.]')

            model_index = self.filesViewModel.setRootPath(full_path)
            proxy_model_index = self.filesViewProxyModel.mapFromSource(
                model_index)

            self.setRootIndex(proxy_model_index)

            # TODO: find a signal for this
            self.window.dirListerCompleted()

    def fileSelected(self, fullPath=False):
        """Return path and index of the currently in Files View highlighted
        (selected) file.

        Args:
            fullPath(bool): Resolve relative to a full path.

        Returns:
            (tuple): Path as a string and the index.
        """
        model_index = self.currentIndex()

        if model_index.column() > 0:
            model_index = model_index.sibling(model_index.row(), 0)

        selected_file = str(self.filesViewProxyModel.data(model_index))

        if selected_file == '/':
            # nothing is selected
            selected_file = ''
            model_index = self.filesViewProxyModel.mapFromSource(
                self.filesViewModel.index(self.path, 0))

        if fullPath:
            # resolve to full path
            selected_file = os.path.join(self.path, selected_file)

        return (selected_file, model_index)

    def multiFileSelected(self, fullPath=False):
        count = 0
        for idx in self.selectedIndexes():
            if idx.column() > 0:
                continue

            selected_file = str(self.filesViewProxyModel.data(idx))

            if selected_file == '/':
                continue

            count += 1

            if fullPath:
                selected_file = os.path.join(self.path, selected_file)

            yield (selected_file, idx)

        if not count:
            # nothing is selected
            idx = self.filesViewProxyModel.mapFromSource(
                self.filesViewModel.index(self.path, 0))

            selected_file = self.path if fullPath else ''

            yield (selected_file, idx)

    def _slot_context_menu(self, point):
        self._context_menu.exec(self.mapToGlobal(point))

    def _MAYBE_slot_files_view_hidden_files_toggled(self, checked: bool):
        self.showHiddenFiles = checked
        self.updateFilesView(1)

    def _slot_item_activated(self, model_index):
        # Dev: move to main window. using an Event signal
        if not model_index:
            return

        # Ctrl button pressed, indicates ongoing multiselection?
        modifiers = self.qapp.keyboardModifiers()
        if Qt.KeyboardModifier.ControlModifier in modifiers:
            return

        rel_path = str(self.filesViewProxyModel.data(model_index))
        if not rel_path:
            return

        self._open_path(rel_path)

    def _slot_add_to_include(self):
        # Dev: move to main window. using an Event signal
        paths = [f for f, idx in self.multiFileSelected(fullPath=True)]
        include = self.config.include()
        updatePlaces = False

        for item in paths:

            if os.path.isdir(item):
                include.append((item, 0))
                updatePlaces = True
            else:
                include.append((item, 1))

        self.config.setInclude(include)

        if updatePlaces:
            self.places.do_update()

    def _slot_add_to_exclude(self):
        # Dev: move to main window. using an Event signal
        paths = [f for f, idx in self.multiFileSelected(fullPath = True)]
        exclude = self.config.exclude()
        exclude.extend(paths)
        self.config.setExclude(exclude)

