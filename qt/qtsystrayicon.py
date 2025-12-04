# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2025 Gregory Deseck
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Separate application managing the systray icon"""
import sys
import os
import subprocess
import signal
import textwrap

# TODO Is this really required? If the client is not configured for X11
#      it may use Wayland or something else...
#      Or is this just required when run as root (where GUIs are not
#      configured normally)?
if not os.getenv('DISPLAY', ''):
    os.putenv('DISPLAY', ':0.0')

import qttools
qttools.register_backintime_path('common')
import logger
# Workaround until the codebase allows a single place to init all translations
import tools
tools.initiate_translation(None)
import snapshots
import progress
import logviewdialog
import encfstools
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QProgressBar, QWidget
from PyQt6.QtGui import QIcon, QRegion

class QtSysTrayIcon:
    """Application instance for the Back In Time systray icon"""

    # pylint: disable-next=line-too-long
    ICON_PATH_ONLY = '<path d="M4.1 1a2.5 2.5 0 0 0-1.768.73 2.504 2.504 0 0 0 0 3.54 2.506 2.506 0 0 0 3.535 0 2.504 2.504 0 0 0 0-3.54A2.5 2.5 0 0 0 4.1 1m7.8 0a2.5 2.5 0 0 0-1.767.73 2.504 2.504 0 0 0 0 3.54 2.506 2.506 0 0 0 3.535 0 2.504 2.504 0 0 0 0-3.54A2.5 2.5 0 0 0 11.9 1M8 10a2.5 2.5 0 0 0-2.5 2.5A2.5 2.5 0 0 0 8 15c1.379 0 2.5-1.121 2.5-2.5S9.379 10 8 10" style="fill-opacity:.5"/>\n<path d="M4.102 1.998A1.504 1.504 0 0 0 3.04 4.562L6.5 8.024V12.5c0 .832.668 1.5 1.5 1.5s1.5-.668 1.5-1.5V8.023l3.46-3.46a1.504 1.504 0 0 0 0-2.125 1.5 1.5 0 0 0-2.12 0L8 5.28 5.16 2.438a1.5 1.5 0 0 0-1.058-.44"/>'
    # pylint: disable-next=line-too-long
    ICON_PART_A = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"'
    ICON_PART_B = '>\n' + ICON_PATH_ONLY + '\n</svg>'

    def __init__(self):

        self.snapshots = snapshots.Snapshots()
        self.config = self.snapshots.config
        self.decode = None

        if len(sys.argv) > 1:
            if not self.config.setCurrentProfile(sys.argv[1]):
                logger.warning(
                    f'Failed to change Profile_ID {sys.argv[1]}', self)

        self.qapp = qttools.create_qapplication(self.config.APP_NAME)
        translator = qttools.initiate_translator(self.config.language())
        self.qapp.installTranslator(translator)
        self.qapp.setQuitOnLastWindowClosed(False)

        import icon
        self.qapp.setWindowIcon(icon.BIT_LOGO)

        self.status_icon = self._create_status_icon()
        self.contextMenu = QMenu()

        self.menuProfileName = self.contextMenu.addAction(
            _('Profile: {profile_name}').format(
                profile_name=self.config.profileName())
        )
        self.contextMenu.addSeparator()

        self.menuStatusMessage = self.contextMenu.addAction(_('Done'))
        self.menuProgress = self.contextMenu.addAction('')
        self.menuProgress.setVisible(False)
        self.contextMenu.addSeparator()

        self.btnPause = self.contextMenu.addAction(
            icon.PAUSE, _('Pause backup process'))
        action = lambda: os.kill(self.snapshots.pid(), signal.SIGSTOP)
        self.btnPause.triggered.connect(action)

        self.btnResume = self.contextMenu.addAction(
            icon.RESUME, _('Resume backup process'))
        action = lambda: os.kill(self.snapshots.pid(), signal.SIGCONT)
        self.btnResume.triggered.connect(action)
        self.btnResume.setVisible(False)

        self.btnStop = self.contextMenu.addAction(
            icon.STOP, _('Stop backup process'))
        self.btnStop.triggered.connect(self.onBtnStop)
        self.contextMenu.addSeparator()

        self.btnDecode = self.contextMenu.addAction(
            icon.VIEW_SNAPSHOT_LOG, _('decode paths'))
        self.btnDecode.setCheckable(True)
        self.btnDecode.setVisible(self.config.snapshotsMode() == 'ssh_encfs')
        self.btnDecode.toggled.connect(self.onBtnDecode)

        self.openLog = self.contextMenu.addAction(
            icon.VIEW_LAST_LOG, _('View Last Log'))
        self.openLog.triggered.connect(self.onOpenLog)
        self.startBIT = self.contextMenu.addAction(
            icon.BIT_LOGO,
            _('Start {appname}').format(appname=self.config.APP_NAME)
        )
        self.startBIT.triggered.connect(self.onStartBIT)
        self.status_icon.setContextMenu(self.contextMenu)

        self.progressBar = self._create_progress_bar()

        self.first_error = self.config.notify()
        self.popup = None
        self.last_message = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateInfo)

    def _create_status_icon(self) -> QSystemTrayIcon:
        # Logo color depending on dark/light mode
        mode = self.config.systray()

        if mode == 'light':
            return QSystemTrayIcon(self.get_light_icon())

        if mode == 'dark':
            return QSystemTrayIcon(self.get_dark_icon())

        if qttools.in_dark_mode(self.qapp):
            return QSystemTrayIcon(self.get_light_icon())

        return QSystemTrayIcon(self.get_dark_icon())


    def _create_progress_bar(self) -> QProgressBar:
        bar = QProgressBar()

        bar.setMinimum(0)
        bar.setMaximum(100)
        bar.setValue(0)

        bar.setTextVisible(False)

        bar.resize(24, 6)

        import icon
        bar.render(
            icon.BIT_LOGO.pixmap(24),
            sourceRegion=QRegion(0, -14, 24, 6),
            flags=QWidget.RenderFlag.DrawChildren
        )

        return bar

    def prepareExit(self):
        self.timer.stop()

        if not self.status_icon is None:
            self.status_icon.hide()
            self.status_icon = None

        if not self.popup is None:
            self.popup.deleteLater()
            self.popup = None

        self.qapp.processEvents()

    def run(self):
        if '--keep-alive' not in sys.argv:
            if not self.snapshots.busy():
                sys.exit()

        self.status_icon.show()
        self.timer.start(500)
        self.qapp.exec()
        self.prepareExit()

    def updateInfo(self):
        # Exit this systray icon "app" when the snapshots is taken
        if '--keep-alive' not in sys.argv:
            if not self.snapshots.busy():
                self.prepareExit()
                self.qapp.exit(0)
                return

        paused = tools.processPaused(self.snapshots.pid())
        self.btnPause.setVisible(not paused)
        self.btnResume.setVisible(paused)

        message = self.snapshots.takeSnapshotMessage()
        if message is None and self.last_message is None:
            message = (0, _('Working…'))

        if not message is None:
            if message != self.last_message:
                self.last_message = message

                if self.decode:
                    message = (message[0], self.decode.log(message[1]))

                self.menuStatusMessage.setText(
                    '\n'.join(textwrap.wrap(message[1], width=80)))

                self.status_icon.setToolTip(message[1])

        pg = progress.ProgressFile(self.config)

        if pg.fileReadable():
            pg.load()
            # percent = pg.intValue('percent')
            ## disable progressbar in icon until BiT has it's own icon
            ## fixes bug #902
            # if percent != self.progressBar.value():
            #     self.progressBar.setValue(percent)
            #     self.progressBar.render(
            #         self.pixmap,
            #         sourceRegion=QRegion(0, -14, 24, 6),
            #         flags=QWidget.RenderFlags(QWidget.DrawChildren))
            #     self.status_icon.setIcon(QIcon(self.pixmap))

            self.menuProgress.setText(' | '.join(self.getMenuProgress(pg)))
            self.menuProgress.setVisible(True)

        else:
            # self.status_icon.setIcon(self.icon.BIT_LOGO)
            self.menuProgress.setVisible(False)

    def getMenuProgress(self, pg):
        """See common/app.py::MainWindow.getProgressBarFormat().

        The code is a near duplicate.
        """
        data = (
            ('sent', _('Sent:')),
            ('speed', _('Speed:')),
            ('eta',    _('ETA:'))
        )

        for key, txt in data:
            value = pg.strValue(key, '')

            if not value:
                continue

            yield txt + ' ' + value

    def onStartBIT(self):
        profileID = self.config.currentProfile()
        cmd = ['backintime-qt',]
        if not profileID == '1':
            cmd += ['--profile-id', profileID]
        _proc = subprocess.Popen(cmd)

    def onOpenLog(self):
        dlg = logviewdialog.LogViewDialog(self, systray = True)
        dlg.decode = self.decode
        dlg.cbDecode.setChecked(self.btnDecode.isChecked())
        dlg.exec()

    def onBtnDecode(self, checked):
        if checked:
            self.decode = encfstools.Decode(self.config)
            self.last_message = None
            self.updateInfo()
        else:
            self.decode = None

    def onBtnStop(self):
        os.kill(self.snapshots.pid(), signal.SIGKILL)
        self.btnStop.setEnabled(False)
        self.btnPause.setEnabled(False)
        self.btnResume.setEnabled(False)
        self.snapshots.setTakeSnapshotMessage(0, 'Backup terminated')

    @classmethod
    def _get_icon_filled(cls, color: str) -> QIcon:
        """Generate the dark symbolic icon"""
        svg_content = cls.ICON_PART_A + f' fill="{color}"' + cls.ICON_PART_B
        qicon = qttools.create_qicon_from_svg_source(svg_content)
        return qicon

    @staticmethod
    def get_dark_icon() -> QIcon:
        return QtSysTrayIcon._get_icon_filled('black')

    @staticmethod
    def get_light_icon() -> QIcon:
        return QtSysTrayIcon._get_icon_filled('white')


if __name__ == '__main__':
    """Use '--keep-alive' to keep the systray icon alive. This is for debug
    purpose only.
    """

    logger.openlog('SYSTRAY')

    # HACK: Minimal arg parsing to enable debug-level logging
    if '--debug' in sys.argv:
        logger.DEBUG = True

    logger.debug('Sub process tries to show systray icon, '
                 f'called with args {str(sys.argv)}')

    QtSysTrayIcon().run()
