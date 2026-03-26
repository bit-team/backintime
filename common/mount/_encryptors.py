# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import json
import subprocess
from enum import Enum, auto
from pathlib import Path
import logger
from password_ipc import TempPasswordThread
from ._error import MountError


class Encryptor:

    class Type(Enum):
        NONE = auto()
        GOCRYPTFS = auto()

    TYPE = None

    def __init__(self, cfg, backend):
        self.cfg = cfg
        self._backend = backend

    def get_fingerprint_base(self) -> str:
        raise NotImplementedError

    def is_initialized(self) -> bool:
        return True

    def initialize(self):
        raise NotImplementedError

    def validate(self):
        raise NotImplementedError

    def mount(self):
        raise NotImplementedError

    def umount(self):
        raise NotImplementedError


class NoEncryption(Encryptor):
    TYPE = Encryptor.Type.NONE

    def get_fingerprint_base(self) -> str:
        return str(self.TYPE) + ': '

    def validate(self):
        pass

    def mount(*args, **kwargs):
        pass

    def umount(*args, **kwargs):
        pass


class GoCryptFS(Encryptor):
    TYPE = Encryptor.Type.GOCRYPTFS

    def __init__(self, cfg, backend):
        super().__init__(cfg, backend)

        # the decrypted (human readable) view of "plain_path"
        self.path = self.cfg.localGocryptfsPath()

        logger.debug(f'{self.path=} {self.cipher_path=}', self)

        self.password = None

    @property
    def cipher_path(self) -> Path:
        """The encrypted path that will be the mount target.

        Gogryptfs does mount that path and decrypt it while mounting.
        """
        return self._backend.path

    def get_fingerprint_base(self) -> str:
        return str(self.TYPE) + f': {self.path} {self.cipher_path}'

    def is_initialized(self) -> bool:
        cfg_fp = self.cipher_path / 'gocryptfs.conf'

        if not cfg_fp.is_file():
            return False

        try:
            content = cfg_fp.read_text('r', encoding='utf-8')
            json.loads(content)

        except Exception as exc:
            logger.debug(
                'Unexpected problem while reading gocryptfs '
                f'config file. {exc=}'
            )
            return False

        return True

    def initialize(self):
        if self.password is None:
            self.password = self.config.password()

        # Dev note: See docstring in EncFS_mount._mount() for detailed
        # description about the password thing.
        thread = TempPasswordThread(self.password)
        env = os.environ.copy()
        env['ASKPASS_TEMP'] = thread.temp_file

        with thread.starter():
            cmd = [
                'gocryptfs',
                '-extpass',
                'backintime-askpass']

            cmd.append('-init')

            cmd.append(self.cipher_path)

            logger.debug(
                f'Call command to create gocryptfs config file: {cmd}',
                self
            )

            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True)

            output = proc.communicate()[0]

            if proc.returncode:
                msg = _('Unable to initialize encryption. "{command}"').format(
                    command=' '.join(cmd)
                )
                msg = f'{msg}:\n\n{output}\n\nReturn code: {proc.returncode}'
                logger.critical(msg, self)

                raise MountError(msg, path=self.cipher_path)

    def validate(self):
        if not self.is_initialized():
            raise MountError(
                _('Backup destination directory is not '
                  'prepared for encryption.'),
                path=self.cipher_path
            )

    def mount(self):
        if self.password is None:
            self.password = self.cfg.password()

        thread = TempPasswordThread(self.password)
        env = os.environ.copy()
        env['ASKPASS_TEMP'] = thread.temp_file

        with thread.starter():
            cmd = [
                'gocryptfs',
                '-extpass',
                'backintime-askpass',
                '-quiet'
            ]

            cmd += [
                self.cipher_path,
                self.path,
            ]

            logger.debug(f'Call mount command: {cmd}', self)
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            output = proc.communicate()[0]

            if proc.returncode:
                msg = _('Unable to mount via "{command}"').format(
                    command=' '.join(cmd)
                )
                raise MountError(
                    f'{msg}:\n\n{output}\n\nReturn code: {proc.returncode}',
                )

    def umount(self):
        cmd = [
            'fusermount',
            '-u',
            self.cipher_path
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if proc.returncode:
            msg = f'Unable to umount {self.plain_path}:\n{proc.stdout}'
            logger.error(msg)

            raise MountError(msg)
