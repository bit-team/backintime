#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import subprocess
import dbus
import pluginmanager


class NotifyPlugin(pluginmanager.Plugin):
    def __init__(self):
        self.user = ''

        try:
            self.user = os.getlogin()
        except:
            pass

        if not self.user:
            try:
                self.user = os.environ['USER']
            except:
                pass

        if not self.user:
            try:
                self.user = os.environ['LOGNAME']
            except:
                pass

    def isGui(self):
        return True

    def message(self, profile_id, profile_name, level, message, timeout):
        try:
            notify_interface = dbus.Interface(object=dbus.SessionBus().get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications"), dbus_interface="org.freedesktop.Notifications")
        except dbus.exceptions.DBusException:
            return
        if 1 == level:
            if timeout > 0:
                timeout = 1000 * timeout
            else:
                timeout = -1 # let timeout default to notification server settings
            title = "Back In Time (%s) : %s" % (self.user, profile_name)
            message = message.replace("\n", ' ')
            message = message.replace("\r", '')
            try:
                notify_interface.Notify("Back In Time", 0, "", title, message, [], {}, timeout)
            except dbus.exceptions.DBusException:
                pass
        return
