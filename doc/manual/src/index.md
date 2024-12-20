<!--
SPDX-FileCopyrightText: © 2016 Germar Reitze

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2).
See file/folder LICENSE or
go to <https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# Introduction
![Back In Time main window](_images/light/main_window.png#only-light)
![Back In Time main window](_images/dark/main_window.png#only-dark)

*Back In Time* is a backup solution for GNU/Linux desktops. It is based on
`rsync` and uses hard links to reduce space used for unchanged files. It comes
with a graphical user interface (GUI) and a command line interface (CLI).

Backups are stored in plain text. They can be browsed with a normal
file-browser or in terminal which makes it possible to restore files even
without _Back In Time_. Files ownership, group and permissions are stored in a
separate compressed plain text file (`fileinfo.bz2`). If the backup drive does
not support permissions _Back In Time_ will restore permissions from
`fileinfo.bz2`. So if you restore files without _Back In Time_, permissions
could get lost.
