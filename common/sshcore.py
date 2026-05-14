# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Core SSH infrastructure module

Provides SSH-related primitives and helper functionality.

Dev note (2026-05, buhtz): This module is the ancestor of sshtools.py.
"""
from __future__ import annotations
import socket
import ipaddress
import subprocess
from typing import Optional
from pathlib import Path
import bitbase
import logger


class SSHHost:
    """SSH connection parameters."""

    DEFAULT_PORT = bitbase.DEFAULT_SSH_PORT

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def __init__(  # noqa: PLR0913
            self,
            host: str,
            user: str = None,
            port: int = DEFAULT_PORT,
            priv_key_file: str = None,
            proxy: Optional[SSHHost] = None,
            path: str = './',
    ):
        self.host = self.ensure_ipv6_brackets(host)
        self.user = user
        self.port = port
        self.priv_key_file = priv_key_file
        self.proxy = proxy
        self.path = path

    @staticmethod
    def ensure_ipv6_brackets(address: str) -> str:
        """Escape IP addresses with square brackets ``[]`` if they are IPv6.

        IPv6 addresses contain ``:``, which conflicts with separators used in
        contexts like SSH/URLs (e.g. host:port). Wrapping IPv6 in ``[]``
        ensures unambiguous parsing.

        If it is an IPv4 address or a hostname (lettersonly) nothing is
        changed.

        Args:
            address (str): IP-Address to escape if needed.

        Returns:
            str: The address, escaped if it is IPv6.

        Dev note (buhtz, 2026-04): The host shouldn't to this escaping. It
        becomes relevant only when the shell command is constructed. Move it
        their if #1966 is solved.
        """

        try:
            ip = ipaddress.ip_address(address)

        except ValueError:
            # invalid IP, e.g. a hostname
            return address

        if ip.version == 6:  # noqa: PLR2004
            return f'[{address}]'

        return address

    @property
    def user_host(self) -> str:
        """User and host as one string."""
        if self.user:
            return f'{self.user}@{self.host}'

        return self.host

    @property
    def user_host_path(self) -> str:
        """User, host and the path in one string"""
        return f'{self.user_host}:{self.path}'

    @property
    def user_host_port(self) -> str:
        """User, host and port in one string"""
        return f'{self.user_host}:{self.port}'

    def __str__(self) -> str:
        """Return unique string for mount fingerprint"""
        result = f'{self.user_host_port};{self.path};{self.priv_key_file}'

        if self.proxy:
            result = f'{result} -> {self.proxy}'

        return result


def can_connect_tcp(host: SSHHost, timeout: float = 2.0) -> bool:
    """Check if a TCP connection to the given SSH host is possible.

    Attempts a raw TCP connection to the host and port defined in the SSHHost
    object. Not performed: SSH authentication, proxy handling, and
    higher-level protocol checks.

    Args:
        host: Target SSH host. `host.proxy` is ignored.
        timeout: Connection timeout in seconds.

    Returns:
        `True` if the TCP connection succeeds, otherwise `False`.

    """
    try:
        with socket.create_connection(
                (
                    # create_connection() does not accept IPv6 brackets
                    host.host.strip('[]'),
                    host.port
                ),
                timeout=timeout
        ):
            return True

    except OSError as exc:
        logger.debug(f'Unreachable host "{host}" ({exc})')

        return False


def ssh_key_fingerprint(path: Path) -> str:
    """Return SHA256 fingerprint of an SSH private key.

    Uses ssh-keygen canonical output.
    """

    if not path.exists():
        return None

    proc = subprocess.run(
        ['ssh-keygen', '-E', 'sha256', '-lf', path],
        capture_output=True,
        text=True
    )

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)

    # format:
    # 256 SHA256:abc... comment (type)
    parts = proc.stdout.strip().split()

    return parts[1]  # SHA256:...
