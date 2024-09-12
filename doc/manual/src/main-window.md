<!--
SPDX-FileCopyrightText: © 2016 Germar Reitze

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2).
See file/folder LICENSE or
go to <https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# Main Window

![Back In Time main window](_images/light/main_window_sections.png#only-light)
![Back In Time main window](_images/dark/main_window_sections.png#only-dark)


## Main Toolbar

![take_snapshot](_images/document-save_btn.svg) Take Snapshot

Take a new Snapshot in background. The main window can be closed during taking the snapshot. Normal behavior is to only compare files size and modification time. Alternatively, you can take a new Snapshot with `checksums` option enabled. This will calculate checksums for every file to decide if the file has changed. Taking a snapshot with checksums option takes a lot more time but it will make sure, the destination files won't be corrupt.

![refresh_snapshot](_images/view-refresh_btn.svg) Refresh Snapshots List

Refresh the Snapshots in [Timeline](#timeline).

![snapshot_name](_images/gtk-edit_btn.svg) Snapshot Name

Add a name for a Snapshot so you can easily identify it later. If `Don't remove
named snapshots` in **Settings \--\> Auto Remove** is enabled this will also
prevent the Snapshot from being removed. If this button is grayed out you need to select a snapshot in[Timeline](#timeline).

![remove_snapshot](_images/edit-delete_btn.svg) Remove Snapshot

Remove one or more Snapshots from Timeline. `Now` can not be removed as this is
no Snapshot but the live view of the local file-system. If this button is grayed out you need to select a snapshot in[Timeline](#timeline).

![view_log](_images/text-plain_btn.svg) View Snapshot Log

View the log of the selected Snapshot. If this button is grayed out you need to select a snapshot in[Timeline](#timeline).

![view_log](_images/document-new_btn.svg) View Last Log

View the log from the last snapshot attempt.

![settings](_images/gtk-preferences_btn.svg) Settings

Open [*Settings*](settings.md).

![shutdown](_images/system-shutdown_btn.svg) Shutdown System after Snapshot has finished

Shutdown the computer and poweroff after a snapshot has finished. The main window must stay open for this. If shutdown is not supported on the system this button will be grayed out.

![exit](_images/window-close_btn.svg) Exit

Close the main window. Running Snapshots will remain in background.

![help](_images/help-contents_btn.svg) Help

Menu with links to this help, FAQ, report bugs, ...

## Files Toolbar

![up](_images/go-up_btn.svg) Up

Go to the parent folder.

![show_hidden](_images/show-hidden_btn.svg) Show hidden files

Toggle hidden files (starting with a dot) to be shown in files view.

![restore](_images/edit-undo_btn.svg) Restore

Restore selected files or folders. This button has a sub-menu (hold down the
button). Default action is `Restore`. If this button is grayed out you need to select a snapshot in[Timeline](#timeline).

![restore](_images/edit-undo_btn.svg) Restore

Restore the selected files or folders to the original destination.

![restore_to](_images/document-revert_btn.svg) Restore to...

Restore the selected files or folders to a new destination.

![restore](_images/edit-undo_btn.svg) Restore */path*

Restore the currently shown folder and all its content to the original destination.

![restore_to](_images/document-revert_btn.svg) Restore *path* to...

Restore the currently shown folder and all its content to a new destination.

![snapshots](_images/file-manager_btn.svg) Snapshots

Open [Snapshots dialog](snapshots-dialog.md).

## Timeline

The Timeline lists all Snapshots which where already taken. You can browse them to see its contents in right hand [Files View](#files-view). The first item `Now` is not a Snapshot. It is a live view on the local file-system. It shows exact the same as your normal file browser. Multi selection is possible to remove multiple Snapshots altogether.

## Files View

Depending on selection in left hand [Timeline](#timeline) this will either show the original files or the files in the selected snapshot. You can jump directly to your home or include folders in `Shortcuts`.

## Statusbar

Show current status. While a snapshot is running this will show a progress-bar combined with current speed, already transferred data and the last message from `rsync`.
