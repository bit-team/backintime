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
import threading
import subprocess
from typing import Any, Generator
from pathlib import Path
from queue import Queue
import logger
import bitbase
from config import Config
from snapshots import SID
from PyQt6.QtGui import (QBrush,
                         QColor,
                         QFont,
                         QGuiApplication,
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
                             QToolButton,
                             QTreeView,
                             QVBoxLayout,
                             QWidget)
from PyQt6.QtCore import (Qt,
                          QDir,
                          QModelIndex,
                          QTimer)
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

        # pylint: disable-next=import-outside-toplevel
        import icon  # noqa: PLC0415
        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(_('Import configuration'))

        layout = QVBoxLayout(self)

        self._create_hint(layout, config)
        self._lbl_spinner, self._spinner, self._btn_scan \
            = self._create_scan_controls(layout)

        self._btn_scan.clicked.connect(self.start_scanning)

        self._tree_view, self._tree_model = self._create_tree()
        layout.addWidget(self._tree_view)

        # expand users home
        self._expand_with_parents(self._index_from_path(Path.home()))

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

        layout.addWidget(btn_box)

        self._queue = Queue()

        self._pool_timer = QTimer(self)
        self._pool_timer.timeout.connect(self._process_found_queue)

        self._scan_fs_thread = None

        self.start_scanning()

        # See _resize_to_full_height() for details.
        self._resize_tries = 10
        QTimer.singleShot(1, self._resize_to_full_hight)

    def start_scanning(self):
        """Start the file system scanning thread and prepare the GUI"""
        self._btn_scan.setVisible(False)
        self._pool_timer.start(1500)  # milliseconds
        self._lbl_spinner.setText(_('Searching…'))
        self._spinner.start(interval_ms=200)
        self._scan_fs_thread = _ScanFileSystem(queue=self._queue)
        self._scan_fs_thread.start()

    def _resize_to_full_hight(self):
        """Resize dialog to full height and center it horizontal.
        """
        screen = QGuiApplication.screenAt(self.pos())
        geom = screen.availableGeometry()

        # Determine the height of the dialog's title bar and border. This
        # value is unknown or incorrect until the dialg is fully drawn.
        # That is the reason why we use this workaround.
        deco_height = self.frameGeometry().height() - self.geometry().height()
        if deco_height == 0 and self._resize_tries > 0:
            self._resize_tries -= 1
            QTimer.singleShot(1, self._resize_to_full_hight)
            return

        new_width = geom.width() // 3

        self.move(
            # center horizontal
            geom.center().x() - (new_width // 2),
            # vertical to top
            geom.y()
        )
        self.resize(
            # the desired width
            new_width,
            # full height (incl. window decoration) on available screen
            geom.height() - deco_height)

    def _create_tree(self) -> tuple[QTreeView, QFileSystemModel]:
        model = _CfgFileSystemModel(self)
        model.setRootPath(QDir().rootPath())
        model.setReadOnly(True)
        model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)

        view = QTreeView(self)
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

    def _create_hint(self,
                     parent_layout: QLayout,
                     config: Config) -> None:
        """Create the label to explain how and where to find existing config
        file.

        Returns:
            (QLabel): The label
        """

        sample_path = os.path.join(
            'backintime',
            config.host(),
            getpass.getuser(), '1',
            SID(datetime.datetime.now(), config).sid
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
        # pylint: disable=protected-access
        fp = self._path_from_index(current)
        cfg = _get_valid_config(fp / bitbase.FILENAME_CONFIG)

        if cfg:
            self._expand_with_parents(current)

            self._lbl_found.setText(str(fp))
            self._lbl_found.setPalette(self._color_green)
            self._show_profile(cfg)
            self._config_to_restore = cfg

        else:
            self._lbl_found.setText(_('No config found'))
            self._lbl_found.setPalette(self._color_red)
            self._wdg_profiles.hide()
            self._config_to_restore = None

        self._btn_restore.setEnabled(bool(cfg))

    def _expand_with_parents(self, index: QModelIndex):
        stack = []

        # Remember index's of the entry and all its parents
        current = index
        while current.isValid():
            stack.insert(0, current)
            current = current.parent()

        def expand_next():
            try:
                self._tree_view.expand(stack.pop(0))
                # Sligthely reduce slowdown/freeze because of resource
                # hungry QFileSystemModel
                QTimer.singleShot(50, expand_next)

            except IndexError:
                pass

        expand_next()

    def _show_profile(self, cfg):
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

    def _process_found_queue(self) -> None:
        self._tree_view.setUpdatesEnabled(False)

        while not self._queue.empty():
            path = self._queue.get()
            self._tree_model.highlight_this(Path(path))
            self._expand_with_parents(self._index_from_path(path))

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
        self._paths.append(path)

        # notify (redraw) the view
        self.layoutChanged.emit()

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
    # foundConfig = pyqtSignal(str)

    def __init__(self, queue: Queue, stop_event=None):
        super().__init__()

        self._queue = queue
        self._stop_event = stop_event or threading.Event()

    def run(self):
        """Run several searches for config files"""
        search_paths = [
            str(Path.home()),
            '/media',
            '/mnt',
            '/',  # keep root at the end!
        ]

        for path_to_scan in search_paths:
            # Exclude the other dirs if searching in root
            if path_to_scan == search_paths[-1]:
                excludes = search_paths[:-1][:]
            else:
                excludes = []

            for found in self._scan(path_to_scan, excludes):
                if self._stop_event.is_set():
                    return

                # print(f'queue.put({found=}')
                self._queue.put(found)

    def _scan(self, search_path: Path, excludes: list[str]
              ) -> Generator[Path, None, None]:
        """Use `find` on shell to search for `config` files."""

        logger.debug(f'Scanning in {search_path} for config files', self)
        cmd = ['find', str(search_path)]

        # exclude directories: defaults + extras
        for exclude in ['/proc', '/var', '/sys', '/tmp', '/run'] + excludes:
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

        with subprocess.Popen(cmd,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,
                              text=True) as proc:

            for line in proc.stdout:

                if self._stop_event.is_set():
                    return

                path = Path(line.strip())

                if _get_valid_config(path):
                    yield path.parent

    def stop(self):
        """Prepare stop and wait for finish."""
        self._stop_event.set()
        self.join()


def _get_valid_config(path: Path) -> Config | None:
    try:
        cfg = Config(str(path))
        if cfg.isConfigured():
            return cfg

    except (FileNotFoundError, UnicodeDecodeError):
        pass

    # pylint: disable-next=broad-exception-caught
    except Exception as exc:
        logger.critical(f'Unhandled branch in code!\n{exc}\n{__file__}')

    return None
