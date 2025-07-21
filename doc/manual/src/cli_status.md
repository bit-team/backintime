# Command: `status`
<!--
SPDX-FileCopyrightText: © 2025 Christian BUHTZ <c.buhtz@posteo.jp>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
## Description
The command `status` summarize the latest run and latest backup state for each
profil or for a specific one.

## Usage examples
**All profiles**:

```sh linenums="0"
$ backintime status
```

```text linenums="0"
Main profile:
  Last Run    : 2025-05-26 21:00:09
  Last Backup : 
     Status   : Success
     Completed At: 2025-05-26 21:00:02
ARCHIV:
  Last Run    : 2025-05-11 11:02:58
  Last Backup : 
     Status   : Success
     Completed At: 2025-05-11 11:02:51
Nerys:
  Last Run    : Not available
Foobar:
  Last Run    : Connect the drive to get status
  Last Backup : for this profile (id=3)
```

**One specific profile**:

```sh linenums="0"
$ backintime status --profile ARCHIV
```

```text linenums="0"
ARCHIV:
  Last Run    : 2025-05-11 11:02:58
  Last Backup : 
     Status   : Success
     Completed At: 2025-05-11 11:02:51
```

**As machine readable JSON format**:
```sh linenums="0"
$ backintime status --profile ARCHIV --json
```

```text linenums="0"
{"ARCHIV": {"Last Run": "Connect the drive to get status", "Last Backup": "for this profile (id=5)"}}
```
