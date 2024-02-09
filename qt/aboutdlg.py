# Back In Time
# Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey,
# Germar Reitze
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import os
import sys

if not os.getenv('DISPLAY', ''):
    os.putenv('DISPLAY', ':0.0')

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
from exceptions import MountException

from PyQt6.QtGui import (QAction,
                         QShortcut,
                         QDesktopServices,
                         QColor,
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
                             QHBoxLayout,
                             QStackedLayout,
                             QSplitter,
                             QGroupBox,
                             QMenu,
                             QToolBar,
                             QProgressBar,
                             QMessageBox,
                             QInputDialog,
                             QDialog,
                             QDialogButtonBox,
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
                          QSize,
                          QUrl,
                          pyqtRemoveInputHook,
                          )
import settingsdialog
import snapshotsdialog
import logviewdialog
from restoredialog import RestoreDialog
import languagedialog
import messagebox


class AboutDlg(QDialog):
    """The about dialog accessiable from the Help menu in the main window."""

    def __init__(self, parent = None):
        super().__init__(parent)
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
        name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        homepage = QLabel(self.mkurl('<https://github.com/bit-team/backintime>'))
        homepage.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse)
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
        btn_authors      = buttonBoxLeft.addButton(_('Authors'), QDialogButtonBox.ButtonRole.ActionRole)
        btn_translations = buttonBoxLeft.addButton(_('Translations'), QDialogButtonBox.ButtonRole.ActionRole)
        btn_license      = buttonBoxLeft.addButton(_('License'), QDialogButtonBox.ButtonRole.ActionRole)

        buttonBoxRight = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)

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
