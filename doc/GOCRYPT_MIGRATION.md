<!--
SPDX-FileCopyrightText: © 2024 Back In Time Team

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# Local Encrypted Backups in Back In Time 1.6.x and 2.0.0
<sub>Last update: October 2026</sub>

Since version `1.6.0` Back In Time_ uses [gocryptfs](https://github.com/rfjakob/gocryptfs) to implement local encrypted
backups.

In version `1.6.x`, _Back In Time_ uses a forward mount to access the
decrypted data. But the planned implementation for version `2.0.0` will change
how encrypted data is handled by the transfer layer. It is intended to
use a reverse mount and to separate mount management from data transfer.

Version `2.0.0` is still under development. The exact technical differences and
the migration procedure have therefore not yet been finalized.

> [!NOTE]
> Until version `2.0.0` is released, avoid creating new local encrypted backup
> profiles if possible.

# Are local encrypted backups in Back In Time 1.6.x buggy?

No bugs affecting local encrypted backups in Back In Time 1.6.x are
currently known. The warning concerns the planned changes in version 2.0.0,
not a known problem with the current implementation.

# How can I access my local encrypted backups without Back In Time?

The encrypted data can be accessed directly using `gocryptfs`. You need the
path to the encrypted directory used by your backup profile and the password
for that encrypted filesystem. For further information, see the [gocryptfs
documentation](https://github.com/rfjakob/gocryptfs).

# What is the technical difference between Back In Time 1.6.x and 2.0.0?

The implementation for version 2.0.0 is not yet complete, so the exact
technical differences have not been finalized.

The current implementation in version 1.6.x uses a forward mount. The planned
implementation for version 2.0.0 changes how encrypted data is handled by the
transfer layer and separates mount management from it. A reverse mount is
planned for the transfer layer.

The details may change during development.

# How will the migration work?

It has not yet been determined whether or how migration will be provided.
The implementation for version 2.0.0 is still under development.

A migration would need to account for the existing encrypted backup data.
The data may need to be copied to a new location or structure, potentially
requiring additional storage space. Whether migration will be available
through the GUI, a separate script, or manual instructions is not yet
known.

Back In Time will try to provide a migration path in version 2.0.0, but
this cannot currently be guaranteed.

# Can I create local encrypted backups with Back In Time 1.6.x?

Yes. Local encrypted backups can be created with Back In Time 1.6.x, and
no known bugs affecting this functionality are currently known.

However, existing backup data might no longer be accessible through Back
In Time 2.0.0 without migration. If possible, avoid creating new local
encrypted backup profiles until version 2.0.0 is released.
