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
    # pylint: disable=too-many-instance-attributes

    def __init__(self, parent):  # noqa: PLR0915
        # pylint: disable=too-many-statements
        super().__init__(parent)

        self.state_data = StateData()
        self.parent = parent
        self.config = parent.config
        self.snapshots = parent.snapshots
        self.config_dict_copy = copy.copy(self.config.dict)
        self.original_current_profile = self.config.currentProfile()

        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415
        self.icon = icon

        self.config.setQuestionHandler(self.questionHandler)
        self.config.setErrorHandler(self.errorHandler)

        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(_('Manage profiles'))

        self._main_layout = QVBoxLayout(self)

        # profiles
        layout = QHBoxLayout()
        self._main_layout.addLayout(layout)

        layout.addWidget(QLabel(_('Profile:'), self))

        self.first_update_all = True
        self.disable_profile_changed = True
        self._combo_profiles = ProfileCombo(self)
        layout.addWidget(self._combo_profiles, 1)
        self._combo_profiles.currentIndexChanged.connect(
            self._slot_profile_changed)
        self.disable_profile_changed = False

        self._btn_edit_profile = QPushButton(
            icon.PROFILE_EDIT, _('Edit'), self)
        self._btn_edit_profile.clicked.connect(self._slot_edit_profile)
        layout.addWidget(self._btn_edit_profile)

        self._btn_add_profile = QPushButton(icon.ADD, _('Add'), self)
        self._btn_add_profile.clicked.connect(self._slot_add_profile)
        layout.addWidget(self._btn_add_profile)

        self._btn_remove_profile = QPushButton(icon.REMOVE, _('Remove'), self)
        self._btn_remove_profile.clicked.connect(self._slot_remove_profile)
        layout.addWidget(self._btn_remove_profile)

        # TABs
        self.tabs = QTabWidget(self)
        self._main_layout.addWidget(self.tabs)

        # occupy whole space for tabs
        # scrollButtonDefault = self.tabs.usesScrollButtons()
        self.tabs.setUsesScrollButtons(False)

        def _add_tab(wdg: QWidget, label: str):
            scroll_area = QScrollArea(self)
            scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
            self.tabs.addTab(scroll_area, label)
            scroll_area.setWidget(wdg)
            scroll_area.setWidgetResizable(True)

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
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self)
        btn_restore = button_box.addButton(
            _('Restore Config'), QDialogButtonBox.ButtonRole.ResetRole)
        # btnUserCallback = buttonBox.addButton(
        #     _('Edit user-callback'), QDialogButtonBox.ButtonRole.ResetRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        btn_restore.clicked.connect(self._slot_restore_config)
        # btnUserCallback.clicked.connect(self.editUserCallback)
        self._main_layout.addWidget(button_box)

        self._update_profiles_combo()
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

    def _slot_add_profile(self):
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
        self._update_profiles_combo()

    def _slot_edit_profile(self):
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

        self._update_profiles_combo(reload_settings=False)

    def _slot_remove_profile(self):
        question = _('Delete the profile "{name}"?').format(
            name=self.config.profileName())

        if self.questionHandler(question):
            self.config.removeProfile()
            self._update_profiles_combo()

    def _slot_profile_changed(self, _index):
        if self.disable_profile_changed:
            return

        current_profile_id = self._combo_profiles.current_profile_id()
        if not current_profile_id:
            return

        if current_profile_id != self.config.currentProfile():
            self.save_profile()
            self.config.setCurrentProfile(current_profile_id)
            self._update_profile()

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

    def _update_profiles_combo(self, reload_settings=True):
        if reload_settings:
            self._update_profile()

        current_profile_id = self.config.currentProfile()

        self.disable_profile_changed = True

        self._combo_profiles.clear()

        qttools.update_combo_profiles(
            self.config, self._combo_profiles, current_profile_id)

        self.disable_profile_changed = False

    def _update_profile(self):
        if self.config.currentProfile() == '1':
            self._btn_edit_profile.setEnabled(False)
            self._btn_remove_profile.setEnabled(False)
        else:
            self._btn_edit_profile.setEnabled(True)
            self._btn_remove_profile.setEnabled(True)
        # self._btn_add_profile.setEnabled(self.config.isConfigured('1'))

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

    def save_profile(self):
        """Save the current profile and its settings"""

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

    # pylint: disable-next=invalid-name
    def errorHandler(self, message):  # noqa: N802
        """Show error in messagebox"""
        messagebox.critical(self, message)

    # pylint: disable-next=invalid-name
    def questionHandler(self, message: str) -> bool:  # noqa: N802
        """Ask question in a question dialog"""
        return messagebox.question(text=message, widget_to_center_on=self)

    # def setComboValue(self, combo, value, t='int'):
    #     for i in range(combo.count()):

    #         if t == 'int' and value == combo.itemData(i):
    #             combo.setCurrentIndex(i)
    #             break

    #         if t == 'str' and value == combo.itemData(i):
    #             combo.setCurrentIndex(i)
    #             break

    def validate(self):
        """Save to config and validate"""
        if not self.save_profile():
            return False

        if not self.config.checkConfig():
            return False

        # This will raise exceptions in case of errors
        self.config.setup_automation()

        return self.config.save()

    def slot_combo_modes_changed(self, *_params):
        """Hide/show widget elements related to one of
        the four snapshot modes.

        That slot is connected to a signal in the `GeneralTab`.
        """
        active_mode = self._tab_general.get_active_snapshots_mode()

        self._tab_general.handle_combo_modes_changed()

        self._tab_exclude.mode = active_mode
        self._tab_exclude.update_exclude_items()
        self._tab_exclude.lbl_ssh_encfs_exclude_warning.setVisible(
            active_mode == 'ssh_encfs')

        enabled = active_mode in ('ssh', 'ssh_encfs')
        self._tab_retention.update_items_state(enabled)
        self._tab_expert_options.update_items_state(enabled)

        # Resize (but don't move) dialog based on backup mode
        self._restore_dims_and_coords(move=False)

    def _slot_restore_config(self, *_args):
        """Handle click on 'Restore config'"""
        RestoreConfigDialog(self.config).exec()
        self._update_profiles_combo()

    def accept(self):
        """OK clicked"""
        if self.validate():
            super().accept()

    def _slot_finished(self, result):
        """Handle dialogs finished signal."""
        self.config.clearHandlers()

        if not result:
            self.config.dict = self.config_dict_copy

        self.config.setCurrentProfile(self.original_current_profile)

        if result:
            # self.parent.remount(self.original_current_profile,
            #                     self.original_current_profile)
            self.parent.updateProfiles()

        # store windows position and size
        state_data = StateData()
        state_data.set_manageprofiles_dims_coords(
            self._tab_general.get_active_snapshots_mode(),
            (self.width(), self.height()),
            (self.x(), self.y())
        )
