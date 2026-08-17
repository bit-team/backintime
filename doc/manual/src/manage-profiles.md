# Manage profiles
<!--
SPDX-FileCopyrightText: © 2016 Germar Reitze

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
## General

You can choose which mode *Back in Time* should use to store backups.

Available modes:

- [Local](#local)
- [Local Encrypted](#local-encrypted)
- [SSH](#ssh)
- [SSH Encrypted](#ssh-encrypted)

### Local

Local backups can be stored on internal or external hard-drives or on mounted
shares. The destination file-system must support hard-links. Also the protocol
used to mount the remote share must support hard-links and symlinks. By default
Samba (SMB/CIFS) servers do not support symlinks (can be activated with `follow
symlinks = yes` and `wide links = yes` in `/etc/samba/smb.conf`). sshfs mounted
shares do not support hard-links.

![Settings - General](_images/light/settings_general.png#only-light)
![Settings - General](_images/dark/settings_general.png#only-dark)

Choose the destination path for backups with the
_directory_ button (to show hidden files use
CTRL + H or context menu with right mouse button). Back in Time will create
sub-directories `backintime/<HOST>/<USER>/<PROFILE>/` inside that directory.
Backups will be placed inside the `<PROFILE>/` directory.

### Local Encrypted

[Local Encrypted](#local-encrypted) works like [Local](#local) but the backups
will be stored encrypted with `gocryptfs`. The encrypted directory will be
created automatically inside the selected folder.

![Manage profiles - General](_images/light/settings_general_local_encrypted.png#only-light)
![Manage profiles - General](_images/dark/settings_general_local_encrypted.png#only-dark)

Enter the password for `gocryptfs` in `Encryption`. The password can be stored
in users keyring. The keyring is unlocked with the users password during
login. When running a scheduled backup-job while the user is not logged in the
keyring is not available. For this case, the password can be cached in memory
by Back in Time.

### SSH

This mode will store backups on a remote host which is available through
`SSH`. It will run `rsync` directly on the remote host which makes it a lot
faster than syncing to a local mounted share.

In order to use this mode the remote host need to be in your `known_hosts`
file. Keep in mind that hostnames treated case-sensitive in that file. You need
to have a public/private SSH key pair installed on the remote host. Starting
with Back in Time version 1.2.0 this will be done automatically. For versions
lower than 1.2.0 you need to do this manually:

- If you did not login into the remote host before you need to run `ssh
  USER@HOST` in Terminal. You will be asked to confirm the fingerprint of the
  remote host-key with `yes`. In order to compare the host-key you need to
  login to the remote host locally and run `ssh-keygen -l -f
  /etc/ssh/ssh_host_ecdsa_key.pub`. The fingerprint from this output must match
  the fingerprint you got asked above. You can exit immediately after this.
- Generate a new public/private SSH key with `ssh-keygen`. Press Enter to
  accept the default path and enter a password for the new key (this has
  nothing to do with your user-password on the remote host).
- Run `ssh-copy-id -i ~/.ssh/id_rsa.pub USER@HOST` to install the newly created
  key on the remote host. For the last time you need to enter the login
  password for the remote user. If successful you should now be able to log in
  without being asked for your login password.

![Settings - General](_images/light/settings_general_ssh.png#only-light)
![Settings - General](_images/dark/settings_general_ssh.png#only-dark)

Enter the name or IP-address of the remote host in `Host` and the port of the
remote SSH-server in `Port` (default `22`). `User` need to be the remote
user. `Path` can be empty to place the backups directory directly into remote
users home folder. Relative paths without leading slash (`foo/bar/`) will be
sub-directories of users home. Paths with leading slash (`/mnt/foo/bar/`) will be
absolute.

In `Cipher` you can choose the cipher (algorithm used to encrypt) for SSH
transfer. Depending on the involved systems it could be faster to select a
different cipher than default. Some of them might not work because they are
known to be insecure.

In `Private Key` you need to select your private SSH key. If this does not yet
exist, you can create a new public/private SSH key without password by clicking
on the _add_ button.

Enter the private key password in `SSH private key` (this is the password you
chose above during creating the public/private key pair, not the login password
for the remote user). The password can be stored in users keyring. The keyring
is unlocked with the users password during login. When running a scheduled
backup-job while the user is not logged in, the keyring is not available. For
this case, the password can be cached in memory by Back in Time.

### SSH Encrypted

SSH Encrypted](#ssh-encrypted) will work like [SSH](#ssh) but the backups
will be stored encrypted using `gocryptfs`. Back in Time will mount an
encrypted view of the file-system and sync it with `rsync` to
the remote host.

![Settings - General](_images/light/settings_general_ssh_encrypted.png#only-light)
![Settings - General](_images/dark/settings_general_ssh_encrypted.png#only-dark)

Additional to those settings from [SSH](#ssh) you need to provide a password
for encryption.

### Advanced

`Host`, `User` and `Profile` will be filled automatically (must not be
empty). They are used for the backup path
`backintime/<HOST>/<USER>/<PROFILE>/`. The full backup path will be shown
below. You can change them to match paths from other machines.

### Schedule

Different schedule types are available for different backup workflows
depending on how backups should be triggered.

Most schedules run backups at **fixed times**. If the computer is turned off at
the scheduled time, the backup is skipped and will not be started later. 
Other schedules can **catch up** on missed backups. If the computer was turned
off when a backup became due, the backup will be started the next time _Back
In Time_ is able to check the schedule. 
Additionally **event-based** schedules start backups in response to
specific events, such as system startup or connecting a backup drive via USB.

**Fixed-time schedule modes**:

- **Every Day**: start a new backup on a configurable time on every day.
- **Every Week**: start a new backup on a configurable week-day/time every week.
- **Every Month**: start a new backup on a configurable day/time every month.
- **Every Year**: start a new backup on first day of first month of each year
  at a configurable time.
- **Every X minutes**: start a new backup every 5, 10 or 30 minutes. This
  will add a line `*/<X> * * * * <COMMAND>` in `crontab`.
- **Every hour**: start a new backup on every full hour. This will add a line
  `0 * * * * <COMMAND>` in `crontab`.
- **Every X hours**: start a new backup every 2, 4, 6 or 12 hours at the full
  hour (e.g. at 0:00, 6:00, 12:00 and 18:00 with schedule "Every 6 hours"). This
  will add a line `0 */<X> * * * <COMMAND>` in `crontab`.
- **Custom Hours**: define custom pattern for `crontab`. This can be either a
  comma separated list of hours (e.g `0,10,13,15,17,20,23`) or `*/<X>` (e.g.
  `*/3`) for periodic schedules. This will add a line
  `0 0,10,13,15,17,20,23 * * * <COMMAND>` in `crontab`.

**Catch-up schedule mode**:

- **Repeatedly**: this schedule triggers backups when a configured number of
  calendar units (hours, days, weeks, or months) has passed since the last
  successful backup.
  A backup becomes due once a new calendar unit has been reached. For
  example, "1 hour" means the backup runs once the next clock hour begins,
  not after a fixed 60-minute duration.
  _Back In Time checks_ the schedule periodically via a crontab entry
  (typically every 15 minutes, or every hour for longer intervals). If no
  backup is due, it exits immediately.
  If the system was powered off or _Back In Time_ was not running when a backup
  became due, the backup will be performed the next time the schedule is
  checked. If a backup fails, it will be retried on the next check.

**Event-based schedule modes**:

- **At every boot/reboot**: start a new backup immediately after
  startup. This will add a `@reboot <COMMAND>` line in `crontab`. Wake up from
  suspend/hibernate will not trigger this schedule.
- **When drive gets connected (udev)**: this schedule will start a new backup
  as soon as the USB/eSATA/Firewire drive gets connected. You can configure a
  delay (hours, days or weeks) so it won't start on
  every new connection. This will add a new udev rule in
  `/etc/udev/rules.d/99-backintime-<USER>.rules` using the partitions UUID.
  Make sure auto-mount is enabled in your system.

**Technical details**:

Most of the modes will use `crontab` to set up new schedules. You can use
`crontab -l` to view them or `crontab -e` to edit them manually.

## Include

![Settings - Include](_images/light/settings_include.png#only-light)
![Settings - Include](_images/dark/settings_include.png#only-dark)

## Exclude

![Settings - Exclude](_images/light/settings_exclude.png#only-light)
![Settings - Exclude](_images/dark/settings_exclude.png#only-dark)

## Remove & Retention
Also known as _Auto-remove_ In previous versions of _Back In Time_.

![Settings - Auto Remove](_images/light/settings_autoremove.png#only-light)
![Settings - Auto Remove](_images/dark/settings_autoremove.png#only-dark)

## Options

![Settings - Options](_images/light/settings_options.png#only-light)
![Settings - Options](_images/dark/settings_options.png#only-dark)

## Expert Options

![Settings - Expert Options](_images/light/settings_expert_options.png#only-light)
![Settings - Expert Options](_images/dark/settings_expert_options.png#only-dark)

## User-callback

For more information on user callback see [this](user-callback.md).

