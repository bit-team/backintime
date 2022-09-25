#    Copyright (C) 2012-2022 Germar Reitze
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

"""
Helper tool for piping passwords into ssh/sshfs and encfs.
Options are read from environ variables.
"""

import os
import sys
try:
    import gtk
except:
    pass

import password
import password_ipc
import tools
import config

if __name__ == '__main__':
    """
    return password.
    """
    cfg = config.Config()
    tools.envLoad(cfg.cronEnvFile())

    profile_id = os.getenv('ASKPASS_PROFILE_ID', '1')
    mode = os.getenv('ASKPASS_MODE', 'local')

    if mode == 'USER':
        prompt = os.getenv('ASKPASS_PROMPT', None)
        pw = password.Password(cfg)

        print(pw.passwordFromUser(None, prompt=prompt))

        sys.exit(0)

    temp_file = os.getenv('ASKPASS_TEMP')

    if temp_file is None:
        # normal mode, get password from module password
        pw = password.Password(cfg)
        print(pw.password(None, profile_id, mode))

        sys.exit(0)

    # temp mode
    fifo = password_ipc.FIFO(temp_file)
    pw = fifo.read(5)

    if pw:
        print(pw)
