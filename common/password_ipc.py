#    Copyright (c) 2012-2013 Germar Reitze
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
import sys
import stat
import signal
import tools
import threading
import base64
import tempfile

class FIFO(object):
    """
    interprocess-communication with named pipes
    """
    def __init__(self, fname):
        self.fifo = fname
        self.alarm = tools.Alarm()
        
    def delfifo(self):
        """
        remove FIFO
        """
        try:
            os.remove(self.fifo)
        except:
            pass
        
    def create(self):
        """
        create the FIFO in a way that only the current user can access it.
        """
        if os.path.exists(self.fifo):
            self.delfifo()
        try:
            os.mkfifo(self.fifo, 0600)
        except OSError, e:
            sys.stderr.write('Failed to create FIFO: %s\n' % e.strerror)
            sys.exit(1)
        
    def read(self, timeout = 0):
        """
        read from fifo untill timeout. If timeout is 0 it will wait forever
        for input.
        """
        #sys.stdout.write('read fifo\n')
        if not self.is_fifo():
            sys.stderr.write('%s is not a FIFO\n' % self.fifo)
            sys.exit(1)
        self.alarm.start(timeout)
        with open(self.fifo, 'r') as fifo:
            ret = fifo.read()
        self.alarm.stop()
        return ret
        
    def write(self, string, timeout = 0):
        """
        write to fifo untill timeout. If timeout is 0 it will wait forever
        for an other process that will read this.
        """
        #sys.stdout.write('write fifo\n')
        if not self.is_fifo():
            sys.stderr.write('%s is not a FIFO\n' % self.fifo)
            sys.exit(1)
        self.alarm.start(timeout)
        with open(self.fifo, 'a') as fifo:
            fifo.write(string)
        self.alarm.stop()
        
    def is_fifo(self):
        """
        make sure file is still a FIFO
        """
        try:
            return stat.S_ISFIFO(os.stat(self.fifo).st_mode)
        except OSError:
            return False

class TempPasswordThread(threading.Thread):
    """
    in case BIT is not configured yet provide password through temp FIFO
    to backintime-askpass.
    """
    def __init__(self, string):
        threading.Thread.__init__(self)
        self.pw_base64 = base64.encodestring(string)
        self.temp_file = os.path.join(tempfile.mkdtemp(), 'FIFO')
        self.fifo = FIFO(self.temp_file)
        
    def run(self):
        self.fifo.create()
        self.fifo.write(self.pw_base64)
        self.fifo.delfifo()

    def read(self):
        """
        read fifo to end the blocking fifo.write
        use only if thread timeout.
        """
        self.fifo.read()
    
    def stop(self):
        self.join(5)
        if self.isAlive():
            #threading does not support signal.alarm
            self.read()
        try:
            os.rmdir(os.path.dirname(self.temp_file))
        except OSError:
            pass