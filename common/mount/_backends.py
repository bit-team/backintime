# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
from enum import Enum, auto
import logger


class Backend:

    class Type(Enum):
        LOCAL = auto()
        SSH = auto()

    TYPE = None

    def __init__(self, cfg):

        self.cfg = cfg
        self.profile_id = cfg.profile_id

        self.hash_id = None
        self.currentMountpoint = None

    def mount(self):
        raise NotImplementedError

    def umount(self):
        raise NotImplementedError


class LocalBackend(Backend):

    TYPE = Backend.Type.LOCAL

    def __init__(self, cfg):

        super().__init__(cfg)

        self.mode = "local"
        self.mountproc = "local filesystem"
        self.symlink_subfolder = None

    def mount(self):

        logger.debug("Local backend mount start", self)

        if self.currentMountpoint is None:
            raise RuntimeError("Mountpoint not initialized")

        logger.debug(
            f"Local backend using mountpoint {self.currentMountpoint}",
            self
        )

        return self.currentMountpoint

    def umount(self):

        logger.debug("Local backend umount (noop)", self)

        return True


class SSHBackend(Backend):
    TYPE = Backend.Type.SSH
