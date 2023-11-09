[![Build Status](https://app.travis-ci.com/bit-team/backintime.svg)](https://app.travis-ci.com/bit-team/backintime)
[![Coverage Status](https://coveralls.io/repos/github/bit-team/backintime/badge.svg?branch=main)](https://coveralls.io/github/bit-team/backintime?branch=main)
[![Source code documentation Status](https://readthedocs.org/projects/backintime-dev/badge/?version=latest)](https://backintime-dev.readthedocs.io)
[![Translation status](https://translate.codeberg.org/widget/backintime/common/svg-badge.svg)](https://translate.codeberg.org/engage/backintime)

# Back In Time
<sub>Copyright (C) 2008-2023 Oprea Dan, Bart de Koning, Richard Bailey,
Germar Reitze, Taylor Raack, Christian Buhtz, Michael Büker, Jürgen Altfeld<sub>
 
It is an easy-to-use backup tool for files and folders.
It runs on GNU Linux and provides a command line tool `backintime` and a
Qt5 GUI `backintime-qt` both written in Python3. It uses 
[`rsync`](https://rsync.samba.org/) to take manual or scheduled snapshots and
stores them locally or remotely through SSH. Each snapshot is its own folder
with copies of the original files, but unchanged files are hard-linked between
snapshots to save space.
It was inspired by [FlyBack](https://en.wikipedia.org/wiki/FlyBack).

You only need to specify 3 things:

* What folders to back up.
* Where to save snapshots.
* The backup frequency (manual, every hour, every day, every month).

## Maintenance status

A small team (Christian Buhtz, Michael Büker and Jürgen Altfeld)
has started in summer 2022 to get things moving again after the
development of this project has been dormant for a while.
We do the development in our spare time and have to prioritise so
stick with us, we all ♥️ _Back In Time_. 😁

We are currently focusing on fixing
[major issues](https://github.com/bit-team/backintime/issues?q=is%3Aissue+is%3Aopen+label%3AHigh)
instead of implementing new
[features](https://github.com/bit-team/backintime/labels/Feature).
If you are interested in the development, please
see [CONTRIBUTING](CONTRIBUTING.md) and have a look on
[open issues](https://github.com/bit-team/backintime/issues) especially
those labeled as [good first](https://github.com/bit-team/backintime/labels/GOOD%20FIRST%20ISSUE)
and [help wanted](https://github.com/bit-team/backintime/issues?q=is%3Aissue+is%3Aopen+label%3AHELP-WANTED).

## Index

- [Documentation, FAQs, Support](#documentation-faqs-support)
- [Installation](#installation)
- [Known Problems and Workarounds](#known-problems-and-workarounds)
- [CONTRIBUTING](CONTRIBUTING.md)

## Documentation, FAQs, Support

 * [End user documentation](https://backintime.readthedocs.org/) (not totally up-to-date)
 * [FAQ - Frequently Asked Questions](FAQ.md)
 * [Source code documentation for developers](https://backintime-dev.readthedocs.org)
 * Use [Issues](https://github.com/bit-team/backintime/issues) to ask questions and report bugs.
 * [Mailing list
   _bit-dev_](https://mail.python.org/mailman3/lists/bit-dev.python.org/) for
   **every topic**, question and idea about _Back In Time_. Despite its name
   it is not restricted to development topics only.

## Installation

_Back In Time_ is included in [many GNU/Linux distributions](https://repology.org/project/backintime/badges).
Use their repositories to install it. If you want to contribute or using the latest development version
of _Back In Time_ please see section [Build & Install](CONTRIBUTING.md#build--install) in [`CONTRIBUTING.md`](CONTRIBUTING.md).
Also the dependencies are described there.

### Alternative installation options
Besides the repositories of the official GNU/Linux distributions, there are other alternative
installation options provided and maintained by third parties.

- A Personal Package Archive (PPA) hosted at Launchpad provided by [@Germar](https://github.com/germar) offering [`ppa:bit-team/stable`](https://launchpad.net/~bit-team/+archive/ubuntu/stable) as stable and [`ppa:bit-team/testing`](https://launchpad.net/~bit-team/+archive/ubuntu/testing) as testing PPA.
- A [PPA distributing _Back In Time_ for the latest stable Ubuntu release](https://git.sdxlive.com/PPA/about) provided by [@jean-christophe-manciot](https://github.com/jean-christophe-manciot). See [PPA requirements](https://git.sdxlive.com/PPA/about/#requirements) and [install instructions](https://git.sdxlive.com/PPA/about/#installing).
- The Arch User Repository (AUR) do offer [some packages](https://aur.archlinux.org/packages?K=backintime).

## Known Problems and Workarounds

In the latest stable release:
- [File permissions handling and therefore possible non-differential backups](#file-permissions-handling-and-therefore-possible-non-differential-backups)
- RTE "module 'qttools' has no attribute 'initate_translator'" with encFS when prompting the user for a password (#1553)
- [Warning: apt-key is deprecated. Manage keyring files in trusted.gpg.d instead (see apt-key(8)).](#warning-apt-key-is-deprecated-manage-keyring-files-in-trustedgpgd-instead-see-apt-key8)

In older releases:
- [Tray icon or other icons not shown correctly](#tray-icon-or-other-icons-not-shown-correctly)
- [Non-working password safe and BiT forgets passwords (keyring backend issues)](#non-working-password-safe-and-bit-forgets-passwords-keyring-backend-issues)
- [Incompatibility with rsync >= 3.2.4](#incompatibility-with-rsync-324-or-newer)
- [Python 3.10 compatibility and Ubuntu version](#python-310-compatibility-and-ubuntu-version)

### Problems in the latest stable release

All releases can be found in the [list of releases](https://github.com/bit-team/backintime/releases).

#### File permissions handling and therefore possible non-differential backups

In version 1.2.0, the handling of file permissions changed.
In versions <= 1.1.24 (until 2017) all file permissions were set to `-rw-r--r--` in the backup target.
In versions >= 1.2.0 (since 2019) `rsync` is executed with `--perms` option which tells `rsync` to
preserve the source file permission.

Therefore backups can be larger and slower, especially the first backup after upgrading to a version >= 1.2.0.

If you don't like the new behavior, you can use _Expert Options_ -> _Paste additional options to rsync_
to add `--no-perms --no-group --no-owner` to it.
Note that the exact file permissions can still be found in `fileinfo.bz2` and are also considered when restoring
files.

#### Warning: apt-key is deprecated. Manage keyring files in trusted.gpg.d instead (see apt-key(8)).

In newer Ubuntu-based distros you may get this warning if you manually install _Back In Time_
as described in the [Installation](#installation) section here.

The reason is that public keys of signed packages shall be stored in a new folder now
(for details see https://itsfoss.com/apt-key-deprecated/).

You can currently ignore this warning until we have found a reliable way
to support all Ubuntu distros (older and newer ones).

This issue is tracked in [#1338](https://github.com/bit-team/backintime/issues/1338).

### Problems in versions older than the latest stable release

#### Tray icon or other icons not shown correctly

**Status: Fixed in v1.4.0**

Missing installations of Qt5-supported themes and icons can cause this effect.
_Back In Time_ may activate the wrong theme in this
case leading to some missing icons. A fix for the next release is in preparation.

As clean solution, please check your Linux settings (Appearance, Styles, Icons)
and install all themes and icons packages for your preferred style via
your package manager.

See issues [#1306](https://github.com/bit-team/backintime/issues/1306)
and [#1364](https://github.com/bit-team/backintime/issues/1364).

#### Non-working password safe and BiT forgets passwords (keyring backend issues)

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

#### Incompatibility with rsync 3.2.4 or newer

The release (`1.3.2`) and earlier versions of _Back In Time_ are incompatible with `rsync >= 3.2.4` ([#1247](https://github.com/bit-team/backintime/issues/1247)). The problem is [fixed](https://github.com/bit-team/backintime/pull/1351) in the current master branch of that repo and will be released with the next release (`1.3.3`) of _Back In Time_.

If you use `rsync >= 3.2.4` and `backintime <= 1.3.2` there is a workaround. Add `--old-args` in [_Expert Options_ / _Additional options to rsync_](https://backintime.readthedocs.io/en/latest/settings.html#expert-options). Note that some GNU/Linux distributions (e.g. Manjaro) using a workaround with environment variable `RSYNC_OLD_ARGS` in their distro-specific packages for _Back In Time_. In that case you may not see any problems.

#### Python 3.10 compatibility and Ubuntu version

_Back In Time_ versions older than 1.3.2 do not start with Python >= 3.10.
Ubuntu 22.04 LTS ships with Python 3.10 and backintime 1.2.1, but has applied
[a patch](https://bugs.launchpad.net/ubuntu/+source/backintime/+bug/1976164/+attachment/5593556/+files/backintime_1.2.1-3_1.2.1-3ubuntu0.1.diff)
to make it work. If you want to update to backintime 1.3.2 in Ubuntu, you may use the PPA: see under [`INSTALL/Ubuntu PPA`](#Ubuntu-PPA).

<sub>November 2023</sub>
