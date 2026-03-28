<!--
SPDX-FileCopyrightText: © 2009 Back In Time Team <backintime-project@posteo.de>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
[![Mailing list bit-dev@python.org](doc/maintain/_images/badge_bit-dev.svg)](https://mail.python.org/mailman3/lists/bit-dev.python.org/)
[![Mastodon @backintime@fosstodon.org](doc/maintain/_images/badge_mastodon.svg)](https://fosstodon.org/@backintime)

[![Build Status](https://app.travis-ci.com/bit-team/backintime.svg?branch=dev)](https://app.travis-ci.com/bit-team/backintime)
[![User manual Status](https://readthedocs.org/projects/backintime/badge/?version=latest)](https://backintime.readthedocs.io)
[![Translation status](https://translate.codeberg.org/widget/backintime/common/svg-badge.svg)](https://translate.codeberg.org/engage/backintime)
[![REUSE status](https://api.reuse.software/badge/github.com/bit-team/backintime)](https://api.reuse.software/info/github.com/bit-team/backintime)

# Back In Time

_Back In Time_ is a comfortable and well-configurable graphical frontend for
incremental backups using [`rsync`](https://rsync.samba.org/), with a
command-line version also available. Modified files are transferred, while
unchanged files are linked to the new directory using rsync's hard link feature,
saving storage space. Restoring is straightforward via file manager, command
line or _Back In Time_ itself.

It is written in Python3 and available for all major GNU/Linux distributions
as command line tool `backintime` and GUI `backintime-qt`. Backups can be
scheduled and stored locally or remotely through SSH.

More background info in [CONTRIBUTING](CONTRIBUTING.md) and
[HISTORY](HISTORY.md).

## Maintenance status

The project is in active development since the [new team](#the-team) joined in
summer 2022. Development is done voluntarily in spare time so things need to be
prioritized. Stick with us, we all ♥️ _Back In Time_. 😁

Current focus is on fixing
[major issues](https://github.com/bit-team/backintime/issues?q=is%3Aissue+is%3Aopen+label%3AHigh)
instead of implementing new
[features](https://github.com/bit-team/backintime/labels/Feature).
Stabilize the code base and its test suite is also a matter. Read the
[strategy outline](CONTRIBUTING.md#strategy-outline) for details.
Please see [CONTRIBUTING](CONTRIBUTING.md) if you are interested in the
development and have a look on
[open issues](https://github.com/bit-team/backintime/issues) especially
those labeled as [good first issues](https://github.com/bit-team/backintime/labels/GOOD%20FIRST%20ISSUE)
and [help wanted](https://github.com/bit-team/backintime/issues?q=is%3Aissue+is%3Aopen+label%3AHELP-WANTED).

## The team
Since around 2024, [@buhtz](https://buhtz.codeberg.page/), part of the projects
third generation of maintainers, has been the sole maintainer. He handles all
core tasks, from code analysis and documentation to issue resolution and
feature implementation. The work is carried out voluntarily during spare
time. The project continues to benefit from an active and engaged community
that provides advice, expertise, and contributions, ensuring it thrives and
evolves.

The project was
[reactivated in 2022](https://github.com/bit-team/backintime/issues/1232))
and thanks in large part to @emtiu and @aryoda, who helped relaunch and
shape its direction. See [HISTORY](HISTORY.md) for more details.

# Index

- [Documentation](#documentation)
- [Contact & Social](#contact--social)
- [Installation](#installation)
- [Known Problems and Workarounds](#known-problems-and-workarounds)
- [Contributing and other ways to support the project](#contributing-and-other-ways-to-support-the-project)
- [Licenses](#licenses)

---

# Documentation

 * [FAQ - Frequently Asked Questions](FAQ.md)
 * [End user documentation](https://backintime.readthedocs.org/) (not totally up-to-date)
 * [Source code documentation for developers](https://backintime-dev.readthedocs.org)
   (**Disabled** and not up-2-tdate. Please open an issue if you need to use it.)

# Contact & Social

 * **Mailing list**:
   [bit-dev@python.org](https://mail.python.org/mailman3/lists/bit-dev.python.org/)
   can be used for **any topic**, question and idea related to _Back In
   Time_. Despite its name it is not restricted to development topics only.
 * **Fediverse** on **Mastodon**: [@backintime@fosstodon.org](https://fosstodon.org/@backintime)
 * **Bugs** & **Feature Requests**: [Issues section](https://github.com/bit-team/backintime/issues)
 * **Email**: [backintime-project@posteo.de](mailto:backintime-project@posteo.de)

# Installation

_Back In Time_ is included in
[many GNU/Linux distributions](https://repology.org/project/backintime/badges).
Use their repositories to install it. If you want to contribute or using the
latest development version of _Back In Time_ please see section
[Build & Install](CONTRIBUTING.md#build--install) in
[`CONTRIBUTING.md`](CONTRIBUTING.md). Also the dependencies are described there.

# Known Problems and Workarounds

In the latest stable release:
- [File permissions handling and therefore possible non-differential backups](#file-permissions-handling-and-therefore-possible-non-differential-backups)
- [`qt_probing.py` may hang with high CPU usage when running BiT as `root` via `cron`](#qt_probingpy-may-hang-with-high-cpu-usage-when-running-bit-as-root-via-cron)

More problems described in
[this FAQ section](FAQ.md#problems-errors--solutions).

## File permissions handling and therefore possible non-differential backups

- In version 1.2.0, the handling of file permissions changed.
- In versions <= 1.1.24 (until 2017) all file permissions were set to
  `-rw-r--r--` in the backup target.
- In versions >= 1.2.0 (since 2019) `rsync` is executed with `--perms` option
  which tells `rsync` to preserve the source file permission.

Therefore backups can be larger and slower, especially the first backup after
upgrading to a version >= 1.2.0.

If you don't like the new behavior, you can use _Expert Options_ ->
_Paste additional options to rsync_ to add `--no-perms --no-group --no-owner`
to it. Note that the exact file permissions can still be found in
`fileinfo.bz2` and are also considered when restoring files.

## `qt_probing.py` may hang with high CPU usage when running BiT as `root` via `cron`

See the related issue [#1592](https://github.com/bit-team/backintime/issues/1592).

The only reliable work-around is to delete (or move into another directory)
the file `/usr/share/backintime/common/qt_probing.py`:

`mv /usr/share/backintime/common/qt_probing.py /usr/share/backintime/`

Renaming does *not* work!

# Contributing and other ways to support the project
See [CONTRIBUTING](CONTRIBUTING.md) file for an overview about the projects
workflow and strategy.

# Licenses
Please read [`LICENSES.md`](LICENSES.md).

---
<sub>February 2026</sub>
