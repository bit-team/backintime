#Back In Time

Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze

##About

Back In Time is a simple backup tool for Linux, inspired by "flyback project".

It provides a command line client 'backintime' and a Qt4 GUI 'backintime-qt4'
both written in Python3.

You only need to specify 3 things:
* where to save snapshots
* what folders to backup
* backup frequency (manual, every hour, every day, every month)

#####Credits

* Francisco Manuel García Claramonte: Spanish translation
* Michael Wiedmann: German translation
* Niklas Grahn: Swedish translation
* Vanja Cvelbar: Slovenian translation
* Michel Corps: French translation
* Tomáš Vadina: Slovak translation
* Paweł Hołuj: Polish translation
* Vadim Peretokin: Russian translation
* translators from [Launchpad](https://translations.launchpad.net/backintime/trunk/+pots/back-in-time)

##INSTALL

Back In Time is included in many distributions and can be installed from their 
repositories.

#####Ubuntu PPA

We provide a PPA (private package archive) with current stable version (ppa:bit-team/stable)
and a testing PPA (ppa:bit-team/testing)

    sudo add-apt-repository ppa:bit-team/stable
    sudo apt-get update
    sudo apt-get install backintime-qt4

#####Debian/Ubuntu make packages

    ./makedeb.sh
    sudo dpkg -i backintime-common-<version>.deb
    sudo dpkg -i backintime-qt4-<version>.deb

#####ArchLinux

Back In time is available through AUR. You need to import a public key once
before installing

    gpg --keyserver pgp.mit.edu --recv-keys 615F366D944B4826
    wget https://aur.archlinux.org/cgit/aur.git/snapshot/backintime.tar.gz
    tar xvzf backintime.tar.gz
    cd backintime
    makepkg -src
    sudo pacman -U backintime-<VERSION>.pkg.tar.xz

###From sources

#####Common

* dependencies
    - python3 (>= 3.3)
    - rsync
    - cron-daemon
    - openssh-client
    - python3-keyring
    - python3-dbus

* recomended
    - powermgmt-base
    - sshfs
    - encfs

* Command

        cd common
        ./configure
        make
        sudo make install


#####Qt4 GUI

* dependencies
    - x11-utils
    - python3-pyqt4
    - libnotify-bin
    - policykit-1
    - python3-dbus.mainloop.qt
    - backintime-common

* recomended
    - python3-secretstorage or
    - python3-keyring-kwallet or
    - python3-gnomekeyring
    - kompare or
    - meld

* Command

        cd qt4
        ./configure
        make
        sudo make install


##configure options

    first value is default:
    --fuse-group | --no-fuse-group (only COMMON)
        Some distributions require user to be in group 'fuse' to use
        sshfs and encfs. This toggles the check on or off.

    --python3 | --python (all)
        Use either 'python3' or 'python' to start Python Version 3.x


##Integrate with filemanager

#####Nautilus

You can make a simple Nautilus integration using nautilus-actions.
** Run System => Preferences => Nautilus Actions Configuration.
* Add a new action
    * Menu Item & Action tab:
        * Label: Open with Back In Time
        * Icon: gtk-save
        * Path: backintime
        * Parameters: %M
    * Conditions Tab:
        * Appears is selection contains: Both
* Press OK and you will see the new actions called "Open with Back In Time" when you right-click an item

<sub>Oct 2015</sub>

