<!--
SPDX-FileCopyrightText: © 2009 Back In Time Team

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# How to contribute to _Back In Time_

😊 **Thanks for taking the time to contribute!**

The maintenance team welcomes all types of contributions. No contribution will
be rejected solely because it doesn't meet our quality standards, guidelines,
or rules. Every contribution is reviewed, and if necessary, improved in
collaboration with the maintenance team.  New contributors who may need
assistance or are less experienced are warmly welcomed and will be mentored by
the maintenance team upon request.

# Index

<!-- TOC start -->
- [Quick guide](#quick-guide)
- [Best practice and recommendations](#best-practice-and-recommendations)
- [Resources & Further Readings](#resources--further-readings)
- [Build & Install](#build--install)
  - [Dependencies](#dependencies)
  - [Build and install via `make` system
    (recommended)](#build-and-install-via-make-system-recommended)
  - [Build own `deb` file](#build-own-deb-file)
- [Testing](#testing)
  - [SSH](#SSH)
- [What happens after you opened a Pull Request (PR)?](#what-happens-after-you-opened-a-pull-request-PR)
- [Strategy Outline](#strategy-outline)
- [Licensing of contributed material](#licensing-of-contributed-material)
<!-- TOC end -->

# Quick guide
> [!IMPORTANT]
> Please remember to create a new branch before you begin any modifications.
> Baseline your feature or bug fix branch on `dev`
> (reflecting the latest development state).

1. Fork this repository. See Microsoft GitHub's own documentation about
   [how to fork](https://docs.github.com/de/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo).

2. Clone your own fork to your local machine and enter the directory:

       $ git clone git@github.com:YOURNAME/backintime.git
       $ cd backintime

3. Create and checkout your own feature or bugfix branch with `dev` as baseline branch:

       $ git checkout --branch myfancyfeature dev

4. Now you can add your modifications.

5. Commit and push it to your forked repo:

        $ git commit -am 'commit message'
        $ git push

6. Test your modifications. See section [Build & Install](#build--install) and [Testing](#testing) for further details.

7. Visit your on repository on Microsoft GitHub's website and create a Pull Request.
   See Microsoft GitHub's own documentation about
   [how to create a Pull Request based on your own fork](https://docs.github.com/de/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork).

# Best practice and recommendations
Please take the following best practices into account if possible. This will reduce
the work load of the maintainers and to increase the chance that your pull
request is accepted.

- Follow [PEP 8](https://peps.python.org/pep-0008/) as a minimal Style Guide
  for Python Code.
- Prefer _single quotes_ (e.g. `'Hello World'`) over _double qutoes_
  (e.g. `"Hello World"`). Exceptions are when single quotes contained in the
  string (e.g. `"Can't unmount"`).
- For docstrings follow [Google Style Guide](https://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html) 
  (see our own [HOWTO about doc generation](doc/maintain/1_doc_howto.md)).
- Avoid the use of automatic formatters like `black` but mention the use of
  them when opening a pull request.
- Run unit tests before you open a Pull Request. You can run them via
  `make`-system with `cd common && ./configure && make && make test` or using a
  regular unittest runner of your choice (e.g. `pytest`). See section
  [Build and install via `make` system](#build-and-install-via-make-system-recommended)
  for further details.
- Try to create new unit tests if appropriate. Use the style of regular Python
  `unittest` rather than `pytest`. If you know the difference, please try to follow
  the _Classical (aka Detroit) school_ instead of _London (aka mockist)
  school_.
- See recommendations about [how to handle translatable strings](doc/maintain/2_localization.md#instructions-for-the-translation-process).

# Resources & Further readings

- [Mailing list _bit-dev_](https://mail.python.org/mailman3/lists/bit-dev.python.org/)
- [Source code documentation for developers](https://backintime-dev.readthedocs.org)
- [Translations](https://translate.codeberg.org/engage/backintime) are done on a separate platform.
- [HowTo's and maintenance](doc/maintain/README.md)
- [contribution-guide.org](https://www.contribution-guide.org)
- [How to submit a contribution (opensource.guide)](https://opensource.guide/how-to-contribute/#how-to-submit-a-contribution)
- [mozillascience.github.io/working-open-workshop/contributing](https://mozillascience.github.io/working-open-workshop/contributing)


# Build & Install

This section describes how to build and install _Back In Time_ in preparation
of your own contributions. It is assumed that you `git clone` this repository
first.

## Dependencies

The following dependencies are based on Ubuntu. Please [open an
Issue](https://github.com/bit-team/backintime/issues/new/choose) if something
is missing. If you use another GNU/Linux distribution, please install the
corresponding packages. Even if some packages are available from PyPi stick to
the packages provided by the official repository of your GNU/Linux distribution.

* Runtime dependencies for the CLI

  - `python3` (>= 3.9)
  - `rsync`
  - `cron-daemon`
  - `openssh-client`
  - `sshfs`
  - `python3-keyring`
  - `python3-dbus`
  - `python3-packaging`
  -  Recommended
     - `encfs`

* Runtime dependencies for the GUI

  - `x11-utils`
  - `python3-pyqt6` (not from _PyPi_ via `pip`)
  - `python3-dbus.mainloop.pyqt6` (not available from _PyPi_ via `pip`)
  - `policykit-1`
  - `qttranslations6-l10n`
  - `qtwayland6` (if Wayland is used as display server instead of X11)
  - Recommended
      - For SSH key storage **one** of these packages
        - `python3-secretstorage`
        - `python3-keyring-kwallet`
        - `python3-gnomekeyring`
      - For diff-like comparing files between backup snapshots **one** of these
        packages
        - `kompare`
        - or `meld`
      - Optional: Default icons
        - The `oxygen` icons should be offered as optional dependency
          since they are used as fallback in case of missing icons
          (mainly app and system-tray icons)

* Build and testing dependencies
  - All runtime dependencies for CLI and GUI including the recommended
  - `build-essential`
  - `gzip`
  - `gettext`
  - `python3-pyfakefs` (>= 5.7)
  - Optional but recommended:
    - `pylint` (>= 3.3.0)
    - `flake8`
    - `ruff` (>= 0.6.0)
    - `codespell`
 
* Dependencies to build documentation
  - All runtime, build, testing dependencies including the recommended
  - `mkdocs`
  - `mkdocs-material`

## Build and install via `make` system (recommended)

> [!IMPORTANT]
> Install [Dependencies](#dependencies) before you build and install.

Remember that _Back In Time_ does consist of two packages, which must be built
and installed separately accordingly.

* Command line tool
   1. `cd common`
   2. `./configure && make`
   3. Run unit tests via `make test`
   4. `sudo make install`

* Qt GUI
   1. `cd qt`
   2. `./configure && make`
   3. Run unit tests via `make test`
   4. `sudo make install`

You can use optional arguments to `./configure` for creating a Makefile.
See `common/configure --help` and `qt/configure --help` for details.

# Testing
> [!IMPORTANT]
> Remember to **manually** test _Back In Time_ and not rely solely on
> the automatic test suite. See section
> [Manual testing](doc/maintain/BiT_release_process.md#manual-testing---recommendations)
> about recommendations how to perform such tests.

After [building and installing](#build--install), `make` can be used to run the
test suite. Since _Back In Time_ consists of two components, `common` and `qt`,
the tests are segregated accordingly.

    $ cd common
    $ make test

Or

    $ cd qt
    $ make test

Alternatively use `make test-v` for a more verbose output. The `make` system
will use `pytest` as test runner if available otherwise Python's own `unittest`
module.

## SSH

Some tests require an available SSH server. They get skipped if this is not the
case. The goal is to log into the SSH server on your local computer via
`ssh localhost` without using a password:

- Generate an RSA key pair executing `ssh-keygen`. Use the default file name
  and don't use a passphrase for the key.
- Populate the public key to the server executing `ssh-copy-id`.
- Make the `ssh` instance run.
- The port `22` (SSH default) should be available.
- _Authorize_ the key with `$ ssh localhost` and insert your user accounts
  password.

To test the connection just execute `ssh localhost` and you should see an
SSH shell **without** being asked for a password.

For detailed setup instructions see the
[how to setup openssh for unit tests](doc/maintain/3_How_to_set_up_openssh_server_for_ssh_unit_tests.md).

# What happens after you opened a Pull Request (PR)?
In short:
1. The maintenance team will review your PR in days or weeks.
2. Modifications may be requested, and the PR will eventually be approved.
3. One of two labels will be added to the PR:
   - [PR: Merge after creative-break](https://github.com/bit-team/backintime/labels/PR%3A%20Merge%20after%20creative-break):
     Merge, but with a minimum delay of one week to allow other maintainers to review.
   - [PR: Waiting for review](https://github.com/bit-team/backintime/labels/PR%3A%20Waiting%20for%20review):
     Wait until a second approval from another maintainer.

The maintenance team members are promptly notified of your request. One of
them will respond within days or weeks. Note that all team members perform
their duties voluntarily in their limited spare time.
Please read the maintainers' responses carefully, answer their questions, and
try to follow their instructions. Do not hesitate to ask for clarification if
needed. At least one maintainer will review and ultimately approve your pull
request.

Depending on the topic or impact of the PR, the maintainer may decide
that an approval from a second maintainer is needed. This may result in
additional waiting time. Please remain patient. In such cases, the PR will be
labeled
[PR: Waiting for review](https://github.com/bit-team/backintime/labels/PR%3A%20Waiting%20for%20review). 

If no second approval is necessary, the PR is labeled
[PR: Merge after creative-break](https://github.com/bit-team/backintime/labels/PR%3A%20Merge%20after%20creative-break)
and will remain open for minimum of one week. This rule allows all maintainers
the chance to review and potentially veto the pull request.

# Strategy Outline
The following tries to give a broad overview of the tasks or steps to
enhance _Back In Time_ as a software and as a project. The schedule is
not fixed, nor is the order of priority.

- [Analyzing code and behavior](#analyzing-code-and-behavior)
- [Code quality & unit tests](#code-quality--unit-tests)
- [Issues](#issues)
- [Replace encryption library EncFS or remove it](#replace-encryption-library-encfs-or-remove-it)
- [Project infrastructure](#project-infrastructure)
- [Graphical User Interface (GUI): Redesign and Refactoring](#graphical-user-interface-gui-redesign-and-refactoring)
- [Terminal User Interface](#terminal-user-interface)

## Analyzing code and behavior

As none of the current team members were involved in the original development
of _Back In Time_, there is a lack of deep understanding of certain aspects of
the codebase and its functionality. Part of the work done in this project
involves conducting research on the code, its features, infrastructure, and
documenting the findings.

## Code quality & unit tests

One challenge resembles a chicken-and-egg problem: the code structure lacks
sufficient isolation, making it difficult, if not nearly impossible in some
cases, to write valuable unit tests. Heavy refactoring of the code is
necessary, but this carries a high risk of introducing new bugs. To mitigate
this risk, unit tests are essential to catch any potential bugs or unintended
changes in the behavior of _Back In Time_. Each of the problems is blocking the
solution to the other problem.

Considering the three major types of tests (_unit_, _integration_, _system_),
the current test suite primarily consists of _system tests_. While these
_system tests_ are valuable, their purpose differs from that of _unit tests_.
Due to the lack of _unit tests_ in the test suite, the codebase
has notably low test coverage
(see [Issue #1489](https://github.com/bit-team/backintime/issues/1489)).

The codebase does not adhere to [PEP8](https://peps.python.org/pep-0008/),
which serves as the minimum Python coding style. Utilizing linters in their
default configuration is currently not feasible. One of our objectives is to
align with PEP8 standards and meet the requirements of code linters.
See [Issue #1755](https://github.com/bit-team/backintime/issues/1755) about it.

## Issues

All existing issues have been triaged by the current team.
[Labels](https://github.com/bit-team/backintime/labels) are assigned to
indicate priority, along with a
[milestone](https://github.com/bit-team/backintime/milestones) indicating which
planned release will address the issue. Some of these issues persists for a
long time and involve multiple complex problems. They can be challenging to
diagnose due to various factors. Enhancing test coverage and code quality is
one aspect aimed at finding and implementing solutions for these issues.

## Replace encryption library EncFS or remove it

Currently, _Back In Time_ uses [EncFS](https://github.com/vgough/encfs) for
encrypting backups, but it has known security vulnerabilities (see issue
[#1549](https://github.com/bit-team/backintime/issues/1549)). This requires
replacing it, with [GoCryptFS](https://github.com/rfjakob/gocryptfs) as a
potential candidate. However, lack of resources hinders this effort. If no
volunteers step forward, the encryption feature will be removed, prioritizing
user security and team maintenance efforts.
See [Issue #1734](https://github.com/bit-team/backintime/issues/1734) about the
transition process and the discussion about alternatives to EncFS.

Besides replacing EncFS there is also a
[discussion](https://mail.python.org/archives/list/bit-dev@python.org/thread/D2GXCCVUAVZ2E5ELBHUZGT7ITUN4ADEP)
going on if _Back In Time_ needs an encryption feature or if encryption should
be done on file systems level via
[LUKS](https://en.wikipedia.org/wiki/Linux_Unified_Key_Setup)
or similar solutions.

## Project infrastructure

At present, _Back In Time_ utilizes a build system that relies on `make`. However,
this approach has several shortcomings and does not adhere to modern standards
in Python packaging ([PEP 621](https://peps.python.org/pep-0621),
[PEP 517](https://peps.python.org/pep-0517),
[src layout](https://packaging.python.org/en/latest/tutorials/packaging-projects),
[pyproject.toml](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)).
The team intends to migrate to these contemporary standards to streamline
the maintenance of _Back In Time_ ([#1575](https://github.com/bit-team/backintime/issues/1575)).

## Graphical User Interface (GUI): Redesign and Refactoring

Over the years, the GUI has become increasingly complex. It requires a visual
redesign as well as code refactoring. Additionally, it lacks tests.

## Terminal User Interface

Various people use _Back In Time_ via the terminal, for example, through an SSH
shell on a headless server. There is an idea of creating a terminal user
interface (TUI) or to enhance the existing command-line interface (CLI). See
[#254](https://github.com/bit-team/backintime/issues/254). The proposal of
having a web frontend was rejected
([#209](https://github.com/bit-team/backintime/issues/209)). Separate
projects offering a web fronted will be supported of course.

# Licensing of contributed material
Keep in mind as you contribute, that code, docs and other material submitted to
the project are considered licensed under the same terms as the rest of the
work. With a few exceptions, this is
[GNU General Public License Version 2 or later](https://spdx.org/licenses/GPL-2.0-or-later.html)
(GPL-2.0-or-later). This project uses [SPDX metadata](https://spdx.dev/) to
provide detailed license and copyright information. This data is also
machine-readable with [REUSE tools](https://reuse.software/).

<sub>November 2024</sub>
