#
#  Python using test for the file applicationInstance.py
#  @Authors Gregory LEFER, Aurelien HAVET, Dorian BURIHABWA, Alexandre FRANCOIS
#           => Universite Lille1, France
#  @Date    2014.10.15
#

import unittest
import subprocess
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "common/"))

from applicationinstance import ApplicationInstance


class TestApplicationInstance(unittest.TestCase):
    def setUp(self):
        self.t = 1

    def test_existing_process_with_correct_procname(self):
        """
        Test the check function with an existing process with correct process
        name
        """
        #              GIVE               #
        # Creation of thread to get a pid
        with open('temp.txt', 'wt') as output:
            subproc = subprocess.Popen("top", stdout=output)
            pid = subproc.pid
        # Get the process name
        with open('/proc/%s/cmdline' % pid, 'r') as file:
            procname = file.read().strip('\n')
            file.close()

        # create file with pid and process name
        file_name = "file_with_pid"
        file_with_pid = open(file_name, "wt")
        file_with_pid.write(str(pid) + "\n")
        file_with_pid.write(procname)
        file_with_pid.close()

        #               WHEN             #
        self.inst = ApplicationInstance(os.path.abspath(file_name), False)
        result = self.inst.check()

        #               THEN             #
        # Clean files and process
        subproc.kill()
        os.remove("temp.txt")
        os.remove("file_with_pid")
        # Execute test
        self.assertFalse(result)

    def test_killing_existing_process(self):
        """
        Test the check function when it kills a instance of existing process
        """
        #              GIVE               #
        # Creation of thread to get a pid
        with open('temp.txt', 'wt') as output:
            subproc = subprocess.Popen("top", stdout=output)
            pid = subproc.pid
        # Get the process name
        with open('/proc/%s/cmdline' % pid, 'r') as file:
            procname = file.read().strip('\n')
            file.close()

        # create file with pid and process name
        file_name = "file_with_pid"
        file_with_pid = open(file_name, "wt")
        file_with_pid.write(str(pid) + "\n")
        # Necessary, because os.kill can't kill Popen Process
        file_with_pid.write(procname + "DELETE")
        file_with_pid.close()

        #               WHEN             #
        self.inst = ApplicationInstance(os.path.abspath(file_name), False)
        result = self.inst.check()

        #               THEN             #
        # Clean files and process
        subproc.kill()
        os.remove("temp.txt")
        os.remove("file_with_pid")

        # Execute test
        self.assertTrue(result)

    def test_non_existing_process(self):
        """ Test the check function with a non existing process """
        #              GIVE               #
        # create file with pid and process name
        file_name = "file_with_pid"
        file_with_pid = open(file_name, "wt")
        file_with_pid.write("987654321\n")
        file_with_pid.write("FAKE_PROCNAME")
        file_with_pid.close()

        #               WHEN             #
        self.inst = ApplicationInstance(os.path.abspath(file_name), False)
        result = self.inst.check()

        #               THEN             #
        # Clean files and process
        os.remove("file_with_pid")

        # Execute test
        self.assertTrue(result)


# Execute tests if this programm is call with python TestApplicationInstance.py
if __name__ == '__main__':
    unittest.main()
