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
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
import os
from pathlib import Path
from typing import Any
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QMessageBox,
                             QGroupBox,
                             QComboBox,
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

        self.lblModes = QLabel(_('Mode:'), self)

        self.comboModes = QComboBox(self)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.lblModes)
        hlayout.addWidget(self.comboModes, 1)
        vlayout.addLayout(hlayout)
        store_modes = {}
        for key in list(self.config.SNAPSHOT_MODES.keys()):
            store_modes[key] = self.config.SNAPSHOT_MODES[key][1]
        self.fillCombo(self.comboModes, store_modes)

        # EncFS deprecation (#1734, #1735)
        self.encfsWarning = self._create_label_encfs_deprecation()
        tab_layout.addWidget(self.encfsWarning)

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
        self.comboSshCipher = QComboBox(self)
        hlayout3.addWidget(self.comboSshCipher)
        self.fillCombo(self.comboSshCipher, self.config.SSH_CIPHERS)

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

        qttools.equalIndent(self.lblSshHost,
                            self.lblSshPath,
                            self.lblSshCipher)

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
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)

        self.lblPassword1 = QLabel(_('Password'), self)
        hlayout1.addWidget(self.lblPassword1)
        self.txtPassword1 = QLineEdit(self)
        self.txtPassword1.setEchoMode(QLineEdit.EchoMode.Password)
        hlayout1.addWidget(self.txtPassword1)

        self.lblPassword2 = QLabel(_('Password'), self)
        hlayout2.addWidget(self.lblPassword2)
        self.txtPassword2 = QLineEdit(self)
        self.txtPassword2.setEchoMode(QLineEdit.EchoMode.Password)
        hlayout2.addWidget(self.txtPassword2)

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
        self.comboModes.currentIndexChanged.connect(
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

    def _slot_full_path_changed(self, _: Any):
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
                self.txt_profile.text()))

    def get_active_snapshots_mode(self, *params):
        logger.debug(f'{params=}', self)
        if not params:
            index = self.comboModes.currentIndex()
        else:
            index = params[0]

        return str(self.comboModes.itemData(index))

    def handle_combo_modes_changed(self, *params):
        """Hide/show widget elements related to one of
        the four snapshot modes.

        This is not a slot connected to a signal. But it is called by the
        parent dialog.
        """
        active_mode = self.get_active_snapshots_mode(params)

        if active_mode != self.mode:
            # DevNote (buhtz): Widgets of the GUI related to the four
            # snapshot modes are acccesed via "getattr(self, ...)".
            # These are 'Local', 'Ssh', 'LocalEncfs', 'SshEncfs'
            for mode in list(self.config.SNAPSHOT_MODES.keys()):
                logger.debug(f'HIDE() :: mode%s' % tools.camelCase(mode))
                # Hide all widgets
                getattr(self, 'mode%s' % tools.camelCase(mode)).hide()

            for mode in list(self.config.SNAPSHOT_MODES.keys()):
                # Show up the widget related to the selected mode.
                if active_mode == mode:
                    logger.debug(f'SHOW() :: mode%s' % tools.camelCase(mode))
                    getattr(self, 'mode%s' % tools.camelCase(mode)).show()

            self.mode = active_mode

        if self.config.modeNeedPassword(active_mode):

            self.lblPassword1.setText(
                self.config.SNAPSHOT_MODES[active_mode][2] + ':')

            self.groupPassword1.show()

            if self.config.modeNeedPassword(active_mode, 2):
                self.lblPassword2.setText(
                    self.config.SNAPSHOT_MODES[active_mode][3] + ':')
                self.lblPassword2.show()
                self.txtPassword2.show()
                qttools.equalIndent(self.lblPassword1, self.lblPassword2)

            else:
                self.lblPassword2.hide()
                self.txtPassword2.hide()
                qttools.equalIndent(self.lblPassword1)

        else:
            self.groupPassword1.hide()

        if active_mode == 'ssh_encfs':
            self.lblSshEncfsExcludeWarning.show()
        else:
            self.lblSshEncfsExcludeWarning.hide()

        self.updateExcludeItems()

        enabled = active_mode in ('ssh', 'ssh_encfs')

        # self.cbNiceOnRemote.setEnabled(enabled)
        # self.cbIoniceOnRemote.setEnabled(enabled)
        # self.cbNocacheOnRemote.setEnabled(enabled)
        # self.cbSmartRemoveRunRemoteInBackground.setHidden(not enabled)
        # self.cbSshPrefix.setHidden(not enabled)
        # self.txtSshPrefix.setHidden(not enabled)
        # self.cbSshCheckPing.setHidden(not enabled)
        # self.cbSshCheckCommands.setHidden(not enabled)

        # EncFS deprecation warnings (see #1734)
        if active_mode in ('local_encfs', 'ssh_encfs'):
            self.encfsWarning.setHidden(False)

            # Workaround to avoid showing the warning messagebox just when
            # opening the manage profiles dialog.
            if self.isVisible():
                # Show the profile specific warning dialog only once per
                # profile.
                if self.config.profileBoolValue('msg_shown_encfs') is False:
                    self.config.setProfileBoolValue('msg_shown_encfs', True)
                    dlg = encfsmsgbox.EncfsCreateWarning(self)
                    dlg.exec()
        else:
            self.encfsWarning.setHidden(True)
