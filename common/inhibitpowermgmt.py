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
from typing import Optional
import dbus
import logger

FLAG_LOGGING_OUT = 1
FLAG_USER_SWITCHING = 2
FLAG_SUSPENDING = 4
FLAG_IDLE = 8

_DBUS_PROVIDERS = (
    {
        'service': 'org.freedesktop.PowerManagement',
        'objectPath': '/org/freedesktop/PowerManagement/Inhibit',
        'methodSet': 'Inhibit',
        'methodUnSet': 'UnInhibit',
        'interface': 'org.freedesktop.PowerManagement.Inhibit',
        'arguments': (0, 2)
    },
    {
        'service': 'org.gnome.SessionManager',
        'objectPath': '/org/gnome/SessionManager',
        'methodSet': 'Inhibit',
        'methodUnSet': 'Uninhibit',
        'interface': 'org.gnome.SessionManager',
        'arguments': (0, 1, 2, 3)
    },
    {
        'service': 'org.mate.SessionManager',
        'objectPath': '/org/mate/SessionManager',
        'methodSet': 'Inhibit',
        'methodUnSet': 'Uninhibit',
        'interface': 'org.mate.SessionManager',
        'arguments': (0, 1, 2, 3)
    },
)


def inhibit_suspend(app_id: str = sys.argv[0],
                    reason: str = 'take snapshot',
                    flags: int = FLAG_SUSPENDING | FLAG_IDLE
                    ) -> Optional[tuple[int, dbus.bus.BusConnection, dict]]:
    """Prevent machine to go to suspend or hibernate.

    Args:
        app_id: Name of the application.
        reason: Reason as string.
        flags: Unknown.

    Returns:
        A 3-item-tuple with the first item containing the inhibit cookie
        which is used to end the inhibitor.
    """

    # Fixes #1592 (BiT hangs as root when trying to establish a dbus user
    # session connection)
    # Side effect: In BiT <= 1.4.1 root still tried to connect to the dbus user
    #              session and it may have worked sometimes (without logging we
    #              don't know) so as root suspend can no longer inhibited.
    if os.geteuid() == 0:  # is root
        # Dev note (buhtz, 2025-04): But does this need to be a "Fail"?
        logger.debug('Inhibit Suspend failed because BIT was started as root.')
        return None

    if not app_id:
        app_id = 'backintime'

    for dbus_props in _DBUS_PROVIDERS:
        try:
            # Connect directly to the socket instead of dbus.SessionBus because
            # the dbus.SessionBus was initiated before we loaded the environ
            # variables and might not work.
            if 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
                bus = dbus.bus.BusConnection(
                    os.environ['DBUS_SESSION_BUS_ADDRESS'])
            else:
                # This code may hang forever (if BIT is run as root via cron
                # job and no user is logged in). See #1592
                bus = dbus.SessionBus()

            interface = bus.get_object(
                dbus_props['service'], dbus_props['objectPath'])

            proxy = interface.get_dbus_method(
                dbus_props['methodSet'], dbus_props['interface'])

            cookie = proxy(*[
                (app_id,
                 0,  # dbus.UInt32(toplevel_xid),
                 reason,
                 dbus.UInt32(flags))[i]
                for i in dbus_props['arguments']
            ])

            return (cookie, bus, dbus_props)

        except dbus.exceptions.DBusException:
            pass

    logger.warning('Inhibit Suspend failed.')

    return None


def uninhibit_suspend(cookie: int,
                      bus: dbus.bus.BusConnection,
                      dbus_props: dict
                      ) -> Optional[tuple[int, dbus.bus.BusConnection, dict]]:
    """Release inhibit"""

    try:
        interface = bus.get_object(
            dbus_props['service'], dbus_props['objectPath'])
        proxy = interface.get_dbus_method(
            dbus_props['methodUnSet'], dbus_props['interface'])
        proxy(cookie)
        logger.debug('Release inhibit Suspend')

        return None

    except dbus.exceptions.DBusException:
        logger.warning('Release inhibit Suspend failed.')

        return (cookie, bus, dbus_props)


class InhibitSuspend:
    """Context manager to prevent machine to go to suspend or hibernate."""

    def __init__(self, reason: str, app_id: str = None):
        self.app_id = app_id if app_id else sys.argv[0]
        self.reason = reason
        self.cookie = None
        self.bus = None
        self.props = None

    def __enter__(self):

        result = inhibit_suspend(
            app_id=self.app_id,
            reason=self.reason,
            flags=FLAG_SUSPENDING | FLAG_IDLE)

        if result is not None:
            self.cookie, self.bus, self.props = result

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.cookie is None:
            return

        uninhibit_suspend(cookie=self.cookie,
                          bus=self.bus,
                          dbus_props=self.props)
