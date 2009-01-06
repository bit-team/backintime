#!/bin/bash

PKGNAME=backintime
PKGVER=`cat VERSION`

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

