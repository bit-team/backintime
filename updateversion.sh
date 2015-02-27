#!/bin/bash

VERSION=`cat VERSION`
echo VERSION: $VERSION

if [ "x$USER" = "xgermar" ]; then
    MAINTAINER="Germar Reitze <germar.reitze@gmail.com>"
else
    MAINTAINER="BIT Team <dan@le-web.org>"
fi

update_config () {
  echo "Update '$1'"
  sed -e "s/^\(\s*\)VERSION = '.*'$/\1VERSION = '$VERSION'/" \
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

update_xml () {
  echo "Update '$1'"
  sed -e "s/^<!ENTITY appversion .*>$/<!ENTITY appversion \"$VERSION\">/" \
      -e "s/^<!ENTITY manrevision .*>$/<!ENTITY manrevision \"$VERSION\">/" \
      -i $1
}

update_changelog () {
  echo "Update '$1'"
  echo "backintime ($VERSION) unstable; urgency=low" > $1
  cat CHANGES | awk 'BEGIN {ins=0} /^Version '$VERSION'/ {ins=1; next} /^Version [0-9.]+/ && (ins == 1) {exit 0} /^\*/ && (ins == 1) {print "  "$0}' >> $1
  if [ $(cat $1 | wc -l) -eq 1 ]; then
      echo "  * prepair next version" >> $1
  fi
  echo  " -- ${MAINTAINER}  $(date -R)" >> $1
}

update_config common/config.py

update_man_page common/man/C/backintime.1

update_man_page common/man/C/backintime-config.1

update_man_page common/man/C/backintime-askpass.1

update_man_page qt4/man/C/backintime-qt4.1

update_xml qt4/docbook/en/index.docbook

update_changelog debian/changelog

