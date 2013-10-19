#!/bin/bash

VERSION=`cat VERSION`
echo VERSION: $VERSION

echo "Update 'common/debian_specific/control'"
sed -i -e "s/^Version: .*$/Version: $VERSION/" common/debian_specific/control

echo "Update 'gnome/debian_specific/control'"
sed -i -e "s/^Version: .*$/Version: $VERSION/" -e "s/backintime-common (>= [^)]*)/backintime-common (>= $VERSION~)/" gnome/debian_specific/control
sed -i -e "s/^Version: .*$/Version: $VERSION/" -e "s/backintime-notify (>= [^)]*)/backintime-notify (>= $VERSION~)/" gnome/debian_specific/control

echo "Update 'kde4/debian_specific/control'"
sed -i -e "s/^Version: .*$/Version: $VERSION/" -e "s/backintime-common (>= [^)]*)/backintime-common (>= $VERSION~)/" kde4/debian_specific/control
sed -i -e "s/^Version: .*$/Version: $VERSION/" -e "s/backintime-notify (>= [^)]*)/backintime-notify (>= $VERSION~)/" kde4/debian_specific/control

echo "Update 'notify/debian_specific/control'"
sed -i -e "s/^Version: .*$/Version: $VERSION/" -e "s/backintime-common (>= [^)]*)/backintime-common (>= $VERSION~)/" notify/debian_specific/control

echo "Update 'common/config.py'"
sed -i -e "s/^    VERSION = '.*'$/    VERSION = '$VERSION'/" common/config.py

echo "Update common man page"
FILE=common/man/C/backintime.1
sed -i -e "s/\.TH\(.*\)\"version\([^\"]*\)\"\(.*\)$/.TH\1\"version $VERSION\"\3/" $FILE

echo "Update config man page"
FILE=common/man/C/backintime-config.1
sed -i -e "s/\.TH\(.*\)\"version\([^\"]*\)\"\(.*\)$/.TH\1\"version $VERSION\"\3/" $FILE

echo "Update Gnome man page"
FILE=gnome/man/C/backintime-gnome.1
sed -i -e "s/\.TH\(.*\)\"version\([^\"]*\)\"\(.*\)$/.TH\1\"version $VERSION\"\3/" $FILE

echo "Update KDE4 man page"
FILE=kde4/man/C/backintime-kde4.1
sed -i -e "s/\.TH\(.*\)\"version\([^\"]*\)\"\(.*\)$/.TH\1\"version $VERSION\"\3/" $FILE

echo "Update help .omf file"
sed -i -e "s/^\([ \]*\)<version\([^0-9]*\)\([^\"]*\)\(.*\)$/\1<version\2$VERSION\4/" gnome/docbook/C/backintime-C.omf

echo "Update GNOME help docbook file"
sed -i -e "s/^<!ENTITY appversion .*>$/<!ENTITY appversion \"$VERSION\">/" -e "s/^<!ENTITY manrevision .*>$/<!ENTITY manrevision \"$VERSION\">/" gnome/docbook/C/backintime.xml

echo "Update KDE4 help docbook file"
sed -i -e "s/^<!ENTITY appversion .*>$/<!ENTITY appversion \"$VERSION\">/" -e "s/^<!ENTITY manrevision .*>$/<!ENTITY manrevision \"$VERSION\">/" kde4/docbook/en/index.docbook

echo "Update Debian changelog"
echo '$BACKINTIME ($VERSION~$RELEASE) $RELEASE; urgency=low' > common/debian_specific/changelog
cat CHANGES | awk 'BEGIN {ins=0} /^Version '$VERSION'/ {ins=1; next} /^Version [0-9.]+/ && (ins == 1) {exit 0} /^\*/ && (ins == 1) {print "  "$0}' >> common/debian_specific/changelog
echo  "-- BIT Team <dan@le-web.org>  $(date -R)" >> common/debian_specific/changelog
