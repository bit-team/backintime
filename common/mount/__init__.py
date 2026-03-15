# SPDX-FileCopyrightText: © 2026 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
from pathlib import Path
from _backens import Backend, LocalBackend, SSHBackend
from _encryptors import Encryptor, NoEncryption, GoCryptFS


class MountManager:

    def __init__(self, backend, encryptor, cfg):
        self.backend = backend
        self.encryptor = encryptor
        self.cfg = cfg

    def mount(self):
        hash_id = self.cfg.hash_id()

        base = Path(self.cfg.mountpointBase())

        mount_base = base / hash_id
        mountpoint = mount_base / "mountpoint"

        mountpoint.mkdir(parents=True, exist_ok=True)

        self.backend.currentMountpoint = mountpoint

        path = self.backend.mount()

        if self.encryptor.TYPE != Encryptor.Type.NONE:
            path = self.encryptor.mount(path)

        return path


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

        backend = cls.BACKENDS[cfg.backend](cfg)
        encryptor = cls.ENCRYPT[cfg.encryption](cfg)

        return MountManager(backend, encryptor)
