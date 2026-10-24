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
from __future__ import annotations
import hashlib
import json
import os
import tempfile
from pathlib import Path
import subprocess
import bitbase
import logger
from mount import MountError
from password_ipc import TempPasswordThread
from sshcore import SSHHost
from storagesize import StorageSize
import tools

# The directory used for all temptorary mount points. In most cases it
# is $HOME/.local/share/backintime/mnt
MOUNT_ROOT_PATH = bitbase.XDG_DATA_HOME / bitbase.BINARY_NAME_BASE / 'mnt'


class BackupSources:
    """The source endpoint of a backup.

    One instance manage all include entries of a backup profile at once.
    """
    def __init__(self, include_paths: list[Path], dest: BackupDestination):
        """
        """
        # The original source paths. In mode "local encrypted" it is the not
        # encrypted.
        self._include_paths = include_paths

        # # The (reverse mounted) encrypted view of the original source path
        self._reverse_mountpoint = MOUNT_ROOT_PATH / 'reverse'
        self._reverse_mountpoint.mkdir(parents=True, exist_ok=True)
        self._reverse_mountpoint = Path(tempfile.mkdtemp(
            prefix=f'{os.getpid()}.',
            dir=self._reverse_mountpoint
        ))

        reverse_mount_dir(
            path_to_mount=Path('/'),
            mountpoint=self._reverse_mountpoint,
            cipher_path=dest.original_path,
            password=dest.gocrypt_password
        )

    def get_include_paths_missing_in_source(self) -> list[Paths]:
        """Return include entries that are missing in the backup source.

        Returns:
            list: List of entries missing.
        """
        missing_entries = filter(
            lambda path: not path.exists(),
            self._include_paths
        )

        return list(missing_entries)

    def get_transfer_root_path(self) -> Path:
        """Return the path used by rsync as SRC for the transfer.

        The return value depends on the backup mode of the current profile.
        That path is the root of the file system or a mountpoint connected to
        the filesystems root.
        Include paths are specified relative to this root path.

        Returns:
            In "local" or "ssh" mode: File system root.
            In "local encrypted" or "ssh encrypted" mode: An encrypted view
                (gocryptfs reverse mount) of file system root.
        """
        pass

    # def get_local_mounted_path(self) -> Path:
    #     """Return the source path through a local mount."""
    #     pass


class BackupDestination:
    """The destination endpoint of a backup.

    """
    def __init__(self,
                 path: Path,
                 gocrypt_password: str | None,
                 ssh_host: SSHHost | None = None):
        # The original destination path.
        # In mode "local" it is the original regular path.
        # In mode "local encrypted" it is the encrypted path.
        # In mode "ssh" it is the original remote path.
        # In mode "ssh encrpyted" it is the original remote path.
        self._destination_path = path

        # Gocryptfs encryption password
        self._gocrypt_password = gocrypt_password

        # In case of SSH profiles
        self._ssh_host = ssh_host

        # The (forward mounted) decrypted view of the original destination path
        # E.g., ``~/.local/share/backintime/mnt/<fp>/mountpoint/``.
        self._decrypted_path = MOUNT_ROOT_PATH / \
            self._get_fingerprint() / 'mountpoint'
        self._decrypted_path.mkdir(parents=True, exist_ok=True)

    def get_transfer_path(self) -> Path | str:
        """Return the destination path used by rsync as DEST for the transfer.

        The return value depends on the backup mode of the current profile.

        Returns:
            In "local" and "local encrypted": The regular destination path.
            In "ssh" and "ssh encrypted" mode: Remote path in SSH syntax.
                (e.g. user@host:/path)
        """
        pass

    def get_local_path(self) -> Path:
        """Return the destination path through a local mount.

        The return value depends on the backup mode of the current profile.

        Returns:
            In "local": The destination path.
            In "local encrypted": A decrypted (gocryptfs forward) mounted view
                of the destination path.
            In "ssh" mode: An sshfs mounted mountpoint.
            In "ssh encrypted" mode: A decrypted (gocryptfs forward) mounted
                mountpoint, of an sshfs mounted mountpoint to the remote
                destination.
        """
        pass

    @property
    def original_path(self) -> Path:
        return self._destination_path

    @property
    def gocrypt_password(self):
        return self._gocrypt_password

    def _get_fingerprint(self):
        # WORKAROUND DRAFT
        # This is "local_gocryptfs" only
        data = f'LOCAL: {self._destination_path}'
        data = f'{data} | '
        data = f'{data} GOCRYPTFS: '

        return compute_fingerprint_from_string(data)

    def is_initialized(self) -> bool:
        return is_initialized(self._destination_path)

    def initialize_if_needed(self):
        """Initialize the destination directory if not still initialized.

        For local encrypted profiles the destination path will be initialized
        for being usable.
        """

        if self.is_initialized():
            return

        init_gocryptfs_dir(
            self._destination_path,
            self._gocrypt_password
        )

    def get_decrypted_view_as_path(self) -> Path:
        """Create a mountpoint with a decrypted view to the destination


        WEITER WEITER WEITER
        Creation and getting should be separated. Should be created round about
        initialization() to validate if it works well before getting it the
        first time.
        """

        forward_mount_dir(
            path_to_mount=self._destination_path,
            mountpoint=self._decrypted_path,
            password=self.gocrypt_password,
        )

        return self._decrypted_path

    def is_free_space_less_than(self, value: StorageSize) -> bool:
        real = self._get_free_space()

        if real is None:
            return False

        return real < value

    def get_free_space(self) -> StorageSize | None:
        """Free space at destination.

        Return:
            A StorageSize object holding the value or `None` in case of errors.
        """

        ssh_cmd = None

        # TODO
        # # Prepare getting free space value
        # if 'ssh' in mode:
        #     # ...on remote host
        #     # dest_path = self.config.sshSnapshotsFullPath()
        #     ssh_cmd = self.config.sshCommand(
        #         [], nice=False, ionice=False)

        return tools.free_space(self._destination_path, ssh_cmd)


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


def compute_fingerprint_from_string(source: str) -> str:
    """Compute a unique fingerprint used for mountpoints.

    The fingerprint is a deterministic hex string and based on the
    given `source` string. That source string consists in most cases of the
    profile configuration regarding destination path, SSH and Gocryptfs
    configuration.

    That fingerprint is unique to the configuration but independent from
    the instance used. Every backintime instance with the identical mount
    setup and configuration should return an identical fingerprint.

    In combination with mountpoint lock mechanic, it serves as a stable
    identifier for mountpoints, allowing mounts with identical
    configurations to be recognized and potentially reused across
    processes.

    Returns:
        A SHA256 hash cut to a 12-character hexadecimal string.
    """
    logger.debug(f'fingerprint: {source=}', self)

    return hashlib.sha256(source.encode()).hexdigest()[:12]
