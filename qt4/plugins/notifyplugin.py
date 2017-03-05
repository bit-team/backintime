#    Back In Time
#    Copyright (C) 2008-2017 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import pluginmanager
import gettext

_=gettext.gettext


class NotifyPlugin( pluginmanager.Plugin ):
    def __init__( self ):
        self.user = ''

        try:
            self.user = os.getlogin()
        except:
            pass

        if not self.user:
            try:
                user = os.environ['USER']
            except:
                pass

        if not self.user:
            try:
                user = os.environ['LOGNAME']
            except:
                pass

    def init( self, snapshots ):
        return True

    def is_gui( self ):
        return True

    def on_process_begins( self ):
        pass

    def on_process_ends( self ):
        pass

    def on_error( self, code, message ):
        return

    def on_new_snapshot( self, snapshot_id, snapshot_path ):
        return

    def on_message( self, profile_id, profile_name, level, message, timeout ):
        if 1 == level:
            cmd = "notify-send "
            if timeout > 0:
                cmd = cmd + " -t %s" % (1000 * timeout)

            title = "Back In Time (%s) : %s" % (self.user, profile_name)
            message = message.replace("\n", ' ')
            message = message.replace("\r", '')

            cmd = cmd + " \"%s\" \"%s\"" % (title, message)
            print(cmd)
            os.system(cmd)
        return
