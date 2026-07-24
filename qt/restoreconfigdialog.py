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
import getpass
import threading
import subprocess
import socket
import configparser
from typing import Any
from collections.abc import Generator
from pathlib import Path
from queue import Queue
import logger
import bitbase
from config import Config
from PyQt6.QtGui import (QBrush,
                         QColor,
                         QFont,
                         QFileSystemModel,
                         QPalette,
                         QShortcut)
from PyQt6.QtWidgets import (QDialog,
                             QDialogButtonBox,
                             QGridLayout,
                             QHBoxLayout,
                             QLabel,
                             QLayout,
                             QPushButton,
                             QSizePolicy,
                             QToolButton,
                             QTreeView,
                             QVBoxLayout,
                             QWidget)
from PyQt6.QtCore import (Qt,
                          QDir,
                          QModelIndex,
                          QTimer)
from konfig import Konfig
import qttools
from bitwidgets import Spinner


# pylint: disable-next=too-many-instance-attributes
class RestoreConfigDialog(QDialog):
    """
    Show a dialog that will help to restore BITs configuration.
    User can select a config from previous snapshots.

    Dev note (2025-07, buhtz): Experiencing the dialog as slow or temporary
    freezing is usual, because the QFileSystemModel is resource consuming and
    blocking the rest of the event loop. Unfold directories in the tree and the
    directories parents is very time consuming because QFileSystemModel access
    the file system each time.
    """

    def __init__(self, config: Config):
        super().__init__()

        self.config = config

        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415
        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(_('Import configuration'))

        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding
        )

        main_layout = QVBoxLayout(self)

        top_layout = QVBoxLayout()
        self._create_hint(top_layout)
        self._lbl_spinner, self._spinner, self._btn_scan \
            = self._create_scan_controls(top_layout)

        self._btn_scan.clicked.connect(self.start_scanning)

        main_layout.addLayout(top_layout, 0)
        self._tree_view, self._tree_model = self._create_tree()
        tree_layout = QVBoxLayout()
        tree_layout.addWidget(self._tree_view)
        main_layout.addLayout(tree_layout, 1)

        # expand users home
        self._expand_with_parents(self._index_from_path(Path.home()))

        # colors
        self._color_red, self._color_green = __class__._red_and_green()

        bottom_layout = QVBoxLayout()

        # show where a snapshot with config was found
        self._lbl_found = QLabel(_('No directory selected'), self)
        self._lbl_found.setWordWrap(True)
        self._lbl_found.setPalette(self._color_red)
        bottom_layout.addWidget(self._lbl_found)

        # show profiles inside the config
        self._wdg_profiles = QWidget(self)
        self._wdg_profiles.setContentsMargins(0, 0, 0, 0)
        self._wdg_profiles.hide()
        self._grid_layout = QGridLayout()
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setHorizontalSpacing(20)
        self._wdg_profiles.setLayout(self._grid_layout)
        bottom_layout.addWidget(self._wdg_profiles)

        self._config_to_restore = None

        self._tree_view.selectionModel().currentChanged.connect(
            self._slot_index_changed)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        self._btn_restore = btn_box.button(QDialogButtonBox.StandardButton.Ok)
        self._btn_restore.setText(_('Import'))
        self._btn_restore.setEnabled(False)

        bottom_layout.addWidget(btn_box)

        main_layout.addLayout(bottom_layout, 0)

        self._queue = Queue()

        self._pool_timer = QTimer(self)
        self._pool_timer.timeout.connect(self._process_found_queue)

        self._scan_fs_thread = None

        self.start_scanning()

    def start_scanning(self):
        """Start the file system scanning thread and prepare the GUI"""
        self._btn_scan.setVisible(False)
        self._pool_timer.start(1500)  # milliseconds
        self._lbl_spinner.setText(_('Searching…'))
        self._spinner.start(interval_ms=200)
        self._scan_fs_thread = _ScanFileSystem(queue=self._queue)
        self._scan_fs_thread.start()

    def _create_tree(self) -> tuple[QTreeView, QFileSystemModel]:
        model = _CfgFileSystemModel(self)
        model.setRootPath(QDir().rootPath())
        model.setReadOnly(True)
        model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)

        view = QTreeView(self)
        view.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        view.setModel(model)
        view.setAnimated(False)

        # Hide all columns (size, typ, mod date) except the first (name)
        for col in range(1, view.header().count()+1):
            view.setColumnHidden(col, True)

        view.header().hide()

        return view, model

    @staticmethod
    def _red_and_green() -> tuple[QColor, QColor]:
        red = QPalette()
        red.setColor(QPalette.ColorRole.WindowText, QColor(205, 0, 0))

        green = QPalette()
        green.setColor(QPalette.ColorRole.WindowText, QColor(0, 160, 0))

        return red, green

    def _create_hint(self, parent_layout: QLayout) -> None:
        """Create the label to explain how and where to find existing config
        file.

        Returns:
            (QLabel): The label
        """

        sample_path = Path.home() / 'backintime' \
            / socket.gethostname() \
            / getpass.getuser() / '1' / '20250203-172341-123'
        sample_path = f'<br /><code>{sample_path!s}</code>'

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

        layout = QHBoxLayout()
        layout.addWidget(qttools.create_icon_label_info(icon_scale_factor=2))
        layout.addWidget(label, stretch=1)

        parent_layout.addLayout(layout)

    def _create_scan_controls(self, parent_layout: QLayout
                              ) -> tuple[QLabel, Spinner, QPushButton]:
        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415

        lbl_spinner = QLabel(_('Searching…'), self)
        spinner = Spinner(self, font_scale=2)

        btn_scan = QPushButton(_('Scan again'), self)
        btn_scan.setIcon(icon.REFRESH)

        hbox = QHBoxLayout()
        hbox.addWidget(lbl_spinner)
        hbox.addWidget(spinner)
        hbox.addWidget(btn_scan)
        hbox.addStretch()
        hbox.addWidget(self._create_button_show_hidden())

        parent_layout.addLayout(hbox)

        return lbl_spinner, spinner, btn_scan

    def _create_button_show_hidden(self) -> QToolButton:
        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415

        btn = QToolButton(self)
        btn.setText(_('Show hidden directories'))
        btn.setIcon(icon.SHOW_HIDDEN)
        btn.setToolTip(_('Show/hide hidden directories (Ctrl+H)'))
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn.setCheckable(True)

        shortcut = QShortcut('Ctrl+H', self)
        shortcut.activated.connect(btn.toggle)

        btn.setChecked(False)
        btn.toggled.connect(self._slot_show_hidden)

        return btn

    def _path_from_index(self, index: QModelIndex) -> Path:
        """
        return a path string for a given treeView index
        """
        return Path(self._tree_model.filePath(index))

    def _index_from_path(self, path: str | Path) -> QModelIndex:
        """
        return the index for path which can be used in treeView
        """

        idx = self._tree_model.index(
            str(path) if isinstance(path, Path) else path)

        return idx

    def _slot_index_changed(self, current, _previous):
        """Called every time a new item is chosen in treeView.

        If there was a config found inside the selected folder, show
        available information about the config.
        """

        if self._config_to_restore is not None:
            # Reset the singleton instance
            self._config_to_restore.delete_this_instance()
            self._config_to_restore = None

        # pylint: disable=protected-access
        fp = self._path_from_index(current)
        cfg = _get_valid_konfig(fp / bitbase.FILENAME_CONFIG)

        if cfg:
            self._expand_with_parents(current)

            self._lbl_found.setText(str(fp))
            self._lbl_found.setPalette(self._color_green)
            self._show_profile(cfg)
            self._config_to_restore = cfg

        else:
            self._lbl_found.setText(_('No config found in this directory.'))
            self._lbl_found.setPalette(self._color_red)
            self._wdg_profiles.hide()
            self._config_to_restore = None

        self._btn_restore.setEnabled(bool(cfg))

    def _expand_with_parents(self, index):
        indexes = []

        current = index.parent()

        while current.isValid():
            indexes.insert(0, current)
            current = current.parent()

        def expand_next():
            if not indexes:
                self._tree_view.scrollTo(index)
                return

            idx = indexes.pop(0)

            self._tree_view.expand(idx)
            self._tree_model.fetchMore(idx)

            QTimer.singleShot(150, expand_next)

        expand_next()

    def _show_profile(self, cfg: Konfig):
        child = self._grid_layout.takeAt(0)

        while child:
            child.widget().deleteLater()
            child = self._grid_layout.takeAt(0)

        for row, profile in enumerate(cfg.iter_profiles()):

            for col, txt in enumerate((
                    _('Profile:') + f' {profile.profile_id}',
                    profile.name,
                    _('Mode:') + f' {profile.mode}'
                    )):
                self._grid_layout.addWidget(QLabel(txt, self), row, col)

        self._grid_layout.setColumnStretch(col, 1)
        self._wdg_profiles.show()

    def _process_found_queue(self) -> None:
        self._tree_view.setUpdatesEnabled(False)

        while not self._queue.empty():
            path = self._queue.get()

            self._tree_model.highlight_this(Path(path))

            idx = self._index_from_path(path)
            self._expand_with_parents(idx)

        self._tree_view.setUpdatesEnabled(True)

        # stop spinner and queue pooling if thread is empty
        if not self._scan_fs_thread.is_alive():
            self._spinner.stop()
            self._lbl_spinner.setText(_('Search complete.'))
            self._pool_timer.stop()
            self._btn_scan.setVisible(True)

    def _slot_show_hidden(self, checked):
        if checked:
            flags = QDir.Filter.AllDirs \
                | QDir.Filter.NoDotAndDotDot \
                | QDir.Filter.Hidden

        else:
            flags = QDir.Filter.AllDirs \
                | QDir.Filter.NoDotAndDotDot \

        self._tree_model.setFilter(flags)

    # def accept(self):
    #     """
    #     handle over the dict from the selected config. The dict contains
    #     all settings from the config.
    #     """
    #     if self._config_to_restore:
    #         self.config = self._config_to_restore

    #     super().accept()

    def reject(self):
        """Dialog was canceled."""
        if self._config_to_restore:
            self._config_to_restore.delete_this_instance()

        super().reject()

    def exec(self):
        """
        stop the scan thread if it is still running after dialog was closed.
        """
        ret = super().exec()
        self._scan_fs_thread.stop()

        return ret


class _CfgFileSystemModel(QFileSystemModel):
    """A sub-classed file-system model to visually highlight some of its
    entries."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._paths = []

        font = QFont()
        font.setBold(True)

        # See data() for details
        self._role_result = {
            Qt.ItemDataRole.ForegroundRole: QBrush(
                parent.palette().color(QPalette.ColorRole.Highlight)),
            Qt.ItemDataRole.FontRole: font
        }

    def highlight_this(self, path: Path) -> None:
        """Remember the path to draw with different font"""
        if path in self._paths:
            return

        self._paths.append(path)

        index = self.index(str(path))
        if index.isValid():
            self.dataChanged.emit(
                index,
                index,
                [
                    Qt.ItemDataRole.ForegroundRole,
                    Qt.ItemDataRole.FontRole,
                ],
            )

        # # notify (redraw) the view
        # self.layoutChanged.emit()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Any:
        """Draw an entry with bold font and highlted font color if in
        `self._paths`.
        """
        if role in self._role_result:
            file_path = Path(self.filePath(index))

            # Return font or brush
            if file_path in self._paths:
                return self._role_result[role]

        return super().data(index, role)


class _ScanFileSystem(threading.Thread):
    """A thread scanning the file system for config files related to BIT."""

    def __init__(self, queue: Queue, stop_event=None):
        super().__init__()

        self._queue = queue
        self._stop_event = stop_event or threading.Event()

    def run(self):
        """Run several searches for config files"""

        # Perform multiple scans starting with the most important parts
        # of the filesystem
        search_paths = [
            str(Path.home()),
            '/media',
            '/mnt',
            '/',  # keep root at the end!
        ]

        for path_to_scan in search_paths:

            if path_to_scan == search_paths[-1]:
                # When scanning the root filesystem, exclude directories that
                # were already scanned separately above.
                excludes = search_paths[:-1][:]
            else:
                excludes = []

            for found in self._scan(path_to_scan, excludes):
                if self._stop_event.is_set():
                    return

                self._queue.put(found)

    def _scan(self, search_path: Path, excludes: list[str]
              ) -> Generator[Path, None, None]:
        """Use `find` on shell to search for `config` files."""

        logger.debug(f'Scanning in {search_path} for config files', self)
        cmd = ['find', str(search_path)]

        to_exclude = [
            '/proc',
            '/var',
            '/sys',
            '/tmp',
            '/run',
            '*/.git',
            '*/__*',
        ]
        to_exclude = to_exclude + excludes

        # exclude directories: defaults + extras
        for exclude in to_exclude:
            cmd = cmd + ['(', '-path', exclude, '-prune', ')', '-o']

        cmd = cmd + [
            '(',
            '-type',
            'f',
            '-name',
            bitbase.FILENAME_CONFIG,
            '-print',
            ')'
        ]

        logger.debug(f'Executing command {" ".join(cmd)}...')

        with subprocess.Popen(cmd,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,
                              text=True) as proc:

            for line in proc.stdout:

                if self._stop_event.is_set():
                    return

                path = Path(line.strip())

                if _get_valid_konfig(path):
                    yield path.parent

    def stop(self):
        """Prepare stop and wait for finish."""
        self._stop_event.set()
        self.join()


def _get_valid_konfig(path: Path) -> Konfig | None:
    try:
        cfg = Konfig()
        cfg.load(path)

        # is "configured"?
        for profile in cfg.iter_profiles():
            if not profile.snapshots_path or not profile.include:
                # Remove the singleton instance
                cfg.delete_this_instance()

                return None

        return cfg

    except (FileNotFoundError, UnicodeDecodeError, configparser.ParsingError):
        pass

    # Remove the singleton instance
    cfg.delete_this_instance()
    return None
