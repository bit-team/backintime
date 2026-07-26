# SPDX-FileCopyrightText: © 2026 arcsinhx
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Disk usage calculation for backups incl. hard-link savings."""
import subprocess
import logger
import snapshots
from storagesize import StorageSize, SizeUnit



def _du_local_total(paths: list, du_flags=None) -> int:
    """Compute total disk usage of local paths via ``du``.

    Args:
        paths: List of path strings.
        du_flags: Flags for ``du``, defaults to ``['-sbc']`` (apparent size
            in bytes, each hard link counted individually).
    """
    if du_flags is None:
        du_flags = ['-sbc']

    if not paths:
        return 0
    try:
        result = subprocess.run(
            ['du'] + du_flags + [str(p) for p in paths],
            capture_output=True, text=True, check=True
        )
        total_line = result.stdout.strip().split('\n')[-1]
        return int(total_line.split()[0])
    except subprocess.CalledProcessError as err:
        logger.error(
            f'Failed to compute local disk usage: {err.stderr.strip()}')
        return -1
    except (ValueError, IndexError):
        logger.error('Failed to parse disk usage output')
        return -1


def _du_remote_total(cfg, backups, du_flags=None,
                     mounted_path=None) -> int:
    """Compute total disk usage of remote backups via SSH.

    Args:
        cfg: Config instance.
        backups: List of (sid_str, path) tuples.
        du_flags: Flags for ``du``, defaults to ``['-sbc']`` (apparent size).
        mounted_path: Mount path required by new mount subsystem.

    Returns:
        Total size in bytes, or -1 on failure.
    """
    if du_flags is None:
        du_flags = ['-sbc']

    mode = cfg.snapshotsMode()
    remote_paths = []

    for sid_str, _ in backups:
        sid_obj = snapshots.SID(sid_str, cfg, mounted_path)
        if mode == 'ssh_encfs':
            remote_path = sid_obj.path(use_mode=['ssh_encfs'])
        else:
            remote_path = sid_obj.path(use_mode=['ssh'])
        remote_paths.append(remote_path)

    ssh_cmd = cfg.sshCommand(
        cmd=['du'] + du_flags + remote_paths,
        nice=False, ionice=False
    )
    try:
        result = subprocess.run(
            ssh_cmd, capture_output=True, text=True, check=True
        )
        total_line = result.stdout.strip().split('\n')[-1]
        return int(total_line.split()[0])
    except subprocess.CalledProcessError as err:
        logger.error(
            f'Failed to compute remote disk usage: {err.stderr.strip()}')
        return -1
    except (ValueError, IndexError):
        logger.error('Failed to parse remote disk usage output')
        return -1


def compute_total_usage(cfg, backups, mounted_path=None):
    """Total physical disk usage of all backups."""
    mode = cfg.snapshotsMode()
    if mode in ('ssh', 'ssh_encfs'):
        return _du_remote_total(cfg, backups,
                                mounted_path=mounted_path)
    return _du_local_total([p for _, p in backups])


def format_usage(size_bytes: int) -> str:
    """Format a disk usage byte count into a human-readable string."""
    if size_bytes < 0:
        return 'Total disk usage: ERROR (could not determine size)'

    size = StorageSize(size_bytes)

    if size >= StorageSize(1, SizeUnit.GIB):
        value = size.value(SizeUnit.GIB, decimal_places=1)
        return f'Total disk usage: {value:.1f} GiB'
    if size >= StorageSize(1, SizeUnit.MIB):
        value = size.value(SizeUnit.MIB, decimal_places=1)
        return f'Total disk usage: {value:.1f} MiB'
    if size_bytes >= 1024:
        value = size_bytes / 1024
        return f'Total disk usage: {value:.1f} KiB'
    return f'Total disk usage: {size_bytes} Byte'


def format_size_human(size_bytes: int) -> str:
    """Format a byte count into a human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string like "1.5 GiB".
    """
    size = StorageSize(size_bytes)

    if size >= StorageSize(1, SizeUnit.GIB):
        value = size.value(SizeUnit.GIB, decimal_places=1)
        return f'{value:.1f} GiB'
    if size >= StorageSize(1, SizeUnit.MIB):
        value = size.value(SizeUnit.MIB, decimal_places=1)
        return f'{value:.1f} MiB'
    if size_bytes >= 1024:
        value = size_bytes / 1024
        return f'{value:.1f} KiB'
    return f'{size_bytes} Byte'



def compute_sizes_local(paths: list) -> tuple:
    """Return (apparent_bytes, physical_bytes) for local backup dirs.

    Apparent = sum of ``du -sbc`` for each snapshot individually
    (hard links NOT deduplicated across snapshots).
    Physical = ``du -sbc`` for all snapshots together
    (hard links deduplicated across snapshots).
    """
    logical = sum(_du_local_total([p]) for p in paths)
    physical = _du_local_total(paths)
    return (logical, physical)


def compute_sizes_remote(cfg, backups, mounted_path=None) -> tuple:
    """Return (apparent_bytes, physical_bytes) for remote backups via SSH.

    Apparent = sum of ``du -sbc`` per snapshot via SSH (no cross-snapshot
    dedup). Physical = ``du -sbc`` for all snapshots via SSH (hard links
    deduplicated across snapshots).
    """
    logical = sum(_du_remote_total(cfg, [b], mounted_path=mounted_path)
                  for b in backups)
    physical = _du_remote_total(cfg, backups, mounted_path=mounted_path)
    return (logical, physical)


def compute_space_savings(cfg, backups, mounted_path=None) -> tuple:
    """Compute space saved by hard link-based deduplication.

    Returns:
        Tuple of (logical_bytes, physical_bytes, saved_bytes, saved_percent).
        Returns (-1, -1, -1, 0.0) on failure.
    """
    mode = cfg.snapshotsMode()

    if mode in ('ssh', 'ssh_encfs'):
        logical, physical = compute_sizes_remote(
            cfg, backups, mounted_path=mounted_path)
    else:
        logical, physical = compute_sizes_local(
            [str(p) for _, p in backups])

    if logical < 0 or physical < 0:
        return (-1, -1, -1, 0.0)

    if logical == 0:
        return (0, 0, 0, 0.0)

    saved = logical - physical
    percent = (saved / logical) * 100.0
    return (logical, physical, saved, percent)
