#    Back In Time
#    Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import sys

if not os.getenv('DISPLAY', ''):
    os.putenv('DISPLAY', ':0.0')

import datetime
import gettext
import re
import subprocess
import shutil
import signal
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import qttools
qttools.registerBackintimePath('common')

import backintime
import tools
import logger
import snapshots
import guiapplicationinstance
import mount
import progress
from exceptions import MountException

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import settingsdialog
import snapshotsdialog
import logviewdialog
import restoredialog
import messagebox


_=gettext.gettext


class MainWindow(QMainWindow):
    def __init__(self, config, appInstance, qapp):
        QMainWindow.__init__(self)

        self.config = config
        self.appInstance = appInstance
        self.qapp = qapp
        self.snapshots = snapshots.Snapshots(config)
        self.lastTakeSnapshotMessage = None
        self.tmpDirs = []

        #main toolbar
        self.mainToolbar = self.addToolBar('main')
        self.mainToolbar.setFloatable(False)

        #window icon
        import icon
        self.qapp.setWindowIcon(icon.BIT_LOGO)

        #profiles
        self.firstUpdateAll = True
        self.disableProfileChanged = False
        self.comboProfiles = qttools.ProfileCombo(self)
        self.comboProfilesAction = self.mainToolbar.addWidget(self.comboProfiles)

        # take_snapshot button
        self.btnTakeSnapshot = self.mainToolbar.addAction(icon.TAKE_SNAPSHOT, _('Take snapshot'))
        self.btnTakeSnapshot.triggered.connect(self.btnTakeSnapshotClicked)

        takeSnapshotMenu = qttools.Menu()
        action = takeSnapshotMenu.addAction(icon.TAKE_SNAPSHOT, _('Take snapshot'))
        action.triggered.connect(self.btnTakeSnapshotClicked)
        self.btnTakeSnapshotChecksum = takeSnapshotMenu.addAction(icon.TAKE_SNAPSHOT, _('Take snapshot with checksums'))
        self.btnTakeSnapshotChecksum.setToolTip(_('Use checksum to detect changes'))
        self.btnTakeSnapshotChecksum.triggered.connect(self.btnTakeSnapshotChecksumClicked)
        self.btnTakeSnapshot.setMenu(takeSnapshotMenu)

        for action in takeSnapshotMenu.actions():
            action.setIconVisibleInMenu(True)

        #pause snapshot button
        self.btnPauseTakeSnapshot = self.mainToolbar.addAction(icon.PAUSE, _('Pause snapshot process'))
        action = lambda: os.kill(self.snapshots.pid(), signal.SIGSTOP)
        self.btnPauseTakeSnapshot.triggered.connect(action)
        self.btnPauseTakeSnapshot.setVisible(False)

        #resume snapshot button
        self.btnResumeTakeSnapshot = self.mainToolbar.addAction(icon.RESUME, _('Resume snapshot process'))
        action = lambda: os.kill(self.snapshots.pid(), signal.SIGCONT)
        self.btnResumeTakeSnapshot.triggered.connect(action)
        self.btnResumeTakeSnapshot.setVisible(False)

        #stop snapshot button
        self.btnStopTakeSnapshot = self.mainToolbar.addAction(icon.STOP, _('Stop snapshot process'))
        self.btnStopTakeSnapshot.triggered.connect(self.btnStopTakeSnapshotClicked)
        self.btnStopTakeSnapshot.setVisible(False)

        # update snapshots button
        self.btnUpdateSnapshots = self.mainToolbar.addAction(icon.REFRESH_SNAPSHOT, _('Refresh snapshots list'))
        self.btnUpdateSnapshots.setShortcuts([Qt.Key_F5, QKeySequence(Qt.CTRL + Qt.Key_R)])
        self.btnUpdateSnapshots.triggered.connect(self.btnUpdateSnapshotsClicked)

        self.btnNameSnapshot = self.mainToolbar.addAction(icon.SNAPSHOT_NAME, _('Snapshot Name'))
        self.btnNameSnapshot.triggered.connect(self.btnNameSnapshotClicked)

        self.btnRemoveSnapshot = self.mainToolbar.addAction(icon.REMOVE_SNAPSHOT, _('Remove Snapshot'))
        self.btnRemoveSnapshot.triggered.connect(self.btnRemoveSnapshotClicked)

        self.btnSnapshotLogView = self.mainToolbar.addAction(icon.VIEW_SNAPSHOT_LOG, _('View Snapshot Log'))
        self.btnSnapshotLogView.triggered.connect(self.btnSnapshotLogViewClicked)

        self.btnLastLogView = self.mainToolbar.addAction(icon.VIEW_LAST_LOG, _('View Last Log'))
        self.btnLastLogView.triggered.connect(self.btnLastLogViewClicked)

        self.mainToolbar.addSeparator()

        self.btnSettings = self.mainToolbar.addAction(icon.SETTINGS, _('Settings'))
        self.btnSettings.triggered.connect(self.btnSettingsClicked)

        self.mainToolbar.addSeparator()

        self.btnShutdown = self.mainToolbar.addAction(icon.SHUTDOWN, _('Shutdown'))
        self.btnShutdown.setToolTip(_('Shutdown system after snapshot has finished.'))
        self.btnShutdown.setCheckable(True)
        self.shutdown = tools.ShutDown()
        self.btnShutdown.setEnabled(self.shutdown.canShutdown())
        self.btnShutdown.toggled.connect(self.btnShutdownToggled)

        self.btnQuit = self.mainToolbar.addAction(icon.EXIT, _('Exit'))
        self.btnQuit.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_W))
        self.btnQuit.triggered.connect(self.close)

        empty = QWidget(self)
        empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.mainToolbar.addWidget(empty)

        menuHelp = QMenu(self)
        self.btnHelp = menuHelp.addAction(icon.HELP, _('Help'))
        self.btnHelp.triggered.connect(self.btnHelpClicked)
        self.btnHelpConfig = menuHelp.addAction(icon.HELP, _('Config File Help'))
        self.btnHelpConfig.triggered.connect(self.btnHelpConfigClicked)
        menuHelp.addSeparator()
        self.btnWebsite = menuHelp.addAction(icon.WEBSITE, _('Website'))
        self.btnWebsite.triggered.connect(self.btnWebsiteClicked)
        self.btnChangelog = menuHelp.addAction(icon.CHANGELOG, _('Changelog'))
        self.btnChangelog.triggered.connect(self.btnChangelogClicked)
        self.btnFaq = menuHelp.addAction(icon.FAQ, _('FAQ'))
        self.btnFaq.triggered.connect(self.btnFaqClicked)
        self.btnAskQuestion = menuHelp.addAction(icon.QUESTION, _('Ask a question'))
        self.btnAskQuestion.triggered.connect(self.btnAskQuestionClicked)
        self.btnReportBug = menuHelp.addAction(icon.BUG, _('Report a bug'))
        self.btnReportBug.triggered.connect(self.btnReportBugClicked)
        menuHelp.addSeparator()
        self.btnAbout = menuHelp.addAction(icon.ABOUT, _('About'))
        self.btnAbout.triggered.connect(self.btnAboutClicked)

        action = self.mainToolbar.addAction(icon.HELP, _('Help'))
        action.triggered.connect(self.btnHelpClicked)
        action.setMenu(menuHelp)

        for action in menuHelp.actions():
            action.setIconVisibleInMenu(True)

        #main splitter
        self.mainSplitter = QSplitter(self)
        self.mainSplitter.setOrientation(Qt.Horizontal)

        #timeline
        self.timeLine = qttools.TimeLine(self)
        self.mainSplitter.addWidget(self.timeLine)
        self.timeLine.updateFilesView.connect(self.updateFilesView)

        #right widget
        self.filesWidget = QGroupBox(self)
        self.mainSplitter.addWidget(self.filesWidget)
        filesLayout = QVBoxLayout(self.filesWidget)
        left, top, right, bottom = filesLayout.getContentsMargins()
        filesLayout.setContentsMargins(0, 0, right, 0)

        #files toolbar
        self.filesViewToolbar = QToolBar(self)
        self.filesViewToolbar.setFloatable(False)

        self.btnFolderUp = self.filesViewToolbar.addAction(icon.UP, _('Up'))
        self.btnFolderUp.setShortcuts([QKeySequence(Qt.ALT + Qt.Key_Up), Qt.Key_Backspace])
        self.btnFolderUp.triggered.connect(self.btnFolderUpClicked)

        self.editCurrentPath = QLineEdit(self)
        self.editCurrentPath.setReadOnly(True)
        self.filesViewToolbar.addWidget(self.editCurrentPath)

        #show hidden files
        self.showHiddenFiles = self.config.boolValue('qt.show_hidden_files', False)
        self.btnShowHiddenFiles = self.filesViewToolbar.addAction(icon.SHOW_HIDDEN, _('Show hidden files'))
        self.btnShowHiddenFiles.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_H))
        self.btnShowHiddenFiles.setCheckable(True)
        self.btnShowHiddenFiles.setChecked(self.showHiddenFiles)
        self.btnShowHiddenFiles.toggled.connect(self.btnShowHiddenFilesToggled)

        self.filesViewToolbar.addSeparator()

        #restore menu
        self.menuRestore = qttools.Menu(self)
        self.btnRestore = self.menuRestore.addAction(icon.RESTORE, _('Restore'))
        self.btnRestore.setToolTip(_('Restore the selected files or folders '
                                     'to the original destination.'))
        self.btnRestore.triggered.connect(self.restoreThis)
        self.btnRestoreTo = self.menuRestore.addAction(icon.RESTORE_TO, _('Restore to ...'))
        self.btnRestoreTo.setToolTip(_('Restore the selected files or '
                                       'folders to a new destination.'))
        self.btnRestoreTo.triggered.connect(self.restoreThisTo)
        self.menuRestore.addSeparator()
        self.btnRestoreParent = self.menuRestore.addAction(icon.RESTORE, '')
        self.btnRestoreParent.setToolTip(_('Restore the currently shown '
                                           'folder and all its content to '
                                           'the original destination.'))
        self.btnRestoreParent.triggered.connect(self.restoreParent)
        self.btnRestoreParentTo = self.menuRestore.addAction(icon.RESTORE_TO, '')
        self.btnRestoreParentTo.setToolTip(_('Restore the currently shown '
                                             'folder and all its content '
                                             'to a new destination.'))
        self.btnRestoreParentTo.triggered.connect(self.restoreParentTo)
        self.menuRestore.addSeparator()
        self.btnRestoreDelete = self.menuRestore.addAction(icon.RESTORE, _('Restore and delete new files'))
        self.btnRestoreDelete.setToolTip(_('Restore selected files or folders '
                                           'to the original destination and\n'
                                           'delete files/folders which are '
                                           'not in the snapshot.\n'
                                           'This will delete files/folders which where '
                                           'excluded during taking the snapshot!\n'
                                           'Be extremely careful!!!'))
        self.btnRestoreDelete.triggered.connect(lambda: self.restoreThis(True))
        self.btnRestoreParentDelete = self.menuRestore.addAction(icon.RESTORE, '')
        self.btnRestoreParentDelete.setToolTip(_('Restore the currently shown folder '
                                                 'and all its content to the original\n'
                                                 'destination and delete files/folders '
                                                 'which are not in the snapshot.\n'
                                                 'This will delete files/folders which '
                                                 'where excluded during taking the snapshot!\n'
                                                 'Be extremely careful!!!'))
        self.btnRestoreParentDelete.triggered.connect(lambda: self.restoreParent(True))

        for action in self.menuRestore.actions():
            action.setIconVisibleInMenu(True)
        self.btnRestoreMenu = self.filesViewToolbar.addAction(icon.RESTORE, _('Restore'))
        self.btnRestoreMenu.setMenu(self.menuRestore)
        self.btnRestoreMenu.setToolTip(_('Restore selected file or folder.\n'
                                          'If this button is grayed out this is most likely '
                                          'because "%(now)s" is selected in left hand snapshots list.') % {'now': _('Now')})
        self.btnRestoreMenu.triggered.connect(self.restoreThis)

        self.btnSnapshots = self.filesViewToolbar.addAction(icon.SNAPSHOTS, _('Snapshots'))
        self.btnSnapshots.triggered.connect(self.btnSnapshotsClicked)

        filesLayout.addWidget(self.filesViewToolbar)

        #menubar
        self.menuSnapshot = self.menuBar().addMenu(_('Snapshot'))
        self.menuSnapshot.addAction(self.btnTakeSnapshot)
        self.menuSnapshot.addAction(self.btnUpdateSnapshots)
        self.menuSnapshot.addAction(self.btnNameSnapshot)
        self.menuSnapshot.addAction(self.btnRemoveSnapshot)
        self.menuSnapshot.addSeparator()
        self.menuSnapshot.addAction(self.btnSettings)
        self.menuSnapshot.addSeparator()
        self.menuSnapshot.addAction(self.btnShutdown)
        self.menuSnapshot.addAction(self.btnQuit)

        self.menuView = self.menuBar().addMenu(_('View'))
        self.menuView.addAction(self.btnFolderUp)
        self.menuView.addAction(self.btnShowHiddenFiles)
        self.menuView.addSeparator()
        self.menuView.addAction(self.btnSnapshotLogView)
        self.menuView.addAction(self.btnLastLogView)
        self.menuView.addSeparator()
        self.menuView.addAction(self.btnSnapshots)

        self.menuRestore = self.menuBar().addMenu(_('Restore'))
        self.menuRestore.addAction(self.btnRestore)
        self.menuRestore.addAction(self.btnRestoreTo)
        self.menuRestore.addSeparator()
        self.menuRestore.addAction(self.btnRestoreParent)
        self.menuRestore.addAction(self.btnRestoreParentTo)
        self.menuRestore.addSeparator()
        self.menuRestore.addAction(self.btnRestoreDelete)
        self.menuRestore.addAction(self.btnRestoreParentDelete)

        self.menuHelp = self.menuBar().addMenu(_('Help'))
        self.menuHelp.addAction(self.btnHelp)
        self.menuHelp.addAction(self.btnHelpConfig)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.btnWebsite)
        self.menuHelp.addAction(self.btnChangelog)
        self.menuHelp.addAction(self.btnFaq)
        self.menuHelp.addAction(self.btnAskQuestion)
        self.menuHelp.addAction(self.btnReportBug)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.btnAbout)

        #shortcuts without buttons
        self.shortcutPreviousFolder = QShortcut(QKeySequence(Qt.ALT + Qt.Key_Left), self)
        self.shortcutPreviousFolder.activated.connect(self.btnFolderHistoryPreviousClicked)
        self.shortcutNextFolder = QShortcut(QKeySequence(Qt.ALT + Qt.Key_Right), self)
        self.shortcutNextFolder.activated.connect(self.btnFolderHistoryNextClicked)
        self.shortcutOpenFolder = QShortcut(QKeySequence(Qt.ALT + Qt.Key_Down), self)
        self.shortcutOpenFolder.activated.connect(self.btnOpenCurrentItemClicked)

        #mouse button navigation
        self.mouseButtonEventFilter = ExtraMouseButtonEventFilter(self)
        self.setMouseButtonNavigation()

        #second spliter
        self.secondSplitter = QSplitter(self)
        self.secondSplitter.setOrientation(Qt.Horizontal)
        self.secondSplitter.setContentsMargins(0, 0, 0, 0)
        filesLayout.addWidget(self.secondSplitter)

        #places
        self.places = QTreeWidget(self)
        self.places.setRootIsDecorated(False)
        self.places.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.places.setHeaderLabel(_('Shortcuts'))
        self.places.header().setSectionsClickable(True)
        self.places.header().setSortIndicatorShown(True)
        self.places.header().setSectionHidden(1, True)
        self.places.header().setSortIndicator(int(self.config.profileIntValue('qt.places.SortColumn', 1)),
                                                   int(self.config.profileIntValue('qt.places.SortOrder', Qt.AscendingOrder)))
        self.placesSortLoop = {self.config.currentProfile(): False}
        self.secondSplitter.addWidget(self.places)
        self.places.header().sortIndicatorChanged.connect(self.sortPlaces)

        #files view stacked layout
        widget = QWidget(self)
        self.stackFilesView = QStackedLayout(widget)
        self.secondSplitter.addWidget(widget)

        #folder don't exist label
        self.lblFolderDontExists = QLabel(_('This folder doesn\'t exist\nin the current selected snapshot!'), self)
        qttools.setFontBold(self.lblFolderDontExists)
        self.lblFolderDontExists.setFrameShadow(QFrame.Sunken)
        self.lblFolderDontExists.setFrameShape(QFrame.Panel)
        self.lblFolderDontExists.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.stackFilesView.addWidget(self.lblFolderDontExists)

        #list files view
        self.filesView = QTreeView(self)
        self.stackFilesView.addWidget(self.filesView)
        self.filesView.setRootIsDecorated(False)
        self.filesView.setAlternatingRowColors(True)
        self.filesView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.filesView.setItemsExpandable(False)
        self.filesView.setDragEnabled(False)
        self.filesView.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.filesView.header().setSectionsClickable(True)
        self.filesView.header().setSectionsMovable(False)
        self.filesView.header().setSortIndicatorShown(True)

        self.filesViewModel = QFileSystemModel(self)
        self.filesViewModel.setRootPath(QDir().rootPath())
        self.filesViewModel.setReadOnly(True)
        self.filesViewModel.setFilter(QDir.AllDirs | QDir.AllEntries
                                            | QDir.NoDotAndDotDot | QDir.Hidden)

        self.filesViewProxyModel = QSortFilterProxyModel(self)
        self.filesViewProxyModel.setDynamicSortFilter(True)
        self.filesViewProxyModel.setSourceModel(self.filesViewModel)

        self.filesView.setModel(self.filesViewProxyModel)

        self.filesViewDelegate = QStyledItemDelegate(self)
        self.filesView.setItemDelegate(self.filesViewDelegate)

        sortColumn = self.config.intValue('qt.main_window.files_view.sort.column', 0)
        sortOrder = self.config.boolValue('qt.main_window.files_view.sort.ascending', True)
        if sortOrder:
            sortOrder = Qt.AscendingOrder
        else:
            sortOrder = Qt.DescendingOrder

        self.filesView.header().setSortIndicator(sortColumn, sortOrder)
        self.filesViewModel.sort(self.filesView.header().sortIndicatorSection(),
                                 self.filesView.header().sortIndicatorOrder())
        self.filesView.header().sortIndicatorChanged.connect(self.filesViewModel.sort)

        self.stackFilesView.setCurrentWidget(self.filesView)

        #
        self.setCentralWidget(self.mainSplitter)

        #context menu
        self.filesView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.filesView.customContextMenuRequested.connect(self.contextMenuClicked)
        self.contextMenu = QMenu(self)
        self.contextMenu.addAction(self.btnRestore)
        self.contextMenu.addAction(self.btnRestoreTo)
        self.contextMenu.addAction(self.btnSnapshots)
        self.contextMenu.addSeparator()
        self.btnAddInclude = self.contextMenu.addAction(icon.ADD, _('Add to Include'))
        self.btnAddExclude = self.contextMenu.addAction(icon.ADD, _('Add to Exclude'))
        self.btnAddInclude.triggered.connect(self.btnAddIncludeClicked)
        self.btnAddExclude.triggered.connect(self.btnAddExcludeClicked)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction(self.btnShowHiddenFiles)

        #ProgressBar
        self.progressBar = QProgressBar(self)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setStyleSheet("QProgressBar {border: 0px solid gray; text-align: left;}")
        self.progressBar.setVisible(False)
        self.status = QLabel(self)

        self.statusBar().addWidget(self.progressBar, 100)
        self.statusBar().addWidget(self.status, 100)
        self.status.setText(_('Done'))

        self.snapshotsList = []
        self.sid = snapshots.RootSnapshot(self.config)
        self.path = self.config.profileStrValue('qt.last_path',
                            self.config.strValue('qt.last_path', '/'))
        self.editCurrentPath.setText(self.path)
        self.path_history = tools.PathHistory(self.path)

        #restore size and position
        x = self.config.intValue('qt.main_window.x', -1)
        y = self.config.intValue('qt.main_window.y', -1)
        if x >= 0 and y >= 0:
            self.move(x, y)

        w = self.config.intValue('qt.main_window.width', 800)
        h = self.config.intValue('qt.main_window.height', 500)
        self.resize(w, h)

        mainSplitterLeftWidth = self.config.intValue('qt.main_window.main_splitter_left_w', 150)
        mainSplitterRightWidth = self.config.intValue('qt.main_window.main_splitter_right_w', 450)
        sizes = [mainSplitterLeftWidth, mainSplitterRightWidth]
        self.mainSplitter.setSizes(sizes)

        secondSplitterLeftWidth = self.config.intValue('qt.main_window.second_splitter_left_w', 150)
        secondSplitterRightWidth = self.config.intValue('qt.main_window.second_splitter_right_w', 300)
        sizes = [secondSplitterLeftWidth, secondSplitterRightWidth]
        self.secondSplitter.setSizes(sizes)

        filesViewColumnNameWidth = self.config.intValue('qt.main_window.files_view.name_width', -1)
        filesViewColumnSizeWidth = self.config.intValue('qt.main_window.files_view.size_width', -1)
        filesViewColumnDateWidth = self.config.intValue('qt.main_window.files_view.date_width', -1)
        if filesViewColumnNameWidth > 0 and filesViewColumnSizeWidth > 0 and filesViewColumnDateWidth > 0:
            self.filesView.header().resizeSection(0, filesViewColumnNameWidth)
            self.filesView.header().resizeSection(1, filesViewColumnSizeWidth)
            self.filesView.header().resizeSection(2, filesViewColumnDateWidth)

        #force settingdialog if it is not configured
        if not config.isConfigured():
            message = _('%(appName)s is not configured. Would you like '
                        'to restore a previous configuration?' % {'appName': self.config.APP_NAME})
            if QMessageBox.Yes == messagebox.warningYesNo(self, message):
                settingsdialog.RestoreConfigDialog(self).exec_()
            settingsdialog.SettingsDialog(self).exec_()

        if not config.isConfigured():
            return

        profile_id = config.currentProfile()

        #mount
        try:
            mnt = mount.Mount(cfg = self.config, profile_id = profile_id, parent = self)
            hash_id = mnt.mount()
        except MountException as ex:
            messagebox.critical(self, str(ex))
        else:
            self.config.setCurrentHashId(hash_id)

        if not config.canBackup(profile_id):
            messagebox.critical(self, _('Can\'t find snapshots folder.\nIf it is on a removable drive please plug it and then press OK'))

        self.filesViewProxyModel.layoutChanged.connect(self.dirListerCompleted)

        #populate lists
        self.updateProfiles()
        self.comboProfiles.currentIndexChanged.connect(self.comboProfileChanged)

        self.filesView.setFocus()

        self.updateSnapshotActions()

        #signals
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

    def closeEvent(self, event):
        if self.shutdown.askBeforeQuit():
            if QMessageBox.Yes != messagebox.warningYesNo(self, _('If you close this window Back In Time will not be able to shutdown your system when the snapshot has finished.\nDo you really want to close?')):
                return event.ignore()

        self.config.setStrValue('qt.last_path', self.path)
        self.config.setProfileStrValue('qt.last_path', self.path)

        self.config.setProfileIntValue('qt.places.SortColumn',
                                          self.places.header().sortIndicatorSection())
        self.config.setProfileIntValue('qt.places.SortOrder',
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

        self.config.setBoolValue('qt.show_hidden_files', self.showHiddenFiles)

        self.config.setIntValue('qt.main_window.files_view.sort.column', self.filesView.header().sortIndicatorSection())
        self.config.setBoolValue('qt.main_window.files_view.sort.ascending', self.filesView.header().sortIndicatorOrder() == Qt.AscendingOrder)

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

        profiles = self.config.profilesSortedByName()

        for profile_id in profiles:
            self.comboProfiles.addProfileID(profile_id)
            if profile_id == self.config.currentProfile():
                self.comboProfiles.setCurrentProfileID(profile_id)

        self.comboProfilesAction.setVisible(len(profiles) > 1)

        self.updateProfile()

        self.disableProfileChanged = False

    def updateProfile(self):
        self.updateTimeLine()
        self.updatePlaces()
        self.updateFilesView(0)

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

            self.config.setProfileIntValue('qt.places.SortColumn',
                                              self.places.header().sortIndicatorSection(),
                                              old_profile_id)
            self.config.setProfileIntValue('qt.places.SortOrder',
                                              self.places.header().sortIndicatorOrder(),
                                              old_profile_id)
            self.placesSortLoop[old_profile_id] = False
            self.places.header().setSortIndicator(int(self.config.profileIntValue('qt.places.SortColumn', 1, profile_id)),
                                                       int(self.config.profileIntValue('qt.places.SortOrder', Qt.AscendingOrder, profile_id)))

            self.config.setProfileStrValue('qt.last_path', self.path, old_profile_id)
            path = self.config.profileStrValue('qt.last_path', self.path, profile_id)
            if not path == self.path:
                self.path = path
                self.path_history.reset(self.path)
                self.editCurrentPath.setText(self.path)

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

    def updateTakeSnapshot(self, force_wait_lock = False):
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
                takeSnapshotMessage = (0, '...')
        elif takeSnapshotMessage is None:
            takeSnapshotMessage = self.lastTakeSnapshotMessage
            if takeSnapshotMessage is None:
                takeSnapshotMessage = (0, _('Done'))

        force_update = False

        if fake_busy:
            if self.btnTakeSnapshot.isEnabled():
                self.btnTakeSnapshot.setEnabled(False)

            if not self.btnStopTakeSnapshot.isVisible():
                for btn in (self.btnPauseTakeSnapshot,
                            self.btnResumeTakeSnapshot,
                            self.btnStopTakeSnapshot):
                    btn.setEnabled(True)
            self.btnTakeSnapshot.setVisible(False)
            self.btnPauseTakeSnapshot.setVisible(not paused)
            self.btnResumeTakeSnapshot.setVisible(paused)
            self.btnStopTakeSnapshot.setVisible(True)
        elif not self.btnTakeSnapshot.isEnabled():
            force_update = True

            self.btnTakeSnapshot.setEnabled(True)
            self.btnTakeSnapshot.setVisible(True)
            for btn in (self.btnPauseTakeSnapshot,
                        self.btnResumeTakeSnapshot,
                        self.btnStopTakeSnapshot):
                btn.setVisible(False)

            #TODO: check if there is a more elegant way than always get a new snapshot list which is very expensive (time)
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
                message = _('Working:') + ' ' + self.lastTakeSnapshotMessage[1].replace('\n', ' ')
            elif takeSnapshotMessage[0] == 0:
                message = self.lastTakeSnapshotMessage[1].replace('\n', ' ')
            else:
                message = _('Error:') + ' ' + self.lastTakeSnapshotMessage[1].replace('\n', ' ')

            self.status.setText(message)

        pg = progress.ProgressFile(self.config)
        if pg.fileReadable():
            self.progressBar.setVisible(True)
            self.status.setVisible(False)
            pg.load()
            self.progressBar.setValue(pg.intValue('percent'))
            self.progressBar.setFormat(' | '.join(self.getProgressBarFormat(pg, self.status.text())))
        else:
            self.progressBar.setVisible(False)
            self.status.setVisible(True)

        #if not fake_busy:
        #	self.lastTakeSnapshotMessage = None

    def getProgressBarFormat(self, pg, message):
        d = (('sent',   _('Sent:')), \
             ('speed',  _('Speed:')),\
             ('eta',    _('ETA:')))
        yield ' %p%'
        for key, txt in d:
            value = pg.strValue(key, '')
            if not value:
                continue
            yield txt + ' ' + value
        yield message

    def placesChanged(self, item, previous):
        if item is None:
            return

        path = str(item.data(0, Qt.UserRole))
        if not path:
            return

        if path == self.path:
            return

        self.path = path
        self.path_history.append(path)
        self.updateFilesView(3)

    def addPlace(self, name, path, icon):
        item = QTreeWidgetItem()

        item.setText(0, name)

        if icon:
            item.setIcon(0, QIcon.fromTheme(icon))

        item.setData(0, Qt.UserRole, path)

        if not path:
            item.setFont(0, qttools.fontBold(item.font(0)))
            item.setFlags(Qt.ItemIsEnabled)
            item.setBackground(0, QColor(196, 196, 196))
            item.setForeground(0, QColor(60, 60, 60))

        self.places.addTopLevelItem(item)

        if path == self.path:
            self.places.setCurrentItem(item)

        return item

    def updatePlaces(self):
        self.places.clear()
        self.addPlace(_('Global'), '', '')
        self.addPlace(_('Root'), '/', 'computer')
        self.addPlace(_('Home'), os.path.expanduser('~'), 'user-home')

        #add backup folders
        include_folders = self.config.include()
        if include_folders:
            folders = []
            for item in include_folders:
                if item[1] == 0:
                    folders.append(item[0])

            if folders:
                sortColumn = self.places.header().sortIndicatorSection()
                sortOrder  = self.places.header().sortIndicatorOrder()
                if not sortColumn:
                    folders.sort(key = lambda v: (v.upper(), v[0].islower()), reverse = sortOrder)
                self.addPlace(_('Backup folders'), '', '')
                for folder in folders:
                    self.addPlace(folder, folder, 'document-save')

    def sortPlaces(self, newColumn, newOrder, force = False):
        profile_id = self.config.currentProfile()
        if newColumn == 0 and newOrder == Qt.AscendingOrder:
            if profile_id in self.placesSortLoop and self.placesSortLoop[profile_id]:
                newColumn, newOrder = 1, Qt.AscendingOrder
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

        #update remove/name snapshot buttons
        self.btnNameSnapshot.setEnabled(enabled)
        self.btnRemoveSnapshot.setEnabled(enabled)
        self.btnSnapshotLogView.setEnabled(enabled)

    def timeLineChanged(self):
        item = self.timeLine.currentItem()
        self.updateSnapshotActions(item)

        if item is None:
            return

        sid = item.snapshotID()
        if not sid or sid == self.sid:
            return

        self.sid = sid
        self.updateFilesView(2)

    def updateTimeLine(self, refreshSnapshotsList = True):
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
        self.btnStopTakeSnapshot.setEnabled(False)
        self.btnPauseTakeSnapshot.setEnabled(False)
        self.btnResumeTakeSnapshot.setEnabled(False)
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
            logviewdialog.LogViewDialog(self).show()

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

        items = [item for item in self.timeLine.selectedItems() if not isinstance(item, snapshots.RootSnapshot)]
        if not items:
            return

        if QMessageBox.Yes != messagebox.warningYesNo(self, \
                              _('Are you sure you want to remove the snapshot:\n%s') \
                                %'\n'.join([item.snapshotID().displayName for item in items])):
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
            settingsdialog.SettingsDialog(self).show()

    def btnShutdownToggled(self, checked):
        self.shutdown.activate_shutdown = checked

    def contextMenuClicked(self, point):
        self.contextMenu.exec_(self.filesView.mapToGlobal(point))

    def btnAboutClicked(self):
        with self.suspendMouseButtonNavigation():
            dlg = About(self)
            dlg.exec_()

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

        msg = self.config.changelog()
        msg = re.sub(r'https?://[^) \n]*', aHref, msg)
        msg = re.sub(r'(?:LP:|bug) ?#?(\d+)', aHref_lp, msg)
        msg = re.sub(r'\n', '<br>', msg)
        messagebox.showInfo(self, _('Changelog'), msg)

    def btnFaqClicked(self):
        self.openUrl('https://github.com/bit-team/backintime/wiki/FAQ')

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
        cb = QCheckBox(_("Backup local files before overwriting or\nremoving with trailing '%(suffix)s'.")
                       % {'suffix': self.snapshots.backupSuffix()})
        cb.setChecked(self.config.backupOnRestore())
        return {'widget': cb, 'retFunc': cb.isChecked, 'id': 'backup'}

    def restoreOnlyNew(self):
        cb = QCheckBox(_('Only restore files which does not exist or\n'    +\
                         'are newer than those in destination.\n' +\
                         'Using "rsync --update" option.'))
        return {'widget': cb, 'retFunc': cb.isChecked, 'id': 'only_new'}

    def listRestorePaths(self, paths):
        fileList = QListWidget()
        fileList.addItems(paths)
        fileList.setSelectionMode(QAbstractItemView.NoSelection)
        return {'widget': fileList, 'retFunc': None}

    def confirmDeleteOnRestore(self, paths, warn_root = False):
        msg = _('Are you sure you want to remove all newer files in your '
                'original folder?')
        if warn_root:
            msg += '\n\n'
            msg += _('WARNING: deleting files in filesystem root could break your whole system!!!')
        msg += '\n\n'
        msg += _('Files to be restored:')

        confirm, opt = messagebox.warningYesNoOptions(self,
                                                      msg,
                                                      (self.listRestorePaths(paths),
                                                       self.backupOnRestore(),
                                                       self.restoreOnlyNew()))
        return (confirm, opt)

    def confirmRestore(self, paths):
        msg = _('Do you really want to restore this files(s):')

        confirm, opt = messagebox.warningYesNoOptions(self,
                                                      msg,
                                                      (self.listRestorePaths(paths),
                                                       self.backupOnRestore(),
                                                       self.restoreOnlyNew()))
        return (confirm, opt)

    def restoreThis(self, delete = False):
        if self.sid.isRoot:
            return

        selected_file = [f for f, idx in self.multiFileSelected()]
        if not selected_file:
            return
        rel_path = [os.path.join(self.path, x) for x in selected_file]

        with self.suspendMouseButtonNavigation():
            if delete:
                confirm, kwargs = self.confirmDeleteOnRestore(rel_path, any([i == '/' for i in selected_file]))
            else:
                confirm, kwargs = self.confirmRestore(rel_path)
        if not confirm:
            return

        restoredialog.restore(self, self.sid, rel_path, delete = delete, **kwargs)

    def restoreThisTo(self):
        if self.sid.isRoot:
            return

        selected_file = [f for f, idx in self.multiFileSelected()]
        if not selected_file:
            return
        rel_path = [os.path.join(self.path, x) for x in selected_file]

        confirm, kwargs = self.confirmRestore(rel_path)
        if not confirm:
            return

        restoredialog.restore(self, self.sid, rel_path, None, **kwargs)

    def restoreParent(self, delete = False):
        if self.sid.isRoot:
            return

        with self.suspendMouseButtonNavigation():
            if delete:
                confirm, kwargs = self.confirmDeleteOnRestore((self.path,), self.path == '/')
            else:
                confirm, kwargs = self.confirmRestore((self.path,))
        if not confirm:
            return

        restoredialog.restore(self, self.sid, self.path, delete = delete, **kwargs)

    def restoreParentTo(self):
        if self.sid.isRoot:
            return

        if not self.confirmRestore((self.path,)):
            return

        restoredialog.restore(self, self.sid, self.path, None)

    def btnSnapshotsClicked(self):
        selected_file, idx = self.fileSelected()
        if not selected_file:
            return

        rel_path = os.path.join(self.path, selected_file)

        with self.suspendMouseButtonNavigation():
            dlg = snapshotsdialog.SnapshotsDialog(self, self.sid, rel_path)
            if QDialog.Accepted == dlg.exec_():
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
        path = self.path_history.previous()
        full_path = self.sid.pathBackup(path)
        if os.path.isdir(full_path) and self.sid.canOpenPath(path):
            self.path = path
            self.updateFilesView(0)

    def btnFolderHistoryNextClicked(self):
        path = self.path_history.next()
        full_path = self.sid.pathBackup(path)
        if os.path.isdir(full_path) and self.sid.canOpenPath(path):
            self.path = path
            self.updateFilesView(0)

    def btnOpenCurrentItemClicked(self):
        path, idx = self.fileSelected()
        if not path:
            return
        self.openPath(path)

    def btnAddIncludeClicked(self):
        selected_file = [f for f, idx in self.multiFileSelected()]
        if not selected_file:
            return
        rel_path = [os.path.join(self.path, x) for x in selected_file]
        include = self.config.include()
        updatePlaces = False
        for item in rel_path:
            if os.path.isdir(item):
                include.append((item, 0))
                updatePlaces = True
            else:
                include.append((item, 1))
        self.config.setInclude(include)
        if updatePlaces:
            self.updatePlaces()

    def btnAddExcludeClicked(self):
        selected_file = [f for f, idx in self.multiFileSelected()]
        if not selected_file:
            return
        rel_path = [os.path.join(self.path, x) for x in selected_file]
        exclude = self.config.exclude()
        exclude.extend(rel_path)
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

        if os.path.exists(full_path) and self.sid.canOpenPath(rel_path):
            if os.path.isdir(full_path):
                self.path = rel_path
                self.path_history.append(rel_path)
                self.updateFilesView(0)
            else:
                # prevent backup data from being accidentally overwritten
                # by create a temporary local copy and only open that one
                if not isinstance(self.sid, snapshots.RootSnapshot):
                    full_path = self.tmpCopy(full_path, self.sid)

                self.run = QDesktopServices.openUrl(QUrl('file://' + full_path))

    @pyqtSlot(int)
    def updateFilesView(self, changed_from, selected_file = None, show_snapshots = False): #0 - files view change directory, 1 - files view, 2 - time_line, 3 - places
        if 0 == changed_from or 3 == changed_from:
            selected_file = ''

        if 0 == changed_from:
            #update places
            self.places.setCurrentItem(None)
            for place_index in range(self.places.topLevelItemCount()):
                item = self.places.topLevelItem(place_index)
                if self.path == str(item.data(0, Qt.UserRole)):
                    self.places.setCurrentItem(item)
                    break

        tooltip = ''
        text = ''
        if self.sid.isRoot:
            text = _('Now')
            tooltip = _('View the current disk content')
        else:
            name = self.sid.displayName
            text = _('Snapshot: %s') % name
            tooltip = _('View the snapshot made at %s') % name

        self.filesWidget.setTitle(text)
        self.filesWidget.setToolTip(tooltip)

        #try to keep old selected file
        if selected_file is None:
            selected_file, idx = self.fileSelected()

        self.selected_file = selected_file

        #update files view
        full_path = self.sid.pathBackup(self.path)

        if os.path.isdir(full_path):
            if self.showHiddenFiles:
                self.filesViewProxyModel.setFilterRegExp(r'')
            else:
                self.filesViewProxyModel.setFilterRegExp(r'^[^\.]')

            model_index = self.filesViewModel.setRootPath(full_path)
            proxy_model_index = self.filesViewProxyModel.mapFromSource(model_index)
            self.filesView.setRootIndex(proxy_model_index)

            self.filesViewToolbar.setEnabled(False)
            self.stackFilesView.setCurrentWidget(self.filesView)
            #TODO: find a signal for this
            self.dirListerCompleted()
        else:
            self.btnRestoreMenu.setEnabled(False)
            self.menuRestore.setEnabled(False)
            self.btnRestore.setEnabled(False)
            self.btnRestoreTo.setEnabled(False)
            self.btnSnapshots.setEnabled(False)
            self.stackFilesView.setCurrentWidget(self.lblFolderDontExists)

        #show current path
        self.editCurrentPath.setText(self.path)
        self.btnRestoreParent.setText(_("Restore '%s'") % self.path)
        self.btnRestoreParentTo.setText(_("Restore '%s' to ...") % self.path)
        self.btnRestoreParentDelete.setText(_("Restore '%s' and delete new files") % self.path)

        #update folder_up button state
        self.btnFolderUp.setEnabled(len(self.path) > 1)

    def dirListerCompleted(self):
        has_files = (self.filesViewProxyModel.rowCount(self.filesView.rootIndex()) > 0)

        #update restore button state
        enable = not self.sid.isRoot and has_files
        self.btnRestoreMenu.setEnabled(enable)
        self.menuRestore.setEnabled(enable)
        self.btnRestore.setEnabled(enable)
        self.btnRestoreTo.setEnabled(enable)

        #update snapshots button state
        self.btnSnapshots.setEnabled(has_files)

        #enable files toolbar
        self.filesViewToolbar.setEnabled(True)

        #select selected_file
        found = False

        if self.selected_file:
            index = self.filesView.indexAt(QPoint(0,0))
            if not index.isValid():
                return
            while index.isValid():
                file_name = (str(self.filesViewProxyModel.data(index)))
                if file_name == self.selected_file:
                    self.filesView.setCurrentIndex(index)
                    found = True
                    break
                index = self.filesView.indexBelow(index)
            self.selected_file = ''

        if not found and has_files:
            self.filesView.setCurrentIndex(self.filesViewProxyModel.index(0, 0))

    def fileSelected(self):
        idx = self.filesView.currentIndex()
        idx = self.indexFirstColumn(idx)
        selected_file = str(self.filesViewProxyModel.data(idx))
        if selected_file == '/':
            #nothing is selected
            return(None, None)
        return(selected_file, idx)

    def multiFileSelected(self):
        for idx in self.filesView.selectedIndexes():
            if idx.column() > 0:
                continue
            selected_file = str(self.filesViewProxyModel.data(idx))
            yield (selected_file, idx)

    def indexFirstColumn(self, idx):
        if idx.column() > 0:
            idx = idx.sibling(idx.row(), 0)
        return idx

    def setMouseButtonNavigation(self):
        self.qapp.installEventFilter(self.mouseButtonEventFilter)

    @contextmanager
    def suspendMouseButtonNavigation(self):
        self.qapp.removeEventFilter(self.mouseButtonEventFilter)
        yield
        self.setMouseButtonNavigation()

class About(QDialog):
    def __init__(self, parent = None):
        super(About, self).__init__(parent)
        self.parent = parent
        self.config = parent.config
        import icon

        self.setWindowTitle(_('About') + ' ' + self.config.APP_NAME)
        logo     = QLabel('Icon')
        logo.setPixmap(icon.BIT_LOGO.pixmap(QSize(48, 48)))
        version = self.config.VERSION
        ref, hashid = tools.gitRevisionAndHash()
        git_version = ''
        if ref:
            git_version = " git branch '{}' hash '{}'".format(ref, hashid)
        name = QLabel('<h1>' + self.config.APP_NAME + ' ' + version + '</h1>' + git_version)
        name.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        homepage = QLabel(self.mkurl('<https://github.com/bit-team/backintime>'))
        homepage.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        homepage.setOpenExternalLinks(True)
        bit_copyright = QLabel(self.config.COPYRIGHT + '\n')

        vlayout = QVBoxLayout(self)
        hlayout = QHBoxLayout()
        hlayout.addWidget(logo)
        hlayout.addWidget(name)
        hlayout.addStretch()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(homepage)
        vlayout.addWidget(bit_copyright)

        buttonBoxLeft  = QDialogButtonBox(self)
        btn_authors      = buttonBoxLeft.addButton(_('Authors'), QDialogButtonBox.ActionRole)
        btn_translations = buttonBoxLeft.addButton(_('Translations'), QDialogButtonBox.ActionRole)
        btn_license      = buttonBoxLeft.addButton(_('License'), QDialogButtonBox.ActionRole)

        buttonBoxRight = QDialogButtonBox(QDialogButtonBox.Ok)

        hlayout = QHBoxLayout()
        hlayout.addWidget(buttonBoxLeft)
        hlayout.addWidget(buttonBoxRight)
        vlayout.addLayout(hlayout)

        btn_authors.clicked.connect(self.authors)
        btn_translations.clicked.connect(self.translations)
        btn_license.clicked.connect(self.license)
        buttonBoxRight.accepted.connect(self.accept)

    def authors(self):
        return messagebox.showInfo(self, _('Authors'), self.mkurl(self.config.authors()))

    def translations(self):
        return messagebox.showInfo(self, _('Translations'), self.mkurl(self.config.translations()))

    def license(self):
        return messagebox.showInfo(self, _('License'), self.config.license())

    def mkurl(self, msg):
        msg = re.sub(r'<(.*?)>', self.aHref, msg)
        msg = re.sub(r'\n', '<br>', msg)
        return msg

    def aHref(self, m):
        if m.group(1).count('@'):
            return '<a href="mailto:%(url)s">%(url)s</a>' % {'url': m.group(1)}
        else:
            return '<a href="%(url)s">%(url)s</a>' % {'url': m.group(1)}

class ExtraMouseButtonEventFilter(QObject):
    """
    globally catch mouse buttons 4 and 5 (mostly used as back and forward)
    and assign it to browse in file history.
    When updating to Qt5 use Qt.BackButton and Qt.ForwardButton instead.
    """
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        super(ExtraMouseButtonEventFilter, self).__init__()

    def eventFilter(self, receiver, event):
        if event.type() == QEvent.MouseButtonPress and event.button() in (Qt.XButton1, Qt.XButton2):
            if event.button() == Qt.XButton1:
                self.mainWindow.btnFolderHistoryPreviousClicked()
            if event.button() == Qt.XButton2:
                self.mainWindow.btnFolderHistoryNextClicked()
            return True
        else:
            return super(ExtraMouseButtonEventFilter, self).eventFilter(receiver, event)

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

def debugTrace():
    """
    Set a tracepoint in the Python debugger that works with Qt
    """
    from pdb import set_trace
    pyqtRemoveInputHook()
    set_trace()

if __name__ == '__main__':
    cfg = backintime.startApp('backintime-qt')

    raiseCmd = ''
    if len(sys.argv) > 1:
        raiseCmd = '\n'.join(sys.argv[1 :])

    appInstance = guiapplicationinstance.GUIApplicationInstance(cfg.appInstanceFile(), raiseCmd)
    cfg.PLUGIN_MANAGER.load(cfg = cfg)
    cfg.PLUGIN_MANAGER.appStart()

    logger.openlog()
    qapp = qttools.createQApplication(cfg.APP_NAME)
    translator = qttools.translator()
    qapp.installTranslator(translator)

    mainWindow = MainWindow(cfg, appInstance, qapp)

    if cfg.isConfigured():
        cfg.xWindowId = mainWindow.winId()
        mainWindow.show()
        qapp.exec_()

    logger.closelog()

    cfg.PLUGIN_MANAGER.appExit()
    appInstance.exitApplication()
