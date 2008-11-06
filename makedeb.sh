#!/bin/bash

PKGNAME=`cat control | grep "Package:" | cut -d" " -f2`
PKGVER=`cat control | grep "Version:" | cut -d" " -f2`
PKGARCH=`cat control | grep "Architecture:" | cut -d" " -f2`

echo $PKGNAME $PKGVER $PKGARCH

rm -rf deb
mkdir -p deb/DEBIAN

cp control deb/DEBIAN
sh install.sh ./deb
dpkg --build deb/ $PKGNAME-${PKGVER}_$PKGARCH.deb

rm -rf deb

