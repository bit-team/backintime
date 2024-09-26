# SPDX-FileCopyrightText: © 2007 Sander Marechal
# SPDX-FileCopyrightText: © 2016 Germar Reitze
#
# SPDX-License-Identifier: CC0-1.0
#
# This file is released under Creative Commons Zero 1.0 (CC0-1.0) and part of
# the program "Back In Time". The program as a whole is released under GNU
# General Public License v2 or any later version (GPL-2.0-or-later).
# See file/folder LICENSE or
# go to <https://spdx.org/licenses/CC0-1.0.html>
# and <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""A generic daemon class.

    Original from:
    http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python
    Copyright © 2007 Sander Marechal
    License CC0 or Public Domain

Notes about the license (by buhtz, 2024-08-13):

    The linked blog article is licensed under CC BY-SA 3.0 which is not
    compatible with GPLv2 used by Back In Time. But the original author
    clarified that the code used in the blog article is public domain.

See this original email.

    Date: Tue, 13 Aug 2024 14:19:48 +0200
    Subject: Re: Your Daemon code in Back In Time
    Message-ID: <06084b4b-2293-4a28-a290-96fa4d309a8b@email.android.com>
    In-Reply-To: <3d57067b590e271ce6f361ce4147ac08@posteo.de>
    From: Sander Marechal <sander@marechal.io>
    To: c.buhtz@posteo.jp

    Hello Christian,

    As far as I am concerned that daemon code is public domain. You can use it
    under any license you want. There are only a few ways to start a daemon so
    technically the code can't be copyrighted as far as I am concerned. That CC
    license is just for my articles in general.

    Kind regards,

    --
    Sander Marechal
"""
import sys
import os
import signal
import atexit
import errno
from time import sleep
import logger
from applicationinstance import ApplicationInstance


def fdDup(old, new_fd, mode='w'):
    """Duplicate file descriptor `old` to `new_fd` and closing the latter
    first.

    Used to redirect stdin, stdout and stderr from daemonized threads.

    Args:
        old (str): Path to the old file (e.g. /dev/stdout).
        new_fd (_io.TextIOWrapper): File object for the new file.
        mode (str): Mode in which the old file should be opened.
    """
    try:
        fd = open(old, mode)
        os.dup2(fd.fileno(), new_fd.fileno())

    except OSError as e:
        logger.debug('Failed to redirect {}: {}'.format(old, str(e)))


class Daemon:
    """A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self,
                 pidfile=None,
                 stdin='/dev/null',
                 stdout='/dev/stdout',
                 stderr='/dev/null',
                 umask=0o022):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.umask = umask
        if pidfile:
            self.appInstance = ApplicationInstance(
                pidfile, autoExit=False, flock=False)

    def daemonize(self):
        """Converts the current process into a daemon.

        It is a process running in the background, sending a SIGTERM signal to
        the current process. This is done via the UNIX double-fork magic, see
        Stevens' 'Advanced Programming in the UNIX Environment' for details
        (ISBN 0201563177) and this explanation:
        https://stackoverflow.com/a/6011298
        """
        try:
            pid = os.fork()
            logger.debug('first fork pid: {}'.format(pid), self)

            if pid > 0:
                # exit first parent
                sys.exit(0)

        except OSError as e:
            logger.error("fork #1 failed: %d (%s)" % (e.errno, str(e)), self)
            sys.exit(1)

        # Decouple from parent environment
        logger.debug('decouple from parent environment', self)
        os.chdir("/")
        os.setsid()
        os.umask(self.umask)

        # Do second fork
        try:
            pid = os.fork()
            logger.debug('second fork pid: {}'.format(pid), self)

            if pid > 0:
                # exit from second parent
                sys.exit(0)

        except OSError as e:
            logger.error("fork #2 failed: %d (%s)" % (e.errno, str(e)), self)
            sys.exit(1)

        # redirect standard file descriptors
        logger.debug('redirect standard file descriptors', self)

        sys.stdout.flush()
        sys.stderr.flush()
        fdDup(self.stdin, sys.stdin, 'r')
        fdDup(self.stdout, sys.stdout, 'w')
        fdDup(self.stderr, sys.stderr, 'w')

        signal.signal(signal.SIGTERM, self.cleanupHandler)

        if self.pidfile:
            atexit.register(self.appInstance.exitApplication)

            # write pidfile
            logger.debug('write pidfile', self)
            self.appInstance.startApplication()

    def cleanupHandler(self, signum, frame):
        if self.pidfile:
            self.appInstance.exitApplication()
        sys.exit(0)

    def start(self):
        """Start the daemon."""

        # Check for a pidfile to see if the daemon already runs
        if self.pidfile and not self.appInstance.check():
            logger.error(f'pidfile {self.pidfile} already exists. '
                         'Daemon already running?\n', self)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """Stop the daemon."""
        if not self.pidfile:
            logger.debug(
                "Unattended daemon can't be stopped. No PID file", self)
            return

        # Get the pid from the pidfile
        pid = self.appInstance.readPidFile()[0]

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            logger.error(message % self.pidfile, self)
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while True:
                os.kill(pid, signal.SIGTERM)
                sleep(0.1)

        except OSError as err:

            if err.errno == errno.ESRCH:
                # No such process
                self.appInstance.exitApplication()

            else:
                logger.error(str(err), self)
                sys.exit(1)

    def restart(self):
        """Restart the daemon."""
        self.stop()
        self.start()

    def reload(self):
        """Send SIGHUP signal to process."""
        if not self.pidfile:
            logger.debug(
                "Unattended daemon can't be reloaded. No PID file", self)
            return

        # Get the pid from the pidfile
        pid = self.appInstance.readPidFile()[0]

        if not pid:
            logger.error(f'pidfile {self.pidfile} does not exist. '
                         'Daemon not running?\n', self)
            return

        # Try killing the daemon process
        try:
            os.kill(pid, signal.SIGHUP)

        except OSError as err:

            if err.errno == errno.ESRCH:
                # no such process
                self.appInstance.exitApplication()

            else:
                sys.stderr.write(str(err))
                sys.exit(1)

    def status(self):
        """Return status."""
        if not self.pidfile:
            logger.debug(
                "Unattended daemon can't be checked. No PID file", self)
            return

        return not self.appInstance.check()

    def run(self):
        """Override this method when subclass ``Daemon``. It will be called
        after the process has been daemonized by ``start()`` or ``restart()``.
        """
        pass
