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
from mount import MountManager
from config import Config


class SSHConfigCheck:
    """An existing SSH mount is used to check if it is prepared for being a
    backup destination.
    """

    def __init__(self,
                 mount_manager: MountManager,
                 config: Config):
        self.mnt = mount_manager
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

        # Taken from `Config.sshDefaultArgs()`
        ssh += ['-o', 'ServerAliveInterval=240']  # keep connection alive
        ssh += ['-o', 'LogLevel=Error']  # disable ssh banner

        # specifying key file here allows to override for potentially
        # conflicting .ssh/config key entry
        if self.cfg.sshPrivateKeyFile_enabled():
            key_file = self.cfg.sshPrivateKeyFile()
            if key_file:
                ssh += ['-o', f'IdentityFile={key_file}']

        # Proxy (aka Jump host)
        if self.cfg.sshProxyHost():
            ssh += ['-J', '{}@{}:{}'.format(
                self.cfg.sshProxyUser(),
                self.cfg.sshProxyHost(),
                self.cfg.sshProxyPort()
            )]

        # remote port
        if port:
            ssh += ['-p', str(self.cfg.sshPort())]

        # # custom arguments
        # if custom_args:
        #     ssh += custom_args

        # user@host
        if user_host:
            ssh.append(
                '{}@{}'.format(self.cfg.sshUser(), self.cfg.sshHost())
            )

        # # quote the command running on remote host
        # if quote and cmd:
        #     ssh.append("'")

        # run 'ionice' on remote host
        if self.cfg.ioniceOnRemote():
            ssh += ['ionice', '-c2', '-n7']

        # run 'nice' on remote host
        if self.niceOnRemote():
            ssh += ['nice', '-n19']

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

        # check_remote_commands()
        #     ├── check_rsync_basic()
        #     ├── check_rsync_hardlinks()
        #     ├── check_remote_tools()
        #     ├── check_filesystem_semantics()
        self._check_rsync_basic()

    def _check_rsync_basic(self):
