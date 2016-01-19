# Back In Time
# Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze, Taylor Raack
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
import os
import sys
import subprocess
from copy import deepcopy
from tempfile import NamedTemporaryFile
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import tools
import config
import configfile
import logger

ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'
ON_RTD = os.environ.get('READTHEDOCS', 'None').lower() == 'true'

#chroot jails used for building may have no UUID devices (because of tmpfs)
#we need to skip tests that require UUIDs
DISK_BY_UUID_AVAILABLE = os.path.exists(tools.DISK_BY_UUID)
UDEVADM_HAS_UUID = subprocess.Popen(['udevadm', 'info', '-e'],
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.DEVNULL
                                   ).communicate()[0].find(b'ID_FS_UUID=') > 0

class TestTools(unittest.TestCase):
    """
    All funtions test here come from tools.py
    """
    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.subproc = None

    def tearDown(self):
        self.killProcess()

    def createProcess(self, *args):
        dummy = 'dummy_proc.sh'
        dummyPath = os.path.join(os.path.dirname(__file__), dummy)
        cmd = [dummyPath]
        cmd.extend(args)
        self.subproc = subprocess.Popen(cmd)
        return self.subproc.pid

    def killProcess(self):
        if self.subproc:
            self.subproc.kill()
            self.subproc.wait()
            self.subproc = None

    def test_read_file(self):
        """
        Test the function read_file
        """
        test_tools_file = os.path.abspath(__file__)
        test_directory = os.path.dirname(test_tools_file)
        non_existing_file = os.path.join(test_directory, "nonExistingFile")
        self.assertIsNotNone(tools.read_file(test_tools_file))
        self.assertIsNone(tools.read_file(non_existing_file))

    def test_read_file_lines(self):
        """
        Test the function read_file_lines
        """
        test_tools_file = os.path.abspath(__file__)
        test_directory = os.path.dirname(test_tools_file)
        non_existing_file = os.path.join(test_directory, "nonExistingFile")
        self.assertIsNotNone(tools.read_file_lines(test_tools_file))
        self.assertIsNone(tools.read_file_lines(non_existing_file))

    def test_read_command_output(self):
        """
        Test the function read_command_output
        """
        ret_val = tools.read_command_output("echo 'Test, read command output'")
        self.assertEqual("Test, read command output", ret_val)

    def test_check_command(self):
        """
        Test the function check_command
        """
        self.assertFalse(tools.check_command("notExistedCommand"))
        self.assertTrue(tools.check_command("ls"))

    def test_which(self):
        """
        Test the function which
        """
        self.assertRegex(tools.which("ls"), r'/.*/ls')
        self.assertIsNone(tools.which("notExistedCommand"))

    def test_prepare_path(self):
        """
        Test the function load_env
        """
        path_with_slash_at_begin = "/test/path"
        path_without_slash_at_begin = "test/path"
        path_with_slash_at_end = "/test/path/"
        path_without_slash_at_end = "/test/path"
        self.assertEqual(
            tools.prepare_path(path_with_slash_at_begin),
            path_with_slash_at_begin)
        self.assertEqual(
            tools.prepare_path(path_without_slash_at_begin),
            path_with_slash_at_begin)
        self.assertEqual(
            tools.prepare_path(path_without_slash_at_end),
            path_without_slash_at_end)
        self.assertEqual(
            tools.prepare_path(path_with_slash_at_end),
            path_without_slash_at_end)

    def test_pids(self):
        pids = tools.pids()
        self.assertGreater(len(pids), 0)
        self.assertIn(os.getpid(), pids)

    def test_process_name(self):
        pid = self.createProcess()
        self.assertEqual(tools.process_name(pid), 'dummy_proc.sh')

    def test_process_cmdline(self):
        pid = self.createProcess()
        self.assertRegex(tools.process_cmdline(pid),
                         r'.*/sh.*/common/test/dummy_proc\.sh')
        self.killProcess()
        pid = self.createProcess('foo', 'bar')
        self.assertRegex(tools.process_cmdline(pid),
                         r'.*/sh.*/common/test/dummy_proc\.sh.foo.bar')

    def test_pids_with_name(self):
        self.assertEqual(len(tools.pids_with_name('nonExistingProcess')), 0)
        pid = self.createProcess()
        pids = tools.pids_with_name('dummy_proc.sh')
        self.assertGreaterEqual(len(pids), 1)
        self.assertIn(pid, pids)

    def test_process_exists(self):
        self.assertFalse(tools.process_exists('nonExistingProcess'))
        pid = self.createProcess()
        self.assertTrue(tools.process_exists('dummy_proc.sh'))

    def test_is_process_alive(self):
        """
        Test the function is_process_alive
        """
        #TODO: add test (in chroot) running proc as root and kill as non-root
        self.assertTrue(tools.is_process_alive(os.getpid()))
        pid = self.createProcess()
        self.assertTrue(tools.is_process_alive(pid))
        self.killProcess()
        self.assertFalse(tools.is_process_alive(pid))
        self.assertFalse(tools.is_process_alive(999999))
        with self.assertRaises(ValueError):
            tools.is_process_alive(0)
        self.assertFalse(tools.is_process_alive(-1))

    def test_power_status_available(self):
        if tools.process_exists('upowerd') and not ON_TRAVIS:
            self.assertTrue(tools.power_status_available())
        else:
            self.assertFalse(tools.power_status_available())
        self.assertIsInstance(tools.on_battery(), bool)

    @unittest.skipIf(not DISK_BY_UUID_AVAILABLE and not UDEVADM_HAS_UUID,
                     'No UUIDs available on this system.')
    def test_get_filesystem_mount_info(self):
        """
        Basic sanity checks on returned structure
        """
        mounts = tools.get_filesystem_mount_info()
        self.assertIsInstance(mounts, dict)
        self.assertGreater(len(mounts.items()), 0)
        self.assertIn('/', mounts)
        self.assertIn('original_uuid', mounts.get('/'))

class TestToolsEnviron(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestToolsEnviron, self).__init__(*args, **kwargs)
        self.env = deepcopy(os.environ)

    def setUp(self):
        logger.DEBUG = '-v' in sys.argv
        self.temp_file = '/tmp/temp.txt'
        os.environ = deepcopy(self.env)

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        os.environ = deepcopy(self.env)

    def test_load_env_without_previous_values(self):
        test_env = configfile.ConfigFile()
        test_env.set_str_value('FOO', 'bar')
        test_env.set_str_value('ASDF', 'qwertz')
        test_env.save(self.temp_file)

        #make sure environ is clean
        self.assertNotIn('FOO', os.environ)
        self.assertNotIn('ASDF', os.environ)

        tools.load_env(self.temp_file)
        self.assertIn('FOO', os.environ)
        self.assertIn('ASDF', os.environ)
        self.assertEqual(os.environ['FOO'], 'bar')
        self.assertEqual(os.environ['ASDF'], 'qwertz')

    def test_load_env_do_not_overwrite_previous_values(self):
        test_env = configfile.ConfigFile()
        test_env.set_str_value('FOO', 'bar')
        test_env.set_str_value('ASDF', 'qwertz')
        test_env.save(self.temp_file)

        #add some environ vars that should not get overwritten
        os.environ['FOO'] = 'defaultFOO'
        os.environ['ASDF'] = 'defaultASDF'

        tools.load_env(self.temp_file)
        self.assertIn('FOO', os.environ)
        self.assertIn('ASDF', os.environ)
        self.assertEqual(os.environ['FOO'], 'defaultFOO')
        self.assertEqual(os.environ['ASDF'], 'defaultASDF')

    def test_save_env(self):
        keys = ('GNOME_KEYRING_CONTROL', 'DBUS_SESSION_BUS_ADDRESS', \
                'DBUS_SESSION_BUS_PID', 'DBUS_SESSION_BUS_WINDOWID', \
                'DISPLAY', 'XAUTHORITY', 'GNOME_DESKTOP_SESSION_ID', \
                'KDE_FULL_SESSION')
        for i, k in enumerate(keys):
            os.environ[k] = str(i)

        tools.save_env(self.temp_file)

        self.assertTrue(os.path.isfile(self.temp_file))

        test_env = configfile.ConfigFile()
        test_env.load(self.temp_file)
        for i, k in enumerate(keys):
            with self.subTest(i = i, k = k):
                #workaround for py.test3 2.5.1 doesn't support subTest
                msg = 'i = %s, k = %s' %(i, k)
                self.assertEqual(test_env.get_str_value(k), str(i), msg)

if __name__ == '__main__':
    unittest.main()
