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
import datetime
import getpass
from PyQt6.QtGui import QPalette, QColor, QFileSystemModel
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QGridLayout,
                             QDialogButtonBox,
                             QWidget,
                             QLabel,
                             QMenu,
                             QProgressBar,
                             )
from PyQt6.QtCore import (Qt,
                          QDir,
                          QSortFilterProxyModel,
                          QThread,
                          pyqtSignal)

import config
import qttools
import snapshots
import logger
import qttools


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
        self.setWindowTitle(_('Import configuration'))

        layout = QVBoxLayout(self)
        layout.addWidget(self._create_hint_label())

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

        self.treeViewFilterProxy.setFilterRegularExpression(r'^[^\.]')

        self.treeView.setModel(self.treeViewFilterProxy)
        for col in range(self.treeView.header().count()):
            self.treeView.setColumnHidden(col, col != 0)
        self.treeView.header().hide()

        # expand users home
        self.expandAll(os.path.expanduser('~'))
        layout.addWidget(self.treeView)

        # context menu
        self.treeView.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.onContextMenu)
        self.contextMenu = QMenu(self)
        self.btnShowHidden = self.contextMenu.addAction(
            icon.SHOW_HIDDEN, _('Show hidden files'))
        self.btnShowHidden.setCheckable(True)
        self.btnShowHidden.toggled.connect(self.onBtnShowHidden)

        # colors
        self.colorRed = QPalette()
        self.colorRed.setColor(
            QPalette.ColorRole.WindowText, QColor(205, 0, 0))
        self.colorGreen = QPalette()
        self.colorGreen.setColor(
            QPalette.ColorRole.WindowText, QColor(0, 160, 0))

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
            _('Import'), QDialogButtonBox.ButtonRole.AcceptRole)
        self.restoreButton.setEnabled(False)
        buttonBox.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

        self.scan.start()

        self.resize(600, 700)

    def _create_hint_label(self):
        """Create the label to explain how and where to find existing config
        file.

        Returns:
            (QLabel): The label
        """

        samplePath = os.path.join(
            'backintime',
            self.config.host(),
            getpass.getuser(), '1',
            snapshots.SID(datetime.datetime.now(), self.config).sid
        )
        samplePath = f'</ br><code>{samplePath}</code>'

        text_a = _(
            'Select the snapshot directory from which the configuration '
            'file should be imported. The path may look like: {samplePath}'
        ).format(samplePath=samplePath)

        text_b = _(
            'If the directory is located on an external or remote drive, '
            'it must be manually mounted beforehand.'
        )

        label = QLabel(f'<p>{text_a}</p><p>{text_b}</p>', self)
        label.setWordWrap(True)

        return label

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
        snapshotPath = os.path.join(
            'backintime', self.config.host(), getpass.getuser())

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

                except Exception as exc:
                    logger.error(
                        f'Unhandled branch in code! See in {__file__} '
                        f'SettingsDialog.searchConfig()\n{exc}')
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
                    _('Profile:') + str(profileId),
                    cfg.profileName(profileId),
                    _('Mode:') + cfg.SNAPSHOT_MODES[
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
            self.treeViewFilterProxy.setFilterRegularExpression(r'')
        else:
            self.treeViewFilterProxy.setFilterRegularExpression(r'^[^\.]')

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
