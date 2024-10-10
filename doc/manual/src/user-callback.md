<!--
SPDX-FileCopyrightText: © 2015 Germar Reitze
SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2).
See file/folder LICENSE or
go to <https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# User callback

During the backup process, _Back In Time_ can call a `user-callback` script at
different steps. That script can be found in the directory
`$XDG_CONFIG_HOME/backintime`. By default `$XDG_CONFIG_HOME` is `~/.config`.

## Arguments and error codes
- The first argument is the profile id (1=Main Profile, ...).
- The second argument is the profile name.
- The third argument is the reason:

1. Backup process begins.
2. Backup process ends.
3. A new snapshot was taken. The extra arguments are snapshot ID and snapshot path.
4. There was an error. The fourth argument is the error code.

   Possible error codes are:

   1. The application is not configured.
   2. A "take snapshot" process is already running.
   3. Can't find snapshots folder (is it on a removable drive ?).
   4. A snapshot for "now" already exist.
   5. Error while taking a snapshot (introduced Aug. 17, 2023)
   6. New snapshot taken but with errors (introduced Aug. 17, 2023)

   The optional fifth argument just for errors is the error message.

5. On (graphical) App start.
6. On (graphical) App close.
7. Mount all necessary drives.
8. Unmount all drives.

## Examples
Example scripts can be found in the directory `/usr/share/doc/backintime` or in
the [projects repository](https://github.com/bit-team/backintime).

## Implementation

For implementation details see the source code in the file
[`pluginmanager.py`](https://github.com/bit-team/backintime/blob/dev/common/pluginmanager.py).

