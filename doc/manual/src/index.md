# Introduction
<!--
SPDX-FileCopyrightText: © 2016 Germar Reitze

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
![Back In Time main window](_images/light/main_window.png#only-light)
![Back In Time main window](_images/dark/main_window.png#only-dark)

**Back In Time** is a backup solution for GNU/Linux desktops. It is based on
`rsync` and uses hard links to reduce space used for unchanged files. It comes
with a graphical user interface (GUI) and a command line interface (CLI).

**Back In Time** acts as a _user mode_ backup tool. This means that you can
backup/restore only folders you have write access to (actually you can backup
read-only folders, but you can't restore them).

Backups are stored in plain text. They can be browsed with a normal
file-browser or in terminal which makes it possible to restore files even
without **Back In Time**. Files ownership, group and permissions are stored in a
separate compressed plain text file (`fileinfo.bz2`). If the backup drive does
not support permissions **Back In Time** will restore permissions from
`fileinfo.bz2`. So if you restore files without **Back In Time**, permissions
could get lost.

## Modes

Several backup profile modes are supported. The simplest is the **Local**
profile, which creates backups from items on the local machine and stores them
on the same machine. **Local encrypted** profiles encrypt the backups using
EncFS. To store backups on a remote machine, the **SSH** profile can be
used. These backups can also be encrypted using the **SSH encrypted** profile.

### Local

Stores backups on local drives or volumes. The device has to be mounted before
creating a new backup.

### Local encrypted

Store encrypted backups on local drives or volumes. 
**Back In Time** use's `encfs` with standard configuration to encrypt all
data. Please [be aware of security implications](settings.md#local-encrypted).

### SSH

With Mode set to SSH you can store the backup on a remote host using the
[Secure Shell](https://en.wikipedia.org/wiki/Secure_Shell) protocol (SSH). The
remote path will be mount local using `sshfs` to provide file-access.  Rsync
and other processes called during backup process will run directly on the
remote host using `ssh`.

So called password-less login need to be configured on the remote machine.

### SSH encrypted

Store encrypted backups on remote hosts using SSH. **Back In Time** uses `encfs
--reverse` to mount the root filesystem `/`. Rsync will sync this encrypted
view of `/` to a remote host over SSH. All encoding will be done on the local
machine. So the password will never be exposed to the remote host. Please [be
aware of security implications](settings.md#local-encrypted).

Because all data is transferred encrypted, the log output shows encrypted
filenames, too. Use the _decode_ option, available via context menu, in the
[Log View](log.md) dialog window. This feature decrypts the paths
automatically.

In the [Main Windows Files View](main_window.md#files-view) all directories and
files shown decoded, so there is no need for explicit decoding.

!!! note

    _Exclude_ does not support wildcards (`foo*`, `[fF]oo`, `foo?`)
    because after
    encoding a file these wildcards can't match any more. Only separate asterisk
    that match a full file or folder will work (`foo/*`, `foo/**/bar`). All other
    excludes that have wildcards will be silently ignored.

## Passwords
If _Save Password to Keyring_ is activated **Back In Time** will save the
password using the keyring available (e.g. GnomeKeyring, KDE-KWallet, …). With
those the password are stored encrypted with the users login-password. So they
can only be accessed if the user is logged in.

A backup cronjob during the user isn't logged in can not collect the password
from keyring. Also if the homedir is encrypted the keyring is not accessible
from cronjobs (even if the user is logged in). For these cases the password can
be cached in RAM. If 'Cache Password for Cron' is activated Back In Time will
start a small daemon in user-space which will collect the password from keyring
and provide them for cronjobs. They will never be written to the harddrive but
a user with root permissions could access the daemon and read the password.

A backup cron job cannot retrieve the password from the keyring if the user is
not logged in. Additionally, if the home directory is encrypted, the keyring is
inaccessible to cron jobs—even when the user is logged in. In such cases, the
password can be cached in RAM. If _Cache Password for Cron_ is enabled, **Back
In Time** will start a user-space daemon (`backintime pw-cache`) that retrieves
the password from the keyring and makes it available to cron jobs. The password
is never written to disk; however, a user with root privileges could access the
daemon and read the password.
