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


import os
import os.path
import pluginmanager
import tools
import logger
import gettext

_=gettext.gettext


class UserScriptsPlugin( pluginmanager.Plugin ):
    def __init__( self ):
        return

    def init( self, snapshots ):
        self.config = snapshots.config
        return True

    def notify_script( self, path, args = '' ):
        if path == None:
            return
        if len( path ) <= 0:
            return

        logger.info( "[UserScriptsPlugin.notify_script] %s %s" % ( path, args ) )
        os.system( "sh \"%s\" %s" % ( self.callback, args ) )

    def on_process_begins( self ):
        self.notify_script( self.config.get_take_snapshot_user_script_before() )

    def on_process_ends( self ):
        self.notify_script( self.config.get_take_snapshot_user_script_after() )

    def on_error( self, code, message ):
        code = str( code )
        if len( message ) > 0:
            code = code + " \"" + message + "\""

        self.notify_script( self.config.get_take_snapshot_user_script_error(), code )

    def on_new_snapshot( self, snapshot_id, snapshot_path ):
        self.notify_script( self.config.get_take_snapshot_user_script_new_snapshot(), "%s \"%s\"" % ( snapshot_id, snapshot_path ) )

