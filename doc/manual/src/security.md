# Security
<!--
SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
## Directory permissions when creating backups
<!--
See this issues for background details and decision history:
- https://github.com/bit-team/backintime/issues/377
-->
!!! note inline end 
    This section is intended for *advanced users* or *system administrators*
    who want detailed information. **In typical setups, no action or changes
    are necessary.**

New backup directories created by **Back In Time** automatically receive
their permissions (through `rsync`) according to the current
[`umask`](https://wikipedia.org/wiki/Umask) of the system or the user running
the program. Depending on this `umask`, directories may be created with
permissions such as `0775` (read, write and execute access for owner and group;
read and execute access for others).

However, the permissions of the parent directory also apply. In most cases,
backups are stored inside a user’s home directory, which is not accessible to
others by default. This means that even if the backup directory itself appears
open, other users usually cannot enter it.

If stronger isolation is desired, a more restrictive **umask** can be set
before starting **Back In Time**, for example `0750` (read, write and execute
access for owner; read and execute access for group; no permissions for
others). Alternatively, permissions can be adjusted manually after creation, or
the parent directory can be secured accordingly.

Effective directory permissions therefore depend on the `umask` and on the
configuration of the parent directories.

