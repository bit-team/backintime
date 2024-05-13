#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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

# Jan 23, 2023: This file was named "qt4plugin.py" until now
#               and renamed to better indicate the purpose
#               (and qt4 is no longer valid - we are using qt5 now for long).
#               The old class name "QtPlugin" was also renamed to:
#                   SysTrayIconPlugin

# TODO Known open issues:
# - this script should get started and consider some cmd line arguments from BiT
#   (parsed via backintime.createParsers()) so that the same paths are used,
#   mainly "share-path" and "config" (path to the config file).
#   Otherwise e.g. unit tests or special user path settings may lead to
#   wrong status info in the systray icon!

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
        # This requires a QApplication instance (otherwise Qt causes a segfault)
        # which we don't have here so we create it to check if a window manager
        # ("GUI") is active at all (e.g. in headless installations it isn't).
        # See: https://forum.qt.io/topic/3852/issystemtrayavailable-always-crashes-segfault-on-ubuntu-10-10-desktop/6

        try:

            if tools.is_Qt_working(systray_required=True):
                logger.debug("System tray is available to show the BiT system tray icon")
                return True

        except Exception as e:
            logger.debug(f"Could not ask Qt if system tray is available: {repr(e)}")

        logger.debug("No system tray available to show the BiT system tray icon")
        return False

    def isGui(self):
        return True

    def processBegin(self):
        try:
            logger.debug("Trying to start systray icon sub process...")
            path = os.path.join(tools.backintimePath('qt'), 'qtsystrayicon.py')
            cmd = [sys.executable, path, self.snapshots.config.currentProfile()]
            if logger.DEBUG:
                cmd.append("--debug")  # HACK to propagate DEBUG logging level to sub process
            self.process = subprocess.Popen(cmd)
            # self.process = subprocess.Popen([sys.executable, path, self.snapshots.config.currentProfile()])
        except:
            pass

    def processEnd(self):
        if not self.process is None:
            try:
                # The "qtsystrayicon.py" app does terminate itself
                # once the snapshot has been taken so there is no need
                # to do anything here to stop it or clean-up anything.
                # self.process.terminate()
                return
            except:
                pass
