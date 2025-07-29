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
"""The manage profiles dialog"""
import re
import copy
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QDialogButtonBox,
                             QInputDialog,
                             QScrollArea,
                             QFrame,
                             QWidget,
                             QTabWidget,
                             QLabel,
                             QPushButton)
import qttools
import messagebox
from pathlib import Path
from statedata import StateData
from manageprofiles.tab_general import GeneralTab
from manageprofiles.tab_remove_retention import RemoveRetentionTab
from manageprofiles.tab_options import OptionsTab
from manageprofiles.tab_expert_options import ExpertOptionsTab
from manageprofiles.tab_include import IncludeTab
from manageprofiles.tab_exclude import ExcludeTab
from restoreconfigdialog import RestoreConfigDialog
from bitwidgets import ProfileCombo


class SettingsDialog(QDialog):
    """The Manage profiles dialog (aka Settings dialog)"""

    def __init__(self, parent):
        super(SettingsDialog, self).__init__(parent)

        self.state_data = StateData()
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
        self.comboProfiles = ProfileCombo(self)
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
        # scrollButtonDefault = self.tabs.usesScrollButtons()
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
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self)
        btnRestore = buttonBox.addButton(
            _('Restore Config'), QDialogButtonBox.ButtonRole.ResetRole)
        # btnUserCallback = buttonBox.addButton(
        #     _('Edit user-callback'), QDialogButtonBox.ButtonRole.ResetRole)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        btnRestore.clicked.connect(self.restoreConfig)
        # btnUserCallback.clicked.connect(self.editUserCallback)
        self.mainLayout.addWidget(buttonBox)

        self.updateProfiles()
        self.slot_combo_modes_changed()

        self._restore_dims_and_coords()

        # enable tabs scroll buttons again but keep dialog size
        # size = self.sizeHint()
        # self.tabs.setUsesScrollButtons(scrollButtonDefault)
        # self.resize(size)

        self.finished.connect(self._slot_finished)

        # Observe other widgets values:
        # "Warn free space" (Options tab) and "Remove at min free space"
        # (Retention & Remove tab). Both widgets/tabs will be informed if
        # the value of the other has changed.
        self._tab_retention.event_remove_free_space_value_changed.register(
            self._tab_options.remove_free_space_value_changed)
        self._tab_options.event_warn_free_space_value_changed.register(
            self._tab_retention.warn_free_space_value_changed)

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
        question = _('Delete the profile "{name}"?').format(
            name=self.config.profileName())

        if self.questionHandler(question):
            self.config.removeProfile()
            self.updateProfiles()

    def profileChanged(self, _index):
        if self.disableProfileChanged:
            return

        current_profile_id = self.comboProfiles.current_profile_id()
        if not current_profile_id:
            return

        if current_profile_id != self.config.currentProfile():
            self.saveProfile()
            self.config.setCurrentProfile(current_profile_id)
            self.updateProfile()

    def _restore_dims_and_coords(self, move=True):
        active_mode = self._tab_general.get_active_snapshots_mode()

        try:
            dims, coords = self.state_data.get_manageprofiles_dims_coords(
                active_mode)

        except KeyError:
            pass

        else:
            if move:
                self.move(*coords)
            self.resize(*dims)

    def updateProfiles(self, reloadSettings=True):
        if reloadSettings:
            self.updateProfile()

        current_profile_id = self.config.currentProfile()

        self.disableProfileChanged = True

        self.comboProfiles.clear()

        qttools.update_combo_profiles(
            self.config, self.comboProfiles, current_profile_id)

        self.disableProfileChanged = False

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
        self._tab_include.load_values(profile_state)

        # TAB: Exclude
        self._tab_exclude.load_values(profile_state)

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

        # TAB: Include
        self._tab_include.store_values(profile_state)

        # TAB: Exclude
        self._tab_exclude.store_values(profile_state)

        return True

    def errorHandler(self, message):
        messagebox.critical(self, message)

    def questionHandler(self, message: str) -> bool:
        return messagebox.question(text=message, widget_to_center_on=self)

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

        # This should raise exceptions in case of errors
        self.config.setup_automation()

        return self.config.save()

    def _ask_include_symlinks_target(self, path: Path):
        question_msg = _(
            '"{path}" is a symlink. The linked target will not be backed up '
            'until it is included, too.').format(path=path)

        question_msg = question_msg + '\n' + _(
            "Include the symlink's target instead?")

        return self.questionHandler(question_msg)

    def slot_combo_modes_changed(self, *_params):
        """Hide/show widget elements related to one of
        the four snapshot modes.

        That slot is connected to a signal in the `GeneralTab`.
        """
        self._tab_general.handle_combo_modes_changed()

        active_mode = self._tab_general.get_active_snapshots_mode()

        self._tab_exclude.mode = active_mode
        self._tab_exclude.update_exclude_items()
        self._tab_exclude.lbl_ssh_encfs_exclude_warning.setVisible(
            active_mode == 'ssh_encfs')

        enabled = active_mode in ('ssh', 'ssh_encfs')
        self._tab_retention.update_items_state(enabled)
        self._tab_expert_options.update_items_state(enabled)

        # Resize (but don't move) dialog based on backup mode
        self._restore_dims_and_coords(move=False)

    def restoreConfig(self, *_args):
        RestoreConfigDialog(self.config).exec()
        self.updateProfiles()

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

        # store windows position and size
        state_data = StateData()
        state_data.set_manageprofiles_dims_coords(
            self._tab_general.get_active_snapshots_mode(),
            (self.width(), self.height()),
            (self.x(), self.y())
        )
