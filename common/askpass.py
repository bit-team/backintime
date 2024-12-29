# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
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
        print(pw.passwordFromUser(None, prompt = prompt))
        sys.exit(0)

    temp_file = os.getenv('ASKPASS_TEMP')
    if temp_file is None:
        #normal mode, get password from module password
        pw = password.Password(cfg)
        print(pw.password(None, profile_id, mode))
        sys.exit(0)

    #temp mode
    fifo = password_ipc.FIFO(temp_file)
    pw = fifo.read(5)

    if pw:
        print(pw)
