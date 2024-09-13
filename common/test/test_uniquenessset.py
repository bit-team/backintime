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
from tempfile import TemporaryDirectory
# import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
from test import generic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from uniquenessset import UniquenessSet


class General(generic.TestCase):
    # TODO: add test for follow_symlink
    def test_unique(self):
        """???"""
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
