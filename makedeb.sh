#!/bin/bash

for i in common notify gnome kde4; do
	PKGNAME=`cat $i/debian_specific/control | grep "^Package:" | cut -d" " -f2`
	PKGVER=`cat $i/debian_specific/control | grep "^Version:" | cut -d" " -f2`
	PKGARCH=`cat $i/debian_specific/control | grep "^Architecture:" | cut -d" " -f2`

	echo $PKGNAME $PKGVER $PKGARCH

	rm -rf tmp
	mkdir -p tmp

	cd $i
	./configure
	make DESTDIR=../tmp install
	cd ..

	#update control
	mkdir -p tmp/DEBIAN
	cp $i/debian_specific/control tmp/DEBIAN/control
	echo "Installed-Size: `du -sk tmp | cut -f1`" >> tmp/DEBIAN/control
	
	cp $i/debian_specific/postrm tmp/DEBIAN/postrm
	[ -e $i/debian_specific/conffiles ] && cp $i/debian_specific/conffiles tmp/DEBIAN/conffiles

	dpkg --build tmp/ $PKGNAME-${PKGVER}_$PKGARCH.deb

	rm -rf tmp
done

