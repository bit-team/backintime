<!--
SPDX-FileCopyrightText: © 2022 Jürgen Altfeld (aryoda)
SPDX-FileCopyrightText: © 2023 Christian Buhtz <c.buhtz@posteo.jp>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See directory LICENSES or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# How to prepare and publish a new BIT release
<sub>August 2024</sub>

## Overview

A release is prepared like a feature by
using a "feature" branch and sending a pull request asking for a review.

- Source branch: `dev`
- Target branch for the pull request: `dev`

## Table of content

- [Preconditions for a new release](#preconditions-for-a-new-release)
- [TLDR ;-)](#tldr--)
- [Step by step](#step-by-step)
   * [Create branch for release candidate](#create-branch-for-release-candidate)
   * [Bump version number](#bump-version-number)
   * [Testing & Miscellaneous](#testing--miscellaneous)
   * [Release Candidate](#release-candidate)
   * [Create Release](#create-release)
   * [Prepare new development version](#prepare-new-development-version)
- [Manual testing - Recommendations](#manual-testing---recommendations)
- [Other noteworthy things](#other-noteworthy-things)
   * ["Read the docs" code documentation](#read-the-docs-code-documentation)
   * [Building `deb` package files](#building-deb-package-files)


## Preconditions for a new release

- Developers agreed on the new version number.
- Most-recent translations were merged into `dev` branch. See the [localization documentation](2_localization.md).
- Full CI build pipeline matrix is activate (see
  [#1529](https://github.com/bit-team/backintime/issues/1529)). This is related
  to the Python versions and also to the Ubuntu Distro versions.
- `dev` version was tested (CLI in `common` and GUI in `qt`) and testers/developers agreed on "readiness to be released".


## TLDR ;-)

- Make sure we have sufficient _Credits_ to run _TravisCI_. Otherwise contact
  their support and kindly ask for new OSS credits.
- Create a new branch in your clone for the new release candidate.
- Update `VERSION` file.
- Update `CHANGES` file.
- Execute the script `./updateversion.sh` to update the version numbers (based on `VERSION` file) in several files.
- Update the "as at" date in the man page files `backintime.1` and `backintime-askpass.1`.
- Autogenerate and update the man page file `backintime-config.1` by executing the script `common/create-manapge-backintime-config.py`.
  - Validate the content of the created man page. For example compared it to a
    previous version of the man page.
  - Create a plain text file from the man pages: `man <man-file> | col -b >
    man.plain.txt`
  - Use `git diff` (or another diff tool) to compare them and see if the
    content is as expected.
- Update `README.md` file.
- Run `codespell` to check for common spelling errors.
- Commit the changes.
- Open a new pull request (PR) for review by other developers.

When the PR is merged:
- Create a new tar archive (eg. `backintime-1.4.0.tar.gz`) with `./make-tarball.sh`.
- Create a new release in Github (attaching above tar archive).
- Update `VERSION` and `CHANGES` for the `dev` branch.


## Step by step

### Create branch for release candidate

- Announce code freeze on `dev` branch to all active developers via email.

- Check that [Travis CI](https://app.travis-ci.com/github/bit-team/backintime)
  did successfully build the latest `dev` branch commit.

- Pull latest `dev` branch changes into your BIT repo clone's `dev` branch:
  ```
  git switch dev
  git pull upstream dev
  ```

- Create a release candidate branch in your clone using the new version number:
  ```
  git checkout -b rc/v1.4.0
  ```

- Enable the full build matrix in Travis CI (Python version * arch[icture])
  by commenting the excluded architectures:
    ```
    jobs:
      # exclude:
      #   -  python: "3.9"
      #   -  python: "3.10"
    ```

- Build the still unchanged release candidate and execute the unit tests:
  ```
  cd common
  ./configure
  make
  make test
  cd ../qt
  ./configure
  make
  ```

### Bump version number

- Update the changelog file `CHANGES` in the project's root folder:

  - Check the commit history about forgotten but relevant entries that are
    currently not present in `CHANGES` file. e.g. `git log v1.4.0..HEAD`

  - Rename the top-most line with the collected `dev` changes from eg.

    `Version 1.3.4-dev (development of upcoming release)`

    into

    `Version 1.4.0 (2023-09-14)`

  using the new version number and release date.

- Update `VERSION` text file in the project's root folder and set the new
  version number **without** the release date (eg. `1.4.0`).

- Execute the script `./updateversion.sh` in the project's root folder
  to automatically update the version number in multiple files
  using the version number from the `VERSION` file
  (so you do not forget to update one file ;-). The script should modify the
  following files:

  - `common/version.py`
  - `common/man/C/backintime*.1`
  - `qt/man/C/backintime*.1`

- Check that the version numbers have been update by opening some of the above
  files.

- Update the "as at" date in the man page files (in
  `common/man/C/backintime*.1` and `qt/man/C/backintime*.1`) manually by
  changing the month and year in the first line that looks like this:

  ```
  .TH backintime-config 1 "Aug 2023" "version 1.4.0" "USER COMMANDS"
  ```

- Update the `AUTHORS` file in the project's root folder if necessary.
  Do not publish contributors names and email address without their permission.

### Testing & Miscellaneous

- Review and update the `README.md` in your release candidate branch

  - Update the **Known Problems and Workarounds** section:
    - Move fixed major known problems from the "Known Problems and Workarounds"
      section (which describes the latest release) into the "Problems in
      Versions older than the latest stable release" to stay visible for users
      of older versions.
    - Remove old known problems if you are sure old BIT versions with this
      issue are unlikely to be used "in the wild" anymore.
    - Update table of contents (TOC) for the changed parts. You can eg. use
      https://derlin.github.io/bitdowntoc/ to generate a TOC and copy the
      changed parts into the `README.md`.

- Build, install and [test (again!)](#manual-testing---recommendations)
  the prepared release candidate.

- Run [`codespell`](https://pypi.org/project/codespell) in the repositories
  root folder to check for common spelling errors.

- Do a [manual smoke and UAT ("user acceptance test")](#manual-testing---recommendations)
  of the GUI. Create snapshot profiles in all (four) available flavors. Create
  snapshots. Restore snapshots. Delete snapshots.
  
- Did you really perform the previous
  [test](#manual-testing---recommendations)? Don't dodge the question! :D

- If you find bugs:

  - Open an issue.
  - Decide if you want to fix this in the release candidate:
    - If yes: Fix it in the release candidate: Update the `CHANGES` file (add
       the issue number + description).
    - If no: Don't fix it (eg. too risky) but add the bug to the
      [Known Problems and Workarounds](https://github.com/bit-team/backintime#known-problems-and-workarounds)
      section of `README.md` (of the release candidate branch) and describe a
      workaround (if any).

### Release Candidate

- Commit and push, if no "show-stopping" bug exists.

  Note: To push your release candidate branch into a new remote branch use:
  ```
  git push --set-upstream origin <new branch name>  # eg. rc/v1.4.0
  ```

- Open a new pull request for your pushed release candidate branch:

  - Add all developers as reviewers.
  - Mention bugs (and status) discovered during preparation of the release
    candidate in the description.

- Fix review findings and push the changes again to update the pull request.

- Finally check the Travis CI status of the pull request (everything must be
  green).

- Once all the PR reviewer approved the PR do a squash-merge into the `dev`
  branch using a commit message like `Release candidate for v1.4.1 (Oct. 1,
  2023)`.

- Wait for the final Travis CI build on the `dev` branch and check
  if everything is OK to proceed with the release.

### Create Release

- Create the tarball archive files to be attached as "binaries" to the release:
  - Update the `dev` branch
    ```
    git switch dev
    git pull upstream dev
    ```
  - Create a new tar archive (eg. `backintime-1.4.0.tar.gz`) with
    `./make-tarball.sh`: The script will `git clone` the current branch into a
    folder `../backintime-$VERSION` and then make a tar archive file from it.
  - Test this tarball via installing it, e.g. on a virtual machine.

- Create a new release in Github (`Releases` button under `code`):
  - Tag in `dev` branch with version number, eg.: `v1.4.0` (don't forget the
    prefix `v`)
  - Release title eg.: _Back In Time 1.4.0 (Sept. 14, 2023)_
  - Description: `# Changelog` + the relevant (not necessary all) parts of the
    `CHANGES` file.
  - Don't forget to mention and honer the exter contributors if there are any.
  - Check `Set as the latest release`.
  - Attach binaries: Upload the generated tar archive
    (eg. `backintime-1.4.0.tar.gz`).
  - Click on the "Publish release" button

### Prepare new development version

- Start a new dev version by preparing a new PR

  ```
  git switch dev
  git pull upstream
  git checkout -b PR/v1.4.1-dev  # use a new minor version number
  ```

-  Increment the version number for the new dev version:

  - Update the `VERSION` text file in the project's root folder.
    Set the new version number by incrementing the last number
    and appending `-dev` (eg. `1.4.1-dev`).

  - Execute `./updateversion.sh` in the project's root folder
    to automatically update the version number in files.

  - Update the `CHANGES` text file in the project's root folder. 
    Add a new top-most line with the new version number, eg.:

    `Version 1.4.1-dev (development of upcoming release)`

  - Edit `.travis.yml` to reduce the build matrix again
    (to save "build credits"). e.g. re-enable the exclusion list:

    ```
    jobs:
      exclude:
        -  python: "3.9"
        -  python: "3.10"
    ```

- Check the "Known Problems and Workarounds" section of the `README.md`
  and make sure it is up-to-date.

- Commit and push the changes. Create a new pull request with commit and PR
  message like `Start of new dev version v1.4.1-dev`.

- Optional: Request PR approval

- After approval or creative cool down squash-merge the PR into the `dev`
  branch.

- Send an email to all developers
  - to announce "end of code freeze"
  - send a link to the github release
  - inform about unexpected (open) problems (if any)

- (Out of scope here): Update the Github milestones and the assigned issues


## Manual testing - Recommendations
Automatic tests won't cover all scenarios and possible problems. There is a high
need to run _Back In Time_ and perform several actions to make sure it works as
expected. The following list suggests several actions and scenarios.

- If available, prefer installing from the source tarball over the git
  repository.
- Use a fresh and clean virtual machine without a previous version of _Back In
  Time_ installed.
- GNU/Linux distribution: Both major lines _Debian GNU/Linux_ and _Arch Linux_
  or distros based on them. Additionally use a none-systemd distro like _Devuan
  GNU/Linux_.
- Run _Back In Time_ and perform the following actions as user and as root.
- Always start from terminal to catch silent errors and warnings.
- Create snapshot profils in all available flavors (Local, SSH, with and
  without encryption).
- Run the snapshots.
- Restore snapshots.
- Delete snapshots.
- Schedule the snapshots using regular cron (e.g. _Every 5 minutes_) and
  anacron-like cron (_Repeatedly (anacran)_). Additionally schedule with udev
  (_When drive gets connected (udev)_).

## Other noteworthy things

### Gather author information from git repository

List all (commit) authors since the last version (tag `1.5.2` in this example):

    git log v1.5.2..HEAD --format='%an' | sort | uniq

Show log entries of a specific author since the last release:

    git log v1.5.2..HEAD --author="buhtz"

Show `diff` of log entries of a specific author since the last release:

    git log v1.5.2..HEAD --author="buhtz" -p
    
Show `diff` of a specific commit compared to its previous commit:

    git diff <commit-hash>^ <commit-hash>

### "Read the docs" code documentation

The "Read the docs" site is automatically updated with every commit on the
`dev` branch. See
[Issue #1533](https://github.com/bit-team/backintime/pull/1533#issuecomment-1720897669)
and the
[_backintime-dev_project](https://readthedocs.org/projects/backintime-dev)
at Read The docs.

