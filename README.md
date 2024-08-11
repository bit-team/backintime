[![Build Status](https://app.travis-ci.com/bit-team/backintime.svg)](https://app.travis-ci.com/bit-team/backintime)
[![Source code documentation Status](https://readthedocs.org/projects/backintime-dev/badge/?version=latest)](https://backintime-dev.readthedocs.io)
[![Translation status](https://translate.codeberg.org/widget/backintime/common/svg-badge.svg)](https://translate.codeberg.org/engage/backintime)

# Back In Time
<sub>Copyright (C) 2008-2024 Oprea Dan, Bart de Koning, Richard Bailey,
Germar Reitze, Taylor Raack</sub><br />
<sub>Copyright (C) 2022 Christian Buhtz, Michael Büker, Jürgen Altfeld</sub>
 
_Back In Time_ is an easy-to-use tool to backup files and folders.
It runs on GNU/Linux (not on Windows or OS X/macOS) and provides a command line
tool `backintime` and a GUI `backintime-qt` both written in Python3. It uses 
[`rsync`](https://rsync.samba.org/) to take manual or scheduled snapshots and
stores them locally or remotely through SSH. Each snapshot is in its own folder
with copies of the original files, but unchanged files are hard-linked between
snapshots to save storage space.
It was inspired by [FlyBack](https://en.wikipedia.org/wiki/FlyBack).

## Maintenance status

The project is in active development since the [new team](#the-team) joined in
summer 2022. Development is done in spare time so things need to be
prioritized. Stick with us, we all ♥️ _Back In Time_. 😁

Current focus is on fixing
[major issues](https://github.com/bit-team/backintime/issues?q=is%3Aissue+is%3Aopen+label%3AHigh)
instead of implementing new
[features](https://github.com/bit-team/backintime/labels/Feature). Read the
[strategy outline](CONTRIBUTING.md#strategy-outline) for details.
Please see  [CONTRIBUTING](CONTRIBUTING.md) if you are interested in the
development and have a look on
[open issues](https://github.com/bit-team/backintime/issues) especially
those labeled as [good first issues](https://github.com/bit-team/backintime/labels/GOOD%20FIRST%20ISSUE)
and [help wanted](https://github.com/bit-team/backintime/issues?q=is%3Aissue+is%3Aopen+label%3AHELP-WANTED).

## The team
The current team started in summer of 2022
(with [#1232](https://github.com/bit-team/backintime/issues/1232)) and
constitutes the project's 3rd generation of maintainers. Consisting of three
members with diverse backgrounds (@aryoda, @buhtz, @emtiu), the team benefits
from the assistance of the former maintainer, @Germar, who contributes from
behind the scenes.

All team members are engaged in every aspect of the project, including code
analysis, documentation, solving issues, and the implementation of new
features. This work is carried out voluntarily during their limited spare time.

# Index

- [Documentation, FAQs, Support](#documentation-faqs-support)
- [Installation](#installation)
- [Known Problems and Workarounds](#known-problems-and-workarounds)
- [Contributing and other ways to support the project](#contributing-and-other-ways-to-support-the-project)

# Documentation, FAQs, Support

 * [FAQ - Frequently Asked Questions](FAQ.md)
 * [End user documentation](https://backintime.readthedocs.org/) (not totally up-to-date)
 * [Mailing list
   _bit-dev_](https://mail.python.org/mailman3/lists/bit-dev.python.org/) for
   **every topic**, question and idea about _Back In Time_. Despite its name
   it is not restricted to development topics only.
 * Use [Issues](https://github.com/bit-team/backintime/issues) to ask
   questions and report bugs.
 * [Source code documentation for developers](https://backintime-dev.readthedocs.org)

# Installation

_Back In Time_ is included in [many GNU/Linux distributions](https://repology.org/project/backintime/badges).
Use their repositories to install it. If you want to contribute or using the latest development version
of _Back In Time_ please see section [Build & Install](CONTRIBUTING.md#build--install) in [`CONTRIBUTING.md`](CONTRIBUTING.md).
Also the dependencies are described there.

## Alternative installation options
Besides the repositories of the official GNU/Linux distributions, there are other alternative
installation options provided and maintained by third parties.

- [@Germar](https://github.com/germar)'s Personal Package Archive ([PPA](https://launchpad.net/ubuntu/+ppas)) offering [`ppa:bit-team/stable`](https://launchpad.net/~bit-team/+archive/ubuntu/stable) as stable and [`ppa:bit-team/testing`](https://launchpad.net/~bit-team/+archive/ubuntu/testing) as testing PPA.
- [@jean-christophe-manciot](https://github.com/jean-christophe-manciot)'s PPA distributing [_Back In Time_ for the latest stable Ubuntu release](https://git.sdxlive.com/PPA/about). See [PPA requirements](https://git.sdxlive.com/PPA/about/#requirements) and [install instructions](https://git.sdxlive.com/PPA/about/#installing-the-ppa).
- The Arch User Repository ([AUR](https://aur.archlinux.org/)) does offer [some packages](https://aur.archlinux.org/packages?K=backintime).

# Known Problems and Workarounds

In the latest stable release:
- [File permissions handling and therefore possible non-differential backups](#file-permissions-handling-and-therefore-possible-non-differential-backups)
- [`qt_probing.py` may hang with high CPU usage when running BiT as `root` via `cron`](#qt_probingpy-may-hang-with-high-cpu-usage-when-running-bit-as-root-via-cron)

In older releases:
- Error: "module 'qttools' has no attribute 'initate_translator'" with EncFS when prompting the user for a password ([#1553](https://github.com/bit-team/backintime/issues/1553))
- [Tray icon or other icons not shown correctly](#tray-icon-or-other-icons-not-shown-correctly)
- [Non-working password safe and BiT forgets passwords (keyring backend issues)](#non-working-password-safe-and-bit-forgets-passwords-keyring-backend-issues)
- [Incompatibility with rsync >= 3.2.4](#incompatibility-with-rsync-324-or-newer)

More problems described in
[this FAQ section](FAQ.md#problems-errors--solutions).

## Problems in the latest stable release

All releases can be found in the [list of releases](https://github.com/bit-team/backintime/releases).

### File permissions handling and therefore possible non-differential backups

In version 1.2.0, the handling of file permissions changed.
In versions <= 1.1.24 (until 2017) all file permissions were set to `-rw-r--r--` in the backup target.
In versions >= 1.2.0 (since 2019) `rsync` is executed with `--perms` option which tells `rsync` to
preserve the source file permission.

Therefore backups can be larger and slower, especially the first backup after upgrading to a version >= 1.2.0.

If you don't like the new behavior, you can use _Expert Options_ -> _Paste additional options to rsync_
to add `--no-perms --no-group --no-owner` to it.
Note that the exact file permissions can still be found in `fileinfo.bz2` and are also considered when restoring
files.

### `qt_probing.py` may hang with high CPU usage when running BiT as `root` via `cron`

See the related issue [#1592](https://github.com/bit-team/backintime/issues/1592).

The only reliable work-around is to delete (or move into another folder)
the file `/usr/share/backintime/common/qt_probing.py`:

`mv /usr/share/backintime/common/qt_probing.py /usr/share/backintime/`

Renaming does *not* work!

## Problems in versions older than the latest stable release

### Tray icon or other icons not shown correctly

**Status: Fixed in v1.4.0**

Missing installations of Qt-supported themes and icons can cause this effect.
_Back In Time_ may activate the wrong theme in this
case leading to some missing icons. A fix for the next release is in preparation.

As clean solution, please check your Linux settings (Appearance, Styles, Icons)
and install all themes and icons packages for your preferred style via
your package manager.

See issues [#1306](https://github.com/bit-team/backintime/issues/1306)
and [#1364](https://github.com/bit-team/backintime/issues/1364).

### Non-working password safe and BiT forgets passwords (keyring backend issues)

**Status: Fixed in v1.3.3 (mostly) and v1.4.0**

_Back in Time_ does only support selected "known-good" backends
to set and query passwords from a user-session password safe by
using the [`keyring`](https://github.com/jaraco/keyring) library.

Enabling a supported keyring requires manual configuration of a configuration file until there is e.g. a settings GUI for this.

Symptoms are DEBUG log output (with the command line argument `--debug`) of keyring problems can be recognized by output like:

```
DEBUG: [common/tools.py:829 keyringSupported] No appropriate keyring found. 'keyring.backends...' can't be used with BackInTime
DEBUG: [common/tools.py:829 keyringSupported] No appropriate keyring found. 'keyring.backends.chainer' can't be used with BackInTime
```

To diagnose and solve this follow these steps in a terminal:

```
# Show default backend
python3 -c "import keyring.util.platform_; print(keyring.get_keyring().__module__)"

# List available backends:
keyring --list-backends 

# Find out the config file folder:
python3 -c "import keyring.util.platform_; print(keyring.util.platform_.config_root())"

# Create a config file named "keyringrc.cfg" in this folder with one of the available backends (listed above)
[backend]
default-keyring=keyring.backends.kwallet.DBusKeyring
```

See also issue [#1321](https://github.com/bit-team/backintime/issues/1321)

### Incompatibility with rsync 3.2.4 or newer

**Status: Fixed in v1.3.3**

The release (`1.3.2`) and earlier versions of _Back In Time_ are incompatible
with `rsync >= 3.2.4`
([#1247](https://github.com/bit-team/backintime/issues/1247)).

If you use `rsync >= 3.2.4` and `backintime <= 1.3.2` there is a
workaround. Add `--old-args` in
[_Expert Options_ / _Additional options to rsync_](https://backintime.readthedocs.io/en/latest/settings.html#expert-options).
Note that some GNU/Linux distributions (e.g. Manjaro) using a workaround with
environment variable `RSYNC_OLD_ARGS` in their distro-specific packages for
_Back In Time_. In that case you may not see any problems.

# Contributing and other ways to support the project
See [CONTRIBUTING](CONTRIBUTING.md) file for an overview about the projects
workflow and strategy.

<sub>July 2024</sub>
