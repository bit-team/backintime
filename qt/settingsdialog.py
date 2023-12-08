#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey,
#                            Germar Reitze, Taylor Raack
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import os
import datetime
import copy
import re

from PyQt6.QtGui import (QIcon,
                         QFont,
                         QPalette,
                         QBrush,
                         QColor,
                         QFileSystemModel)
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QGridLayout,
                             QDialogButtonBox,
                             QMessageBox,
                             QInputDialog,
                             QGroupBox,
                             QScrollArea,
                             QFrame,
                             QWidget,
                             QTabWidget,
                             QComboBox,
                             QLabel,
                             QPushButton,
                             QToolButton,
                             QLineEdit,
                             QSpinBox,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QAbstractItemView,
                             QHeaderView,
                             QCheckBox,
                             QMenu,
                             QProgressBar,
                             QPlainTextEdit)
from PyQt6.QtCore import (Qt,
                          QDir,
                          QSortFilterProxyModel,
                          QThread,
                          pyqtSignal,
                          pyqtRemoveInputHook)

import config
import tools
import qttools
import mount
import messagebox
import snapshots
import sshtools
import logger
from exceptions import MountException, NoPubKeyLogin, KnownHost


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

        layout.addWidget(QLabel(_('Profile') + ':', self))

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
        scrollArea.setFrameStyle(QFrame.NoFrame)
        self.tabs.addTab(scrollArea, _('&General'))

        layoutWidget = QWidget(self)
        layout = QVBoxLayout(layoutWidget)

        # select mode
        self.mode = None
        vlayout = QVBoxLayout()
        layout.addLayout(vlayout)

        self.lblModes = QLabel(_('Mode') + ':', self)

        self.comboModes = QComboBox(self)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.lblModes)
        hlayout.addWidget(self.comboModes, 1)
        vlayout.addLayout(hlayout)
        store_modes = {}
        for key in list(self.config.SNAPSHOT_MODES.keys()):
            store_modes[key] = self.config.SNAPSHOT_MODES[key][1]
        self.fillCombo(self.comboModes, store_modes)

        # encfs security warning
        self.encfsWarning = QLabel('<b>{}:</b> {}'.format(
            _('Warning'),
            _('{app} uses EncFS for encryption. A recent security audit '
              'revealed several possible attack vectors for this. Please '
              'take a look at "A NOTE ON SECURITY" in "man backintime".')
            .format(app=self.config.APP_NAME)
        ))
        self.encfsWarning.setWordWrap(True)
        layout.addWidget(self.encfsWarning)

        # Where to save snapshots
        groupBox = QGroupBox(self)
        self.modeLocal = groupBox
        groupBox.setTitle(_('Where to save snapshots'))
        layout.addWidget(groupBox)

        vlayout = QVBoxLayout(groupBox)

        hlayout = QHBoxLayout()
        vlayout.addLayout(hlayout)

        self.editSnapshotsPath = QLineEdit(self)
        self.editSnapshotsPath.setReadOnly(True)
        self.editSnapshotsPath.textChanged.connect(self.fullPathChanged)
        hlayout.addWidget(self.editSnapshotsPath)

        self.btnSnapshotsPath = QToolButton(self)
        self.btnSnapshotsPath.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btnSnapshotsPath.setIcon(icon.FOLDER)
        self.btnSnapshotsPath.setText(_('Folder'))
        self.btnSnapshotsPath.setMinimumSize(32, 28)
        hlayout.addWidget(self.btnSnapshotsPath)
        self.btnSnapshotsPath.clicked.connect(self.btnSnapshotsPathClicked)

        # SSH
        groupBox = QGroupBox(self)
        self.modeSsh = groupBox
        groupBox.setTitle(_('SSH Settings'))
        layout.addWidget(groupBox)

        vlayout = QVBoxLayout(groupBox)

        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)
        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)

        self.lblSshHost = QLabel(_('Host') + ':', self)
        hlayout1.addWidget(self.lblSshHost)
        self.txtSshHost = QLineEdit(self)
        hlayout1.addWidget(self.txtSshHost)

        self.lblSshPort = QLabel(_('Port') + ':', self)
        hlayout1.addWidget(self.lblSshPort)
        self.txtSshPort = QLineEdit(self)
        hlayout1.addWidget(self.txtSshPort)

        self.lblSshUser = QLabel(_('User') + ':', self)
        hlayout1.addWidget(self.lblSshUser)
        self.txtSshUser = QLineEdit(self)
        hlayout1.addWidget(self.txtSshUser)

        self.lblSshPath = QLabel(_('Path') + ':', self)
        hlayout2.addWidget(self.lblSshPath)
        self.txtSshPath = QLineEdit(self)
        self.txtSshPath.textChanged.connect(self.fullPathChanged)
        hlayout2.addWidget(self.txtSshPath)

        self.lblSshCipher = QLabel(_('Cipher') + ':', self)
        hlayout3.addWidget(self.lblSshCipher)
        self.comboSshCipher = QComboBox(self)
        hlayout3.addWidget(self.comboSshCipher)
        self.fillCombo(self.comboSshCipher, self.config.SSH_CIPHERS)

        self.lblSshPrivateKeyFile = QLabel(_('Private Key') + ':', self)
        hlayout3.addWidget(self.lblSshPrivateKeyFile)
        self.txtSshPrivateKeyFile = QLineEdit(self)
        self.txtSshPrivateKeyFile.setReadOnly(True)
        hlayout3.addWidget(self.txtSshPrivateKeyFile)

        self.btnSshPrivateKeyFile = QToolButton(self)
        self.btnSshPrivateKeyFile.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btnSshPrivateKeyFile.setIcon(icon.FOLDER)
        self.btnSshPrivateKeyFile.setToolTip(
            _('Choose an existing private key file (normally named "id_rsa")'))
        self.btnSshPrivateKeyFile.setMinimumSize(32, 28)
        hlayout3.addWidget(self.btnSshPrivateKeyFile)
        self.btnSshPrivateKeyFile.clicked \
            .connect(self.btnSshPrivateKeyFileClicked)

        self.btnSshKeyGen = QToolButton(self)
        self.btnSshKeyGen.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btnSshKeyGen.setIcon(icon.ADD)
        self.btnSshKeyGen.setToolTip(
            _('Create a new SSH key without password (not allowed if a '
              'private key file is already selected)'))
        self.btnSshKeyGen.setMinimumSize(32, 28)
        hlayout3.addWidget(self.btnSshKeyGen)
        self.btnSshKeyGen.clicked.connect(self.btnSshKeyGenClicked)
        # Disable SSH key generation button if a key file is already set
        self.txtSshPrivateKeyFile.textChanged \
            .connect(lambda x: self.btnSshKeyGen.setEnabled(not x))

        qttools.equalIndent(self.lblSshHost,
                            self.lblSshPath,
                            self.lblSshCipher)

        # encfs
        self.modeLocalEncfs = self.modeLocal
        self.modeSshEncfs = self.modeSsh

        # password
        groupBox = QGroupBox(self)
        self.groupPassword1 = groupBox
        groupBox.setTitle(_('Password'))
        layout.addWidget(groupBox)

        vlayout = QVBoxLayout(groupBox)
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)

        self.lblPassword1 = QLabel(_('Password'), self)
        hlayout1.addWidget(self.lblPassword1)
        self.txtPassword1 = QLineEdit(self)
        self.txtPassword1.setEchoMode(QLineEdit.Password)
        hlayout1.addWidget(self.txtPassword1)

        self.lblPassword2 = QLabel(_('Password'), self)
        hlayout2.addWidget(self.lblPassword2)
        self.txtPassword2 = QLineEdit(self)
        self.txtPassword2.setEchoMode(QLineEdit.Password)
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
        self.comboModes.currentIndexChanged.connect(self.comboModesChanged)

        # host, user, profile id
        groupBox = QGroupBox(self)
        self.frameAdvanced = groupBox
        groupBox.setTitle(_('Advanced'))
        layout.addWidget(groupBox)

        hlayout = QHBoxLayout(groupBox)
        hlayout.addSpacing(12)

        vlayout2 = QVBoxLayout()
        hlayout.addLayout(vlayout2)

        hlayout2 = QHBoxLayout()
        vlayout2.addLayout(hlayout2)

        self.lblHost = QLabel(_('Host') + ':', self)
        hlayout2.addWidget(self.lblHost)
        self.txtHost = QLineEdit(self)
        self.txtHost.textChanged.connect(self.fullPathChanged)
        hlayout2.addWidget(self.txtHost)

        self.lblUser = QLabel(_('User') + ':', self)
        hlayout2.addWidget(self.lblUser)
        self.txtUser = QLineEdit(self)
        self.txtUser.textChanged.connect(self.fullPathChanged)
        hlayout2.addWidget(self.txtUser)

        self.lblProfile = QLabel(_('Profile') + ':', self)
        hlayout2.addWidget(self.lblProfile)
        self.txt_profile = QLineEdit(self)
        self.txt_profile.textChanged.connect(self.fullPathChanged)
        hlayout2.addWidget(self.txt_profile)

        self.lblFullPath = QLabel(_('Full snapshot path') + ': ', self)
        self.lblFullPath.setWordWrap(True)
        vlayout2.addWidget(self.lblFullPath)

        # Schedule
        groupBox = QGroupBox(self)
        self.globalScheduleGroupBox = groupBox
        groupBox.setTitle(_('Schedule'))
        layout.addWidget(groupBox)

        glayout = QGridLayout(groupBox)
        glayout.setColumnStretch(1, 2)

        self.comboSchedule = QComboBox(self)
        glayout.addWidget(self.comboSchedule, 0, 0, 1, 2)

        # import gettext
        # Regular schedule modes for that combo box
        schedule_modes_dict = {
            config.Config.NONE: _('Disabled'),
            config.Config.AT_EVERY_BOOT: _('At every boot/reboot'),
            config.Config._5_MIN: ngettext(
                'Every {n} minute', 'Every {n} minutes', 5).format(n=5),
            config.Config._10_MIN: ngettext(
                'Every {n} minute', 'Every {n} minutes', 10).format(n=10),
            config.Config._30_MIN: ngettext(
                'Every {n} minute', 'Every {n} minutes', 30).format(n=30),
            config.Config._1_HOUR: _('Every hour'),
            config.Config._2_HOURS: ngettext(
                'Every {n} hour', 'Every {n} hours', 2).format(n=2),
            config.Config._4_HOURS: ngettext(
                'Every {n} hour', 'Every {n} hours', 4).format(n=4),
            config.Config._6_HOURS: ngettext(
                'Every {n} hour', 'Every {n} hours', 6).format(n=6),
            config.Config._12_HOURS: ngettext(
                'Every {n} hour', 'Every {n} hours', 12).format(n=12),
            config.Config.CUSTOM_HOUR: _('Custom hours'),
            config.Config.DAY: _('Every day'),
            config.Config.REPEATEDLY: _('Repeatedly (anacron)'),
            config.Config.UDEV: _('When drive gets connected (udev)'),
            config.Config.WEEK: _('Every week'),
            config.Config.MONTH: _('Every month'),
            config.Config.YEAR: _('Every year')
        }

        self.fillCombo(self.comboSchedule, schedule_modes_dict)

        self.lblScheduleDay = QLabel(_('Day') + ':', self)
        self.lblScheduleDay.setContentsMargins(5, 0, 0, 0)
        self.lblScheduleDay.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        glayout.addWidget(self.lblScheduleDay, 1, 0)

        self.comboScheduleDay = QComboBox(self)
        glayout.addWidget(self.comboScheduleDay, 1, 1)

        for d in range(1, 29):
            self.comboScheduleDay.addItem(QIcon(), str(d), d)

        self.lblScheduleWeekday = QLabel(_('Weekday') + ':', self)
        self.lblScheduleWeekday.setContentsMargins(5, 0, 0, 0)
        self.lblScheduleWeekday.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        glayout.addWidget(self.lblScheduleWeekday, 2, 0)

        self.comboScheduleWeekday = QComboBox(self)
        glayout.addWidget(self.comboScheduleWeekday, 2, 1)

        for d in range(1, 8):
            self.comboScheduleWeekday.addItem(
                QIcon(),
                datetime.date(2011, 11, 6 + d).strftime("%A"),
                d
            )

        self.lblScheduleTime = QLabel(_('Hour') + ':', self)
        self.lblScheduleTime.setContentsMargins(5, 0, 0, 0)
        self.lblScheduleTime.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        glayout.addWidget(self.lblScheduleTime, 3, 0)

        self.comboScheduleTime = QComboBox(self)
        glayout.addWidget(self.comboScheduleTime, 3, 1)

        for t in range(0, 2400, 100):
            self.comboScheduleTime.addItem(
                QIcon(),
                datetime.time(t // 100, t % 100).strftime("%H:%M"),
                t
            )

        self.lblScheduleCronPatern = QLabel(_('Hours') + ':', self)
        self.lblScheduleCronPatern.setContentsMargins(5, 0, 0, 0)
        self.lblScheduleCronPatern.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        glayout.addWidget(self.lblScheduleCronPatern, 4, 0)

        self.txtScheduleCronPatern = QLineEdit(self)
        glayout.addWidget(self.txtScheduleCronPatern, 4, 1)

        # anacron
        self.lblScheduleRepeated = QLabel(
            _('Run Back In Time repeatedly. This is useful if the '
              'computer is not running regularly.')
        )
        self.lblScheduleRepeated.setContentsMargins(5, 0, 0, 0)
        self.lblScheduleRepeated.setWordWrap(True)
        glayout.addWidget(self.lblScheduleRepeated, 5, 0, 1, 2)

        self.lblScheduleRepeatedPeriod = QLabel(_('Every') + ':')
        self.lblScheduleRepeatedPeriod.setContentsMargins(5, 0, 0, 0)
        self.lblScheduleRepeatedPeriod.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        glayout.addWidget(self.lblScheduleRepeatedPeriod, 7, 0)

        hlayout = QHBoxLayout()
        self.spbScheduleRepeatedPeriod = QSpinBox(self)
        self.spbScheduleRepeatedPeriod.setSingleStep(1)
        self.spbScheduleRepeatedPeriod.setRange(1, 10000)
        hlayout.addWidget(self.spbScheduleRepeatedPeriod)

        self.comboScheduleRepeatedUnit = QComboBox(self)
        REPEATEDLY_UNITS = {
            config.Config.HOUR: _('Hour(s)'),
            config.Config.DAY: _('Day(s)'),
            config.Config.WEEK: _('Week(s)'),
            config.Config.MONTH: _('Month(s)')}

        self.fillCombo(self.comboScheduleRepeatedUnit,
                       REPEATEDLY_UNITS)
        hlayout.addWidget(self.comboScheduleRepeatedUnit)
        hlayout.addStretch()
        glayout.addLayout(hlayout, 7, 1)

        # udev
        self.lblScheduleUdev = QLabel(
            _('Run Back In Time as soon as the drive is connected (only once'
              ' every X days).\nYou will be prompted for your sudo password.')
        )
        self.lblScheduleUdev.setWordWrap(True)
        glayout.addWidget(self.lblScheduleUdev, 6, 0, 1, 2)

        self.comboSchedule.currentIndexChanged.connect(self.scheduleChanged)

        #
        layout.addStretch()
        scrollArea.setWidget(layoutWidget)
        scrollArea.setWidgetResizable(True)

        # TAB: Include
        tabWidget = QWidget(self)
        self.tabs.addTab(tabWidget, _('&Include'))
        layout = QVBoxLayout(tabWidget)

        self.listInclude = QTreeWidget(self)
        self.listInclude.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.listInclude.setRootIsDecorated(False)
        self.listInclude.setHeaderLabels(
            [_('Include files and folders'), 'Count'])

        self.listInclude.header().setSectionResizeMode(0, QHeaderView.Stretch)
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

        self.lblSshEncfsExcludeWarning = QLabel(
            "<b>{}:</b> {}".format(
                _("Warning"),
                _(
                    "Wildcards ({example1}) will be ignored "
                    "with mode 'SSH encrypted'.\nOnly single or double "
                    "asterisks are allowed ({example2})"
                ).format(example1="'foo*', '[fF]oo', 'fo?'",
                         example2="'foo/*', 'foo/**/bar'")
            ),
            self
        )
        self.lblSshEncfsExcludeWarning.setWordWrap(True)
        layout.addWidget(self.lblSshEncfsExcludeWarning)

        self.listExclude = QTreeWidget(self)
        self.listExclude.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.listExclude.setRootIsDecorated(False)
        self.listExclude.setHeaderLabels(
            [_('Exclude patterns, files or folders'), 'Count'])

        self.listExclude.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.listExclude.header().setSectionsClickable(True)
        self.listExclude.header().setSortIndicatorShown(True)
        self.listExclude.header().setSectionHidden(1, True)
        self.listExcludeSortLoop = False
        self.listExclude.header().sortIndicatorChanged \
            .connect(self.excludeCustomSortOrder)

        layout.addWidget(self.listExclude)
        self.listExcludeCount = 0

        label = QLabel(_('Highly recommended') + ':', self)
        qttools.setFontBold(label)
        layout.addWidget(label)
        label = QLabel(', '.join(sorted(self.config.DEFAULT_EXCLUDE)), self)
        label.setWordWrap(True)
        layout.addWidget(label)

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
            _('Exclude files bigger than: '), self)
        self.cbExcludeBySize.setToolTip(
            _('Exclude files bigger than value in %(prefix)s.\n'
              'With \'Full rsync mode\' disabled this will only affect '
              'new files\n'
              'because for rsync this is a transfer option, not an '
              'exclude option.\n'
              'So big files that have been backed up before will remain '
              'in snapshots\n'
              'even if they have changed.' % {'prefix': 'MiB'})
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
        scrollArea.setFrameStyle(QFrame.NoFrame)
        self.tabs.addTab(scrollArea, _('&Auto-remove'))

        layoutWidget = QWidget(self)
        layout = QGridLayout(layoutWidget)

        # remove old snapshots
        self.cbRemoveOlder = QCheckBox(_('Older than') + ':', self)
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
            _('If free space is less than') + ':', self)
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
            _('If free inodes is less than') + ':', self)
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
        self.cbSmartRemove = QCheckBox(_('Smart remove:'), self)
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
        scrollArea.setFrameStyle(QFrame.NoFrame)
        self.tabs.addTab(scrollArea, _('&Options'))

        layoutWidget = QWidget(self)
        layout = QVBoxLayout(layoutWidget)

        self.cbNotify = QCheckBox(_('Enable notifications'), self)
        layout.addWidget(self.cbNotify)

        self.cbNoSnapshotOnBattery \
            = QCheckBox(_('Disable snapshots when on battery'), self)
        if not tools.powerStatusAvailable():
            self.cbNoSnapshotOnBattery.setEnabled(False)
            self.cbNoSnapshotOnBattery.setToolTip(
                _('Power status not available from system'))
        layout.addWidget(self.cbNoSnapshotOnBattery)

        self.cbGlobalFlock = QCheckBox(_('Run only one snapshot at a time'))
        self.cbGlobalFlock.setToolTip(
            _('Other snapshots will be blocked until the current snapshot '
              'is done.\n'
              'This is a global option. So it will affect all profiles '
              'for this user.\n'
              'But you need to activate this for all other users, too.')
        )
        layout.addWidget(self.cbGlobalFlock)

        self.cbBackupOnRestore = QCheckBox(
            _('Backup replaced files on restore'), self)
        self.cbBackupOnRestore.setToolTip(
            _("Newer versions of files will be renamed with trailing "
              "{suffix} before restoring.\n"
              "If you don't need them anymore you can remove them with {cmd}")
            .format(suffix=self.snapshots.backupSuffix(),
                    cmd='find ./ -name "*{suffix}" -delete'
                        .format(suffix=self.snapshots.backupSuffix())
                    )
        )
        layout.addWidget(self.cbBackupOnRestore)

        self.cbContinueOnErrors = QCheckBox(
            _('Continue on errors (keep incomplete snapshots)'), self)
        layout.addWidget(self.cbContinueOnErrors)

        self.cbUseChecksum = QCheckBox(
            _('Use checksum to detect changes'), self)
        layout.addWidget(self.cbUseChecksum)

        self.cbTakeSnapshotRegardlessOfChanges = QCheckBox(
            _('Take a new snapshot whether there were changes or not.'))
        layout.addWidget(self.cbTakeSnapshotRegardlessOfChanges)

        # log level
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)

        hlayout.addWidget(QLabel(_('Log Level') + ':', self))

        self.comboLogLevel = QComboBox(self)
        hlayout.addWidget(self.comboLogLevel, 1)

        self.comboLogLevel.addItem(QIcon(), _('None'), 0)

        # Note about ngettext plural forms: n=102 means "Other" in Arabic and
        # "Few" in Polish.
        # Research in translation community indicate this as the best fit to
        # the meaning of "all".
        self.comboLogLevel.addItem(QIcon(), _('Errors'), 1)
        self.comboLogLevel.addItem(
            QIcon(),
            _('Changes') + ' & ' + _('Errors'), 2)
        self.comboLogLevel.addItem(QIcon(), _('All'), 3)

        #
        layout.addStretch()
        scrollArea.setWidget(layoutWidget)
        scrollArea.setWidgetResizable(True)

        # TAB: Expert Options
        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.NoFrame)
        self.tabs.addTab(scrollArea, _('E&xpert Options'))

        layoutWidget = QWidget(self)
        layout = QVBoxLayout(layoutWidget)

        label = QLabel(_('Caution: Change these options only if you really '
                         'know what you are doing.'), self)
        qttools.setFontBold(label)
        layout.addWidget(label)

        label = QLabel(_("Run 'rsync' with '{cmd}':").format(cmd='nice'))
        layout.addWidget(label)
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        layout.addLayout(grid)

        self.cbNiceOnCron = QCheckBox(
            _('as cron job') + self.printDefault(
                self.config.DEFAULT_RUN_NICE_FROM_CRON), self)
        grid.addWidget(self.cbNiceOnCron, 0, 1)

        self.cbNiceOnRemote = QCheckBox(
            _('on remote host') + self.printDefault(
                self.config.DEFAULT_RUN_NICE_ON_REMOTE), self)
        grid.addWidget(self.cbNiceOnRemote, 1, 1)

        label = QLabel(_("Run 'rsync' with '{cmd}':").format(cmd='ionice'))
        layout.addWidget(label)
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        layout.addLayout(grid)

        self.cbIoniceOnCron = QCheckBox(
            _('as cron job') + self.printDefault(
                self.config.DEFAULT_RUN_IONICE_FROM_CRON), self)
        grid.addWidget(self.cbIoniceOnCron, 0, 1)

        self.cbIoniceOnUser = QCheckBox(
            _('when taking a manual snapshot') + self.printDefault(
                self.config.DEFAULT_RUN_IONICE_FROM_USER), self)
        grid.addWidget(self.cbIoniceOnUser, 1, 1)

        self.cbIoniceOnRemote = QCheckBox(
            _('on remote host') + self.printDefault(
                self.config.DEFAULT_RUN_IONICE_ON_REMOTE), self)
        grid.addWidget(self.cbIoniceOnRemote, 2, 1)

        self.nocacheAvailable = tools.checkCommand('nocache')
        txt = _("Run 'rsync' with '{cmd}':").format(cmd='nocache')

        if not self.nocacheAvailable:
            txt += ' ' + _("(Please install 'nocache' to enable this option)")
        layout.addWidget(QLabel(txt))
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        layout.addLayout(grid)

        self.cbNocacheOnLocal = QCheckBox(
            _('on local machine') + self.printDefault(
                self.config.DEFAULT_RUN_NOCACHE_ON_LOCAL), self)
        self.cbNocacheOnLocal.setEnabled(self.nocacheAvailable)
        grid.addWidget(self.cbNocacheOnLocal, 0, 1)

        self.cbNocacheOnRemote = QCheckBox(
            _('on remote host') + self.printDefault(
                self.config.DEFAULT_RUN_NOCACHE_ON_REMOTE), self)
        grid.addWidget(self.cbNocacheOnRemote, 2, 1)

        self.cbRedirectStdoutInCron = QCheckBox(
            _('Redirect stdout to /dev/null in cronjobs.')
            + self.printDefault(self.config.DEFAULT_REDIRECT_STDOUT_IN_CRON),
            self)
        self.cbRedirectStdoutInCron.setToolTip(
            'cron will automatically send an email with attached output '
            'of cronjobs if an MTA is installed.')
        layout.addWidget(self.cbRedirectStdoutInCron)

        self.cbRedirectStderrInCron = QCheckBox(
            _('Redirect stderr to /dev/null in cronjobs.')
            + self.printDefault(self.config.DEFAULT_REDIRECT_STDERR_IN_CRON),
            self)
        self.cbRedirectStderrInCron.setToolTip(
            'cron will automatically send an email with attached errors '
            'of cronjobs if an MTA is installed.')
        layout.addWidget(self.cbRedirectStderrInCron)

        # bwlimit
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        self.cbBwlimit = QCheckBox(
            _('Limit rsync bandwidth usage') + ': ', self)
        hlayout.addWidget(self.cbBwlimit)
        self.spbBwlimit = QSpinBox(self)
        self.spbBwlimit.setSuffix(' ' + _('KB/sec'))
        self.spbBwlimit.setSingleStep(100)
        self.spbBwlimit.setRange(0, 1000000)
        hlayout.addWidget(self.spbBwlimit)
        hlayout.addStretch()
        enabled = lambda state: self.spbBwlimit.setEnabled(state)
        enabled(False)
        self.cbBwlimit.stateChanged.connect(enabled)
        self.cbBwlimit.setToolTip(
            'uses \'rsync --bwlimit=RATE\'\n'
            'From \'man rsync\':\n'
            'This option allows you to specify the maximum transfer rate for\n'
            'the data sent over the socket, specified in units per second.\n'
            'The RATE value can be suffixed with a string to indicate a size\n'
            'multiplier, and may be a fractional value '
            '(e.g. "--bwlimit=1.5m").\n'
            'If no suffix is specified, the value will be assumed to be in\n'
            'units of 1024 bytes (as if "K" or "KiB" had been appended).\n'
            'See the --max-size option for a description of '
            'all the available\n'
            'suffixes. A value of zero specifies no limit.\n\n'
            'For backward-compatibility reasons, the rate limit will be\n'
            'rounded to the nearest KiB unit, so no rate smaller than\n'
            '1024 bytes per second is possible.\n\n'
            'Rsync writes data over the socket in blocks, and this option\n'
            'both limits the size of the blocks that rsync writes, and tries\n'
            'to keep the average transfer rate at the requested limit.\n'
            'Some "burstiness" may be seen where rsync writes out a block\n'
            'of data and then sleeps to bring the average rate '
            'into compliance.\n\n'
            'Due to the internal buffering of data, the --progress option\n'
            'may not be an accurate reflection on how fast the data is being\n'
            'sent. This is because some files can show up as being rapidly\n'
            'sent when the data is quickly buffered, while other can show up\n'
            'as very slow when the flushing of the output buffer occurs.\n'
            'This may be fixed in a future version.'
            )

        self.cbPreserveAcl = QCheckBox(_('Preserve ACL'), self)
        self.cbPreserveAcl.setToolTip(
            'uses \'rsync -A\'\n'
            'From \'man rsync\':\n'
            'This option causes rsync to update the destination ACLs to be\n'
            'the same as the source ACLs. The option also implies '
            '--perms.\n\n'
            'The source and destination systems must have compatible ACL\n'
            'entries for this option to work properly.\n'
            'See the --fake-super option for a way to backup and restore\n'
            'ACLs that are not compatible.'
        )
        layout.addWidget(self.cbPreserveAcl)

        self.cbPreserveXattr = QCheckBox(
            _('Preserve extended attributes (xattr)'), self)
        self.cbPreserveXattr.setToolTip(
            'uses \'rsync -X\'\n'
            'From \'man rsync\':\n'
            'This option causes rsync to update the destination extended\n'
            'attributes to be the same as the source ones.\n\n'
            'For systems that support extended-attribute namespaces, a copy\n'
            'being done by a super-user copies all namespaces except\n'
            'system.*. A normal user only copies the user.* namespace.\n'
            'To be able to backup and restore non-user namespaces as '
            'a normal\n'
            'user, see the --fake-super option.\n\n'
            'Note that this option does not copy rsyncs special xattr values\n'
            '(e.g. those used by --fake-super) unless you repeat the option\n'
            '(e.g. -XX). This "copy all xattrs" mode cannot be used\n'
            'with --fake-super.'
        )
        layout.addWidget(self.cbPreserveXattr)

        self.cbCopyUnsafeLinks = QCheckBox(
            _('Copy unsafe links (works only with absolute links)'), self)
        self.cbCopyUnsafeLinks.setToolTip(
            'uses \'rsync --copy-unsafe-links\'\n'
            'From \'man rsync\':\n'
            'This tells rsync to copy the referent of symbolic links that\n'
            'point outside the copied tree. Absolute symlinks are also\n'
            'treated like ordinary files, and so are any symlinks in the\n'
            'source path itself when --relative is used. This option has\n'
            'no additional effect if --copy-links was also specified.\n'
        )
        layout.addWidget(self.cbCopyUnsafeLinks)

        self.cbCopyLinks = QCheckBox(
            _('Copy links (dereference symbolic links)'), self)
        self.cbCopyLinks.setToolTip(
            'uses \'rsync --copy-links\'\n'
            'From \'man rsync\':\n'
            'When symlinks are encountered, the item that they point to\n'
            '(the referent) is copied, rather than the symlink. In older\n'
            'versions of rsync, this option also had the side-effect of\n'
            'telling the receiving side to follow symlinks, such as\n'
            'symlinks to directories. In a modern rsync such as this one,\n'
            'you\'ll need to specify --keep-dirlinks (-K) to get this extra\n'
            'behavior. The only exception is when sending files to an rsync\n'
            'that is too old to understand -K -- in that case, the -L option\n'
            'will still have the side-effect of -K on that older '
            'receiving rsync.'
        )
        layout.addWidget(self.cbCopyLinks)

        # additional rsync options
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        tooltip = _('Options must be quoted e.g. {example}.').format(
            example='--exclude-from="/path/to/my exclude file"')
        self.cbRsyncOptions = QCheckBox(
            _('Paste additional options to rsync'), self)
        self.cbRsyncOptions.setToolTip(tooltip)
        hlayout.addWidget(self.cbRsyncOptions)
        self.txtRsyncOptions = QLineEdit(self)
        self.txtRsyncOptions.setToolTip(tooltip)
        hlayout.addWidget(self.txtRsyncOptions)

        enabled = lambda state: self.txtRsyncOptions.setEnabled(state)
        enabled(False)
        self.cbRsyncOptions.stateChanged.connect(enabled)

        # ssh prefix
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        tooltip = _(
            'Prefix to run before every command on remote host.\n'
            'Variables need to be escaped with \\$FOO.\n'
            'This doesn\'t touch rsync. So to add a prefix\n'
            'for rsync use "%(cbRsyncOptions)s" with\n'
            '%(rsync_options_value)s\n\n'
            '%(default)s: %(def_value)s') % {
                'cbRsyncOptions': self.cbRsyncOptions.text(),
                'rsync_options_value': '--rsync-path="FOO=bar:\\$FOO /usr/bin/rsync"',
                'default': _('default'),
                'def_value': self.config.DEFAULT_SSH_PREFIX}
        self.cbSshPrefix = QCheckBox(_('Add prefix to SSH commands'), self)
        self.cbSshPrefix.setToolTip(tooltip)
        hlayout.addWidget(self.cbSshPrefix)
        self.txtSshPrefix = QLineEdit(self)
        self.txtSshPrefix.setToolTip(tooltip)
        hlayout.addWidget(self.txtSshPrefix)

        enabled = lambda state: self.txtSshPrefix.setEnabled(state)
        enabled(False)
        self.cbSshPrefix.stateChanged.connect(enabled)

        qttools.equalIndent(self.cbRsyncOptions, self.cbSshPrefix)

        self.cbSshCheckPing = QCheckBox(_('Check if remote host is online'))
        self.cbSshCheckPing.setToolTip(
            _('Warning: if disabled and the remote host\n'
              'is not available, this could lead to some\n'
              'weird errors.'))
        self.cbSshCheckCommands = QCheckBox(
            _('Check if remote host supports all necessary commands'))
        self.cbSshCheckCommands.setToolTip(
            _('Warning: if disabled and the remote host\n'
              'does not support all necessary commands,\n'
              'this could lead to some weird errors.'))
        layout.addWidget(self.cbSshCheckPing)
        layout.addWidget(self.cbSshCheckCommands)

        #
        layout.addStretch()
        scrollArea.setWidget(layoutWidget)
        scrollArea.setWidgetResizable(True)

        # buttons
        buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self)
        btnRestore = buttonBox.addButton(
            _('Restore Config'), QDialogButtonBox.ResetRole)
        btnUserCallback = buttonBox.addButton(
            _('Edit user-callback'), QDialogButtonBox.ResetRole)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        btnRestore.clicked.connect(self.restoreConfig)
        btnUserCallback.clicked.connect(self.editUserCallback)
        self.mainLayout.addWidget(buttonBox)

        self.updateProfiles()
        self.comboModesChanged()

        # enable tabs scroll buttons again but keep dialog size
        size = self.sizeHint()
        self.tabs.setUsesScrollButtons(scrollButtonDefault)
        self.resize(size)

        self.finished.connect(self.cleanup)

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

    def updateSchedule(self, backup_mode):
        if backup_mode == self.config.CUSTOM_HOUR:
            self.lblScheduleCronPatern.show()
            self.txtScheduleCronPatern.show()
        else:
            self.lblScheduleCronPatern.hide()
            self.txtScheduleCronPatern.hide()

        if backup_mode == self.config.WEEK:
            self.lblScheduleWeekday.show()
            self.comboScheduleWeekday.show()
        else:
            self.lblScheduleWeekday.hide()
            self.comboScheduleWeekday.hide()

        if backup_mode == self.config.MONTH:
            self.lblScheduleDay.show()
            self.comboScheduleDay.show()
        else:
            self.lblScheduleDay.hide()
            self.comboScheduleDay.hide()

        if backup_mode >= self.config.DAY:
            self.lblScheduleTime.show()
            self.comboScheduleTime.show()
        else:
            self.lblScheduleTime.hide()
            self.comboScheduleTime.hide()

        if self.config.REPEATEDLY <= backup_mode <= self.config.UDEV:
            self.lblScheduleRepeatedPeriod.show()
            self.spbScheduleRepeatedPeriod.show()
            self.comboScheduleRepeatedUnit.show()
            self.lblScheduleTime.hide()
            self.comboScheduleTime.hide()
        else:
            self.lblScheduleRepeatedPeriod.hide()
            self.spbScheduleRepeatedPeriod.hide()
            self.comboScheduleRepeatedUnit.hide()

        if backup_mode == self.config.REPEATEDLY:
            self.lblScheduleRepeated.show()
        else:
            self.lblScheduleRepeated.hide()

        if backup_mode == self.config.UDEV:
            self.lblScheduleUdev.show()
        else:
            self.lblScheduleUdev.hide()

    def scheduleChanged(self, index):
        backup_mode = self.comboSchedule.itemData(index)
        self.updateSchedule(backup_mode)

    def profileChanged(self, index):
        if self.disableProfileChanged:
            return

        profile_id = self.comboProfiles.currentProfileID()
        if not profile_id:
            return

        if profile_id != self.config.currentProfile():
            self.saveProfile()
            self.config.setCurrentProfile(profile_id)
            self.updateProfile()

    def updateProfiles(self, reloadSettings=True):
        if reloadSettings:
            self.updateProfile()

        current_profile_id = self.config.currentProfile()

        self.disableProfileChanged = True

        self.comboProfiles.clear()

        profiles = self.config.profilesSortedByName()
        for profile_id in profiles:
            self.comboProfiles.addProfileID(profile_id)
            if profile_id == current_profile_id:
                self.comboProfiles.setCurrentProfileID(profile_id)

        self.disableProfileChanged = False

    def updateProfile(self):
        if self.config.currentProfile() == '1':
            self.btnEditProfile.setEnabled(False)
            self.btnRemoveProfile.setEnabled(False)
        else:
            self.btnEditProfile.setEnabled(True)
            self.btnRemoveProfile.setEnabled(True)
        self.btnAddProfile.setEnabled(self.config.isConfigured('1'))

        # TAB: General
        # mode
        self.setComboValue(self.comboModes,
                           self.config.snapshotsMode(),
                           t='str')

        # local
        self.editSnapshotsPath.setText(
            self.config.snapshotsPath(mode='local'))

        # ssh
        self.txtSshHost.setText(self.config.sshHost())
        self.txtSshPort.setText(str(self.config.sshPort()))
        self.txtSshUser.setText(self.config.sshUser())
        self.txtSshPath.setText(self.config.sshSnapshotsPath())
        self.setComboValue(self.comboSshCipher,
                           self.config.sshCipher(),
                           t='str')
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

        self.setComboValue(self.comboSchedule, self.config.scheduleMode())
        self.setComboValue(self.comboScheduleTime, self.config.scheduleTime())
        self.setComboValue(self.comboScheduleDay, self.config.scheduleDay())
        self.setComboValue(self.comboScheduleWeekday,
                           self.config.scheduleWeekday())
        self.txtScheduleCronPatern.setText(self.config.customBackupTime())
        self.spbScheduleRepeatedPeriod.setValue(
            self.config.scheduleRepeatedPeriod())
        self.setComboValue(self.comboScheduleRepeatedUnit,
                           self.config.scheduleRepeatedUnit())
        self.updateSchedule(self.config.scheduleMode())

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
            self.addExclude(exclude)
        self.cbExcludeBySize.setChecked(self.config.excludeBySizeEnabled())
        self.spbExcludeBySize.setValue(self.config.excludeBySize())

        excludeSortColumn = int(self.config.profileIntValue(
            'qt.settingsdialog.exclude.SortColumn', 1))
        excludeSortOrder = Qt.SortOrder(
            self.config.profileIntValue('qt.settingsdialog.exclude.SortOrder',
                                        Qt.SortOrder.AscendingOrder)
        )
        self.listExclude.sortItems(excludeSortColumn, excludeSortOrder)

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
        self.cbNotify.setChecked(self.config.notify())
        self.cbNoSnapshotOnBattery.setChecked(
            self.config.noSnapshotOnBattery())
        self.cbGlobalFlock.setChecked(self.config.globalFlock())
        self.cbBackupOnRestore.setChecked(self.config.backupOnRestore())
        self.cbContinueOnErrors.setChecked(self.config.continueOnErrors())
        self.cbUseChecksum.setChecked(self.config.useChecksum())
        self.cbTakeSnapshotRegardlessOfChanges.setChecked(
            self.config.takeSnapshotRegardlessOfChanges())
        self.setComboValue(self.comboLogLevel, self.config.logLevel())

        # TAB: Expert Options
        self.cbNiceOnCron.setChecked(self.config.niceOnCron())
        self.cbIoniceOnCron.setChecked(self.config.ioniceOnCron())
        self.cbIoniceOnUser.setChecked(self.config.ioniceOnUser())
        self.cbNiceOnRemote.setChecked(self.config.niceOnRemote())
        self.cbIoniceOnRemote.setChecked(self.config.ioniceOnRemote())
        self.cbNocacheOnLocal.setChecked(
            self.config.nocacheOnLocal() and self.nocacheAvailable)
        self.cbNocacheOnRemote.setChecked(self.config.nocacheOnRemote())
        self.cbRedirectStdoutInCron.setChecked(
            self.config.redirectStdoutInCron())
        self.cbRedirectStderrInCron.setChecked(
            self.config.redirectStderrInCron())
        self.cbBwlimit.setChecked(self.config.bwlimitEnabled())
        self.spbBwlimit.setValue(self.config.bwlimit())
        self.cbPreserveAcl.setChecked(self.config.preserveAcl())
        self.cbPreserveXattr.setChecked(self.config.preserveXattr())
        self.cbCopyUnsafeLinks.setChecked(self.config.copyUnsafeLinks())
        self.cbCopyLinks.setChecked(self.config.copyLinks())
        self.cbRsyncOptions.setChecked(self.config.rsyncOptionsEnabled())
        self.txtRsyncOptions.setText(self.config.rsyncOptions())
        self.cbSshPrefix.setChecked(self.config.sshPrefixEnabled())
        self.txtSshPrefix.setText(self.config.sshPrefix())
        self.cbSshCheckPing.setChecked(self.config.sshCheckPingHost())
        self.cbSshCheckCommands.setChecked(self.config.sshCheckCommands())

        # update
        self.updateRemoveOlder()
        self.updateFreeSpace()

    def saveProfile(self):
        item_data = self.comboSchedule.itemData(
            self.comboSchedule.currentIndex())

        if item_data == self.config.CUSTOM_HOUR:

            if not tools.checkCronPattern(self.txtScheduleCronPatern.text()):

                self.errorHandler(
                    _('Custom hours can only be a comma separated list of '
                      'hours (e.g. 8,12,18,23) or */3 for periodic '
                      'backups every 3 hours.')
                )

                return False

        # mode
        mode = str(self.comboModes.itemData(self.comboModes.currentIndex()))
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

        # save ssh
        self.config.setSshHost(self.txtSshHost.text())
        self.config.setSshPort(self.txtSshPort.text())
        self.config.setSshUser(self.txtSshUser.text())
        self.config.setSshSnapshotsPath(self.txtSshPath.text())
        self.config.setSshCipher(
            self.comboSshCipher.itemData(self.comboSshCipher.currentIndex()))

        if mode in ('ssh', 'ssh_encfs'):

            if not self.txtSshPrivateKeyFile.text():

                question = _('You did not choose a private key file for '
                             'SSH.\nWould you like to generate a new '
                             'password-less public/private key pair?')
                if self.questionHandler(question):
                    self.btnSshKeyGenClicked()

                if not self.txtSshPrivateKeyFile.text():
                    return False

            if not os.path.isfile(self.txtSshPrivateKeyFile.text()):
                self.errorHandler(
                    _('Private key file "{file}" does not exist.')
                    .format(file=self.txtSshPrivateKeyFile.text())
                )
                self.txtSshPrivateKeyFile.setText('')

                return False

        self.config.setSshPrivateKeyFile(self.txtSshPrivateKeyFile.text())

        # save local_encfs
        self.config.setLocalEncfsPath(self.editSnapshotsPath.text())

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
            include_list.append((item.text(0), item.data(0, Qt.ItemDataRole.UserRole)))

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

        # schedule
        self.config.setScheduleMode(
            self.comboSchedule.itemData(self.comboSchedule.currentIndex()))
        self.config.setScheduleTime(
            self.comboScheduleTime.itemData(
                self.comboScheduleTime.currentIndex()))
        self.config.setScheduleWeekday(
            self.comboScheduleWeekday.itemData(
                self.comboScheduleWeekday.currentIndex()))
        self.config.setScheduleDay(
            self.comboScheduleDay.itemData(
                self.comboScheduleDay.currentIndex()))
        self.config.setCustomBackupTime(self.txtScheduleCronPatern.text())
        self.config.setScheduleRepeatedPeriod(
            self.spbScheduleRepeatedPeriod.value())
        self.config.setScheduleRepeatedUnit(
            self.comboScheduleRepeatedUnit.itemData(
                self.comboScheduleRepeatedUnit.currentIndex()))

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
        self.config.setNotify(self.cbNotify.isChecked())
        self.config.setNoSnapshotOnBattery(
            self.cbNoSnapshotOnBattery.isChecked())
        self.config.setGlobalFlock(self.cbGlobalFlock.isChecked())
        self.config.setBackupOnRestore(self.cbBackupOnRestore.isChecked())
        self.config.setContinueOnErrors(self.cbContinueOnErrors.isChecked())
        self.config.setUseChecksum(self.cbUseChecksum.isChecked())
        self.config.setTakeSnapshotRegardlessOfChanges(
            self.cbTakeSnapshotRegardlessOfChanges.isChecked())
        self.config.setLogLevel(
            self.comboLogLevel.itemData(self.comboLogLevel.currentIndex()))

        # expert options
        self.config.setNiceOnCron(self.cbNiceOnCron.isChecked())
        self.config.setIoniceOnCron(self.cbIoniceOnCron.isChecked())
        self.config.setIoniceOnUser(self.cbIoniceOnUser.isChecked())
        self.config.setNiceOnRemote(self.cbNiceOnRemote.isChecked())
        self.config.setIoniceOnRemote(self.cbIoniceOnRemote.isChecked())
        self.config.setNocacheOnLocal(self.cbNocacheOnLocal.isChecked())
        self.config.setNocacheOnRemote(self.cbNocacheOnRemote.isChecked())
        self.config.setRedirectStdoutInCron(
            self.cbRedirectStdoutInCron.isChecked())
        self.config.setRedirectStderrInCron(
            self.cbRedirectStderrInCron.isChecked())
        self.config.setBwlimit(self.cbBwlimit.isChecked(),
                               self.spbBwlimit.value())
        self.config.setPreserveAcl(self.cbPreserveAcl.isChecked())
        self.config.setPreserveXattr(self.cbPreserveXattr.isChecked())
        self.config.setCopyUnsafeLinks(self.cbCopyUnsafeLinks.isChecked())
        self.config.setCopyLinks(self.cbCopyLinks.isChecked())
        self.config.setRsyncOptions(self.cbRsyncOptions.isChecked(),
                                    self.txtRsyncOptions.text())
        self.config.setSshPrefix(self.cbSshPrefix.isChecked(),
                                 self.txtSshPrefix.text())
        self.config.setSshCheckPingHost(self.cbSshCheckPing.isChecked())
        self.config.setSshCheckCommands(self.cbSshCheckCommands.isChecked())

        # TODO - consider a single API method to bridge the UI layer
        # (settings dialog) and backend layer (config)
        # when setting snapshots path rather than having to call the
        # mount module from the UI layer
        #
        # currently, setting snapshots path requires the path to be mounted.
        # it seems that it might be nice,
        # since the config object is more than a data structure, but has
        # side-effect logic as well, to have the
        # config.setSnapshotsPath() method take care of everything it needs
        # to perform its job
        # (mounting and unmounting the fuse filesystem if necessary).
        # https://en.wikipedia.org/wiki/Single_responsibility_principle

        if not self.config.SNAPSHOT_MODES[mode][0] is None:
            # preMountCheck
            mnt = mount.Mount(cfg=self.config, tmp_mount=True, parent=self)

            try:
                mnt.preMountCheck(mode=mode, first_run=True, **mount_kwargs)
            except NoPubKeyLogin as ex:
                logger.error(str(ex), self)

                question = _(
                    'Would you like to copy your public SSH key to the\n'
                    'remote host to enable password-less login?'
                )
                rc_copy_id = sshtools.sshCopyId(
                    self.config.sshPrivateKeyFile() + '.pub',
                    self.config.sshUser(),
                    self.config.sshHost(),
                    port=str(self.config.sshPort()),
                    askPass=tools.which('backintime-askpass'),
                    cipher=self.config.sshCipher()
                )

                if self.questionHandler(question) and rc_copy_id:
                    return self.saveProfile()
                else:
                    return False

            except KnownHost as ex:
                logger.error(str(ex), self)
                fingerprint, hashedKey, keyType = sshtools.sshHostKey(
                    self.config.sshHost(), str(self.config.sshPort())
                )

                if not fingerprint:
                    self.errorHandler(str(ex))

                    return False

                msg = _("The authenticity of host {host} can't be "
                        "established.\n\n{keytype} key fingerprint is:") \
                        .format(host='"{}"'.format(self.config.sshHost()),
                                keytype=keyType)
                options = []
                lblFingerprint = QLabel(fingerprint + '\n')
                lblFingerprint.setWordWrap(False)
                lblFingerprint.setFont(QFont('Monospace'))
                options.append({'widget': lblFingerprint, 'retFunc': None})
                lblQuestion = QLabel(
                    _("Please verify this fingerprint! Would you like to "
                      "add it to your 'known_hosts' file?")
                )
                options.append({'widget': lblQuestion, 'retFunc': None})

                if messagebox.warningYesNoOptions(self, msg, options)[0]:
                    sshtools.writeKnownHostsFile(hashedKey)
                    return self.saveProfile()
                else:
                    return False

            except MountException as ex:
                self.errorHandler(str(ex))

                return False

            # okay, lets try to mount
            try:
                hash_id = mnt.mount(mode=mode, check=False, **mount_kwargs)

            except MountException as ex:
                self.errorHandler(str(ex))

                return False

        # save password
        self.config.setPasswordSave(self.cbPasswordSave.isChecked(),
                                    mode=mode)
        self.config.setPasswordUseCache(self.cbPasswordUseCache.isChecked(),
                                        mode=mode)
        self.config.setPassword(password_1, mode=mode)
        self.config.setPassword(password_2, mode=mode, pw_id=2)

        # save snaphots_path
        if self.config.SNAPSHOT_MODES[mode][0] is None:
            snapshots_path = self.editSnapshotsPath.text()
        else:
            snapshots_path = self.config.snapshotsPath(mode=mode,
                                                       tmp_mount=True)

        ret = self.config.setSnapshotsPath(snapshots_path, mode=mode)

        if not ret:
            return ret

        # umount
        if not self.config.SNAPSHOT_MODES[mode][0] is None:

            try:
                mnt.umount(hash_id=hash_id)
            except MountException as ex:
                self.errorHandler(str(ex))

                return False

        return True

    def errorHandler(self, message):
        messagebox.critical(self, message)

    def questionHandler(self, message):
        return QMessageBox.Yes == messagebox.warningYesNo(self, message)

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

        if data[1] == 0:
            item.setIcon(0, self.icon.FOLDER)
        else:
            item.setIcon(0, self.icon.FILE)

        item.setText(0, data[0])
        item.setData(0, Qt.ItemDataRole.UserRole, data[1])
        self.listIncludeCount += 1
        item.setText(1, str(self.listIncludeCount).zfill(6))
        item.setData(1, Qt.ItemDataRole.UserRole, self.listIncludeCount)
        self.listInclude.addTopLevelItem(item)

        if self.listInclude.currentItem() is None:
            self.listInclude.setCurrentItem(item)

        return item

    def addExclude(self, pattern):
        item = QTreeWidgetItem()
        item.setText(0, pattern)
        item.setData(0, Qt.ItemDataRole.UserRole, pattern)
        self.listExcludeCount += 1
        item.setText(1, str(self.listExcludeCount).zfill(6))
        item.setData(1, Qt.ItemDataRole.UserRole, self.listExcludeCount)
        self.formatExcludeItem(item)
        self.listExclude.addTopLevelItem(item)

        if self.listExclude.currentItem() is None:
            self.listExclude.setCurrentItem(item)

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

    def addExclude_(self, pattern):
        if not pattern:
            return

        for index in range(self.listExclude.topLevelItemCount()):
            item = self.listExclude.topLevelItem(index)
            if pattern == item.text(0):
                return

        self.addExclude(pattern)

    def btnExcludeAddClicked(self):
        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.setWindowTitle(_('Exclude pattern'))
        dlg.setLabelText('')
        dlg.resize(400, 0)
        if not dlg.exec():
            return
        pattern = dlg.textValue().strip()

        if not pattern:
            return

        self.addExclude_(pattern)

    def btnExcludeFileClicked(self):
        for path in qttools.getOpenFileNames(self, _('Exclude file')):
            self.addExclude_(path)

    def btnExcludeFolderClicked(self):
        for path in qttools.getExistingDirectories(self, _('Exclude folder')):
            self.addExclude_(path)

    def btnExcludeDefaultClicked(self):
        for path in self.config.DEFAULT_EXCLUDE:
            self.addExclude_(path)

    def btnIncludeRemoveClicked(self):
        for item in self.listInclude.selectedItems():
            index = self.listInclude.indexOfTopLevelItem(item)
            if index < 0:
                continue

            self.listInclude.takeTopLevelItem(index)

        if self.listInclude.topLevelItemCount() > 0:
            self.listInclude.setCurrentItem(self.listInclude.topLevelItem(0))

    def btnIncludeFileClicked(self):
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

    def btnSnapshotsPathClicked(self):
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
                if not self.questionHandler(question):
                    return

                self.config.removeProfileKey('snapshots.path.uuid')

            self.editSnapshotsPath.setText(self.config.preparePath(path))

    def btnSshPrivateKeyFileClicked(self):
        old_file = self.txtSshPrivateKeyFile.text()

        if old_file:
            start_dir = self.txtSshPrivateKeyFile.text()
        else:
            start_dir = self.config.sshPrivateKeyFolder()
        f = qttools.getOpenFileName(self, _('SSH private key'), start_dir)
        if f:
            self.txtSshPrivateKeyFile.setText(f)

    def btnSshKeyGenClicked(self):
        key = os.path.join(self.config.sshPrivateKeyFolder(), 'id_rsa')
        if sshtools.sshKeyGen(key):
            self.txtSshPrivateKeyFile.setText(key)
        else:
            self.errorHandler(_('Failed to create new SSH key in {path}')
                              .format(path=key))

    def comboModesChanged(self, *params):
        if not params:
            index = self.comboModes.currentIndex()
        else:
            index = params[0]
        active_mode = str(self.comboModes.itemData(index))
        if active_mode != self.mode:
            for mode in list(self.config.SNAPSHOT_MODES.keys()):
                getattr(self, 'mode%s' % tools.camelCase(mode)).hide()
            for mode in list(self.config.SNAPSHOT_MODES.keys()):
                if active_mode == mode:
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
        self.cbNiceOnRemote.setEnabled(enabled)
        self.cbIoniceOnRemote.setEnabled(enabled)
        self.cbNocacheOnRemote.setEnabled(enabled)
        self.cbSmartRemoveRunRemoteInBackground.setHidden(not enabled)
        self.cbSshPrefix.setHidden(not enabled)
        self.txtSshPrefix.setHidden(not enabled)
        self.cbSshCheckPing.setHidden(not enabled)
        self.cbSshCheckCommands.setHidden(not enabled)

        self.encfsWarning.setHidden(
            active_mode not in ('local_encfs', 'ssh_encfs'))

    def fullPathChanged(self, dummy):
        if self.mode in ('ssh', 'ssh_encfs'):
            path = self.txtSshPath.text()
        else:
            path = self.editSnapshotsPath.text()
        self.lblFullPath.setText(
            _('Full snapshot path: ') +
            os.path.join(
                path,
                'backintime',
                self.txtHost.text(),
                self.txtUser.text(),
                self.txt_profile.text()
                ))

    def updateExcludeItems(self):
        for index in range(self.listExclude.topLevelItemCount()):
            item = self.listExclude.topLevelItem(index)
            self.formatExcludeItem(item)

    def formatExcludeItem(self, item):
        no_encr_wildcard = tools.patternHasNotEncryptableWildcard(item.text(0))
        if self.mode == 'ssh_encfs' and no_encr_wildcard:
            item.setIcon(0, self.icon.INVALID_EXCLUDE)
            item.setBackground(0, QPalette().brush(QPalette.Active,
                                                   QPalette.Link))

        elif item.text(0) in self.config.DEFAULT_EXCLUDE:
            item.setIcon(0, self.icon.DEFAULT_EXCLUDE)
            item.setBackground(0, QBrush())

        else:
            item.setIcon(0, self.icon.EXCLUDE)
            item.setBackground(0, QBrush())

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

    def printDefault(self, value):
        if value:
            value_ = _('enabled')

        else:
            value_ = _('disabled')

        return ' (%s: %s)' % (_('default'), value_)

    def restoreConfig(self, *args):
        RestoreConfigDialog(self).exec()
        self.updateProfiles()

    def editUserCallback(self, *args):
        EditUserCallback(self).exec()

    def accept(self):
        if self.validate():
            super(SettingsDialog, self).accept()

    def cleanup(self, result):
        self.config.clearHandlers()

        if not result:
            self.config.dict = self.configDictCopy

        self.config.setCurrentProfile(self.originalCurrentProfile)

        if result:
            self.parent.remount(self.originalCurrentProfile,
                                self.originalCurrentProfile)
            self.parent.updateProfiles()


class RestoreConfigDialog(QDialog):
    """
    Show a dialog that will help to restore BITs configuration.
    User can select a config from previous snapshots.
    """

    def __init__(self, parent):
        super(RestoreConfigDialog, self).__init__(parent)

        self.parent = parent
        self.config = parent.config
        self.snapshots = parent.snapshots

        import icon
        self.icon = icon
        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(_('Restore Settings'))

        layout = QVBoxLayout(self)

        # show a hint on how the snapshot path will look like.
        samplePath = os.path.join(
            'backintime',
            self.config.host(),
            self.config.user(), '1',
            snapshots.SID(datetime.datetime.now(), self.config).sid
        )

        label = QLabel(_(
            "Please navigate to the snapshot from which you want to restore "
            "{appName}'s configuration. The path may look like:\n"
            "{samplePath}\n\nIf your snapshots are on a remote drive or if "
            "they are encrypted you need to manually mount them first. "
            "If you use Mode SSH you also may need to set up public key "
            "login to the remote host.\n"
            "Take a look at 'man backintime'.")
            .format(
                appName=self.config.APP_NAME,
                samplePath=samplePath),
            self
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        # treeView
        self.treeView = qttools.MyTreeView(self)
        self.treeViewModel = QFileSystemModel(self)
        self.treeViewModel.setRootPath(QDir().rootPath())
        self.treeViewModel.setReadOnly(True)
        self.treeViewModel.setFilter(QDir.Filter.AllDirs |
                                     QDir.Filter.NoDotAndDotDot |
                                     QDir.Filter.Hidden)

        self.treeViewFilterProxy = QSortFilterProxyModel(self)
        self.treeViewFilterProxy.setDynamicSortFilter(True)
        self.treeViewFilterProxy.setSourceModel(self.treeViewModel)

        self.treeViewFilterProxy.setFilterRegExp(r'^[^\.]')

        self.treeView.setModel(self.treeViewFilterProxy)
        for col in range(self.treeView.header().count()):
            self.treeView.setColumnHidden(col, col != 0)
        self.treeView.header().hide()

        # expand users home
        self.expandAll(os.path.expanduser('~'))
        layout.addWidget(self.treeView)

        # context menu
        self.treeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.onContextMenu)
        self.contextMenu = QMenu(self)
        self.btnShowHidden = self.contextMenu.addAction(
            icon.SHOW_HIDDEN, _('Show hidden files'))
        self.btnShowHidden.setCheckable(True)
        self.btnShowHidden.toggled.connect(self.onBtnShowHidden)

        # colors
        self.colorRed = QPalette()
        self.colorRed.setColor(QPalette.WindowText, QColor(205, 0, 0))
        self.colorGreen = QPalette()
        self.colorGreen.setColor(QPalette.WindowText, QColor(0, 160, 0))

        # wait indicator which will show that the scan for
        # snapshots is still running
        self.wait = QProgressBar(self)
        self.wait.setMinimum(0)
        self.wait.setMaximum(0)
        self.wait.setMaximumHeight(7)
        layout.addWidget(self.wait)

        # show where a snapshot with config was found
        self.lblFound = QLabel(_('No config found'), self)
        self.lblFound.setWordWrap(True)
        self.lblFound.setPalette(self.colorRed)
        layout.addWidget(self.lblFound)

        # show profiles inside the config
        self.widgetProfiles = QWidget(self)
        self.widgetProfiles.setContentsMargins(0, 0, 0, 0)
        self.widgetProfiles.hide()
        self.gridProfiles = QGridLayout()
        self.gridProfiles.setContentsMargins(0, 0, 0, 0)
        self.gridProfiles.setHorizontalSpacing(20)
        self.widgetProfiles.setLayout(self.gridProfiles)
        layout.addWidget(self.widgetProfiles)

        self.restoreConfig = None

        self.scan = ScanFileSystem(self)

        self.treeView.myCurrentIndexChanged.connect(self.indexChanged)
        self.scan.foundConfig.connect(self.scanFound)
        self.scan.finished.connect(self.scanFinished)

        buttonBox = QDialogButtonBox(self)
        self.restoreButton = buttonBox.addButton(
            _('Restore'), QDialogButtonBox.AcceptRole)
        self.restoreButton.setEnabled(False)
        buttonBox.addButton(QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

        self.scan.start()

        self.resize(600, 700)

    def pathFromIndex(self, index):
        """
        return a path string for a given treeView index
        """
        sourceIndex = self.treeViewFilterProxy.mapToSource(index)
        return str(self.treeViewModel.filePath(sourceIndex))

    def indexFromPath(self, path):
        """
        return the index for path which can be used in treeView
        """
        indexSource = self.treeViewModel.index(path)
        return self.treeViewFilterProxy.mapFromSource(indexSource)

    def indexChanged(self, current, previous):
        """
        called every time a new item is chosen in treeView.
        If there was a config found inside the selected folder, show
        available information about the config.
        """
        cfg = self.searchConfig(self.pathFromIndex(current))
        if cfg:
            self.expandAll(
                os.path.dirname(os.path.dirname(cfg._LOCAL_CONFIG_PATH)))
            self.lblFound.setText(cfg._LOCAL_CONFIG_PATH)
            self.lblFound.setPalette(self.colorGreen)
            self.showProfile(cfg)
            self.restoreConfig = cfg
        else:
            self.lblFound.setText(_('No config found'))
            self.lblFound.setPalette(self.colorRed)
            self.widgetProfiles.hide()
            self.restoreConfig = None
        self.restoreButton.setEnabled(bool(cfg))

    def searchConfig(self, path):
        """
        try to find config in couple possible subfolders
        """
        snapshotPath = os.path.join('backintime',
                                    self.config.host(),
                                    self.config.user())
        tryPaths = ['', '..', 'last_snapshot']
        tryPaths.extend([
            os.path.join(snapshotPath, str(i), 'last_snapshot')
            for i in range(10)])

        for p in tryPaths:
            cfgPath = os.path.join(path, p, 'config')

            if os.path.exists(cfgPath):

                try:
                    cfg = config.Config(cfgPath)
                    if cfg.isConfigured():
                        return cfg
                except:
                    pass

        return

    def expandAll(self, path):
        """
        expand all folders from filesystem root to given path
        """
        paths = [path, ]
        while len(path) > 1:
            path = os.path.dirname(path)
            paths.append(path)
        paths.append('/')
        paths.reverse()
        [self.treeView.expand(self.indexFromPath(p)) for p in paths]

    def showProfile(self, cfg):
        """
        show information about the profiles inside cfg
        """
        child = self.gridProfiles.takeAt(0)

        while child:
            child.widget().deleteLater()
            child = self.gridProfiles.takeAt(0)

        for row, profileId in enumerate(cfg.profiles()):

            for col, txt in enumerate((
                    _('Profile') + ': ' + str(profileId),
                    cfg.profileName(profileId),
                    _('Mode') + ': ' + cfg.SNAPSHOT_MODES[
                        cfg.snapshotsMode(profileId)][1]
                    )):
                self.gridProfiles.addWidget(QLabel(txt, self), row, col)

        self.gridProfiles.setColumnStretch(col, 1)
        self.widgetProfiles.show()

    def scanFound(self, path):
        """
        scan hit a config. Expand the snapshot folder.
        """
        self.expandAll(os.path.dirname(path))

    def scanFinished(self):
        """
        scan is done. Delete the wait indicator
        """
        self.wait.deleteLater()

    def onContextMenu(self, point):
        self.contextMenu.exec(self.treeView.mapToGlobal(point))

    def onBtnShowHidden(self, checked):
        if checked:
            self.treeViewFilterProxy.setFilterRegExp(r'')
        else:
            self.treeViewFilterProxy.setFilterRegExp(r'^[^\.]')

    def accept(self):
        """
        handle over the dict from the selected config. The dict contains
        all settings from the config.
        """
        if self.restoreConfig:
            self.config.dict = self.restoreConfig.dict
        super(RestoreConfigDialog, self).accept()

    def exec(self):
        """
        stop the scan thread if it is still running after dialog was closed.
        """
        ret = super(RestoreConfigDialog, self).exec()
        self.scan.stop()
        return ret


class ScanFileSystem(QThread):
    CONFIG = 'config'
    BACKUP = 'backup'
    BACKINTIME = 'backintime'

    foundConfig = pyqtSignal(str)

    def __init__(self, parent):
        super(ScanFileSystem, self).__init__(parent)
        self.stopper = False

    def stop(self):
        """
        prepare stop and wait for finish.
        """
        self.stopper = True
        return self.wait()

    def run(self):
        """
        search in order of hopefully fastest way to find the snapshots.
        1. /home/USER 2. /media 3. /mnt and at last filesystem root.
        Already searched paths will be excluded.
        """
        searchOrder = [os.path.expanduser('~'), '/media', '/mnt', '/']
        for scan in searchOrder:
            exclude = searchOrder[:]
            exclude.remove(scan)
            for path in self.scanPath(scan, exclude):
                self.foundConfig.emit(path)

    def scanPath(self, path, excludes=()):
        """
        walk through all folders and try to find 'config' file.
        If found make sure it is nested in backintime/FOO/BAR/1/2345/config and
        return its path.
        Exclude all paths from excludes and also
        all backintime/FOO/BAR/1/2345/backup
        """
        for root, dirs, files in os.walk(path, topdown=True):

            if self.stopper:
                return

            for exclude in excludes:
                exDir, exBase = os.path.split(exclude)

                if root == exDir:

                    if exBase in dirs:
                        del dirs[dirs.index(exBase)]

            if self.CONFIG in files:
                rootdirs = root.split(os.sep)

                if len(rootdirs) > 4 and rootdirs[-5].startswith(self.BACKINTIME):

                    if self.BACKUP in dirs:
                        del dirs[dirs.index(self.BACKUP)]

                    yield root


class EditUserCallback(QDialog):
    def __init__(self, parent):
        super(EditUserCallback, self).__init__(parent)
        self.config = parent.config
        self.script = self.config.takeSnapshotUserCallback()

        import icon
        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(self.script)
        self.resize(800, 500)

        layout = QVBoxLayout(self)
        self.edit = QPlainTextEdit(self)

        try:
            with open(self.script, 'rt') as f:
                self.edit.setPlainText(f.read())

        except IOError:
            pass

        layout.addWidget(self.edit)

        btnBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self)

        btnBox.accepted.connect(self.accept)
        btnBox.rejected.connect(self.reject)
        layout.addWidget(btnBox)

    def checkScript(self, script):
        m = re.match(r'^#!(/[\w/-]+)\n', script)

        if not m:
            logger.error(
                'user-callback script has no shebang (#!/bin/sh) line.')
            self.config.errorHandler(
                _('user-callback script has no shebang (#!/bin/sh) line.'))

            return False

        if not tools.checkCommand(m.group(1)):
            logger.error('Shebang in user-callback script is not executable.')
            self.config.errorHandler(
                _('Shebang in user-callback script is not executable.'))

            return False

        return True

    def accept(self):
        if not self.checkScript(self.edit.toPlainText()):
            return

        with open(self.script, 'wt') as f:
            f.write(self.edit.toPlainText())

        os.chmod(self.script, 0o755)

        super(EditUserCallback, self).accept()


def debugTrace():
    """
    Set a tracepoint in the Python debugger that works with Qt
    """
    from pdb import set_trace

    pyqtRemoveInputHook()
    set_trace()
