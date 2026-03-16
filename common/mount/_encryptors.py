# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
from enum import Enum, auto


class Encryptor:

    class Type(Enum):
        NONE = auto()
        GOCRYPTFS = auto()

    TYPE = None

    def __init__(self, cfg):
        self.cfg = cfg


class NoEncryption(Encryptor):
    TYPE = Encryptor.Type.NONE

    def mount(*args, **kwargs):
        pass

    def umount(*args, **kwargs):
        pass


class GoCryptFS(Encryptor):
    TYPE = Encryptor.Type.GOCRYPTFS
