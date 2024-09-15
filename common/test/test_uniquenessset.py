# SPDX-FileCopyrightText: © 2010 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests about the uniquenessset module."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import pyfakefs.fake_filesystem_unittest as pyfakefs_ut
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from uniquenessset import UniquenessSet
import logger
logger.DEBUG = True


class General(pyfakefs_ut.TestCase):
    # TODO: add test for follow_symlink
    def setUp(self):
        """Setup a fake filesystem."""
        self.setUpPyfakefs(allow_root_user=False)

    def _create_unique_file_pairs(self, pairs):
        result = []
        for one, two, content in pairs:
            for fp in [one, two]:
                # create dir
                fp.parent.mkdir(parents=True, exist_ok=True)

                # create file
                with fp.open('wt', encoding='utf-8') as handle:
                    handle.write(content)

            # Sync their timestamps
            os.utime(two, times=(one.stat().st_atime, one.stat().st_mtime))

            result.extend((one, two))

        return result

    def test_ctor_defaults(self):
        """Default values in constructor."""
        with TemporaryDirectory(prefix='bit.') as temp_name:
            temp_path = Path(temp_name)
            files = self._create_unique_file_pairs([(
                temp_path / 'foo',
                temp_path / 'bar',
                'xyz')])

            sut = UniquenessSet()

            # unique-check by default
            self.assertTrue(sut.check(files[0]))
            # Comopared to previous file, not unique by size & mtime
            self.assertFalse(sut.check(files[1]))

    def test_fail_equal_without_equal_to(self):
        """Uncovered (but not important) edge case."""
        with TemporaryDirectory(prefix='bit.') as temp_name:
            temp_path = Path(temp_name)
            fp = temp_path / 'foo'
            fp.write_text('bar')

            sut = UniquenessSet(deep_check=False,
                                follow_symlink=False,
                                equal_to='')

            with self.assertRaises(AttributeError):
                # Explicit equal-check not possible because 'equal_to' is
                # empty.
                sut.checkEqual(fp)

    def test_unique_myself(self):
        """Test file uniqueness to itself"""
        with TemporaryDirectory(prefix='bit.') as temp_name:
            temp_path = Path(temp_name)
            fp = temp_path / 'bar'
            fp.write_text('foo')

            # unique-check is used because 'equal_to' is empty
            sut = UniquenessSet(deep_check=False,
                                follow_symlink=False,
                                equal_to='')

            # Is unique, because no check was done before.
            self.assertTrue(sut.check(fp))

            # Not unique anymore, not even to itself, because its hash was
            # stored from the previous check.
            self.assertFalse(sut.check(fp))

    def test_size_mtime(self):
        """Uniqueness by size and mtime"""
        with TemporaryDirectory(prefix='bit.') as temp_name:
            temp_path = Path(temp_name)
            files = self._create_unique_file_pairs([
                (
                    temp_path / '1' / 'foo',
                    temp_path / '2' / 'foo',
                    'bar'
                ),
                (
                    temp_path / '3' / 'foo',
                    temp_path / '4' / 'foo',
                    '42'
                ),
            ])

            sut = UniquenessSet(deep_check=False,
                                follow_symlink=False,
                                equal_to='')

            self.assertTrue(sut.check(files[0]))
            self.assertTrue(sut.check(files[2]))

            self.assertFalse(sut.check(files[1]))
            self.assertFalse(sut.check(files[3]))

    def test_unique_size_but_different_mtime(self):
        """Unique size but mtime is different."""
        with TemporaryDirectory(prefix='bit.') as temp_name:
            temp_path = Path(temp_name)
            files = self._create_unique_file_pairs([
                (
                    temp_path / '1' / 'foo',
                    temp_path / '2' / 'foo',
                    'bar'
                ),
                (
                    temp_path / '3' / 'foo',
                    temp_path / '4' / 'foo',
                    'different_size'
                ),
            ])

            # different mtime
            os.utime(files[0], times=(0, 0))
            os.utime(files[2], times=(0, 0))

            # same size different mtime
            sut = UniquenessSet(deep_check=False,
                                follow_symlink=False,
                                equal_to='')

            # Each file is unique (different from each other)
            self.assertTrue(sut.check(files[0]))
            self.assertTrue(sut.check(files[1]))
            self.assertTrue(sut.check(files[2]))
            self.assertTrue(sut.check(files[3]))

    def test_deep_check(self):
        """Uniqueness by content only"""
        with TemporaryDirectory(prefix='bit.') as temp_name:
            temp_path = Path(temp_name)

            # Size is the same (3 chars content per file)
            fpa = temp_path / 'foo'
            fpa.write_text('one')
            fpb = temp_path / 'bar'
            fpb.write_text('bar')

            # mtime is the same
            os.utime(fpb, times=(fpa.stat().st_atime, fpa.stat().st_mtime))

            # Not deep: check by size and mtime
            sut = UniquenessSet(deep_check=False,
                                follow_symlink=False,
                                equal_to='')

            self.assertTrue(sut.check(fpa))
            self.assertFalse(sut.check(fpb))

            # Now with deep check
            sut = UniquenessSet(deep_check=True,
                                follow_symlink=False,
                                equal_to='')

            self.assertTrue(sut.check(fpa))
            self.assertTrue(sut.check(fpb))

    # def test_something_with_hardlinks(self):
    #     """Despite its method name, it does not really test for hardlinks.
    #     That dest origins from the original code base. I see not much value
    #     in it. The hardlink behavior in the productive code seems untestable
    #     to me. the ``checkUnique()`` method internally shortens its path if
    #     there are hardlinks, otherwise it use md5sum.
    #     """
    #     with TemporaryDirectory(prefix='bit.') as temp_name:
    #         temp_path = Path(temp_name)

    #         fpa = temp_path / 'foo'
    #         fpb = temp_path / 'bar'

    #         fpa_hardlink = temp_path / 'hl_foo'
    #         fpb_hardlink = temp_path / 'hl_bar'

    #         fpa.write_text('red')
    #         fpb.write_text('blue')
    #         fpa_hardlink.write_text('red')
    #         fpb_hardlink.write_text('blue')

    #         # fpa_hardlink.hardlink_to(fpa)
    #         # fpb_hardlink.hardlink_to(fpb)

    #         # os.utime(fpa_hardlink,
    #         #          times=(fpa.stat().st_atime, fpa.stat().st_mtime))
    #         # os.utime(fpb_hardlink,
    #         #          times=(fpb.stat().st_atime, fpb.stat().st_mtime))

    #         # # Be sure that this are hardlinks. (But it does not matter)
    #         # self.assertEqual(fpa.stat().st_ino, fpa_hardlink.stat().st_ino)
    #         # self.assertEqual(fpb.stat().st_ino, fpb_hardlink.stat().st_ino)

    #         sut = UniquenessSet(deep_check=True,
    #                             follow_symlink=False,
    #                             equal_to='')

    #         self.assertTrue(sut.check(fpa))
    #         self.assertFalse(sut.check(fpa_hardlink))
    #         self.assertTrue(sut.check(fpb))
    #         self.assertFalse(sut.check(fpb_hardlink))
