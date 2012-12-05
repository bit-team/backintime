#    Copyright (c) 2012 Germar Reitze
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

class Timeout(Exception):
    pass

class FIFO(object):
    def __init__(self, fname):
        self.fifo = fname
        self.alarm = Alarm()
        
    def delfifo(self):
        try:
            os.remove(self.fifo)
        except:
            pass
        
    def create(self):
        if os.path.exists(self.fifo):
            self.delfifo()
        try:
            os.mkfifo(self.fifo, 0600)
        except OSError, e:
            sys.stderr.write('Failed to create FIFO: %s\n' % e.strerror)
            sys.exit(1)
        
    def read(self, timeout = 0):
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
        #sys.stdout.write('write fifo\n')
        if not self.is_fifo():
            sys.stderr.write('%s is not a FIFO\n' % self.fifo)
            sys.exit(1)
        self.alarm.start(timeout)
        with open(self.fifo, 'a') as fifo:
            fifo.write(string)
        self.alarm.stop()
        
    def is_fifo(self):
        try:
            return stat.S_ISFIFO(os.stat(self.fifo).st_mode)
        except OSError:
            return False

class Alarm(object):
    def __init__(self):
        pass
        
    def start(self, timeout):
        try:
            signal.signal(signal.SIGALRM, self.handler)
            signal.alarm(timeout)
        except ValueError:
            pass
        
    def stop(self):
        try:
            signal.alarm(0)
        except:
            pass
        
    def handler(self, signum, frame):
        raise Timeout()
