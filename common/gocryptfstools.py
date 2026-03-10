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
import sshtools
import logger
import config
from password_ipc import TempPasswordThread
from mount import MountControl
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
            if not os.path.isdir(self.path):
                os.makedirs(self.path, exist_ok=True)

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


class Gocryptfs_SSH(GocryptfsMount):
    """
    Mount encrypted remote path with sshfs and gocryptfs.

    Flow:
    1. sshfs mounts remote encrypted directory
    2. gocryptfs mounts that directory as plaintext
    rsync works on plaintext view.
    """

    def __init__(
            self,
            cfg=None,
            profile_id=None,
            mode=None,
            parent=None,
            *args,
            **kwargs
    ):
        # DEBUG
        print(f'Gocryptfs_SSH.__init__() :: {mode=} {parent=} '
              f'{args=} {kwargs=}')

        self.config = cfg or config.Config()
        self.profile_id = profile_id or self.config.currentProfile()
        self.mode = mode or self.config.snapshotsMode(self.profile_id)
        self.parent = parent
        self.args = args
        self.kwargs = kwargs

        self.ssh = sshtools.SSH(
            *self.args,
            symlink=False,
            **self.splitKwargs('ssh')
        )

        super().__init__(
            *self.args,
            symlink=False,
            **self.splitKwargs('gocryptfs')
        )

        # print('3'*100)  # DEBUG
        # if not self.isConfigured():
        #     print('4'*100)  # DEBUG
        #     self.init_backend()
        # print('5'*100)  # DEBUG

    def mount(self, *args, **kwargs):
        # SSH mount
        self.ssh.mount(*args, **kwargs)

        cipher_path = self.ssh.currentMountpoint
        self.path = cipher_path

        conf_fp = Path(cipher_path) / 'gocryptfs.conf'
        if not conf_fp.exists():
            if not any(Path(cipher_path).iterdir()):
                self.init_backend()

        # gocryptfs mount
        gocrypt_kwargs = self.splitKwargs('gocryptfs')
        gocrypt_kwargs['check'] = False

        return super().mount(**gocrypt_kwargs)

    def umount(self, *args, **kwargs):
        # gocryptfs
        super().umount(*args, **kwargs)

        # SSH mount
        self.ssh.umount(*args, **kwargs)

    def preMountCheck(self, *args, **kwargs):
        return (
            self.ssh.preMountCheck(*args, **kwargs)
            and super().preMountCheck(*args, **kwargs)
        )

    def isConfigured(self):
        """Checks if cogryptfs.conf exists on the mounted SSH path"""
        print("SSH MP:", self.ssh.currentMountpoint)
        print("PATH:", self.path)
        print("CHECK:", self.configFile())
        print("EXISTS:", Path(self.configFile()).exists())
        if self.ssh.currentMountpoint is None:
            return False

        self.path = self.ssh.currentMountpoint

        return super().isConfigured()

    def splitKwargs(self, mode: str) -> dict:
        """Split kwargs into backend-specific kwargs.

        Args:
            mode: 'ssh' or 'gocryptfs'

        Returns:
            dict: Filtered and adapted arguments for one of the selected
                backends.
        """
        d = self.kwargs.copy()

        d['cfg'] = self.config
        d['profile_id'] = self.profile_id
        d['mode'] = self.mode
        d['parent'] = self.parent

        if mode == 'ssh':
            if 'path' in d:
                d.pop('path')
            if 'ssh_path' in d:
                d['path'] = d.pop('ssh_path')
            d['password'] = d.pop(
                'ssh_password',
                self.config.password(
                    parent=self.parent,
                    profile_id=self.profile_id,
                    mode=self.mode
                )
            )

            return d

        elif mode == 'gocryptfs':
            d['path'] = self.ssh.currentMountpoint
            d['password'] = d.pop(
                'gocryptfs_password',
                self.config.password(
                    parent=self.parent,
                    profile_id=self.profile_id,
                    mode=self.mode,
                    pw_id=2
                )
            )

            return d
