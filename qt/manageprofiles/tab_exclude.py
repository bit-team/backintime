# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raak
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2025 Devin Black
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.

from PyQt6.QtWidgets import (QWidget,
                             QVBoxLayout,
                             QLabel,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QPushButton,
                             QHBoxLayout,
                             QCheckBox,
                             QSpinBox,
                             QInputDialog,
                             QHeaderView,
                             QAbstractItemView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QBrush
import tools
import qttools
from qttools import custom_sort_order
from filedialog import FileDialog

MATCH_FLAGS = Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive


class ExcludeTab(QWidget):
    """Create the 'Exclude' tab."""

    def __init__(self, parent):
        super().__init__(parent=parent)

        self._parent_dialog = parent
        self.icon = parent.icon
        self.config = parent.config

        # Snapshot mode
        self.mode = None

        layout = QVBoxLayout(self)

        self.lbl_ssh_encfs_exclude_warning = QLabel(_(
            "{BOLD}Info{ENDBOLD}: "
            "In 'SSH encrypted' mode, only single or double asterisks are "
            "functional (e.g. {example2}). Other types of wildcards and "
            "patterns will be ignored (e.g. {example1}). Filenames are "
            "unpredictable in this mode due to encryption by EncFS.").format(
                BOLD='<strong>',
                ENDBOLD='</strong>',
                example1="<code>'foo*'</code>, "
                         "<code>'[fF]oo'</code>, "
                         "<code>'fo?'</code>",
                example2="<code>'foo/*'</code>, "
                         "<code>'foo/**/bar'</code>"
            ),
            self
        )
        self.lbl_ssh_encfs_exclude_warning.setWordWrap(True)
        layout.addWidget(self.lbl_ssh_encfs_exclude_warning)

        self.list_exclude = QTreeWidget(self)
        self.list_exclude.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_exclude.setRootIsDecorated(False)
        self.list_exclude.setHeaderLabels(
            [_('Exclude patterns, files or directories'), 'Count'])

        self.list_exclude.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.list_exclude.header().setSectionsClickable(True)
        self.list_exclude.header().setSortIndicatorShown(True)
        self.list_exclude.header().setSectionHidden(1, True)
        self.list_exclude_sort_loop = False
        self.list_exclude.header().sortIndicatorChanged \
            .connect(self.exclude_custom_sort_order)

        layout.addWidget(self.list_exclude)

        self._label_exclude_recommend = QLabel('', self)
        self._label_exclude_recommend.setWordWrap(True)
        layout.addWidget(self._label_exclude_recommend)

        buttons_layout = QHBoxLayout()
        layout.addLayout(buttons_layout)

        self.btn_exclude_add = QPushButton(self.icon.ADD, _('Add'), self)
        buttons_layout.addWidget(self.btn_exclude_add)
        self.btn_exclude_add.clicked.connect(self.btn_exclude_add_clicked)

        self.btn_exclude_file = QPushButton(
            self.icon.ADD, _('Add files'), self)
        buttons_layout.addWidget(self.btn_exclude_file)
        self.btn_exclude_file.clicked.connect(self.btn_exclude_file_clicked)

        self.btn_exclude_folder = QPushButton(
            self.icon.ADD, _('Add directories'), self)
        buttons_layout.addWidget(self.btn_exclude_folder)
        self.btn_exclude_folder.clicked.connect(
            self.btn_exclude_folder_clicked)

        self.btn_exclude_default = QPushButton(
            self.icon.DEFAULT_EXCLUDE, _('Add default'), self)
        buttons_layout.addWidget(self.btn_exclude_default)
        self.btn_exclude_default.clicked.connect(
            self.btn_exclude_default_clicked)

        self.btn_exclude_remove = QPushButton(
            self.icon.REMOVE, _('Remove'), self)
        buttons_layout.addWidget(self.btn_exclude_remove)
        self.btn_exclude_remove.clicked.connect(
            self.btn_exclude_remove_clicked)

        # exclude files by size
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        self.cb_exclude_by_size = QCheckBox(
            _('Exclude files bigger than:'), self)
        qttools.set_wrapped_tooltip(
            self.cb_exclude_by_size,
            [
                _('Exclude files bigger than value in {size_unit}.')
                .format(size_unit='MiB'),
                _("With 'Full rsync mode' disabled, this setting affects only "
                  "newly created files, as rsync treats it as transfer option "
                  "rather than an exclusion rule. Consequently, large files "
                  "that have already been backed up will remain in backups "
                  "even if they are modified.")
            ]
        )
        hlayout.addWidget(self.cb_exclude_by_size)
        self.spb_exclude_by_size = QSpinBox(self)
        self.spb_exclude_by_size.setSuffix(' MiB')
        self.spb_exclude_by_size.setRange(0, 100000000)
        hlayout.addWidget(self.spb_exclude_by_size)
        hlayout.addStretch()
        enabled = lambda state: self.spb_exclude_by_size.setEnabled(state)
        enabled(False)
        self.cb_exclude_by_size.stateChanged.connect(enabled)

    def load_values(self, profile_state):
        self.list_exclude.clear()

        for exclude in self.config.exclude():
            self._add_exclude_pattern(exclude)
        self.cb_exclude_by_size.setChecked(self.config.excludeBySizeEnabled())
        self.spb_exclude_by_size.setValue(self.config.excludeBySize())
        self._update_exclude_recommend_label()

        try:
            excl_sort = profile_state.exclude_sorting
            self.list_exclude.sortItems(
                excl_sort[0], Qt.SortOrder(excl_sort[1])
            )
        except KeyError:
            pass

    def store_values(self, profile_state):
        # exclude patterns
        profile_state.exclude_sorting = (
            self.list_exclude.header().sortIndicatorSection(),
            self.list_exclude.header().sortIndicatorOrder().value
        )
        # Sort (optional: replicates original behavior)
        self.list_exclude.sortItems(1, Qt.SortOrder.AscendingOrder)

        # Store exclude list
        exclude_list = []
        for index in range(self.list_exclude.topLevelItemCount()):
            item = self.list_exclude.topLevelItem(index)
            exclude_list.append(item.text(0))
        self.config.setExclude(exclude_list)

        # Store "exclude by size" settings
        self.config.setExcludeBySize(
            self.cb_exclude_by_size.isChecked(),
            self.spb_exclude_by_size.value()
        )

        return True

    def _update_exclude_recommend_label(self):
        """Update the label about recommended exclude patterns."""

        # Default patterns that are not still in the list widget
        recommend = list(filter(
            lambda val: not self.list_exclude.findItems(val, MATCH_FLAGS),
            self.config.DEFAULT_EXCLUDE
        ))

        if not recommend:
            text = _('{BOLD}Highly recommended{ENDBOLD}: (All recommendations '
                     'already included.)').format(
                        BOLD='<strong>', ENDBOLD='</strong>')

        else:
            text = _('{BOLD}Highly recommended{ENDBOLD}: {files}').format(
                BOLD='<strong>',
                ENDBOLD='</strong>',
                files=', '.join(sorted(recommend)))

        self._label_exclude_recommend.setText(text)

    def _add_exclude_pattern(self, pattern):
        item = QTreeWidgetItem()
        item.setText(0, pattern)
        item.setData(0, Qt.ItemDataRole.UserRole, pattern)
        self._format_exclude_item(item)

        # Add item to the widget
        self.list_exclude.addTopLevelItem(item)

        return item

    def btn_exclude_remove_clicked(self):
        for item in self.list_exclude.selectedItems():
            index = self.list_exclude.indexOfTopLevelItem(item)
            if index < 0:
                continue

            self.list_exclude.takeTopLevelItem(index)

        if self.list_exclude.topLevelItemCount() > 0:
            self.list_exclude.setCurrentItem(self.list_exclude.topLevelItem(0))

        self._update_exclude_recommend_label()

    def add_exclude(self, pattern):
        """Initiate adding a new exclude pattern to the list widget.

        See `_add_exclude_pattern()` also.
        """
        if not pattern:
            return

        # Duplicate?
        duplicates = self.list_exclude.findItems(pattern, MATCH_FLAGS)

        if duplicates:
            # TODO notify user about duplicates
            self.list_exclude.setCurrentItem(duplicates[0])
            return

        # Create new entry and add it to the list widget.
        item = self._add_exclude_pattern(pattern)

        # Select/highlight that entry.
        self.list_exclude.setCurrentItem(item)

        self._update_exclude_recommend_label()

    def btn_exclude_add_clicked(self):
        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.InputMode.TextInput)
        dlg.setWindowTitle(_('Exclude pattern'))
        dlg.setLabelText('')
        dlg.resize(400, 0)
        if not dlg.exec():
            return
        pattern = dlg.textValue().strip()

        if not pattern:
            return

        self.add_exclude(pattern)

    def btn_exclude_file_clicked(self):
        for path in qttools.getOpenFileNames(self, _('Exclude files')):
            self.add_exclude(path)

    def btn_exclude_folder_clicked(self):
        # pylint: disable=duplicate-code
        dlg = FileDialog(parent=self,
                         title=_('Exclude directories'),
                         show_hidden=True,
                         allow_multiselection=True,
                         dirs_only=True)
        dirs = dlg.result()

        for path in dirs:
            self.add_exclude(str(path))

    def btn_exclude_default_clicked(self):
        for path in self.config.DEFAULT_EXCLUDE:
            self.add_exclude(path)

    def update_exclude_items(self):
        for index in range(self.list_exclude.topLevelItemCount()):
            item = self.list_exclude.topLevelItem(index)
            self._format_exclude_item(item)

    def _format_exclude_item_encfs_invalid(self, item):
        """Modify visual appearance of an item in the exclude list widget to
        express that the item is invalid.

        See :py:func:`_format_exclude_item` for details.
        """
        # Icon
        item.setIcon(0, self.icon.INVALID_EXCLUDE)

        # ToolTip
        item.setData(
            0,
            Qt.ItemDataRole.ToolTipRole,
            _("Disabled because this pattern is not functional in "
              "mode 'SSH encrypted'.")
        )

        # Fore- and Backgroundcolor (as disabled)
        item.setBackground(0, QPalette().brush(QPalette.ColorGroup.Disabled,
                                               QPalette.ColorRole.Window))
        item.setForeground(0, QPalette().brush(QPalette.ColorGroup.Disabled,
                                               QPalette.ColorRole.Text))

    def _format_exclude_item(self, item):
        """Modify visual appearance of an item in the exclude list widget.
        """
        if (self.mode == 'ssh_encfs'
                and tools.patternHasNotEncryptableWildcard(item.text(0))):
            # Invalid item (because of encfs restrictions)
            self._format_exclude_item_encfs_invalid(item)

        else:
            # default background color
            item.setBackground(0, QBrush())
            item.setForeground(0, QBrush())

            # Remove items tooltip
            item.setData(0, Qt.ItemDataRole.ToolTipRole, None)

            # Icon: default exclude item
            if item.text(0) in self.config.DEFAULT_EXCLUDE:
                item.setIcon(0, self.icon.DEFAULT_EXCLUDE)

            else:
                # Icon: user defined
                item.setIcon(0, self.icon.EXCLUDE)

    def exclude_custom_sort_order(self, *args):
        self.list_exclude_sort_loop = custom_sort_order(
            self.list_exclude.header(), self.list_exclude_sort_loop, *args)
