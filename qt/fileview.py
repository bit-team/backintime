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
from __future__ import annotations
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
from event import Event
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

class ProxyModel(QSortFilterProxyModel):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.setDynamicSortFilter(True)
        self.setSourceModel(model)


class FilesModel(QFileSystemModel):
    def __init__(self, parent):
        super().__init__(parent)

        self.setRootPath(QDir().rootPath())
        self.setReadOnly(True)
        self.setFilter(
            QDir.Filter.AllDirs |
            QDir.Filter.AllEntries |
            QDir.Filter.NoDotAndDotDot |
            QDir.Filter.Hidden
        )

    def set_sort(self, view: FilesView):
        self.sort(
            view.header().sortIndicatorSection(),
            view.header().sortIndicatorOrder()
        )


class FilesView(QTreeView):
    """File view widget in the main window"""

    def __init__(self,
                 parent,
                 action_restore: QAction,
                 action_restore_to: QAction,
                 action_snapshots_dialog: QAction,
                 action_show_hidden: QAction,
                 sort_column,
                 sort_order):
        super().__init__(parent)

        self._profile_operations = None

        # self.filesView = QTreeView(self)
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setItemsExpandable(False)
        self.setDragEnabled(False)
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)

        # ???
        self.styled_item_delegate = QStyledItemDelegate(self)
        self.setItemDelegate(self.styled_item_delegate)

        self.header().setSectionsClickable(True)
        self.header().setSectionsMovable(False)
        self.header().setSortIndicatorShown(True)

        # = model
        self.model = FilesModel(self)

        # = proxy
        self.proxy = ProxyModel(self, self.model)

        self.setModel(self.proxy)

        # setup sorting
        self.header().setSortIndicator(sort_column, Qt.SortOrder(sort_order))
        self.header().sortIndicatorChanged.connect(self.model.sort)
        self.model.set_sort(self)

        self._context_menu = self._create_context_menu(
                 action_restore,
                 action_restore_to,
                 action_snapshots_dialog,
                 action_show_hidden
        )

        # self._restore_visual_state()

        # self._try_to_mount()

        self.proxy.layoutChanged.connect(self._on_proxy_layout_changed)

        # Dev note (buhtz, 2026-01): Don't use doubleClicked signal because
        # it won't catch desktops with single-click-as-double-click settings.
        self.activated.connect(self._slot_item_activated)

        self.event_path_clicked = Event()
        self.event_proxy_changed = Event()

    def _on_proxy_layout_changed(self):
        """A workaround until app.py::MainWindow.dirListerComplete() is
        refactored.
        """
        self.event_proxy_changed.notify()

    def set_profile_operations(self, pop: ProfileOperations) -> None:
        self._profile_operations = pop

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

    def _create_context_menu(self,
                             action_restore: QAction,
                             action_restore_to: QAction,
                             action_snapshots_dialog: QAction,
                             action_show_hidden: QAction) -> QMenu:
        """Create a menu instance for later reuse as context menu."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested \
                      .connect(self._slot_context_menu)

        menu  = QMenu(self)
        menu.addAction(action_restore)
        menu.addAction(action_restore_to)
        menu.addAction(action_snapshots_dialog)

        menu.addSeparator()

        import icon
        btn_include = menu.addAction(icon.ADD, _('Add to Include'))
        btn_exclude = menu.addAction(icon.ADD, _('Add to Exclude'))
        btn_include.triggered.connect(self._slot_add_to_include)
        btn_exclude.triggered.connect(self._slot_add_to_exclude)

        menu.addSeparator()

        menu.addAction(action_show_hidden)

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
                self.proxy.setFilterRegularExpression(r'')

            else:
                self.proxy.setFilterRegularExpression(r'^[^\.]')

            model_index = self.model.setRootPath(full_path)
            proxy_model_index = self.proxy.mapFromSource(
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

        selected_file = str(self.proxy.data(model_index))

        if selected_file == '/':
            # nothing is selected
            selected_file = ''
            model_index = self.proxy.mapFromSource(
                self.model.index(self.path, 0))

        if fullPath:
            # resolve to full path
            selected_file = os.path.join(self.path, selected_file)

        return (selected_file, model_index)

    def multiFileSelected(self, fullPath=False):
        # ????
        count = 0
        for idx in self.selectedIndexes():
            if idx.column() > 0:
                continue

            selected_file = str(self.proxy.data(idx))

            if selected_file == '/':
                continue

            count += 1

            if fullPath:
                selected_file = os.path.join(self.path, selected_file)

            yield (selected_file, idx)

        if not count:
            # nothing is selected
            idx = self.proxy.mapFromSource(
                self.model.index(self.path, 0))

            selected_file = self.path if fullPath else ''

            yield (selected_file, idx)

    def _slot_context_menu(self, point):
        self._context_menu.exec(self.mapToGlobal(point))

    def _MAYBE_slot_files_view_hidden_files_toggled(self, checked: bool):
        self.showHiddenFiles = checked
        self.updateFilesView(1)

    def _slot_item_activated(self, model_index):
        if not model_index:
            return

        # Ctrl button pressed, indicates ongoing multiselection?
        qapp = QApplication.instance()
        modifiers = qapp.keyboardModifiers()
        if Qt.KeyboardModifier.ControlModifier in modifiers:
            return

        rel_path = str(self.proxy.data(model_index))
        if not rel_path:
            return

        # "double" clicked?
        self.event_path_clicked.notify(rel_path)

        self._open_path(rel_path)

    def _slot_add_to_include(self):
        paths = [f for f, idx in self.multiFileSelected(fullPath=True)]
        self._profile_operations.add_include(paths)

        updatePlaces = True  # False

        # for item in paths:

        #     if os.path.isdir(item):
        #         include.append((item, 0))
        #         updatePlaces = True
        #     else:
        #         include.append((item, 1))

        # self.config.setInclude(include)

        if updatePlaces:
            self.places.do_update()

    def _slot_add_to_exclude(self):
        paths = [f for f, idx in self.multiFileSelected(fullPath = True)]
        self._profile_operations.add_excludes(paths)
