# (from BackInTime)
# Copyright (C) 2015-2015 Germar Reitze
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# (from jockey)
# (c) 2008 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# (from python-dbus-docs)
# Copyright (C) 2004-2006 Red Hat Inc. <http://www.redhat.com/>
# Copyright (C) 2005-2007 Collabora Ltd. <http://www.collabora.co.uk/>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy,
# modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#
# This file was modified by David D. Lowe in 2009.
# To the extent possible under law, David D. Lowe has waived all 
# copyright and related or neighboring rights to his modifications to
# this file under this license: http://creativecommons.org/publicdomain/zero/1.0/

import os
import time
import re
from tempfile import TemporaryFile
from subprocess import Popen, PIPE
try:
    import pwd
except importError:
    pwd = None

import dbus
import dbus.service
import dbus.mainloop.qt
from PyQt4.QtCore import QCoreApplication

UDEV_RULES_PATH = '/etc/udev/rules.d/99-backintime-%s.rules'

class InvalidChar(dbus.DBusException):
    _dbus_error_name = 'net.launchpad.backintime.InvalidChar'

class PermissionDeniedByPolicy(dbus.DBusException):
    _dbus_error_name = 'com.ubuntu.DeviceDriver.PermissionDeniedByPolicy'

class UdevRules(dbus.service.Object):
    def __init__(self, conn=None, object_path=None, bus_name=None):
        super(UdevRules, self).__init__(conn, object_path, bus_name)
        
        # the following variables are used by _checkPolkitPrivilege
        self.dbus_info = None
        self.polkit = None
        self.enforce_polkit = True

        self.tmpDict = {}

        #find su path
        proc = Popen(['which', 'su'], stdout = PIPE)
        self.su = proc.communicate()[0].strip().decode()
        if proc.returncode:
            self.su = '/bin/su'

    @dbus.service.method("net.launchpad.backintime.serviceHelper.UdevRules",
                         in_signature='ss', out_signature='',
                         sender_keyword='sender', connection_keyword='conn')
    def addRule(self, cmd, uuid, sender=None, conn=None):
        """Receive command and uuid and create an Udev rule out of this.
        This is done on the service side to prevent malicious code to
        run as root.
        """
        #prevent breaking out of su command
        chars = re.findall(r'[\'"$\{\}\[\]\(\);#\t\n\r\f\v\\]', cmd)
        if chars:
            raise InvalidChar("Parameter 'cmd' contains invalid character(s) %s"
                              % '|'.join(set(chars)) )
        #only allow relevant chars in uuid
        chars = re.findall(r'[^a-zA-Z0-9-]', uuid)
        if chars:
            raise InvalidChar("Parameter 'uuid' contains invalid character(s) %s"
                              % '|'.join(set(chars)) )

        user = self._getConnectionUser(sender, conn)
        #create su command
        sucmd = "%s - '%s' -c '%s'" %(self.su, user, cmd)
        #create Udev rule
        rule = 'ACTION=="add", ENV{ID_FS_UUID}=="%s", RUN+="%s"\n' %(uuid, sucmd)

        #store rule in tmp file
        self._senderTmpFile(sender, conn).write(rule)

    @dbus.service.method("net.launchpad.backintime.serviceHelper.UdevRules",
                         in_signature='', out_signature='b',
                         sender_keyword='sender', connection_keyword='conn')
    def save(self, sender=None, conn=None):
        """Save rules to destiantion file after user authenticated as admin.
        This will first check if there are any changes between 
        temporary added rules and current rules in destiantion file.
        Returns False if files are identical or no rules to be installed.
        """
        user = self._getConnectionUser(sender, conn)
        tmp = self._senderTmpFile(sender, conn)
        tmp.seek(0)
        tmpRules = tmp.read()
        tmp.close()
        #delete rule if no rules in tmp
        if not tmpRules:
            self.delete(sender, conn)
            return False
        #return False if rule already exist.
        if os.path.exists(UDEV_RULES_PATH % user):
            with open(UDEV_RULES_PATH % user, 'r') as f:
                if tmpRules == f.read():
                    return False
        #auth to save changes
        self._checkPolkitPrivilege(sender, conn, 'net.launchpad.backintime.UdevRuleSave')
        with open(UDEV_RULES_PATH % user, 'w') as f:
            f.write(tmpRules)
        return True

    @dbus.service.method("net.launchpad.backintime.serviceHelper.UdevRules",
                         in_signature='', out_signature='',
                         sender_keyword='sender', connection_keyword='conn')
    def delete(self, sender=None, conn=None):
        """Delete existing Udev rule
        """
        user = self._getConnectionUser(sender, conn)
        if os.path.exists(UDEV_RULES_PATH % user):
            #auth to delete rule
            self._checkPolkitPrivilege(sender, conn, 'net.launchpad.backintime.UdevRuleDelete')
            os.remove(UDEV_RULES_PATH % user)

    @classmethod
    def _logInFile(klass, filename, string):
        date = time.asctime(time.localtime())
        with open(filename, "a") as ff:
            ff.write("%s : %s\n" %(date,str(string)))

    def _senderTmpFile(self, sender, conn):
        senderName = self._getConnectionUser(sender, conn)
        if not senderName in self.tmpDict or self.tmpDict[senderName].closed:
            self.tmpDict[senderName] = TemporaryFile(mode = 'r+')
        return self.tmpDict[senderName]

    def _initDbusInfo(self, sender, conn):
        if self.dbus_info is None:
            self.dbus_info = dbus.Interface(conn.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus/Bus', False), 'org.freedesktop.DBus')

    def _initPolkit(self):
        if self.polkit is None:
            self.polkit = dbus.Interface(dbus.SystemBus().get_object(
                'org.freedesktop.PolicyKit1',
                '/org/freedesktop/PolicyKit1/Authority', False),
                'org.freedesktop.PolicyKit1.Authority')

    def _getConnectionUser(self, sender, conn):
        self._initDbusInfo(sender, conn)
        uid = self.dbus_info.GetConnectionUnixUser(sender)
        if pwd:
            return pwd.getpwuid(uid).pw_name
        else:
            return uid

    def _getConnectionPid(self, sender, conn):
        self._initDbusInfo(sender, conn)
        return self.dbus_info.GetConnectionUnixProcessID(sender)

    def _checkPolkitPrivilege(self, sender, conn, privilege):
        # from jockey
        '''Verify that sender has a given PolicyKit privilege.

        sender is the sender's (private) D-BUS name, such as ":1:42"
        (sender_keyword in @dbus.service.methods). conn is
        the dbus.Connection object (connection_keyword in
        @dbus.service.methods). privilege is the PolicyKit privilege string.

        This method returns if the caller is privileged, and otherwise throws a
        PermissionDeniedByPolicy exception.
        '''
        if sender is None and conn is None:
            # called locally, not through D-BUS
            return
        if not self.enforce_polkit:
            # that happens for testing purposes when running on the session
            # bus, and it does not make sense to restrict operations here
            return

        # get peer PID
        pid = self._getConnectionPid(sender, conn)

        # query PolicyKit
        self._initPolkit()
        try:
            # we don't need is_challenge return here, since we call with AllowUserInteraction
            (is_auth, _, details) = self.polkit.CheckAuthorization(
                    ('unix-process', {'pid': dbus.UInt32(pid, variant_level=1),
                    'start-time': dbus.UInt64(0, variant_level=1)}), 
                    privilege, {'': ''}, dbus.UInt32(1), '', timeout=600)
        except dbus.DBusException as e:
            if e._dbus_error_name == 'org.freedesktop.DBus.Error.ServiceUnknown':
                # polkitd timed out, connect again
                self.polkit = None
                return self._checkPolkitPrivilege(sender, conn, privilege)
            else:
                raise

        if not is_auth:
            raise PermissionDeniedByPolicy(privilege)

if __name__ == '__main__':
    dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)

    app = QCoreApplication([])

    bus = dbus.SystemBus()
    name = dbus.service.BusName("net.launchpad.backintime.serviceHelper", bus)
    object = UdevRules(bus, '/UdevRules')

    print("Running BIT service.")
    app.exec_()
