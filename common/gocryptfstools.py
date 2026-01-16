# SPDX-FileCopyrightText: © 2017 Germar Reitze
# SPDX-FileCopyrightText: © 2025 David Wales (@daviewales)
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import subprocess

import logger
from password_ipc import TempPasswordThread
from mount import MountControl
from exceptions import MountException


class GocryptfsMount(MountControl):
    """
    """

    def __init__(self, *args, **kwargs):
        super(GocryptfsMount, self).__init__(*args, **kwargs)

        # Workaround for some linters.
        self.path = None
        self.reverse = None
        self.config_path = None

        self.setattrKwargs(
            'path', self.config.localGocryptfsPath(self.profile_id), **kwargs
        )
        self.setattrKwargs('reverse', False, **kwargs)
        self.setattrKwargs('password', None, store=False, **kwargs)
        self.setattrKwargs('config_path', None, **kwargs)

        self.setDefaultArgs()

        self.mountproc = 'gocryptfs'
        self.log_command = f'{self.mode}: {self.path}'
        self.symlink_subfolder = None

    def _mount(self):
        """
        mount the service
        """
        if self.password is None:
            self.password = self.config.password(
                self.parent, self.profile_id, self.mode
            )
        thread = TempPasswordThread(self.password)
        env = os.environ.copy()
        env['ASKPASS_TEMP'] = thread.temp_file

        with thread.starter():
            gocryptfs = [
                self.mountproc,
                '-extpass',
                'backintime-askpass',
                '-quiet'
            ]
            if self.reverse:
                gocryptfs += ['-reverse']

            gocryptfs += [
                self.path,
                self.currentMountpoint
            ]

            logger.debug(f'Call mount command: {gocryptfs}', self)

            proc = subprocess.Popen(
                gocryptfs,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            output = proc.communicate()[0]

            if proc.returncode:
                msg = _('Unable to mount "{command}"').format(
                    command=' '.join(gocryptfs)
                )
                raise MountException(
                    f'{msg}:\n\n{output}\n\nReturn code: {proc.returncode}'
                )

    def init_backend(self):
        """
        init the cipher path
        """
        if self.password is None:
            self.password = self.config.password(
                self.parent, self.profile_id, self.mode)

        # Dev note: See docstring in EncFS_mount._mount() for detailed
        # description about the password thing.
        thread = TempPasswordThread(self.password)
        env = os.environ.copy()
        env['ASKPASS_TEMP'] = thread.temp_file

        with thread.starter():
            gocryptfs = [
                self.mountproc,
                '-extpass',
                'backintime-askpass']

            gocryptfs.append('-init')

            gocryptfs.append(self.path)

            logger.debug(
                f'Call command to create gocryptfs config file: {gocryptfs}',
                self
            )

            proc = subprocess.Popen(
                gocryptfs,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True)

            output = proc.communicate()[0]

            if proc.returncode:
                msg = _('Unable to init encrypted path "{command}"').format(
                    command=' '.join(gocryptfs)
                )
                raise MountException(
                    f'{msg}:\n\n{output}\n\nReturn code: {proc.returncode}'
                )

    def preMountCheck(self, first_run=False):
        """
        check what ever conditions must be given for the mount
        """
        self.checkFuse()

        if first_run:
            pass

        return True

    def configFile(self) -> str:
        """Full path of gocryptfs config file"""
        fn = 'gocryptfs.conf'

        if self.config_path is None:
            cfg = os.path.join(self.path, fn)
        else:
            cfg = os.path.join(self.config_path, fn)

        return cfg

