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

        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.Shape.NoFrame)

        # TAB: General
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
        qttools.set_wrapped_tooltip(
            self.cbGlobalFlock,
            _('Other snapshots will be blocked until the current snapshot '
              'is done. This is a global option. So it will affect all '
              'profiles for this user. But you need to activate this for all '
              'other users, too.')
        )
        layout.addWidget(self.cbGlobalFlock)

        self.cbBackupOnRestore = QCheckBox(
            _('Backup replaced files on restore'), self)
        qttools.set_wrapped_tooltip(
            self.cbBackupOnRestore,
            _("Newer versions of files will be renamed with trailing {suffix} "
              "before restoring. If you don't need them anymore you can "
              "remove them with {cmd}").format(
                  suffix=self.snapshots.backupSuffix(),
                  cmd='find ./ -name "*{suffix}" -delete'.format(
                      suffix=self.snapshots.backupSuffix()
                  )
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

        hlayout.addWidget(QLabel(_('Log Level:'), self))

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
        scrollArea.setFrameStyle(QFrame.Shape.NoFrame)
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
        qttools.set_wrapped_tooltip(
            self.cbRedirectStdoutInCron,
            _('Cron will automatically send an email with attached output '
              'of cronjobs if an MTA is installed.')
        )
        layout.addWidget(self.cbRedirectStdoutInCron)

        self.cbRedirectStderrInCron = QCheckBox(
            _('Redirect stderr to /dev/null in cronjobs.')
            + self.printDefault(self.config.DEFAULT_REDIRECT_STDERR_IN_CRON),
            self)
        qttools.set_wrapped_tooltip(
            self.cbRedirectStderrInCron,
            _('Cron will automatically send an email with attached errors '
              'of cronjobs if an MTA is installed.')
        )
        layout.addWidget(self.cbRedirectStderrInCron)

        # bwlimit
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        self.cbBwlimit = QCheckBox(_('Limit rsync bandwidth usage:'), self)
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
        qttools.set_wrapped_tooltip(
            self.cbBwlimit,
            [
                "Uses 'rsync --bwlimit=RATE'. From 'man rsync':",
                'This option allows you to specify the maximum transfer rate '
                'for the data sent over the socket, specified in units per '
                'second. The RATE value can be suffixed with a string to '
                'indicate a size multiplier, and may be a fractional value '
                '(e.g. "--bwlimit=1.5m").',
                'If no suffix is specified, the value will be assumed to be '
                'in units of 1024 bytes (as if "K" or "KiB" had been '
                'appended).',
                'See the --max-size option for a description of all the '
                'available suffixes. A value of zero specifies no limit.'
                '',
                'For backward-compatibility reasons, the rate limit will be '
                'rounded to the nearest KiB unit, so no rate smaller than '
                '1024 bytes per second is possible.',
                '',
                'Rsync writes data over the socket in blocks, and this option '
                'both limits the size of the blocks that rsync writes, and '
                'tries to keep the average transfer rate at the requested '
                'limit. Some "burstiness" may be seen where rsync writes out '
                'a block of data and then sleeps to bring the average rate '
                'into compliance.',
                '',
                'Due to the internal buffering of data, the --progress '
                'option may not be an accurate reflection on how fast the '
                'data is being sent. This is because some files can show up '
                'as being rapidly sent when the data is quickly buffered, '
                'while other can show up as very slow when the flushing of '
                'the output buffer occurs. This may be fixed in a future '
                'version.'
            ]
        )

        self.cbPreserveAcl = QCheckBox(_('Preserve ACL'), self)
        qttools.set_wrapped_tooltip(
            self.cbPreserveAcl,
            [
                "Uses 'rsync -A'. From 'man rsync':",
                'This option causes rsync to update the destination ACLs to '
                'be the same as the source ACLs. The option also implies '
                '--perms.',
                '',
                'The source and destination systems must have compatible ACL '
                'entries for this option to work properly. See the '
                '--fake-super option for a way to backup and restore ACLs '
                'that are not compatible.'
            ]
        )
        layout.addWidget(self.cbPreserveAcl)

        self.cbPreserveXattr = QCheckBox(
            _('Preserve extended attributes (xattr)'), self)
        qttools.set_wrapped_tooltip(
            self.cbPreserveXattr,
            [
                "Uses 'rsync -X'. From 'man rsync':",
                'This option causes rsync to update the destination extended '
                'attributes to be the same as the source ones.',
                '',
                'For systems that support extended-attribute namespaces, a '
                'copy being done by a super-user copies all namespaces '
                'except system.*. A normal user only copies the user.* '
                'namespace. To be able to backup and restore non-user '
                'namespaces as a normal user, see the --fake-super option.',
                '',
                'Note that this option does not copy rsyncs special xattr '
                'values (e.g. those used by --fake-super) unless you repeat '
                'the option (e.g. -XX). This "copy all xattrs" mode cannot be '
                'used with --fake-super.'
            ]
        )
        layout.addWidget(self.cbPreserveXattr)

        self.cbCopyUnsafeLinks = QCheckBox(
            _('Copy unsafe links (works only with absolute links)'), self)
        qttools.set_wrapped_tooltip(
            self.cbCopyUnsafeLinks,
            [
                "Uses 'rsync --copy-unsafe-links'. From 'man rsync':",
                'This tells rsync to copy the referent of symbolic links that '
                'point outside the copied tree. Absolute symlinks are also '
                'treated like ordinary files, and so are any symlinks in the '
                'source path itself when --relative is used. This option has '
                'no additional effect if --copy-links was also specified.'
            ]
        )
        layout.addWidget(self.cbCopyUnsafeLinks)

        self.cbCopyLinks = QCheckBox(
            _('Copy links (dereference symbolic links)'), self)
        qttools.set_wrapped_tooltip(
            self.cbCopyLinks,
            [
                "Uses 'rsync --copy-links'. From 'man rsync':",
                'When symlinks are encountered, the item that they point to '
                '(the referent) is copied, rather than the symlink. In older '
                'versions of rsync, this option also had the side-effect of '
                'telling the receiving side to follow symlinks, such as '
                'symlinks to directories. In a modern rsync such as this one,'
                ' you will need to specify --keep-dirlinks (-K) to get this '
                'extra behavior. The only exception is when sending files to '
                'an rsync that is too old to understand -K -- in that case, '
                'the -L option will still have the side-effect of -K on that '
                'older receiving rsync.'
            ]
        )
        layout.addWidget(self.cbCopyLinks)

        # one file system option
        self.cbOneFileSystem = QCheckBox(
            _('Restrict to one file system'), self)
        qttools.set_wrapped_tooltip(
            self.cbOneFileSystem,
            [
                "Uses 'rsync --one-file-system'. From 'man rsync':",
                'This tells rsync to avoid crossing a filesystem boundary '
                'when recursing. This does not limit the user\'s ability '
                'to specify items to copy from multiple filesystems, just '
                'rsync\'s recursion through the hierarchy of each directory '
                'that the user specified, and also the analogous recursion '
                'on the receiving side during deletion. Also keep in mind '
                'that rsync treats a "bind" mount to the same device as '
                'being on the same filesystem.'
            ]
        )
        layout.addWidget(self.cbOneFileSystem)

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
        self.txtRsyncOptions.editingFinished.connect(
            self._slot_rsync_options_editing_finished)
        self.txtRsyncOptions.setToolTip(tooltip)
        hlayout.addWidget(self.txtRsyncOptions)

        enabled = lambda state: self.txtRsyncOptions.setEnabled(state)
        enabled(False)
        self.cbRsyncOptions.stateChanged.connect(enabled)

        # ssh prefix
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        self.cbSshPrefix = QCheckBox(_('Add prefix to SSH commands'), self)
        tooltip = [
            _('Prefix to run before every command on remote host.'),
            _("Variables need to be escaped with \\$FOO. This doesn't touch "
              'rsync. So to add a prefix for rsync use "{example_value}" with '
              '{rsync_options_value}.').format(
                  example_value=self.cbRsyncOptions.text(),
                  rsync_options_value \
                      ='--rsync-path="FOO=bar:\\$FOO /usr/bin/rsync"'),
            '',
            '{default}: {def_value}'.format(
                default=_('default'),
                def_value=self.config.DEFAULT_SSH_PREFIX)
        ]
        qttools.set_wrapped_tooltip(self.cbSshPrefix, tooltip)
        hlayout.addWidget(self.cbSshPrefix)
        self.txtSshPrefix = QLineEdit(self)
        qttools.set_wrapped_tooltip(self.txtSshPrefix, tooltip)
        hlayout.addWidget(self.txtSshPrefix)

        enabled = lambda state: self.txtSshPrefix.setEnabled(state)
        enabled(False)
        self.cbSshPrefix.stateChanged.connect(enabled)

        qttools.equalIndent(self.cbRsyncOptions, self.cbSshPrefix)

        self.cbSshCheckPing = QCheckBox(_('Check if remote host is online'))
        qttools.set_wrapped_tooltip(
            self.cbSshCheckPing,
            _('Warning: If disabled and the remote host is not available, '
              'this could lead to some weird errors.')
        )
        self.cbSshCheckCommands = QCheckBox(
            _('Check if remote host supports all necessary commands.'))
        qttools.set_wrapped_tooltip(
            self.cbSshCheckCommands,
            _('Warning: If disabled and the remote host does not support all '
              'necessary commands, this could lead to some weird errors.')
        )
        layout.addWidget(self.cbSshCheckPing)
        layout.addWidget(self.cbSshCheckCommands)

        #
        layout.addStretch()
        scrollArea.setWidget(layoutWidget)
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

    def _slot_rsync_options_editing_finished(self):
        """When editing the rsync options is finished warn and remove
        --old-args option if present.
        """
        txt = self.txtRsyncOptions.text()

        if '--old-args' in txt:
            # No translation for this message because it is a rare case.
            messagebox.warning(
                text='Found rsync flag "--old-args". That flag will be removed'
                ' from the options because it conflicts with the flag "-s" '
                '(also known as "--secluded-args" or "--protected-args") which'
                ' is used by Back In Time to force the "new form of argument '
                'protection" in rsync.',
                widget_to_center_on=self
            )

            # Don't leave two-blank spaces between other arguments
            txt = txt.replace('--old-args ', '')
            txt = txt.replace(' --old-args', '')
            txt = txt.replace('--old-args', '')
            self.txtRsyncOptions.setText(txt)

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

        qttools.update_combo_profiles(self.config, self.comboProfiles, current_profile_id)

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
        self.cbOneFileSystem.setChecked(self.config.oneFileSystem())
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
        """Store all settings from the dialog in the configuration object and
        additionally does some testing of the settings.

        Dev note (buhtz, 2024-10): The order of taking and storing the settings
        in this method is very important. Shouldn't be modified without knowing
        the consequences. It is known that the current state is not optimal and
        should be modified in a refactoring session.
        """

        # Workaround: We need to know the mode first. But all other settings in
        # the "Generals" tab need to be stored as last. See the end of this
        # method.
        mode = self._tab_general.get_active_snapshots_mode()
        self.config.setSnapshotsMode(mode)

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
        self.config.setOneFileSystem(self.cbOneFileSystem.isChecked())
        self.config.setRsyncOptions(self.cbRsyncOptions.isChecked(),
                                    self.txtRsyncOptions.text())
        self.config.setSshPrefix(self.cbSshPrefix.isChecked(),
                                 self.txtSshPrefix.text())
        self.config.setSshCheckPingHost(self.cbSshCheckPing.isChecked())
        self.config.setSshCheckCommands(self.cbSshCheckCommands.isChecked())

        # Dev note: The method need to be the last. Some validation and testing
        # happens in there. These tests depends on the settings in all other
        # tabs. So they need to be stored first.
        return self._tab_general.store_values()

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

        self.cbNiceOnRemote.setEnabled(enabled)
        self.cbIoniceOnRemote.setEnabled(enabled)
        self.cbNocacheOnRemote.setEnabled(enabled)
        self.cbSmartRemoveRunRemoteInBackground.setVisible(enabled)
        self.cbSshPrefix.setVisible(enabled)
        self.txtSshPrefix.setVisible(enabled)
        self.cbSshCheckPing.setVisible(enabled)
        self.cbSshCheckCommands.setVisible(enabled)

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

    def printDefault(self, value):
        return ' ' + _('(default: {})').format(
            _('enabled') if value else _('disabled'))

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
