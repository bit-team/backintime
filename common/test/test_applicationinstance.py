# Back In Time
# Copyright (C) 2008-2017 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public Licensealong
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import unittest
import subprocess
import os
import sys
from threading import Thread
from time import sleep
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import logger
from applicationinstance import ApplicationInstance


class TestApplicationInstance(unittest.TestCase):
    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.temp_file = '/tmp/temp.txt'
        self.file_name = "/tmp/file_with_pid"
        self.inst = ApplicationInstance(os.path.abspath(self.file_name), False)
        self.subproc = None

    def tearDown(self):
        for f in (self.temp_file, self.file_name):
            if os.path.exists(f):
                os.remove(f)
        if self.subproc:
            self.subproc.kill()
            self.subproc = None

    def createProcess(self):
        with open(self.temp_file, 'wt') as output:
            self.subproc = subprocess.Popen("top", stdout=output)
            return self.subproc.pid

    def getProcName(self, pid):
        with open('/proc/%s/cmdline' % pid, 'r') as file:
            return file.read().strip('\n')

    def test_create_and_remove_pid_file(self):
        #create pid file
        self.inst.start_application()
        self.assertTrue(os.path.isfile(self.file_name))

        #remove pid file
        self.inst.exit_application()
        self.assertFalse(os.path.isfile(self.file_name))

    def test_write_pid_file(self):
        self.inst.start_application()

        #get pid/procname of current process
        this_pid = os.getpid()
        this_procname = self.getProcName(this_pid)

        with open(self.file_name, 'rt') as file_with_pid:
            self.assertEqual(file_with_pid.read(), '%s\n%s' %(this_pid, this_procname))

    def test_existing_process_with_correct_procname(self):
        """
        Test the check function with an existing process with correct process
        name
        """
        pid = self.createProcess()
        procname = self.getProcName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        # Execute test
        self.assertFalse(self.inst.check())

    def test_existing_process_with_wrong_procname(self):
        """
        Test the check function with an existing process with wrong process
        name
        """
        pid = self.createProcess()
        procname = self.getProcName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname + "DELETE")

        # Execute test
        self.assertTrue(self.inst.check())

    def test_existing_process_with_wrong_pid(self):
        """
        Test the check function with an existing process with wrong pid
        """
        pid = self.createProcess()
        procname = self.getProcName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write("987654321\n")
            file_with_pid.write(procname)

        # Execute test
        self.assertTrue(self.inst.check())

    def test_killing_existing_process(self):
        """
        Test the check function with an existing process with correct process
        name
        """
        pid = self.createProcess()
        procname = self.getProcName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        #kill process
        self.subproc.kill()
        self.subproc.wait()
        self.subproc = None

        # Execute test
        self.assertTrue(self.inst.check())

    def test_non_existing_process(self):
        """ Test the check function with a non existing process """
        #              GIVE               #
        # create file with fake pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write("987654321\n")
            file_with_pid.write("FAKE_PROCNAME")

        # Execute test
        self.assertTrue(self.inst.check())

    def test_leftover_empty_lockfile(self):
        with open(self.file_name, 'wt')as f:
            pass
        self.assertTrue(self.inst.check())

    def write_after_flock(self, pid_file,):
        inst = ApplicationInstance(os.path.abspath(pid_file), False)
        inst.flockExclusiv()
        with open(self.temp_file, 'wt') as f:
            f.write('foo')
        inst.flockUnlock()

    def test_thread_write_without_flock(self):
        thread = Thread(target = self.write_after_flock, args = (self.file_name, ))
        thread.start()
        #wait for the thread to finish
        thread.join()
        self.assertTrue(os.path.exists(self.temp_file))
        with open(self.temp_file, 'rt') as f:
            self.assertEqual(f.read(), 'foo')

    def test_flock_exclusive(self):
        self.inst.flockExclusiv()
        thread = Thread(target = self.write_after_flock, args = (self.file_name, ))
        thread.start()
        #give the thread some time
        sleep(0.01)
        self.assertFalse(os.path.exists(self.temp_file))
        self.inst.flockUnlock()
        #wait for the thread to finish
        thread.join()
        self.assertTrue(os.path.exists(self.temp_file))
        with open(self.temp_file, 'rt') as f:
            self.assertEqual(f.read(), 'foo')

# Execute tests if this programm is call with python TestApplicationInstance.py
if __name__ == '__main__':
    unittest.main()
