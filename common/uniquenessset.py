# SPDX-FileCopyrightText: © 2010 paul <paul@woland>
# SPDX-FileCopyrightText: © 2010 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module about UniquenessSet"""
import os
import logger
from tools import md5sum


class UniquenessSet:
    """Check for uniqueness or equality of file(s).

    Uniqueness means that there are no duplicates. Equality means that two
    elements have the same value or properties.

    Equality is checked only if a file is specified with ``equal_to`` otherwise
    uniqueness will be checked. The latter is based on previous file
    checks. The class store hashes of each file checked via ``check()`` or
    ``checkUnique()``.

    Dev note (buhtz, 2024-10): The class is used in SnapshotsDialog and only in
    the specific/rare case when single files are compared. The class does two
    different things implicit. Not sure if this is a good solution. My
    recommendation is to move that code/feature into 'qt' into or near the
    `SnapshotsDialog` class.
    """

    def __init__(self, deep_check=False, follow_symlink=False, equal_to=''):
        """
        Args:
            deep_check (bool): If ``True`` use deep check which will compare
                files md5sums if they are of same size but no
                hardlinks (don't have the same inode).
                If ``False`` use files size and mtime
            follow_symlink (bool): Check symlinks target instead of the
                link itself (default: ``False``).
            equal_to (str): Full path to file. If not empty only return
                equal files to the given path instead of unique
                files. (default: ``''``)
        """
        self.deep_check = deep_check
        self.follow_sym = follow_symlink

        # if not self._uniq_dict[size] -> size already checked with md5sum
        self._uniq_dict = {}

        # if (size, inode) in self._size_inode -> path is a hlink
        self._size_inode = set()

        self.equal_to = equal_to

        if equal_to:
            st = os.stat(equal_to)

            if self.deep_check:
                self.reference = (st.st_size, md5sum(equal_to))

            else:
                self.reference = (st.st_size, int(st.st_mtime))

    def check(self, input_path):
        """Check file ``input_path`` for either uniqueness or equality
        (depending on ``equal_to`` from constructor).

        Args:
            input_path (str):   full path to file

        Returns:
            bool: ``True`` if file is unique and ``equal_to``
                is empty. Or ``True`` if file is equal to file in
                ``equal_to``
        """
        path = input_path

        # follow symlinks ?
        if self.follow_sym and os.path.islink(input_path):
            path = os.readlink(input_path)

        if self.equal_to:
            return self.checkEqual(path)

        else:
            return self.checkUnique(path)

    def checkUnique(self, path):
        """Check file ``path`` for uniqueness and store a unique key for
        ``path``.

        This check is performed if `equal_to` is empty. By default
        (``deep_check is False``) the uniqueness is based on file size and
        mtime. If ``deep_check is True`` the uniqueness is based on inode
        number and the files size (or md5sum).

        Args:
            path (str): Full path to file.

        Returns:
            bool: ``True`` if file is unique.

        """
        logger.debug(f'{path=}')

        if self.deep_check:
            stat = os.stat(path)
            size, inode = stat.st_size, stat.st_ino

            # Hardlink?
            if (size, inode) in self._size_inode:
                logger.debug(
                    "[deep test]: skip, it's a duplicate (size, inode)", self)
                return False

            self._size_inode.add((size, inode))

            if size not in self._uniq_dict:
                # first item of that size
                unique_key = size
                logger.debug("[deep test]: store current size?", self)

            else:
                prev = self._uniq_dict[size]
                if prev:
                    # store md5sum instead of previously stored size
                    md5sum_prev = md5sum(prev)
                    self._uniq_dict[md5sum_prev] = prev
                    # remove the entry with that size
                    self._uniq_dict[size] = None
                    logger.debug(
                        "[deep test]: size duplicate, remove the size, store "
                        "prev md5sum", self)
                unique_key = md5sum(path)
                logger.debug("[deep test]: store current md5sum?", self)

        else:
            # store a tuple of (size, modification time)
            obj = os.stat(path)
            unique_key = (obj.st_size, int(obj.st_mtime))

        # store if not already present, then return True
        if unique_key not in self._uniq_dict:
            logger.debug(" >> ok, store!", self)
            self._uniq_dict[unique_key] = path

            return True

        logger.debug(" >> skip (it's a duplicate)", self)

        return False

    def checkEqual(self, path):
        """Check if ``path`` is equal to the file specified by ``equal_to``.

        Args:
            path (str): Full path to file.

        Returns:
            bool: ``True`` if file is equal.
        """
        st = os.stat(path)

        if self.deep_check:

            if self.reference[0] == st.st_size:
                return self.reference[1] == md5sum(path)

            return False

        else:
            return self.reference == (st.st_size, int(st.st_mtime))
