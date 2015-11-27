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
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common/'))
import tools
import config
import configfile

class TestTools(unittest.TestCase):
    ''' All funtions test here come from tools.py '''

    def test_read_file(self):
        ''' Test the function read_file '''
        test_tools_file = os.path.abspath(__file__)
        test_directory = os.path.dirname(test_tools_file)
        non_existing_file = os.path.join(test_directory, "nonExistingFile")
        self.assertNotEquals(tools.read_file(test_tools_file), None)
        self.assertEquals(tools.read_file(non_existing_file), None)

    def test_read_file_lines(self):
        ''' Test the function read_file_lines '''
        test_tools_file = os.path.abspath(__file__)
        test_directory = os.path.dirname(test_tools_file)
        non_existing_file = os.path.join(test_directory, "nonExistingFile")
        self.assertNotEquals(tools.read_file_lines(test_tools_file), None)
        self.assertEquals(tools.read_file_lines(non_existing_file), None)

    def test_read_command_output(self):
        ''' Test the function read_command_output '''
        ret_val = tools.read_command_output("echo 'Test, read command output'")
        self.assertEquals("Test, read command output", ret_val)

    def test_check_command(self):
        ''' Test the function check_command '''
        self.assertFalse(tools.check_command("notExistedCommand"))
        self.assertTrue(tools.check_command("ls"))

    def test_which(self):
        ''' Test the function which '''
        assert tools.which("ls") is not None
        assert tools.which("notExistedCommand") is None

    def test_process_exists(self):
        ''' Test the function process_exists '''
        self.assertTrue(tools.process_exists("init"))
        self.assertFalse(tools.process_exists("notExistedProcess"))

    def test_load_env(self):
        ''' Test the function load_env '''
        d = {}
        lines = []
        path_user = os.path.expanduser('~')
        path_cron_env = os.path.join(
            path_user,
            ".local/share/backintime/cron_env")
        try:
            with open(path_cron_env, 'rt') as file:
                lines = file.readlines()
        except:
            pass
        for line in lines:
            items = line.split('=', 1)
            if len(items) == 2:
                d[items[0]] = items[1][:-1]
        cfg = config.Config(None)
        tools.load_env(cfg)
        for key in d.keys():
            self.assertEquals(os.environ[key], d[key])

    def test_prepare_path(self):
        ''' Test the function load_env '''
        path_with_slash_at_begin = "/test/path"
        path_without_slash_at_begin = "test/path"
        path_with_slash_at_end = "/test/path/"
        path_without_slash_at_end = "/test/path"
        self.assertEquals(
            tools.prepare_path(path_with_slash_at_begin),
            path_with_slash_at_begin)
        self.assertEquals(
            tools.prepare_path(path_without_slash_at_begin),
            path_with_slash_at_begin)
        self.assertEquals(
            tools.prepare_path(path_without_slash_at_end),
            path_without_slash_at_end)
        self.assertEquals(
            tools.prepare_path(path_with_slash_at_end),
            path_without_slash_at_end)

    def test_is_process_alive(self):
        ''' Test the function is_process_alive '''
        self.assertTrue(tools.is_process_alive(0))
        self.assertFalse(tools.is_process_alive(99999999999))
