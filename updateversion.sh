#!/bin/bash
# SPDX-FileCopyrightText: © 2008 Oprea Dan
# SPDX-FileCopyrightText: © 2012 Germar Reitze
# SPDX-FileCopyrightText: © 2022 Jürgen Altfeld (aryoda)
# SPDX-FileCopyrightText: © 2023 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.

# Updates all version numbers using the VERSION file
# and creates a new DEBIAN changelog file for this version
# by extracting the changes of this version from the
# CHANGES file.
#
# Development notes (May '23, Buhtz):
# Should be treated as a workaround that will get replaced in the future.
# Handling of version numbers and other package metadata can be done very
# elegant and centralized within the Python Packaging process (e.g. using
# pyproject.toml and additional tools.
# Handling of Debian (and PPA) related stuff will be separated from that
# upstream repo because it is distro specific.

# Outdated TODOs:
# TODO Requires refactoring and adjustments to separate
#      - the update of version numbers
#      - from the preparation of a new DEBIAN package release
#      since version updates must be possible without
#      a DEBIAN package release.
#
# TODO The version number must still be maintained in two places
#      (despite this script):
#      1. File "VERSION"
#      2. As headline in the file "CHANGES"
#      If those two numbers do not match the script does
#      not extract the correct changes of the version from the CHANGES file.
#
# TODO The name of this script file is misleading (find a better one)
# TODO Make sure this script works idempotent (multiple calls = same result)
# TODO This script does not update release dates scattered around in
#      different files (eg. common/man/C/backintime.1 line 1)
VERSION=`cat VERSION`
VERSION_WITHOUT_BRANCH=$VERSION

if [[ $VERSION == *-dev ]]
then
    VERSION+="."`git rev-parse --short HEAD`
fi

echo VERSION: $VERSION
echo VERSION_WITHOUT_BRANCH: $VERSION_WITHOUT_BRANCH

# MAINTAINER="Germar Reitze <germar.reitze@gmail.com>"
# MAINTAINER="BIT Team <dan@le-web.org>"
MAINTAINER="BIT Team <bit-dev@python.org>"

update_app_version () {
  echo "Update '$1'"
  sed --expression="s/^\(\s*\)__version__ = '.*'$/\1__version__ = '$VERSION'/" --in-place $1
}
update_app_version common/version.py
