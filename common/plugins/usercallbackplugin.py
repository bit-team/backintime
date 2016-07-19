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


import os
import pluginmanager
import logger
import gettext
from subprocess import Popen, PIPE
from exceptions import StopException

_=gettext.gettext


class UserCallbackPlugin( pluginmanager.Plugin ):
    def __init__( self ):
        return

    def init( self, snapshots ):
        self.config = snapshots.config
        self.callback = self.config.takeSnapshotUserCallback()
        if not os.path.exists( self.callback ):
            return False
        return True

    def callback(self, *args):
        cmd = [self.callback, self.config.currentProfile(), self.config.profileName()]
        cmd.extend([str(x) for x in args])
        logger.debug('Call user-callback: %s' %' '.join(cmd), self)
        if self.config.userCallbackNoLogging():
            stdout, stderr = None, None
        else:
            stdout, stderr = PIPE, PIPE
        try:
            callback = Popen(cmd,
                             stdout = stdout,
                             stderr = stderr,
                             universal_newlines = True)
            output = callback.communicate()
            if output[0]:
                logger.info('user-callback returned \'%s\'' %output[0].strip('\n'), self)
            if output[1]:
                logger.error('user-callback returned \'%s\'' %output[1].strip('\n'), self)
            if callback.returncode != 0:
                logger.warning('user-callback returncode: %s' %callback.returncode, self)
                raise StopException()
        except OSError as e:
            logger.error("Exception when trying to run user callback: %s" % e.strerror, self)

    def processBegin(self):
        self.callback('1')

    def processEnd(self):
        self.callback('2')

    def error(self, code, message):
        if not message:
            self.callback('4', code)
        else:
            self.callback('4', code, message)

    def newSnapshot(self, snapshot_id, snapshot_path):
        self.callback('3', snapshot_id, snapshot_path)

    def appStart(self):
        self.callback('5')

    def appExit(self):
        self.callback('6')

    def mount(self):
        self.callback('7')

    def unmount(self):
        self.callback('8')
