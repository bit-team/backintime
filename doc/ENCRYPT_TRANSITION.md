<!--
SPDX-FileCopyrightText: © 2024 Back In Time Team

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->

# Transition of the encryption feature in _Back In Time_
<sub>Last update: June 2026</sub>

This document outlines the status of the encryption feature.  Starting with
_Back In Time_ version [2.0.0], support for [EncFS] was dropped in favor of
[gocryptfs]. See [meta issue
#1734](https://github.com/bit-team/backintime/issues/1734) for technical
details.

 * [Rationale](#rationale)
 * [The transition process](#the-transition-process)
 * [FAQ - Frequently Asked Questions](#faq--frequently-asked-questions)
   * [How to migrate an EncFS backup profile to a gocryptfs backup profile?](#how-to-migrate-an-encfs-backup-profile-to-a-gocryptfs-backup-profile)
   * [How to access existing EncFS snapshots without Back In Time?](#how-to-access-existing-encfs-snapshots-without-back-in-time)
 * [About EncFS security issues](#about-encfs-security-issues)
 * [Further readings and resources](#further-readings-and-resources)

## Rationale
Removing [EncFS] was necessary because it has [security issues known since
2014](#about-encfs-security-issues). Additionally the the upstream project is
not active anymore. To keep _Back In Time_ secure and maintainable there was no
alternative to remove it.

## The transition process
Replacing EncFS in _Back In Time_ was [first
discussed](https://github.com/bit-team/backintime/issues/1248) in the
year 2023. The plan was designed for a longer transition period, beginning in
2024 with prominent user warnings and ending around 2027 upstream or around
2029 with the release of Debian 14.

However, the timeline changed and the upstream release introducing these
changes arrived earlier than expected with version [2.0.0]. This version will
also likely be included in [Debian GNU/Linux] 14 around 2027.

The main reason is that integrating gocryptfs as a replacement for EncFS turned
out to be extremely difficult due to _Back In Time_’s historically grown and
hard-to-maintain codebase. As a result, the already planned restructuring and
refactoring of the mount subsystem and related components had to be brought
forward. Removing EncFS support became necessary as part of that work. The
creation of new EncFS profiles [was
disabled](https://github.com/bit-team/backintime/issues/2315) in version
[1.6.1] early 2026. It must be noted, that at this time there was no full
gocryptfs support implemented.

## FAQ - Frequently Asked Questions
### How to migrate an EncFS backup profile to a gocryptfs backup profile?

Within _Back In Time_ itself it is not possible to migrate an EncFS profile to
a gocryptfs profile. Existing EncFS profiles also cannot be converted into
gocryptfs profiles.

A new gocryptfs encrypted profile need to be created.  See [this
issue](https://github.com/bit-team/backintime/issues/2495) and [this discussion
on the mailing
list](https://mail.python.org/archives/list/bit-dev@python.org/message/ZYA6YRSCBIVLQTGR2VMNOQQIBA522AWI/)
about technical details.

> [!NOTE]
> :wink: If you are successful, it would help a lot if you could contribute
> a tutorial like documentation to the project.

### How to access existing EncFS snapshots without Back In Time?

Even after upgrading to _Back In Time_ 2.0.0, your old EncFS-encrypted
snapshots still exist on disk. You can access them directly using the
`encfs` or `encfsctl` command-line tools — no Back In Time needed.

**Prerequisites:** Install the EncFS tools for your distribution:

```bash
# Debian / Ubuntu
sudo apt install encfs

# Fedora
sudo dnf install fuse-encfs

# Arch Linux
sudo pacman -S encfs

# macOS (Homebrew)
brew install encfs-mac
```

**Option 1 — Mount interactively (browse files):**
```bash
# Create a mount point
mkdir -p ~/encfs-mount

# Mount the encrypted directory (you'll be prompted for the password)
encfs /path/to/backintime/encrypted-backup ~/encfs-mount

# Now browse your files
ls ~/encfs-mount

# When done, unmount
fusermount -u ~/encfs-mount        # Linux
umount ~/encfs-mount               # macOS
```

**Option 2 — Export without mounting (batch extract):**
```bash
# Export all files from the encrypted directory to a plain directory
encfs --extpass="echo your-password" \
  /path/to/backintime/encrypted-backup \
  /path/to/export-directory \
  --reverse
```
> [!CAUTION]
> Putting the password on the command line leaves it in your shell history.
> Use `encfs` without `--extpass` (interactive prompt) unless you fully trust
> the environment.

**Option 3 — Inspect without password (metadata only):**
```bash
# List encrypted filenames and sizes without decrypting content
encfsctl info /path/to/backintime/encrypted-backup
```

**After extracting your data**, create a new gocryptfs-encrypted profile in
_Back In Time_ and take a fresh backup.

> [!TIP]
> The EncFS encrypted data is stored at the path you configured in your old
> Back In Time profile (typically under the snapshot directory with an
> `.encfs` suffix or a separate `encfs` folder). Look for a file named
> `.encfs6.xml` — that's the EncFS configuration file identifying the
> encrypted data.

## About EncFS security issues

   - EncFS Security Audit
       - https://defuse.ca/audits/encfs.htm (as updated blog post)
       - https://sourceforge.net/p/encfs/mailman/message/31849549/ (original mailing list entry)
   - [EncFS#314](https://github.com/vgough/encfs/issues/314) (a **not-fixed** meta issue with a list of several open issues related to the Security Audit)
   - [EncFS#659](https://github.com/vgough/encfs/issues/659)
   - [EncFS#9](https://github.com/vgough/encfs/issues/9)
   - [EncFS - Ubuntu Users Wiki (German)](https://wiki.ubuntuusers.de/Archiv/EncFS)

## Further readings and resources

- The meta issue [#1734](https://github.com/bit-team/backintime/issues/1734)
  about the transition, its current state and related steps and issues.
- First concrete discussion about deprecating EncFS was in
  [#1549](https://github.com/bit-team/backintime/issues/1549). But the topic
  started much further
  (e.g. [#1248](https://github.com/bit-team/backintime/issues/1248)).
- Our [mailing list](https://mail.python.org/mailman3/lists/bit-dev.python.org).
- Our [mailing list]
- [EncFS]
- [gocryptfs]

[EncFS]: https://github.com/vgough/encfs
[gocryptfs]: https://github.com/rfjakob/gocryptfs
[1.6.1]: https://github.com/bit-team/backintime/releases/tag/v1.6.1
[2.0.0]: https://github.com/bit-team/backintime/releases/tag/v2.0.0
[mailing list]: https://mail.python.org/mailman3/lists/bit-dev.python.org
[Debian GNU/Linux]: https://www.debian.org/
