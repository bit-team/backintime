# SPDX-FileCopyrightText: © 2017 Germar Reitze
# SPDX-FileCopyrightText: © 2025 David Wales (@daviewales)
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import subprocess

from pathlib import Path
import logger
from password_ipc import TempPasswordThread
from mountold import MountControl
from exceptions import MountException


class GocryptfsMount(MountControl):
    """Mounts a local GoCryptFS encrypted directory.

    After mounting the dir is accessible in plaintext (encrypted).
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
        """init the cipher path"""

        self.checkFuse()  # gocryptfs binary available?

        if self.password is None:
            self.password = self.config.password(
                self.parent, self.profile_id, self.mode)

        # Dev note: See docstring in EncFS_mount._mount() for detailed
        # description about the password thing.
        thread = TempPasswordThread(self.password)
        env = os.environ.copy()
        env['ASKPASS_TEMP'] = thread.temp_file

        with thread.starter():
            # if not os.path.isdir(self.path):
            #     os.makedirs(self.path, exist_ok=True)

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
                msg = f'{msg}:\n\n{output}\n\nReturn code: {proc.returncode}'
                logger.critical(msg, self)
                raise MountException(msg)

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
            return os.path.join(self.path, fn)

        return os.path.join(self.config_path, fn)

    def isConfigured(self) -> bool:
        """Check if `gocryptfs.conf` exists."""
        fp_conf = Path(self.configFile())

        if fp_conf.exists():
            logger.debug(f'Found gocryptfs config file in {fp_conf}', self)
            return True

        logger.debug(f'No gocryptfs config found. Missing {fp_conf}', self)

        return False
