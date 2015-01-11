#!/bin/bash

RELEASES="trusty utopic"

PKGNAME=backintime
PKGVER=$(cat VERSION)
TMP=$(mktemp -d)
CURRENT=$(pwd)

for release in ${RELEASES}; do
	echo ""
	echo "${PKGNAME} ${PKGVER} ${release}"
	echo ""
	DST=${TMP}/${PKGNAME}_${PKGVER}~${release}/
	mkdir ${DST}
	cp -aR ${CURRENT}/* ${DST}
	cd ${DST}

	#debian: changelog
	sed -e "s/\$RELEASE/${release}/g" -i debian/changelog

	debuild -i -S
done

cp ${TMP}/*.build ${TMP}/*.changes ${TMP}/*.dsc ${TMP}/*.tar.gz ${CURRENT}
rm -rf ${TMP}

