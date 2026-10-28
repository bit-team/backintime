# SPDX-FileCopyrightText: © 2026 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Low level operations related to gocryptfs"""
import json
import os
from pathlib import Path
import subprocess
import logger
from mount import MountError
from password_ipc import TempPasswordThread
import tools


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
            # Use AES-SIV instead of AES-GCM. Allows us to -reverse mount a
            # directory with the config of another gocryptfs directory.
            '-aessiv',
            # We don't want to deal with diriv files. Also recommended by
            # the gocryptfs maintainer himself.
            '-deterministic-names',
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
                      password: str,
                      socket_path: Path):
    """Create a decrypted view (forward mount) of `path_to_mount` accessible
    at `mountpoint`.

    Args:
        path_to_mount: The originial encrypted gocryptfs cipher dir.
        mountpoint: That path provide the decrypted view of `path_to_mount`.
        password: The password to decrypt the cipher dir.
        socket_path: Socket file to later de- and encrypt filennames.
    """
    thread = TempPasswordThread(password)
    env = os.environ.copy()
    env['ASKPASS_TEMP'] = thread.temp_file

    with thread.starter():
        cmd = [
            'gocryptfs',
            # The socket is used later (via gocryptfs-xray) to de- and encrypt
            # filenames.
            '-ctlsock',
            str(socket_path),
            # password
            '-extpass',
            'backintime-askpass',
            # origina & mountpoint
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
        f'(source: "{path_to_mount}" -> target: "{mountpoint}")'
    )


def reverse_mount_dir(path_to_mount: Path,
                      mountpoint: Path,
                      cipher_path: Path,
                      password: str,
                      read_only: bool = True):
    """Create an encrypted view (reverse mount) of `path_to_mount` accessible
    at `mountpoint`, but using the cipher config stored in `cipher_dir`.

    Please see `init_gocryptfs_dir()` for further explanations about the used
    ``gocryptfs` commandline flags.

    Args:
        path_to_mount: The original unencrypted directory.
        mountpoint: That path will provide the encrypted view to
            `path_to_mount`.
        cipher_path: A gocryptfs initialized directory which config will be
            used for mounting/encrypting.
        password: Gocrypt password.
        read_only: Mount read-only (default).
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
        ]

        if read_only:
            # The mount will be used as rsync SRC.
            cmd += ['-ro']

        cmd += [
            # Note that 'cipher_config' need have '-aessive' and
            # '-deterministic-names' enabled.
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


def umount(path: Path):
    """Release the mountpoint.

    Nothing happens if not mounted.

    Raises: MountError
    """
    if not tools.is_mounted(path):
        logger.debug(f'Is not mounted. {path}')
        return

    proc = subprocess.run(
        [
            'fusermount',
            '-u',
            path
        ],
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
            + '\n'
            + _('Original error: {err}').format(err=proc.stdout)
        )
        raise MountError(log_msg, gui_msg)

    logger.info(f'Unmounted encrypted directory "{path}"')


class GocryptPathMapper:
    """Map (or translate) encrypted or decrypted paths in both directions.

    The tool `gocryptfs-xray` is used in combination with a socket file created
    via the forward mount.
    """
    def __init__(self, socket_path: Path):
        self._socket = socket_path

    def encrypt_paths(self, paths: list[Path]) -> list[Path]:
        return self._translate(paths, 'encrypt-paths')

    def decrypt_paths(self, paths: list[Path]) -> list[Path]:
        return self._translate(paths, 'decrypt-paths')

    def _translate(self, paths: list[Path], operation: str) -> list[Path]:
        if not paths:
            return []

        result = subprocess.run(
            [
                'gocryptfs-xray',
                '-0',
                f'-{operation}',
                str(self._socket_path),
            ],
            input='\0'.join(str(path) for path in paths) + '\0',
            capture_output=True,
            text=True,
            check=True,
        )

        output = result.stdout
        if output.endswith('\0'):
            output = output[:-1]

        return [Path(path) for path in output.split('\0')]
