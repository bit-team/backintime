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
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import copy
from PyQt6.QtGui import QPalette, QBrush, QIcon
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QGridLayout,
                             QDialogButtonBox,
                             QMessageBox,
                             QInputDialog,
                             QScrollArea,
                             QFrame,
                             QWidget,
                             QTabWidget,
                             QComboBox,
                             QLabel,
                             QPushButton,
                             QLineEdit,
                             QSpinBox,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QAbstractItemView,
                             QHeaderView,
                             QCheckBox)
from PyQt6.QtCore import Qt
import config
import tools
import qttools
import messagebox
from manageprofiles.tab_general import GeneralTab
from manageprofiles.tab_options import OptionsTab
from manageprofiles.tab_expert_options import ExpertOptionsTab
from editusercallback import EditUserCallback
from restoreconfigdialog import RestoreConfigDialog


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


        # TAB: General
        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.Shape.NoFrame)
        self.tabs.addTab(scrollArea, _('&General'))
        self._tab_general = GeneralTab(self)
        scrollArea.setWidget(self._tab_general)
        scrollArea.setWidgetResizable(True)

        # TAB: Include
        tabWidget = QWidget(self)
        self.tabs.addTab(tabWidget, _('&Include'))
        layout = QVBoxLayout(tabWidget)

        self.listInclude = QTreeWidget(self)
        self.listInclude.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.listInclude.setRootIsDecorated(False)
        self.listInclude.setHeaderLabels(
            [_('Include files and folders'), 'Count'])

        self.listInclude.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.listInclude.header().setSectionsClickable(True)
        self.listInclude.header().setSortIndicatorShown(True)
        self.listInclude.header().setSectionHidden(1, True)
        self.listIncludeSortLoop = False
        self.listInclude.header().sortIndicatorChanged \
            .connect(self.includeCustomSortOrder)

        layout.addWidget(self.listInclude)
        self.listIncludeCount = 0

        buttonsLayout = QHBoxLayout()
        layout.addLayout(buttonsLayout)

        self.btnIncludeFile = QPushButton(icon.ADD, _('Add file'), self)
        buttonsLayout.addWidget(self.btnIncludeFile)
        self.btnIncludeFile.clicked.connect(self.btnIncludeFileClicked)

        self.btnIncludeAdd = QPushButton(icon.ADD, _('Add folder'), self)
        buttonsLayout.addWidget(self.btnIncludeAdd)
        self.btnIncludeAdd.clicked.connect(self.btnIncludeAddClicked)

        self.btnIncludeRemove = QPushButton(icon.REMOVE, _('Remove'), self)
        buttonsLayout.addWidget(self.btnIncludeRemove)
        self.btnIncludeRemove.clicked.connect(self.btnIncludeRemoveClicked)

        # TAB: Exclude
        tabWidget = QWidget(self)
        self.tabs.addTab(tabWidget, _('&Exclude'))
        layout = QVBoxLayout(tabWidget)

        self.lblSshEncfsExcludeWarning = QLabel(_(
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
        self.lblSshEncfsExcludeWarning.setWordWrap(True)
        layout.addWidget(self.lblSshEncfsExcludeWarning)

        self.listExclude = QTreeWidget(self)
        self.listExclude.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.listExclude.setRootIsDecorated(False)
        self.listExclude.setHeaderLabels(
            [_('Exclude patterns, files or folders'), 'Count'])

        self.listExclude.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.listExclude.header().setSectionsClickable(True)
        self.listExclude.header().setSortIndicatorShown(True)
        self.listExclude.header().setSectionHidden(1, True)
        self.listExcludeSortLoop = False
        self.listExclude.header().sortIndicatorChanged \
            .connect(self.excludeCustomSortOrder)

        layout.addWidget(self.listExclude)

        self._label_exclude_recommend = QLabel('', self)
        self._label_exclude_recommend.setWordWrap(True)
        layout.addWidget(self._label_exclude_recommend)

        buttonsLayout = QHBoxLayout()
        layout.addLayout(buttonsLayout)

        self.btnExcludeAdd = QPushButton(icon.ADD, _('Add'), self)
        buttonsLayout.addWidget(self.btnExcludeAdd)
        self.btnExcludeAdd.clicked.connect(self.btnExcludeAddClicked)

        self.btnExcludeFile = QPushButton(icon.ADD, _('Add file'), self)
        buttonsLayout.addWidget(self.btnExcludeFile)
        self.btnExcludeFile.clicked.connect(self.btnExcludeFileClicked)

        self.btnExcludeFolder = QPushButton(icon.ADD, _('Add folder'), self)
        buttonsLayout.addWidget(self.btnExcludeFolder)
        self.btnExcludeFolder.clicked.connect(self.btnExcludeFolderClicked)

        self.btnExcludeDefault = QPushButton(icon.DEFAULT_EXCLUDE,
                                             _('Add default'),
                                             self)
        buttonsLayout.addWidget(self.btnExcludeDefault)
        self.btnExcludeDefault.clicked.connect(self.btnExcludeDefaultClicked)

        self.btnExcludeRemove = QPushButton(icon.REMOVE, _('Remove'), self)
        buttonsLayout.addWidget(self.btnExcludeRemove)
        self.btnExcludeRemove.clicked.connect(self.btnExcludeRemoveClicked)

        # exclude files by size
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        self.cbExcludeBySize = QCheckBox(
            _('Exclude files bigger than:'), self)
        qttools.set_wrapped_tooltip(
            self.cbExcludeBySize,
            [
                _('Exclude files bigger than value in {size_unit}.')
                .format(size_unit='MiB'),
                _("With 'Full rsync mode' disabled, this will only impact "
                  "new files since for rsync, this is a transfer option, not "
                  "an exclusion option. Therefore, large files that have "
                  "been backed up previously will persist in snapshots even "
                  "if they have been modified.")
            ]
        )
        hlayout.addWidget(self.cbExcludeBySize)
        self.spbExcludeBySize = QSpinBox(self)
        self.spbExcludeBySize.setSuffix(' MiB')
        self.spbExcludeBySize.setRange(0, 100000000)
        hlayout.addWidget(self.spbExcludeBySize)
        hlayout.addStretch()
        enabled = lambda state: self.spbExcludeBySize.setEnabled(state)
        enabled(False)
        self.cbExcludeBySize.stateChanged.connect(enabled)

        # TAB: Auto-remove
        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.Shape.NoFrame)
        self.tabs.addTab(scrollArea, _('&Auto-remove'))

        layoutWidget = QWidget(self)
        layout = QGridLayout(layoutWidget)

        # remove old snapshots
        self.cbRemoveOlder = QCheckBox(_('Older than:'), self)
        layout.addWidget(self.cbRemoveOlder, 0, 0)
        self.cbRemoveOlder.stateChanged.connect(self.updateRemoveOlder)

        self.spbRemoveOlder = QSpinBox(self)
        self.spbRemoveOlder.setRange(1, 1000)
        layout.addWidget(self.spbRemoveOlder, 0, 1)

        self.comboRemoveOlderUnit = QComboBox(self)
        layout.addWidget(self.comboRemoveOlderUnit, 0, 2)

        REMOVE_OLD_BACKUP_UNITS = {
            config.Config.DAY: _('Day(s)'),
            config.Config.WEEK: _('Week(s)'),
            config.Config.YEAR: _('Year(s)')}

        self.fillCombo(self.comboRemoveOlderUnit, REMOVE_OLD_BACKUP_UNITS)

        # min free space
        enabled, value, unit = self.config.minFreeSpace()

        self.cbFreeSpace = QCheckBox(
            _('If free space is less than:'), self)
        layout.addWidget(self.cbFreeSpace, 1, 0)
        self.cbFreeSpace.stateChanged.connect(self.updateFreeSpace)

        self.spbFreeSpace = QSpinBox(self)
        self.spbFreeSpace.setRange(1, 1000)
        layout.addWidget(self.spbFreeSpace, 1, 1)

        self.comboFreeSpaceUnit = QComboBox(self)
        layout.addWidget(self.comboFreeSpaceUnit, 1, 2)
        MIN_FREE_SPACE_UNITS = {
            config.Config.DISK_UNIT_MB: 'MiB',
            config.Config.DISK_UNIT_GB: 'GiB'
        }

        self.fillCombo(self.comboFreeSpaceUnit,
                       MIN_FREE_SPACE_UNITS)

        # min free inodes
        self.cbFreeInodes = QCheckBox(
            _('If free inodes is less than:'), self)
        layout.addWidget(self.cbFreeInodes, 2, 0)

        self.spbFreeInodes = QSpinBox(self)
        self.spbFreeInodes.setSuffix(' %')
        self.spbFreeInodes.setSingleStep(1)
        self.spbFreeInodes.setRange(0, 15)
        layout.addWidget(self.spbFreeInodes, 2, 1)

        enabled = lambda state: self.spbFreeInodes.setEnabled(state)
        enabled(False)
        self.cbFreeInodes.stateChanged.connect(enabled)

        # smart remove
        self.cbSmartRemove = QCheckBox(_('Smart removal:'), self)
        layout.addWidget(self.cbSmartRemove, 3, 0)

        widget = QWidget(self)
        widget.setContentsMargins(25, 0, 0, 0)
        layout.addWidget(widget, 4, 0, 1, 3)

        smlayout = QGridLayout(widget)

        self.cbSmartRemoveRunRemoteInBackground = QCheckBox(
            '{} {}!'.format(
                _('Run in background on remote host.'),
                _('EXPERIMENTAL')
            ),
            self)
        smlayout.addWidget(self.cbSmartRemoveRunRemoteInBackground, 0, 0, 1, 3)

        smlayout.addWidget(
            QLabel(_('Keep all snapshots for the last'), self), 1, 0)
        self.spbKeepAll = QSpinBox(self)
        self.spbKeepAll.setRange(1, 10000)
        smlayout.addWidget(self.spbKeepAll, 1, 1)
        smlayout.addWidget(QLabel(_('day(s).'), self), 1, 2)

        smlayout.addWidget(
            QLabel(_('Keep one snapshot per day for the last'), self), 2, 0)
        self.spbKeepOnePerDay = QSpinBox(self)
        self.spbKeepOnePerDay.setRange(1, 10000)
        smlayout.addWidget(self.spbKeepOnePerDay, 2, 1)
        smlayout.addWidget(QLabel(_('day(s).'), self), 2, 2)

        smlayout.addWidget(
            QLabel(_('Keep one snapshot per week for the last'), self), 3, 0)
        self.spbKeepOnePerWeek = QSpinBox(self)
        self.spbKeepOnePerWeek.setRange(1, 10000)
        smlayout.addWidget(self.spbKeepOnePerWeek, 3, 1)
        smlayout.addWidget(QLabel(_('week(s).'), self), 3, 2)

        smlayout.addWidget(
            QLabel(_('Keep one snapshot per month for the last'), self), 4, 0)
        self.spbKeepOnePerMonth = QSpinBox(self)
        self.spbKeepOnePerMonth.setRange(1, 1000)
        smlayout.addWidget(self.spbKeepOnePerMonth, 4, 1)
        smlayout.addWidget(QLabel(_('month(s).'), self), 4, 2)

        smlayout.addWidget(
            QLabel(_('Keep one snapshot per year for all years.'), self),
            5, 0, 1, 3)

        enabled = lambda state: [smlayout.itemAt(x).widget().setEnabled(state) for x in range(smlayout.count())]
        enabled(False)
        self.cbSmartRemove.stateChanged.connect(enabled)

        # don't remove named snapshots
        self.cbDontRemoveNamedSnapshots \
            = QCheckBox(_("Don't remove named snapshots."), self)
        layout.addWidget(self.cbDontRemoveNamedSnapshots, 5, 0, 1, 3)

        #
        layout.addWidget(QWidget(self), 6, 0)
        layout.setRowStretch(6, 2)
        scrollArea.setWidget(layoutWidget)
        scrollArea.setWidgetResizable(True)

        # TAB: Options
        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.Shape.NoFrame)
        self.tabs.addTab(scrollArea, _('&Options'))
        self._tab_options = OptionsTab(self)
        scrollArea.setWidget(self._tab_options)
        scrollArea.setWidgetResizable(True)

        # TAB: Expert Options
        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.Shape.NoFrame)
        self.tabs.addTab(scrollArea, _('E&xpert Options'))
        self._tab_expert_options = ExpertOptionsTab(self)
        scrollArea.setWidget(self._tab_expert_options)
        scrollArea.setWidgetResizable(True)

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
            lambda val: not self.listExclude.findItems(
                val, Qt.MatchFlag.MatchFixedString),
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

    def updateProfile(self):
        if self.config.currentProfile() == '1':
            self.btnEditProfile.setEnabled(False)
            self.btnRemoveProfile.setEnabled(False)
        else:
            self.btnEditProfile.setEnabled(True)
            self.btnRemoveProfile.setEnabled(True)
        self.btnAddProfile.setEnabled(self.config.isConfigured('1'))

        # TAB: General
        self._tab_general.load_values()

        # TAB: Include
        self.listInclude.clear()

        for include in self.config.include():
            self.addInclude(include)

        includeSortColumn = int(
            self.config.profileIntValue('qt.settingsdialog.include.SortColumn',
                                        1)
        )
        includeSortOrder = Qt.SortOrder(
            self.config.profileIntValue('qt.settingsdialog.include.SortOrder',
                                        Qt.SortOrder.AscendingOrder)
        )
        self.listInclude.sortItems(includeSortColumn, includeSortOrder)

        # TAB: Exclude
        self.listExclude.clear()

        for exclude in self.config.exclude():
            self._add_exclude_pattern(exclude)
        self.cbExcludeBySize.setChecked(self.config.excludeBySizeEnabled())
        self.spbExcludeBySize.setValue(self.config.excludeBySize())

        excludeSortColumn = int(self.config.profileIntValue(
            'qt.settingsdialog.exclude.SortColumn', 1))
        excludeSortOrder = Qt.SortOrder(
            self.config.profileIntValue('qt.settingsdialog.exclude.SortOrder',
                                        Qt.SortOrder.AscendingOrder)
        )
        self.listExclude.sortItems(excludeSortColumn, excludeSortOrder)
        self._update_exclude_recommend_label()

        # TAB: Auto-remove

        # remove old snapshots
        enabled, value, unit = self.config.removeOldSnapshots()
        self.cbRemoveOlder.setChecked(enabled)
        self.spbRemoveOlder.setValue(value)
        self.setComboValue(self.comboRemoveOlderUnit, unit)

        # min free space
        enabled, value, unit = self.config.minFreeSpace()
        self.cbFreeSpace.setChecked(enabled)
        self.spbFreeSpace.setValue(value)
        self.setComboValue(self.comboFreeSpaceUnit, unit)

        # min free inodes
        self.cbFreeInodes.setChecked(self.config.minFreeInodesEnabled())
        self.spbFreeInodes.setValue(self.config.minFreeInodes())

        # smart remove
        smart_remove, keep_all, keep_one_per_day, keep_one_per_week, \
            keep_one_per_month = self.config.smartRemove()
        self.cbSmartRemove.setChecked(smart_remove)
        self.spbKeepAll.setValue(keep_all)
        self.spbKeepOnePerDay.setValue(keep_one_per_day)
        self.spbKeepOnePerWeek.setValue(keep_one_per_week)
        self.spbKeepOnePerMonth.setValue(keep_one_per_month)
        self.cbSmartRemoveRunRemoteInBackground.setChecked(
            self.config.smartRemoveRunRemoteInBackground())

        # don't remove named snapshots
        self.cbDontRemoveNamedSnapshots.setChecked(
            self.config.dontRemoveNamedSnapshots())

        # TAB: Options
        self._tab_options.load_values()

        # TAB: Expert Options
        self._tab_expert_options.load_values()

        # update
        self.updateRemoveOlder()
        self.updateFreeSpace()

    def saveProfile(self):
        # Dev note: This return "False" if something goes wrong. Otherwise it
        # returns a dict with several mounting related information.
        success = self._tab_general.store_values()

        if success is False:
            return False

        # include list
        self.config.setProfileIntValue(
            'qt.settingsdialog.include.SortColumn',
            self.listInclude.header().sortIndicatorSection())
        self.config.setProfileIntValue(
            'qt.settingsdialog.include.SortOrder',
            self.listInclude.header().sortIndicatorOrder())
        self.listInclude.sortItems(1, Qt.SortOrder.AscendingOrder)

        include_list = []
        for index in range(self.listInclude.topLevelItemCount()):
            item = self.listInclude.topLevelItem(index)
            include_list.append(
                (item.text(0), item.data(0, Qt.ItemDataRole.UserRole)))

        self.config.setInclude(include_list)

        # exclude patterns
        self.config.setProfileIntValue(
            'qt.settingsdialog.exclude.SortColumn',
            self.listExclude.header().sortIndicatorSection())
        self.config.setProfileIntValue(
            'qt.settingsdialog.exclude.SortOrder',
            self.listExclude.header().sortIndicatorOrder())
        self.listExclude.sortItems(1, Qt.SortOrder.AscendingOrder)

        exclude_list = []
        for index in range(self.listExclude.topLevelItemCount()):
            item = self.listExclude.topLevelItem(index)
            exclude_list.append(item.text(0))

        self.config.setExclude(exclude_list)
        self.config.setExcludeBySize(self.cbExcludeBySize.isChecked(),
                                     self.spbExcludeBySize.value())

        # auto-remove
        self.config.setRemoveOldSnapshots(
                        self.cbRemoveOlder.isChecked(),
                        self.spbRemoveOlder.value(),
                        self.comboRemoveOlderUnit.itemData(
                            self.comboRemoveOlderUnit.currentIndex()))
        self.config.setMinFreeSpace(
                        self.cbFreeSpace.isChecked(),
                        self.spbFreeSpace.value(),
                        self.comboFreeSpaceUnit.itemData(
                            self.comboFreeSpaceUnit.currentIndex()))
        self.config.setMinFreeInodes(
                        self.cbFreeInodes.isChecked(),
                        self.spbFreeInodes.value())
        self.config.setDontRemoveNamedSnapshots(
            self.cbDontRemoveNamedSnapshots.isChecked())
        self.config.setSmartRemove(
                        self.cbSmartRemove.isChecked(),
                        self.spbKeepAll.value(),
                        self.spbKeepOnePerDay.value(),
                        self.spbKeepOnePerWeek.value(),
                        self.spbKeepOnePerMonth.value())
        self.config.setSmartRemoveRunRemoteInBackground(
            self.cbSmartRemoveRunRemoteInBackground.isChecked())

        # options
        self._tab_options.store_values()

        # expert options
        self._tab_expert_options.store_values()

        return True

    def errorHandler(self, message):
        messagebox.critical(self, message)

    def questionHandler(self, message):
        answer = messagebox.warningYesNo(self, message)

        return answer == QMessageBox.StandardButton.Yes

    def updateRemoveOlder(self):
        enabled = self.cbRemoveOlder.isChecked()
        self.spbRemoveOlder.setEnabled(enabled)
        self.comboRemoveOlderUnit.setEnabled(enabled)

    def updateFreeSpace(self):
        enabled = self.cbFreeSpace.isChecked()
        self.spbFreeSpace.setEnabled(enabled)
        self.comboFreeSpaceUnit.setEnabled(enabled)

    def addInclude(self, data):
        item = QTreeWidgetItem()

        # Directory(0) or file(1)?
        if data[1] == 0:
            item.setIcon(0, self.icon.FOLDER)
        else:
            item.setIcon(0, self.icon.FILE)

        # Prevent duplicates
        duplicates = self.listInclude.findItems(
            data[0], Qt.MatchFlag.MatchFixedString)

        if duplicates:
            self.listInclude.setCurrentItem(duplicates[0])
            return

        # First column
        item.setText(0, data[0])
        item.setData(0, Qt.ItemDataRole.UserRole, data[1])
        self.listIncludeCount += 1

        # Second (hidden!) column.
        # Don't know why we need it.
        item.setText(1, str(self.listIncludeCount).zfill(6))
        item.setData(1, Qt.ItemDataRole.UserRole, self.listIncludeCount)

        self.listInclude.addTopLevelItem(item)

        # Select/highlight that entry.
        self.listInclude.setCurrentItem(item)

    def _add_exclude_pattern(self, pattern):
        item = QTreeWidgetItem()
        item.setText(0, pattern)
        item.setData(0, Qt.ItemDataRole.UserRole, pattern)
        self._formatExcludeItem(item)

        # Add item to the widget
        self.listExclude.addTopLevelItem(item)

        return item

    def fillCombo(self, combo, d):
        keys = list(d.keys())
        keys.sort()

        for key in keys:
            combo.addItem(QIcon(), d[key], key)

    def setComboValue(self, combo, value, t='int'):
        for i in range(combo.count()):

            if t == 'int' and value == combo.itemData(i):
                combo.setCurrentIndex(i)
                break

            if t == 'str' and value == combo.itemData(i):
                combo.setCurrentIndex(i)
                break

    def validate(self):
        if not self.saveProfile():
            return False

        if not self.config.checkConfig():
            return False

        if not self.config.setupCron():
            return False

        return self.config.save()

    def btnExcludeRemoveClicked(self):
        for item in self.listExclude.selectedItems():
            index = self.listExclude.indexOfTopLevelItem(item)
            if index < 0:
                continue

            self.listExclude.takeTopLevelItem(index)

        if self.listExclude.topLevelItemCount() > 0:
            self.listExclude.setCurrentItem(self.listExclude.topLevelItem(0))

        self._update_exclude_recommend_label()

    def addExclude(self, pattern):
        """Initiate adding a new exclude pattern to the list widget.

        See `_add_exclude_pattern()` also.
        """
        if not pattern:
            return

        # Duplicate?
        duplicates = self.listExclude.findItems(
            pattern, Qt.MatchFlag.MatchFixedString)

        if duplicates:
            self.listExclude.setCurrentItem(duplicates[0])
            return

        # Create new entry and add it to the list widget.
        item = self._add_exclude_pattern(pattern)

        # Select/highlight that entry.
        self.listExclude.setCurrentItem(item)

        self._update_exclude_recommend_label()

    def btnExcludeAddClicked(self):
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

        self.addExclude(pattern)

    def btnExcludeFileClicked(self):
        for path in qttools.getOpenFileNames(self, _('Exclude file')):
            self.addExclude(path)

    def btnExcludeFolderClicked(self):
        for path in qttools.getExistingDirectories(self, _('Exclude folder')):
            self.addExclude(path)

    def btnExcludeDefaultClicked(self):
        for path in self.config.DEFAULT_EXCLUDE:
            self.addExclude(path)

    def btnIncludeRemoveClicked(self):
        for item in self.listInclude.selectedItems():
            index = self.listInclude.indexOfTopLevelItem(item)
            if index < 0:
                continue

            self.listInclude.takeTopLevelItem(index)

        if self.listInclude.topLevelItemCount() > 0:
            self.listInclude.setCurrentItem(self.listInclude.topLevelItem(0))

    def btnIncludeFileClicked(self):
        """Development Note (buhtz 2023-12):
        This is a candidate for refactoring. See btnIncludeAddClicked() with
        much duplicated code.
        """

        for path in qttools.getOpenFileNames(self, _('Include file')):
            if not path:
                continue

            if os.path.islink(path) \
                and not (self.cbCopyUnsafeLinks.isChecked()
                         or self.cbCopyLinks.isChecked()):

                question_msg = _(
                    '"{path}" is a symlink. The linked target will not be '
                    'backed up until you include it, too.\nWould you like '
                    'to include the symlink target instead?'
                ).format(path=path)

                if self.questionHandler(question_msg):
                    path = os.path.realpath(path)

            path = self.config.preparePath(path)

            for index in range(self.listInclude.topLevelItemCount()):
                if path == self.listInclude.topLevelItem(index).text(0):
                    continue

            self.addInclude((path, 1))

    def btnIncludeAddClicked(self):
        """Development Note (buhtz 2023-12):
        This is a candidate for refactoring. See btnIncludeFileClicked() with
        much duplicated code.
        """
        for path in qttools.getExistingDirectories(self, _('Include folder')):
            if not path:
                continue

            if os.path.islink(path) \
                and not (self.cbCopyUnsafeLinks.isChecked()
                         or self.cbCopyLinks.isChecked()):

                question_msg = _(
                    '"{path}" is a symlink. The linked target will not be '
                    'backed up until you include it, too.\nWould you like '
                    'to include the symlink target instead?') \
                    .format(path=path)
                if self.questionHandler(question_msg):
                    path = os.path.realpath(path)

            path = self.config.preparePath(path)

            for index in range(self.listInclude.topLevelItemCount()):
                if path == self.listInclude.topLevelItem(index).text(0):
                    continue

            self.addInclude((path, 0))

    def slot_combo_modes_changed(self, *params):
        """Hide/show widget elements related to one of
        the four snapshot modes.

        That slot is connected to a signal in the `GeneralTab`.
        """
        self._tab_general.handle_combo_modes_changed()

        active_mode = self._tab_general.get_active_snapshots_mode()

        self.updateExcludeItems()

        enabled = active_mode in ('ssh', 'ssh_encfs')

        self._tab_expert_options.update_items_state(enabled)

        self.cbSmartRemoveRunRemoteInBackground.setVisible(enabled)

    def updateExcludeItems(self):
        for index in range(self.listExclude.topLevelItemCount()):
            item = self.listExclude.topLevelItem(index)
            self._formatExcludeItem(item)

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
        self.listIncludeSortLoop = self.customSortOrder(
            self.listInclude.header(), self.listIncludeSortLoop, *args)

    def excludeCustomSortOrder(self, *args):
        self.listExcludeSortLoop = self.customSortOrder(
            self.listExclude.header(), self.listExcludeSortLoop, *args)

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
