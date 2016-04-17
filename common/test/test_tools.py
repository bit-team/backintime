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
import random
import gzip
import stat
from copy import deepcopy
from tempfile import NamedTemporaryFile, TemporaryDirectory
from datetime import datetime
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import tools
import config
import configfile

#chroot jails used for building may have no UUID devices (because of tmpfs)
#we need to skip tests that require UUIDs
DISK_BY_UUID_AVAILABLE = os.path.exists(tools.DISK_BY_UUID)
UDEVADM_HAS_UUID = subprocess.Popen(['udevadm', 'info', '-e'],
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.DEVNULL
                                   ).communicate()[0].find(b'ID_FS_UUID=') > 0

RSYNC_INSTALLED = tools.check_command('rsync')

RSYNC_307_VERSION = """rsync  version 3.0.7  protocol version 30
Copyright (C) 1996-2009 by Andrew Tridgell, Wayne Davison, and others.
Web site: http://rsync.samba.org/
Capabilities:
    64-bit files, 64-bit inums, 32-bit timestamps, 64-bit long ints,
    socketpairs, hardlinks, symlinks, IPv6, batchfiles, inplace,
    append, ACLs, xattrs, iconv, symtimes

rsync comes with ABSOLUTELY NO WARRANTY.  This is free software, and you
are welcome to redistribute it under certain conditions.  See the GNU
General Public Licence for details.
"""
RSYNC_310_VERSION = """rsync  version 3.1.0  protocol version 31
Copyright (C) 1996-2013 by Andrew Tridgell, Wayne Davison, and others.
Web site: http://rsync.samba.org/
Capabilities:
    64-bit files, 64-bit inums, 64-bit timestamps, 64-bit long ints,
    socketpairs, hardlinks, symlinks, IPv6, batchfiles, inplace,
    append, ACLs, xattrs, iconv, symtimes, prealloc

rsync comes with ABSOLUTELY NO WARRANTY.  This is free software, and you
are welcome to redistribute it under certain conditions.  See the GNU
General Public Licence for details.
"""

class TestTools(generic.TestCase):
    """
    All funtions test here come from tools.py
    """
    def setUp(self):
        super(TestTools, self).setUp()
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

    def test_get_share_path(self):
        share = tools.get_share_path()
        self.assertTrue(share.endswith('share'), 'share = {}'.format(share))

    def test_get_backintime_path(self):
        path = tools.get_backintime_path('common')
        self.assertRegex(path, r'.*/backintime.*/common$')

    def test_register_backintime_path(self):
        path = tools.get_backintime_path('foo')
        tools.register_backintime_path('foo')
        self.assertIn(path, sys.path)
        sys.path.remove(path)

    def test_running_from_source(self):
        self.assertTrue(tools.running_from_source())

    def test_add_source_to_path_environ(self):
        source = tools.get_backintime_path('common')
        path = [x for x in os.getenv('PATH').split(':') if x != source]
        os.environ['PATH'] = ':'.join(path)

        tools.add_source_to_path_environ()
        self.assertIn(source, os.environ['PATH'])

    def test_get_git_ref_hash(self):
        ref, hashid = tools.get_git_ref_hash()
        if isinstance(ref, str):
            self.assertGreater(len(ref), 0)
        else:
            self.assertIsNone(ref)

        if isinstance(hashid, str):
            self.assertEqual(len(hashid), 7)
        else:
            self.assertIsNone(hashid)

    def test_read_file(self):
        """
        Test the function read_file
        """
        test_tools_file = os.path.abspath(__file__)
        test_directory = os.path.dirname(test_tools_file)
        non_existing_file = os.path.join(test_directory, "nonExistingFile")

        self.assertIsInstance(tools.read_file(test_tools_file), str)
        self.assertIsNone(tools.read_file(non_existing_file))

        with NamedTemporaryFile('wt') as tmp:
            tmp.write('foo\nbar')
            tmp.flush()
            self.assertIsInstance(tools.read_file(tmp.name), str)
            self.assertEqual(tools.read_file(tmp.name), 'foo\nbar')

        tmp_gz = NamedTemporaryFile().name
        with gzip.open(tmp_gz + '.gz', 'wt') as f:
            f.write('foo\nbar')
            f.flush()
        self.assertIsInstance(tools.read_file(tmp_gz), str)
        self.assertEqual(tools.read_file(tmp_gz), 'foo\nbar')
        os.remove(tmp_gz+ '.gz')

    def test_read_file_lines(self):
        """
        Test the function read_file_lines
        """
        test_tools_file = os.path.abspath(__file__)
        test_directory = os.path.dirname(test_tools_file)
        non_existing_file = os.path.join(test_directory, "nonExistingFile")

        output = tools.read_file_lines(test_tools_file)
        self.assertIsInstance(output, list)
        self.assertGreaterEqual(len(output), 1)
        self.assertIsInstance(output[0], str)
        self.assertIsNone(tools.read_file_lines(non_existing_file))

        with NamedTemporaryFile('wt') as tmp:
            tmp.write('foo\nbar')
            tmp.flush()
            self.assertIsInstance(tools.read_file_lines(tmp.name), list)
            self.assertListEqual(tools.read_file_lines(tmp.name), ['foo', 'bar'])

        tmp_gz = NamedTemporaryFile().name
        with gzip.open(tmp_gz + '.gz', 'wt') as f:
            f.write('foo\nbar')
            f.flush()
        self.assertIsInstance(tools.read_file_lines(tmp_gz), list)
        self.assertEqual(tools.read_file_lines(tmp_gz), ['foo', 'bar'])
        os.remove(tmp_gz+ '.gz')

    def test_check_command(self):
        """
        Test the function check_command
        """
        self.assertFalse(tools.check_command(''))
        self.assertFalse(tools.check_command("notExistedCommand"))
        self.assertTrue(tools.check_command("ls"))
        self.assertTrue(tools.check_command('backintime'))

    def test_which(self):
        """
        Test the function which
        """
        self.assertRegex(tools.which("ls"), r'/.*/ls')
        self.assertEqual(tools.which('backintime'),
                         os.path.join(os.getcwd(), 'backintime'))
        self.assertIsNone(tools.which("notExistedCommand"))

    def test_make_dirs(self):
        self.assertFalse(tools.make_dirs('/'))
        self.assertTrue(tools.make_dirs(os.getcwd()))
        with TemporaryDirectory() as d:
            path = os.path.join(d, 'foo', 'bar')
            self.assertTrue(tools.make_dirs(path))

    def test_make_dirs_not_writeable(self):
        with TemporaryDirectory() as d:
            os.chmod(d, stat.S_IRUSR)
            path = os.path.join(d, 'foobar{}'.format(random.randrange(100, 999)))
            self.assertFalse(tools.make_dirs(path))

    def test_mkdir(self):
        self.assertFalse(tools.mkdir('/'))
        with TemporaryDirectory() as d:
            path = os.path.join(d, 'foo')
            self.assertTrue(tools.mkdir(path))
            for mode in (0o700, 0o644, 0o777):
                msg = 'new path should have octal permissions {0:#o}'.format(mode)
                path = os.path.join(d, '{0:#o}'.format(mode))
                self.assertTrue(tools.mkdir(path, mode), msg)
                self.assertEqual('{0:o}'.format(os.stat(path).st_mode & 0o777), '{0:o}'.format(mode), msg)

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

    def test_check_x_server(self):
        try:
            tools.check_x_server()
        except Exception as e:
            self.fail('tools.ckeck_x_server() raised exception {}'.format(str(e)))

    def test_prepare_path(self):
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

    def test_power_status_available(self):
        if tools.process_exists('upowerd') and not generic.ON_TRAVIS:
            self.assertTrue(tools.power_status_available())
        else:
            self.assertFalse(tools.power_status_available())
        self.assertIsInstance(tools.on_battery(), bool)

    def test_get_rsync_caps(self):
        if RSYNC_INSTALLED:
            caps = tools.get_rsync_caps()
            self.assertIsInstance(caps, list)
            self.assertGreaterEqual(len(caps), 1)

        self.assertListEqual(tools.get_rsync_caps(data = RSYNC_307_VERSION),
                             ['64-bit files',
                              '64-bit inums',
                              '32-bit timestamps',
                              '64-bit long ints',
                              'socketpairs',
                              'hardlinks',
                              'symlinks',
                              'IPv6',
                              'batchfiles',
                              'inplace',
                              'append',
                              'ACLs',
                              'xattrs',
                              'iconv',
                              'symtimes'])

        self.assertListEqual(tools.get_rsync_caps(data = RSYNC_310_VERSION),
                             ['progress2',
                              '64-bit files',
                              '64-bit inums',
                              '64-bit timestamps',
                              '64-bit long ints',
                              'socketpairs',
                              'hardlinks',
                              'symlinks',
                              'IPv6',
                              'batchfiles',
                              'inplace',
                              'append',
                              'ACLs',
                              'xattrs',
                              'iconv',
                              'symtimes',
                              'prealloc'])

    @unittest.skip('Not yet implemented')
    def test_get_rsync_prefix(self):
        pass

    @unittest.skip('Not yet implemented')
    def test_temp_failure_retry(self):
        pass

    def test_get_md5sum_from_path(self):
        with NamedTemporaryFile() as f:
            f.write(b'foo')
            f.flush()

            self.assertEqual(tools._get_md5sum_from_path(f.name),
                             'acbd18db4cc2f85cedef654fccc4a4d8')

    def test_check_cron_pattern(self):
        self.assertTrue(tools.check_cron_pattern('0'))
        self.assertTrue(tools.check_cron_pattern('0,10,13,15,17,20,23'))
        self.assertTrue(tools.check_cron_pattern('*/6'))
        self.assertFalse(tools.check_cron_pattern('a'))
        self.assertFalse(tools.check_cron_pattern(' 1'))
        self.assertFalse(tools.check_cron_pattern('0,10,13,1a,17,20,23'))
        self.assertFalse(tools.check_cron_pattern('0,10,13, 15,17,20,23'))
        self.assertFalse(tools.check_cron_pattern('*/6,8'))
        self.assertFalse(tools.check_cron_pattern('*/6 a'))

    @unittest.skip('Not yet implemented')
    def test_check_home_encrypt(self):
        pass

    #load_env and save_env tests are in TestToolsEnviron below

    @unittest.skip('Not yet implemented')
    def test_keyring_supported(self):
        pass

    @unittest.skip('Not yet implemented')
    def test_get_password(self):
        pass

    @unittest.skip('Not yet implemented')
    def test_set_password(self):
        pass

    def test_get_mountpoint(self):
        self.assertEqual(tools.get_mountpoint('/nonExistingFolder/foo/bar'), '/')
        proc = os.path.join('/proc', str(os.getpid()), 'fd')
        self.assertEqual(tools.get_mountpoint(proc), '/proc')

    def test_get_mount_args(self):
        rootArgs = tools.get_mount_args('/')
        self.assertIsInstance(rootArgs, list)
        self.assertGreaterEqual(len(rootArgs), 3)
        self.assertEqual(rootArgs[1], '/')

        procArgs = tools.get_mount_args('/proc')
        self.assertGreaterEqual(len(procArgs), 3)
        self.assertEqual(procArgs[0], 'proc')
        self.assertEqual(procArgs[1], '/proc')
        self.assertEqual(procArgs[2], 'proc')

    def test_get_device(self):
        self.assertEqual(tools.get_device('/proc'), 'proc')
        self.assertRegex(tools.get_device('/sys'), r'sys.*')
        self.assertRegex(tools.get_device('/nonExistingFolder/foo/bar'),
                         r'/dev/.*')

    def test_get_filesystem(self):
        self.assertEqual(tools.get_filesystem('/proc'), 'proc')
        self.assertRegex(tools.get_filesystem('/sys'), r'sys.*')
        self.assertRegex(tools.get_filesystem('/nonExistingFolder/foo/bar').lower(),
                         r'(:?ext[2-4]|xfs|zfs|jfs|raiserfs|btrfs)')

    # tools.get_uuid() get called from tools.get_uuid_from_path.
    # So we skip an extra unittest as it's hard to find a dev on all systems
    @unittest.skipIf(not DISK_BY_UUID_AVAILABLE and not UDEVADM_HAS_UUID,
                     'No UUIDs available on this system.')
    def test_get_uuid_from_path(self):
        uuid = tools.get_uuid_from_path('/nonExistingFolder/foo/bar')
        self.assertIsInstance(uuid, str)
        self.assertRegex(uuid.lower(), r'^[a-f0-9\-]+$')
        self.assertEqual(len(uuid.replace('-', '')), 32)

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

    @unittest.skip('Not yet implemented')
    def test_wrap_line(self):
        pass

    def test_syncfs(self):
        self.assertTrue(tools.syncfs())

    def test_isRoot(self):
        self.assertIsInstance(tools.isRoot(), bool)

    def test_usingSudo(self):
        self.assertIsInstance(tools.usingSudo(), bool)

    def test_patternHasNotEncryptableWildcard(self):
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('/foo'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo/*/bar'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo/**/bar'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('*/foo'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('**/foo'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo/*'))
        self.assertFalse(tools.patternHasNotEncryptableWildcard('foo/**'))

        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo?'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo[1-2]'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo*'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('*foo'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('**foo'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('*.foo'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo*bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo**bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo*/bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo**/bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo/*bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo/**bar'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('foo/*/bar*'))
        self.assertTrue(tools.patternHasNotEncryptableWildcard('*foo/*/bar'))

    def test_readTimeStamp(self):
        with NamedTemporaryFile('wt') as f:
            f.write('20160127 0124')
            f.flush()
            self.assertEqual(tools.readTimeStamp(f.name),
                             datetime(2016, 1, 27, 1, 24))

        with NamedTemporaryFile('wt') as f:
            f.write('20160127')
            f.flush()
            self.assertEqual(tools.readTimeStamp(f.name),
                             datetime(2016, 1, 27, 0, 0))

    def test_writeTimeStamp(self):
        with NamedTemporaryFile('rt') as f:
            tools.writeTimeStamp(f.name)
            s = f.read().strip('\n')
            self.assertTrue(s.replace(' ', '').isdigit())
            self.assertEqual(len(s), 13)

    @unittest.skip('Not yet implemented')
    def test_inhibitSuspend(self):
        pass

    @unittest.skip('Not yet implemented')
    def test_unInhibitSuspend(self):
        pass

    @unittest.skipIf(not tools.check_command('ssh-keygen'),
                     "'ssh-keygen' not found.")
    def test_getSshKeyFingerprint(self):
        self.assertIsNone(tools.getSshKeyFingerprint(os.path.abspath(__file__)))

        with TemporaryDirectory() as d:
            key = os.path.join(d, 'key')
            cmd = ['ssh-keygen', '-q', '-N', '', '-f', key]
            proc = subprocess.Popen(cmd)
            proc.communicate()

            fingerprint = tools.getSshKeyFingerprint(key)
            self.assertIsInstance(fingerprint, str)
            if fingerprint.startswith('SHA256'):
                self.assertEqual(len(fingerprint), 50)
                self.assertRegex(fingerprint, r'^SHA256:[a-zA-Z0-9/+]+$')
            else:
                self.assertEqual(len(fingerprint), 47)
                self.assertRegex(fingerprint, r'^[a-fA-F0-9:]+$')

    @unittest.skipIf(not tools.check_command('crontab'),
                     "'crontab' not found.")
    def test_readWriteCrontab(self):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        oldCrontab = tools.readCrontab()
        self.assertIsInstance(oldCrontab, list)

        testLine = '#BackInTime Unittest from {}. Test probably failed. You can remove this line.'.format(now)
        self.assertTrue(tools.writeCrontab(oldCrontab + [testLine,]))

        newCrontab = tools.readCrontab()
        self.assertIn(testLine, newCrontab)
        self.assertEqual(len(newCrontab), len(oldCrontab) + 1)

        self.assertTrue(tools.writeCrontab(oldCrontab))
        if oldCrontab:
            self.assertListEqual(oldCrontab, tools.readCrontab())

    def test_splitCommands(self):
        ret = list(tools.splitCommands(['echo foo;'],
                                       head = 'echo start;',
                                       tail = 'echo end',
                                       maxLength = 40))
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0], 'echo start;echo foo;echo end')

        ret = list(tools.splitCommands(['echo foo;']*3,
                                       head = 'echo start;',
                                       tail = 'echo end',
                                       maxLength = 40))
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret[0], 'echo start;echo foo;echo foo;echo end')
        self.assertEqual(ret[1], 'echo start;echo foo;echo end')

        ret = list(tools.splitCommands(['echo foo;']*3,
                                       head = 'echo start;',
                                       tail = 'echo end',
                                       maxLength = 0))
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0], 'echo start;echo foo;echo foo;echo foo;echo end')

        ret = list(tools.splitCommands(['echo foo;']*3,
                                       head = 'echo start;',
                                       tail = 'echo end',
                                       maxLength = -10))
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0], 'echo start;echo foo;echo foo;echo foo;echo end')

class TestToolsEnviron(generic.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestToolsEnviron, self).__init__(*args, **kwargs)
        self.env = deepcopy(os.environ)

    def setUp(self):
        super(TestToolsEnviron, self).setUp()
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

class TestToolsUniquenessSet(generic.TestCase):
    #TODO: add test for follow_symlink
    def test_check_unique(self):
        with TemporaryDirectory() as d:
            for i in range(1, 5):
                os.mkdir(os.path.join(d, str(i)))
            t1 = os.path.join(d, '1', 'foo')
            t2 = os.path.join(d, '2', 'foo')
            t3 = os.path.join(d, '3', 'foo')
            t4 = os.path.join(d, '4', 'foo')

            for i in (t1, t2):
                with open(i, 'wt') as f:
                    f.write('bar')
            for i in (t3, t4):
                with open(i, 'wt') as f:
                    f.write('42')

            #same size and mtime
            uniqueness = tools.UniquenessSet(dc = False,
                                             follow_symlink = False,
                                             list_equal_to = '')
            self.assertTrue(uniqueness.check_for(t1))
            self.assertFalse(uniqueness.check_for(t2))
            self.assertTrue(uniqueness.check_for(t3))
            self.assertFalse(uniqueness.check_for(t4))

            os.utime(t1, times = (0, 0))
            os.utime(t3, times = (0, 0))

            #same size different mtime
            uniqueness = tools.UniquenessSet(dc = False,
                                             follow_symlink = False,
                                             list_equal_to = '')
            self.assertTrue(uniqueness.check_for(t1))
            self.assertTrue(uniqueness.check_for(t2))
            self.assertTrue(uniqueness.check_for(t3))
            self.assertTrue(uniqueness.check_for(t4))

            #same size different mtime use deep_check
            uniqueness = tools.UniquenessSet(dc = True,
                                             follow_symlink = False,
                                             list_equal_to = '')
            self.assertTrue(uniqueness.check_for(t1))
            self.assertFalse(uniqueness.check_for(t2))
            self.assertTrue(uniqueness.check_for(t3))
            self.assertFalse(uniqueness.check_for(t4))

    def test_check_unique_hardlinks(self):
        with TemporaryDirectory() as d:
            for i in range(1, 5):
                os.mkdir(os.path.join(d, str(i)))
            t1 = os.path.join(d, '1', 'foo')
            t2 = os.path.join(d, '2', 'foo')
            t3 = os.path.join(d, '3', 'foo')
            t4 = os.path.join(d, '4', 'foo')

            with open(t1, 'wt') as f:
                f.write('bar')
            os.link(t1, t2)
            self.assertEqual(os.stat(t1).st_ino, os.stat(t2).st_ino)

            with open(t3, 'wt') as f:
                f.write('42')
            os.link(t3, t4)
            self.assertEqual(os.stat(t3).st_ino, os.stat(t4).st_ino)

            uniqueness = tools.UniquenessSet(dc = True,
                                             follow_symlink = False,
                                             list_equal_to = '')
            self.assertTrue(uniqueness.check_for(t1))
            self.assertFalse(uniqueness.check_for(t2))
            self.assertTrue(uniqueness.check_for(t3))
            self.assertFalse(uniqueness.check_for(t4))

    def test_check_equal(self):
        with TemporaryDirectory() as d:
            for i in range(1, 5):
                os.mkdir(os.path.join(d, str(i)))
            t1 = os.path.join(d, '1', 'foo')
            t2 = os.path.join(d, '2', 'foo')
            t3 = os.path.join(d, '3', 'foo')
            t4 = os.path.join(d, '4', 'foo')

            for i in (t1, t2):
                with open(i, 'wt') as f:
                    f.write('bar')
            for i in (t3, t4):
                with open(i, 'wt') as f:
                    f.write('42')

            #same size and mtime
            uniqueness = tools.UniquenessSet(dc = False,
                                             follow_symlink = False,
                                             list_equal_to = t1)
            self.assertTrue(uniqueness.check_for(t1))
            self.assertTrue(uniqueness.check_for(t2))
            self.assertFalse(uniqueness.check_for(t3))

            os.utime(t1, times = (0, 0))

            #same size different mtime
            uniqueness = tools.UniquenessSet(dc = False,
                                             follow_symlink = False,
                                             list_equal_to = t1)
            self.assertTrue(uniqueness.check_for(t1))
            self.assertFalse(uniqueness.check_for(t2))
            self.assertFalse(uniqueness.check_for(t3))

            #same size different mtime use deep_check
            uniqueness = tools.UniquenessSet(dc = True,
                                             follow_symlink = False,
                                             list_equal_to = t1)
            self.assertTrue(uniqueness.check_for(t1))
            self.assertTrue(uniqueness.check_for(t2))
            self.assertFalse(uniqueness.check_for(t3))

class TestToolsExecuteSubprocess(generic.TestCase):
    # new method with subprocess
    def test_returncode(self):
        self.assertEqual(tools.Execute(['true']).run(), 0)
        self.assertEqual(tools.Execute(['false']).run(), 1)

    def test_callback(self):
        c = lambda x, y: self.callback(self.assertEqual, x, 'foo')
        tools.Execute(['echo', 'foo'], callback = c).run()
        self.assertTrue(self.run)
        self.run = False

        # give extra user_data for callback
        c = lambda x, y: self.callback(self.assertEqual, x, y)
        tools.Execute(['echo', 'foo'], callback = c, user_data = 'foo').run()
        self.assertTrue(self.run)
        self.run = False

        # no output
        c = lambda x, y: self.callback(self.fail,
                                       'callback was called unexpectedly')
        tools.Execute(['true'], callback = c).run()
        self.assertFalse(self.run)
        self.run = False

    def test_pausable(self):
        proc = tools.Execute(['true'])
        self.assertTrue(proc.pausable)

class TestToolsExecuteOsSystem(generic.TestCase):
    # old method with os.system
    def test_returncode(self):
        self.assertEqual(tools.Execute('true').run(), 0)
        self.assertEqual(tools.Execute('false').run(), 256)

    def test_callback(self):
        c = lambda x, y: self.callback(self.assertEqual, x, 'foo')
        tools.Execute('echo foo', callback = c).run()
        self.assertTrue(self.run)
        self.run = False

        # give extra user_data for callback
        c = lambda x, y: self.callback(self.assertEqual, x, y)
        tools.Execute('echo foo', callback = c, user_data = 'foo').run()
        self.assertTrue(self.run)
        self.run = False

        # no output
        c = lambda x, y: self.callback(self.fail,
                                       'callback was called unexpectedly')
        tools.Execute('true', callback = c).run()
        self.assertFalse(self.run)
        self.run = False

    def test_pausable(self):
        proc = tools.Execute('true')
        self.assertFalse(proc.pausable)

if __name__ == '__main__':
    unittest.main()
