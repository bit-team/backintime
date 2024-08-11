# Back In Time
# Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
from unittest.mock import patch
from threading import Thread
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from applicationinstance import ApplicationInstance
import tools


class TestApplicationInstance(generic.TestCase):
    """
    """

    def setUp(self):
        """Preparing unittests including the instantiation of an
        ``ÀpplicationInstance``.
        """
        super(TestApplicationInstance, self).setUp()

        self.temp_file = '/tmp/temp.txt'
        self.file_name = "/tmp/file_with_pid"

        self.app_instance = ApplicationInstance(
            pidFile=os.path.abspath(self.file_name),
            autoExit=False)

        self.subproc = None

    def tearDown(self):
        """Delete temporary files and kill subprocesses.
        """
        super(TestApplicationInstance, self).tearDown()

        for f in (self.temp_file, self.file_name):
            if os.path.exists(f):
                os.remove(f)

        self._killProcess()

    def _createProcess(self):
        """Start a shell script and return ins PID."""

        # path to the shell script
        dummyPath = os.path.join(os.path.dirname(__file__), generic.DUMMY)

        self.subproc = subprocess.Popen(dummyPath)

        return self.subproc.pid

    def _killProcess(self):
        if self.subproc:
            self.subproc.kill()
            self.subproc.wait()
            self.subproc = None

    def test_create_and_remove_pid_file(self):
        # create pid file
        self.app_instance.startApplication()
        self.assertIsFile(self.file_name)

        # remove pid file
        self.app_instance.exitApplication()
        self.assertIsNoFile(self.file_name)

    def test_pid_file_content(self):
        """Content of pid file fits to current process."""
        self.app_instance.startApplication()

        this_pid = os.getpid()
        this_procname = tools.processName(this_pid)
        expected_file_content = f'{this_pid}\n{this_procname}'

        with open(self.file_name, 'rt') as file_with_pid:
            pid_file_content = file_with_pid.read()

        self.assertEqual(pid_file_content, expected_file_content)

    @patch('builtins.open')
    def test_write_pid_fail(self, mock_open):
        """The test is not clear. Because of the OSError() a log error will be
        generated. But this isn't tested here.

        I assume the expected behavior is just that nothing bad happens
        because the OSError was caught.
        """
        mock_open.side_effect = OSError()
        self.app_instance.startApplication()

    def test_existing_process_with_correct_procname(self):
        """
        Test the check function with an existing process with correct process
        name
        """
        pid = self._createProcess()
        procname = tools.processName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        # Execute test
        self.assertFalse(self.app_instance.check())
        self.assertTrue(self.app_instance.busy())

    def test_existing_process_with_correct_proc_cmdline(self):
        """
        Test the check function with an existing process with correct process
        cmdline (for backwards compatibility)
        """

        # start an extern shell script
        pid = self._createProcess()

        procname = tools.processCmdline(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        # Execute test
        self.assertFalse(self.app_instance.check())

    def test_no_pid_file(self):
        self.assertTrue(self.app_instance.check())

    def test_existing_process_with_wrong_procname(self):
        """
        Test the check function with an existing process with wrong process
        name
        """
        pid = self._createProcess()
        procname = tools.processName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname + "DELETE")

        # Execute test
        self.assertTrue(self.app_instance.check())

    def test_existing_process_with_wrong_pid(self):
        """
        Test the check function with an existing process with wrong pid
        """
        pid = self._createProcess()
        procname = tools.processName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write("987654321\n")
            file_with_pid.write(procname)

        # Execute test
        self.assertTrue(self.app_instance.check())

    def test_killing_existing_process(self):
        """
        Test the check function with an existing process with correct process
        name
        """
        pid = self._createProcess()
        procname = tools.processName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        self.assertFalse(self.app_instance.check())

        self._killProcess()

        # Execute test
        self.assertTrue(self.app_instance.check())

    def test_non_existing_process(self):
        """ Test the check function with a non existing process """
        #              GIVE               #
        # create file with fake pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write("987654321\n")
            file_with_pid.write("FAKE_PROCNAME")

        # Execute test
        self.assertTrue(self.app_instance.check())

    def test_leftover_empty_lockfile(self):
        with open(self.file_name, 'wt') as f:
            pass
        self.assertTrue(self.app_instance.check())

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
        self.assertExists(self.temp_file)
        with open(self.temp_file, 'rt') as f:
            self.assertEqual(f.read(), 'foo')

    def test_flock_exclusive(self):
        self.app_instance.flockExclusiv()
        thread = Thread(target = self.write_after_flock, args = (self.file_name,))
        thread.start()
        #give the thread some time
        thread.join(0.01)
        self.assertNotExists(self.temp_file)
        self.app_instance.flockUnlock()
        #wait for the thread to finish
        thread.join()
        self.assertExists(self.temp_file)
        with open(self.temp_file, 'rt') as f:
            self.assertEqual(f.read(), 'foo')

    @patch('builtins.open')
    def test_flock_exclusive_fail(self, mock_open):
        """Dev note (buhtz: 2023-09)
        Nothing is tested here.
        Looking into flockExclusive() there is only the opportunity to
        test for ERROR log output. Log output shouldn't be tested.

        The behavior to test is unclear.

        Proposal:
          - Remove the test.
          - Refactor flockExclusive() and related code to make its behavior
            clear.
        """
        mock_open.side_effect = OSError()
        self.app_instance.flockExclusiv()

    def test_auto_flock(self):
        self.app_instance = ApplicationInstance(os.path.abspath(self.file_name),
                                        autoExit = False,
                                        flock = True)
        thread = Thread(target = self.write_after_flock, args = (self.file_name,))
        thread.start()
        #give the thread some time
        thread.join(0.01)
        self.assertNotExists(self.temp_file)
        self.app_instance.startApplication()
        #wait for the thread to finish
        thread.join()
        self.assertExists(self.temp_file)
        with open(self.temp_file, 'rt') as f:
            self.assertEqual(f.read(), 'foo')

    def test_autoExit_unique_process(self):
        self.app_instance = ApplicationInstance(os.path.abspath(self.file_name),
                                        autoExit = True)

        self.assertExists(self.file_name)
        this_pid = os.getpid()
        this_procname = tools.processName(this_pid)
        with open(self.file_name, 'rt') as file_with_pid:
            self.assertEqual(file_with_pid.read(), '{}\n{}'.format(this_pid, this_procname))

    def test_autoExit_other_running_process(self):
        pid = self._createProcess()
        procname = tools.processName(pid)

        # create file with pid and process name
        with open(self.file_name, "wt") as file_with_pid:
            file_with_pid.write(str(pid) + "\n")
            file_with_pid.write(procname)

        with self.assertRaises(SystemExit):
            self.app_instance = ApplicationInstance(os.path.abspath(self.file_name),
                                            autoExit = True)

    def test_readPidFile(self):
        with open(self.file_name, "wt") as f:
            f.write('123\nfoo')
        self.assertEqual(self.app_instance.readPidFile(), (123, 'foo'))

        # ValueError
        with open(self.file_name, "wt") as f:
            f.write('foo\nbar')
        self.assertEqual(self.app_instance.readPidFile(), (0, 'bar'))

    @patch('builtins.open')
    def test_readPidFile_fail(self, mock_open):
        mock_open.side_effect = OSError()
        self.assertEqual(self.app_instance.readPidFile(), (0, ''))
