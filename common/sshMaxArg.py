#!/usr/bin/env python3
#    Copyright (C) 2015-2022 Germar Reitze
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""This module determines the maximum possible length of an SSH command.

It can also be called as a stand alone script.
"""

import random
import string
import subprocess
import socket
import argparse

# original was 1048320, must be divisable by 8
_INITIAL_SSH_COMMAND_SIZE = 400000


def probe_max_ssh_command_size(config,
                               ssh_command_size=_INITIAL_SSH_COMMAND_SIZE,
                               size_offset=_INITIAL_SSH_COMMAND_SIZE):
    """Determin the maximum length of an argument via SSH.

    Try a an SSH command with length ``ssh_command_size``. The command is
    decreased by ``size_offset`` if it was to long or increased if it worked.
    The function calls itself in a recursition until it finds the maximum
    possible length. The offset ``size_offset`` is bisect in each try.

    Args:
        config (config.Config): Back In Time config instance including the
                                details about the current SSH snapshto profile.
        ssh_command_size (int): Initial length used for the test argument.
        size_offset (int): Offset for increase or decrease
                           ``ssh_command_size``.

    Returns:
        (int): The maximum possible length.

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
    ssh = config.sshCommand(
        cmd=['printf', command_string],
        nice=False,
        ionice=False,
        prefix=False)

    try:
        proc = subprocess.Popen(ssh,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        out, err = proc.communicate()

    except OSError as err:
        # Only handle "Argument to long error" (E2BIG)
        if err.errno != 7:
            raise err

        report_test(
            ssh_command_size,
            f'Python exception: "{err.strerror}". Decrease '
            f'by {size_offset:,} and try again.')

        # reducy by "r" and try again
        return probe_max_ssh_command_size(
            config,
            ssh_command_size - size_offset,
            size_offset)

    else:
        # Successfull SSH command
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

            # increae by "r" and try again
            return probe_max_ssh_command_size(
                config,
                ssh_command_size + size_offset,
                size_offset)

        # command string was to long
        elif 'Argument list too long' in err:
            report_test(ssh_command_size,
                       f'stderr: "{err.strip()}". Decrease '
                       f'by {size_offset:,} and try again.')

            # reduce by "r" and try again
            return probe_max_ssh_command_size(
                config,
                ssh_command_size - size_offset,
                size_offset)

    raise Exception('Unhandled case.\n'
                    f'{ssh[:-1]}\nout="{out}"\nerr="{err}"\n'
                    f'mid={ssh_command_size:,}\nr={size_offset:,}')


def report_test(ssh_command_size, msg):
    print(f'Tried length {ssh_command_size:,}... {msg}')


def report_result(host, mid):
    print(f'Maximum SSH argument length between "{socket.gethostname()}" '
          f'and "{host}" is {mid:,}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check maximal argument length on SSH connection',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('SSH_COMMAND_SIZE',
                        type=int,
                        nargs='?',
                        default=_INITIAL_SSH_COMMAND_SIZE,
                        help='Start checking with SSH_COMMAND_SIZE arg length')

    args = parser.parse_args()

    import config
    cfg = config.Config()

    ssh_command_size = probe_max_ssh_command_size(cfg, args.MID)

    report_result(cfg.sshHost(), ssh_command_size)
