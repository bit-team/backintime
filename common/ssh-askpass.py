#!/usr/bin/env python
#    Copyright (c) 2012 Germar Reitze
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

import os
import sys
import password

def get_password(profile_id, mode):
    pw = password.Password()
    return pw.get_password(profile_id, mode)

if __name__ == '__main__':
    try:
        profile_id = os.environ['SSH_ASKPASS_PROFILE_ID']
        mode = os.environ['SSH_ASKPASS_MODE']
    except:
        sys.exit(1)
    print(get_password(profile_id, mode))