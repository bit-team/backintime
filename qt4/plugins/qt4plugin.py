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


import sys
import os
import pluginmanager
import tools
import logger
import time
import gettext
import _thread
import subprocess


_=gettext.gettext


if not os.getenv('DISPLAY', ''):
    os.putenv('DISPLAY', ':0.0')


class Qt4Plugin(pluginmanager.Plugin):
    def __init__(self):
        self.process = None
        self.snapshots = None

    def init(self, snapshots):
        self.snapshots = snapshots

        if not tools.checkXServer():
            return False
        return True

    def isGui(self):
        return True

    def processBegin(self):
        try:
            path = os.path.join(tools.backintimePath('qt4'), 'qt4systrayicon.py')
            self.process = subprocess.Popen([sys.executable, path, self.snapshots.config.currentProfile()])
        except:
            pass

    def processEnd(self):
        if not self.process is None:
            try:
                #self.process.terminate()
                return
            except:
                pass
