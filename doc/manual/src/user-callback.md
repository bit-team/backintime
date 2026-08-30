# User callback script
<!--
SPDX-FileCopyrightText: © 2015 Germar Reitze
SPDX-FileCopyrightText: © 2024 Kosta Vukicevic (stcksmsh)
SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
## Introduction

During the backup process, _Back In Time_ can call a user defined script can be
called in response to various events. This script is named `user-callback`.

By default, the path is `$XDG_CONFIG_HOME/backintime/user-callback`. It always
resides in the same location as the config file itself. Therefore, if the
`--config` option is used to define a config file in another location, _Back
In Time_ will search in that location for the user-callback script.

The file needs to be executable. The filename cannot be modified.
The content of the file can be edited via the GUI: _Manage profiles_ >
_Options_ > _Edit user-callback_ (see also
[Options tab in Manage profiles dialog](manage-profiles.md#options)).

## Arguments and return value

The script can take **three arguments**. In case of error events, there will be a
fourth argument with an error code and sometimes a fifth argument with
additional information.

The **return value** of the script should be `0` if the backup should
continue. Return values other than `0` will stop the backup.

1. The profile id (1=Main Profile, ...).
2. Profile name.
3. Callback reason:

| Value | Reason                                                             |
| ----- | -------------------------------------------------------------------|
| **1** | A backup process is about to start.                                |
| **2** | A backup process has ended.                                        |
| **3** | A new backup was created. The following two extra arguments are backup ID and backup path. |
| **4** | There was an error. See next table for [error codes](#errorcodes). |
| **5** | The (graphical) application has started.                           |
| **6** | The (graphical) application has closed.                            |
| **7** | Mounting a filesystem for the profile may be necessary.            |
| **8** | Unmounting a filesystem for the profile may be necessary.          |

<a id="errorcodes"></a>
Possible **error codes** (see _Callback reason_ **4**) as fourth argument are:

| Code  | Error                                                              |
| ------| -------------------------------------------------------------------|
| **1** | Configuration is either missing or invalid.                        |
| **2** | A backup process is already running.[^1]                           |
| **3** | Can't find backups directory.[^2]                                   |
| **4** | A backup for "now" already exists. The fifth argument is the backup ID. |
| **5** | Error while creating a backup.[^3] The fifth argument contains more error information. |
| **6** | New backup created but with errors.[^3] The fifth argument is the backup ID. |

## Implementation

The `UserCallbackPlugin` is a class defined in
[`common/plugins/usercallbackplugin.py`](https://github.com/bit-team/backintime/blob/dev/common/plugins/usercallback.plugin.py).
It is a child class of `Plugin` which you can be found in
[`common/pluginmanager.py`](https://github.com/bit-team/backintime/blob/dev/common/pluginmanager.py).

## Examples

Several example scripts can be found in the directory
`/usr/share/doc/backintime` or in the
[projects repository](https://github.com/bit-team/backintime/tree/dev/doc/user-callback-examples).

[^1]: Ensure that manual and automatic backups do not run at the same time.
    
[^2]: For example, if the backups directory is on a removable drive, which is
    either not mounted, or is mounted at a different location.
    
[^3]: Supported added in _Back In Time_ version 1.4.0.
