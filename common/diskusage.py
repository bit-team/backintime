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
import config
# import konfig  # Will come...

DEFAULT_DU_FLAGS = [
    # display only a total for each argument
    '--summarize',
    # equivalent to '--apparent-size --block-size=1'
    '--bytes',
    '--total'
]


def _du_local_total(paths: list, du_flags=None) -> int:
    """Compute total disk usage of local paths via ``du``.

    Args:
        paths: List of path strings.
        du_flags: Flags for ``du``, defaults to ``['-sbc']`` (apparent size
            in bytes, each hard link counted individually).
    """
    if du_flags is None:
        du_flags = DEFAULT_DU_FLAGS

    if not paths:
        return 0

    try:
        cmd = ['du'] + du_flags + [str(p) for p in paths]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
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


def _du_remote_total(cfg: config.Config,
                     backups,
                     du_flags: bool | None = None) -> int:
    """Compute total disk usage of remote backups via SSH.

    Args:
        cfg: (Deprecated) config object.
        backups: List of (sid_str, path) tuples.
        du_flags: Flags for ``du``, defaults to ``['-sbc']`` (apparent size).
        mounted_path: Mount path required by new mount subsystem.

    Returns:
        Total size in bytes, or -1 on failure.
    """

    if du_flags is None:
        du_flags = DEFAULT_DU_FLAGS

    remote_paths = [one_backup[1] for one_backup in backups]

    # Config.sshCommand() is deprecated
    ssh_cmd = cfg.sshCommand(
        cmd=['du'] + du_flags + remote_paths,
        nice=False,
        ionice=False
    )

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout
        total_line = output.strip().split('\n')[-1]

        total_size_bytes = int(total_line.split()[0])

        return total_size_bytes

    except subprocess.CalledProcessError as err:
        logger.error(
            f'Failed to compute remote disk usage: {err.stderr.strip()}')
        return -1

    except (ValueError, IndexError):
        logger.error('Failed to parse remote disk usage output')
        return -1


def compute_total_usage(cfg: config.Config, backups):
    """Total physical disk usage of all backups."""

    if 'ssh' in cfg.snapshotsMode():
        return _du_remote_total(cfg, backups)

    return _du_local_total([p for _unused, p in backups])


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


def compute_sizes_remote(cfg, backups) -> tuple:
    """Return (apparent_bytes, physical_bytes) for remote backups via SSH.

    Apparent = sum of ``du -sbc`` per snapshot via SSH (no cross-snapshot
    dedup). Physical = ``du -sbc`` for all snapshots via SSH (hard links
    deduplicated across snapshots).
    """
    logical = sum(
        _du_remote_total(cfg, [one_backup]) for one_backup in backups
    )

    physical = _du_remote_total(cfg, backups)

    return (logical, physical)


def compute_space_savings(cfg, backups) -> tuple:
    """Compute space saved by hard link-based deduplication.

    Returns:
        Tuple of (logical_bytes, physical_bytes, saved_bytes, saved_percent).
        Returns (-1, -1, -1, 0.0) on failure.
    """
    mode = cfg.snapshotsMode()

    if 'ssh' in mode:
        logical, physical = compute_sizes_remote(cfg, backups)

    else:
        logical, physical = compute_sizes_local(
            [str(one_backup[1]) for one_backup in backups]
        )

    if logical < 0 or physical < 0:
        # failure
        return (-1, -1, -1, 0.0)

    if logical == 0:
        return (0, 0, 0, 0.0)

    saved = logical - physical
    percent = (saved / logical) * 100.0

    return (logical, physical, saved, percent)
