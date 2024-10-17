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
from pathlib import Path
from typing import Any
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QGridLayout,
                             QMessageBox,
                             QGroupBox,
                             QLabel,
                             QToolButton,
                             QLineEdit,
                             QCheckBox,
                             QToolTip)
import config
import tools
import qttools
import messagebox
import sshtools
import logger
import encfsmsgbox
import mount
from exceptions import MountException, NoPubKeyLogin, KnownHost
from manageprofiles import combobox
from manageprofiles import schedulewidget
from manageprofiles.sshproxywidget import SshProxyWidget
from bitbase import URL_ENCRYPT_TRANSITION


class GeneralTab(QDialog):
    """Create the 'Generals' tab."""

    def __init__(self, parent):
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

        # EncFS deprecation (#1734, #1735)
        self._lbl_encfs_warning = self._create_label_encfs_deprecation()
        tab_layout.addWidget(self._lbl_encfs_warning)

        # Where to save snapshots
        groupBox = QGroupBox(self)
        self.modeLocal = groupBox
        groupBox.setTitle(_('Where to save snapshots'))
        tab_layout.addWidget(groupBox)

        vlayout = QVBoxLayout(groupBox)

        hlayout = QHBoxLayout()
        vlayout.addLayout(hlayout)

        self.editSnapshotsPath = QLineEdit(self)
        self.editSnapshotsPath.setReadOnly(True)
        self.editSnapshotsPath.textChanged.connect(
            self._slot_full_path_changed)
        hlayout.addWidget(self.editSnapshotsPath)

        self.btnSnapshotsPath = QToolButton(self)
        self.btnSnapshotsPath.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btnSnapshotsPath.setIcon(self.icon.FOLDER)
        self.btnSnapshotsPath.setText(_('Folder'))
        self.btnSnapshotsPath.setMinimumSize(32, 28)
        hlayout.addWidget(self.btnSnapshotsPath)
        self.btnSnapshotsPath.clicked.connect(
            self._slot_snapshots_path_clicked)

        # --- SSH ---
        groupBox = QGroupBox(self)
        self.modeSsh = groupBox
        groupBox.setTitle(_('SSH Settings'))
        tab_layout.addWidget(groupBox)

        vlayout = QVBoxLayout(groupBox)

        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)
        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)

        self.lblSshHost = QLabel(_('Host:'), self)
        hlayout1.addWidget(self.lblSshHost)
        self.txtSshHost = QLineEdit(self)
        hlayout1.addWidget(self.txtSshHost)

        self.lblSshPort = QLabel(_('Port:'), self)
        hlayout1.addWidget(self.lblSshPort)
        self.txtSshPort = QLineEdit(self)
        hlayout1.addWidget(self.txtSshPort)

        self.lblSshUser = QLabel(_('User:'), self)
        hlayout1.addWidget(self.lblSshUser)
        self.txtSshUser = QLineEdit(self)
        hlayout1.addWidget(self.txtSshUser)

        self.lblSshPath = QLabel(_('Path:'), self)
        hlayout2.addWidget(self.lblSshPath)
        self.txtSshPath = QLineEdit(self)
        self.txtSshPath.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self.txtSshPath)

        self.lblSshCipher = QLabel(_('Cipher:'), self)
        hlayout3.addWidget(self.lblSshCipher)
        self.comboSshCipher = self._cipher_combobox()
        hlayout3.addWidget(self.comboSshCipher)

        self.lblSshPrivateKeyFile = QLabel(_('Private Key:'), self)
        hlayout3.addWidget(self.lblSshPrivateKeyFile)
        self.txtSshPrivateKeyFile = QLineEdit(self)
        self.txtSshPrivateKeyFile.setReadOnly(True)
        hlayout3.addWidget(self.txtSshPrivateKeyFile)

        self.btnSshPrivateKeyFile = QToolButton(self)
        self.btnSshPrivateKeyFile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btnSshPrivateKeyFile.setIcon(self.icon.FOLDER)
        self.btnSshPrivateKeyFile.setToolTip(
            _('Choose an existing private key file (normally named "id_rsa")'))
        self.btnSshPrivateKeyFile.setMinimumSize(32, 28)
        hlayout3.addWidget(self.btnSshPrivateKeyFile)
        self.btnSshPrivateKeyFile.clicked \
            .connect(self._slot_ssh_private_key_file_clicked)

        self.btnSshKeyGen = QToolButton(self)
        self.btnSshKeyGen.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btnSshKeyGen.setIcon(self.icon.ADD)
        qttools.set_wrapped_tooltip(
            self.btnSshKeyGen,
            _('Create a new SSH key without password (not allowed if a '
              'private key file is already selected).')
        )
        self.btnSshKeyGen.setMinimumSize(32, 28)
        hlayout3.addWidget(self.btnSshKeyGen)
        self.btnSshKeyGen.clicked.connect(self._slot_ssh_key_gen_clicked)

        # Disable SSH key generation button if a key file is already set
        self.txtSshPrivateKeyFile.textChanged \
            .connect(lambda x: self.btnSshKeyGen.setEnabled(not x))

        # Align the width of that three labels
        width = max(
            self.lblSshHost.sizeHint().width(),
            self.lblSshPath.sizeHint().width(),
            self.lblSshCipher.sizeHint().width()
        )
        self.lblSshHost.setMinimumWidth(width)
        self.lblSshPath.setMinimumWidth(width)
        self.lblSshCipher.setMinimumWidth(width)

        self.wdgSshProxy = SshProxyWidget(
            self,
            self.config.sshProxyHost(),
            self.config.sshProxyPort(),
            self.config.sshProxyUser()
        )
        vlayout.addWidget(self.wdgSshProxy)

        # encfs
        self.modeLocalEncfs = self.modeLocal
        self.modeSshEncfs = self.modeSsh

        # password
        groupBox = QGroupBox(self)
        self.groupPassword1 = groupBox
        groupBox.setTitle(_('Password'))
        tab_layout.addWidget(groupBox)

        vlayout = QVBoxLayout(groupBox)

        grid = QGridLayout()

        self.lblPassword1 = QLabel(_('Password'), self)
        self.txtPassword1 = QLineEdit(self)
        self.txtPassword1.setEchoMode(QLineEdit.EchoMode.Password)

        self.lblPassword2 = QLabel(_('Password'), self)
        self.txtPassword2 = QLineEdit(self)
        self.txtPassword2.setEchoMode(QLineEdit.EchoMode.Password)

        grid.addWidget(self.lblPassword1, 0, 0)
        grid.addWidget(self.txtPassword1, 0, 1)
        grid.addWidget(self.lblPassword2, 1, 0)
        grid.addWidget(self.txtPassword2, 1, 1)
        vlayout.addLayout(grid)

        self.cbPasswordSave = QCheckBox(_('Save Password to Keyring'), self)
        vlayout.addWidget(self.cbPasswordSave)

        self.cbPasswordUseCache = QCheckBox(
            _('Cache Password for Cron (Security '
              'issue: root can read password)'),
            self
        )
        vlayout.addWidget(self.cbPasswordUseCache)

        self.keyringSupported = tools.keyringSupported()
        self.cbPasswordSave.setEnabled(self.keyringSupported)

        # mode change
        self._combo_modes.currentIndexChanged.connect(
            self._parent_dialog.slot_combo_modes_changed)

        # host, user, profile id
        groupBox = QGroupBox(self)
        self.frameAdvanced = groupBox
        groupBox.setTitle(_('Advanced'))
        tab_layout.addWidget(groupBox)

        hlayout = QHBoxLayout(groupBox)
        hlayout.addSpacing(12)

        vlayout2 = QVBoxLayout()
        hlayout.addLayout(vlayout2)

        hlayout2 = QHBoxLayout()
        vlayout2.addLayout(hlayout2)

        self.lblHost = QLabel(_('Host:'), self)
        hlayout2.addWidget(self.lblHost)
        self.txtHost = QLineEdit(self)
        self.txtHost.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self.txtHost)

        self.lblUser = QLabel(_('User:'), self)
        hlayout2.addWidget(self.lblUser)
        self.txtUser = QLineEdit(self)
        self.txtUser.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self.txtUser)

        self.lblProfile = QLabel(_('Profile:'), self)
        hlayout2.addWidget(self.lblProfile)
        self.txt_profile = QLineEdit(self)
        self.txt_profile.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self.txt_profile)

        self.lblFullPath = QLabel(_('Full snapshot path:'), self)
        self.lblFullPath.setWordWrap(True)
        vlayout2.addWidget(self.lblFullPath)

        self._wdg_schedule = schedulewidget.ScheduleWidget(self)
        tab_layout.addWidget(self._wdg_schedule)

        #
        tab_layout.addStretch()

    @property
    def mode(self) -> str:
        return self._parent_dialog.mode

    @mode.setter
    def mode(self, value: str) -> None:
        self._parent_dialog.mode = value

    @property
    def config(self) -> config.Config:
        return self._parent_dialog.config

    @property
    def icon(self):
        """Workaround. Remove until import of icon module is solved."""
        return self._parent_dialog.icon

    def load_values(self) -> Any:
        """Set the values of the widgets regarding the current config."""

        self._combo_modes.select_by_data(self.config.snapshotsMode())

        # local
        self.editSnapshotsPath.setText(
            self.config.snapshotsPath(mode='local'))

        # SSH
        self.txtSshHost.setText(self.config.sshHost())
        self.txtSshPort.setText(str(self.config.sshPort()))
        self.txtSshUser.setText(self.config.sshUser())
        self.txtSshPath.setText(self.config.sshSnapshotsPath())
        self.comboSshCipher.select_by_data(self.config.sshCipher())
        self.txtSshPrivateKeyFile.setText(self.config.sshPrivateKeyFile())

        # local_encfs
        if self.mode == 'local_encfs':
            self.editSnapshotsPath.setText(self.config.localEncfsPath())

        # password
        password_1 = self.config.password(
            mode=self.mode, pw_id=1, only_from_keyring=True)
        password_2 = self.config.password(
            mode=self.mode, pw_id=2, only_from_keyring=True)

        if password_1 is None:
            password_1 = ''

        if password_2 is None:
            password_2 = ''

        self.txtPassword1.setText(password_1)
        self.txtPassword2.setText(password_2)

        self.cbPasswordSave.setChecked(
            self.keyringSupported and self.config.passwordSave(mode=self.mode))

        self.cbPasswordUseCache.setChecked(
            self.config.passwordUseCache(mode=self.mode))

        host, user, profile = self.config.hostUserProfile()
        self.txtHost.setText(host)
        self.txtUser.setText(user)
        self.txt_profile.setText(profile)

        # Schedule
        self._wdg_schedule.load_values(self.config)

    def store_values(self) -> bool:
        """Store the tab's values into the config instance.

        Returns:
            bool: Success or not.
        """
        mode = self.get_active_snapshots_mode()
        self.config.setSnapshotsMode(mode)

        mount_kwargs = {}

        # password
        password_1 = self.txtPassword1.text()
        password_2 = self.txtPassword2.text()

        if mode in ('ssh', 'local_encfs'):
            mount_kwargs = {'password': password_1}

        if mode == 'ssh_encfs':
            mount_kwargs = {'ssh_password': password_1,
                            'encfs_password': password_2}

        # snapshots path
        self.config.setHostUserProfile(
            self.txtHost.text(),
            self.txtUser.text(),
            self.txt_profile.text()
        )

        # SSH
        self.config.setSshHost(self.txtSshHost.text())
        self.config.setSshPort(self.txtSshPort.text())
        self.config.setSshUser(self.txtSshUser.text())
        sshproxy_vals = self.wdgSshProxy.values()
        self.config.setSshProxyHost(sshproxy_vals['host'])
        self.config.setSshProxyPort(sshproxy_vals['port'])
        self.config.setSshProxyUser(sshproxy_vals['user'])
        self.config.setSshSnapshotsPath(self.txtSshPath.text())
        self.config.setSshCipher(self.comboSshCipher.current_data)

        # SSH key file
        if mode in ('ssh', 'ssh_encfs'):

            if not self.txtSshPrivateKeyFile.text():

                question = '{}\n{}'.format(
                        _('You did not choose a private key file for SSH.'),
                        _('Would you like to generate a new password-less '
                          'public/private key pair?'))
                answer = messagebox.warningYesNo(self, question)
                answer = answer == QMessageBox.StandardButton.Yes
                if answer:
                    self.btnSshKeyGenClicked()

                if not self.txtSshPrivateKeyFile.text():
                    return False

            if not os.path.isfile(self.txtSshPrivateKeyFile.text()):
                msg = _('Private key file "{file}" does not exist.') \
                    .format(file=self.txtSshPrivateKeyFile.text())
                messagebox.critical(self, msg)
                self.txtSshPrivateKeyFile.setText('')

                return False

        self.config.setSshPrivateKeyFile(self.txtSshPrivateKeyFile.text())

        # save local_encfs
        self.config.setLocalEncfsPath(self.editSnapshotsPath.text())

        # schedule
        success = self._wdg_schedule.store_values(self.config)

        if success is False:
            return False

        if mode != 'local':
            mnt = mount.Mount(cfg=self.config, tmp_mount=True, parent=self)
            hash_id = self._do_alot_pre_mount_checking(mnt, mount_kwargs)

            if hash_id is False:
                return False

        # save password
        self.config.setPasswordSave(self.cbPasswordSave.isChecked(),
                                    mode=mode)
        self.config.setPasswordUseCache(self.cbPasswordUseCache.isChecked(),
                                        mode=mode)
        self.config.setPassword(password_1, mode=mode)
        self.config.setPassword(password_2, mode=mode, pw_id=2)

        # snaphots_path
        if mode == 'local':
            self.config.set_snapshots_path(self.editSnapshotsPath.text())

        snapshots_mountpoint = self.config.get_snapshots_mountpoint(
            tmp_mount=True)

        success = tools.validate_and_prepare_snapshots_path(
            path=snapshots_mountpoint,
            host_user_profile=self.config.hostUserProfile(),
            mode=mode,
            copy_links=self.config.copyLinks(),
            error_handler=self.config.notifyError)

        if success is False:
            return False

        # umount
        if mode != 'local':
            try:
                mnt.umount(hash_id=hash_id)

            except MountException as ex:
                messagebox.critical(self, str(ex))
                return False

        return True

    def _do_alot_pre_mount_checking(self, mnt, mount_kwargs):
        """Initiate several checks related to mounting and similar tasks.

        Depending on the snapshots mode used different checks are initiated.

        Dev note (buhtz, 2024-09): The code is parked and ready to refactoring.

        Returns:
            bool: ``True`` if successful otherwise ``False``.
        """
        # preMountCheck

        try:
            # This will run several checks depending on the snapshots mode
            # used. Exceptions are raised if something goes wrong. On mode
            # "local" nothing is checked.
            mnt.preMountCheck(
                mode=self.config.snapshotsMode(),
                first_run=True,
                **mount_kwargs)

        except NoPubKeyLogin as ex:
            logger.error(str(ex), self)

            question = _('Would you like to copy your public SSH key to '
                         'the remote host to enable password-less login?')
            rc_copy_id = sshtools.sshCopyId(
                self.config.sshPrivateKeyFile() + '.pub',
                self.config.sshUser(),
                self.config.sshHost(),
                port=str(self.config.sshPort()),
                proxy_user=self.config.sshProxyUser(),
                proxy_host=self.config.sshProxyHost(),
                proxy_port=self.config.sshProxyPort(),
                askPass=tools.which('backintime-askpass'),
                cipher=self.config.sshCipher()
            )

            answer = messagebox.warningYesNo(self, question)
            answer = answer == QMessageBox.StandardButton.Yes
            if answer and rc_copy_id:
                # --- DEV NOTE TODO ---
                # Why this recursive call?
                return self._parent_dialog.saveProfile()
            else:
                return False

        except KnownHost as ex:
            logger.error(str(ex), self)
            fingerprint, hashedKey, keyType = sshtools.sshHostKey(
                self.config.sshHost(), str(self.config.sshPort())
            )

            if not fingerprint:
                messagebox.critical(self, str(ex))
                return False

            msg = '{}\n\n{}'.format(
                    _("The authenticity of host {host} can't be "
                        "established.").format(
                            host=self.config.sshHost()),
                    _('{keytype} key fingerprint is:').format(
                        keytype=keyType))
            options = []
            lblFingerprint = QLabel(fingerprint + '\n')
            lblFingerprint.setWordWrap(False)
            lblFingerprint.setFont(QFont('Monospace'))
            options.append({'widget': lblFingerprint, 'retFunc': None})
            lblQuestion = QLabel(
                _("Please verify this fingerprint. Would you like to "
                  "add it to your 'known_hosts' file?")
            )
            options.append({'widget': lblQuestion, 'retFunc': None})

            if messagebox.warningYesNoOptions(self, msg, options)[0]:
                sshtools.writeKnownHostsFile(hashedKey)
                # --- DEV NOTE TODO ---
                # AGAIN: Why this recursive call?
                return self.saveProfile()
            else:
                return False

        except MountException as ex:
            messagebox.critical(self, str(ex))
            return False

        # okay, lets try to mount
        try:
            hash_id = mnt.mount(
                mode=self.config.snapshotsMode(),
                check=False,
                **mount_kwargs)

        except MountException as ex:
            messagebox.critical(self, str(ex))
            return False

        return hash_id

    def _snapshot_mode_combobox(self) -> combobox.BitComboBox:
        snapshot_modes = {}
        for key in self.config.SNAPSHOT_MODES:
            snapshot_modes[key] = self.config.SNAPSHOT_MODES[key][1]
        logger.debug(f'{snapshot_modes=}')

        return combobox.BitComboBox(self, snapshot_modes)

    def _cipher_combobox(self) -> combobox.BitComboBox:
        return combobox.BitComboBox(self, self.config.SSH_CIPHERS)

    def _create_label_encfs_deprecation(self):
        # encfs deprecation warning (see #1734, #1735)
        label = QLabel('<b>{}:</b> {}'.format(
            _('Warning'),
            _('Support for EncFS will be discontinued in the foreseeable '
              'future. A decision on a replacement for continued support of '
              'encrypted backups is still pending, depending on project '
              'resources and contributor availability. More details are '
              'available in this {whitepaper}.').format(
                  whitepaper='<a href="{}">{}</a>'.format(
                      URL_ENCRYPT_TRANSITION,
                      _('whitepaper'))
                  )
        ))
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)

        # Show URL in tooltip without anoing http-protocol prefix.
        label.linkHovered.connect(
            lambda url: QToolTip.showText(
                QCursor.pos(), url.replace('https://', ''))
        )

        return label

    def _slot_snapshots_path_clicked(self):
        old_path = self.editSnapshotsPath.text()

        path = str(qttools.getExistingDirectory(
            self,
            _('Where to save snapshots'),
            self.editSnapshotsPath.text()
        ))

        if path:

            if old_path and old_path != path:
                question = _('Are you sure you want to change '
                             'snapshots folder?')

                answer = messagebox.warningYesNo(self, question)
                answer = answer == QMessageBox.StandardButton.Yes

                if not answer:
                    return

                # Why?
                self.config.removeProfileKey('snapshots.path.uuid')

            self.editSnapshotsPath.setText(self.config.preparePath(path))

    def _slot_ssh_private_key_file_clicked(self):
        old_file = self.txtSshPrivateKeyFile.text()

        if old_file:
            start_dir = self.txtSshPrivateKeyFile.text()
        else:
            start_dir = self.config.sshPrivateKeyFolder()
        f = qttools.getOpenFileName(self, _('SSH private key'), start_dir)
        if f:
            self.txtSshPrivateKeyFile.setText(f)

    def _slot_ssh_key_gen_clicked(self):
        priv_key_folder = self.config.sshPrivateKeyFolder()

        # Workaround
        if isinstance(priv_key_folder, str):
            priv_key_folder = Path(priv_key_folder)

        key_file_path = priv_key_folder / 'id_rsa'

        if sshtools.sshKeyGen(str(key_file_path)):
            self.txtSshPrivateKeyFile.setText(key_file_path)
        else:
            msg = _('Failed to create new SSH key in {path}.') \
                .format(path=key_file_path)
            messagebox.critical(self, msg)

    def _slot_full_path_changed(self, _text: Any):
        if self.mode in ('ssh', 'ssh_encfs'):
            path = self.txtSshPath.text()

        else:
            path = self.editSnapshotsPath.text()

        self.lblFullPath.setText(
            _('Full snapshot path:') + ' ' +
            os.path.join(
                path,
                'backintime',
                self.txtHost.text(),
                self.txtUser.text(),
                self.txt_profile.text()
            ))

    def get_active_snapshots_mode(self) -> str:
        return self._combo_modes.current_data

    def handle_combo_modes_changed(self):
        """Hide/show widget elements related to one of
        the four snapshot modes.

        This is not a slot connected to a signal. But it is called by the
        parent dialog.
        """
        active_mode = self.get_active_snapshots_mode()

        # hide/show group boxes related to current mode
        # note: self.modeLocalEncfs = self.modeLocal
        # note: self.modeSshEncfs = self.modeSsh
        if active_mode != self.mode:
            # logger.debug(f'{active_mode=} {self.mode=}')
            # # DevNote (buhtz): Widgets of the GUI related to the four
            # # snapshot modes are acccesed via "getattr(self, ...)".
            # # These are 'Local', 'Ssh', 'LocalEncfs', 'SshEncfs'
            # for mode in list(self.config.SNAPSHOT_MODES.keys()):
            #     logger.debug(f'HIDE() :: mode%s' % tools.camelCase(mode))
            #     # Hide all widgets
            #     getattr(self, 'mode%s' % tools.camelCase(mode)).hide()

            # for mode in list(self.config.SNAPSHOT_MODES.keys()):
            #     # Show up the widget related to the selected mode.
            #     if active_mode == mode:
            #         logger.debug(f'SHOW() :: mode%s' % tools.camelCase(mode))
            #         getattr(self, 'mode%s' % tools.camelCase(mode)).show()

            self.mode = active_mode

            self.modeLocal.setVisible(active_mode in ('local', 'local_encfs'))
            self.modeSsh.setVisible(active_mode in ('ssh', 'ssh_encfs'))
            # self.modeLocalEncfs = self.modeLocal
            # self.modeSshEncfs = self.modeSsh

        if self.config.modeNeedPassword(active_mode):

            self.lblPassword1.setText(
                self.config.SNAPSHOT_MODES[active_mode][2] + ':')

            self.groupPassword1.show()

            if self.config.modeNeedPassword(active_mode, 2):
                self.lblPassword2.setText(
                    self.config.SNAPSHOT_MODES[active_mode][3] + ':')
                self.lblPassword2.show()
                self.txtPassword2.show()

            else:
                self.lblPassword2.hide()
                self.txtPassword2.hide()

        else:
            self.groupPassword1.hide()

        # EncFS deprecation warnings (see #1734)
        if active_mode in ('local_encfs', 'ssh_encfs'):
            self._lbl_encfs_warning.show()

            # Workaround to avoid showing the warning messagebox just when
            # opening the manage profiles dialog.
            if self._parent_dialog.isVisible():
                # Show the profile specific warning dialog only once per
                # profile.
                if self.config.profileBoolValue('msg_shown_encfs') is False:
                    self.config.setProfileBoolValue('msg_shown_encfs', True)
                    dlg = encfsmsgbox.EncfsCreateWarning(self)
                    dlg.exec()
        else:
            self._lbl_encfs_warning.hide()
