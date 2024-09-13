# SPDX-FileCopyrightText: © 2010 paul <paul@woland>
# SPDX-FileCopyrightText: © 2010 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module with UniquenessSet class"""
import os
import sys
import pathlib
import subprocess
import shlex
import signal
import re
import errno
import gzip
import locale
import gettext
import hashlib
import ipaddress
from datetime import datetime
from packaging.version import Version
from typing import Union
import logger
from tools import md5sum

# # Try to import keyring
# is_keyring_available = False
# try:
#     # Jan 4, 2024 aryoda: The env var BIT_USE_KEYRING is neither documented
#     #                     anywhere nor used at all in the code.
#     #                     Via "git blame" I have found a commit message saying:
#     #                     "block subsequent 'import keyring' if it failed once"
#     #                     So I assume it is an internal temporary env var only.
#     # Note: os.geteuid() is used instead of tools.isRoot() here
#     #       because the latter is still not available here in the global
#     #       module code.
#     if os.getenv('BIT_USE_KEYRING', 'true') == 'true' and os.geteuid() != 0:
#         import keyring
#         from keyring import backend
#         import keyring.util.platform_
#         is_keyring_available = True
# except Exception as e:
#     is_keyring_available = False
#     # block subsequent 'import keyring' if it failed once before
#     os.putenv('BIT_USE_KEYRING', 'false')
#     logger.warning(f"'import keyring' failed with: {repr(e)}")

# # getting dbus imports to work in Travis CI is a huge pain
# # use conditional dbus import
# ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'
# ON_RTD = os.environ.get('READTHEDOCS', 'None').lower() == 'true'

# try:
#     import dbus
# except ImportError:
#     if ON_TRAVIS or ON_RTD:
#         # python-dbus doesn't work on Travis yet.
#         dbus = None
#     else:
#         raise

# import configfile
# import bcolors
# from exceptions import Timeout, InvalidChar, InvalidCmd, LimitExceeded, PermissionDeniedByPolicy
# import languages

# # Workaround:
# # While unittesting and without regular invocation of BIT the GNU gettext
# # class-based API isn't setup yet.
# try:
#     _('Warning')
# except NameError:
#     _ = lambda val: val

# DISK_BY_UUID = '/dev/disk/by-uuid'


class UniquenessSet:
    """
    Check for uniqueness or equality of files.

    """
    def __init__(self, dc=False, follow_symlink=False, list_equal_to=''):
        """
        Args:
            dc (bool):              if ``True`` use deep check which will compare
                                    files md5sums if they are of same size but no
                                    hardlinks (don't have the same inode).
                                    If ``False`` use files size and mtime
            follow_symlink (bool):  if ``True`` check symlinks target instead of the
                                    link
            list_equal_to (str):    full path to file. If not empty only return
                                    equal files to the given path instead of
                                    unique files.
        """
        self.deep_check = dc
        self.follow_sym = follow_symlink
        self._uniq_dict = {}      # if not self._uniq_dict[size] -> size already checked with md5sum
        self._size_inode = set()  # if (size,inode) in self._size_inode -> path is a hlink
        self.list_equal_to = list_equal_to
        if list_equal_to:
            st = os.stat(list_equal_to)
            if self.deep_check:
                self.reference = (st.st_size, md5sum(list_equal_to))
            else:
                self.reference = (st.st_size, int(st.st_mtime))

    def check(self, input_path):
        """
        Check file ``input_path`` for either uniqueness or equality
        (depending on ``list_equal_to`` from constructor).

        Args:
            input_path (str):   full path to file

        Returns:
            bool:               ``True`` if file is unique and ``list_equal_to``
                                is empty.
                                Or ``True`` if file is equal to file in
                                ``list_equal_to``
        """
        # follow symlinks ?
        path = input_path
        if self.follow_sym and os.path.islink(input_path):
            path = os.readlink(input_path)

        if self.list_equal_to:
            return self.checkEqual(path)
        else:
            return self.checkUnique(path)

    def checkUnique(self, path):
        """
        Check file ``path`` for uniqueness and store a unique key for ``path``.

        Args:
            path (str): full path to file

        Returns:
            bool:       ``True`` if file is unique
        """
        # check
        if self.deep_check:
            dum = os.stat(path)
            size,inode  = dum.st_size, dum.st_ino
            # is it a hlink ?
            if (size, inode) in self._size_inode:
                logger.debug("[deep test]: skip, it's a duplicate (size, inode)", self)
                return False
            self._size_inode.add((size,inode))
            if size not in self._uniq_dict:
                # first item of that size
                unique_key = size
                logger.debug("[deep test]: store current size?", self)
            else:
                prev = self._uniq_dict[size]
                if prev:
                    # store md5sum instead of previously stored size
                    md5sum_prev = md5sum(prev)
                    self._uniq_dict[size] = None
                    self._uniq_dict[md5sum_prev] = prev
                    logger.debug("[deep test]: size duplicate, remove the size, store prev md5sum", self)
                unique_key = md5sum(path)
                logger.debug("[deep test]: store current md5sum?", self)
        else:
            # store a tuple of (size, modification time)
            obj  = os.stat(path)
            unique_key = (obj.st_size, int(obj.st_mtime))
        # store if not already present, then return True
        if unique_key not in self._uniq_dict:
            logger.debug(" >> ok, store!", self)
            self._uniq_dict[unique_key] = path
            return True
        logger.debug(" >> skip (it's a duplicate)", self)
        return False

    def checkEqual(self, path):
        """
        Check if ``path`` is equal to the file in ``list_equal_to`` from
        constructor.

        Args:
            path (str): full path to file

        Returns:
            bool:       ``True`` if file is equal
        """
        st = os.stat(path)
        if self.deep_check:
            if self.reference[0] == st.st_size:
                return self.reference[1] == md5sum(path)
            return False
        else:
            return self.reference == (st.st_size, int(st.st_mtime))
