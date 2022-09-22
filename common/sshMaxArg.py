#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

import random
import string
import subprocess
import socket
import argparse


def randomId(size=6, chars=string.ascii_uppercase + string.digits):
    """
    """
    return ''.join(random.choice(chars) for x in range(size))


def maxArgLength(config, mid=1048320):
    """
    """
    r = round(mid / 2)

    while r > 0:
        ssh = config.sshCommand(
            cmd=['printf', randomId(mid)],
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

            if e.errno == 7:
                reportTest(mid, 'python exception: %s' % e.strerror)
                mid -= r

            else:
                raise

        else:
            l = len(out)

            if l == mid:
                reportTest(mid, 'can be longer')
                mid += r

            else:
                reportTest(mid, 'is to long')
                mid -= r

        r = round(r / 2)

    return mid + 6


def reportTest(mid, msg):
    """
    """
    print('Check length %s:\t%s' % (mid, msg))


def reportResult(host, mid):
    """
    """
    print('Maximum SSH argument length between "%s" and "%s" is %s'
          % (socket.gethostname(), host, mid))


# buhtz: Couldn't find a hint that this script is executed diretly like
# "./sshMaxArg.py". It more seems that is done via "import sshMaxArg"

# if __name__ == '__main__':
#     """
#     """
#     parser = argparse.ArgumentParser(
#         description='Check maximal argument length on SSH connection',
#         formatter_class=argparse.ArgumentDefaultsHelpFormatter
#     )

#     parser.add_argument('MID',
#                         type=int,
#                         nargs='?',
#                         default=1048320,
#                         help='Start checking with MID arg length')

#     args = parser.parse_args()

#     import config

#     cfg = config.Config()
#     mid = maxArgLength(cfg, args.MID)

#     reportResult(cfg.sshHost(), mid)
