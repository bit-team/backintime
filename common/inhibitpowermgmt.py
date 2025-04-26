# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
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
import logger

# Dev note (buhtz, 2025-04): Investigate and get rid of that.
# getting dbus imports to work in Travis CI is a huge pain
# use conditional dbus import
ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'
ON_RTD = os.environ.get('READTHEDOCS', 'None').lower() == 'true'
try:
    import dbus
except ImportError:
    if ON_TRAVIS or ON_RTD:
        # python-dbus doesn't work on Travis yet.
        dbus = None
    else:
        raise

INHIBIT_LOGGING_OUT = 1
INHIBIT_USER_SWITCHING = 2
INHIBIT_SUSPENDING = 4
INHIBIT_IDLE = 8

INHIBIT_DBUS = (
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


def inhibit_suspend(app_id=sys.argv[0],
                    reason='take snapshot',
                    flags=INHIBIT_SUSPENDING | INHIBIT_IDLE):
    """Prevent machine to go to suspend or hibernate.

    Args:
        app_id: Name of the application (default: ``sys.argv[0]``)
        toplevel_xid: Not used anymore.
        reason: Reason as string.
        flags: Unknown.

    Returns:
        A 3-item-tuple with the first item containing the inhibit cookie
        which is used to end the inhibitor.
    """

    # Dev note (buhtz, 2025-04): Get rid of that.
    # if ON_TRAVIS or dbus is None:
    if dbus is None:
        logger.debug(
            f'No suspend on Travis {ON_TRAVIS=} or dbus not available {dbus=}')
        return None

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

    for dbus_props in INHIBIT_DBUS:
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

            # logger.debug('Inhibit Suspend started. '
            #              f'Reason: {reason} Cookie: "{cookie}"')

            return (cookie, bus, dbus_props)

        except dbus.exceptions.DBusException:
            pass

    logger.warning('Inhibit Suspend failed.')

    return None


def uninhibit_suspend(cookie: int,
                      bus: dbus.bus.BusConnection,
                      dbus_props: dict
                      ) -> tuple[int, dbus.bus.BusConnection, dict]:
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
