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

    @property
    def fingerprint(self) -> str:
        return hash((self.backend.fingerprint, self.encryptor.fingerprint))

    def mount(self):
        self.backend.mount()
        self.encryptor.mount(self.backend)

    def umount(self):
        self.encryptor.umount(self.backend)
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
