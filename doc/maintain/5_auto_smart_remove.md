<!--
SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES folder or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# Auto- & Smart-Remove
## Table of contents
* [Introduction](#introduction)
* [What we know](#what-we-know)
* [What we don't](#what-we-dont-know)

# Introduction
The actual auto- and smart-remove behavior of BIT will be described in this
document. Don't take this as a regular user manual. The document will help to
decide how that feature can be revised. See
[Meta Issue #1945](https://github.com/bit-team/backintime/issues/1945) about
the background story.

![Aut-remove tab](https://translate.codeberg.org/media/screenshots/bit_manage_profiles_autoremove.gif)

# What we know
## Location in code
* `common/snapshots.py`
  * `Snapshots.freeSpace()` is the main entry for the overall logic.
  * `Snapshots.smartRemoveList()` is called by `freeSpace()` and is the entry
    for _Smart remove_ related rules.

## Weekly
GUI wording: _Keep one snapshot per week for the last `N` week(s)._

Current behavior of the algorithm:
* A "week" is defined based on the weekdays Monday to Sunday.
* The first week BIT is looking into is the current week even if it is not
  completed yet. E.g. today is Wednesday the 27th November, BIT will look
  for existing backups starting with Sunday the 24th ending and including the
  Saturday 30th November.
* If there is not backup in the current week found that week is "lost" and
  there will only be `N-1` backups in the resulting list of weekly backups.
* See
  * [#1094](https://github.com/bit-team/backintime/issues/1094)
  * [PR #1944](https://github.com/bit-team/backintime/pull/1944)
  * [PR #1819](https://github.com/bit-team/backintime/pull/1819)

# What we don't know
A lot!

<sub>December 2024</sub>
