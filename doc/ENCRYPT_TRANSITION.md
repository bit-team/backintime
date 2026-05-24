<!--
SPDX-FileCopyrightText: © 2024 Back In Time Team

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->

# Transition of the encryption feature in _Back In Time_
<sub>Last update: June 2026</sub>

This document outlines the status of the encryption feature in _Back In Time_.
Starting with version `2.0.0` [EncFS] was **removed** and replaced with
[gocryptfs]. See [meta issue #1734](https://github.com/bit-team/backintime/issues/1734)
for technical details.

 * [Rational](#rational)
 * [Planned steps of the transition process](#planned-steps-of-the-transition-process)
 * [How to migrate an EncFS backup profile to an gocryptfs backup profile?](#how-to-migrate-an-encfs-backup-profile-to-an-gocryptfs-backup-profile)
 * [About EncFS security issues](#about-encfs-security-issues)
 * [Further readings and resources](#further-readings-and-resources)

## Rational
Removing [EncFS] was necessary because it has [known security
issues](#about-encfs-security-issues) and the upstream project is not active
anymore. To keep _Back In Time_ secure and maintenable there was no alternative
to remove it.

## The transition process
The original plan was designed for a longer transition period, beginning in
2024 with prominent user warnings and ending around 2027 upstream or around
2029 with the release of Debian 14.

However, the timeline changed and the upstream release introducing these
changes happend earlier with version 2.0.0 (released late 2026 or early 2027).
This version will also likely become part of Debian 14 around 2027.

The main reason is that integrating gocryptfs as a replacement for EncFS
turned out to be extremely difficulut due to Back In Time’s historically
grown and hard-to-maintain codebase. As a result, the already planned
restructuring and refactoring of the mount subsystem and related components
had to be brought forward. Removing EncFS support became necessary as part of
that work.

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
- First concrete discussion about deprecating EncFS was in
  [#1549](https://github.com/bit-team/backintime/issues/1549). But the topic
  started much further
  (e.g. [#1248](https://github.com/bit-team/backintime/issues/1248)).
- Our [mailing list](https://mail.python.org/mailman3/lists/bit-dev.python.org).
- [EncFS]
- [gocryptfs]

[EncFS]: https://github.com/vgough/encfs
[gocryptfs]: https://github.com/rfjakob/gocryptfs
