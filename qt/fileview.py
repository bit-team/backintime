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
from functools import partial
from contextlib import contextmanager
# We need to import common/tools.py
import qttools_path
qttools_path.register_backintime_path('common')
# Workaround until the codebase is rectified/equalized.
import tools
tools.initiate_translation(None)
from event import Event
from PyQt6.QtGui import QAction, QFileSystemModel
from PyQt6.QtWidgets import (QAbstractItemView,
                             QApplication,
                             QMenu,
                             QStyledItemDelegate,
                             QTreeView)
from PyQt6.QtCore import (QDir,
                          QItemSelectionModel,
                          QSortFilterProxyModel,
                          Qt,
                          QTimer)
import messagebox
from profile_operations import ProfileOperations


class ProxyModel(QSortFilterProxyModel):
    """Filter between model and view"""

    def __init__(self, parent, model):
        super().__init__(parent)
        self.setDynamicSortFilter(True)
        self.setSourceModel(model)

        self.setFilterRole(Qt.ItemDataRole.DisplayRole)
        self.setFilterKeyColumn(0)
        # self.setRecursiveFilteringEnabled(False)

    def show_hidden(self, show: bool):
        """Set regex based filter to show or hide hidden files."""
        self.setFilterRegularExpression(
            r'' if show else r'^[^\.].*'
        )


class FilesModel(QFileSystemModel):
    """The model containing data about file system elements and structure"""

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

    event_path_clicked = Event()
    # event_proxy_changed = Event()

    def __init__(self,  # pylint: disable=too-many-arguments
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

        # Dev note (buhtz, 2026-01): Don't use doubleClicked signal because
        # it won't catch desktops with single-click-as-double-click settings.
        self.activated.connect(self._slot_item_activated)

    @contextmanager
    def _preserve_selection(self):
        # Helper variable to restore item selection after rebuilding the
        # files view; e.g. in case show-hidden-files state was toggled.
        previous_selection = self.get_selected_paths()

        try:
            yield

        finally:
            # Call asynchronously, to make sure the fileview is ready
            QTimer.singleShot(
                0,
                partial(self.select_paths, previous_selection)
            )

    def set_root_path(self, path: str):
        # self.selectionModel().clear()

        # model: path to read from
        model_index = self.model.setRootPath(path)
        proxy_model_index = self.proxy.mapFromSource(model_index)

        # view: show that path as root path
        self.setRootIndex(proxy_model_index)

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
        self.customContextMenuRequested.connect(self._slot_context_menu)

        menu = QMenu(self)
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

    def select_paths(self, paths: list[str]):
        flag = QItemSelectionModel.SelectionFlag.Select \
            | QItemSelectionModel.SelectionFlag.Rows

        for path in paths:
            src_idx = self.model.index(path)
            proxy_idx = self.proxy.mapFromSource(src_idx)

            if not proxy_idx.isValid():
                # Don't select if it isn't visible
                print(f'dont select ::{path=}')
                continue

            self.selectionModel().select(proxy_idx, flag)

    def show_hidden(self, show: bool):
        with self._preserve_selection():
            self.proxy.show_hidden(show)

    def get_selected_paths(self) -> list[str]:
        """All selected paths

        Returns: Path list as strings
        """
        selection = []

        for proxy_idx in self.selectionModel().selectedRows(0):
            src_idx = self.proxy.mapToSource(proxy_idx)
            path = self.model.filePath(src_idx)
            selection.append(path)

        return selection

    def get_current_path(self) -> str | None:
        """Current selcted path.

        Returns: The path as string.
        """
        proxy_idx = self.selectionModel().currentIndex()

        if not proxy_idx.isValid():
            return None

        src_idx = self.proxy.mapToSource(proxy_idx)

        # visible in proxy?
        if self.proxy.mapFromSource(src_idx) != proxy_idx:
            # no it is hidden
            return None

        return self.model.filePath(src_idx)

    def _slot_context_menu(self, point):
        self._context_menu.exec(self.mapToGlobal(point))

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

    def _slot_add_to_include(self):
        paths = self.get_selected_paths()
        duplicates = self._profile_operations.add_include(paths)

        if len(paths) == len(duplicates):
            messagebox.warning(ngettext(
                'The selected item is already in the include list.',
                'The selected items are already in the include list.',
                len(duplicates)
            ))
        elif len(duplicates):
            messagebox.warning('{}\n\n{}'.format(
                ngettext(
                    'The following item is already in the include list.',
                    'The following items are already in the include list.',
                    len(duplicates)
                ),
                '\n'.join(duplicates)
            ))

    def _slot_add_to_exclude(self):
        paths = self.get_selected_paths()

        duplicates = self._profile_operations.add_exclude(paths)

        if len(paths) == len(duplicates):
            messagebox.warning(ngettext(
                'The selected item is already in the exclude list.',
                'The selected items are already in the exclude list.',
                len(duplicates)
            ))
        elif len(duplicates):
            messagebox.warning('{}\n\n{}'.format(
                ngettext(
                    'The following item is already in the exclude list.',
                    'The following items are already in the exclude list.',
                    len(duplicates)
                ),
                '\n'.join(duplicates)
            ))
