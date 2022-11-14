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


_MID_INITIAL = 400000  # original was 1048320, must be divisable by 8


def maxArgLength(config, mid=_MID_INITIAL, r=_MID_INITIAL):
    """Determin the maximum length of an argument via SSH.

    Try a an SSH command with length ``mid``. The command is decreased by ``r``
    if it was to long or increased by ``r`` if it worked. The function calls
    itself in a recursition until it finds the maximum possible length.

    Args:
        config (config.Config): Back In Time config instance including the
                                details about the current SSH snapshto profile.
        mid (int): Initial length used for the test argument.
        r (int): Offset for increase or decrease ``mid``.

    Returns:
        (int): The maximum possible length.

    Raises:
        Exception: If there are unhandled cases.
        OSError: If there are unhandled cases.
    """
    r = round(r / 2)

    # random string of desired length
    mid_string = ''.join(
        random.choices(string.ascii_uppercase+string.digits, k=mid)
    )

    # use that string in a printf statement via SSH
    ssh = config.sshCommand(
        cmd=['printf', mid_string],
        nice=False,
        ionice=False,
        prefix=False)

    try:
        proc = subprocess.Popen(ssh,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        out, err = proc.communicate()

    except OSError as e:
        # Only handle "Argument to long error" (E2BIG)
        if e.errno != 7:
            raise e

        reportTest(
            mid,
            f'Python exception: "{e.strerror}". Decrease '
            f'by {r:,} and try again.')

        # reducy by "r" and try again
        return maxArgLength(config, mid - r, r)

    else:
        # Successfull SSH command
        if out == mid_string:

            # no increases possible anymore
            if r == 0:
                reportTest(mid, 'Found correct length. Adding '
                                f'length of "{ssh[-2]}" to it.')

                return mid + len(ssh[-2])  # must be length of "printf"

            # there is room to increase the length
            reportTest(
                mid, f'Can be longer. Increase by {r:,} and try again.')

            # increae by "r" and try again
            return maxArgLength(config, mid + r, r)

        # command string was to long
        elif 'Argument list too long' in err:
            reportTest(
                mid,
                f'stderr: "{err.strip()}". Decrease by {r:,} and try again.')

            # reduce by "r" and try again
            return maxArgLength(config, mid - r, r)

    raise Exception('Unhandled case.\n'
                    f'{ssh[:-1]}\nout="{out}"\n'
                    f'err="{err}"\nmid={mid:,}\nr={r:,}')


def reportTest(mid, msg):
    print(f'Tried length {mid:,}... {msg}')


def reportResult(host, mid):
    print(f'Maximum SSH argument length between "{socket.gethostname()}" '
          f'and "{host}" is {mid:,}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check maximal argument length on SSH connection',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('MID',
                        type=int,
                        nargs='?',
                        default=_MID_INITIAL,
                        help='Start checking with MID arg length')

    args = parser.parse_args()

    import config
    cfg = config.Config()

    mid = maxArgLength(cfg, args.MID)

    reportResult(cfg.sshHost(), mid)
