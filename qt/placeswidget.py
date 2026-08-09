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
"""Module offering the Places widget in the main window.
"""
import os
import pathlib
from PyQt6.QtWidgets import (QAbstractItemView,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QWidget)
from PyQt6.QtGui import QFont, QIcon, QPalette
from PyQt6.QtCore import Qt
import bitbase
import konfig
import config
import logger
from profilecontext import ProfileContext
from profile_operations import ProfileOperations


class PlacesWidget(QTreeWidget):
    """A tree widget used in the main window.

    It contain the file system root and current users home directory as entry
    points. It also contain all included backup directories as entries.
    """

    def __init__(self, parent: QWidget, cfg: config.Config):
        QTreeWidget.__init__(self, parent=parent)

        self.config = cfg
        self.parent = parent

        self._profile_operations = None

        # Do not show controls for expanding and collapsing top-level items
        self.setRootIsDecorated(False)

        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.setHeaderLabel(_('Shortcuts'))

        self.header().setSectionsClickable(True)
        self.header().setSortIndicatorShown(True)
        self.header().setSectionHidden(1, True)

        self.header().sortIndicatorChanged.connect(
            self._on_sort_indicator_changed)

        # previous and new item given as arguments
        self.currentItemChanged.connect(self._slot_changed)

    def _on_sort_indicator_changed(self, _column: int):
        self.do_update()

    def set_profile_operations(self, pop: ProfileOperations) -> None:
        """Connect an `ProfileOperations` instance and register
        event callbacks to it.
        """
        self._profile_operations = pop
        self._profile_operations.event_dir_added_to_include.register(
            self._handle_new_dir_included
        )

    def _handle_new_dir_included(self):
        self.do_update()

    def on_now_selected(self):
        """Event handler if 'Now' entry in timeline was selected"""
        self.do_update(now_selected=True)

    def on_backup_changed(self, _sid):
        """Event handler if a backup entry in timeline was selected"""
        self.do_update(now_selected=False)

    def do_update(self, now_selected: bool | None = None) -> None:
        """Update the places view"""

        # Workaround
        if now_selected is None:
            now_selected = self.parent.is_now_selected()

        self.clear()

        # name, path, icon
        self._add_place(_('Places'), '', '')
        self._add_place(_('File System'), '/', 'computer')

        fp_home = pathlib.Path.home()
        home_item = self._add_place(
            # Use full path in root mode ("/root") otherwise users name only
            str(fp_home) if bitbase.IS_IN_ROOT_MODE else fp_home.name,
            str(fp_home),
            'user-home'
        )

        # formally known as self.sid
        backup_id = self.parent.selected_backup_id()

        include_dirs = None

        # "Now" or no specific backup selected?
        if now_selected or backup_id is None:
            include_dirs = ProfileContext().profile.include_directories

        else:
            # Check the config file which is stored in the backup itself
            cfg_fp = pathlib.Path(backup_id.path()) / 'config'

            try:
                with konfig.load_archived_config(cfg_fp) as acfg:
                    ap = acfg.profile(ProfileContext().profile.profile_id)
                    include_dirs = ap.include_directories

            # pylint: disable-next=broad-exception-caught
            except Exception as exc:  # noqa
                logger.critical(
                    'Unexpected problem while loading archived config file '
                    f'from {cfg_fp}. {exc!s}'
                )

                # Fallback if something unexpected went wrong
                include_dirs = self._determine_include_dirs_fallback(backup_id)

        if include_dirs:

            if not self.header().sortIndicatorSection():
                indic = self.header().sortIndicatorOrder()
                reverse = indic == Qt.SortOrder.DescendingOrder
                include_dirs = sorted(include_dirs, reverse=reverse)

            self._add_place(_('Backup directories'), '', '')

            for folder in include_dirs:
                self._add_place(folder, folder, 'document-save')

            # Select "home" if nothing is selected
            if self.currentItem() is None:
                self.setCurrentItem(home_item)

    def _determine_include_dirs_fallback(self, backup_id) -> list[str] | None:
        """Determine the include dirs in the selected backup.

        Usually this information is taken from the archived config file
        stored in the specfici backup. If this fails for some reasons
        the include dirs are determined from the real filesystem and the
        backups structure.
        """
        logger.debug(
            f'Determine include dirs for {backup_id} from filesystem.'
        )

        # Workaround
        backup_path = pathlib.Path(backup_id.path()) / 'backup' \
            / str(pathlib.Path.home())[1:]

        # Determine directories from the backup itself
        base = os.path.expanduser('~')
        if not backup_path.exists():
            return None

        folders = [
            fp.name for fp in backup_path.iterdir() if fp.is_dir()
        ]

        include_entries = [(os.path.join(base, f), 0) for f in folders]

        # Use folders only (if 2nd tuple entry is 0)
        only_folders = filter(lambda entry: entry[1] == 0, include_entries)

        return [item[0] for item in only_folders]

    def _add_place(self, name, path, icon) -> QTreeWidgetItem:
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
            font = item.font(0)
            font.setWeight(QFont.Weight.Bold)
            item.setFont(0, font)

            # item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(
                0, self.palette().color(QPalette.ColorRole.PlaceholderText))
            item.setBackground(
                0, self.palette().color(QPalette.ColorRole.AlternateBase))

        self.addTopLevelItem(item)

        if path == self.parent.path:
            self.setCurrentItem(item)

        return item

    def _slot_changed(self, item, _previous):
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

    def get_sorting(self) -> tuple[int, int]:
        """Current sorting column and order as a tuple."""
        return (
            self.header().sortIndicatorSection(),
            self.header().sortIndicatorOrder().value
        )

    def set_sorting(self, sorting: tuple[int, int]) -> None:
        """Set sorting."""
        self.header().setSortIndicator(sorting[0], Qt.SortOrder(sorting[1]))
