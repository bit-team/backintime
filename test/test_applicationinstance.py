# Back In Time
# Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "common/"))

from applicationinstance import ApplicationInstance


class TestApplicationInstance(unittest.TestCase):
    def setUp(self):
        self.temp_file = 'temp.txt'
        self.file_name = "file_with_pid"
        self.inst = ApplicationInstance(os.path.abspath(self.file_name), False)

    def tearDown(self):
        for f in (self.temp_file, self.file_name):
            if os.path.exists(f):
                os.remove(f)

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
        with open('/proc/%s/cmdline' % this_pid, 'r') as file:
            this_procname = file.read().strip('\n')

        with open(self.file_name, 'rt') as file_with_pid:
            self.assertEqual(file_with_pid.read(), '%s\n%s' %(this_pid, this_procname))

    def test_existing_process_with_correct_procname(self):
        """
        Test the check function with an existing process with correct process
        name
        """
        #              GIVE               #
        # Creation of thread to get a pid
        with open(self.temp_file, 'wt') as output:
            subproc = subprocess.Popen("top", stdout=output)
            pid = subproc.pid
        # Get the process name
        with open('/proc/%s/cmdline' % pid, 'r') as file:
            procname = file.read().strip('\n')

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        #               WHEN             #
        result = self.inst.check()

        #               THEN             #
        # Clean files and process
        subproc.kill()
        # Execute test
        self.assertFalse(result)

    def test_existing_process_with_wrong_procname(self):
        """
        Test the check function with an existing process with wrong process
        name
        """
        #              GIVE               #
        # Creation of thread to get a pid
        with open(self.temp_file, 'wt') as output:
            subproc = subprocess.Popen("top", stdout=output)
            pid = subproc.pid
        # Get the process name
        with open('/proc/%s/cmdline' % pid, 'r') as file:
            procname = file.read().strip('\n')

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname + "DELETE")

        #               WHEN             #
        result = self.inst.check()

        #               THEN             #
        # Clean files and process
        subproc.kill()

        # Execute test
        self.assertTrue(result)

    def test_existing_process_with_wrong_pid(self):
        """
        Test the check function with an existing process with wrong pid
        """
        #              GIVE               #
        # Creation of thread to get a pid
        with open(self.temp_file, 'wt') as output:
            subproc = subprocess.Popen("top", stdout=output)
            pid = subproc.pid
        # Get the process name
        with open('/proc/%s/cmdline' % pid, 'r') as file:
            procname = file.read().strip('\n')

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write("987654321\n")
            file_with_pid.write(procname)

        #               WHEN             #
        result = self.inst.check()

        #               THEN             #
        # Clean files and process
        subproc.kill()

        # Execute test
        self.assertTrue(result)

    def test_killing_existing_process(self):
        """
        Test the check function with an existing process with correct process
        name
        """
        #              GIVE               #
        # Creation of thread to get a pid
        with open(self.temp_file, 'wt') as output:
            subproc = subprocess.Popen("top", stdout=output)
            pid = subproc.pid
        # Get the process name
        with open('/proc/%s/cmdline' % pid, 'r') as file:
            procname = file.read().strip('\n')

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        #kill process
        subproc.kill()

        #               WHEN             #
        result = self.inst.check()

        #               THEN             #
        # Clean files
        # Execute test
        self.assertTrue(result)

    def test_non_existing_process(self):
        """ Test the check function with a non existing process """
        #              GIVE               #
        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write("987654321\n")
            file_with_pid.write("FAKE_PROCNAME")

        #               WHEN             #
        result = self.inst.check()

        # Execute test
        self.assertTrue(result)

#TODO: add flock tests

# Execute tests if this programm is call with python TestApplicationInstance.py
if __name__ == '__main__':
    unittest.main()
