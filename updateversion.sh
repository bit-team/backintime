#!/bin/bash

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

if [[ $VERSION == *-dev ]]
then
    VERSION+="."`git rev-parse --short HEAD`
fi

echo VERSION: $VERSION

MAINTAINER="Germar Reitze <germar.reitze@gmail.com>"
# MAINTAINER="BIT Team <dan@le-web.org>"
# MAINTAINER="BIT Team <bit-dev@python.org>"

# update_sphinx_config () {
#   echo "Update '$1'"
#   sed -e "s/^\(\s*\)version = '.*'$/\1version = '$VERSION'/" \
#       -i $1
# }

update_app_version () {
  echo "Update '$1'"
  sed -e "s/^\(\s*\)__version__ = '.*'$/\1__version__ = '$VERSION'/" \
      -i $1
}

update_man_page () {
  echo "Update '$1'"
  sed -e "s/\.TH\(.*\)\"version\([^\"]*\)\"\(.*\)$/.TH\1\"version $VERSION\"\3/" \
      -i $1
}

update_omf () {
  echo "Update '$1'"
  sed -e "s/^\([ \]*\)<version\([^0-9]*\)\([^\"]*\)\(.*\)$/\1<version\2$VERSION\4/" \
      -i $1
}

# Extract all changelog lines of the specified version from the CHANGES file
# into the file given by the first argument ($1).
# This does only work if you strictly use the correct version headlines
# in the changes file:
# Version x.y.z and whatever you want # x.y.z must match $VERSION (from the VERSION file)
update_changelog () {
  echo "Update '$1'"
  echo "backintime ($VERSION) unstable; urgency=low" > $1
  # The following awk code extracts the changelog
  # starting from the "Version" headline of $VERSION
  # until the next "Version" headline
  # and create a new file with all the lines in between.
  cat CHANGES | awk 'BEGIN {ins=0} /^Version '$VERSION'/ && (ins == 0) {ins=1; next} /^Version [0-9.]+/ && (ins == 1) {exit 0} (ins == 1) {print "  "$0}' >> $1
  if [ $(cat $1 | wc -l) -eq 1 ]; then
      echo "  * TODO prepare next version" >> $1
  fi
  echo  " -- ${MAINTAINER}  $(date -R)" >> $1
}

update_app_version common/version.py

# Sphinx now ask "backintime" itself about its version
# update_sphinx_config common/doc-dev/conf.py

update_man_page common/man/C/backintime.1

update_man_page common/man/C/backintime-config.1

update_man_page common/man/C/backintime-askpass.1

update_man_page qt/man/C/backintime-qt.1

update_changelog debian/changelog
