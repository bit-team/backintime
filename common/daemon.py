# SPDX-FileCopyrightText: © 2007 Sander Marechal
# SPDX-FileCopyrightText: © 2016 Germar Reitze
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: CC0-1.0
#
# This file is released under Creative Commons Zero 1.0 (CC0-1.0) and part of
# the program "Back In Time". The program as a whole is released under GNU
# General Public License v2 or any later version (GPL-2.0-or-later).
# See LICENSES directory or
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
import io
import signal
import atexit
import errno
from time import sleep
import logger
from applicationinstance import ApplicationInstance


def _duplicate_fd(old_fd: str, new_fd: io.TextIOWrapper, mode: str = 'w'
                  ) -> None:
    """Duplicate a file descriptor and close it after.

    Used to redirect stdin, stdout and stderr from daemonized threads.

    Args:
        old_fd: Path to the old file (e.g. /dev/stdout).
        new_fd (_io.TextIOWrapper): File object for the new file.
        mode (str): Mode in which the old file should be opened.
    """
    try:
        # pylint: disable-next=unspecified-encoding
        with open(file=old_fd, mode=mode, encoding=None) as fd:
            os.dup2(fd.fileno(), new_fd.fileno())

    except OSError as exc:
        logger.error(f'Failed to redirect {old_fd}: {exc}')


class Daemon:
    """A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """

    def __init__(self,  # pylint: disable=R0913,R0917
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
            self.app_instance = ApplicationInstance(
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
            logger.debug(f'first fork pid: {pid}', self)

            if pid > 0:
                # exit first parent
                sys.exit(0)

        except OSError as exc:
            logger.error(f'fork #1 failed: {exc.errno} ({exc})', self)
            sys.exit(1)

        # Decouple from parent environment
        # logger.debug('decouple from parent environment', self)
        os.chdir('/')
        os.setsid()
        os.umask(self.umask)

        # Do second fork
        try:
            pid = os.fork()
            logger.debug(f'second fork pid: {pid}', self)

            if pid > 0:
                # exit from second parent
                sys.exit(0)

        except OSError as exc:
            logger.error(f'fork #2 failed: {exc.errno} ({exc})', self)
            sys.exit(1)

        # redirect standard file descriptors
        # logger.debug('redirect standard file descriptors', self)

        sys.stdout.flush()
        sys.stderr.flush()
        _duplicate_fd(self.stdin, sys.stdin, 'r')
        _duplicate_fd(self.stdout, sys.stdout, 'w')
        _duplicate_fd(self.stderr, sys.stderr, 'w')

        signal.signal(signal.SIGTERM, self.cleanup_handler)

        if self.pidfile:
            atexit.register(self.app_instance.exitApplication)

            # write pidfile
            # logger.debug('write pidfile', self)
            self.app_instance.startApplication()

    def cleanup_handler(self, _signum, _frame):
        """Handle process termination."""
        if self.pidfile:
            self.app_instance.exitApplication()

        sys.exit(0)

    def start(self):
        """Start the daemon."""

        # Check for a pidfile to see if the daemon already runs
        if self.pidfile and not self.app_instance.check():
            logger.error(f'pidfile {self.pidfile} already exists. '
                         'Daemon already running?', self)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """Stop the daemon."""

        if not self.pidfile:
            logger.warning(
                'Unattended daemon can not be stopped. No PID file.', self)
            return

        # Get the pid from the pidfile
        pid = self.app_instance.readPidFile()[0]

        if not pid:
            logger.error(
                f'pidfile {self.pidfile} does not exist. Daemon not running?',
                self)
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while True:  # <-- Why?
                os.kill(pid, signal.SIGTERM)
                sleep(0.1)

        except OSError as err:

            if err.errno == errno.ESRCH:
                # No such process
                self.app_instance.exitApplication()

            else:
                logger.error(f'Unable to stop process with pid {pid}: {err}',
                             self)
                sys.exit(1)

    def restart(self):
        """Restart the daemon."""
        self.stop()
        self.start()

    def reload(self):
        """Send SIGHUP signal to process."""
        if not self.pidfile:
            logger.warning(
                "Unattended daemon can't be reloaded. No PID file", self)
            return

        # Get the pid from the pidfile
        pid = self.app_instance.readPidFile()[0]

        if not pid:
            logger.error(f'pidfile {self.pidfile} does not exist. '
                         'Daemon not running?', self)
            return

        # Try killing the daemon process
        try:
            os.kill(pid, signal.SIGHUP)

        except OSError as err:

            if err.errno == errno.ESRCH:
                # no such process
                self.app_instance.exitApplication()

            else:
                sys.stderr.write(str(err))
                sys.exit(1)

    def status(self):
        """Return status."""
        if not self.pidfile:
            logger.warning(
                "Unattended daemon can't be checked. No PID file", self)
            return False

        return not self.app_instance.check()

    def run(self):
        """Override this method when subclass ``Daemon``. It will be called
        after the process has been daemonized by ``start()`` or ``restart()``.
        """
