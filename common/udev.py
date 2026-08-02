# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raack
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Split from tools.py
"""Udev related module to manage scheduled backups triggered by pluged in
storage devices (e.g. USB sticks).
"""
import logger
from exceptions import (InvalidChar,
                        InvalidCmd,
                        LimitExceeded,
                        PermissionDeniedByPolicy,
                        Timeout)

try:
    import dbus
except ImportError:
    import os
    # getting dbus imports to work in Travis CI is a huge pain
    # use conditional dbus import
    ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'
    ON_RTD = os.environ.get('READTHEDOCS', 'None').lower() == 'true'

    if ON_TRAVIS or ON_RTD:
        # python-dbus doesn't work on Travis yet.
        dbus = None
    else:
        raise

# Workaround:
# While unittesting and without regular invocation of BIT the GNU gettext
# class-based API isn't setup yet.
try:
    _('Warning')
except NameError:
    _ = lambda val: val


class SetupUdev:
    """
    Setup Udev rules for starting BackInTime when a drive get connected.
    This is done by serviceHelper.py script (included in backintime-qt)
    running as root though DBus.
    """
    CONNECTION = 'net.launchpad.backintime.serviceHelper'
    OBJECT = '/UdevRules'
    INTERFACE = 'net.launchpad.backintime.serviceHelper.UdevRules'
    MEMBERS = ('addRule', 'save', 'delete')

    def __init__(self):
        if dbus is None:
            self.isReady = False
            return

        try:
            bus = dbus.SystemBus()
            conn = bus.get_object(SetupUdev.CONNECTION, SetupUdev.OBJECT)
            self.iface = dbus.Interface(conn, SetupUdev.INTERFACE)
            # Dummy message to catch org.freedesktop.DBus.Error.AccessDenied
            # See #2366
            self.iface.clean()

        except dbus.exceptions.DBusException as exc:
            user_msg = (
                'Some profiles cannot be checked or edited because automatic '
                'device detection (via Udev) is unavailable.'
            )
            debug_msg = (
                'Failed connection to Udev serviceHelper daemon '
                f'via D-Bus "{exc.get_dbus_name()}" | '
                f'Message: "{exc.get_dbus_message()}"'
            )
            logger.debug(debug_msg)

            logger.warning(user_msg)

            conn = None

        self.isReady = bool(conn)

    def addRule(self, cmd, uuid):
        """Prepare rules in serviceHelper.py
        """
        if not self.isReady:
            return

        try:
            return self.iface.addRule(cmd, uuid)

        except dbus.exceptions.DBusException as exc:
            err_prefix = 'net.launchpad.backintime.'
            if exc._dbus_error_name == f'{err_prefix}InvalidChar':
                raise InvalidChar(str(exc)) from exc

            elif exc._dbus_error_name == f'{err_prefix}InvalidCmd':
                raise InvalidCmd(str(exc)) from exc

            elif exc._dbus_error_name == f'{err_prefix}LimitExceeded':
                raise LimitExceeded(str(exc)) from exc

            else:
                raise

    def save(self):
        """Save rules with serviceHelper.py after authentication.

        If no rules where added before this will delete current rule.
        """
        if not self.isReady:
            return

        try:
            return self.iface.save()

        except dbus.exceptions.DBusException as err:
            dbus_name = err.get_dbus_name()

            if (dbus_name
                    == 'com.ubuntu.DeviceDriver.PermissionDeniedByPolicy'):
                raise PermissionDeniedByPolicy(str(err)) from err

            if dbus_name == 'org.freedesktop.DBus.Error.NoReply':
                raise Timeout() from err

            raise

    def clean(self):
        """Clean up remote cache.
        """
        if not self.isReady:
            return

        self.iface.clean()
