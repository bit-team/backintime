#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2015-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""This module determines the maximum possible length of an SSH command.

It can also can run as a stand alone script. The solution is based on
https://www.theeggeadventure.com/wikimedia/index.php/Ssh_argument_length
"""
import random
import string
import subprocess
import socket
import argparse
from config import Config

# Must be divisible by 8
_INITIAL_SSH_CMD_SIZE = 1048320
_ERR_CODE_E2BIG = 7


def probe_max_ssh_command_size(
        cfg: Config,
        ssh_command_size: int = _INITIAL_SSH_CMD_SIZE,
        size_offset: int = _INITIAL_SSH_CMD_SIZE) -> int:
    """Determine the maximum length of SSH commands for the current config

    Try a SSH command with length ``ssh_command_size``. The command is
    decreased by ``size_offset`` if it was too long or increased if it worked.
    The function calls itself recursively until it finds the maximum
    possible length. The offset ``size_offset`` is bisect in each try.

    Args:
        config: Back In Time config instance including the details about the
            current SSH snapshot profile. The current profile must use the SSH
            mode.
        ssh_command_size: Initial length used for the test argument.
        size_offset: Offset for increase or decrease ``ssh_command_size``.

    Returns:
        The maximum possible SSH command length.

    Raises:
        Exception: If there are unhandled cases or the recurse ends in an
                   undefined state.
        OSError: If there are unhandled cases.
    """
    size_offset = round(size_offset / 2)

    # random string of desired length
    command_string = ''.join(random.choices(
        string.ascii_uppercase+string.digits, k=ssh_command_size))

    # use that string in a printf statement via SSH
    ssh = cfg.sshCommand(
        cmd=['printf', command_string],
        nice=False,
        ionice=False,
        prefix=False)

    try:
        proc = subprocess.run(ssh, capture_output=True, text=True, check=True)
        out, err = proc.stdout, proc.stderr

    except OSError as exc:
        # Only handle "Argument to long error"
        if exc.errno != _ERR_CODE_E2BIG:
            raise exc

        report_test(
            ssh_command_size,
            f'Python exception: "{exc.strerror}". Decrease '
            f'by {size_offset:,} and try again.')

        # test again with new ssh_command_size
        return probe_max_ssh_command_size(
            cfg,
            ssh_command_size - size_offset,
            size_offset)

    # Successful SSH command
    if out == command_string:

        # no increases possible anymore
        if size_offset == 0:
            report_test(ssh_command_size,
                        'Found correct length. Adding '
                        f'length of "{ssh[-2]}" to it.')

            # the final command size
            return ssh_command_size + len(ssh[-2])  # length of "printf"

        # there is room to increase the length
        report_test(ssh_command_size,
                    f'Can be longer. Increase by {size_offset:,} '
                    'and try again.')

        # increase by "size_offset" and try again
        return probe_max_ssh_command_size(
            cfg,
            ssh_command_size + size_offset,
            size_offset)

    # command string was too long
    if 'Argument list too long' in err:
        report_test(ssh_command_size,
                    f'stderr: "{err.strip()}". Decrease '
                    f'by {size_offset:,} and try again.')

        # reduce by "size_offset" and try again
        return probe_max_ssh_command_size(
            cfg,
            ssh_command_size - size_offset,
            size_offset)

    raise RuntimeError('Unhandled case.\n'
                       f'{ssh[:-1]}\n'
                       f'out="{out}"\nerr="{err}"\n'
                       f'ssh_command_size={ssh_command_size:,}\n'
                       f'size_offset={size_offset:,}')


def report_test(ssh_command_size, msg):
    """Report proceeding test."""
    print(f'Tried length {ssh_command_size:,}... {msg}')


def report_result(host, max_ssh_cmd_size):
    """Report test result."""
    print(f'Maximum SSH command length between "{socket.gethostname()}" '
          f'and "{host}" is {max_ssh_cmd_size:,}.')


def main(args):
    """Entry."""
    cfg = Config()

    # loop over all profiles in the configuration
    for profile_id in cfg.profiles():
        cfg.setCurrentProfile(profile_id)
        print(f'Profile {profile_id} - {cfg.profileName()}: '
              f'Mode = {cfg.snapshotsMode()}')

        if cfg.snapshotsMode() == 'ssh':
            ssh_command_size = probe_max_ssh_command_size(
                cfg, args.SSH_COMMAND_SIZE)
            report_result(cfg.sshHost(), ssh_command_size)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check the maximal ssh command size for all ssh profiles '
                    'in the configurations',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('SSH_COMMAND_SIZE',
                        type=int,
                        nargs='?',
                        default=_INITIAL_SSH_CMD_SIZE,
                        help='Start checking with SSH_COMMAND_SIZE as length')

    main(parser.parse_args())
