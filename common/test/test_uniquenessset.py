# SPDX-FileCopyrightText: © 2010 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about the uniquenessset module."""
import os
import sys
import subprocess
import random
import pathlib
import gzip
import stat
import signal
from datetime import datetime
from time import sleep
from unittest.mock import patch
from copy import deepcopy
from tempfile import NamedTemporaryFile, TemporaryDirectory
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from uniquenessset import UniquenessSet
import configfile

# # chroot jails used for building may have no UUID devices (because of tmpfs)
# # we need to skip tests that require UUIDs
# DISK_BY_UUID_AVAILABLE = os.path.exists(tools.DISK_BY_UUID)

# UDEVADM_HAS_UUID = subprocess.Popen(
#     ['udevadm', 'info', '-e'],
#     stdout=subprocess.PIPE,
#     stderr=subprocess.DEVNULL).communicate()[0].find(b'ID_FS_UUID=') > 0

# RSYNC_INSTALLED = tools.checkCommand('rsync')

# RSYNC_307_VERSION = """rsync  version 3.0.7  protocol version 30
# Copyright (C) 1996-2009 by Andrew Tridgell, Wayne Davison, and others.
# Web site: http://rsync.samba.org/
# Capabilities:
#     64-bit files, 64-bit inums, 32-bit timestamps, 64-bit long ints,
#     socketpairs, hardlinks, symlinks, IPv6, batchfiles, inplace,
#     append, ACLs, xattrs, iconv, symtimes

# rsync comes with ABSOLUTELY NO WARRANTY.  This is free software, and you
# are welcome to redistribute it under certain conditions.  See the GNU
# General Public License for details.
# """

# RSYNC_310_VERSION = """rsync  version 3.1.0  protocol version 31
# Copyright (C) 1996-2013 by Andrew Tridgell, Wayne Davison, and others.
# Web site: http://rsync.samba.org/
# Capabilities:
#     64-bit files, 64-bit inums, 64-bit timestamps, 64-bit long ints,
#     socketpairs, hardlinks, symlinks, IPv6, batchfiles, inplace,
#     append, ACLs, xattrs, iconv, symtimes, prealloc

# rsync comes with ABSOLUTELY NO WARRANTY.  This is free software, and you
# are welcome to redistribute it under certain conditions.  See the GNU
# General Public License for details.
# """


class General(generic.TestCase):
    # TODO: add test for follow_symlink
    def test_checkUnique(self):
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

            # fix timestamps because otherwise test will fail on slow machines
            obj = os.stat(t1)
            os.utime(t2, times=(obj.st_atime, obj.st_mtime))
            obj = os.stat(t3)
            os.utime(t4, times=(obj.st_atime, obj.st_mtime))

            # same size and mtime
            uniqueness = UniquenessSet(dc=False,
                                             follow_symlink=False,
                                             list_equal_to='')
            self.assertTrue(uniqueness.check(t1))
            self.assertFalse(uniqueness.check(t2))
            self.assertTrue(uniqueness.check(t3))
            self.assertFalse(uniqueness.check(t4))

            os.utime(t1, times=(0, 0))
            os.utime(t3, times=(0, 0))

            # same size different mtime
            uniqueness = UniquenessSet(dc=False,
                                             follow_symlink=False,
                                             list_equal_to='')
            self.assertTrue(uniqueness.check(t1))
            self.assertTrue(uniqueness.check(t2))
            self.assertTrue(uniqueness.check(t3))
            self.assertTrue(uniqueness.check(t4))

            # same size different mtime use deep_check
            uniqueness = UniquenessSet(dc=True,
                                             follow_symlink=False,
                                             list_equal_to='')
            self.assertTrue(uniqueness.check(t1))
            self.assertFalse(uniqueness.check(t2))
            self.assertTrue(uniqueness.check(t3))
            self.assertFalse(uniqueness.check(t4))

    def test_checkUnique_hardlinks(self):
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

            uniqueness = UniquenessSet(dc=True,
                                             follow_symlink=False,
                                             list_equal_to='')
            self.assertTrue(uniqueness.check(t1))
            self.assertFalse(uniqueness.check(t2))
            self.assertTrue(uniqueness.check(t3))
            self.assertFalse(uniqueness.check(t4))

    def test_checkEqual(self):
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

            # fix timestamps because otherwise test will fail on slow machines
            obj = os.stat(t1)
            os.utime(t2, times=(obj.st_atime, obj.st_mtime))
            obj = os.stat(t3)
            os.utime(t4, times=(obj.st_atime, obj.st_mtime))

            # same size and mtime
            uniqueness = UniquenessSet(dc=False,
                                             follow_symlink=False,
                                             list_equal_to=t1)
            self.assertTrue(uniqueness.check(t1))
            self.assertTrue(uniqueness.check(t2))
            self.assertFalse(uniqueness.check(t3))

            os.utime(t1, times=(0, 0))

            # same size different mtime
            uniqueness = UniquenessSet(dc=False,
                                             follow_symlink=False,
                                             list_equal_to=t1)
            self.assertTrue(uniqueness.check(t1))
            self.assertFalse(uniqueness.check(t2))
            self.assertFalse(uniqueness.check(t3))

            # same size different mtime use deep_check
            uniqueness = UniquenessSet(dc=True,
                                             follow_symlink=False,
                                             list_equal_to=t1)
            self.assertTrue(uniqueness.check(t1))
            self.assertTrue(uniqueness.check(t2))
            self.assertFalse(uniqueness.check(t3))
