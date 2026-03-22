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
import logger
from password_ipc import TempPasswordThread


class Encryptor:

    class Type(Enum):
        NONE = auto()
        GOCRYPTFS = auto()

    TYPE = None

    def __init__(self, cfg):
        self.cfg = cfg

    def get_fingerprint_base(self) -> str:
        raise NotImplementedError

    def is_initialized(self) -> bool:
        return True

    def initialize(self):
        raise NotImplementedError


class NoEncryption(Encryptor):
    TYPE = Encryptor.Type.NONE

    def get_fingerprint_base(self) -> str:
        return str(self.TYPE) + ': '

    def mount(*args, **kwargs):
        pass

    def umount(*args, **kwargs):
        pass


class GoCryptFS(Encryptor):
    TYPE = Encryptor.Type.GOCRYPTFS

    def __init__(self, cfg, backend):
        super().__init__(cfg)

        self.path = self.cfg.localGocryptfsPath()
        self.plain_path = backend.path

        logger.debug(
            f'GoCryptFS.__init__() :: {self.path=} {self.plain_path=}', self
        )

        self.password = None

    def is_initialized(self) -> bool:
        cfg_fp = self.path / 'gocryptfs.conf'

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

            cmd.append(self.path)

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
                msg = _('Unable to init encrypted path "{command}"').format(
                    command=' '.join(cmd)
                )
                msg = f'{msg}:\n\n{output}\n\nReturn code: {proc.returncode}'
                logger.critical(msg, self)

                raise RuntimeError(msg)

    def mount(self):
        if self.password is None:
            self.password = self.config.password()

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
                self.path,
                self.plain_path
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
                raise RuntimeError(
                    f'{msg}:\n\n{output}\n\nReturn code: {proc.returncode}'
                )

    def umount(self):
        cmd = [
            'fusermount',
            '-u',
            self.plain_path
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if proc.returncode:
            msg = f'Unable to unmount {self.plain_path}:\n{proc.stdout}'
            logger.error(msg)

            raise RuntimeError(msg)
