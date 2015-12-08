#!/bin/bash

PKGNAME=backintime
PKGVER=$(cat VERSION)
ARCH=all

dpkg-buildpackage -us -uc
