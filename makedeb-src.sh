#!/bin/bash

RELEASES="trusty utopic"

for i in common qt4; do
	PKGNAME=`cat $i/debian_specific/control | grep "^Package:" | cut -d" " -f2`
	PKGVER=`cat $i/debian_specific/control | grep "^Version:" | cut -d" " -f2`
	PKGARCH=`cat $i/debian_specific/control | grep "^Architecture:" | cut -d" " -f2`
	DST=${PKGNAME}-${PKGVER}~

	echo $PKGNAME $PKGVER $PKGARCH

	rm -rf tmp
	mkdir -p tmp/${DST}

	cd $i
	./makedeb-src.sh ../tmp/${DST}
	cd ..

	cd tmp

	for release in $RELEASES; do
		mv ${DST}* ${DST}${release}
		cd ${DST}${release}
		#debian: control
		cp ../../$i/debian_specific/control.source debian/control
		cat ../../$i/debian_specific/control | \
			sed -e '/^Version:\|^Source:\|^Maintainer:/d' \
			    -e 's/^Depends: /Depends: ${misc:Depends}, /g' \
			    -e "s/backintime-\(common\|notify\|qt\|kde\|kde4\|gnome\) (\(>=\|<<\) [^)]*)/backintime-\1 (\2 $PKGVER~$release)/g" \
			    >> debian/control

		if [ -e ../../$i/debian_specific/control.virtual ]; then
			echo "" >> debian/control
			cat ../../$i/debian_specific/control.virtual | \
				sed -e 's/^Depends: /Depends: ${misc:Depends}, /g' \
				    >> debian/control
		fi

		#debian: changelog
		cp ../../common/debian_specific/changelog debian
		sed -e "s/\$BACKINTIME/backintime-$i/g" -e "s/\$VERSION/$PKGVER/g"  -e "s/\$RELEASE/$release/g" -i debian/changelog

		debuild -i -S
		#debuild -i -us -uc -S
		cd ..
	done

	rm -rf ${DST}*
	mv * ../
	cd ..

	rm -rf tmp
done

