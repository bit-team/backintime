#/bin/bash

APPLANG=$1
BASEPATH=$2

if [ -z $APPLANG ]; then
	echo "You must specify a language (ex: fr)"
	exit 1
fi

install -d $BASEPATH/usr/share/locale/$APPLANG/LC_MESSAGES
install --mode=644 locale/fr/LC_MESSAGES/*.mo $BASEPATH/usr/share/locale/$APPLANG/LC_MESSAGES

