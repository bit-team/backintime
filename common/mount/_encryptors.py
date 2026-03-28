# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import json
import hashlib
import subprocess
from enum import Enum, auto
from pathlib import Path
import logger
import tools
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

    @property
    def fingerprint(self) -> str:
        """Compute a unique mount fingerprint.

        The fingerprint is a deterministic hex string and based on the
        encryptors configuration parameters and the backend.  It serves as a
        stable identifier for mountpoints, allowing mounts with identical
        configurations to be recognized and potentially reused across
        processes.

        Returns:
            A SHA256 hash cut to a 12-character hexadecimal string.

        """
        data = '|'.join([
            self._backend.get_fingerprint_base(),
            self.get_fingerprint_base()
        ])
        return hashlib.sha256(data.encode()).hexdigest()[:12]

    @property
    def mount_root(self) -> Path:
        return self._backend.mount_root

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

    def __init__(self, cfg, backend):
        super().__init__(cfg, backend)
        self.path = self._backend.path

    def get_fingerprint_base(self) -> str:
        return str(self.TYPE) + ': '

    def validate(self):
        pass

    def mount(*args, **kwargs):
        pass

    def umount(*args, **kwargs):
        pass


class GoCryptFS(Encryptor):
    """GoCryptFS for encrypted backups.

    This encryptor manages mounting and unmounting of encrypted storage, and
    therefor handles temporary decrypted view for user or backup operations.

    Path mapping in this implementation with example:

        Assuming `backend.path` points to ``/home/user/ziel``. That is the
        the user-specified backup target. It is not human readable. The
        directory contains encrypted data and gocryptfs.conf.

        The parameter `encryptor.cipher_path` is identical to `backend.path`
        and points to the same directory. GoCryptFS will use it for mounting.

        The parameter `encryptor.path` is the mountpoint and decrypted view.
        E.g., ``/home/user/.zieltmp``. Human-readable files are accessible
        here during backup.
    """

    TYPE = Encryptor.Type.GOCRYPTFS

    def __init__(self, cfg, backend):
        super().__init__(cfg, backend)

        # the decrypted (human readable) view of "plain_path"
        # mount_root + hash_id/fingerpint + 'mountpoint'
        # e.g. `~/.local/share/backintime/mnt/<hash_id>/mountpoint`
        self.path = self.mount_root / self.fingerprint / 'mountpoint'
        self.path.mkdir(parents=True, exist_ok=True)

        logger.debug(f'{self.path=} {self.cipher_path=}', self)

        self.password = None

    @property
    def cipher_path(self) -> Path:
        """The encrypted path that will be the mount target.

        Gogryptfs does mount that path and decrypt it while mounting.
        """
        return self._backend.path

    def get_fingerprint_base(self) -> str:
        return str(self.TYPE) + f': {self.cipher_path}'

    def is_initialized(self) -> bool:
        cfg_fp = self.cipher_path / 'gocryptfs.conf'

        if not cfg_fp.is_file():
            return False

        try:
            content = cfg_fp.read_text('utf-8')
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
            self.password = self.cfg.password()

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
                msg = _('Unable to initialize encryption via "{command}"').format(
                    command=cmd
                )
                msg = f'{msg}:\n\n{output}\n\nReturn code: {proc.returncode}'
                logger.critical(msg, self)

                raise MountError(msg, path=self.cipher_path)

    def validate(self):
        """Check if encryption setup is ready to get mounted.

        Raises: MountError
        """
        if not self.is_initialized():
            raise MountError(
                _('Backup destination directory is not '
                  'prepared for encryption.'),
                path=self.cipher_path
            )

        if not self.path.exists():
            raise MountError(
                'Mointpoint as decrypted view is missing.',
                path=self.path
            )

    def mount(self):
        """Mount

        Raises: MountError
        """
        if tools.is_mounted(self.path):
            logger.debug(
                f'Mountpoint {self.path.relative_to(self.mount_root)} is '
                'already mounted',
                self
            )
            return

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
                    command=cmd
                )
                raise MountError(
                    f'{msg}:\n\n{output}\n\nReturn code: {proc.returncode}',
                )

        logger.info(
            'Mounted (and decrypted) encrypted directory '
            f'"{self.cipher_path}" to "{self.path}"')

    def umount(self):
        """Release the mountpoint.

        Nothing happens if not mounted.

        Raises: MountError
        """
        if not tools.is_mounted(self.path):
            logger.debug(f'Is not mounted. {self.path}', self)
            return

        proc = subprocess.run(
            ['fusermount', '-u', self.path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if proc.returncode:
            msg = f'Unable to umount {self.path}:\n{proc.stdout}'
            logger.error(msg)

            raise MountError(msg)
