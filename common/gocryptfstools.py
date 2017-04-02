#    Copyright (C) 2017 Germar Reitze
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
import subprocess
from gettext import gettext

import logger
import tools
from password_ipc import TempPasswordThread
from mount import MountControl
from exceptions import MountException

_ = gettext

class GoCryptFS_mount(MountControl):
    """
    """
    def __init__(self, *args, **kwargs):
        super(GoCryptFS_mount, self).__init__(*args, **kwargs)

        self.setattrKwargs('path', self.config.localEncfsPath(self.profile_id), **kwargs)
        self.setattrKwargs('reverse', False, **kwargs)
        self.setattrKwargs('password', None, store = False, **kwargs)

        self.setDefaultArgs()

        self.mountproc = 'gocryptfs'
        self.log_command = '%s: %s' % (self.mode, self.path)
        self.symlink_subfolder = None

    def _mount(self):
        """
        mount the service
        """
        if self.password is None:
            self.password = self.config.password(self.parent, self.profile_id, self.mode)
        logger.debug('Provide password through temp FIFO', self)
        thread = TempPasswordThread(self.password)
        env = os.environ.copy()
        env['ASKPASS_TEMP'] = thread.temp_file

        with thread.starter():
            gocryptfs = [self.mountproc, '-extpass', 'backintime-askpass']
            if self.reverse:
                gocryptfs += ['-reverse']
            gocryptfs += [self.path, self.currentMountpoint]
            logger.debug('Call mount command: %s'
                         %' '.join(gocryptfs),
                         self)

            proc = subprocess.Popen(gocryptfs, env = env,
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.STDOUT,
                                    universal_newlines = True)
            output = proc.communicate()[0]
            #### self.backupConfig()
            if proc.returncode:
                raise MountException(_('Can\'t mount \'%(command)s\':\n\n%(error)s') \
                                        % {'command': ' '.join(gocryptfs), 'error': output})

    def init(self):
        """
        init the cipher path
        """
        if self.password is None:
            self.password = self.config.password(self.parent, self.profile_id, self.mode)
        logger.debug('Provide password through temp FIFO', self)
        thread = TempPasswordThread(self.password)
        env = os.environ.copy()
        env['ASKPASS_TEMP'] = thread.temp_file

        with thread.starter():
            gocryptfs = [self.mountproc, '-extpass', 'backintime-askpass']
            gocryptfs.append('-init')
            gocryptfs.append(self.path)
            logger.debug('Call command: %s'
                         %' '.join(gocryptfs),
                         self)

            proc = subprocess.Popen(gocryptfs, env = env,
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.STDOUT,
                                    universal_newlines = True)
            output = proc.communicate()[0]
            #### self.backupConfig()
            if proc.returncode:
                raise MountException(_('Can\'t init encrypted path \'%(command)s\':\n\n%(error)s') \
                                        % {'command': ' '.join(gocryptfs), 'error': output})

    def preMountCheck(self, first_run = False):
        """
        check what ever conditions must be given for the mount
        """
        self.checkFuse()
        if first_run:
            pass
        return True
