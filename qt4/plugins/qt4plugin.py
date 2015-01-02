#    Back In Time
#    Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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


import sys
import os
import pluginmanager
import tools
import logger
import time
import gettext
import _thread
import subprocess


_=gettext.gettext


if not os.getenv( 'DISPLAY', '' ):
    os.putenv( 'DISPLAY', ':0.0' )


class Qt4Plugin( pluginmanager.Plugin ):
    def __init__( self ):
        self.process = None
        self.snapshots = None

    def init( self, snapshots ):
        self.snapshots = snapshots

        if not tools.check_x_server():
            return False
        return True
    
    def is_gui( self ):
        return True

    def on_process_begins( self ):
        try:
            path = os.path.join(tools.get_backintime_path('qt4'), 'qt4systrayicon.py')
            self.process = subprocess.Popen( [ sys.executable, path, self.snapshots.config.get_current_profile() ] )
        except:
            pass

    def on_process_ends( self ):
        if not self.process is None:
            try:
                #self.process.terminate()
                return
            except:
                pass

