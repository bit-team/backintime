<!--
SPDX-FileCopyrightText: © 2024 Back In Time Team

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->

# Transition of the encryption feature in _Back In Time_
<sub>Last update: January 2026</sub>

This document outlines the current status of the encryption feature in _Back In
Time_. Support for encrypted backup profiles is undergoing significant
changes.

 * [Short summary](#short-summary)
 * [Rational](#rational)
 * [Alternatives to EncFS](#alternatives-to-encfs)
 * [Planned steps of the transition process](#planned-steps-of-the-transition-process)
 * [How to migrate an EncFS backup profile to an gocryptfs backup profile?](#how-to-migrate-an-encfs-backup-profile-to-an-gocryptfs-backup-profile)
 * [About EncFS security issues](#about-encfs-security-issues)
 * [Further readings and resources](#further-readings-and-resources)

## Short summary
- To realize encrypted backups in _Back In Time_, EncFS was/is used.
- **Dropping support** for EncFS backup profiles started with _Back In Time_
  version 1.6.0 is performed in several stages, with sufficient warnings and
  lead time.
- Final **removal** will happen **around the year 2029** at the code level.
  This will happen in slow and small steps with sufficient advance warnings and
  lead time.
- EncFS has known security issues, is no longer maintained and therefore does
  not receive updates.
- The plan is to replace [EncFS] with [gocryptfs].
  Implementing gocryptfs support does not align with the EncFS removal time
  schedule, due to limited resources in the project team. See
  [meta issue #1734](https://github.com/bit-team/backintime/issues/1734) about
  the current progress.

## Rational

Removing [EncFS] is necessary because it has known security issues, the upstream
project is not active anymore and its maintainer himself recommends to replace
EncFS. To keep _Back In Time_ secure and maintenable there is no alternative to
remove it.

The necessity to remove EncFS exists regardless of whether an alternative for
this library is implemented or not.

## Alternatives to EncFS

The [EncFS] maintainer himself [recommends to
switch](https://github.com/vgough/encfs?tab=readme-ov-file#status) to
[gocryptfs]. So we are going this path. See
[#1734](https://github.com/bit-team/backintime/issues/1734) for details.

## Planned steps of the transition process

The transition is a process *not fixed* in all details and planned to take
until the *year 2029 or 2030*. The project will try to adapt to users needs and
other extern issues. Therefore the plan is not written in stone.
The transition is scheduled around the release cycles of
[Debian GNU/Linux](https://www.debian.org/). It has very long release cycles
and is the base for most of the distributions out there.
This is a short overview of the plan. See
[#1734](https://github.com/bit-team/backintime/issues/1734) for a more accurate
and up-to-date plan.

1. Year 2024: Clear and strong warning about the planned removing of EncFS in
   version 1.5.*.
2. Year 2025 after Debian 13 released: Creation of new EncFS profiles is
   disabled ([#2356](https://github.com/bit-team/backintime/issues/2315))
   starting with _Back In Time_ version 1.6.0. This become relevant for "Debian
   stable" users when Debian 14 will be released (round about year 2027/28).
   - Version 1.6.0 will have support for _local_ backup profiles using
     _gocryptfs_.
   - There is a high chance that _gocrypt_ support for _SSH_ profiles can be
     implemented in this 1.6.*.
3. Year 2027/2028 after Debian 14 released: Final removal of EncFS in upstream
   _Back In Time_. This will affect rolling release GNU/Linux distributions
   (e.g. Arch) and upcoming Ubuntu releases.
4. Year 2029/30 with Debian 15 release: Transformation then has reached Debian
   stable.


## How to migrate an EncFS backup profile to an gocryptfs backup profile?

...will follow...

See [this discussion on the mailing list](https://mail.python.org/archives/list/bit-dev@python.org/message/ZYA6YRSCBIVLQTGR2VMNOQQIBA522AWI/).

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
- First discussion about deprecating EncFS was in
  [#1549](https://github.com/bit-team/backintime/issues/1549).
- Our [mailing list](https://mail.python.org/mailman3/lists/bit-dev.python.org).
- [EncFS]
- [gocryptfs]

[EncFS]: https://github.com/vgough/encfs
[gocryptfs]: https://github.com/rfjakob/gocryptfs
