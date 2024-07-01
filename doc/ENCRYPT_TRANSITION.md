# Transition of the encryption feature in _Back In Time_
<sub>July 2024</sub>

This document outlines the current status of the encryption feature in _Back In
Time_. Support for encrypted snapshot profiles is undergoing significant
changes.

 * [Short summary](#short-summary)
 * [Rational](#rational)
 * [Alternatives to EncFS](#alternatives-to-encfs)
 * [Planned steps of the transition process](#planned-steps-of-the-transition-process)
 * [About EncFS security issues](#about-encfs-security-issues)
 * [Further readings and resources](#further-readings-and-resources)

## Short summary
- To realize encrypted snapshots in _Back In Time_, [EncFS] is used.
- EncFS has known security issues and also is no longer maintained.
- EncFS library will be **removed** from _Back In Time_ **around the year 2029**.
  This will happen in slow and small steps with sufficient advance warnings and
  lead time.
- In the best case, EncFS will be replaced with an alternative library
  (expected to be [GoCryptFS]).
- The current maintenance team does not have the resources to implement an
  alternative for EncFS. So extern contributors are need to step in.
- If GoCryptFS or another alternative will be implemented, depending on project
  resources and contributor availability.

## Rational

Removing [EncFS] is necessary because it has known security issues, the
upstream project is not active anymore and its maintainer himself recommends to
replace EncFS. To keep _Back In Time_ secure and maintenable there is no
alternative to deprecat EncFS in _Back In Time_ and finally remove it.

The necessity to remove EncFS exists regardless of whether an alternative for
this library is implemented or not.

## Alternatives to EncFS

The [EncFS] maintainer himself [recommends to
switch](https://github.com/vgough/encfs?tab=readme-ov-file#status) to
[GoCryptFS]. It seems to work similar to EncFS. Therefore, according to the
[current state of research and discussion](https://github.com/bit-team/backintime/issues/1734),
GoCryptFS is the preferred choice for a solution.

It was also discussed if file system encryption (e.g. [LUKS]) could be an
option. In this case _Back In Time_ won't need an encryption feature anymore
because the file system tools do take care of it. It might be an option for
some of the affected users but [it was also
shown](https://github.com/bit-team/backintime/issues/1734#issuecomment-2151875246)
that file system encryption is not an option in all use cases. Therefore, LUKS
might not be the first choice solution, but is better then nothing in case the
project won't find a contributor for replacing EncFS with GoCryptFS or
something else.

The project also is open for other alternative solutions.

## Planned steps of the transition process

The transition is a process *not fixed* in all details and planned to take
until the *year 2029 or 2030*. The project will try to adapt to users needs and
other extern issues. Therefore the plan is not written in stone. The goal is to
have slow and transparent steps in a timeline of multiple years until round
about the year 2029 or 2030 when Debian 15 will be released. Current stable
Debian is version 12.

The transition is scheduled around the release cycles of Debian GNU Linux
because Debian has very long release cycles and is the base for most of the
distributions out there.

1. Year 2024: Clear and strong warning about the planned removing or replacement
   of EncFS ([#1735](https://github.com/bit-team/backintime/issues/1734)).
   Planned for the upcoming release 1.5.0 reaching Ubuntu 24.10 ("Oracular
   Oriole").
2. After Debian 13 released (year 2025 or 2026): Disable creation of new EncFS
   profiles. This become "relevant" for "Debian stable" users round about year
   2027/28 when Debian 14 is released.
3. After Debian 14 released (Year 2027 or 2028): Remove EncFS in upstream
   BIT. This will affect rolling release GNU Linux distributions (e.g. Arch)
   and upcoming Ubuntu releases.
4. Debian 15 in year 2029 or 2030: Our transformation then has reached Debian
   stable.

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
- [GoCryptFS]

[EncFS]: https://github.com/vgough/encfs
[GoCryptFS]: https://github.com/rfjakob/gocryptfs
[LUKS]: https://en.wikipedia.org/wiki/Linux_Unified_Key_Setup
