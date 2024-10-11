# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
import stat
import tools
import threading
import tempfile
from contextlib import contextmanager

import logger

class FIFO:
    """Inter-process communication (IPC) with named pipes using the first-in,
    first-out principle (FIFO).

    Params:
        fifo (str): Name of the named pipe file.
        alarm (tools.Alarm): To handle read/write timeouts.
    """

    def __init__(self, fname):
        self.fifo = fname
        self.alarm = tools.Alarm()

    def delfifo(self):
        """Remove named pipe file."""
        try:
            os.remove(self.fifo)
        # TODO: Catch FileNotFoundError only
        except:
            pass

    def create(self):
        """Create the named pipe file in a way that only the current user has
        access to it.
        """
        if os.path.exists(self.fifo):
            self.delfifo()

        try:
            # Permissions are "rw- --- ---"
            os.mkfifo(self.fifo, 0o600)

        except OSError as e:
            logger.error(f'Failed to create named pipe file. Error: {e}', self)
            sys.exit(1)

    def read(self, timeout=0):
        """Read from named pipe until timeout. If timeout is 0 it will wait
        forever for input.
        """
        # sys.stdout.write('read fifo\n')
        if not self.isFifo():
            # TODO raise an Exception or write to stderr
            sys.exit(1)

        self.alarm.start(timeout)

        with open(self.fifo, 'r') as handle:
            # Will wait until data is available,
            # or an exception (e.g. exception.Timeout) is raised.
            # The latter will happen when the timeout is finished.
            ret = handle.read()

        # If the alarm timeout ends but read() received not data, a
        # exception.Timeout will be raised at this point.
        # The exception will be caught far away in
        # password.py::Password_Cache.run().

        self.alarm.stop()

        return ret

    def write(self, string, timeout=0):
        """Write to named pipe file until timeout. If timeout is 0 it will wait
        forever for an other process that will read this.
        """
        if not self.isFifo():
            # TODO raise an Exception or write to stderr
            sys.exit(1)

        self.alarm.start(timeout)

        with open(self.fifo, 'w') as fifo:
            fifo.write(string)

        # See FIFO.read() to learn about "hidden" handling of Timeout
        # exception.

        self.alarm.stop()

    def isFifo(self):
        """Make sure file is still a FIFO and has correct permissions."""
        try:
            s = os.stat(self.fifo)

        except OSError:
            return False

        if not s.st_uid == os.getuid():
            logger.error(f'{self.fifo} is not owned by user', self)
            return False

        mode = s.st_mode
        if not stat.S_ISFIFO(mode):
            logger.error(f'{self.fifo} is not a named pipe file (FIFO)', self)
            return False

        forbidden_perm = stat.S_IXUSR + stat.S_IRWXG + stat.S_IRWXO
        if mode & forbidden_perm > 0:
            logger.error(f'{self.fifo} has wrong permissions', self)
            return False

        return True


class TempPasswordThread(threading.Thread):
    """
    in case BIT is not configured yet provide password through temp FIFO
    to backintime-askpass.
    """

    def __init__(self, string):
        super(TempPasswordThread, self).__init__()
        self.pw = string
        self.temp_file = os.path.join(tempfile.mkdtemp(), 'FIFO')
        self.fifo = FIFO(self.temp_file)

    @contextmanager
    def starter(self):
        self.start()
        yield
        self.stop()

    def run(self):
        self.fifo.create()
        self.fifo.write(self.pw)
        self.fifo.delfifo()

    def read(self):
        """
        read fifo to end the blocking fifo.write
        use only if thread timeout.
        """
        self.fifo.read()

    def stop(self):
        self.join(5)
        if self.is_alive():
            #threading does not support signal.alarm
            self.read()
        try:
            os.rmdir(os.path.dirname(self.temp_file))
        except OSError:
            pass
