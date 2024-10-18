# SPDX-FileCopyrightText: © 2017 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.

import os
import subprocess

import logger
import tools
from password_ipc import TempPasswordThread
from mount import MountControl
from exceptions import MountException


class GoCryptFS_mount(MountControl):
    """
    """
    def __init__(self, *args, **kwargs):
        super(GoCryptFS_mount, self).__init__(*args, **kwargs)

        self.setattrKwargs('path', self.config.localGocryptfsPath(self.profile_id), **kwargs)
        self.setattrKwargs('reverse', False, **kwargs)
        self.setattrKwargs('password', None, store = False, **kwargs)
        self.setattrKwargs('config_path', None, **kwargs)

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
            gocryptfs = [self.mountproc, '-extpass', 'backintime-askpass', '-quiet']
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
            logger.debug('Call command to create gocryptfs config file: %s'
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

    def configFile(self):
        """
        return gocryptfs config file
        """
        f = 'gocryptfs.conf'
        if self.config_path is None:
            cfg = os.path.join(self.path, f)
        else:
            cfg = os.path.join(self.config_path, f)
        return cfg

    def isConfigured(self):
        """
        Check if `gocryptfs.conf` exists.
        """
        conf = self.configFile()
        ret = os.path.exists(conf)
        if ret:
            logger.debug('Found gocryptfs config file in {}'.format(conf), self)
        else:
            logger.debug('No config in {}'.format(conf), self)
        return ret
