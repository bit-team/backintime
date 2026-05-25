# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Encryption subsystem related to mounting"""
import os
import json
import subprocess
from enum import Enum, auto
from pathlib import Path
import logger
import tools
from password_ipc import TempPasswordThread
from ._error import MountError


class Encryptor:
    """Base class for encryption"""

    class Type(Enum):
        """Supported encryptor types"""
        NONE = auto()
        GOCRYPTFS = auto()

    TYPE = None

    def __init__(self, cfg, backend):
        self.cfg = cfg
        self._backend = backend

    def setup(self):
        """Called by the mount manager after setting up the backend."""
        raise NotImplementedError

    def get_fingerprint_base(self) -> str:
        """Return encryptor-specific string for fingerprint calculation."""
        raise NotImplementedError

    @property
    def fingerprint(self) -> str:
        """See `MountManager.fingerprint`"""
        return self._backend.fingerprint

    @property
    def mount_root(self) -> Path:
        """See ``Backend.mount_root``"""
        return self._backend.mount_root

    def is_initialized(self) -> bool:
        """Check if the encryptor is initialized."""
        return True

    def initialize(self):
        """Perform encryptor-specific initialization."""
        raise NotImplementedError

    def validate(self):
        """See ``Backend.validate``"""
        raise NotImplementedError

    def mount(self):
        """See ``Backend.mount``"""
        raise NotImplementedError

    def umount(self):
        """See ``Backend.umount``"""
        raise NotImplementedError


class NoEncryption(Encryptor):
    """No encryption"""
    TYPE = Encryptor.Type.NONE

    def __init__(self, cfg, backend):
        super().__init__(cfg, backend)
        self.path = None

    def setup(self):
        """See ``Encryptor.setup()``"""
        self.path = self._backend.path

    def get_fingerprint_base(self) -> str:
        return str(self.TYPE) + ': '

    def initialize(self):
        """See ``Encryptor.initialize()``"""

    def validate(self):
        """See ``Encryptor.validate()``"""

    def mount(self):
        """See ``Encryptor.mount()``"""

    def umount(self):
        """See ``Encryptor.umount()``"""


class GoCryptFS(Encryptor):
    """GoCryptFS for encrypted backups.

    This encryptor manages mounting and unmounting of encrypted storage, and
    therefore handles temporary decrypted view for user or backup operations.

    Path mapping in this implementation with example:

        Assuming `backend.path` points to ``/home/user/ziel``. That is the
        the user-specified backup target. It is not human readable. The
        directory contains encrypted data and gocryptfs.conf.

        The parameter `encryptor.cipher_path` is identical to `backend.path`
        and points to the same directory. GoCryptFS will use it for mounting.

        The parameter `encryptor.path` is the mountpoint and decrypted view.
        E.g., ``~/.local/share/backintime/mnt/<fp>/mountpoint/``.
        Human-readable files are accessible here during backup.
    """

    TYPE = Encryptor.Type.GOCRYPTFS

    def __init__(self, cfg, backend):
        super().__init__(cfg, backend)

        # the decrypted (human readable) view of "plain_path"
        # mount_root + hash_id/fingerprint + 'mountpoint'
        # e.g. `~/.local/share/backintime/mnt/<hash_id>/mountpoint`
        self.path = None
        self.password = None

    def setup(self):
        """See ``Encryptor.setup()``"""
        self.path = self.mount_root / self.fingerprint / 'mountpoint'
        self.path.mkdir(parents=True, exist_ok=True)
        logger.debug(f'mkdir() {self.path=}')

    @property
    def cipher_path(self) -> Path:
        """The encrypted path that will be the mount target.

        Gogryptfs does mount that path and decrypt it while mounting.
        """
        return self._backend.path

    def get_fingerprint_base(self) -> str:
        return str(self.TYPE) + f': {self.cipher_path}'

    def is_initialized(self) -> bool:
        """See ``Encryptor.is_initialized()``"""
        cfg_fp = self.cipher_path / 'gocryptfs.conf'

        if not cfg_fp.is_file():
            return False

        try:
            content = cfg_fp.read_text('utf-8')
            json.loads(content)

        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                'Unexpected problem while reading gocryptfs '
                f'config file. {exc=}'
            )
            return False

        return True

    def _ensure_password(self):
        """Make sure that a password is known to the encryptor."""
        if self.password:
            return

        self.password = self.cfg.get_encryption_password()

    def _ensure_cipher_dir_empty_for_init(self):
        try:
            next(self.cipher_path.iterdir())
        except StopIteration:
            # it is empty
            return

        log_msg = (
            f'gocryptfs init blocked: cipherdir not empty: {self.cipher_path}'
        )

        gui_msg = (
            _('Cannot initialize encryption because the backup '
              'destination is not empty.')
            + '\n\n'
            + _('Remove existing files or choose an empty directory.')
        )

        raise MountError(log_msg, gui_msg)

    def _ensure_runtime(self):
        """Raise error if gocryptfs is not available.

        This is a workaround.
        """
        tool = 'gocryptfs'
        if tools.which(tool):
            return

        log_msg = f'Dependency "{tool}" not found'

        gui_msg = _(
            'Required tool "{tool}" is not installed or not available.'
        ).format(tool=tool) + '\n\n' \
        + _('Please install it and try again.')

        raise MountError(log_msg, gui_msg)

    def initialize(self):
        """See ``Encryptor.initialized()``"""

        self._ensure_runtime()

        self._ensure_cipher_dir_empty_for_init()

        self._ensure_password()

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

            with subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            ) as proc:

                output = proc.communicate()[0]
                output = output.strip()

                if proc.returncode:
                    log_msg = f'Unable to initialize encryption via "{cmd}"'
                    log_msg = f'{log_msg} | {output} '
                    log_msg = f'{log_msg} | Return code: {proc.returncode}'
                    logger.critical(log_msg)

                    gui_msg = (
                        _('Unable to initialize encryption.')
                        + '\n\n' + _('Details:')
                        + f'\nrc: {proc.returncode}\n{output}\n{cmd}'
                    )

                    raise MountError(log_msg, gui_msg)

    def validate(self):
        """Check if encryption setup is ready to get mounted.

        Raises: MountError
        """
        if not self.is_initialized():
            log_msg = 'Backup destination not prepared for ' \
                f'encryption: {self.cipher_path}'
            gui_msg = _(
                'Backup destination directory is not prepared for encryption. '
                'Path: {path}'
            ).format(path=self.cipher_path)

            raise MountError(log_msg, gui_msg)

        if not self.path.exists():
            log_msg = f'Mointpoint (as decrypted view) missing: {self.path}'
            gui_msg = _(
                'Mointpoint as decrypted view is missing. Path: {path}'
            ).format(path=self.path)
            raise MountError(log_msg, gui_msg)

    def mount(self):
        """Mount

        Raises: MountError
        """
        if tools.is_mounted(self.path):
            logger.info(
                'Encrypted directory already mounted '
                f'(source: "{self.cipher_path}" -> target: "{self.path}")'
            )
            return

        self._ensure_password()

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
            with subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            ) as proc:
                output = proc.communicate()[0]

                if proc.returncode != 0:
                    log_msg = f'Mount failed via "{cmd}"'
                    log_msg = f'{log_msg} | {output}'
                    log_msg = f'{log_msg} | Return code: {proc.returncode}'
                    logger.critical(log_msg)

                    gui_msg = (
                        _('Mount failed with return code {rc}.').format(
                            rc=proc.returncode
                        ) + '\n\n'
                        + _('Error:') + f'\n{output}'
                        + _('Command:') + f'\n{cmd}'
                    )
                    raise MountError(log_msg, gui_msg)

        logger.info(
            'Encrypted directory mounted '
            f'(source: "{self.cipher_path}" -> target: "{self.path}")')

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
            text=True,
            check=False
        )

        if proc.returncode != 0:
            log_msg = f'Unmount failed. | {proc.stdout} | {proc.returncode}'
            logger.error(log_msg)
            gui_msg = (
                _('Unmount failed')
                + '\n'
                + _('Return code: {rc}').format(rc=proc.returncode)
                + _('Original error: {err}').format(err=proc.stdout)
            )
            raise MountError(log_msg, gui_msg)

        logger.info(
            'Encrypted directory unmounted '
            f'(source: "{self.cipher_path}" -> target: "{self.path}")'
        )
