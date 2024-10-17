<!--
SPDX-FileCopyrightText: © 2015 Germar Reitze
SPDX-FileCopyrightText: © 2024 Kosta Vukicevic (stcksmsh)
SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or
go to <https://spdx.org/licenses/GPL-2.0-or-later.html>.
-->
# User callback

## Introduction

During the backup process, `Back In Time` can call a user defined script at
different steps. This script is named `user-callback` and contained in the directory
`$XDG_CONFIG_HOME/backintime`. By default `$XDG_CONFIG_HOME` is
`~/.config`). It can also be configured via the GUI: _Manage profiles_ >
_Options_ > _Edit user-callback_ (see also
[Options tab in Manage profiles dialog](settings.md#options)).

## Script arguments

1. The profile id (1=Main Profile, ...).
2. Profile name.
3. Callback reason:

| Value | Reason                                                             |
| ----- | -------------------------------------------------------------------|
| **1** | A backup process is about to start.                                |
| **2** | A backup process has ended.                                        |
| **3** | A new snapshot was taken. The following two extra arguments are snapshot ID and snapshot path. |
| **4** | There was an error. See next table for [error codes](#errorcodes). |
| **5** | The (graphical) application has started.                           |
| **6** | The (graphical) application has closed.                            |
| **7** | Mounting a filesystem for the profile may be necessary.            |
| **8** | Unmounting a filesystem for the profile may be necessary.          |

<a id="errorcodes"></a>
Possible **error codes** (see _Callback reason_ **4**) are:

| Code  | Error                                                              |
| ------| -------------------------------------------------------------------|
| **1** | Configuration is either missing or invalid.                        |
| **2** | A backup process is already running.[^1]                           |
| **3** | Can't find snapshots folder.[^2]                                   |
| **4** | A snapshot for "now" already exists. The fifth argument is the snapshot ID. |
| **5** | Error while taking a snapshot.[^3] The fifth argument contains more error information. |
| **6** | New snapshot taken but with errors.[^3] The fifth argument is the snapshot ID. |

## Return value

The script should return `0` if the backup should continue, any value other
than `0` will cancel the backup.

## Implementation

The `UserCallbackPlugin` is a class defined in
[`common/plugins/usercallbackplugin.py`](https://github.com/bit-team/backintime/blob/dev/common/plugins/usercallback.plugin.py).
It is a child class of `Plugin` which you can be found in
[`common/pluginmanager.py`](https://github.com/bit-team/backintime/blob/dev/common/pluginmanager.py).

## Examples

Several example scripts can be found in the directory
`/usr/share/doc/backintime` or in the
[projects repository](https://github.com/bit-team/backintime).

The following is a minimal script to log all calls to user-callback to a file
in `$HOME/.local/state/backintime_callback_log`.

```sh
#!/bin/bash
# SPDX-FileCopyrightText: © 2024 Kosta Vukicevic
# SPDX-FileCopyrightText: © 2024 @daveTheOldCoder
# SPDX-License-Identifier: CC0-1.0

LOG_FILE='/tmp/backintime_callback.log'

# Get current time
current_time=$(date +"%Y-%m-%d %H:%M:%S")

# Check if file exists, if not create it
touch $LOG_FILE

# Append current time to the file
echo -n "{$current_time}: " >> "$LOG_FILE"

# Iterate through all arguments
for arg in "$@"
do
    # Append argument to the file
    echo -n "$arg," >> "$LOG_FILE"
done

# Append newline character at the end
echo >> "$LOG_FILE"
```

[^1]: Ensure that manual and automatic backups do not run at the same time.
    
[^2]: For example, if the snapshots folder is on a removable drive, which is
    either not mounted, or is mounted at a different location.
    
[^3]: Supported added in _Back In Time_ version 1.4.0.
