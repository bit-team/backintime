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
"""A dialog to identify and import old Back In Time configs.
"""
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
                             QTreeView)
from PyQt6.QtCore import (Qt,
                          QDir,
                          QSortFilterProxyModel,
                          QThread,
                          pyqtSignal)
import logger
import bitbase
from config import Config
from snapshots import SID, Snapshots


# pylint: disable-next=too-many-instance-attributes
class RestoreConfigDialog(QDialog):
    """
    Show a dialog that will help to restore BITs configuration.
    User can select a config from previous snapshots.
    """

    def __init__(self, config: Config, snapshots: Snapshots):
        super().__init__()

        self.config = config
        self.snapshots = snapshots

        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415
        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(_('Import configuration'))

        layout = QVBoxLayout(self)
        layout.addWidget(self._create_hint_label())

        self._tree_view, self._tree_model, self._filter_proxy \
            = self._create_tree()

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
        self._color_red, self._color_green = __class__._red_and_green()

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

        self._tree_view.selectionModel().currentChanged.connect(
            self._slot_index_changed)
        self._scan_fs_thread.foundConfig.connect(self.handle_scan_found)

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

    def _create_tree(self):
        view = QTreeView(self)  # MyTreeView(self)
        model = QFileSystemModel(self)
        model.setRootPath(QDir().rootPath())
        model.setReadOnly(True)
        model.setFilter(QDir.Filter.AllDirs |
                        QDir.Filter.NoDotAndDotDot |
                        QDir.Filter.Hidden)

        filter_proxy = QSortFilterProxyModel(self)
        filter_proxy.setDynamicSortFilter(True)
        filter_proxy.setSourceModel(model)

        filter_proxy.setFilterRegularExpression(r'^[^\.]')

        view.setModel(filter_proxy)

        for col in range(view.header().count()):
            view.setColumnHidden(col, col != 0)

        view.header().hide()

        return view, model, filter_proxy

    @staticmethod
    def _red_and_green() -> tuple[QColor, QColor]:
        red = QPalette()
        red.setColor(QPalette.ColorRole.WindowText, QColor(205, 0, 0))

        green = QPalette()
        green.setColor(QPalette.ColorRole.WindowText, QColor(0, 160, 0))

        return red, green

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
            SID(datetime.datetime.now(), self.config).sid
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
        idx_source = self._filter_proxy.mapToSource(index)

        return str(self._tree_model.filePath(idx_source))

    def _index_from_path(self, path: str) -> int:
        """
        return the index for path which can be used in treeView
        """
        idx = self._tree_model.index(path)

        return self._filter_proxy.mapFromSource(idx)

    def _slot_index_changed(self, current, _previous):
        """Called every time a new item is chosen in treeView.

        If there was a config found inside the selected folder, show
        available information about the config.
        """
        # pylint: disable=protected-access
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

    def _search_config(self, path: str) -> Config:
        """Try to find config file in couple possible subdirectories.
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
                    cfg = Config(cfg_path)

                    if cfg.isConfigured():
                        return cfg

                # Dev note (2025-07, buhtz): Remove it soon.
                # pylint: disable-next=broad-exception-caught
                except Exception as exc:
                    logger.critical(
                        f'Unhandled branch in code! See in {__file__} '
                        f'SettingsDialog.searchConfig()\n{exc}',
                        self)

        return None

    def _expand_all(self, path):
        """Expand all folders from filesystem root to given path

        ???
        """
        paths = [path, ]

        while len(path) > 1:
            path = os.path.dirname(path)
            paths.append(path)

        paths.append('/')
        paths.reverse()

        for p in paths:
            self._tree_view.expand(self._index_from_path(p))

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
        print(f'handle_scan_found() :: {path=}')
        self._expand_all(os.path.dirname(path))

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

        super().accept()

    def exec(self):
        """
        stop the scan thread if it is still running after dialog was closed.
        """
        ret = super().exec()
        self._scan_fs_thread.stop()

        return ret


class ScanFileSystem(QThread):
    """A thread scanning the file system for config files related to BIT."""
    foundConfig = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self._stopper = False

    def stop(self):
        """Prepare stop and wait for finish."""
        self._stopper = True

        return self.wait()

    def run(self):
        """Search in order of hopefully fastest way to find the backups.

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
        """Walk through all directories and try to find 'config' file.

        If found make sure it is nested in backintime/FOO/BAR/1/2345/config and
        return its path. Exclude all paths from excludes and also
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

            if bitbase.FILENAME_CONFIG in files:
                rootdirs = root.split(os.sep)

                if (len(rootdirs) > 4  # noqa: PLR2004
                        and rootdirs[-5].startswith(bitbase.BINARY_NAME_BASE)):

                    if 'backup' in dirs:
                        del dirs[dirs.index('backup')]

                    yield root
