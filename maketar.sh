#!/bin/bash

PKGNAME=`cat control | grep "Package:" | cut -d" " -f2`
PKGVER=`cat control | grep "Version:" | cut -d" " -f2`

echo $PKGNAME $PKGVER

rm *~
rm *.deb
rm *.pyc
rm -rf locale

cd ..
mkdir $PKGNAME-$PKGVER
cp -a backintime/* $PKGNAME-$PKGVER

tar cfz $PKGNAME-${PKGVER}_src.tar.gz $PKGNAME-$PKGVER
rm -rf $PKGNAME-$PKGVER
cd backintime

