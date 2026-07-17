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
"""Module about the General tab"""
# pylint: disable=wrong-import-order
import os
from pathlib import Path
from typing import Any
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox,
                             QDialog,
                             QGridLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QLineEdit,
                             QToolButton,
                             QVBoxLayout)
from config import Config
import tools
import logger
import sshtools
from bitbase import DIR_SSH_KEYS
import version
import schedule
import qttools
import messagebox
import core_events
from manageprofiles import combobox, schedulewidget
from manageprofiles.sshproxywidget import SshProxyWidget
from manageprofiles.sshkeyselector import SshKeySelector
from filedialog import FileDialog
from mount import MountManager, MountError
from sshsetupvalidator import SSHSetupValidator, SSHSetupError


class GeneralTab(QDialog):
    """Create the 'Generals' tab."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, parent):  # noqa: PLR0915
        # pylint: disable=too-many-statements
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        # Snapshot mode
        self.mode = None

        vlayout = QVBoxLayout()
        tab_layout.addLayout(vlayout)

        self._combo_modes = self._snapshot_mode_combobox()
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel(_('Mode:'), self))
        hlayout.addWidget(self._combo_modes, 1)
        vlayout.addLayout(hlayout)

        # Where to save snapshots
        group_box = QGroupBox(self)
        self._group_mode_local = group_box
        group_box.setTitle(_('Where to save backups'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)

        hlayout = QHBoxLayout()
        vlayout.addLayout(hlayout)

        self._edit_backup_path = QLineEdit(self)
        self._edit_backup_path.setReadOnly(True)
        self._edit_backup_path.textChanged.connect(
            self._slot_full_path_changed)
        hlayout.addWidget(self._edit_backup_path)

        self._btn_backup_path = QToolButton(self)
        self._btn_backup_path.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._btn_backup_path.setIcon(self.icon.FOLDER)
        self._btn_backup_path.setMinimumSize(32, 28)
        hlayout.addWidget(self._btn_backup_path)
        self._btn_backup_path.clicked.connect(
            self._slot_snapshots_path_clicked)

        # --- SSH ---
        group_box = QGroupBox(self)
        self._group_mode_ssh = group_box
        group_box.setTitle(_('SSH Settings'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)

        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)
        # hlayout3 = QHBoxLayout()
        # vlayout.addLayout(hlayout3)

        self._lbl_ssh_host = QLabel(_('Host:'), self)
        hlayout1.addWidget(self._lbl_ssh_host)
        self._txt_ssh_host = QLineEdit(self)
        hlayout1.addWidget(self._txt_ssh_host)

        self._lbl_ssh_port = QLabel(_('Port:'), self)
        hlayout1.addWidget(self._lbl_ssh_port)
        self._txt_ssh_port = QLineEdit(self)
        hlayout1.addWidget(self._txt_ssh_port)

        self._lbl_ssh_user = QLabel(_('User:'), self)
        hlayout1.addWidget(self._lbl_ssh_user)
        self._txt_ssh_user = QLineEdit(self)
        hlayout1.addWidget(self._txt_ssh_user)

        self._lbl_ssh_path = QLabel(_('Path:'), self)
        hlayout2.addWidget(self._lbl_ssh_path)
        self._txt_ssh_path = QLineEdit(self)
        self._txt_ssh_path.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self._txt_ssh_path)

        group_box = QGroupBox(self)
        group_box.setTitle(_('Key file:'))
        group_layout = QVBoxLayout()
        group_box.setLayout(group_layout)
        self.key_selector = SshKeySelector(
            self,
            self._slot_ssh_private_key_file_clicked,
            self._slot_ssh_key_gen_clicked
        )
        group_layout.addWidget(self.key_selector)
        vlayout.addWidget(group_box)

        # Align the width of that three labels
        width = max(
            self._lbl_ssh_host.sizeHint().width(),
            self._lbl_ssh_path.sizeHint().width()
        )
        self._lbl_ssh_host.setMinimumWidth(width)
        self._lbl_ssh_path.setMinimumWidth(width)

        self._wdg_ssh_proxy = SshProxyWidget(
            self,
            self.config.sshProxyHost(),
            self.config.sshProxyPort(),
            self.config.sshProxyUser()
        )
        vlayout.addWidget(self._wdg_ssh_proxy)

        # # encfs
        # self._group_mode_local_encfs = self._group_mode_local
        # self._group_mode_ssh_encfs = self._group_mode_ssh

        # gocryptfs
        self._group_mode_local_gocrypt = self._group_mode_local

        # password
        group_box = QGroupBox(self)
        self._group_password1 = group_box
        group_box.setTitle(_('Password'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)

        grid = QGridLayout()

        # Used for SSH passphrase & Gocryptfs password
        self._lbl_password1 = QLabel(_('Password'), self)
        self._txt_password1 = QLineEdit(self)
        self._txt_password1.setEchoMode(QLineEdit.EchoMode.Password)

        # Used for gocryptfs password in "ssh encrypted" mode *rofl*
        self._lbl_password2 = QLabel(_('Password'), self)
        self._txt_password2 = QLineEdit(self)
        self._txt_password2.setEchoMode(QLineEdit.EchoMode.Password)

        # DEBUG
        if logger.DEBUG or version.IS_UNSTABLE_DEV_VERSION:
            self._lbl_password1.setToolTip('DEBUG - password 1')
            self._txt_password1.setToolTip('DEBUG - password 1')
            self._lbl_password2.setToolTip('DEBUG - password 2')
            self._txt_password2.setToolTip('DEBUG - password 2')

        grid.addWidget(self._lbl_password1, 0, 0)
        grid.addWidget(self._txt_password1, 0, 1)
        grid.addWidget(self._lbl_password2, 1, 0)
        grid.addWidget(self._txt_password2, 1, 1)
        vlayout.addLayout(grid)

        self._cb_password_save = QCheckBox(_('Save Password to Keyring'), self)
        vlayout.addWidget(self._cb_password_save)

        self._cb_password_use_cache = QCheckBox(
            _('Cache Password for Cron (Security '
              'issue: root can read password)'),
            self
        )
        vlayout.addWidget(self._cb_password_use_cache)

        self._keyring_supported = tools.KEYRING_SUPPORTED
        self._cb_password_save.setEnabled(self._keyring_supported)

        # mode change
        self._combo_modes.currentIndexChanged.connect(
            self._parent_dialog.slot_combo_modes_changed)

        # host, user, profile id
        group_box = QGroupBox(self)
        self._frame_advanced = group_box
        group_box.setTitle(_('Advanced'))
        tab_layout.addWidget(group_box)

        hlayout = QHBoxLayout(group_box)
        hlayout.addSpacing(12)

        vlayout2 = QVBoxLayout()
        hlayout.addLayout(vlayout2)

        hlayout2 = QHBoxLayout()
        vlayout2.addLayout(hlayout2)

        self._lbl_host = QLabel(_('Host:'), self)
        hlayout2.addWidget(self._lbl_host)
        self._txt_host = QLineEdit(self)
        self._txt_host.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self._txt_host)

        self._lbl_user = QLabel(_('User:'), self)
        hlayout2.addWidget(self._lbl_user)
        self._txt_user = QLineEdit(self)
        self._txt_user.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self._txt_user)

        self._lbl_profile = QLabel(_('Profile:'), self)
        hlayout2.addWidget(self._lbl_profile)
        self.txt_profile = QLineEdit(self)
        self.txt_profile.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self.txt_profile)

        self._lbl_full_path = QLabel(_('Full backup path:'), self)
        self._lbl_full_path.setWordWrap(True)
        vlayout2.addWidget(self._lbl_full_path)

        self._wdg_schedule = schedulewidget.ScheduleWidget(self)

        if schedule.CRONTAB_COMMAND is None:
            lbl_warning = qttools.create_info_label(
                text=_('Scheduling is disabled because no cron installation '
                       'was found. Please install cron to enable scheduled '
                       'backups.')
            )
            tab_layout.addWidget(lbl_warning)

            self._wdg_schedule.setHidden(True)

        tab_layout.addWidget(self._wdg_schedule)

        tab_layout.addStretch()

    @property
    def mode(self) -> str:
        """The backup mode"""
        return self._parent_dialog.mode

    @mode.setter
    def mode(self, value: str) -> None:
        self._parent_dialog.mode = value

    @property
    def config(self) -> Config:
        """The config instance"""
        return self._parent_dialog.config

    @property
    def icon(self):
        """Workaround. Remove until import of icon module is solved."""
        return self._parent_dialog.icon

    def _load_passwords(self):
        """A workaround to fix #2093 until the widgets are refactored and
        redesigned.
        """
        # password
        password_1 = self.config.password(
            mode=self.mode, pw_id=1, only_from_keyring=True)
        password_2 = self.config.password(
            mode=self.mode, pw_id=2, only_from_keyring=True)

        if password_1 is None:
            password_1 = ''

        if password_2 is None:
            password_2 = ''

        self._txt_password1.setText(password_1)
        self._txt_password2.setText(password_2)

        self._cb_password_save.setChecked(
            self._keyring_supported
            and self.config.passwordSave(mode=self.mode)
        )

        self._cb_password_use_cache.setChecked(
            self.config.passwordUseCache(mode=self.mode))

    def load_values(self) -> Any:
        """Set the values of the widgets regarding the current config."""
        backup_mode = self.config.snapshotsMode()
        self._combo_modes.select_by_data(backup_mode)

        # local
        self._edit_backup_path.setText(
            self.config.snapshotsPath(mode='local'))

        # SSH
        self._txt_ssh_host.setText(self.config.sshHost())
        self._txt_ssh_port.setText(str(self.config.sshPort()))
        self._txt_ssh_user.setText(self.config.sshUser())
        self._txt_ssh_path.setText(self.config.sshSnapshotsPath())

        # SSH: Priate key file
        val = self.config.sshPrivateKeyFile()

        if val is False:
            # using key is disabled
            val = None

        elif val is None:
            # Select key by default if present
            try:
                val = sshtools.get_private_ssh_key_files()[0]
            except IndexError:
                # no key available
                pass

        self.key_selector.set_key(Path(val) if val else val)

        # local_gocryptfs
        if self.mode == 'local_gocryptfs':
            self._edit_backup_path.setText(
                self.config.localGocryptfsPath(self.config.currentProfile())
            )

        self._load_passwords()

        host, user, profile = self.config.hostUserProfile()
        self._txt_host.setText(host)
        self._txt_user.setText(user)
        self.txt_profile.setText(profile)

        # Schedule
        self._wdg_schedule.load_values(self.config)

    def _store_local_gocryptfs_destination_path(self) -> bool:
        """Path and password related to local gocryptfs profile.
        """

        # save local_gocryptfs
        if self.get_active_snapshots_mode() != 'local_gocryptfs':
            return True

        # backup path
        path = self._edit_backup_path.text()

        if path is None:
            messagebox.warning(
                _('The backup destination path cannot be empty.'),
                _('Where to save backups'),
                self
            )
            return False

        # if not self._is_gocryptfs_path_empty(Path(path)):
        #     return False

        self.config.setLocalGocryptfsPath(path, self.config.currentProfile())

        # password
        password_1 = self._txt_password1.text()

        if not password_1:
            messagebox.warning(
                _('The encryption password cannot be empty.'),
                _('Encryption'),
                self
            )
            return False

        return True

    # pylint: disable-next=too-many-return-statements, too-many-statements
    def store_values(self) -> bool:  # noqa: PLR0915, PLR0911
        """Store the tab's values into the config instance.

        Returns:
            bool: Success or not.
        """
        mode = self.get_active_snapshots_mode()
        self.config.setSnapshotsMode(mode)

        # WTF!!!
        # passwords
        password_1 = self._txt_password1.text()
        password_2 = self._txt_password2.text()

        # mount_kwargs = {}

        # if mode in ('ssh', 'local_encfs'):
        #     mount_kwargs = {'password': password_1}

        # elif mode == 'ssh_encfs':
        #     mount_kwargs = {'ssh_password': password_1,
        #                     'encfs_password': password_2}

        self.config.setHostUserProfile(
            self._txt_host.text(),
            self._txt_user.text(),
            self.txt_profile.text()
        )

        # SSH
        self.config.setSshHost(self._txt_ssh_host.text())
        self.config.setSshPort(self._txt_ssh_port.text())
        self.config.setSshUser(self._txt_ssh_user.text())
        sshproxy_vals = self._wdg_ssh_proxy.values()
        self.config.setSshProxyHost(sshproxy_vals['host'])
        self.config.setSshProxyPort(sshproxy_vals['port'])
        self.config.setSshProxyUser(sshproxy_vals['user'])
        self.config.setSshSnapshotsPath(self._txt_ssh_path.text())

        # SSH key file
        if 'ssh' in mode:
            key_file = self.key_selector.get_key()
            self.config.setSshPrivateKeyFile(str(key_file) if key_file else '')

        # # save local_encfs
        # self.config.setLocalEncfsPath(self._edit_backup_path.text())

        # _gocryptfs: path & password
        if self._store_local_gocryptfs_destination_path() is False:
            return False

        # schedule
        success = self._wdg_schedule.store_values(self.config)

        if success is False:
            return False

        # save password
        self.config.setPasswordSave(self._cb_password_save.isChecked(),
                                    mode=mode)
        self.config.setPasswordUseCache(
            self._cb_password_use_cache.isChecked(),
            mode=mode)
        self.config.setPassword(password_1, mode=mode)
        self.config.setPassword(password_2, mode=mode, pw_id=2)

        if 'ssh' in mode:
            mnt = MountManager.create(self.config)
            ssh_check = SSHSetupValidator(mnt)
            try:
                ssh_check.run()
            except SSHSetupError as exc:
                logger.error(exc)
                msg = _(
                    'Back In Time could not validate the SSH configuration.'
                ) + '\n\n' + _('Reason:') + '\n' + exc.gui_msg
                messagebox.critical(self, msg, _('SSH profile setup failed'))

                return False

        # Dev note (2026-05, buhtz): Gocryptfs needs an empty dir to get
        # initialized. Here this is check. Important is that this check
        # happens after the SSH checks.
        # For local encrypted profiles a similar check is used. Not here,
        # but in _slot_snapshots_path_clicked().
        # This is a pragmatic workaround/solution and might be restructured
        # later.
        if mode == 'ssh_gocryptfs':
            mnt = MountManager.create(self.config)

            try:
                # Mount SSH only, without gocryptfs
                mnt.backend.mount()

                if not self._is_empty_or_initialized_gocryptfs(
                        mnt.backend.path):

                    mnt.backend.umount()
                    return False

                mnt.backend.umount()

            except MountError as exc:
                messagebox.critical(self, exc.gui_msg)
                return False

        if mode == 'local':
            self.config.set_snapshots_path(self._edit_backup_path.text())

        # Attention! The mount manager instance need to be fresh at this point
        # because the config was changed.
        # Current problem with the Manage profile dialog is that there is to
        # much mounting stuff involved.
        try:
            mnt = MountManager.create(self.config)
            mnt.mount()

        except MountError as exc:
            logger.error(self, str(exc))
            messagebox.critical(
                self, exc.gui_msg, _('Profile setup failed')
            )
            return False

        success = tools.validate_and_prepare_snapshots_path(
            path=mnt.path,
            host_user_profile=self.config.hostUserProfile(),
            mode=mode,
            copy_links=self.config.copyLinks(),
            error_event=core_events.event_error
        )

        if success is False:
            return False

        # umount
        try:
            mnt.umount()
        except MountError as exc:
            logger.error(self, str(exc))
            messagebox.critical(self, exc.gui_msg)
            return False

        return True

    # def _do_alot_pre_mount_checking(self, mnt, mount_kwargs):
    #     """Initiate several checks related to mounting and similar tasks.

    #     Depending on the backup mode used different checks are initiated.

    #     Dev note (buhtz, 2024-09): The code is parked and ready to
    #     refactoring.

    #     Returns:
    #         bool: ``True`` if successful otherwise ``False``.
    #     """
    #     # pylint: disable=too-many-return-statements

    #     try:
    #         if not mnt.is_initialized():
    #             mnt.initialize()
    #         mnt.validate()
    #         mnt.mount()

    #     except MountError as exc:
    #         messagebox.critical(self, exc.gui_msg)
    #         return False

    #     return True

        # except NoPubKeyLogin as ex:
        #     logger.error(str(ex), self)

        #     if not self.config.sshPrivateKeyFile_enabled():
        #         # Configured without explicit SSH key file
        #         messagebox.critical(self, str(ex))
        #         return False

        #     question = (
        #         '<p>' + _('An error occurred while attempting to log in to '
        #                   'the remote host. The following error message was '
        #                   'returned:')
        #         + '</p><p>' + str(ex) + '</p><p>'
        #         + _('To enable password-less login, the public SSH key can '
        #             'be copied to the remote host.')
        #         + '</p><p>'
        #         + _('Proceed with copying the SSH key?')
        #         + '</p>'
        #     )

        #     answer = messagebox.warning(text=question, as_question=True)

        #     if not answer:
        #         return False

        #     rc_copy_id = sshtools.sshCopyId(
        #         self.config.sshPrivateKeyFile() + '.pub',
        #         self.config.sshUser(),
        #         self.config.sshHost(),
        #         port=str(self.config.sshPort()),
        #         proxy_user=self.config.sshProxyUser(),
        #         proxy_host=self.config.sshProxyHost(),
        #         proxy_port=self.config.sshProxyPort(),
        #         # This will open an extra input dialog to ask for the
        #         # SSH password.
        #         askPass=tools.which('backintime-askpass'),
        #         cipher=self.config.sshCipher()
        #     )

        #     if not rc_copy_id:
        #         messagebox.warning(_(
        #             'The public SSH key could not be copied. This may '
        #             'be due to a connection or permission issue.'
        #         ))
        #         return False

        #     # --- DEV NOTE TODO ---
        #     # Why this recursive call?
        #     return self._parent_dialog.save_profile()

        # except KnownHost as ex:
        #     logger.error(str(ex), self)
        #     fingerprint, hashed_key, key_type = sshtools.sshHostKey(
        #         host=self.config.sshHost(),
        #         port=str(self.config.sshPort()))

        #     if not fingerprint:
        #         messagebox.critical(self, str(ex))
        #         return False

        #     msg = (
        #         '<p>'
        #         + _("The authenticity of host {host} can't be "
        #             "established.").format(host=self.config.sshHost())
        #         + '</p><p>'
        #         + _('{keytype} key fingerprint is:').format(keytype=key_type)
        #         + '</p><p><code>'
        #         + fingerprint
        #         + '</code></p><p>'
        #         + _('Please verify this fingerprint. Add it to the '
        #             '"known_hosts" file?')
        #         + '</p>'
        #     )

        #     if messagebox.question(msg):
        #         sshtools.writeKnownHostsFile(hashed_key)

        #         # --- DEV NOTE TODO ---
        #         # AGAIN: Why this recursive call?
        #         return self.saveProfile()

        #     return False

    def _snapshot_mode_combobox(self) -> combobox.BitComboBox:
        tooltips = {
            'local': _('Backups are stored locally.'),
            'local_gocryptfs': _(
                'Backups are stored locally and encrypted using gocryptfs.'
            ),
            'ssh': _('Backups are stored on a remote system via SSH.'),
            'ssh_gocryptfs': _(
                'Backups are stored on a remote system via SSH and '
                'encrypted using gocryptfs.'
            )
        }
        snapshot_modes = {}
        for key in self.config.SNAPSHOT_MODES:
            snapshot_modes[key] = (
                # label
                self.config.SNAPSHOT_MODES[key][1],
                # tooltip
                tooltips[key]
            )

        return combobox.BitComboBox(self, snapshot_modes)

    def _slot_snapshots_path_clicked(self):
        """The dir button beside backup destination path was clicked.
        Note: This button exists only on local profiles.
        """
        old_path = Path(self._edit_backup_path.text())

        dlg = FileDialog(
            parent=self,
            title=_('Where to save backups'),
            show_hidden=True,
            allow_multiselection=False,
            dirs_only=True,
            start_dir=Path.home() if old_path == Path('.') else old_path)
        path = dlg.result()

        # nothing selected (Cancel)
        if not path:
            return

        # nothing changed
        if old_path and old_path == path:
            return

        # gocryptfs destination need to be empty
        if 'gocryptfs' in self.mode:
            # is not empty
            if not self._is_empty_or_initialized_gocryptfs(path):
                return

        # Really change?
        if old_path != Path('.'):
            answer = messagebox.question(
                text=_('Really change the backup directory?'),
                widget_to_center_on=self)

            if not answer:
                return

        # Set the path
        self._edit_backup_path.setText(str(path))

    def _is_empty_or_initialized_gocryptfs(self, path: Path) -> bool:
        # Existing initialized repository
        if (path / 'gocryptfs.conf').is_file():
            return True

        # Empty directory
        if not any(path.iterdir()):
            return True

        messagebox.warning(
            '<p>'
            + _('The selected backup destination cannot be used for '
                'encryption.')
            + '<p></p>'
            + _('It must either be empty or already initialized for '
                'gocryptfs.')
            + '</p>',
            widget_to_center_on=self
        )

        return False

    def _slot_ssh_private_key_file_clicked(self):
        key_file = self.key_selector.get_key()

        if key_file:
            start_dir = key_file.parent
        else:
            start_dir = DIR_SSH_KEYS

        file_dialog = FileDialog(
            parent=self,
            title=_('SSH private key'),
            start_dir=start_dir,
            allow_multiselection=False
        )

        key_file = file_dialog.result()

        if not key_file:
            return

        # No public key
        if key_file.suffix.lower() == '.pub':
            title = _('Invalid file: Not a private SSH key')
            msg = _('The selected file ({path}) is a public SSH key. '
                    'Please choose the corresponding private key file instead '
                    '(without ".pub").').format(path=key_file)
            messagebox.warning(msg, title, self)

            return

        # self.txtSshPrivateKeyFile.setText(str(key_file))
        self.key_selector.add_and_select_key(key_file)

    def _slot_ssh_key_gen_clicked(self):

        default_keyfile_name = sshtools.determine_default_ssh_key_filename()

        if not default_keyfile_name:
            msg = 'Unable to determine the default filename for new ' \
                'generated ssh keys used by "ssh-keygen".'
            logger.critical(msg)
            messagebox.critical(self, msg)
            return

        key_file_path = DIR_SSH_KEYS / default_keyfile_name

        if key_file_path.exists():
            msg = _('The file {path} already exists. Cannot create a new '
                    'SSH key with that name.').format(path=key_file_path)
            messagebox.critical(self, msg)
            return

        # Generate the key
        if sshtools.sshKeyGen(str(key_file_path)):
            self.key_selector.add_and_select_key(key_file_path)
            return

        msg = _('Failed to create new SSH key in {path}.') \
            .format(path=key_file_path)
        messagebox.critical(self, msg)

    def _slot_full_path_changed(self, _text: Any):
        if self.mode and 'ssh' in self.mode:
            path = self._txt_ssh_path.text()

        else:
            path = self._edit_backup_path.text()

        self._lbl_full_path.setText(
            _('Full backup path:') + ' ' +
            os.path.join(
                path,
                'backintime',
                self._txt_host.text(),
                self._txt_user.text(),
                self.txt_profile.text()
            ))

    def get_active_snapshots_mode(self) -> str:
        """Current profile mode"""
        return self._combo_modes.current_data

    def handle_combo_modes_changed(self):
        """Hide/show widget elements related to one of
        the four snapshot modes.

        This is not a slot connected to a signal. But it is called by the
        parent dialog.
        """
        # Mode selected in the combo box
        active_mode = self.get_active_snapshots_mode()

        # state_data = StateData()
        # profile_state = state_data.profile(self.config.currentProfile())

        # New selected mode different from previous one?
        if active_mode != self.mode:

            self.mode = active_mode

            self._group_mode_local.setVisible('local' in active_mode)
            self._group_mode_ssh.setVisible('ssh' in active_mode)
            self._wdg_schedule.allow_udev('local' in active_mode)

            # gocryptfs destination need to be empty
            if 'gocryptfs' in self.mode:
                path = self._edit_backup_path.text()
                # dir exists and is not empty
                try:
                    if path and any(Path(path).iterdir()):
                        self._edit_backup_path.setText('')
                except FileNotFoundError as exc:
                    logger.error(exc)
                    self._edit_backup_path.setText('')

        # A mode using password fields?
        if self.config.modeNeedPassword(active_mode):

            self._lbl_password1.setText(
                self.config.SNAPSHOT_MODES[active_mode][2] + ':')

            self._group_password1.show()

            if self.config.modeNeedPassword(active_mode, 2):
                self._lbl_password2.setText(
                    self.config.SNAPSHOT_MODES[active_mode][3] + ':')
                self._lbl_password2.show()
                self._txt_password2.show()

            else:
                self._lbl_password2.hide()
                self._txt_password2.hide()

            self._load_passwords()

        else:
            self._group_password1.hide()
