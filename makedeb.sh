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

dpkg-buildpackage -us -uc

cd ..
cp *.deb ${CURRENT}
#rm -rf ${TMP}
