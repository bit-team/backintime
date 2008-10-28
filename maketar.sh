#!/bin/bash

PKGNAME=`cat control | grep "Package:" | cut -d" " -f2`
PKGVER=`cat control | grep "Version:" | cut -d" " -f2`

echo $PKGNAME $PKGVER

rm *.pyc
rm -rf locale

tar cfz $PKGNAME-${PKGVER}_src.tar.gz *
