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
import gettext

_=gettext.gettext

def create():
    home = os.path.expanduser('~')
    autostart = os.path.join(home, '.config', 'autostart')
    if not os.path.isdir(autostart):
        os.makedirs(autostart)
    backintime_autostart = os.path.join(autostart, 'backintime.desktop')
    if not os.path.isfile(backintime_autostart):
        print('create autostart file')
        s  = '[Desktop Entry]\n'
        s += 'Version=1.0\n'
        s += 'Name=' + _('Backintime Password Cache\n')
        s += 'Exec=backintime --pw-cache restart\n'
        s += 'Comment=' + _('Cache passwords for non-interactive Backintime cronjobs\n')
        s += 'Icon=gtk-save\n'
        s += 'Terminal=false\n'
        s += 'Type=Application\n'
        with open(backintime_autostart, 'w') as f:
            f.write(s)