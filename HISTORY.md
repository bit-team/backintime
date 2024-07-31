# Looking back in time at _Back In Time_

*by Michael Büker, 2024*

The history of the _Back In Time_ project, which at the time of this writing already spans nearly 16 years, is best understood in four periods:

1. The **First Era** from 2008 to 2012, releases 0.5 to ~1.0.12
2. The **Second Era** from 2012 to 2019, releases ~1.0.14 to 1.2
3. A **Dark Age** from 2019 to 2022, releases 1.2.0 to 1.3.2
4. The **Third Era** since 2022, since release 1.3.3

These periods correspond roughly to who was maintaining and developing _Back In Time_. Important technical and organizational changes happened at various moments in between.

For details, refer to [CHANGES](CHANGES).

## The First Era: 0.5 to ~1.0.12 (2008–2012)

### Maintenance

_Back In Time_ was created by **Oprea Dan** and first published on a private blog in late 2008 ([wayback link](https://web.archive.org/web/20081014041759/http://www.le-web.org/2008/10/03/back-in-time-version-05/)). Shortly thereafter, collaborative development started happening on Launchpad. Sometime around 2010, development and publication appears to have moved entirely to Launchpad, with the private blog being discontinued.

### Core functionality

At first, _Back In Time_ used `diff` to compare the latest snapshot with the source, in order to check if a new snapshot was necessary. If the answer was yes, it would use `cp` to create a new snapshot.

This was changed in version 0.9.2 in early 2009, when `diff` was replaced by `rsync` for the comparison. Copying was still done by `cp`, apparently without special permissions handling.

This changed when, shortly thereafter, version 0.9.24 introduced `fileinfo.bz2`, which holds permissions information on all files in a snapshot. Introduced to allow saving backups on non-Unix-permission-aware filesystems like NTFS, `fileinfo.bz2` is consulted upon restoring a file in order to recreate its original ownership and permissions.

### GUI

Initially, _Back In Time_ had only a GNOME GUI.

Version 0.9 from early 2009 separated the backend (`backintime-common`) from the GUI, allowing for different frontends. Over the course of 2009, finishing roughly with version 0.9.24, two separate frontends were completed: `backintime-gnome` and `backintime-kde4`.

## The Second Era: ~1.0.14 to 1.2 (2012–2019)

### Maintenance

Around 2012, **Germar Reitze** took over publication, maintenance and further development from Oprea Dan.

In early 2016, starting with version 1.1.10, development and publication moved to Microsoft GitHub, leaving the Launchpad project mostly abandoned (except for translation management and PPA publication).

### Core functionality
Development during the Second Era centered largely around remote backup capabilities.

In late 2012, version 1.0.12 introduced remote backup locations enabled by `ssh`.

In early 2013, version 1.0.22 introduced an optional "full rsync mode". This replaced `cp` with `rsync` for all operations, including full replication of permissions.

In late 2013, version 1.0.26 introduced encrypted backup locations enabled by `encfs`.

### GUI

In early 2015, version 1.1.0 eliminated the separate `backintime-gnome` and `backintime-kde4` frontends and introduced `backintime-qt4` as the only frontend.

## The Dark Age: 1.2.0 to 1.3.2 (2019–2022)
In 2019, version 1.2.0 was released. It was the first release since version 1.1.24 in late 2017 and contained many bugfixes accumulated over the previous 1.5 years.

Version 1.2.0 introduced a fundamental change: ***"make full-rsync mode default, remove the other mode"***. This meant that files would always be transferred by `rsync` instead of `cp`. Specifically, `rsync` was instructed to retain full ownership and permissions information when transferring the files to the backup (*in addition* to the information stored in `fileinfo.bz2`).

This caused bug [#988](https://github.com/bit-team/backintime/issues/988), which broke _Back In Time_'s core functionality for any backup created with version <1.2.0 (unless "full rsync mode" had been enabled): many unchanged files were no longer hardlinked upon transferring, but unnecessarily copied. This led to very long backup times and high disk usage. A related bug with a somewhat smaller impact is [#994](https://github.com/bit-team/backintime/issues/994).

As these bugs are currently understood, the underlying reason for the problem is differing ownership/permissions between the files in the source and on the backup drive. Since multiple hardlinks to the same file are, by definition, identical, they cannot have differing permissions. `rsync` fails to handle this case correctly when a new snapshot is created, leading to the files in question being copied unnecessarily.

With many users complaining and trading workarounds on Microsoft GitHub, development soon came to a halt. Some bugs were fixed with version 1.3.0 in 2021, but [#988](https://github.com/bit-team/backintime/issues/988) and [#994](https://github.com/bit-team/backintime/issues/994) remained.

## The Third Era: since 1.3.3 (since 2022)

In early 2022, an epic discussion on the state of the project arose in [#1232](https://github.com/bit-team/backintime/issues/1232). Many users declared their love for _Back In Time_, and a few were ready to step up and restart development. With help and permission from Germar Reitze, **Christian Buhtz**, **Jürgen Altfeld** and **Michael Büker** formed a new core team. The team first curated and triaged over 200 open issues that had accumulated since 2019.

The first release by the new team was version 1.3.3 in early 2023. Early work focused on ensuring compatibility with rsync 3.2.4, fixing keyring issues for SSH operations, system tray functionality in both X11 and Wayland as well as testing, coding style and other modernization to align _Back In Time_ with current Python practices.

### Core functionality

Work on fixing [#988](https://github.com/bit-team/backintime/issues/988) and [#994](https://github.com/bit-team/backintime/issues/994) is still ongoing as of this writing. These bugs are largely understood now, but any possible fix could potentially have grave consequences for existing backups, which have not been thoroughly tested for.

Given that EncFS suffers from known security issues and is not actively maintained, _Back In Time_ is preparing to deprecate it in the foreseeable future ([#1734](https://github.com/bit-team/backintime/issues/1734)).

### GUI

The GUI is slated for a redesign and code refactoring, as it has become complex and convoluted over the years.

A commonly requested feature is a terminal user interface (TUI), or an enhancement of the existing command-line interface (CLI), as discussed in [#254](https://github.com/bit-team/backintime/issues/254). The proposal for a web frontend was rejected ([#209](https://github.com/bit-team/backintime/issues/209)), but separate projects offering a web fronted would be supported.
