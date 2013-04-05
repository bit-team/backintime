#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
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
import thread
import subprocess


_=gettext.gettext


if len( os.getenv( 'DISPLAY', '' ) ) == 0:
    os.putenv( 'DISPLAY', ':0.0' )


class KDE4Plugin( pluginmanager.Plugin ):
    def __init__( self ):
        self.process = None
        self.snapshots = None

    def init( self, snapshots ):
        self.snapshots = snapshots

        if not tools.process_exists( 'ksmserver' ):
            return False

        if not tools.check_x_server():
            return False

        if len( tools.read_command_output( "ksmserver --version | grep \"KDE: 4.\"" ) ) <= 0:
            return False

        return True
    
    def is_gui( self ):
        return True

    def on_process_begins( self ):
        try:
            self.process = subprocess.Popen( [ sys.executable, '/usr/share/backintime/kde4/kde4systrayicon.py', self.snapshots.config.get_current_profile() ] )
        except:
            pass

    def on_process_ends( self ):
        if not self.process is None:
            try:
                #self.process.terminate()
                return
            except:
                pass

