# Back In Time
# Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import subprocess
import os
import sys
import unittest
from unittest.mock import patch
from threading import Thread
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from applicationinstance import ApplicationInstance
import tools

class TestApplicationInstance(generic.TestCase):
    def setUp(self):
        super(TestApplicationInstance, self).setUp()
        self.temp_file = '/tmp/temp.txt'
        self.file_name = "/tmp/file_with_pid"
        self.inst = ApplicationInstance(os.path.abspath(self.file_name), False)
        self.subproc = None

    def tearDown(self):
        super(TestApplicationInstance, self).tearDown()
        for f in (self.temp_file, self.file_name):
            if os.path.exists(f):
                os.remove(f)
        self.killProcess()

    def createProcess(self):
        dummyPath = os.path.join(os.path.dirname(__file__), generic.DUMMY)
        self.subproc = subprocess.Popen(dummyPath)
        return self.subproc.pid

    def killProcess(self):
        if self.subproc:
            self.subproc.kill()
            self.subproc.wait()
            self.subproc = None

    def test_create_and_remove_pid_file(self):
        #create pid file
        self.inst.startApplication()
        self.assertTrue(os.path.isfile(self.file_name))

        #remove pid file
        self.inst.exitApplication()
        self.assertFalse(os.path.isfile(self.file_name))

    def test_write_pid_file(self):
        self.inst.startApplication()

        #get pid/procname of current process
        this_pid = os.getpid()
        this_procname = tools.processName(this_pid)

        with open(self.file_name, 'rt') as file_with_pid:
            self.assertEqual(file_with_pid.read(), '{}\n{}'.format(this_pid, this_procname))

    @patch('builtins.open')
    def test_write_pid_fail(self, mock_open):
        mock_open.side_effect = OSError()
        self.inst.startApplication()

    def test_existing_process_with_correct_procname(self):
        """
        Test the check function with an existing process with correct process
        name
        """
        pid = self.createProcess()
        procname = tools.processName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        # Execute test
        self.assertFalse(self.inst.check())
        self.assertTrue(self.inst.busy())

    def test_existing_process_with_correct_proc_cmdline(self):
        """
        Test the check function with an existing process with correct process
        cmdline (for backwards compatibility)
        """
        pid = self.createProcess()
        procname = tools.processCmdline(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        # Execute test
        self.assertFalse(self.inst.check())

    def test_no_pid_file(self):
        self.assertTrue(self.inst.check())

    def test_existing_process_with_wrong_procname(self):
        """
        Test the check function with an existing process with wrong process
        name
        """
        pid = self.createProcess()
        procname = tools.processName(pid)

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
        procname = tools.processName(pid)

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
        procname = tools.processName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        self.assertFalse(self.inst.check())

        self.killProcess()

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

    def write_after_flock(self, pid_file):
        inst = ApplicationInstance(os.path.abspath(pid_file),
                                   autoExit = False,
                                   flock = True)
        with open(self.temp_file, 'wt') as f:
            f.write('foo')
        inst.flockUnlock()

    def test_thread_write_without_flock(self):
        thread = Thread(target = self.write_after_flock, args = (self.file_name,))
        thread.start()
        #wait for the thread to finish
        thread.join()
        self.assertTrue(os.path.exists(self.temp_file))
        with open(self.temp_file, 'rt') as f:
            self.assertEqual(f.read(), 'foo')

    def test_flock_exclusive(self):
        self.inst.flockExclusiv()
        thread = Thread(target = self.write_after_flock, args = (self.file_name,))
        thread.start()
        #give the thread some time
        thread.join(0.01)
        self.assertFalse(os.path.exists(self.temp_file))
        self.inst.flockUnlock()
        #wait for the thread to finish
        thread.join()
        self.assertTrue(os.path.exists(self.temp_file))
        with open(self.temp_file, 'rt') as f:
            self.assertEqual(f.read(), 'foo')

    @patch('builtins.open')
    def test_flock_exclusive_fail(self, mock_open):
        mock_open.side_effect = OSError()
        self.inst.flockExclusiv()

    def test_auto_flock(self):
        self.inst = ApplicationInstance(os.path.abspath(self.file_name),
                                        autoExit = False,
                                        flock = True)
        thread = Thread(target = self.write_after_flock, args = (self.file_name,))
        thread.start()
        #give the thread some time
        thread.join(0.01)
        self.assertFalse(os.path.exists(self.temp_file))
        self.inst.startApplication()
        #wait for the thread to finish
        thread.join()
        self.assertTrue(os.path.exists(self.temp_file))
        with open(self.temp_file, 'rt') as f:
            self.assertEqual(f.read(), 'foo')

    def test_autoExit_unique_process(self):
        self.inst = ApplicationInstance(os.path.abspath(self.file_name),
                                        autoExit = True)

        self.assertTrue(os.path.exists(self.file_name))
        this_pid = os.getpid()
        this_procname = tools.processName(this_pid)
        with open(self.file_name, 'rt') as file_with_pid:
            self.assertEqual(file_with_pid.read(), '{}\n{}'.format(this_pid, this_procname))

    def test_autoExit_other_running_process(self):
        pid = self.createProcess()
        procname = tools.processName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        with self.assertRaises(SystemExit):
            self.inst = ApplicationInstance(os.path.abspath(self.file_name),
                                            autoExit = True)

    def test_readPidFile(self):
        with open(self.file_name, "wt") as f:
            f.write('123\nfoo')
        self.assertEqual(self.inst.readPidFile(), (123, 'foo'))

        # ValueError
        with open(self.file_name, "wt") as f:
            f.write('foo\nbar')
        self.assertEqual(self.inst.readPidFile(), (0, 'bar'))

    @patch('builtins.open')
    def test_readPidFile_fail(self, mock_open):
        mock_open.side_effect = OSError()
        self.assertEqual(self.inst.readPidFile(), (0, ''))

# Execute tests if this program is called with python TestApplicationInstance.py
if __name__ == '__main__':
    unittest.main()
