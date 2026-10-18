# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""An interim module offering features around gocryptfs profiles.

Dev note (buhtz, 2026-10):
Code will refactored and restructered later, after I figured out how this
should work.
"""
import json
import os
from pathlib import Path
import subprocess
import logger
from mount import MountError
from password_ipc import TempPasswordThread
from sshcore import SSHHost
import tools


class BackupSource:
    """The source endpoint of a backup.

    """
    def __init__(self, path: Path):

        # The original source path. In mode "local encrypted" it is the not
        # encrypted.
        self._source_path = path

        # The (reverse mounted) encrypted view of the original source path
        self._encrypted_path = None

        self._source_path.mkdir(parents=True, exist_ok=True)

    def create_encrypted_view(self,
                              backup_destination: BackupDestination) -> Path:
        """
        """

class BackupDestination:
    """The destination endpoint of a backup.

    """
    def __init__(self,
                 path: Path,
                 gocrypt_password: str | None,
                 ssh_host: SSHHost | None = None):
        # The original destination path. In mode "local encrypted" it is the
        # encrypted path.
        self._destination_path = path

        # Gocryptfs encryption password
        self._gocrypt_password = gocrypt_password

        # In case of "SSH (encrypted)" profile
        self._ssh_host = ssh_host

        # The (forward mounted) decrypted view of the original destination path
        self._decrypted_path = None

    def initialize_if_needed(self):
        """Initialize the destination directory if not still initialized.

        For local encrypted profiles the destination path will be initialized
        for being usable.
        """
        # 1. Initialize the destination dir
        if neo.is_initialized(self._destination_path):
            return

        neo.init_gocryptfs_dir(
            self._destination_path,
            self._gocrypt_password
        )


def init_gocryptfs_dir(path: Path, password: str):

        """Initialize a fresh gocryptfs directory.

    The dir need to be empty. It uses the `-aessiv` option to reuse the config
    for reverse mounts on any other directories.

    Use `Config.get_encryption_password()` to set the `password` argument.
    """

    ensure_runtime()
    ensure_cipher_dir_empty_for_init(path)

    # Dev note: See docstring in EncFS_mount._mount() for detailed
    # description about the password thing.
    thread = TempPasswordThread(password)
    env = os.environ.copy()
    env['ASKPASS_TEMP'] = thread.temp_file

    with thread.starter():
        cmd = [
            'gocryptfs',
            '-extpass',
            'backintime-askpass',
            '-aessiv',
            '-init',
            str(path)
        ]

        logger.debug(f'Calling {cmd}...')
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
                    + '\n\n'
                    + _('Details:')
                    + f'\nrc: {proc.returncode}\n{output}\n{cmd}'
                )

                raise MountError(log_msg, gui_msg)


def ensure_cipher_dir_empty_for_init(path: Path):
    """Checks if the path is emppty.

    Raises: If the dir is not empty.
    """

    try:
        next(path.iterdir())
    except StopIteration:
        # it is empty
        return

    log_msg = f'gocryptfs init blocked: cipherdir not empty: {path}'

    gui_msg = (
        _(
            'Cannot initialize encryption because the backup '
            'destination is not empty.'
        )
        + '\n\n'
        + _('Remove existing files or choose an empty directory.')
    )

    raise MountError(log_msg, gui_msg)


def ensure_runtime():
    """Raise error if gocryptfs is not available.

    This is a workaround.
    """
    tool = 'gocryptfs'

    if tools.which(tool):
        return

    log_msg = f'Dependency "{tool}" not found'

    gui_msg = _(
        'Required tool "{tool}" is not installed or not available.'
    ).format(tool=tool) + '\n\n' + _('Please install it and try again.')

    raise MountError(log_msg, gui_msg)


def is_initialized(path: Path) -> bool:
    cfg_fp = path / 'gocryptfs.conf'

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


def forward_mount_dir(path_to_mount: Path,
                      mountpoint: Path,
                      password: str):
    """Create a decrypted view (forward mount) of `path_to_mount` accessible
    at `mountpoint`.
    """
    thread = TempPasswordThread(password)
    env = os.environ.copy()
    env['ASKPASS_TEMP'] = thread.temp_file

    with thread.starter():
        cmd = [
            'gocryptfs',
            '-extpass',
            'backintime-askpass',
            str(path_to_mount),
            str(mountpoint)
        ]

        logger.debug(f'Calling {cmd}')

        with subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        ) as proc:
            output = proc.communicate()[0]

            if proc.returncode != 0:
                log_msg = f'Forward mount failed via "{cmd}"'
                log_msg = f'{log_msg} | {output}'
                log_msg = f'{log_msg} | Return code: {proc.returncode}'
                logger.critical(log_msg)

                gui_msg = (
                    _('Forward mount failed with return code {rc}.').format(
                        rc=proc.returncode
                    ) + '\n\n'
                    + _('Error:') + f'\n{output}'
                    + '\n'
                    + _('Command:') + f'\n{cmd}'
                )
                raise MountError(log_msg, gui_msg)

    logger.info(
        'Created decrypted view (forward mount). '
        f'(source: "{path_to_mount}" -> target: "{mountpoint}")')


def reverse_mount_dir(path_to_mount: Path,
                      mountpoint: Path,
                      cipher_path: Path,
                      password: str):
    """Create an encrypted view (reverse mount) of `path_to_mount` accessible
    at `mountpoint`, but using the cipher config stored in `cipher_dir`.
    """
    cipher_config = cipher_path / 'gocryptfs.conf'

    thread = TempPasswordThread(password)
    env = os.environ.copy()
    env['ASKPASS_TEMP'] = thread.temp_file

    with thread.starter():
        cmd = [
            'gocryptfs',
            '-extpass',
            'backintime-askpass',
            '-config',
            str(cipher_config),
            '-reverse',
            str(path_to_mount),
            str(mountpoint)
        ]

        logger.debug(f'Calling {cmd}')

        with subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        ) as proc:
            output = proc.communicate()[0]

            if proc.returncode != 0:
                log_msg = f'Reverse mount failed via "{cmd}"'
                log_msg = f'{log_msg} | {output}'
                log_msg = f'{log_msg} | Return code: {proc.returncode}'
                logger.critical(log_msg)

                gui_msg = (
                    _('Reverse mount failed with return code {rc}.').format(
                        rc=proc.returncode
                    ) + '\n\n'
                    + _('Error:') + f'\n{output}'
                    + '\n'
                    + _('Command:') + f'\n{cmd}'
                )
                raise MountError(log_msg, gui_msg)

    logger.info(
        'Created encrypted view (reverse mount). '
        f'(source: "{path_to_mount}" -> target: "{mountpoint}")')
