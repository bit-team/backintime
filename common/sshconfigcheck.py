# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""SSH setup checks.

The code is based on `sshtools.py:SSH.preMountCheck()`. These checks are now
distinguished between two types of checks.
Checks running on every mount operation now handled in the new mount subsystem
via `Backend.validate()`. Checks that run only when setup or modifiy a profile
are done here.

Feel free to move this code somewhere else.
"""
import tempfile
import subprocess
from pathlib import Path
from typing import Union
import logger
from mount import MountManager, MountE
from config import Config


class SSHConfigCheck:
    """An existing SSH mount is used to check if it is prepared for being a
    backup destination.
    """

    def __init__(self,
                 mount_manager: MountManager,
                 config: Config):
        self.mnt = mount_manager

        # The SSH backends current config, will be used for the tests.
        self.ssh_host = mount_manager.backend.host

        self.cfg = config

    def _build_ssh_command(self) -> list[str]:
        """Taken from `Config.sshCommand()`. Refactor later. See #1966 about
        encapsulate shell commands.

        Maybe the mount manager could provide some basics SSH commands because
        it knews the host configuration?

        Returns:
            list:               ssh command with chosen arguments
        """
        # Refactor: Use of assert is discouraged in productive code.
        # Raise Exceptions instead.
        ssh = ['ssh']

        # # Taken from `Config.sshDefaultArgs()`
        # ssh += ['-o', 'ServerAliveInterval=240']  # keep connection alive
        # ssh += ['-o', 'LogLevel=Error']  # disable ssh banner

        # specifying key file here allows to override for potentially
        # conflicting .ssh/config key entry
        if self.ssh_host.priv_key_file:
            ssh += ['-o', f'IdentityFile={self.ssh_host.priv_key_file}']

        # Proxy (aka Jump host)
        if self.ssh_host.proxy:
            ssh += ['-J', self.ssh_host.proxy.user_host_port]

        # remote port
        ssh += ['-p', str(self.ssh_host.port)]

        # # custom arguments
        # if custom_args:
        #     ssh += custom_args

        # user@host
        ssh.append(self.ssh_host.user_host)

        # # quote the command running on remote host
        # if quote and cmd:
        #     ssh.append("'")

        # # run 'ionice' on remote host
        # if self.cfg.ioniceOnRemote():
        #     ssh += ['ionice', '-c2', '-n7']

        # # run 'nice' on remote host
        # if self.niceOnRemote():
        #     ssh += ['nice', '-n19']

        # TODO
        # # run prefix on remote host
        # if prefix and cmd and self.sshPrefixEnabled(profile_id):
        #     ssh += self.sshPrefixCmd(profile_id, cmd_type=type(cmd))

        return ssh

    def _ssh(self, cmd: list[str]) -> tuple[int, str, str]:
        proc = subprocess.Popen(
            self._build_ssh_command() + cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, err = proc.communicate()

        return proc.returncode, out, err

    def run(self):
        # check fuse (ist sshfs präsent?)

        # checkKnownHosts()
        # unlockSshAgent(force=True)
        # checkRemoteFolder()  -> evtl. in validate()

        if self.config.sshCheckCommands():
            # check_remote_commands()
            #     ├── check_rsync_basic()
            #     ├── check_rsync_hardlinks()
            #     ├── check_remote_tools()
            #     ├── check_filesystem_semantics()
            self._check_rsync_basic()

    def _check_rsync_basic(self):
        """Checks if it is possible to write a file via rsync to the SSH
        remote host.
        """
        with tempfile.TemporaryDirectory() as tmp:
            local_fp = Path(tmp) / 'a'
            local_fp.write_text('foo', encoding='utf-8')

            remote_tmp = self.ssh_host.user_host_path + '/bit_check_tmp'

            cmd = [
                'rsync',
                '--archive',
                local_fp,
                remote_tmp + '/'
            ]

            logger.info(f'Calling {cmd}...', self)

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            _, err = proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(f'rsync basic failed: {err}')

    def _check_rsync_hardlinks(self):
        """Checks if rsync creates real hardlinks on remote file system."""
        with tempfile.TemporaryDirectory() as tmp:
            local_fp = Path(tmp) / 'a'
            local_fp.write_text('foo', encoding='utf-8')

            remote_base = self.ssh_host.user_host_path
            remote_1 = remote_base + '/bit_check_1'
            remote_2 = remote_base + '/bit_check_2'

            # First upload
            cmd1 = [
                'rsync',
                '--archive',
                local_fp,
                remote_1 + '/'
            ]

            # Second upload with link-dest
            cmd2 = [
                'rsync',
                '--archive',
                '--link-dest=../bit_check_1',
                local_fp,
                remote_2 + '/'
            ]

            for cmd in (cmd1, cmd2):
                logger.info(f'Calling {cmd}...', self)
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                _, err = proc.communicate()

                if proc.returncode != 0:
                    raise RuntimeError(f'rsync hardlink test failed: {err}')

            def _remote_stat_inode(path: str) -> int:
                cmd = self._build_ssh_command()
                cmd.extend(['stat', '--format', '%i', path])
                logger.info(f'Calling {cmd}...', self)
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                out, err = proc.communicate()
                if proc.returncode != 0:
                    raise RuntimeError(err)

                return int(out.strip())

            # inode check via ssh
            inode_1 = _remote_stat_inode(f'{remote_1}/a')
            inode_2 = _remote_stat_inode(f'{remote_2}/a')
            if inode_1 != inode_2:
                raise RuntimeError(
                    'Remote file system does not support hardlinks'
                )
