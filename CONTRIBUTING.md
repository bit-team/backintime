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
- [Resources](#resources)
- [Build & Install](#build--install)
  * [Dependencies](#dependencies)
  * [Build and install via `make` system
    (recommended)](#build-and-install-via-make-system-recommended)
  * [Build own `deb` file](#build-own-deb-file)
- [Testing](#testing)
- [Further reading](#further-reading)
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
   for Python Code
 - For docstrings follow [Google Style Guide](https://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html) 
   (see our own [HOWTO about doc generation](common/doc-dev/1_doc_maintenance_howto.md)).
 - Be careful when using automatic formatters like `black` and please mention
   the use of it when opening a pull request.
 - Run unit tests before you open a Pull Request. You can run them via
   `make`-system with `cd common && ./configure && make && make test` or you
   can use `pytest`. See section [Build and install via `make` system](#build-and-install-via-make-system-recommended) for further details.
 - Try to create new unit tests if appropriated. Use Pythons regular `unittest`
   instead of `pytest`. If you know the difference please try follow the
   _Classical (aka Detroit) school_ instead of _London (aka mockist) school_.

# Resources

 - [Mailing list _bit-dev_](https://mail.python.org/mailman3/lists/bit-dev.python.org/) for development related topics
 - [Source code documentation for developers](https://backintime-dev.readthedocs.org)
 - [Translations](https://translate.codeberg.org/engage/backintime) are done on a separate platform
 - [HowTo's and maintenance documents](common/doc-dev/README.md)

# Build & Install

This section describes how to build and install _Back In Time_ in preparation
of your own contributions. It is assumed that you `git clone` this repository
first.

## Dependencies

The following dependencies are based on Ubuntu. Please [open an
Issue](https://github.com/bit-team/backintime/issues/new/choose) if something
is missing. If you use another GNU/Linux distribution, please install the
corresponding packages. Be aware that some of the named packages can be
replaced with PyPi packages.

* Runtime dependencies for the CLI

  - `python3` (>= 3.8)
  - `rsync`
  - `cron-daemon`
  - `openssh-client`
  - `python3-keyring`
  - `python3-dbus`
  - `python3-packaging`
  -  Recommended
     - `sshfs`
     - `encfs`

* Runtime dependencies for the GUI

  - `x11-utils`
  - `python3-pyqt6`
  - `python3-dbus.mainloop.pyqt6`
  - `libnotify-bin`
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
  - `python3-pyfakefs`
  - `pylint`

## Build and install via `make` system (recommended)

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

## Build own `deb` file

1. Run `./makedeb.sh` in the repositories root directory.
2. Two `deb` files are built and places in the repositories parent directory.
3. Install the packages
  - `sudo dpkg -i ../backintime-common-<version>.deb`
  - `sudo dpkg -i ../backintime-qt-<version>.deb`

# Testing
> [!IMPORTANT]
> Remember to **manually** test _Back In Time_ and not rely solely on
> the automatic test suite.

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

# Further reading
- https://www.contribution-guide.org
- https://mozillascience.github.io/working-open-workshop/contributing

## Licensing of contributed material
Keep in mind as you contribute, that code, docs and other material submitted
to the project are considered licensed under the same terms (see
[LICENSE](LICENSE)) as the rest of the work.

<sub>April 2024</sub>
