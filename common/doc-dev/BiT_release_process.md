# How to prepare and publish a new BiT release


## Overview

A release is prepared like a feature by
using a "feature" branch and sending a pull request asking for a review.

- Source branch: `dev`
- Target branch for the pull request: `dev`



## Preconditions for a new release

- Developers agreed on the new version number.
- Most-recent translations were merged into `dev` branch. See the [localization documentation](2_localization.md).
- Full CI build pipeline matrix is activate (see [#1529](https://github.com/bit-team/backintime/issues/1529)).
- `dev` version was tested (CLI in `common` and GUI in `qt`) and testers/developers agreed on "readiness to be released".


## TLDR ;-)

- Create a new branch in your clone for the new release candidate.
- Update `VERSION` file.
- Update `CHANGES` file.
- Execute the script `./updateversion.sh` to update the version numbers (based on `VERSION` file) in several files.
- Update the "as at" date in the man page files `backintime.1` and `backintime-askpass.1`.
- Autogenerate and update the man page file `backintime-config.1` by executing the script `common/create-manapge-backintime-config.py`.
- Update `README.md` file.
- Run `codespell` to check for common spelling errors.
- Commit the changes.
- Open a new pull request (PR) for review by other developers.

When the PR is merged:
- Create a new tar archive (eg. `backintime-1.4.0.tar.gz`) with `./make-tarball.sh`.
- Create a new release in Github (attaching above tar archive).
- Update `VERSION` and `CHANGES` for the `dev` branch.


## Step by step

- Announce code freeze on `dev` branch to all active developers via email.

- Check that Travis CI did successfully build the latest `dev` branch commit:
 
  https://app.travis-ci.com/github/bit-team/backintime

- Pull latest `dev` branch changes into your BiT repo clone's `dev` branch:
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

- **Recommended:** Use a linter like [`pylint`](https://pypi.org/project/pylint/) to identify code errors that are not obvious but
  may be found only (too late) at run-time, eg. object name typos (see e.g. [#1553](https://github.com/bit-team/backintime/issues/1553)).
  
  *Note:* Since v1.4.x there is a unit test `test_lint.py` which performs
          a minimal check for severe problems via `make test`.

- Update the `CHANGES` text file in the project's root folder:

  - Check `git log` to find and add forgotten but relevant entries for `CHANGES`, eg.
    using the tag of the previous release:
  
    `git log v1.4.0..HEAD`

  - Rename the top-most line with the collected `dev` changes from eg.
  
    `Version 1.3.4-dev (development of upcoming release)`
  
    into
  
    `Version 1.4.0 (2023-09-14)`
  
  using the new version number and release date.

- Update `VERSION` text file in the project's root folder:

  Set the new version number **without** the release date (eg. `1.4.0`)

- Execute the script `./updateversion.sh` in the project's root folder
  to automatically update the version number in multiple files
  using the version number from the `VERSION` file
  (so you do not forget to update one file ;-).

  - BiT CLI config in `common/config.py`
  - Sphinx config in `common/doc-dev/conf.py`
  - man pages in `common/man/C/backintime*.1` and `qt/man/C/backintime*.1`
  - changelog to build a debian package in `debian/changelog`
    (this will be deprecated once we give up or separate the packaging for distros)

- Check that the version numbers have been update by opening some of the above files.

- Update the "as at" date in the man page files (in `common/man/C/backintime*.1` and `qt/man/C/backintime*.1`) manually by changing
  the month and year in the first line that looks like this:

  ```
  .TH backintime-config 1 "Aug 2023" "version 1.4.0" "USER COMMANDS"
  ```

- Optional: Search for all "copyright" strings in the code to update the year and add missing major contributors

  Eg.:
  - common/config.py

  There is also script `updatecopyright.sh` in the project's root folder
  which updates the copyright dates in all files but this script
  needs an overhaul to be able to insert new contributors too...

- Update the `AUTHORS` file in the project's root folder

  - Should be done during development normally
  - Ask contributors for explicit permission to publish their
    name and email address!

- Review and update the `README.md` in your release candidate branch

  - Copyright: Names and year
  - Update the **Known Problems and Workarounds** section:
    - Move fixed major known problems
      from the "Known Problems and Workarounds" section
      (which describes the latest release)
      into the "Problems in Versions older than the latest stable release"
      to stay visible for users of older versions.
    - Remove old known problems if you are sure old BiT versions with this issue
      are unlikely to be used "in the wild" anymore.
    - Update table of contents (TOC) for the changed parts.
      You can eg. use https://github.com/derlin/bitdowntoc to generate a TOC and
      copy the changed parts into the `README.md`.

- Build the prepared release candidate and execute the unit tests:

  ```
  cd common
  ./configure
  make
  make test
  cd ../qt
  ./configure
  make
  ```

- Execute [`codespell`](https://pypi.org/project/codespell) in the repositories root folder to check for common spelling errors.

- Do a manual smoke and UAT ("user acceptance test") of the GUI.

- If you find bugs:

  - Open an issue.
  - Decide if you want to fix this in the release candidate.
  - If you fix it in the release candidate: Update the CHANGES file (add the issue number + description).
  - If you don't fix it (eg. too risky) and it is a HIGH bug:
    - Add the bug to the [Known Problems and Workarounds](https://github.com/bit-team/backintime#known-problems-and-workarounds)
      section of `README.md` (of the release candidate branch) and describe
      a workaround (if any).

- Commit and push, if no "show-stopping" bug exists.

  Note: To push your release candidate branch into a new remote branch use:
  ```
  git push --set-upstream origin <new branch name>  # eg. rc/v1.4.0
  ```

- Open a new pull request for your pushed release candidate branch:

  - Add all developers as reviewers.
  - Mention bugs (and status) discovered during preparation of the release candidate
    in the description.

- Fix review findings and push the changes again to update the pull request.

- Finally check the Travis CI status of the pull request (everything must be green).

- Once all the PR reviewer approved the PR do a squash-merge (= all changes are "squashed" into one commit)
  into the `dev` branch using a commit message like

  `Release candidate for v1.4.1 (Oct. 1, 2023)`

- Wait for the final Travis CI build on the `dev` branch and check
  if everything is OK to proceed with the release.

- Create the tarball archive files to be attached as "binaries" to the release:
  - Update the `dev` branch
    ```
    git switch dev
    git pull upstream dev
    ```
  - Create a new tar archive (eg. `backintime-1.4.0.tar.gz`) with `./make-tarball.sh`:
    The script will actually `git clone` the current branch
    into a new folder `../backintime-$VERSION` and then make an tar archive file
    using that new folder.
    Cloning into a new folder ensures that there are no left-over files inside the tar archive.

- Create a new release in Github (`Releases` button under `code`):
  - Tag in `dev` branch with version number, eg.: `v1.4.0`
  - Release title eg.: Back in Time 1.4.0 (Sept. 14, 2023)
  - Description: `# Changelog` + the relevant part of the CHANGES file
  - Check `Set as the latest release`
  - Attach binaries: Upload the generated tar archive (eg. `backintime-1.4.0.tar.gz`).
    In releases < 1.4.0 also the public key of Germar was attached (`*.asc` file)
    since it can be used to validate signed debian packages files (`backintime*.deb`).
    Since we neither have the private key of Germar nor do publish any `deb`
    packages via Ubuntu PPA anymore this is not required or helpful anymore.
  - Click on the "Publish release" button

- Start a new dev version by preparing a new PR

  ```
  git switch dev
  git pull upstream
  git checkout -b PR/v1.4.1-dev  # use a new minor version number
  ```

-  Increment the version number for the new dev version:

  - Update the `VERSION` text file in the project's root folder:

    Set the new version number by incrementing the last number
    and appending `-dev` (eg. `1.4.1-dev`)

  - Update the `CHANGES` text file in the project's root folder:

    Add a new top-most line with the new version number, eg.:
  
    `Version 1.4.1-dev (development of upcoming release)`

  - Execute the script `./updateversion.sh` in the project's root folder
    to automatically update the version number in  files
  
  - Edit `.travis.yml` to reduce the build matrix again
    (to save "build credits")

    Eg. re-enable the exclusion list:
  
    ```
    jobs:
      exclude:
        -  python: "3.9"
        -  python: "3.10"
    ```

- Check the "Known Problems and Workarounds" section of the `README.md`
  and make sure it is up-to-date

- Commit and push the changes and create a new pull request

  Commit and PR message, eg.: `Start of new dev version v1.4.1-dev`

- Optional: Request PR approval

- Squash-merge the PR into the `dev` branch

- Send an email to all developers
  - to announce "end of code freeze"
  - send a link to the github release
  - inform about unexpected (open) problems (if any)

- (Out of scope here): Update the Github milestones and the assigned issues



## Other noteworthy things

### "Read the docs" code documentation

The "Read the docs" site is automatically updated with every commit on the `dev` branch. See [Issue #1533](https://github.com/bit-team/backintime/pull/1533#issuecomment-1720897669) and the [_backintime-dev_ project](https://readthedocs.org/projects/backintime-dev) at Read the docs.


### Building `deb` package files

We do no longer maintain and publish `deb` package files.
To build your own `deb` file see:

https://github.com/bit-team/backintime/blob/dev/CONTRIBUTING.md#build-own-deb-file

<sub>November 2023</sub>