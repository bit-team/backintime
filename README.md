# Back In Time

Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze, Taylor Raack

[![Build Status](https://travis-ci.org/bit-team/backintime.svg?branch=master)](https://travis-ci.org/bit-team/backintime)
[![Coverage Status](https://coveralls.io/repos/github/bit-team/backintime/badge.svg?branch=master)](https://coveralls.io/github/bit-team/backintime?branch=master)
[![Documentation Status](https://readthedocs.org/projects/backintime-dev/badge/?version=latest)](http://backintime.readthedocs.org/projects/backintime-dev/en/latest/?badge=latest)

## About

Back In Time is a simple backup tool for Linux, inspired by "flyback project".

It provides a command line tool 'backintime' and a Qt5 GUI 'backintime-qt'
both written in Python3.

You only need to specify 3 things:

* what folders to back up
* where to save snapshots
* backup frequency (manual, every hour, every day, every month)


## Index

* [Documentation](#documentation)
* [Support](#support)
* [Known Problems and Workarounds](#known-problems-and-workarounds)
* [Download](#download)
* [Installation](#installation)
* [News Feed](#newsfeed)
* [Contribute](#contribute)



## Documentation

The documentation is currently under development in https://backintime.readthedocs.org/

## Support

Please ask questions and report bug on
https://github.com/bit-team/backintime/issues

## Known Problems and Workarounds

#### Development / Maintainment status

The development of this project has been dormant for a while,
but a small team has started to get things moving again.
Stick with us, we all love Back In Time :)

We are currently trying to fix the major issues while not implementing
new features to prepare a new stable release.

If you are interested in the development, have a look below under [`Contribute`](#Contribute).

#### Incompatibility with rsync >= 3.2.4

Back In Time is currently incompatible with rsync >= 3.2.4.

If you use rsync >= 3.2.4, you can use one of two workarounds:

1. add "--old-args" in "Expert Options / Additional options to rsync" **or**
2. modify /usr/bin/backintime to include `export RSYNC_OLD_ARGS=1`.

Note that Manjaro has included the `export RSYNC_OLD_ARGS=1` workaround in their official 1.3.2-2 version of the package.

#### File permissions handling and therefore possible non-differential backups

In version 1.2.0, the handling of file permissions changed.

In versions <= 1.1.24 (until 2017) all file permissions were set to -rw-r--r-- in the backup target.

In versions >= 1.2.0 (since 2019) rsync is executed with --perms option which tells rsync to preserve the source file
permission.
As a consequence backups can be larger and slower, especially the first backup after upgrading to a version >= 1.2.0.

If you don't like the new behaviour, you can use "Expert Options" -> "Paste additional options to rsync" -> "--no-perms
--no-group --no-owner".
Note that the exact file permissions can still be found in the file fileinfo.bz2 and are also considered when restoring
files.

#### Python 3.10 compatibility and Ubuntu version

backintime versions older than 1.3.2 do not start with Python >= 3.10.

Ubuntu 22.04 LTS ships with Python 3.10 and backintime 1.2.1, but has applied [a patch](https://bugs.launchpad.net/ubuntu/+source/backintime/+bug/1976164/+attachment/5593556/+files/backintime_1.2.1-3_1.2.1-3ubuntu0.1.diff) to make it work.

If you want to update to backintime 1.3.2 in Ubuntu, you may use the PPA: see under [`INSTALL/Ubuntu PPA`](#Ubuntu-PPA).


#### Non-working password safe / BiT forgets passwords (`keyring` backend issues)

`Back in Time` does only support selected "known-good" backends
to set and query passwords from a user-session password safe by
using the [keyring](https://github.com/jaraco/keyring) library.

This may require manual configuration via a configuration file until there is eg. a settings GUI for this.

Symptoms are DEBUG log output (with the command line argument `--debug`) like:

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


## Download

Please find the latest versions on
https://github.com/bit-team/backintime/releases/latest

## Installation

Back In Time is included in many distributions and can be installed from their
repositories.

### From distribution packages

##### Ubuntu PPA

We provide a PPA (Private Package Archive) with current stable version
(ppa:bit-team/stable) and a testing PPA (ppa:bit-team/testing)

**Important:** Until version 1.3.2 there was a bug that caused
`backintime` failed to start if the package `backintime-qt` was not installed.
As work-around also install `backintime-qt` because the missing
Udev `serviceHelper` system D-Bus daemon is packaged there.

    sudo add-apt-repository ppa:bit-team/stable
    sudo apt-get update
    sudo apt-get install backintime-qt

or

    sudo add-apt-repository ppa:bit-team/testing
    sudo apt-get update
    sudo apt-get install backintime-qt

##### Debian/Ubuntu make packages

    ./makedeb.sh
    sudo dpkg -i ../backintime-common-<version>.deb
    sudo dpkg -i ../backintime-qt-<version>.deb

##### ArchLinux

Back In Time is available through the AUR package [`backintime`](https://aur.archlinux.org/packages/backintime)
that also includes the GUI (`backintime-qt`).

**Important:** Until version 1.3.2 there was a bug that prevented the
           successful **first-time** installation due to a unit test failure when
           building with the PKGBUILD script (see [#1233](https://github.com/bit-team/backintime/issues/1233))
           and required to edit the PKGBUILD file for a sucessful installation
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

To build and install from the source code do a `git clone https://github.com/bit-team/backintime.git`
on your computer and install the required dependencies before `make`ing.

The dependencies are described for Ubuntu here.
If you use another Linux distribution please install the corresponding packages.

##### Common (command line tool)

* dependencies
    - python3 (>= 3.3)
    - rsync
    - cron-daemon
    - openssh-client
    - python3-keyring
    - python3-dbus
    - python3-packaging

* recomended
    - sshfs
    - encfs

* Command

        cd common
        ./configure
        make
        make test
        sudo make install

##### Qt5 GUI

* dependencies
    - x11-utils
    - python3-pyqt5
    - libnotify-bin
    - policykit-1
    - python3-dbus.mainloop.pyqt5
    - backintime-common

* recomended
    - python3-secretstorage or
    - python3-keyring-kwallet or
    - python3-gnomekeyring
    - kompare or
    - meld

* Command

        cd qt
        ./configure
        make
        sudo make install

#### configure options

You can use these optional arguments to `./configure` for creating a Makefile:

    --no-fuse-group | --fuse-group (only COMMON)
        Some distributions require user to be in group 'fuse' to use
        sshfs and encfs. This toggles the check on or off.

    --python3 | --python (all)
        Use either 'python3' or 'python' to start Python Version 3.x

Note: The first value is default.

See also `common/configure --help?` and `qt/configure --help`


## NewsFeed

Back In Time has a RSS feed
https://feeds.launchpad.net/backintime/announcements.atom

## Contribute

There is a mailing list for people who want to contribute to the development:
https://mail.python.org/mailman3/lists/bit-dev.python.org/

There is a dev-docu on https://backintime-dev.readthedocs.org
It's not complete yet but I'm working on it. If you'd like to contribute
please add docstrings following the
[Google style guide](https://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html)
and add unit-tests for new methods in common. To run unit-test locally you can
run `cd common && ./configure && make && make test`

<sub>December 2016</sub>
