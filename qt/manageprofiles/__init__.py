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
import copy
from PyQt6.QtGui import QPalette, QBrush, QIcon
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QDialogButtonBox,
                             QMessageBox,
                             QInputDialog,
                             QScrollArea,
                             QFrame,
                             QWidget,
                             QTabWidget,
                             QLabel,
                             QPushButton,
                             QSpinBox,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QAbstractItemView,
                             QHeaderView,
                             QCheckBox)
from PyQt6.QtCore import Qt
import tools
import qttools
import messagebox
from statedata import StateData
from manageprofiles.tab_general import GeneralTab
from manageprofiles.tab_remove_retention import RemoveRetentionTab
from manageprofiles.tab_options import OptionsTab
from manageprofiles.tab_expert_options import ExpertOptionsTab
from manageprofiles.tab_include import IncludeTab
from manageprofiles.tab_exclude import ExcludeTab
from editusercallback import EditUserCallback
from restoreconfigdialog import RestoreConfigDialog


MATCH_FLAGS = Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super(SettingsDialog, self).__init__(parent)

        self.parent = parent
        self.config = parent.config
        self.snapshots = parent.snapshots
        self.configDictCopy = copy.copy(self.config.dict)
        self.originalCurrentProfile = self.config.currentProfile()
        import icon
        self.icon = icon

        self.config.setQuestionHandler(self.questionHandler)
        self.config.setErrorHandler(self.errorHandler)

        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(_('Manage profiles'))

        self.mainLayout = QVBoxLayout(self)

        # profiles
        layout = QHBoxLayout()
        self.mainLayout.addLayout(layout)

        layout.addWidget(QLabel(_('Profile:'), self))

        self.firstUpdateAll = True
        self.disableProfileChanged = True
        self.comboProfiles = qttools.ProfileCombo(self)
        layout.addWidget(self.comboProfiles, 1)
        self.comboProfiles.currentIndexChanged.connect(self.profileChanged)
        self.disableProfileChanged = False

        self.btnEditProfile = QPushButton(icon.PROFILE_EDIT, _('Edit'), self)
        self.btnEditProfile.clicked.connect(self.editProfile)
        layout.addWidget(self.btnEditProfile)

        self.btnAddProfile = QPushButton(icon.ADD, _('Add'), self)
        self.btnAddProfile.clicked.connect(self.addProfile)
        layout.addWidget(self.btnAddProfile)

        self.btnRemoveProfile = QPushButton(icon.REMOVE, _('Remove'), self)
        self.btnRemoveProfile.clicked.connect(self.removeProfile)
        layout.addWidget(self.btnRemoveProfile)

        # TABs
        self.tabs = QTabWidget(self)
        self.mainLayout.addWidget(self.tabs)

        # occupy whole space for tabs
        scrollButtonDefault = self.tabs.usesScrollButtons()
        self.tabs.setUsesScrollButtons(False)

        def _add_tab(wdg: QWidget, label: str):
            scrollArea = QScrollArea(self)
            scrollArea.setFrameStyle(QFrame.Shape.NoFrame)
            self.tabs.addTab(scrollArea, label)
            scrollArea.setWidget(wdg)
            scrollArea.setWidgetResizable(True)

        # TAB: General
        self._tab_general = GeneralTab(self)
        _add_tab(self._tab_general, _('&General'))

        # TAB: Include
        self._tab_include = IncludeTab(self)
        _add_tab(self._tab_include, _('&Include'))

        # TAB: Exclude
        self._tab_exclude = ExcludeTab(self)
        _add_tab(self._tab_exclude, _('&Exclude'))

        # TAB: Auto-remove
        self._tab_retention = RemoveRetentionTab(self)
        _add_tab(self._tab_retention,
                 # Mask the "&" character, so Qt does not interpret it as a
                 # shortcut indicator. Doing this via regex to prevent
                 # confusing our translators. hide this from
                 # our translators.
                 re.sub(
                     # "&" followed by whitespace
                     r'&(?=\s)',
                     # replace with this
                     '&&',
                     # act on that string
                     _('&Remove & Retention')
                 ))
        # TAB: Options
        self._tab_options = OptionsTab(self)
        _add_tab(self._tab_options, _('&Options'))

        # TAB: Expert Options
        self._tab_expert_options = ExpertOptionsTab(self)
        _add_tab(self._tab_expert_options, _('E&xpert Options'))

        # buttons
        buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self)
        btnRestore = buttonBox.addButton(
            _('Restore Config'), QDialogButtonBox.ButtonRole.ResetRole)
        btnUserCallback = buttonBox.addButton(
            _('Edit user-callback'), QDialogButtonBox.ButtonRole.ResetRole)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        btnRestore.clicked.connect(self.restoreConfig)
        btnUserCallback.clicked.connect(self.editUserCallback)
        self.mainLayout.addWidget(buttonBox)

        self.updateProfiles()
        self.slot_combo_modes_changed()

        # enable tabs scroll buttons again but keep dialog size
        size = self.sizeHint()
        self.tabs.setUsesScrollButtons(scrollButtonDefault)
        self.resize(size)

        self.finished.connect(self._slot_finished)

    def addProfile(self):
        ret_val = QInputDialog.getText(self, _('New profile'), str())
        if not ret_val[1]:
            return

        name = ret_val[0].strip()
        if not name:
            return

        profile_id = self.config.addProfile(name)
        if profile_id is None:
            return

        self.config.setCurrentProfile(profile_id)
        self.updateProfiles()

    def editProfile(self):
        ret_val = QInputDialog.getText(
            self, _('Rename profile'), str(),
            text=self.config.profileName())

        if not ret_val[1]:
            return

        name = ret_val[0].strip()
        if not name:
            return

        if not self.config.setProfileName(name):
            return

        self.updateProfiles(reloadSettings=False)

    def removeProfile(self):
        question = _('Are you sure you want to delete '
                     'the profile "{name}"?').format(
                         name=self.config.profileName())

        if self.questionHandler(question):
            self.config.removeProfile()
            self.updateProfiles()

    def profileChanged(self, index):
        if self.disableProfileChanged:
            return

        current_profile_id = self.comboProfiles.currentProfileID()
        if not current_profile_id:
            return

        if current_profile_id != self.config.currentProfile():
            self.saveProfile()
            self.config.setCurrentProfile(current_profile_id)
            self.updateProfile()

    def updateProfiles(self, reloadSettings=True):
        if reloadSettings:
            self.updateProfile()

        current_profile_id = self.config.currentProfile()

        self.disableProfileChanged = True

        self.comboProfiles.clear()

        qttools.update_combo_profiles(
            self.config, self.comboProfiles, current_profile_id)

        self.disableProfileChanged = False

    def _update_exclude_recommend_label(self):
        """Update the label about recommended exclude patterns."""

        # Default patterns that are not still in the list widget
        recommend = list(filter(
            lambda val: not self._tab_exclude.listExclude.findItems(val, MATCH_FLAGS),
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

        self._tab_exclude._label_exclude_recommend.setText(text)

    def updateProfile(self):
        if self.config.currentProfile() == '1':
            self.btnEditProfile.setEnabled(False)
            self.btnRemoveProfile.setEnabled(False)
        else:
            self.btnEditProfile.setEnabled(True)
            self.btnRemoveProfile.setEnabled(True)
        self.btnAddProfile.setEnabled(self.config.isConfigured('1'))

        profile_state = StateData().profile(self.config.currentProfile())

        # TAB: General
        self._tab_general.load_values()

        # TAB: Include
        self._tab_include.load_values()

        # TAB: Exclude
        self._tab_exclude.load_values()
        self.cbExcludeBySize.setChecked(self.config.excludeBySizeEnabled())
        self.spbExcludeBySize.setValue(self.config.excludeBySize())

        try:
            incl_sort = profile_state.include_sorting
            excl_sort = profile_state.exclude_sorting
            self._tab_include.listInclude.sortItems(
                incl_sort[0], Qt.SortOrder(incl_sort[1])
            )
            self._tab_exclude.listExclude.sortItems(
                excl_sort[0], Qt.SortOrder(excl_sort[1]))
        except KeyError:
            pass

        self._update_exclude_recommend_label()

        self._tab_retention.load_values()
        self._tab_options.load_values()
        self._tab_expert_options.load_values()

    def saveProfile(self):
        # These tabs need to be stored before the Generals tab, because the
        # latter is doing some premount checking and need to know this settings
        # first.
        self._tab_retention.store_values()
        self._tab_options.store_values()
        self._tab_expert_options.store_values()

        # Dev note: This return "False" if something goes wrong. Otherwise it
        # returns a dict with several mounting related information.
        success = self._tab_general.store_values()

        if success is False:
            return False

        profile_state = StateData().profile(self.config.currentProfile())

        # include list
        profile_state.include_sorting = (
            self._tab_include.listInclude.header().sortIndicatorSection(),
            self._tab_include.listInclude.header().sortIndicatorOrder().value
        )
        # Why?
        self._tab_include.listInclude.sortItems(1, Qt.SortOrder.AscendingOrder)

        include_list = []
        for index in range(self._tab_include.listInclude.topLevelItemCount()):
            item = self._tab_include.listInclude.topLevelItem(index)
            include_list.append(
                (item.text(0), item.data(0, Qt.ItemDataRole.UserRole)))

        self.config.setInclude(include_list)

        # exclude patterns
        profile_state.exclude_sorting = (
            self._tab_exclude.listExclude.header().sortIndicatorSection(),
            self._tab_exclude.listExclude.header().sortIndicatorOrder().value
        )
        # Why?
        self._tab_exclude.listExclude.sortItems(1, Qt.SortOrder.AscendingOrder)

        exclude_list = []
        for index in range(self._tab_exclude.listExclude.topLevelItemCount()):
            item = self._tab_exclude.listExclude.topLevelItem(index)
            exclude_list.append(item.text(0))

        self.config.setExclude(exclude_list)
        self.config.setExcludeBySize(self.cbExcludeBySize.isChecked(),
                                     self.spbExcludeBySize.value())

        return True

    def errorHandler(self, message):
        messagebox.critical(self, message)

    def questionHandler(self, message):
        answer = messagebox.warningYesNo(self, message)

        return answer == QMessageBox.StandardButton.Yes

    def validate(self):
        if not self.saveProfile():
            return False

        if not self.config.checkConfig():
            return False

        if not self.config.setupCron():
            return False

        return self.config.save()

    def slot_combo_modes_changed(self, *params):
        """Hide/show widget elements related to one of
        the four snapshot modes.

        That slot is connected to a signal in the `GeneralTab`.
        """
        self._tab_general.handle_combo_modes_changed()

        active_mode = self._tab_general.get_active_snapshots_mode()

        enabled = active_mode in ('ssh', 'ssh_encfs')

        self.updateExcludeItems()

        self._tab_retention.update_items_state(enabled)
        self._tab_expert_options.update_items_state(enabled)

    def updateExcludeItems(self):
        for index in range(self._tab_exclude.listExclude.topLevelItemCount()):
            item = self._tab_exclude.listExclude.topLevelItem(index)
            self._tab_exclude._formatExcludeItem(item)

    def _format_exclude_item_encfs_invalid(self, item):
        """Modify visual appearance of an item in the exclude list widget to
        express that the item is invalid.

        See :py:func:`_formatExcludeItem` for details.
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

    def _formatExcludeItem(self, item):
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

    def customSortOrder(self, header, loop, newColumn, newOrder):

        if newColumn == 0 and newOrder == Qt.SortOrder.AscendingOrder:

            if loop:
                newColumn, newOrder = 1, Qt.SortOrder.AscendingOrder
                header.setSortIndicator(newColumn, newOrder)
                loop = False

            else:
                loop = True

        header.model().sort(newColumn, newOrder)

        return loop

    def includeCustomSortOrder(self, *args):
        self._tab_include.listIncludeSortLoop = self.customSortOrder(
            self._tab_include.listInclude.header(), self._tab_include.listIncludeSortLoop, *args)

    def excludeCustomSortOrder(self, *args):
        self._tab_exclude.listExcludeSortLoop = self.customSortOrder(
            self._tab_exclude.listExclude.header(), self._tab_exclude.listExcludeSortLoop, *args)

    def restoreConfig(self, *args):
        RestoreConfigDialog(self).exec()
        self.updateProfiles()

    def editUserCallback(self, *args):
        EditUserCallback(self).exec()

    def accept(self):
        if self.validate():
            super(SettingsDialog, self).accept()

    def _slot_finished(self, result):
        """Handle dialogs finished signal."""
        self.config.clearHandlers()

        if not result:
            self.config.dict = self.configDictCopy

        self.config.setCurrentProfile(self.originalCurrentProfile)

        if result:
            self.parent.remount(self.originalCurrentProfile,
                                self.originalCurrentProfile)
            self.parent.updateProfiles()
