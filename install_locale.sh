#/bin/bash

APPLANG=$1
BASEPATH=$2

if [ -z $APPLANG ]; then
	echo "You must specify a language (ex: fr)"
	exit 1
fi

if [ -e locale/$APPLANG/LC_MESSAGES ]; then
	install -d $BASEPATH/usr/share/locale/$APPLANG/LC_MESSAGES
	install --mode=644 locale/$APPLANG/LC_MESSAGES/*.mo $BASEPATH/usr/share/locale/$APPLANG/LC_MESSAGES
fi

if [ -e docbook/$APPLANG ]; then
	install -d $BASEPATH/usr/share/gnome/help/backintime/$APPLANG/figures
	install --mode=644 docbook/$APPLANG/*.xml $BASEPATH/usr/share/gnome/help/backintime/$APPLANG
	install --mode=644 docbook/$APPLANG/figures/*.png $BASEPATH/usr/share/gnome/help/backintime/$APPLANG/figures
fi

if [ -e man/$APPLANG ]; then
	install -d $BASEPATH/usr/share/man/$APPLANG/man1
	install --mode=644 man/C/*.gz $BASEPATH/usr/share/man/$APPLANG/man1
fi

