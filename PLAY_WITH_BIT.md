<!--
SPDX-FileCopyrightText: © 2026 Back In Time Team

SPDX-License-Identifier: CC0-1.0

This file is released under Creative Commons Zero 1.0 (CC0-1.0) and part of
the program "Back In Time". The program as a whole is released under GNU
General Public License v2 or any later version (GPL-2.0-or-later).
See LICENSES directory or
go to <https://spdx.org/licenses/CC0-1.0.html>
and <https://spdx.org/licenses/GPL-2.0-or-later.html>.
-->
# Manual Testing Recommendations

Automatic tests cannot cover all scenarios or potential issues. **Manual
testing by real users ensures** that _Back In Time_ behaves as
expected. It provides **insight, intuition, and real-world validation**.

From experience, manual testing of _Back In Time_ is **extremely valuable,
essential, and absolutely necessary**. Every real-world scenario, edge case,
and subtle interaction (especially in diverse GNU/Linux environments) becomes
visible only when a human actually runs the application. No automated script,
no matter how thorough, can fully capture these nuances.

Manual testing is therefore **irreplaceable**: it uncovers hidden bugs, UI
quirks, and workflow issues that only emerge under **authentic user
conditions**. Every bit of feedback from hands-on testing directly improves
reliability, usability, and user confidence.

The following recommendations help guide testing, but experienced users may
naturally explore relevant workflows without strict instructions.

## Table of contents
<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [1. Setup](#1-setup)
- [2. General Testing Guidelines](#2-general-testing-guidelines)
- [3. Core Actions](#3-core-actions)
- [4. Scheduling Tests](#4-scheduling-tests)
- [5. GUI Tests](#5-gui-tests)
- [6. Notes](#6-notes)

<!-- TOC end -->

---

## 1. Setup

- Install the latest state in the `dev` branch of the **git repository**. If
  this test is about a **Release Candidate** use the available **source
  tarball**. Consider the [install instructions and
  dependencies](CONTRIBUTING.md#build--install).
- Use a **fresh virtual machine or clean system** without a previous _Back In
  Time_ installation. If you test on your productive machine, the minimal
  recommendation is using the `--config=` option to seperate the test
  configuration from the regular one.
- Test on different GNU/Linux distributions:
  - Major lines: Debian, Arch Linux (or derivatives)
  - Non-systemd distro: Devuan GNU/Linux

---

## 2. General Testing Guidelines

- Always start from the **terminal** to catch silent errors or warnings.
- Create backup profiles in all available flavors:
  - **Local**
  - **SSH** (test keys with and without passphrase, cached, in keyring)
  - With and without **encryption**
- Consider testing _Back In Time_ in its **root-mode**, too.

---

## 3. Core Actions

- **Create a backup**
- **Restore a backup**
- **Delete a backup**
- **Delete a profile**
- **Change mode of an existing profile**

---

## 4. Scheduling Tests

- Regular **cron jobs** (e.g., every 5 minutes)
- **Repeatedly schedules** (anacron-like execution)
- **USB-triggered backups** via udev (when a drive is connected)

---

## 5. GUI Tests

- Open all dialogs and interact with them; watch for crashes or display issues.
- Try different desktop environments (e.g., MATE, Budgie).
- Try Wayland-only systems.
- Check GUI translations in your native language(s).
- Test with **qt6ct** theme overrides.

---

## 6. Notes

- Experienced users may naturally explore additional workflows beyond this list.
- Any **bugs, crashes, or unexpected behaviors** should be reported in the
  [project’s issues](https://github.com/bit-team/backintime/issues/new) with
  logs, version info or diagnostics info (use `--diagnostics`) or screenshots
  if possible.
