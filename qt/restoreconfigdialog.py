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
                             QTreeView)
from PyQt6.QtCore import (Qt,
                          QDir,
                          QSortFilterProxyModel,
                          QThread,
                          QModelIndex,
                          pyqtSignal)

import config
import snapshots
import logger


class MyTreeView(QTreeView):
    """
    subclass QTreeView to emit a SIGNAL myCurrentIndexChanged
    if the SLOT currentChanged is called

    Used by restoreconfigdialog.py
    """
    myCurrentIndexChanged = pyqtSignal(QModelIndex, QModelIndex)

    # pylint: disable-next=invalid-name
    def currentChanged(self, current, previous):
        self.myCurrentIndexChanged.emit(current, previous)
        super(MyTreeView, self).currentChanged(current, previous)


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
        self._tree_view = MyTreeView(self)
        self._tree_model = QFileSystemModel(self)
        self._tree_model.setRootPath(QDir().rootPath())
        self._tree_model.setReadOnly(True)
        self._tree_model.setFilter(QDir.Filter.AllDirs |
                                     QDir.Filter.NoDotAndDotDot |
                                     QDir.Filter.Hidden)

        self._filter_proxy = QSortFilterProxyModel(self)
        self._filter_proxy.setDynamicSortFilter(True)
        self._filter_proxy.setSourceModel(self._tree_model)

        self._filter_proxy.setFilterRegularExpression(r'^[^\.]')

        self._tree_view.setModel(self._filter_proxy)
        for col in range(self._tree_view.header().count()):
            self._tree_view.setColumnHidden(col, col != 0)
        self._tree_view.header().hide()

        # expand users home
        self._expand_all(os.path.expanduser('~'))
        layout.addWidget(self._tree_view)

        # context menu
        self._tree_view.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree_view.customContextMenuRequested.connect(
            self._slot_on_context_menu)
        self._context_menu = QMenu(self)
        self._btn_show_hidden = self._context_menu.addAction(
            icon.SHOW_HIDDEN, _('Show hidden files'))
        self._btn_show_hidden.setCheckable(True)
        self._btn_show_hidden.toggled.connect(self._slot_show_hidden)

        # colors
        self._color_red = QPalette()
        self._color_red.setColor(
            QPalette.ColorRole.WindowText, QColor(205, 0, 0))
        self._color_green = QPalette()
        self._color_green.setColor(
            QPalette.ColorRole.WindowText, QColor(0, 160, 0))

        # wait indicator which will show that the scan for
        # snapshots is still running
        self.wait = QProgressBar(self)
        self.wait.setMinimum(0)
        self.wait.setMaximum(0)
        self.wait.setMaximumHeight(7)
        layout.addWidget(self.wait)

        # show where a snapshot with config was found
        self._lbl_found = QLabel(_('No config found'), self)
        self._lbl_found.setWordWrap(True)
        self._lbl_found.setPalette(self._color_red)
        layout.addWidget(self._lbl_found)

        # show profiles inside the config
        self._wdg_profiles = QWidget(self)
        self._wdg_profiles.setContentsMargins(0, 0, 0, 0)
        self._wdg_profiles.hide()
        self._grid_layout = QGridLayout()
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setHorizontalSpacing(20)
        self._wdg_profiles.setLayout(self._grid_layout)
        layout.addWidget(self._wdg_profiles)

        self._config_to_restore = None

        self._scan_fs_thread = ScanFileSystem(self)

        self._tree_view.myCurrentIndexChanged.connect(self._slot_index_changed)
        self._scan_fs_thread.foundConfig.connect(self.handle_scan_found)
        self._scan_fs_thread.finished.connect(self.handle_scan_finished)

        btn_box = QDialogButtonBox(self)
        self._btn_restore = btn_box.addButton(
            _('Import'), QDialogButtonBox.ButtonRole.AcceptRole)
        self._btn_restore.setEnabled(False)
        btn_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._scan_fs_thread.start()

        self.resize(600, 700)

    def _create_hint_label(self):
        """Create the label to explain how and where to find existing config
        file.

        Returns:
            (QLabel): The label
        """

        sample_path = os.path.join(
            'backintime',
            self.config.host(),
            getpass.getuser(), '1',
            snapshots.SID(datetime.datetime.now(), self.config).sid
        )
        sample_path = f'</ br><code>{sample_path}</code>'

        text_a = _(
            'Select the backup directory from which the configuration '
            'file should be imported. The path may look like: {samplePath}'
        ).format(samplePath=sample_path)

        text_b = _(
            'If the directory is located on an external or remote drive, '
            'it must be manually mounted beforehand.'
        )

        label = QLabel(f'<p>{text_a}</p><p>{text_b}</p>', self)
        label.setWordWrap(True)

        return label

    def _path_from_index(self, index: int) -> str:
        """
        return a path string for a given treeView index
        """
        idx = self._filter_proxy.mapToSource(index)

        return str(self._tree_model.filePath(idx))

    def _index_from_path(self, path: str) -> int:
        """
        return the index for path which can be used in treeView
        """
        indexSource = self._tree_model.index(path)
        return self._filter_proxy.mapFromSource(indexSource)

    def _slot_index_changed(self, current, previous):
        """Called every time a new item is chosen in treeView.

        If there was a config found inside the selected folder, show
        available information about the config.
        """
        cfg = self._search_config(self._path_from_index(current))

        if cfg:
            self._expand_all(
                os.path.dirname(os.path.dirname(cfg._LOCAL_CONFIG_PATH)))
            self._lbl_found.setText(cfg._LOCAL_CONFIG_PATH)
            self._lbl_found.setPalette(self._color_green)
            self._show_profile(cfg)
            self._config_to_restore = cfg

        else:
            self._lbl_found.setText(_('No config found'))
            self._lbl_found.setPalette(self._color_red)
            self._wdg_profiles.hide()
            self._config_to_restore = None

        self._btn_restore.setEnabled(bool(cfg))

    def _search_config(self, path):
        """
        try to find config in couple possible subfolders
        """
        backup_path = os.path.join(
            'backintime', self.config.host(), getpass.getuser())

        try_paths = ['', '..', 'last_snapshot']
        try_paths.extend([
            os.path.join(backup_path, str(i), 'last_snapshot')
            for i in range(10)])

        for p in try_paths:
            cfg_path = os.path.join(path, p, 'config')

            if os.path.exists(cfg_path):

                try:
                    cfg = config.Config(cfg_path)

                    if cfg.isConfigured():
                        return cfg

                except Exception as exc:
                    logger.critical(
                        f'Unhandled branch in code! See in {__file__} '
                        f'SettingsDialog.searchConfig()\n{exc}',
                        self)

    def _expand_all(self, path):
        """
        expand all folders from filesystem root to given path
        """
        paths = [path, ]
        while len(path) > 1:
            path = os.path.dirname(path)
            paths.append(path)
        paths.append('/')
        paths.reverse()
        [self._tree_view.expand(self._index_from_path(p)) for p in paths]

    def _show_profile(self, cfg):
        """
        show information about the profiles inside cfg
        """
        child = self._grid_layout.takeAt(0)

        while child:
            child.widget().deleteLater()
            child = self._grid_layout.takeAt(0)

        for row, pid in enumerate(cfg.profiles()):

            for col, txt in enumerate((
                    _('Profile:') + str(pid),
                    cfg.profileName(pid),
                    _('Mode:') + cfg.SNAPSHOT_MODES[
                        cfg.snapshotsMode(pid)][1]
                    )):
                self._grid_layout.addWidget(QLabel(txt, self), row, col)

        self._grid_layout.setColumnStretch(col, 1)
        self._wdg_profiles.show()

    def handle_scan_found(self, path):
        """
        scan hit a config. Expand the snapshot folder.
        """
        self._expand_all(os.path.dirname(path))

    def handle_scan_finished(self):
        """
        scan is done. Delete the wait indicator
        """
        self.wait.deleteLater()

    def _slot_on_context_menu(self, point):
        self._context_menu.exec(self._tree_view.mapToGlobal(point))

    def _slot_show_hidden(self, checked):
        if checked:
            self._filter_proxy.setFilterRegularExpression(r'')
        else:
            self._filter_proxy.setFilterRegularExpression(r'^[^\.]')

    def accept(self):
        """
        handle over the dict from the selected config. The dict contains
        all settings from the config.
        """
        if self._config_to_restore:
            self.config.dict = self._config_to_restore.dict
        super(RestoreConfigDialog, self).accept()

    def exec(self):
        """
        stop the scan thread if it is still running after dialog was closed.
        """
        ret = super(RestoreConfigDialog, self).exec()
        self._scan_fs_thread.stop()
        return ret


class ScanFileSystem(QThread):
    CONFIG = 'config'
    BACKUP = 'backup'
    BACKINTIME = 'backintime'

    foundConfig = pyqtSignal(str)

    def __init__(self, parent):
        super(ScanFileSystem, self).__init__(parent)
        self._stopper = False

    def stop(self):
        """
        prepare stop and wait for finish.
        """
        self._stopper = True
        return self.wait()

    def run(self):
        """
        search in order of hopefully fastest way to find the snapshots.
        1. /home/USER 2. /media 3. /mnt and at last filesystem root.
        Already searched paths will be excluded.
        """
        search_order = [os.path.expanduser('~'), '/media', '/mnt', '/']

        for scan in search_order:
            exclude = search_order[:]
            exclude.remove(scan)

            for path in self._scan_path(scan, exclude):
                self.foundConfig.emit(path)

    def _scan_path(self, path, excludes=()):
        """
        walk through all folders and try to find 'config' file.
        If found make sure it is nested in backintime/FOO/BAR/1/2345/config and
        return its path.
        Exclude all paths from excludes and also
        all backintime/FOO/BAR/1/2345/backup
        """
        for root, dirs, files in os.walk(path, topdown=True):

            if self._stopper:
                return

            for exclude in excludes:
                ex_dir, ex_base = os.path.split(exclude)

                if root == ex_dir:

                    if ex_base in dirs:
                        del dirs[dirs.index(ex_base)]

            if self.CONFIG in files:
                rootdirs = root.split(os.sep)

                if (len(rootdirs) > 4
                        and rootdirs[-5].startswith(self.BACKINTIME)):

                    if self.BACKUP in dirs:
                        del dirs[dirs.index(self.BACKUP)]

                    yield root
