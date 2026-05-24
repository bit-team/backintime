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
 * [About EncFS security issues](#about-encfs-security-issues)
 * [Further readings and resources](#further-readings-and-resources)

## Rationale
Removing [EncFS] was necessary because it has [known security
issues](#about-encfs-security-issues) (since 2014) and the upstream project is
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
[1.6.1] early 2026.  At this time there was no full gocryptfs support
implemented.

## FAQ - Frequently Asked Questions
### How to migrate an EncFS backup profile to an gocryptfs backup profile?

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
