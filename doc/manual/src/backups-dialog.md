Backups dialog
<!--
SPDX-FileCopyrightText: © 2016 Germar Reitze

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
![Backups Dialog](_images/light/backupsdialog.png#only-light)
![Backups Dialog](_images/dark/backupsdialog.png#only-dark)

List only different Backups

If checked only Backups with different file versions will be shown below.

List only equal Backups to

If checked only Backups with file versions equal to the Backups on the right
will be shown below.

Deep check

Calculate checksums to decide if file versions are equal or different with
`List only different Backups` or `List only equal Backups to`. This takes a
lot more time but is more accurate, too.

Restore

Restore the file/folder from the selected backup. Will be grayed out if `Now`
or multiple Backups are selected.

Delete

Delete the file/folder from one or multiple selected backups. Will be grayed
out if `Now` is selected.

Select All

Select all backups except `Now`.

Backups

Lists all backups which contain the file/folder. Can be filtered with `List
only different backups` or `List only equal backups to`.

Diff

Open a Side-by-Side view of the file/folder in the backup above and the
backup in the right hand selection.

Diff Options

Change the Program which is used for the Side-by-Side view with `Diff`. You can
use `%1` and `%2` for the paths of both backups.

Go To

Return to the Main Window and show the file in the above selected backup.
