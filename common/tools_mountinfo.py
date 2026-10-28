# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Helper functions regarding /proc/self/mountinfo"""
from pathlib import Path
import re


def get_all_mount_infos() -> dict[Path, dict]:
    """Extract all mount information from `/proc/self/mountinfo`.

    Returns:
        A dictionary indexed by mountpoint paths.

    Raises:
        OSError: In case of read errors.

    See also <https://docs.kernel.org/filesystems/proc.html>.
    The implementation is based on ideas of "moby" (written in Go):
       <https://github.com/moby/sys/blob/main/mountinfo/
        mountinfo_linux.go?utm_source=chatgpt.com>
    """
    result = {}
    mountinfo = Path('/proc/self/mountinfo')

    def unescape_mountinfo(value: str) -> str:
        """Decode three-digit octal escapes starting with 0 or 1.

        The GNU/Linux kernel does escape several characters (e.g. blanks in
        filenames) when writing the mount info file.
        """
        return re.sub(
            r'\\([01][0-7]{2})',
            lambda match: chr(int(match.group(1), 8)),
            value,
        )

    for row in mountinfo.read_text(encoding='utf-8').splitlines():
        fields = row.split(' ')
        separator = fields.index('-')

        mpoint = Path(unescape_mountinfo(fields[4]))

        # Dev note (buhtz, 2026-10):
        # Multiple mounts can share the same mountpoint (overmounts).
        # Later mounts hide earlier ones, but all may appear in mountinfo.
        # A dict keyed by mountpoint therefore cannot represent all entries.
        # For BIT, only the topmost, visible mount is relevant.

        result[mpoint] = {
            'root': Path(unescape_mountinfo(fields[3])),
            'mountpoint': mpoint,
            'fstype': fields[separator + 1],
            'options': set(fields[5].split(',')),
            # "filesystem-specific information"
            # In case of a gocryptfs reverse(!) mount this will be the
            # cipher dir who's config was used to create the reverse mount,
            # from "root" to "mountpoint". But in other cases it is not
            # always a path.
            'source': unescape_mountinfo(fields[separator + 2]),
        }

    return result


def get_mount_info(path: Path) -> dict | None:
    """Get mount information for an exact mountpoint."""
    return get_all_mount_infos().get(path.resolve(), None)


def get_mount_info_for_path(path: Path) -> dict | None:
    """Mount information for the filesystem containing `path`.

    Return: Dictionary with the info or `None` if nothing was found.
    """
    path = path.resolve()

    all_infos = get_all_mount_infos()

    # Sort the mountpoints descending based on the number of path elements.
    # Therefore, we get the most specific mountpoint first.
    for mpoint in sorted(
        all_infos,
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        if path.is_relative_to(mpoint):
            return all_infos[mpoint]

    return None


def is_mounted(path: Path) -> bool:
    """Checks whether `path` is a mounted mountpoint."""

    absolute = path.resolve()

    if not absolute.exists():
        return False

    if not absolute.is_mount():
        return False

    # Keep in mind, that is_mount() can be false positive on btrfs-subvolumes
    # Issue #2487. That's why we need to be sure and also check the
    # proc-mountinfo file
    return get_mount_info(absolute) is not None


# mountpoint_of_path
def mountpoint(path: Path | str) -> str | None:
    """Get the mountpoint of the filesystem containing `path`.

    For example, if your HOME is on a separate partition
    mountpoint('/home/user/foo') would return '/home'.

    Args:
        path (str): full path

    Returns:
        The mountpoint (as string) or None nothing found.
    """
    # WORKAROUND
    if isinstance(path, str):
        path = Path(path)

    info = get_mount_info_for_path(path)

    if info is not None:
        return str(info['mountpoint'])

    return None


# device_of_path
def device(path: Path | str) -> str | None:
    """Get the device (aka source) for the filesystem of ``path``.
    """
    info = get_mount_info_for_path(path)

    if info is not None:
        return info['source']

    return None


# filesystem_of_path
def filesystem(path: Path | str) -> str | None:
    """Get the type of the filesystem containing `path`."""
    info = get_mount_info_for_path(path)

    if info is not None:
        return info['fstype']

    return None
