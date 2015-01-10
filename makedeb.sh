#!/bin/bash

PKGNAME=backintime
PKGVER=$(cat VERSION)
ARCH=all
TMP=$(mktemp -d)
CURRENT=$(pwd)

DST=${TMP}/${PKGNAME}_${PKGVER}/
mkdir ${DST}
cp -aR ${CURRENT}/* ${DST}
cd ${DST}

#debian: changelog
sed -e "s/\$VERSION/${PKGVER}/g" -e "s/\$RELEASE/source/g" -i debian/changelog

dpkg-buildpackage -us -uc

cd ..
cp *.deb ${CURRENT}
#rm -rf ${TMP}
