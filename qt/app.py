# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys

if not os.getenv('DISPLAY', ''):
    os.putenv('DISPLAY', ':0.0')

import pathlib
import re
import subprocess
import shutil
import signal
from contextlib import contextmanager
from tempfile import TemporaryDirectory

# We need to import common/tools.py
import qttools_path
qttools_path.registerBackintimePath('common')

# Workaround until the codebase is rectified/equalized.
import tools
tools.initiate_translation(None)

import qttools

import backintime
import tools
import logger
import snapshots
import guiapplicationinstance
import mount
import progress
import encfsmsgbox
from exceptions import MountException

from PyQt6.QtGui import (QAction,
                         QShortcut,
                         QDesktopServices,
                         QPalette,
                         QIcon,
                         QFileSystemModel)
from PyQt6.QtWidgets import (QWidget,
                             QFrame,
                             QMainWindow,
                             QToolButton,
                             QLabel,
                             QLineEdit,
                             QCheckBox,
                             QListWidget,
                             QTreeView,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QAbstractItemView,
                             QStyledItemDelegate,
                             QVBoxLayout,
                             QStackedLayout,
                             QSplitter,
                             QGroupBox,
                             QMenu,
                             QToolBar,
                             QProgressBar,
                             QMessageBox,
                             QInputDialog,
                             QDialog,
                             QApplication,
                             )
from PyQt6.QtCore import (Qt,
                          QObject,
                          QPoint,
                          pyqtSlot,
                          pyqtSignal,
                          QTimer,
                          QThread,
                          QEvent,
                          QSortFilterProxyModel,
                          QDir,
                          QUrl)
from manageprofiles import SettingsDialog
import snapshotsdialog
import logviewdialog
from restoredialog import RestoreDialog
from restoreconfigdialog import RestoreConfigDialog
import languagedialog
import messagebox
from aboutdlg import AboutDlg
import qttools
from usermessagedialog import UserMessageDialog
import version


class MainWindow(QMainWindow):
    def __init__(self, config, appInstance, qapp):
        QMainWindow.__init__(self)

        self.config = config
        self.appInstance = appInstance
        self.qapp = qapp
        self.snapshots = snapshots.Snapshots(config)

        self.lastTakeSnapshotMessage = None
        self.tmpDirs = []
        self.firstUpdateAll = True
        self.disableProfileChanged = False

        # "Magic" object handling shutdown procedure in different desktop
        # environments.
        self.shutdown = tools.ShutDown()

        # Import on module level not possible because of Qt restrictions.
        import icon
        globals()['icon'] = icon

        # window icon
        self.qapp.setWindowIcon(icon.BIT_LOGO)

        # shortcuts without buttons
        self._create_shortcuts_without_actions()

        self._create_actions()
        self._create_menubar()
        self._create_main_toolbar()

        # timeline (left widget)
        self.timeLine = qttools.TimeLine(self)
        self.timeLine.updateFilesView.connect(self.updateFilesView)

        # right widget
        self.filesWidget = QGroupBox(self)
        filesLayout = QVBoxLayout(self.filesWidget)
        left, top, right, bottom = filesLayout.getContentsMargins()
        filesLayout.setContentsMargins(0, 0, right, 0)

        # main splitter
        self.mainSplitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.mainSplitter.addWidget(self.timeLine)
        self.mainSplitter.addWidget(self.filesWidget)

        # FilesView toolbar
        self.toolbar_filesview = self._create_and_get_filesview_toolbar()
        filesLayout.addWidget(self.toolbar_filesview)

        # mouse button navigation
        self.mouseButtonEventFilter = ExtraMouseButtonEventFilter(self)
        self.setMouseButtonNavigation()

        # second splitter:
        # part of files-layout
        self.secondSplitter = QSplitter(self)
        self.secondSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.secondSplitter.setContentsMargins(0, 0, 0, 0)
        filesLayout.addWidget(self.secondSplitter)

        # places
        self.places = QTreeWidget(self)
        self.places.setRootIsDecorated(False)
        self.places.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.places.setHeaderLabel(_('Shortcuts'))
        self.places.header().setSectionsClickable(True)
        self.places.header().setSortIndicatorShown(True)
        self.places.header().setSectionHidden(1, True)
        self.places.header().setSortIndicator(
            int(self.config.profileIntValue('qt.places.SortColumn', 1)),
            Qt.SortOrder(self.config.profileIntValue(
                'qt.places.SortOrder', Qt.SortOrder.AscendingOrder))
        )
        self.placesSortLoop = {self.config.currentProfile(): False}
        self.secondSplitter.addWidget(self.places)
        self.places.header().sortIndicatorChanged.connect(self.sortPlaces)

        # files view stacked layout
        widget = QWidget(self)
        self.stackFilesView = QStackedLayout(widget)
        self.secondSplitter.addWidget(widget)

        # folder don't exist label
        self.lblFolderDontExists = QLabel(
            _("This directory doesn't exist\n"
              "in the current selected snapshot."),
            self)
        qttools.setFontBold(self.lblFolderDontExists)
        self.lblFolderDontExists.setFrameShadow(QFrame.Shadow.Sunken)
        self.lblFolderDontExists.setFrameShape(QFrame.Shape.Panel)
        self.lblFolderDontExists.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.stackFilesView.addWidget(self.lblFolderDontExists)

        # list files view
        self.filesView = QTreeView(self)
        self.stackFilesView.addWidget(self.filesView)
        self.filesView.setRootIsDecorated(False)
        self.filesView.setAlternatingRowColors(True)
        self.filesView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.filesView.setItemsExpandable(False)
        self.filesView.setDragEnabled(False)
        self.filesView.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.filesView.header().setSectionsClickable(True)
        self.filesView.header().setSectionsMovable(False)
        self.filesView.header().setSortIndicatorShown(True)

        self.filesViewModel = QFileSystemModel(self)
        self.filesViewModel.setRootPath(QDir().rootPath())
        self.filesViewModel.setReadOnly(True)
        self.filesViewModel.setFilter(QDir.Filter.AllDirs |
                                      QDir.Filter.AllEntries |
                                      QDir.Filter.NoDotAndDotDot |
                                      QDir.Filter.Hidden)

        self.filesViewProxyModel = QSortFilterProxyModel(self)
        self.filesViewProxyModel.setDynamicSortFilter(True)
        self.filesViewProxyModel.setSourceModel(self.filesViewModel)

        self.filesView.setModel(self.filesViewProxyModel)

        self.filesViewDelegate = QStyledItemDelegate(self)
        self.filesView.setItemDelegate(self.filesViewDelegate)

        sortColumn = self.config.intValue(
            'qt.main_window.files_view.sort.column', 0)
        sortOrder = self.config.boolValue(
            'qt.main_window.files_view.sort.ascending', True)
        sortOrder = Qt.SortOrder.AscendingOrder if sortOrder else Qt.SortOrder.DescendingOrder

        self.filesView.header().setSortIndicator(sortColumn, sortOrder)
        self.filesViewModel.sort(
            self.filesView.header().sortIndicatorSection(),
            self.filesView.header().sortIndicatorOrder())
        self.filesView.header() \
                      .sortIndicatorChanged.connect(self.filesViewModel.sort)

        self.stackFilesView.setCurrentWidget(self.filesView)

        #
        self.setCentralWidget(self.mainSplitter)

        # context menu for Files View
        self.filesView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.filesView.customContextMenuRequested \
                      .connect(self.contextMenuClicked)
        self.contextMenu = QMenu(self)
        self.contextMenu.addAction(self.act_restore)
        self.contextMenu.addAction(self.act_restore_to)
        self.contextMenu.addAction(self.act_snapshots_dialog)
        self.contextMenu.addSeparator()
        self.btnAddInclude = self.contextMenu.addAction(
            icon.ADD, _('Add to Include'))
        self.btnAddExclude = self.contextMenu.addAction(
            icon.ADD, _('Add to Exclude'))
        self.btnAddInclude.triggered.connect(self.btnAddIncludeClicked)
        self.btnAddExclude.triggered.connect(self.btnAddExcludeClicked)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction(self.act_show_hidden)

        # ProgressBar
        layoutWidget = QWidget()
        layout = QVBoxLayout(layoutWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layoutWidget.setContentsMargins(0, 0, 0, 0)
        layoutWidget.setLayout(layout)
        self.progressBar = QProgressBar(self)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setContentsMargins(0, 0, 0, 0)
        self.progressBar.setFixedHeight(5)
        self.progressBar.setVisible(False)

        self.progressBarDummy = QWidget()
        self.progressBarDummy.setContentsMargins(0, 0, 0, 0)
        self.progressBarDummy.setFixedHeight(5)

        self.status = QLabel(self)
        self.status.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.status)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.progressBarDummy)

        self.statusBar().addWidget(layoutWidget, 100)
        self.status.setText(_('Done'))

        self.snapshotsList = []
        self.sid = snapshots.RootSnapshot(self.config)
        self.path = self.config.profileStrValue(
            'qt.last_path',
            self.config.strValue('qt.last_path', '/')
        )
        self.widget_current_path.setText(self.path)
        self.path_history = tools.PathHistory(self.path)

        # restore size and position
        x = self.config.intValue('qt.main_window.x', -1)
        y = self.config.intValue('qt.main_window.y', -1)
        if x >= 0 and y >= 0:
            self.move(x, y)

        w = self.config.intValue('qt.main_window.width', 800)
        h = self.config.intValue('qt.main_window.height', 500)
        self.resize(w, h)

        mainSplitterLeftWidth = self.config.intValue(
            'qt.main_window.main_splitter_left_w', 150)
        mainSplitterRightWidth = self.config.intValue(
            'qt.main_window.main_splitter_right_w', 450)
        sizes = [mainSplitterLeftWidth, mainSplitterRightWidth]
        self.mainSplitter.setSizes(sizes)

        secondSplitterLeftWidth = self.config.intValue(
            'qt.main_window.second_splitter_left_w', 150)
        secondSplitterRightWidth = self.config.intValue(
            'qt.main_window.second_splitter_right_w', 300)
        sizes = [secondSplitterLeftWidth, secondSplitterRightWidth]
        self.secondSplitter.setSizes(sizes)

        filesViewColumnNameWidth = self.config.intValue(
            'qt.main_window.files_view.name_width', -1)
        filesViewColumnSizeWidth = self.config.intValue(
            'qt.main_window.files_view.size_width', -1)
        filesViewColumnDateWidth = self.config.intValue(
            'qt.main_window.files_view.date_width', -1)

        if (filesViewColumnNameWidth > 0
                and filesViewColumnSizeWidth > 0
                and filesViewColumnDateWidth > 0):
            self.filesView.header().resizeSection(0, filesViewColumnNameWidth)
            self.filesView.header().resizeSection(1, filesViewColumnSizeWidth)
            self.filesView.header().resizeSection(2, filesViewColumnDateWidth)

        # Force dialog to import old configuration
        if not config.isConfigured():
            message = _(
                '{app_name} appears to be running for the first time as no '
                'configuration is found.'
            ).format(app_name=self.config.APP_NAME)
            message = f'{message}\n\n'
            message = message + _(
                'Import an existing configuration (from a backup target '
                'directory or another computer)?')
            answer = messagebox.warningYesNo(self, message)
            if answer == QMessageBox.StandardButton.Yes:
                RestoreConfigDialog(self).exec()

            SettingsDialog(self).exec()

        if not config.isConfigured():
            return

        profile_id = config.currentProfile()

        # mount
        try:
            mnt = mount.Mount(cfg=self.config,
                              profile_id=profile_id,
                              parent=self)
            hash_id = mnt.mount()

        except MountException as ex:
            messagebox.critical(self, str(ex))

        else:
            self.config.setCurrentHashId(hash_id)

        if not config.canBackup(profile_id):
            msg = _("Can't find snapshots directory.") + '\n' \
                + _('If it is on a removable drive please plug it in and then '
                    'press OK.')
            messagebox.critical(self, msg)

        self.filesViewProxyModel.layoutChanged.connect(self.dirListerCompleted)

        # populate lists
        self.updateProfiles()
        self.comboProfiles.currentIndexChanged \
                          .connect(self.comboProfileChanged)

        self.filesView.setFocus()

        self.updateSnapshotActions()

        # signals
        self.timeLine.itemSelectionChanged.connect(self.timeLineChanged)
        self.places.currentItemChanged.connect(self.placesChanged)
        self.filesView.activated.connect(self.filesViewItemActivated)

        self.forceWaitLockCounter = 0

        self.timerRaiseApplication = QTimer(self)
        self.timerRaiseApplication.setInterval(1000)
        self.timerRaiseApplication.setSingleShot(False)
        self.timerRaiseApplication.timeout.connect(self.raiseApplication)
        self.timerRaiseApplication.start()

        self.timerUpdateTakeSnapshot = QTimer(self)
        self.timerUpdateTakeSnapshot.setInterval(1000)
        self.timerUpdateTakeSnapshot.setSingleShot(False)
        self.timerUpdateTakeSnapshot.timeout.connect(self.updateTakeSnapshot)
        self.timerUpdateTakeSnapshot.start()

        SetupCron(self).start()

        # Finished countdown of manual GUI starts
        if 0 == self.config.manual_starts_countdown():

            # Do nothing if English is the current used language
            if self.config.language_used != 'en':

                # Show the message only if the current used language is
                # translated equal or less then 97%
                self._open_approach_translator_dialog(cutoff=97)

        # BIT counts down how often the GUI was started. Until the end of that
        # countdown a dialog with a text about contributing to translating
        # BIT is presented to the users.
        self.config.decrement_manual_starts_countdown()

        # If the encfs-deprecation warning was never shown before
        if self.config.boolValue('internal.msg_shown_encfs') == False:

            # Are there profiles using EncFS?
            encfs_profiles = []
            for pid in self.config.profiles():
                if 'encfs' in self.config.snapshotsMode(pid):
                    encfs_profiles.append(
                        f'{self.config.profileName(pid)} ({pid})')

            # EncFS deprecation warning (#1734, #1735)
            if encfs_profiles:
                dlg = encfsmsgbox.EncfsExistsWarning(self, encfs_profiles)
                dlg.exec()
                self.config.setBoolValue('internal.msg_shown_encfs', True)

        # Release Candidate
        if version.is_release_candidate():
            last_vers = self.config.strValue('internal.msg_rc')
            if last_vers != version.__version__:
                self.config.setStrValue('internal.msg_rc', version.__version__)
                self._open_release_candidate_dialog()

    @property
    def showHiddenFiles(self):
        return self.config.boolValue('qt.show_hidden_files', False)

    # TODO The qt.show_hidden_files key should be a constant instead of a duplicated string
    @showHiddenFiles.setter
    def showHiddenFiles(self, value):
        self.config.setBoolValue('qt.show_hidden_files', value)

    def _create_actions(self):
        """Create all action objects used by this main window.

        All actions are stored as instance attributes to ``self`` and their
        names begin with ``act_``. The actions can be added to GUI elements
        (menu entries, buttons) in later steps.

        Note:
            All actions used in the main window and its child widgets should
            be created in this function.

        Note:
            Shortcuts need to be strings in a list even if it is only one
            entry. It is done this way to spare one ``if...else`` statement
            deciding between `QAction.setShortcuts()` and
            `QAction.setShortcut()` (singular; without ``s`` at the end).
        """

        action_dict = {
            # because of "icon"
            # pylint: disable=undefined-variable

            # 'Name of action attribute in "self"': (
            #     ICON, Label text,
            #     trigger_handler_function,
            #     keyboard shortcuts (type list[str])
            #     tooltip
            # ),
            'act_take_snapshot': (
                icon.TAKE_SNAPSHOT, _('Take a snapshot'),
                self.btnTakeSnapshotClicked, ['Ctrl+S'],
                _('Use modification time & size for file change detection.')),

            'act_take_snapshot_checksum': (
                icon.TAKE_SNAPSHOT, _('Take a snapshot (checksum mode)'),
                self.btnTakeSnapshotChecksumClicked, ['Ctrl+Shift+S'],
                _('Use checksums for file change detection.')),

            'act_pause_take_snapshot': (
                icon.PAUSE, _('Pause snapshot process'),
                lambda: os.kill(self.snapshots.pid(), signal.SIGSTOP), None,
                None),

            'act_resume_take_snapshot': (
                icon.RESUME, _('Resume snapshot process'),
                lambda: os.kill(self.snapshots.pid(), signal.SIGCONT), None,
                None),
            'act_stop_take_snapshot': (
                icon.STOP, _('Stop snapshot process'),
                self.btnStopTakeSnapshotClicked, None,
                None),
            'act_update_snapshots': (
                icon.REFRESH_SNAPSHOT, _('Refresh snapshot list'),
                self.btnUpdateSnapshotsClicked, ['F5', 'Ctrl+R'],
                None),
            'act_name_snapshot': (
                icon.SNAPSHOT_NAME, _('Name snapshot'),
                self.btnNameSnapshotClicked, ['F2'],
                None),
            'act_remove_snapshot': (
                icon.REMOVE_SNAPSHOT, _('Remove snapshot'),
                self.btnRemoveSnapshotClicked, ['Delete'],
                None),
            'act_snapshot_logview': (
                icon.VIEW_SNAPSHOT_LOG, _('View snapshot log'),
                self.btnSnapshotLogViewClicked, None,
                None),
            'act_last_logview': (
                icon.VIEW_LAST_LOG, _('View last log'),
                self.btnLastLogViewClicked, None,
                None),
            'act_settings': (
                icon.SETTINGS, _('Manage profiles…'),
                self.btnSettingsClicked, ['Ctrl+Shift+P'],
                None),
            'act_shutdown': (
                icon.SHUTDOWN, _('Shutdown'),
                None, None,
                _('Shut down system after snapshot has finished.')),
            'act_setup_language': (
                icon.LANGUAGE, _('Setup language…'),
                self.slot_setup_language, None,
                None),
            'act_quit': (
                icon.EXIT, _('Exit'),
                self.close, ['Ctrl+Q'],
                None),
            'act_help_help': (
                icon.HELP, _('Help'),
                self.btnHelpClicked, ['F1'],
                None),
            'act_help_configfile': (
                icon.HELP, _('Profiles config file'),
                self.btnHelpConfigClicked, None, None),
            'act_help_website': (
                icon.WEBSITE, _('Website'),
                self.btnWebsiteClicked, None, None),
            'act_help_changelog': (
                icon.CHANGELOG, _('Changelog'),
                self.btnChangelogClicked, None, None),
            'act_help_faq': (
                icon.FAQ, _('FAQ'),
                self.btnFaqClicked, None, None),
            'act_help_question': (
                icon.QUESTION, _('Ask a question'),
                self.btnAskQuestionClicked, None, None),
            'act_help_bugreport': (
                icon.BUG, _('Report a bug'),
                self.btnReportBugClicked, None, None),
            'act_help_translation': (
                icon.LANGUAGE, _('Translation'),
                self.slot_help_translation, None,
                _('Shows the message about participation '
                  'in translation again.')),
            'act_help_encryption': (
                icon.ENCRYPT,
                _('Encryption Transition (EncFS)'),
                self.slot_help_encryption, None,
                _('Shows the message about EncFS removal again.')),
            'act_help_about': (
                icon.ABOUT, _('About'),
                self.btnAboutClicked, None, None),
            'act_restore': (
                icon.RESTORE, _('Restore'),
                self.restoreThis, None,
                _('Restore the selected files or directories to the '
                  'original destination.')),
            'act_restore_to': (
                icon.RESTORE_TO, _('Restore to …'),
                self.restoreThisTo, None,
                _('Restore the selected files or directories to a '
                  'new destination.')),
            'act_restore_parent': (
                icon.RESTORE,
                None,  # text label is set elsewhere
                self.restoreParent, None,
                _('Restore the currently shown directory and all its contents '
                  'to the original destination.')),
            'act_restore_parent_to': (
                icon.RESTORE_TO,
                None,  # text label is set elsewhere
                self.restoreParentTo, None,
                _('Restore the currently shown directory and all its contents '
                  'to a new destination.')),
            'act_folder_up': (
                icon.UP, _('Up'),
                self.btnFolderUpClicked, ['Alt+Up', 'Backspace'], None),
            'act_show_hidden': (
                icon.SHOW_HIDDEN, _('Show hidden files'),
                None, ['Ctrl+H'], None),
            'act_snapshots_dialog': (
                icon.SNAPSHOTS, _('Compare snapshots…'),
                self.btnSnapshotsClicked, None, None),
        }

        for attr in action_dict:
            ico, txt, slot, keys, tip = action_dict[attr]

            # Create action (with icon)
            action = QAction(ico, txt, self) if ico else \
                QAction(txt, self)

            # Connect handler function
            if slot:
                action.triggered.connect(slot)

            # Add keyboardshortcuts
            if keys:
                action.setShortcuts(keys)

            # Tooltip
            if tip:
                action.setToolTip(tip)

            # populate the action to "self"
            setattr(self, attr, action)

        # Release Candidate ?
        self.act_help_release_candidate = None
        if version.is_release_candidate():
            # pylint: disable=undefined-variable
            action = QAction(icon.QUESTION, _('Release Candidate'), self)
            action.triggered.connect(self.slot_help_release_candidate)
            action.setToolTip(
                _('Shows the message about this Release Candidate again.'))
            self.act_help_release_candidate = action

        # Fine tuning
        self.act_shutdown.toggled.connect(self.btnShutdownToggled)
        self.act_shutdown.setCheckable(True)
        self.act_shutdown.setEnabled(self.shutdown.canShutdown())
        self.act_pause_take_snapshot.setVisible(False)
        self.act_resume_take_snapshot.setVisible(False)
        self.act_stop_take_snapshot.setVisible(False)
        self.act_show_hidden.setCheckable(True)
        self.act_show_hidden.setChecked(self.showHiddenFiles)
        self.act_show_hidden.toggled.connect(self.btnShowHiddenFilesToggled)

    def _create_shortcuts_without_actions(self):
        """Create shortcuts that are not related to a visual element in the
        GUI and don't have an QAction instance because of that.
        """

        shortcut_list = (
            ('Alt+Left', self.btnFolderHistoryPreviousClicked),
            ('Alt+Right', self.btnFolderHistoryNextClicked),
            ('Alt+Down', self.btnOpenCurrentItemClicked),
        )

        for keys, slot in shortcut_list:
            shortcut = QShortcut(keys, self)
            shortcut.activated.connect(slot)

    def _create_menubar(self):
        """Create the menubar and connect it to actions."""

        menu_dict = {
            # The application name itself shouldn't be translated but the
            # shortcut indicator (marked with &) should be translated and
            # decided by the translator.
            _('Back In &Time'): (
                self.act_setup_language,
                self.act_shutdown,
                self.act_quit,
            ),
            _('&Backup'): (
                self.act_take_snapshot,
                self.act_take_snapshot_checksum,
                self.act_settings,
                self.act_snapshots_dialog,
                self.act_name_snapshot,
                self.act_remove_snapshot,
                self.act_snapshot_logview,
                self.act_last_logview,
                self.act_update_snapshots,
            ),
            _('&Restore'): (
                self.act_restore,
                self.act_restore_to,
                self.act_restore_parent,
                self.act_restore_parent_to,
            ),
            _('&Help'): (
                self.act_help_help,
                self.act_help_configfile,
                self.act_help_website,
                self.act_help_changelog,
                self.act_help_faq,
                self.act_help_question,
                self.act_help_bugreport,
                self.act_help_translation,
                self.act_help_encryption,
                self.act_help_about,
            )
        }

        for key in menu_dict:
            menu = self.menuBar().addMenu(key)
            menu.addActions(menu_dict[key])
            menu.setToolTipsVisible(True)

        # The action of the restore menu. It is used by the menuBar and by the
        # files toolbar.
        # It is populated to "self" because it's state to be altered.
        # See "self._enable_restore_ui_elements()" for details.
        self.act_restore_menu = self.menuBar().actions()[2]

        # fine tuning.
        # Attention: Take care of the actions() index here when modifying the
        # main menu!
        backup = self.menuBar().actions()[1].menu()
        backup.insertSeparator(self.act_settings)
        backup.insertSeparator(self.act_snapshot_logview)
        help = self.menuBar().actions()[-1].menu()
        help.insertSeparator(self.act_help_website)
        help.insertSeparator(self.act_help_about)
        if self.act_help_release_candidate:
            help.addSeparator()
            help.addAction(self.act_help_release_candidate)
        restore = self.act_restore_menu.menu()
        restore.insertSeparator(self.act_restore_parent)
        restore.setToolTipsVisible(True)

    def _create_main_toolbar(self):
        """Create the main toolbar and connect it to actions."""

        toolbar = self.addToolBar('main')
        toolbar.setFloatable(False)

        # Drop-Down: Profiles
        self.comboProfiles = qttools.ProfileCombo(self)
        self.comboProfilesAction = toolbar.addWidget(self.comboProfiles)

        actions_for_toolbar = [
            self.act_take_snapshot,
            self.act_pause_take_snapshot,
            self.act_resume_take_snapshot,
            self.act_stop_take_snapshot,
            self.act_update_snapshots,
            self.act_name_snapshot,
            self.act_remove_snapshot,
            self.act_snapshot_logview,
            self.act_last_logview,
            self.act_settings,
            self.act_shutdown,
        ]

        # Add each action to toolbar
        for act in actions_for_toolbar:
            toolbar.addAction(act)

            # Assume an explicit tooltip if it is different from "text()".
            # Note that Qt use "text()" as "toolTip()" by default.
            if act.toolTip() != act.text():

                if QApplication.instance().isRightToLeft():
                    # RTL/BIDI language like Hebrew
                    button_tip = f'{act.toolTip()} :{act.text()}'
                else:
                    # (default) LTR language (e.g. English)
                    button_tip = f'{act.text()}: {act.toolTip()}'

                toolbar.widgetForAction(act).setToolTip(button_tip)

        # toolbar sub menu: take snapshot
        submenu_take_snapshot = QMenu(self)
        submenu_take_snapshot.addAction(self.act_take_snapshot)
        submenu_take_snapshot.addAction(self.act_take_snapshot_checksum)
        submenu_take_snapshot.setToolTipsVisible(True)

        # get the toolbar buttons widget...
        button_take_snapshot = toolbar.widgetForAction(self.act_take_snapshot)
        # ...and add the menu to it
        button_take_snapshot.setMenu(submenu_take_snapshot)
        button_take_snapshot.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        # separators and stretchers
        toolbar.insertSeparator(self.act_settings)
        toolbar.insertSeparator(self.act_shutdown)

    def _create_and_get_filesview_toolbar(self):
        """Create the filesview toolbar object, connect it to actions and
        return it for later use.

        Returns:
            The toolbar object."""

        toolbar = QToolBar(self)
        toolbar.setFloatable(False)

        actions_for_toolbar = [
            self.act_folder_up,
            self.act_show_hidden,
            self.act_restore,
            self.act_snapshots_dialog,
        ]

        toolbar.addActions(actions_for_toolbar)

        # LineEdit widget to display the current path
        self.widget_current_path = QLineEdit(self)
        self.widget_current_path.setReadOnly(True)
        toolbar.insertWidget(self.act_show_hidden, self.widget_current_path)

        # Restore sub menu
        restore_sub_menu = self.act_restore_menu.menu()
        # get the toolbar buttons widget...
        button_restore = toolbar.widgetForAction(self.act_restore)
        # ...and add the menu to it
        button_restore.setMenu(restore_sub_menu)
        button_restore.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        # Fine tuning
        toolbar.insertSeparator(self.act_restore)

        return toolbar

    def closeEvent(self, event):
        if self.shutdown.askBeforeQuit():
            msg = _('If you close this window, Back In Time will not be able '
                    'to shut down your system when the snapshot is finished.')
            msg = msg + '\n'
            msg = msg + _('Do you really want to close it?')
            answer = messagebox.warningYesNo(self, msg)
            if answer != QMessageBox.StandardButton.Yes:
                return event.ignore()

        self.config.setStrValue('qt.last_path', self.path)
        self.config.setProfileStrValue('qt.last_path', self.path)

        self.config.setProfileIntValue(
            'qt.places.SortColumn',
            self.places.header().sortIndicatorSection())
        self.config.setProfileIntValue(
            'qt.places.SortOrder',
            self.places.header().sortIndicatorOrder())

        self.config.setIntValue('qt.main_window.x', self.x())
        self.config.setIntValue('qt.main_window.y', self.y())
        self.config.setIntValue('qt.main_window.width', self.width())
        self.config.setIntValue('qt.main_window.height', self.height())

        sizes = self.mainSplitter.sizes()
        self.config.setIntValue('qt.main_window.main_splitter_left_w', sizes[0])
        self.config.setIntValue('qt.main_window.main_splitter_right_w', sizes[1])

        sizes = self.secondSplitter.sizes()
        self.config.setIntValue('qt.main_window.second_splitter_left_w', sizes[0])
        self.config.setIntValue('qt.main_window.second_splitter_right_w', sizes[1])

        self.config.setIntValue('qt.main_window.files_view.name_width', self.filesView.header().sectionSize(0))
        self.config.setIntValue('qt.main_window.files_view.size_width', self.filesView.header().sectionSize(1))
        self.config.setIntValue('qt.main_window.files_view.date_width', self.filesView.header().sectionSize(2))

        self.config.setIntValue('qt.main_window.files_view.sort.column', self.filesView.header().sortIndicatorSection())
        self.config.setBoolValue('qt.main_window.files_view.sort.ascending', self.filesView.header().sortIndicatorOrder() == Qt.SortOrder.AscendingOrder)

        self.filesViewModel.deleteLater()

        #umount
        try:
            mnt = mount.Mount(cfg = self.config, parent = self)
            mnt.umount(self.config.current_hash_id)
        except MountException as ex:
            messagebox.critical(self, str(ex))

        self.config.save()

        # cleanup temporary local copies of files which were opened in GUI
        for d in self.tmpDirs:
            d.cleanup()

        event.accept()

    def updateProfiles(self):
        if self.disableProfileChanged:
            return

        self.disableProfileChanged = True

        self.comboProfiles.clear()

        qttools.update_combo_profiles(self.config, self.comboProfiles, self.config.currentProfile())
        profiles = self.config.profilesSortedByName()

        self.comboProfilesAction.setVisible(len(profiles) > 1)

        self.updateProfile()

        self.disableProfileChanged = False

    def updateProfile(self):
        self.updateTimeLine()
        self.updatePlaces()
        self.updateFilesView(0)

        # EncFS deprecation warning (see #1734)
        current_mode = self.config.snapshotsMode(self.config.currentProfile())
        if current_mode in ('local_encfs', 'ssh_encfs'):
            # Show the profile specific warning dialog only once per profile.
            if self.config.profileBoolValue('msg_shown_encfs') is False:
                self.config.setProfileBoolValue('msg_shown_encfs', True)
                dlg = encfsmsgbox.EncfsCreateWarning(self)
                dlg.exec()

    def comboProfileChanged(self, index):
        if self.disableProfileChanged:
            return

        profile_id = self.comboProfiles.currentProfileID()
        if not profile_id:
            return

        old_profile_id = self.config.currentProfile()

        if profile_id != old_profile_id:
            self.remount(profile_id, old_profile_id)
            self.config.setCurrentProfile(profile_id)

            self.config.setProfileIntValue(
                'qt.places.SortColumn',
                self.places.header().sortIndicatorSection(),
                old_profile_id)
            self.config.setProfileIntValue(
                'qt.places.SortOrder',
                self.places.header().sortIndicatorOrder(),
                old_profile_id)

            self.placesSortLoop[old_profile_id] = False
            self.places.header().setSortIndicator(
                int(self.config.profileIntValue(
                    'qt.places.SortColumn', 1, profile_id)),
                Qt.SortOrder(self.config.profileIntValue(
                    'qt.places.SortOrder',
                    Qt.SortOrder.AscendingOrder,
                    profile_id))
            )

            self.config.setProfileStrValue(
                'qt.last_path', self.path, old_profile_id)
            path = self.config.profileStrValue(
                'qt.last_path', self.path, profile_id)

            if not path == self.path:
                self.path = path
                self.path_history.reset(self.path)
                self.widget_current_path.setText(self.path)

            self.updateProfile()

    def remount(self, new_profile_id, old_profile_id):
        try:
            mnt = mount.Mount(cfg = self.config, profile_id = old_profile_id, parent = self)
            hash_id = mnt.remount(new_profile_id)
        except MountException as ex:
            messagebox.critical(self, str(ex))
        else:
            self.config.setCurrentHashId(hash_id)

    def raiseApplication(self):
        raiseCmd = self.appInstance.raiseCommand()
        if raiseCmd is None:
            return

        logger.debug("Raise cmd: %s" %raiseCmd, self)
        self.qapp.alert(self)

    def updateTakeSnapshot(self, force_wait_lock=False):
        """Update the statusbar and progress indicator with latest message
        from the snapshot message file.

        This method is called via a timeout event. See
        `self.timerUpdateTakeSnapshot`. Also see
        `Snapshots.takeSnapshotMessage()` for further details.
        """
        if force_wait_lock:
            self.forceWaitLockCounter = 10

        busy = self.snapshots.busy()

        if busy:
            self.forceWaitLockCounter = 0
            paused = tools.processPaused(self.snapshots.pid())
        else:
            paused = False

        if self.forceWaitLockCounter > 0:
            self.forceWaitLockCounter = self.forceWaitLockCounter - 1

        fake_busy = busy or self.forceWaitLockCounter > 0

        message = _('Working:')
        takeSnapshotMessage = self.snapshots.takeSnapshotMessage()

        if fake_busy:
            if takeSnapshotMessage is None:
                takeSnapshotMessage = (0, '…')

        elif takeSnapshotMessage is None:
            takeSnapshotMessage = self.lastTakeSnapshotMessage
            if takeSnapshotMessage is None:
                takeSnapshotMessage = (0, _('Done'))

        force_update = False

        if fake_busy:  # What is this?
            if self.act_take_snapshot.isEnabled():
                self.act_take_snapshot.setEnabled(False)

            if not self.act_stop_take_snapshot.isVisible():
                for action in (self.act_pause_take_snapshot,
                            self.act_resume_take_snapshot,
                            self.act_stop_take_snapshot):
                    action.setEnabled(True)
            self.act_take_snapshot.setVisible(False)
            self.act_pause_take_snapshot.setVisible(not paused)
            self.act_resume_take_snapshot.setVisible(paused)
            self.act_stop_take_snapshot.setVisible(True)

        elif not self.act_take_snapshot.isEnabled():
            force_update = True

            self.act_take_snapshot.setEnabled(True)
            self.act_take_snapshot.setVisible(True)
            for action in (self.act_pause_take_snapshot,
                           self.act_resume_take_snapshot,
                           self.act_stop_take_snapshot):
                action.setVisible(False)

            # TODO: check if there is a more elegant way than always get a
            # new snapshot list which is very expensive (time)
            snapshotsList = snapshots.listSnapshots(self.config)

            if snapshotsList != self.snapshotsList:
                self.snapshotsList = snapshotsList
                self.updateTimeLine(False)
                takeSnapshotMessage = (0, _('Done'))
            else:
                if takeSnapshotMessage[0] == 0:
                    takeSnapshotMessage = (0, _('Done, no backup needed'))

            self.shutdown.shutdown()

        if takeSnapshotMessage != self.lastTakeSnapshotMessage or force_update:
            self.lastTakeSnapshotMessage = takeSnapshotMessage

            if fake_busy:
                message = '{}: {}'.format(
                    _('Working'),
                    self.lastTakeSnapshotMessage[1].replace('\n', ' ')
                )

            elif takeSnapshotMessage[0] == 0:
                message = self.lastTakeSnapshotMessage[1].replace('\n', ' ')

            else:
                message = '{}: {}'.format(
                    _('Error'),
                    self.lastTakeSnapshotMessage[1].replace('\n', ' ')
                )

            self.status.setText(message)

        pg = progress.ProgressFile(self.config)
        if pg.fileReadable():
            self.progressBar.setVisible(True)
            self.progressBarDummy.setVisible(False)
            pg.load()
            self.progressBar.setValue(pg.intValue('percent'))
            message = ' | '.join(self.getProgressBarFormat(pg, message))
            self.status.setText(message)
        else:
            self.progressBar.setVisible(False)
            self.progressBarDummy.setVisible(True)

        #if not fake_busy:
        #	self.lastTakeSnapshotMessage = None

    def getProgressBarFormat(self, pg, message):
        d = (
            ('sent', '{}:'.format(_('Sent'))),
            ('speed', '{}:'.format(_('Speed'))),
            ('eta', '{}:'.format(_('ETA')))
        )
        yield '{}%'.format(pg.intValue('percent'))

        for key, txt in d:
            value = pg.strValue(key, '')

            if not value:
                continue

            yield txt + ' ' + value

        yield message

    def placesChanged(self, item, previous):
        if item is None:
            return

        path = str(item.data(0, Qt.ItemDataRole.UserRole))
        if not path:
            return

        if path == self.path:
            return

        self.path = path
        self.path_history.append(path)
        self.updateFilesView(3)

    def addPlace(self, name, path, icon):
        """
        Dev note (buhtz, 2024-01-14): Parts of that code are redundant with
        qttools.py::HeaderItem.__init__().
        """
        item = QTreeWidgetItem()

        item.setText(0, name)

        if icon:
            item.setIcon(0, QIcon.fromTheme(icon))

        item.setData(0, Qt.ItemDataRole.UserRole, path)

        if not path:
            item.setFont(0, qttools.fontBold(item.font(0)))

            # item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(
                0, self.palette().color(QPalette.ColorRole.PlaceholderText))
            item.setBackground(
                0, self.palette().color(QPalette.ColorRole.Window))

        self.places.addTopLevelItem(item)

        if path == self.path:
            self.places.setCurrentItem(item)

        return item

    def updatePlaces(self):
        self.places.clear()
        self.addPlace(_('Global'), '', '')
        self.addPlace(_('Root'), '/', 'computer')
        self.addPlace(_('Home'), os.path.expanduser('~'), 'user-home')

        # "Now" or a specific snapshot selected?
        if self.sid.isRoot:
            # Use snapshots profiles list of include files and folders
            include_entries = self.config.include()

        else:
            # Determine folders from the snapshot itself
            base = os.path.expanduser('~')
            if not os.path.isdir(self.sid.pathBackup(base)):
                # Folder not mounted. We can skip for the next updatePlaces()
                return
            folders = [i.name for i in os.scandir(self.sid.pathBackup(base)) if i.is_dir()]
            include_entries = [(os.path.join(base, f), 0) for f in folders]

        # Use folders only (if 2nd tuple entry is 0)
        only_folders = filter(lambda entry: entry[1] == 0, include_entries)
        include_folders = [item[0] for item in only_folders]

        if not include_folders:
            return

        if not self.places.header().sortIndicatorSection():
            indic = self.places.header().sortIndicatorOrder()
            reverse = True if indic == Qt.SortOrder.DescendingOrder else False
            include_folders = sorted(include_folders, reverse=reverse)

        self.addPlace(_('Backup directories'), '', '')

        for folder in include_folders:
            self.addPlace(folder, folder, 'document-save')

    def sortPlaces(self, newColumn, newOrder, force = False):
        profile_id = self.config.currentProfile()

        if newColumn == 0 and newOrder == Qt.SortOrder.AscendingOrder:

            if profile_id in self.placesSortLoop and self.placesSortLoop[profile_id]:
                newColumn, newOrder = 1, Qt.SortOrder.AscendingOrder
                self.places.header().setSortIndicator(newColumn, newOrder)
                self.placesSortLoop[profile_id] = False

            else:
                self.placesSortLoop[profile_id] = True

        self.updatePlaces()

    def updateSnapshotActions(self, item = None):
        enabled = False

        if item is None:
            item = self.timeLine.currentItem()

        if not item is None:
            if not item.snapshotID().isRoot:
                enabled = True

        # update remove/name snapshot buttons
        self.act_name_snapshot.setEnabled(enabled)
        self.act_remove_snapshot.setEnabled(enabled)
        self.act_snapshot_logview.setEnabled(enabled)

    def timeLineChanged(self):
        item = self.timeLine.currentItem()
        self.updateSnapshotActions(item)

        if item is None:
            return

        sid = item.snapshotID()
        if not sid or sid == self.sid:
            return

        self.sid = sid
        self.updatePlaces()
        self.updateFilesView(2)

    def updateTimeLine(self, refreshSnapshotsList=True):
        self.timeLine.clear()
        self.timeLine.addRoot(snapshots.RootSnapshot(self.config))

        if refreshSnapshotsList:
            self.snapshotsList = []
            thread = FillTimeLineThread(self)
            thread.addSnapshot.connect(self.timeLine.addSnapshot)
            thread.finished.connect(self.timeLine.checkSelection)
            thread.start()

        else:
            for sid in self.snapshotsList:
                item = self.timeLine.addSnapshot(sid)
            self.timeLine.checkSelection()

    def btnTakeSnapshotClicked(self):
        backintime.takeSnapshotAsync(self.config)
        self.updateTakeSnapshot(True)

    def btnTakeSnapshotChecksumClicked(self):
        backintime.takeSnapshotAsync(self.config, checksum = True)
        self.updateTakeSnapshot(True)

    def btnStopTakeSnapshotClicked(self):
        os.kill(self.snapshots.pid(), signal.SIGKILL)
        self.act_stop_take_snapshot.setEnabled(False)
        self.act_pause_take_snapshot.setEnabled(False)
        self.act_resume_take_snapshot.setEnabled(False)
        self.snapshots.setTakeSnapshotMessage(0, 'Snapshot terminated')

    def btnUpdateSnapshotsClicked(self):
        self.updateTimeLine()
        self.updateFilesView(2)

    def btnNameSnapshotClicked(self):
        item = self.timeLine.currentItem()
        if item is None:
            return

        sid = item.snapshotID()
        if sid.isRoot:
            return

        name = sid.name

        new_name, accept = QInputDialog.getText(self, _('Snapshot Name'), '', text = name)
        if not accept:
            return

        new_name = new_name.strip()
        if name == new_name:
            return

        sid.name = new_name
        item.updateText()

    def btnLastLogViewClicked (self):
        with self.suspendMouseButtonNavigation():
            logviewdialog.LogViewDialog(self).show()  # no SID argument in constructor means "show last log"

    def btnSnapshotLogViewClicked (self):
        item = self.timeLine.currentItem()
        if item is None:
            return

        sid = item.snapshotID()
        if sid.isRoot:
            return

        with self.suspendMouseButtonNavigation():
            dlg = logviewdialog.LogViewDialog(self, sid)
            dlg.show()
            if sid != dlg.sid:
                self.timeLine.setCurrentSnapshotID(dlg.sid)

    def btnRemoveSnapshotClicked (self):
        def hideItem(item):
            try:
                item.setHidden(True)
            except RuntimeError:
                #item has been deleted
                #probably because user pressed refresh
                pass

        # try to use filter(..)
        items = [item for item in self.timeLine.selectedItems() if not isinstance(item, snapshots.RootSnapshot)]

        if not items:
            return

        question_msg = '{}\n{}'.format(
            ngettext(
                'Are you sure you want to remove this snapshot?',
                'Are you sure you want to remove these snapshots?',
                len(items)
            ),
            '\n'.join([item.snapshotID().displayName for item in items]))

        answer = messagebox.warningYesNo(self, question_msg)

        if answer != QMessageBox.StandardButton.Yes:
            return

        for item in items:

            item.setDisabled(True)

            if item is self.timeLine.currentItem():
                self.timeLine.selectRootItem()

        thread = RemoveSnapshotThread(self, items)
        thread.refreshSnapshotList.connect(self.updateTimeLine)
        thread.hideTimelineItem.connect(hideItem)
        thread.start()

    def btnSettingsClicked(self):
        with self.suspendMouseButtonNavigation():
            SettingsDialog(self).show()

    def btnShutdownToggled(self, checked):
        self.shutdown.activate_shutdown = checked

    def contextMenuClicked(self, point):
        self.contextMenu.exec(self.filesView.mapToGlobal(point))

    def btnAboutClicked(self):
        with self.suspendMouseButtonNavigation():
            dlg = AboutDlg(self)
            dlg.exec()

    def btnHelpClicked(self):
        self.openManPage('backintime')

    def btnHelpConfigClicked(self):
        self.openManPage('backintime-config')

    def btnWebsiteClicked(self):
        self.openUrl('https://github.com/bit-team/backintime')

    def btnChangelogClicked(self):
        def aHref(m):
            if m.group(0).count('@'):
                return '<a href="mailto:%(url)s">%(url)s</a>' % {'url': m.group(0)}
            else:
                return '<a href="%(url)s">%(url)s</a>' % {'url': m.group(0)}

        def aHref_lp(m):
            return '<a href="https://bugs.launchpad.net/backintime/+bug/%(id)s">%(txt)s</a>' % {'txt': m.group(0), 'id': m.group(1)}

        changelog_path = pathlib.Path(tools.docPath()) / 'CHANGES'
        msg = changelog_path.read_text('utf-8')
        msg = re.sub(r'https?://[^) \n]*', aHref, msg)
        msg = re.sub(r'(?:LP:|bug) ?#?(\d+)', aHref_lp, msg)
        msg = re.sub(r'\n', '<br>', msg)
        messagebox.showInfo(self, _('Changelog'), msg)

    def btnFaqClicked(self):
        self.openUrl('https://github.com/bit-team/backintime/blob/-/FAQ.md')

    def btnAskQuestionClicked(self):
        self.openUrl('https://github.com/bit-team/backintime/issues')

    def btnReportBugClicked(self):
        self.openUrl('https://github.com/bit-team/backintime/issues/new')

    def openUrl(self, url):
        return QDesktopServices.openUrl(QUrl(url))

    def openManPage(self, man_page):
        if not tools.checkCommand('man'):
            messagebox.critical(self, "Couldn't find 'man' to show the help page. Please install 'man'")
            return
        env = os.environ
        env['MANWIDTH'] = '80'
        proc = subprocess.Popen(['man', man_page],
                                stdout = subprocess.PIPE,
                                universal_newlines = True,
                                env = env)
        out, err = proc.communicate()
        messagebox.showInfo(self, 'Manual Page {}'.format(man_page), out)

    def btnShowHiddenFilesToggled(self, checked):
        self.showHiddenFiles = checked
        self.updateFilesView(1)

    def backupOnRestore(self):
        cb = QCheckBox(_(
            'Create backup copies with trailing {suffix}\n'
            'before overwriting or removing local elements.').format(
                suffix=self.snapshots.backupSuffix()))

        cb.setChecked(self.config.backupOnRestore())
        qttools.set_wrapped_tooltip(
            cb,
            [
                _("Newer versions of files will be renamed with trailing "
                  "{suffix} before restoring. If you don't need them anymore "
                  "you can remove them with the following command:").format(
                      suffix=self.snapshots.backupSuffix()),
                'find ./ -name "*{suffix}" -delete'.format(
                    suffix=self.snapshots.backupSuffix())
            ]
        ),

        return {
            'widget': cb,
            'retFunc': cb.isChecked,
            'id': 'backup'
        }

    def restoreOnlyNew(self):
        cb = QCheckBox(_('Only restore elements which do not exist or\n'
                         'are newer than those in destination.\n'
                         'Using "rsync --update" option.'))
        qttools.set_wrapped_tooltip(
            cb,
            ["From 'man rsync':",
             "",
             "This forces rsync to skip any files which exist on the "
             "destination and have a modified time that is newer than the "
             "source file. (If an existing destination file has a "
             "modification time equal to the source file’s, it will be "
             "updated if the sizes are different.)",
             "",
             "Note that this does not affect the copying of dirs, symlinks, "
             "or other special files. Also, a difference of file format "
             "between the sender and receiver is always considered to be "
             "important enough for an update, no matter what date is on the "
             "objects. In other words, if the source has a directory where "
             "the destination has a file, the transfer would occur regardless "
             "of the timestamps.",
             "",
             "This option is a transfer rule, not an exclude, so it doesn’t "
             "affect the data that goes into the file-lists, and thus it "
             "doesn’t affect deletions. It just limits the files that the "
             "receiver requests to be transferred."]
        )
        return {'widget': cb, 'retFunc': cb.isChecked, 'id': 'only_new'}

    def listRestorePaths(self, paths):
        fileList = QListWidget()
        fileList.addItems(paths)
        fileList.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        return {'widget': fileList, 'retFunc': None}

    def deleteOnRestore(self):
        cb = QCheckBox(_('Remove newer elements in original directory.'))
        qttools.set_wrapped_tooltip(
            cb,
            _('Restore selected files or directories to the original '
              'destination and delete files or directories which are not in '
              'the snapshot. Be extremely careful because this will delete '
              'files and directories which were excluded during taking the '
              'snapshot.')
        )
        return {'widget': cb, 'retFunc': cb.isChecked, 'id': 'delete'}

    def confirmRestore(self, paths, restoreTo=None):
        if restoreTo:
            msg = ngettext(
                # singular
                'Do you really want to restore this element into the '
                'new directory?',
                # plural
                'Do you really want to restore these elements into the '
                'new directory?',
                len(paths))
            msg = f'{msg}\n{restoreTo}'
        else:
            msg = ngettext(
                # singular
                'Do you really want to restore this element?',
                # plural
                'Do you really want to restore these elements?',
                len(paths))

        confirm, opt = messagebox.warningYesNoOptions(
            self,
            msg,
            (
                self.listRestorePaths(paths),
                self.backupOnRestore(),
                self.restoreOnlyNew(),
                self.deleteOnRestore()
            )
        )
        return (confirm, opt)

    def confirmDelete(self, warnRoot=False, restoreTo=None):
        if restoreTo:
            msg = _('Are you sure you want to remove all newer files '
                    'in {path}?').format(path=restoreTo)
        else:
            msg = _('Are you sure you want to remove all newer files in your '
                    'original directory?')

        if warnRoot:
            msg = f'<p>{msg}</p><p>'
            msg = msg + _(
                '{BOLD}Warning{BOLDEND}: Deleting files in the filesystem '
                'root could break your entire system.').format(
                    BOLD='<strong>', BOLDEND='</strong>')
            msg = msg + '</p>'

        answer = messagebox.warningYesNo(self, msg)

        return answer == QMessageBox.StandardButton.Yes

    def restoreThis(self):
        if self.sid.isRoot:
            return

        paths = [f for f, idx in self.multiFileSelected(fullPath = True)]

        with self.suspendMouseButtonNavigation():
            confirm, opt = self.confirmRestore(paths)
            if not confirm:
                return
            if opt['delete'] and not self.confirmDelete(warnRoot = '/' in paths):
                return

        rd = RestoreDialog(self, self.sid, paths, **opt)
        rd.exec()

    def restoreThisTo(self):
        if self.sid.isRoot:
            return

        paths = [f for f, idx in self.multiFileSelected(fullPath = True)]

        with self.suspendMouseButtonNavigation():
            restoreTo = qttools.getExistingDirectory(self, _('Restore to …'))
            if not restoreTo:
                return
            restoreTo = self.config.preparePath(restoreTo)
            confirm, opt = self.confirmRestore(paths, restoreTo)
            if not confirm:
                return
            if opt['delete'] and not self.confirmDelete(warnRoot = '/' in paths, restoreTo = restoreTo):
                return

        rd = RestoreDialog(self, self.sid, paths, restoreTo, **opt)
        rd.exec()

    def restoreParent(self):
        if self.sid.isRoot:
            return

        with self.suspendMouseButtonNavigation():
            confirm, opt = self.confirmRestore((self.path,))
            if not confirm:
                return
            if opt['delete'] and not self.confirmDelete(warnRoot = self.path == '/'):
                return

        rd = RestoreDialog(self, self.sid, self.path, **opt)
        rd.exec()

    def restoreParentTo(self):
        if self.sid.isRoot:
            return

        with self.suspendMouseButtonNavigation():
            restoreTo = qttools.getExistingDirectory(self, _('Restore to …'))
            if not restoreTo:
                return
            restoreTo = self.config.preparePath(restoreTo)
            confirm, opt = self.confirmRestore((self.path,), restoreTo)
            if not confirm:
                return
            if opt['delete'] and not self.confirmDelete(warnRoot = self.path == '/', restoreTo = restoreTo):
                return

        rd = RestoreDialog(self, self.sid, self.path, restoreTo, **opt)
        rd.exec()

    def btnSnapshotsClicked(self):
        path, idx = self.fileSelected(fullPath = True)

        with self.suspendMouseButtonNavigation():
            dlg = snapshotsdialog.SnapshotsDialog(self, self.sid, path)

            if dlg.exec() == QDialog.DialogCode.Accepted:

                if dlg.sid != self.sid:
                    self.timeLine.setCurrentSnapshotID(dlg.sid)

    def btnFolderUpClicked(self):

        if len(self.path) <= 1:
            return

        path = os.path.dirname(self.path)

        if self.path == path:
            return

        self.path = path
        self.path_history.append(self.path)
        self.updateFilesView(0)

    def btnFolderHistoryPreviousClicked(self):
        self._folderHistoryClicked(self.path_history.previous())

    def btnFolderHistoryNextClicked(self):
        self._folderHistoryClicked(self.path_history.next())

    def _folderHistoryClicked(self, path):
        full_path = self.sid.pathBackup(path)

        if (os.path.isdir(full_path)
                and self.sid.isExistingPathInsideSnapshotFolder(path)):
            self.path = path
            self.updateFilesView(0)

    def btnOpenCurrentItemClicked(self):
        path, idx = self.fileSelected()

        if not path:
            return

        self.openPath(path)

    def btnAddIncludeClicked(self):
        paths = [f for f, idx in self.multiFileSelected(fullPath = True)]
        include = self.config.include()
        updatePlaces = False

        for item in paths:

            if os.path.isdir(item):
                include.append((item, 0))
                updatePlaces = True
            else:
                include.append((item, 1))

        self.config.setInclude(include)

        if updatePlaces:
            self.updatePlaces()

    def btnAddExcludeClicked(self):
        paths = [f for f, idx in self.multiFileSelected(fullPath = True)]
        exclude = self.config.exclude()
        exclude.extend(paths)
        self.config.setExclude(exclude)

    def filesViewItemActivated(self, model_index):
        if self.qapp.keyboardModifiers() and Qt.ControlModifier:
            return

        if model_index is None:
            return

        rel_path = str(self.filesViewProxyModel.data(model_index))

        if not rel_path:
            return

        self.openPath(rel_path)

    def tmpCopy(self, full_path, sid = None):
        """
        Create a temporary local copy of the file ``full_path`` and add the
        temp folder to ``self.tmpDirs`` which will remove them on exit.

        Args:
            full_path (str):        path to original file
            sid (snapshots.SID):    snapshot ID used as temp folder suffix

        Returns:
            str:                    temporary path to file
        """
        if sid:
            sid = '_' + sid.sid

        d = TemporaryDirectory(suffix = sid)
        tmp_file = os.path.join(d.name, os.path.basename(full_path))

        if os.path.isdir(full_path):
            shutil.copytree(full_path, tmp_file)
        else:
            shutil.copy(full_path, d.name)

        self.tmpDirs.append(d)

        return tmp_file

    def openPath(self, rel_path):
        rel_path = os.path.join(self.path, rel_path)
        full_path = self.sid.pathBackup(rel_path)

        # The class "GenericNonSnapshot" indicates that "Now" is selected
        # in the snapshots timeline widget.
        if (os.path.exists(full_path)
            and (isinstance(self.sid, snapshots.GenericNonSnapshot)  # "Now"
                 or self.sid.isExistingPathInsideSnapshotFolder(rel_path))):

            if os.path.isdir(full_path):
                self.path = rel_path
                self.path_history.append(rel_path)
                self.updateFilesView(0)

            else:
                # prevent backup data from being accidentally overwritten
                # by create a temporary local copy and only open that one
                if not isinstance(self.sid, snapshots.RootSnapshot):
                    full_path = self.tmpCopy(full_path, self.sid)

                file_url = QUrl('file://' + full_path)
                self.run = QDesktopServices.openUrl(file_url)

    @pyqtSlot(int)
    def updateFilesView(self, changed_from, selected_file = None, show_snapshots = False): #0 - files view change directory, 1 - files view, 2 - time_line, 3 - places
        if 0 == changed_from or 3 == changed_from:
            selected_file = ''

        if 0 == changed_from:
            # update places
            self.places.setCurrentItem(None)
            for place_index in range(self.places.topLevelItemCount()):
                item = self.places.topLevelItem(place_index)
                if self.path == str(item.data(0, Qt.ItemDataRole.UserRole)):
                    self.places.setCurrentItem(item)
                    break

        text = ''
        if self.sid.isRoot:
            text = _('Now')
        else:
            name = self.sid.displayName
            # buhtz (2023-07)3 blanks at the end of that string as a
            # workaround to a visual issue where the last character was
            # cutoff. Not sure if this is DE and/or theme related.
            # Wasn't able to reproduc in an MWE. Remove after refactoring.
            text = '{}: {}   '.format(_('Snapshot'), name)

        self.filesWidget.setTitle(text)

        # try to keep old selected file
        if selected_file is None:
            selected_file, idx = self.fileSelected()

        self.selected_file = selected_file

        # update files view
        full_path = self.sid.pathBackup(self.path)

        if os.path.isdir(full_path):
            if self.showHiddenFiles:
                self.filesViewProxyModel.setFilterRegularExpression(r'')
            else:
                self.filesViewProxyModel.setFilterRegularExpression(r'^[^\.]')

            model_index = self.filesViewModel.setRootPath(full_path)
            proxy_model_index = self.filesViewProxyModel.mapFromSource(model_index)
            self.filesView.setRootIndex(proxy_model_index)

            self.toolbar_filesview.setEnabled(False)
            self.stackFilesView.setCurrentWidget(self.filesView)

            # TODO: find a signal for this
            self.dirListerCompleted()

        else:
            self._enable_restore_ui_elements(False)
            self.act_snapshots_dialog.setEnabled(False)
            self.stackFilesView.setCurrentWidget(self.lblFolderDontExists)

        # show current path
        self.widget_current_path.setText(self.path)
        self.act_restore_parent.setText(
            _('Restore {path}').format(path=self.path))
        self.act_restore_parent_to.setText(
            _('Restore {path} to …').format(path=self.path))

        # update folder_up button state
        self.act_folder_up.setEnabled(len(self.path) > 1)

    def _enable_restore_ui_elements(self, enable):
        """Enable or disable all buttons and menu entries related to the
        restore feature.

        Args:
            enable(bool): Enable or disable.

        If a specific snapshot is selected in the timeline widget then all
        restore UI elements are enabled. If "Now" (the first/root) is selected
        in the timeline all UI elements related to restoring should be
        disabled.
        """

        # The whole sub-menu incl. its button/entry. The related UI elements
        # are the "Restore" entry in the main-menu and the toolbar button in
        # the files-view toolbar.
        self.act_restore_menu.setEnabled(enable)

        # This two entries do appear, independent from the sub-menu above, in
        # the context menu of the files view.
        self.act_restore.setEnabled(enable)
        self.act_restore_to.setEnabled(enable)

    def dirListerCompleted(self):
        row_count = self.filesViewProxyModel.rowCount(
            self.filesView.rootIndex())
        has_files = row_count > 0

        # update restore button state
        enable = not self.sid.isRoot and has_files
        # TODO(buhtz) self.btnRestoreMenu.setEnabled(enable)
        self._enable_restore_ui_elements(enable)

        # update snapshots button state
        self.act_snapshots_dialog.setEnabled(has_files)

        # enable files toolbar
        self.toolbar_filesview.setEnabled(True)

        # select selected_file
        found = False

        if self.selected_file:
            index = self.filesView.indexAt(QPoint(0,0))

            if not index.isValid():
                return

            while index.isValid():
                file_name = (str(self.filesViewProxyModel.data(index)))

                if file_name == self.selected_file:
                    # TODO: doesn't work reliable
                    self.filesView.setCurrentIndex(index)
                    found = True
                    break

                index = self.filesView.indexBelow(index)

            self.selected_file = ''

        if not found and has_files:
            self.filesView.setCurrentIndex(self.filesViewProxyModel.index(0, 0))

    def fileSelected(self, fullPath=False):
        """Return path and index of the currently in Files View highlighted
        (selected) file.

        Args:
            fullPath(bool): Resolve relative to a full path.

        Returns:
            (tuple): Path as a string and the index.
        """
        idx = qttools.indexFirstColumn(self.filesView.currentIndex())
        selected_file = str(self.filesViewProxyModel.data(idx))

        if selected_file == '/':
            # nothing is selected
            selected_file = ''
            idx = self.filesViewProxyModel.mapFromSource(
                self.filesViewModel.index(self.path, 0))

        if fullPath:
            # resolve to full path
            selected_file = os.path.join(self.path, selected_file)

        return (selected_file, idx)

    def multiFileSelected(self, fullPath = False):
        count = 0
        for idx in self.filesView.selectedIndexes():
            if idx.column() > 0:
                continue

            selected_file = str(self.filesViewProxyModel.data(idx))

            if selected_file == '/':
                continue

            count += 1

            if fullPath:
                selected_file = os.path.join(self.path, selected_file)

            yield (selected_file, idx)

        if not count:
            # nothing is selected
            idx = self.filesViewProxyModel.mapFromSource(self.filesViewModel.index(self.path, 0))
            if fullPath:
                selected_file = self.path
            else:
                selected_file = ''

            yield (selected_file, idx)

    def setMouseButtonNavigation(self):
        self.qapp.installEventFilter(self.mouseButtonEventFilter)

    @contextmanager
    def suspendMouseButtonNavigation(self):
        self.qapp.removeEventFilter(self.mouseButtonEventFilter)
        yield
        self.setMouseButtonNavigation()

    def _open_approach_translator_dialog(self, cutoff=101):
        code = self.config.language_used
        name, perc = tools.get_native_language_and_completeness(code)

        if perc > cutoff:
            return

        def _complete_text(language: str, percent: int) -> str:
            # (2023-08): Move to packages meta-data (pyproject.toml).
            _URL_PLATFORM = 'https://translate.codeberg.org/engage/backintime'
            _URL_PROJECT = 'https://github.com/bit-team/backintime'

            txt = _(
                'Hello'
                '\n'
                'You have used Back In Time in the {language} '
                'language a few times by now.'
                '\n'
                'The translation of your installed version of Back In Time '
                'into {language} is {perc} complete. Regardless of your '
                'level of technical expertise, you can contribute to the '
                'translation and thus Back In Time itself.'
                '\n'
                'Please visit the {translation_platform_url} if you wish '
                'to contribute. For further assistance and questions, '
                'please visit the {back_in_time_project_website}.'
                '\n'
                'We apologize for the interruption, and this message '
                'will not be shown again. This dialog is available at '
                'any time via the help menu.'
                '\n'
                'Your Back In Time Team'
            )

            # Wrap paragraphs in <p> tags.
            result = ''
            for t in txt.split('\n'):
                result = f'{result}<p>{t}</p>'

            # Insert data in placeholder variables.
            platform_url \
                = f'<a href="{_URL_PLATFORM}">' \
                + _('translation platform') \
                + '</a>'

            project_url \
                = f'<a href="{_URL_PROJECT}">Back In Time ' \
                + _('Website') \
                + ' </a>'

            result = result.format(
                language=f'<strong>{language}</strong>',
                perc=f'<strong>{percent} %</strong>',
                translation_platform_url=platform_url,
                back_in_time_project_website=project_url
            )

            return result

        dlg = UserMessageDialog(
            parent=self,
            title=_('Your translation'),
            full_label=_complete_text(name, perc))
        dlg.exec()

    def _open_release_candidate_dialog(self):
        html_contact_list = (
            '<ul>'
            '<li>{email}</li>'
            '<li>{mailinglist}</li>'
            '<li>{issue}</li>'
            '<li>{alternative}</li>'
            '</ul>').format(
                email=_('Email to {link_and_label}.').format(
                    link_and_label='<a href="mailto:backintime@tuta.io">'
                                   'backintime@tuta.io</a>'),
                mailinglist=_('Mailing list {link_and_label}').format(
                    link_and_label='<a href="https://mail.python.org/mailman3/'
                                   'lists/bit-dev.python.org/">'
                                   'bit-dev@python.org</a>'),
                issue=_('{link_and_label} on the project website.').format(
                    link_and_label='<a href="https://github.com/bit-team/'
                                   'backintime/issues/new">{open_issue}</a>').format(
                                       open_issue=_('Open an issue')),
                alternative=_('Alternatively, you can use another channel '
                              'of your choice.')
            )

        rc_message = _(
            'This version of Back In Time is a Release Candidate and is '
            'primarily intended for stability testing in preparation for the '
            'next official release.'
            '\n'
            'No user data or telemetry is collected. However, the Back In '
            'Time team is very interested in knowing if the Release Candidate '
            'is being used and if it is worth continuing to provide such '
            'pre-release versions.'
            '\n'
            'Therefore, the team kindly asks for a short feedback on whether '
            'you have tested this version, even if you didn’t encounter any '
            'issues. Even a quick test run of a few minutes would help us a '
            'lot.'
            '\n'
            'The following contact options are available:'
            '\n'
            '{contact_list}'
            '\n'
            "In this version, this message won't be shown again but can be "
            'accessed anytime through the help menu.'
            '\n'
            'Thank you for your support and for helping us improve '
            'Back In Time!'
            '\n'
            'Your Back In Time Team').format(contact_list=html_contact_list)

        dlg = UserMessageDialog(
            parent=self,
            title=_('Release Candidate'),
            full_label=rc_message)
        dlg.exec()


    # |-------|
    # | Slots |
    # |-------|
    def slot_setup_language(self):
        """Show a modal language settings dialog and modify the UI language
        settings."""

        dlg = languagedialog.LanguageDialog(
            used_language_code=self.config.language_used,
            configured_language_code=self.config.language())

        dlg.exec()

        # Apply/OK pressed & the language value modified
        if dlg.result() == 1 and self.config.language() != dlg.language_code:

            self.config.setLanguage(dlg.language_code)

            messagebox.info(_('The language settings take effect only after '
                              'restarting Back In Time.'),
                            widget_to_center_on=dlg)

    def slot_help_translation(self):
        self._open_approach_translator_dialog()

    def slot_help_release_candidate(self):
        self._open_release_candidate_dialog()

    def slot_help_encryption(self):
        dlg = encfsmsgbox.EncfsExistsWarning(self, ['(not determined)'])
        dlg.exec()


class ExtraMouseButtonEventFilter(QObject):
    """
    globally catch mouse buttons 4 and 5 (mostly used as back and forward)
    and assign it to browse in file history.
    Dev Note (Germar): Maybe use Qt.BackButton and Qt.ForwardButton instead.
    """
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        super(ExtraMouseButtonEventFilter, self).__init__()

    def eventFilter(self, receiver, event):
        if (event.type() == QEvent.Type.MouseButtonPress
            and event.button() in (Qt.MouseButton.XButton1, Qt.MouseButton.XButton2)):

            if event.button() == Qt.MouseButton.XButton1:
                self.mainWindow.btnFolderHistoryPreviousClicked()

            if event.button() == Qt.MouseButton.XButton2:
                self.mainWindow.btnFolderHistoryNextClicked()

            return True

        else:

            return super(ExtraMouseButtonEventFilter, self) \
                .eventFilter(receiver, event)

class RemoveSnapshotThread(QThread):
    """
    remove snapshots in background thread so GUI will not freeze
    """
    refreshSnapshotList = pyqtSignal()
    hideTimelineItem = pyqtSignal(qttools.SnapshotItem)
    def __init__(self, parent, items):
        self.config = parent.config
        self.snapshots = parent.snapshots
        self.items = items
        super(RemoveSnapshotThread, self).__init__(parent)

    def run(self):
        last_snapshot = snapshots.lastSnapshot(self.config)
        renew_last_snapshot = False
        #inhibit suspend/hibernate during delete
        self.config.inhibitCookie = tools.inhibitSuspend(toplevel_xid = self.config.xWindowId,
                                                         reason = 'deleting snapshots')

        for item, sid in [(x, x.snapshotID()) for x in self.items]:
            self.snapshots.remove(sid)
            self.hideTimelineItem.emit(item)
            if sid == last_snapshot:
                renew_last_snapshot = True

        self.refreshSnapshotList.emit()

        #set correct last snapshot again
        if renew_last_snapshot:
            self.snapshots.createLastSnapshotSymlink(snapshots.lastSnapshot(self.config))

        #release inhibit suspend
        if self.config.inhibitCookie:
            self.config.inhibitCookie = tools.unInhibitSuspend(*self.config.inhibitCookie)


class FillTimeLineThread(QThread):
    """
    add snapshot IDs to timeline in background
    """
    addSnapshot = pyqtSignal(snapshots.SID)

    def __init__(self, parent):
        self.parent = parent
        self.config = parent.config
        super(FillTimeLineThread, self).__init__(parent)

    def run(self):
        for sid in snapshots.iterSnapshots(self.config):
            self.addSnapshot.emit(sid)
            self.parent.snapshotsList.append(sid)

        self.parent.snapshotsList.sort()


class SetupCron(QThread):
    """
    Check crontab entries on startup.
    """

    def __init__(self, parent):
        self.config = parent.config
        super(SetupCron, self).__init__(parent)

    def run(self):
        self.config.setupCron()


if __name__ == '__main__':
    cfg = backintime.startApp('backintime-qt')

    raiseCmd = ''
    if len(sys.argv) > 1:
        raiseCmd = '\n'.join(sys.argv[1:])

    appInstance = guiapplicationinstance.GUIApplicationInstance(
        cfg.appInstanceFile(), raiseCmd)
    cfg.PLUGIN_MANAGER.load(cfg=cfg)
    cfg.PLUGIN_MANAGER.appStart()

    logger.openlog()
    qapp = qttools.createQApplication(cfg.APP_NAME)
    translator = qttools.initiate_translator(cfg.language())
    qapp.installTranslator(translator)

    mainWindow = MainWindow(cfg, appInstance, qapp)

    if cfg.isConfigured():
        cfg.xWindowId = mainWindow.winId()
        mainWindow.show()
        qapp.exec()

    mainWindow.qapp.removeEventFilter(mainWindow.mouseButtonEventFilter)

    cfg.PLUGIN_MANAGER.appExit()
    appInstance.exitApplication()

    logger.closelog()  # must be last line (log until BiT "dies" ;-)
