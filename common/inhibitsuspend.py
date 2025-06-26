# SPDX-FileCopyrightText: © 2014 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Split from common/tools.py
"""Manage inhibition of suspend mode via DBus.
"""
import os
import sys
import dbus
import logger


class InhibitSuspend:
    """Context manager to prevent machine to go to suspend or hibernate."""

    def __init__(self, reason: str = None, app_id: str = None):
        self.app_id = app_id if app_id else sys.argv[0]
        self.reason = reason if reason else 'take snapshot'
        self.cookie = None
        self.bus = None
        self.interface = None
        self.file_descs = []

        # Order is important. Don't change it for no good reason.
        self.providers = {
            'freedesktop.login1':
                self._inhibit_via_freedesktop_login_one,
            'freedesktop.PowerManagment':
                self._inhibit_via_freedesktop_power_management,
            'gnome':
                self._inhibit_via_gnome,
            'mate':
                self._inhibit_via_mate,
        }

    def _open_system_bus(self):
        try:
            self.bus = dbus.SystemBus()
        except dbus.exceptions.DBusException as exc:
            logger.error(f'Unable to open DBus system bus. {exc}')

    def _open_session_bus(self):
        # Fixes #1592 (BiT hangs as root when trying to establish a dbus user
        # session connection)
        # Side effect: In BiT <= 1.4.1 root still tried to connect to the dbus
        # user session and it may have worked sometimes (without logging we
        # don't know) so as root suspend can no longer inhibited.
        if os.geteuid() == 0:  # is root
            # Dev note (buhtz, 2025-04): But does this need to be a "Fail"?
            logger.debug(
                'Inhibit Suspend aborted because BIT was started as root.')
            return

        # Connect directly to the socket instead of dbus.SessionBus because
        # the dbus.SessionBus was initiated before we loaded the environ
        # variables and might not work.
        try:
            self.bus = dbus.bus.BusConnection(
                os.environ['DBUS_SESSION_BUS_ADDRESS'])
        except KeyError:
            pass
        except dbus.exceptions.DBusException as exc:
            logger.error(f'Unable to open DBus session bus. {exc}')

        if self.bus:
            return

        try:
            # This code may hang forever (if BIT is run as root via cron
            # job and no user is logged in). See #1592
            self.bus = dbus.SessionBus()
        except dbus.exceptions.DBusException as exc:
            logger.error(f'Unable to open DBus session bus. {exc}')

    def _inhibit_via_freedesktop_login_one(self):
        """Inhibit using system bus and login1 method.

        Method should be available on modern systems with and without
        systemd. Uninhibition is done via closing a file descriptor.
        """
        self._open_system_bus()

        if not self.bus:
            return False

        try:
            obj = self.bus.get_object(
                bus_name='org.freedesktop.login1',
                object_path='/org/freedesktop/login1')

            iface = dbus.Interface(
                object=obj,
                dbus_interface='org.freedesktop.login1.Manager')

            # Inhibition is active until this file descriptor is closed
            file_desc = iface.Inhibit(
                'sleep', self.app_id, self.reason, "block").take()

        except dbus.DBusException as exc:
            logger.debug(f'Inhibition (via "login1") failed: {exc}')
            return False

        self.file_descs.append(file_desc)

        return True

    def _inhibit_generic_in_session(self,
                                    bus_name: str,
                                    object_path: str,
                                    dbus_interface: str,
                                    args: tuple) -> bool:
        if not self.bus:
            return False

        try:
            obj = self.bus.get_object(
                bus_name=bus_name, object_path=object_path)

            self.interface = dbus.Interface(
                object=obj, dbus_interface=dbus_interface)

            self.cookie = self.interface.Inhibit(*args)

        except dbus.DBusException as exc:
            logger.debug(f'Inhibition (via "{bus_name}") failed: {exc}')
            return False

        return True

    def _inhibit_via_freedesktop_power_management(self):
        return self._inhibit_generic_in_session(
            bus_name='org.freedesktop.PowerManagement',
            object_path='/org/freedesktop/Inhibit',
            dbus_interface='org.freedesktop.PowerManager.Inhibit',
            args=(
                self.app_id,
                self.reason
            )
        )

    def _inhibit_via_gnome(self):
        return self._inhibit_generic_in_session(
            bus_name='org.gnome.SessionManager',
            object_path='/org/gnome/SessionManager',
            dbus_interface='org.gnome.SessionManager.Inhibit',
            args=(
                self.app_id,
                0,  # xwindow-id not relevant today
                self.reason,
                dbus.UInt32(4),  # 4 = SUSPEND
            )
        )

    def _inhibit_via_mate(self):
        return self._inhibit_generic_in_session(
            bus_name='org.mate.SessionManager',
            object_path='/org/mate/SessionManager',
            dbus_interface='org.mate.SessionManager.Inhibit',
            args=(
                self.app_id,
                0,  # xwindow-id not relevant today
                self.reason,
                dbus.UInt32(4),  # 4 = SUSPEND
            )
        )

    def __enter__(self):
        failed = []
        for name, inhibit in self.providers.items():
            # logger.debug(f'Try inhibiting suspend mode via "{name}"')

            result = inhibit()

            if result:
                logger.info(f'Suspend mode inhibited via "{name}"')
                break

            failed.append(name)

        result = True
        if failed:
            if result:
                logger.debug('Inhibiting suspend mode failed '
                             f'beforehand with {failed}')
            else:
                logger.error('Inhibiting suspend mode failed. '
                             f'Tried with {failed}')

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        try:
            if self.cookie:
                self.interface.UnInhibit(self.cookie)

            for fd in self.file_descs:
                os.close(fd)

        except dbus.exceptions.DBusException as exc:
            logger.error(f'Release suspend mode inhibition failed: {exc}')

        else:
            if self.cookie or self.file_descs:
                logger.info('Released suspend mode inhibition')
