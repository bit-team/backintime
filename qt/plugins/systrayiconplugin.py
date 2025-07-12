# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.

# TODO Known open issues:
# this script should get started and consider some cmd line arguments from BiT
# (parsed via backintime.createParsers()) so that the same paths are used,
# mainly "share-path" and "config" (path to the config file).
# Otherwise e.g. unit tests or special user path settings may lead to
# wrong status info in the systray icon!

import sys
import os
import pluginmanager
import tools
import logger
import gettext
import subprocess


_ = gettext.gettext


if not os.getenv('DISPLAY', ''):
    os.putenv('DISPLAY', ':0.0')


class SysTrayIconPlugin(pluginmanager.Plugin):
    def __init__(self):
        self.process = None
        self.snapshots = None

    def init(self, snapshots):
        self.snapshots = snapshots

        # Old implementation disabled:
        # Why can a systray icon only be shown on X11 (not wayland)?
        # Qt can handle wayland now!
        #    if not tools.checkXServer():
        #        return False

        # New implementation: Let Qt decide if a system tray icon can be shown.
        # See https://doc.qt.io/qt-5/qsystemtrayicon.html#details:
        # > To check whether a system tray is present on the user's desktop,
        # > call the QSystemTrayIcon::isSystemTrayAvailable() static function.
        #
        # This requires a QApplication instance (otherwise Qt causes a
        # segfault) which we don't have here so we create it to check if a
        # window manager ("GUI") is active at all (e.g. in headless
        # installations it isn't).
        # See: https://forum.qt.io/topic/3852/issystemtrayavailable-
        # always-crashes-segfault-on-ubuntu-10-10-desktop/6

        try:

            if tools.is_Qt_working(systray_required=True):
                logger.debug('System tray is available to show the '
                             'BIT system tray icon')
                return True

        except Exception as exc:
            logger.debug(
                f'Could not ask Qt if system tray is available: {repr(exc)}')

        logger.debug(
            'No system tray available to show the BIT system tray icon')
        return False

    def isGui(self):
        return True

    def processBegin(self):
        try:
            logger.debug('Trying to start systray icon sub process...')
            path = os.path.join(
                tools.as_backintime_path('qt'), 'qtsystrayicon.py')
            cmd = [
                sys.executable,
                path,
                self.snapshots.config.currentProfile()
            ]

            if logger.DEBUG:
                # HACK to propagate DEBUG logging level to sub process
                cmd.append('--debug')

            self.process = subprocess.Popen(cmd)

        except Exception as exc:
            logger.critical(f'Undefined situation: {exc}', self)

    def processEnd(self):
        """Dev note(2025-07, buhtz): Method makes no sense to me anymore.
        Remove it soon.
        """
        if self.process is not None:
            try:
                # The "qtsystrayicon.py" app does terminate itself
                # once the snapshot has been taken so there is no need
                # to do anything here to stop it or clean-up anything.
                # self.process.terminate()
                return

            # ???
            except:
                pass
