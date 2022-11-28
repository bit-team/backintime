[![Build Status](https://app.travis-ci.com/bit-team/backintime.svg?branch=master)](https://app.travis-ci.com/bit-team/backintime)
[![Coverage Status](https://coveralls.io/repos/github/bit-team/backintime/badge.svg?branch=master)](https://coveralls.io/github/bit-team/backintime?branch=master)
[![Source code documentation status](https://readthedocs.org/projects/backintime-dev/badge/?version=latest)](http://backintime.readthedocs.org/projects/backintime-dev/en/latest/?badge=latest)

# Back In Time
<sub>Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze, Taylor Raack<sub>
 
It is an easy to use backup tool for Linux heavily using [`rsync`](https://rsync.samba.org/) in the back. It was inspired by [FlyBack](https://en.wikipedia.org/wiki/FlyBack).
It provides a command line tool `backintime` and a Qt5 GUI `backintime-qt` both written in Python3.

You only need to specify 3 things:

* What folders to back up.
* Where to save snapshots.
* The backup frequency (manual, every hour, every day, every month).

## Maintenance status

The development of this project has been dormant for a while. But a small team has started
in summer 2022 to get things moving again. Stick with us, we all ♥️ _Back In Time_. 😁

We are currently trying to fix the [major issues](https://github.com/bit-team/backintime/issues?q=is%3Aissue+is%3Aopen+label%3AHigh)
while not implementing new features to prepare a new stable release. The next release is planned in early 2023. If you are interested in the development, please see the [Contribute](#contribute) section.

## Index

* [Documentation & FAQs](#documentation--faqs)
* [Support](#support)
* [Known Problems and Workarounds](#known-problems-and-workarounds)
* [Download](#download)
* [Installation and Dependencies](#installation)
* [Contribute](#contribute)

## Documentation & FAQs

 * [End user documentation](https://backintime.readthedocs.org/) (not totally up-to-date)
 * [Wiki including a FAQs](https://github.com/bit-team/backintime/wiki)
 * [Source code documentation for developers](https://backintime-dev.readthedocs.org)

## Support

Please feel free to ask questions and report bugs in form of [Issues](https://github.com/bit-team/backintime/issues)

## Known Problems and Workarounds
 - [Incompatibility with rsync >= 3.2.4](#incompatibility-with-rsync-324-or-newer)
 - [File permissions handling and therefore possible non-differential backups](#file-permissions-handling-and-therefore-possible-non-differential-backups)
 - [Python 3.10 compatibility and Ubuntu version](#python-310-compatibility-and-ubuntu-version)
 - [Non-working password safe and BiT forgets passwords (keyring backend issues)](#non-working-password-safe-and-bit-forgets-passwords-keyring-backend-issues)
 - [Warning: apt-key is deprecated. Manage keyring files in trusted.gpg.d instead (see apt-key(8)).](#warning-apt-key-is-deprecated-manage-keyring-files-in-trustedgpgd-instead-see-apt-key8)
 - [Tray icon or other icons not shown correctly](#tray-icon-or-other-icons-not-shown-correctly)
### Incompatibility with rsync 3.2.4 or newer

The latest release (`1.3.2`) and earlier versions of _Back In Time_ are incompatible with `rsync >= 3.2.4` ([#1247](https://github.com/bit-team/backintime/issues/1247)). The problem is [fixed](https://github.com/bit-team/backintime/pull/1351) in the current master branch of that repo and will be released with the next release (`1.3.3`) of _Back In Time_.

If you use `rsync >= 3.2.4` and `backintime <= 1.3.2` there is a workaround. Add `--old-args` in [_Expert Options_ / _Additional options to rsync_](https://backintime.readthedocs.io/en/latest/settings.html#expert-options). Note that some GNU/Linux distributions (e.g. Manjaro) using a workaround with environment variable `RSYNC_OLD_ARGS` in their distro-specific packages for _Back In Time_. In that case you may not see any problems.

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

### Python 3.10 compatibility and Ubuntu version

_Back In Time_ versions older than 1.3.2 do not start with Python >= 3.10.
Ubuntu 22.04 LTS ships with Python 3.10 and backintime 1.2.1, but has applied
[a patch](https://bugs.launchpad.net/ubuntu/+source/backintime/+bug/1976164/+attachment/5593556/+files/backintime_1.2.1-3_1.2.1-3ubuntu0.1.diff)
to make it work. If you want to update to backintime 1.3.2 in Ubuntu, you may use the PPA: see under [`INSTALL/Ubuntu PPA`](#Ubuntu-PPA).

### Non-working password safe and BiT forgets passwords (keyring backend issues)

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

### Warning: apt-key is deprecated. Manage keyring files in trusted.gpg.d instead (see apt-key(8)).

In newer Ubuntu-based distros you may get this warning if you manually install _Back In Time_
as described in the [Installation](#installation) section here.

The reason is that public keys of signed packages shall be stored in a new folder now
(for details see https://itsfoss.com/apt-key-deprecated/).

You can currently ignore this warning until we have found a reliable way
to support all Ubuntu distros (older and newer ones).

This issue is tracked in [#1338](https://github.com/bit-team/backintime/issues/1338).

### Tray icon or other icons not shown correctly

Missing installations of Qt5-supported themes and icons can cause this effect.
_Back In Time_ may activate the wrong theme in this
case leading to some missing icons. A fix for the next release is in preparation.

As clean solution, please check your Linux settings (Appearance, Styles, Icons)
and install all themes and icons packages for your preferred style via
your package manager.

See issues [#1306](https://github.com/bit-team/backintime/issues/1306)
and [#1364](https://github.com/bit-team/backintime/issues/1364).

## Download

Please find the latest versions in the [release section](https://github.com/bit-team/backintime/releases/latest).

## Installation

_Back In Time_ is included in many distributions. Use their repositories to install it.

### From distribution packages

#### Ubuntu PPA

We provide a PPA (Private Package Archive) with current stable version
(ppa:bit-team/stable) and a testing PPA (ppa:bit-team/testing)

**Important:** Until version 1.3.2 there was a bug that caused
`backintime` failed to start if the package `backintime-qt` was not installed.
As work-around also install `backintime-qt` because the missing
Udev `serviceHelper` system D-Bus daemon is packaged there.

    # You can ignore "Warning: apt-key is deprecated..." for now (see issue #1338)
    sudo add-apt-repository ppa:bit-team/stable
    sudo apt-get update
    sudo apt-get install backintime-qt

or

    sudo add-apt-repository ppa:bit-team/testing
    sudo apt-get update
    sudo apt-get install backintime-qt

#### Debian/Ubuntu make packages

    ./makedeb.sh
    sudo dpkg -i ../backintime-common-<version>.deb
    sudo dpkg -i ../backintime-qt-<version>.deb

#### ArchLinux

_Back In Time_ is available through the AUR package [`backintime`](https://aur.archlinux.org/packages/backintime)
that also includes the GUI (`backintime-qt`).

**Important:** Until version 1.3.2 there was a bug that prevented the
           successful **first-time** installation due to a unit test failure when
           building with the PKGBUILD script (see [#1233](https://github.com/bit-team/backintime/issues/1233))
           and required to edit the PKGBUILD file for a successful installation
           (see description in [#921](https://github.com/bit-team/backintime/issues/921#issuecomment-1276888138)).

    # You need to import a public key once before installing
    gpg --keyserver pgp.mit.edu --recv-keys 615F366D944B4826
    # Fingerprint: 3E70 692E E3DB 8BDD A599  1C90 615F 366D 944B 4826

    wget https://aur.archlinux.org/cgit/aur.git/snapshot/backintime.tar.gz
    tar xvzf backintime.tar.gz
    cd backintime
    makepkg -srci

An alternative way of installation [clones the AUR package](https://averagelinuxuser.com/install-aur-manually-helpers/) which has the
advantage to use `git pull` instead of downloading `backintime.tar.gz`
to be prepared to build an updated version of the package:

    git clone https://aur.archlinux.org/backintime.git
    # Optional: Edit PKGBUILD to comment the `make test` line for the first-time installation of version 1.3.2 or less
    cd backintime
    makepkg -si

### From sources

The dependencies are based on Ubuntu. Please [open an Issue](https://github.com/bit-team/backintime/issues/new/choose)
if something is missing. If you use another GNU/Linux distribution, please install the corresponding packages.

#### Common (command line tool)

* Build dependencies

  To build and install _Back In Time_ from the source code install these packages (together with the run-time dependencies):
  - `build-essential`
  - `gzip`
  - `gettext`
  - `python3-pyfakefs` (since Ubuntu 22.04) or via `python3 -m pip pyfakefs` - required for a unit test

* Runtime dependencies
    - `python3` (>= 3.6)
    - `rsync`
    - `cron-daemon`
    - `openssh-client`
    - `python3-keyring`
    - `python3-dbus`
    - `python3-packaging`

* Recommended
    - `sshfs`
    - `encfs`

* Commands to build and install
        cd common
        ./configure
        make
        make test
        sudo make install

#### Qt5 GUI

* Build dependencies
  
  See above...

* Runtime dependencies
    - `x11-utils`
    - `python3-pyqt5`
    - `python3-dbus.mainloop.pyqt5`
    - `qtwayland5` (if Wayland is used as display server instead of X11)
    - `libnotify-bin`
    - `policykit-1`
    - `backintime-common` (installed with `sudo make install` after building it)

* Recommended
    - For SSH key storage **one** of these packages
      - `python3-secretstorage`
      - `python3-keyring-kwallet`
      - `python3-gnomekeyring`
    - For diff-like comparing files between backup snapshots **one** of these packages
      - `kompare`
      - `meld`

* Commands to build and install

        cd qt
        ./configure
        make
        sudo make install

#### Options for `configure`

You can use optional arguments to `./configure` for creating a Makefile.
See `common/configure --help` and `qt/configure --help` for details.

## Contribute
### Resources
 - [Mailing list _bit-dev_](https://mail.python.org/mailman3/lists/bit-dev.python.org/) for development related topics
 - [Source code documentation for developers](https://backintime-dev.readthedocs.org)
 - [Translations](https://translations.launchpad.net/backintime) are done on a separate plattform
### Guidelines & Rules
The maintenance team will welcome all types of contributions. No contribution will be rejected
just because it doesn't fit to our quality standards, guidelines or rules. Every contribution
is reviewed and if needed will be improved together with the maintainers.

Please take the following best practices into account if possible (to reduce the work load of the maintainers):
 - Follow [PEP8](https://peps.python.org/pep-0008/) as a minimal Style Guide for Python Code
 - Follow [Google Style Guide](https://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html) for docstrings
 - Be careful when using automatic formatters like `black` and please mention the use of it when opening a Pull Request.
 - Run unittests before you open a Pull Request. You can run them via `make`-system with `cd common && ./configure && make && make test` or you can use `pytest`.
 - Try to create new unittests if appropriated. Use Pythons regular `unittest` instead of `pytest`.

<sub>November 2022</sub>
