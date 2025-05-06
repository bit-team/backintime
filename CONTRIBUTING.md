<!--
SPDX-FileCopyrightText: © 2009 Back In Time Team

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# How to contribute to _Back In Time_

😊 **Thanks for taking the time to contribute.** 😊

🟢 **Contributions can be much more than code.** 🟢

The maintenance team welcomes all types of contributions. No contribution will
be rejected solely because it doesn't meet our quality standards, guidelines,
or rules. Every contribution is reviewed, and if necessary, improved in
collaboration with the maintenance team.  New contributors who may need
assistance or are less experienced are warmly welcomed and will be mentored by
the maintenance team upon request.

There are many ways to contribute beyond coding:
[translating the project](https://github.com/bit-team/backintime/issues/1915),
performing manual tests, analyzing and reproducing
[bugs](https://github.com/bit-team/backintime/issues), reviewing and testing
[pull requests](https://github.com/bit-team/backintime/pulls),
providing feedback on new features, designing an
[application logo](https://github.com/bit-team/backintime/issues/1961), or
reviewing the documentation and suggesting improvements.
🚀 Every contribution helps the project grow! 🚀

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
- [Instructions about translation](#instructions-about-translation)
  - [Terminology](#terminology)
  - [General recommendations for developers](#general-recommendations-for-developers)
  - [Consider Right-to-Left (RTL) and Bidirectional (BIDI) languages](#consider-right-to-left-rtl-and-bidirectional-bidi-languages)
  - [Be aware of shortcut indicators and possible duplicates](#be-aware-of-shortcut-indicators-and-possible-duplicates)
  - [Treat other translators work with respect](#treat-other-translators-work-with-respect)
- [Strategy Outline](#strategy-outline)
- [Licensing of contributed material](#licensing-of-contributed-material)
<!-- TOC end -->

# Quick guide
> [!IMPORTANT]
> Please remember to create a new branch before you begin any modifications.
> Baseline your feature or bug fix branch on `dev`
> (reflecting the latest development state).

1. Fork this repository. See Microsoft GitHub's own documentation about
   [how to fork](https://docs.github.com/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo).

2. Clone your own fork to your local machine and enter the directory:

       $ git clone git@github.com:YOURNAME/backintime.git
       $ cd backintime

3. Create and checkout your own feature or bugfix branch with `dev` as baseline branch:

       $ git checkout -b myfancyfeature dev

4. Now you can add your modifications.

5. Commit and push it to your forked repo:

        $ git commit -am 'commit message'
        $ git push

6. Test your modifications. See section [Build & Install](#build--install) and [Testing](#testing) for further details.

7. Visit your own repository on Microsoft GitHub's website and create a Pull Request.
   See Microsoft GitHub's own documentation about
   [how to create a Pull Request based on your own fork](https://docs.github.com/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork).

# Best practice and recommendations
If possible, please consider the following best practices. This will
reduce the workload of the maintainers and increase the chances of your
pull request being accepted.

- Follow [PEP 8](https://peps.python.org/pep-0008/) as a minimal Style Guide
  for Python Code.
- About strings:
  - Prefer _single quotes_ (e.g. `'Hello World'`) over _double qutoes_
    (e.g. `"Hello World"`). Exceptions are when single quotes contained in the
    string (e.g. `"Can't unmount"`).
  - Enclose translatable strings like this: `_('Translate me')`. Find more
    details in our
    [localization docu](doc/maintain/2_localization.md#instructions-for-the-translation-process).
- For docstrings follow [Google Style Guide](https://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html) 
  (see our own [HOWTO about doc generation](doc/maintain/1_doc_howto.md)).
- Avoid the use of automatic formatters like `black` but mention the use of
  them when opening a pull request.
- Run unit tests before you open a pull request. Read [Testing](#testing)
  for further details.
- Try to create new unit tests if appropriate. Use the style of regular Python
  `unittest` rather than `pytest`. If you know the difference, please try to
  follow the _Classical (aka Detroit) school_ instead of _London (aka mockist)
  school_.
- See recommendations about [how to handle translatable strings](doc/maintain/2_localization.md#instructions-for-the-translation-process).

# Resources & Further readings

- [Mailing list _bit-dev_](https://mail.python.org/mailman3/lists/bit-dev.python.org/)
- [Source code documentation for developers](https://backintime-dev.readthedocs.org)
- [Translations](https://translate.codeberg.org/engage/backintime) are done on a separate platform.
- [HowTo's and maintenance](doc/maintain/README.md)
- Further readings
   - [contribution-guide.org](https://www.contribution-guide.org)
   - [How to submit a contribution (opensource.guide)](https://opensource.guide/how-to-contribute/#how-to-submit-a-contribution)
   - [mozillascience.github.io/working-open-workshop/contributing](https://mozillascience.github.io/working-open-workshop/contributing)

# Build & Install

This section describes how to build and install _Back In Time_ in preparation
of your own contributions. It is assumed that you `git clone` this repository
first.

## Dependencies

The following dependencies are based on _Debian GNU/Linux_. Please [open an
Issue](https://github.com/bit-team/backintime/issues/new/choose) if something
is missing. If you use another GNU/Linux distribution, please install the
corresponding packages. Even if some packages are available from PyPi stick to
the packages provided by the official repository of your GNU/Linux
distribution.

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
  - `pkexec`
  - `polkitd`
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
  - All CLI runtime dependencies including the recommended
  - All GUI runtime dependencies including the recommended
  - `build-essential`
  - `gzip`
  - `gettext`
  - `python3-pyfakefs` (>= 5.7)
  - `asciidoctor`
  - Optional but recommended:
    - `pylint` (>= 3.3.0)
    - `flake8`
    - `ruff` (>= 0.6.0)
    - `codespell`
    - `reuse` (>= 4.0.0)
 
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
   3. Run unit tests via `python -m unittest` or `pytest`.
   4. `sudo make install`

* Qt GUI
   1. `cd qt`
   2. `./configure && make`
   3. Run unit tests via `python -m unittest` or `pytest`.
   4. `sudo make install`

You can use optional arguments to `./configure` for creating a Makefile.
See `common/configure --help` and `qt/configure --help` for details.

# Testing
> [!IMPORTANT]
> Remember to **manually** test _Back In Time_ and not rely solely on
> the automatic test suite. See section
> [Manual testing](doc/maintain/BiT_release_process.md#manual-testing---recommendations)
> about recommendations how to perform such tests.

After [building and installing](#build--install), run the test suite. Feel free
to use Python's own `unittest` module or `pytest` as a test runer.
Since _Back In Time_ consists of two components, `common` and `qt`,
the tests are segregated accordingly.

    $ cd common
    $ pytest

Or

    $ cd qt
    $ pytest

> [!IMPORTANT]
> Even if `pytest` is used as test runner, don't write tests in
> `pytest`-style. Stick to the good old `unittest`-style. This is a project
> rule, taking maintainability into account.

## SSH

Some tests require an available SSH server. Those tests get skipped if no SSH
server is available. The goal is to log into the SSH server on your local
computer via `ssh localhost` without using a password:

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


# Instructions about translation

## Terminology
- The translators, as native speakers, are the maintainers of the translation
  in their language and have the final decision. All following points are 
  strong recommendations, but not written in stone. Language maintainers are
  free to overule them for good reasons.
- "Directory" or "Folder"? We prefer "Directory". In our opinion, it is a
  clearly defined technical term and more precise in describing an element in
  the file system.
- Translate "Back In Time"? It is the name of the application. That shouldn't
  be translated at all.
- Some points of the following
  [General recommendations for developers](#general-recommendations-for-develoeprs)
  are also relevant for translators. 

## General recommendations for developers
The following points are about creating translatable source strings.

- Be aware that most of our translators not skilled in Python programming. They
  might don't know about GNU gettext internals and other technical
  details. They only see the translatable string in the web-frontend of our
  [translation platform](https://translate.codeberg.org/engage/backintime).
- Avoid escape characters in the strings.
- Give translators enough context with providing meaningful placeholder names.
- Avoid addressing the person with "you".
- Don't "scream" by using upper case letters (e.g. `WARNING`) or an exclamation
  mark (`!`).
- Please provide a screenshot when introducing new translatable strings or
  modifying them. The picture will be used on the translation web-frontend to
  provide translators with more context.
- [Consider Right-to-Left (RTL) and Bidiretional (BIDI) languages](#consider-right-to-left-rtl-and-bidiretional-bidi-languages).
- [Be aware of shortcut indicators and possible duplicates](#be-aware-of-shortcut-indicators-and-possible-duplicates).
- [Treat other translators work with respect](#treat-other-translators-work-with-respect).
    
```python
# Avoid escape characters for string delimiters
problematic = _('Hello \'World\'')
correct = _("Hello 'World'")

# Avoid escape characters like new lines
problematic = _('One\nTwo')`
correct = _('One') + '\n' + _('Two')  # <- Separation into multiple strings is
                                      #    no problem, because the translator
                                      #    will have a screenshot.

# Provide meaningful placeholder names
problematic = _('Can not delete {var}.')
correct = _('Can not delete {snapshot_path}.')

# Avoid addressing the person with "you"
problematic = _('Do you really want to delete this snapshot?')
correct = _('Is it really intended to delete this snapshot?')
```

## Consider Right-to-Left (RTL) and Bidirectional (BIDI) languages

In short: Always include punctuation marks (e.g. colons) in the strings to
translate.

Languages such as Arabic or Hebrew are read from right to left (RTL). To
be more precise, they can have mixed reading directions (BIDI). The GUI library used
by _Back In Time_ takes this into account when arrange elements in a
window. For example, a text-input widget is left from a label
widget. This switched order is the reason why punctuation marks (e.g. colons)
in the string of a label widget need to change their direction as well. This
task can only be performed by the translator themselves, which is why
punctuation marks need to be included in the string to translate.

## Be aware of shortcut indicators and possible duplicates

In short:
1. Use the character `&` to indicate the letter to access a GUI element via
   keyboard shortcut.
2. Be careful not to create conflicts by using the same letter multiple times
   in the same GUI context.

The _Back In Time_ GUI can be controlled via keyboard shortcuts. In the English
version, for example, the menu _Back In Time_ in the main window can be
unfolded via `Alt+T`, _Backup_ via `Alt+B`, or _Help_ via `Alt+H`. The keyboard
letters to use are indicated in the GUI with an underlined letter. The original
string in the source code uses the character `&` in front of a letter to
indicate the shortcut and produce this underline. The example above use the
source strings `Back In &Time`, `&Backup`, and `&Help`. This illustrates why it
is not appropriate to always use the first letter for shortcuts. Here in this
example, `&Back In Time` and `&Backup` would use the same letter.

Translating `&Backup` and `&Help` into Turkish becomes `&Yedek` and `Y&ardım`,
where using the first letter only would produce conflicts again.

That is why the translator needs to decide which letter to use.

## Treat other translators work with respect
Sometimes it is a matter of taste or habit how do you translate
something. People are different, therefore their translation are also
different. When modifying an existing translation please consider _Comments_
and _History_ section of that string on our translation platform. There might
be another translator who has good reason for this translation. Don't waste
other people work for no good reason. Also use the _Comments_ to document your
own reasons if you expect discussions or conflicts.

The translation for some specific languages (e.g.
[German](https://translate.codeberg.org/projects/backintime/common/de/))
do have rules every translator should follow. That rules can be found in a
colored box on top of the translation platform. Open an issue if you think
they should be modified.

# Strategy Outline
This is a broad overview of the tasks or steps to enhance _Back In Time_ as a
software and as a project. The schedule is not fixed, nor is the order of
priority.

- [Analyzing code and behavior](#analyzing-code-and-behavior)
- [Code quality & unit tests](#code-quality--unit-tests)
- [Issues](#issues)
- [Replace and remove encryption library EncFS](#replace-and-remove-encryption-library-encfs)
- [Project infrastructure](#project-infrastructure)
- [Graphical User Interface (GUI): Redesign and Refactoring](#graphical-user-interface-gui-redesign-and-refactoring)
- [Terminal User Interface (TUI)](#terminal-user-interface-tui)

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

## Replace and remove encryption library EncFS

Currently, _Back In Time_ uses [EncFS](https://github.com/vgough/encfs) for
encrypting backups, but it has known security vulnerabilities (see issue
[#1549](https://github.com/bit-team/backintime/issues/1549)). This requires
to remove it. A potential candidate for replacement is
[GoCryptFS](https://github.com/rfjakob/gocryptfs).
However, lack of resources hinders this effort. If no volunteers step forward,
the encryption feature will be removed, prioritizing user security and team
maintenance efforts. See
[Issue #1734](https://github.com/bit-team/backintime/issues/1734) about the
transition process and the discussion about alternatives to EncFS.

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

## Terminal User Interface (TUI)

Various people use _Back In Time_ via the terminal, for example, through an SSH
shell on a headless server. There is an idea of creating a terminal user
interface (TUI) or to enhance the existing command-line interface (CLI)
([#254](https://github.com/bit-team/backintime/issues/254)) or to create a
web-frontend ([#209](https://github.com/bit-team/backintime/issues/209)). The
later idea was rejected. The TUI idea also has been postponed for now. As an
alternative, it is currently being considered to change the format of the
configuration file to TOML
([#1984](https://github.com/bit-team/backintime/issues/1984)), assuming that
a TUI, while convenient and pleasant, would no longer be necessary.

# Licensing of contributed material
Keep in mind as you contribute, that code, docs and other material submitted to
the project are considered licensed under the same terms as the rest of the
work. With a few exceptions, this is
[GNU General Public License Version 2 or later](https://spdx.org/licenses/GPL-2.0-or-later.html)
(`GPL-2.0-or-later`). This project uses [SPDX metadata](https://spdx.dev/) to
provide detailed license and copyright information. This data is also
machine-readable with [REUSE tools](https://reuse.software/).

<sub>January 2025</sub>
