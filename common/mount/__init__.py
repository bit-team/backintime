# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
from pathlib import Path
from ._backends import Backend, LocalBackend, SSHBackend
from ._encryptors import Encryptor, NoEncryption, GoCryptFS


class MountManager:

    def __init__(self, backend, encryptor, cfg):
        self.backend = backend
        self.encryptor = encryptor
        self.cfg = cfg
        self._hash_id = None

    def mount(self):
        self._hash_id = self.backend.mount()

        if self.encryptor.TYPE != Encryptor.Type.NONE:
            self._hash_id = self.encryptor.mount(self.backend)

        return self._hash_id

    def umount(self):
        if self.encryptor.TYPE != Encryptor.Type.NONE:
            self._hash_id = self.encryptor.umount(self.backend)
        self.backend.umount()


class MountFactory:

    BACKENDS = {
        Backend.Type.LOCAL: LocalBackend,
        Backend.Type.SSH: SSHBackend,
    }

    ENCRYPT = {
        Encryptor.Type.NONE: NoEncryption,
        Encryptor.Type.GOCRYPTFS: GoCryptFS,
    }

    @classmethod
    def create(cls, cfg):
        # backend = cls.BACKENDS[cfg.backend](cfg)
        # encryptor = cls.ENCRYPT[cfg.encryption](cfg)

        if cfg.snapshotsMode() == 'local':
            return MountManager(
                cls.BACKENDS[Backend.Type.LOCAL](cfg),
                cls.ENCRYPT[Encryptor.Type.NONE](cfg),
                cfg
            )

        raise NotImplementedError(cfg.snapshotsMode())
