# Main Window
<!--
SPDX-FileCopyrightText: © 2016 Germar Reitze

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
![Back In Time main window](_images/light/main_window_sections.png#only-light)
![Back In Time main window](_images/dark/main_window_sections.png#only-dark)

## Main Toolbar

**_Create a backup_**

Create a new backup in background. The main window can be closed during 
creation. Normal behavior is to only compare files size and modification
time. Alternatively, you can take a new backup with `checksums` option
enabled. This will calculate checksums for every file to decide if the file has
changed. Creating a backup with checksums option takes a lot more time but it
will make sure, the destination files won't be corrupt.

**_Refresh backup list_**

Refresh the Backups in [Timeline](#timeline).

**_Name backup_**

Add a name for a backup so you can easily identify it later. If `Don't remove
named backups` in **Manage profile \--\> Remote & Retention** is enabled this will also
prevent the backup from being removed.

**_Remove backup_**

Remove one or more backups from Timeline. `Now` can not be removed as this is
no backup but the live view of the local file-system. If this button is
grayed out you need to select a backup in [Timeline](#timeline).

**_View log of the selected backup_**

View the log of the selected backup.

**_Open last backup log_**

View the log from the last backup attempt.

**_Manage profiles_**

Open [*Manage profiles*](manage-profiles.md).

**_Shutdown_**

Shutdown the computer and poweroff after a backup has finished. The main
window must stay open for this. If shutdown is not supported on the system this
button will be grayed out.

## Files Toolbar

**_Up_**

Go to the parent directory.

**_Show hidden files_**

Toggle hidden files (starting with a dot) to be shown in files view.

**_Restore_**

Restore selected files or directories. This button has a sub-menu (hold down
the button). Default action is `Restore`.

Or, Restore the selected files or directories to the original destination.

Or, Restore the selected files or directories to a new destination.

Or, Restore the currently shown directory and all its content to the original
destination.

Or, Restore the currently shown directory and all its content to a new destination.

**_Compare backups_**

Open [Backups dialog](backups-dialog.md).

## Timeline

The Timeline lists all backups which where already created. You can browse them
to see its contents in right hand [Files View](#files-view). The first item
`Now` is not a backup. It is a live view on the local file-system. It shows
exact the same as your normal file browser. Multi selection is possible to
remove multiple backups altogether.

## Files View

Depending on selection in left hand [Timeline](#timeline) this will either show
the original files or the files in the selected backup. You can jump directly
to your home or include directories in `Shortcuts`.

## Statusbar

Show current status. While a backup is running this will show a progress-bar
combined with current speed, already transferred data and the last message from
`rsync`.
