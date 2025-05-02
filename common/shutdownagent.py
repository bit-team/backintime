# SPDX-FileCopyrightText: © 2013 Germar Reitze
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# File was split from "common/tools.py".
"""Shutdown the system via DBus"""
import os
import subprocess
import dbus
import logger


class ShutdownAgent:
    """Shutdown the system after the current snapshot has finished."""

    # The order is relevant. Don't modify it without a good reason.
    DBUS_SHUTDOWN = {
        'login1': {
            'bus': 'systembus',
            'service': 'org.freedesktop.login1',
            'objectPath': '/org/freedesktop/login1',
            'method': 'PowerOff',
            'interface': 'org.freedesktop.login1.Manager',
            # False=non-interactive (no confirmation dialog)
            'arguments': (False,)
        },
        'gnome':   {
            'bus': 'sessionbus',
            'service': 'org.gnome.SessionManager',
            'objectPath': '/org/gnome/SessionManager',
            'method': 'Shutdown',  # available: Shutdown, Reboot, Logout
            'interface': 'org.gnome.SessionManager',
            'arguments': ()
            # arg (only with Logout)
            #            0 normal
            #            1 no confirm
            #            2 force
        },
        'kde': {
            'bus': 'sessionbus',
            'service': 'org.kde.ksmserver',
            'objectPath': '/KSMServer',
            'method': 'logout',
            'interface': 'org.kde.KSMServerInterface',
            'arguments': (-1, 2, -1)
            # 1st arg   -1 confirm
            #            0 no confirm
            # 2nd arg   -1 full dialog with default logout
            #            0 logout
            #            1 restart
            #            2 shutdown
            # 3rd arg   -1 wait 30sec
            #            2 immediately
        },
        'xfce': {
            'bus': 'sessionbus',
            'service': 'org.xfce.SessionManager',
            'objectPath': '/org/xfce/SessionManager',
            'method': 'Shutdown',
            # methods    Shutdown
            #            Restart
            #            Suspend (no args)
            #            Hibernate (no args)
            #            Logout (two args)
            'interface': 'org.xfce.Session.Manager',
            'arguments': (True,)
            # arg        True    allow saving
            #            False   don't allow saving
            # 1st arg (only with Logout)
            #            True    show dialog
            #            False   don't show dialog
            # 2nd arg (only with Logout)
            #            True    allow saving
            #            False   don't allow saving
        },
        'mate': {
            'bus': 'sessionbus',
            'service': 'org.mate.SessionManager',
            'objectPath': '/org/mate/SessionManager',
            'method': 'Shutdown',
            # methods    Shutdown
            #            Logout
            'interface': 'org.mate.SessionManager',
            'arguments': ()
            # arg (only with Logout)
            #            0 normal
            #            1 no confirm
            #            2 force
        },
        'e17': {
            'bus': 'sessionbus',
            'service': 'org.enlightenment.Remote.service',
            'objectPath': '/org/enlightenment/Remote/RemoteObject',
            'method': 'Halt',
            # methods    Halt -> Shutdown
            #            Reboot
            #            Logout
            #            Suspend
            #            Hibernate
            'interface': 'org.enlightenment.Remote.Core',
            'arguments': ()
        },
        'e19': {
            'bus': 'sessionbus',
            'service': 'org.enlightenment.wm.service',
            'objectPath': '/org/enlightenment/wm/RemoteObject',
            'method': 'Shutdown',
            # methods    Shutdown
            #            Restart
            'interface': 'org.enlightenment.wm.Core',
            'arguments': ()
        },
    }

    def __init__(self):
        if self._am_i_root():
            self.proxy, self.args = None, None
        else:
            self.proxy, self.args = self._prepair()

        # Dev note (buhtz, 2025-04): Investigate why we need this
        # and who sets it.
        self.activate_shutdown = False
        self.started = False

    def _am_i_root(self) -> bool:
        return os.geteuid() == 0

    def _prepair(self):
        """Try to connect to the given dbus services. If successful it will
        return a callable dbus proxy and those arguments."""

        # Session bus
        try:
            sessionbus = dbus.bus.BusConnection(
                os.environ['DBUS_SESSION_BUS_ADDRESS'])
        except KeyError:
            sessionbus = dbus.SessionBus()

        except dbus.DBusException as exc:
            logger.debug('Exception while connection to session bus for '
                         f'shutdown. {exc}')
            return (None, None)

        # System bus
        try:
            systembus = dbus.SystemBus()

        except dbus.DBusException as exc:
            logger.debug('Exception while connection to session bus for '
                         f'shutdown. {exc}')
            return (None, None)

        # try each desktop environment
        for de, dbus_props in self.DBUS_SHUTDOWN.items():
            logger.debug(f'Try to receive shutdown proxy using "{de}".')

            try:
                if dbus_props['bus'] == 'sessionbus':
                    the_bus = sessionbus
                else:
                    the_bus = systembus

                interface = the_bus.get_object(
                    dbus_props['service'],
                    dbus_props['objectPath'])
                proxy = interface.get_dbus_method(
                    dbus_props['method'],
                    dbus_props['interface'])

                return (proxy, dbus_props['arguments'])

            except dbus.exceptions.DBusException as exc:
                logger.debug(f'{exc} Will try the next one if available.')
                continue

        return (None, None)

    def can_shutdown(self):
        """Indicate if a valid dbus service is available to shutdown system.
        """
        return self.proxy is not None or self._am_i_root()

    def ask_before_quit(self):
        """
        Indicate if the agent is ready to fire and so the application
        shouldn't be closed.

        Dev note (buhtz, 2025-04): Makes not much sense to me, this method.
        Investigate further.
        """
        return self.activate_shutdown and not self.started

    def _shutdown_via_shell(self):
        self.started = True

        with subprocess.Popen(['shutdown', '-h', 'now']) as proc:
            proc.communicate()
            rc = proc.returncode

        return rc

    def _shutdown_via_dbus_proxy(self):
        self.started = True
        return self.proxy(*self.args)

    def shutdown(self):
        """Shutdown via shell command (if root) or using the DBus proxy.

        Returns:
            What?
        """

        # As root
        if self._am_i_root():
            return self._shutdown_via_shell()

        # As user
        if self.proxy is not None:
            self._shutdown_via_dbus_proxy()

        # Dev note (buhtz, 2025-04): Isn't that an undefined state and should
        # raise an Exception?
        # To my research no one who calls this method is checking its return
        # value.
        logger.error('Shutdown not possible because of undefined state. '
                     'Please open a bug report.')
        return False
