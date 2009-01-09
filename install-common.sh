#/bin/bash

BASEPATH=$1

#install python
install -d $BASEPATH/usr/share/backintime
install --mode=644 applicationinstance.py $BASEPATH/usr/share/backintime
install --mode=644 backintime.py $BASEPATH/usr/share/backintime
install --mode=644 config.py $BASEPATH/usr/share/backintime
install --mode=644 configfile.py $BASEPATH/usr/share/backintime
install --mode=644 guiapplicationinstance.py $BASEPATH/usr/share/backintime
install --mode=644 logger.py $BASEPATH/usr/share/backintime
install --mode=644 snapshots.py $BASEPATH/usr/share/backintime
install --mode=644 tools.py $BASEPATH/usr/share/backintime

#install copyright file
install -d $BASEPATH/usr/share/doc/backintime-common
install --mode=644 debian/copyright $BASEPATH/usr/share/doc/backintime-common

#install doc file(s)
install -d $BASEPATH/usr/share/doc/backintime
install --mode=644 AUTHORS $BASEPATH/usr/share/doc/backintime
install --mode=644 CHANGES $BASEPATH/usr/share/doc/backintime
install --mode=644 LICENSE $BASEPATH/usr/share/doc/backintime
install --mode=644 README $BASEPATH/usr/share/doc/backintime
install --mode=644 TRANSLATIONS $BASEPATH/usr/share/doc/backintime
install --mode=644 VERSION $BASEPATH/usr/share/doc/backintime

#install man file(s)
install -d $BASEPATH/usr/share/man/man1
install --mode=644 man/C/*.gz $BASEPATH/usr/share/man/man1

#install application
install -d $BASEPATH/usr/bin
install backintime $BASEPATH/usr/bin

#install language files
rm -rf locale
mkdir -p locale

for langfile in `ls po/*.po`; do
	lang=`echo $langfile | cut -d/ -f2 | cut -d. -f1`
	echo Translate: $lang
	mkdir -p locale/$lang/LC_MESSAGES
	msgfmt -o locale/$lang/LC_MESSAGES/backintime.mo po/$lang.po

	install -d $BASEPATH/usr/share/locale/$lang/LC_MESSAGES
	install --mode=644 locale/$lang/LC_MESSAGES/*.mo $BASEPATH/usr/share/locale/$lang/LC_MESSAGES

	if [ -e man/$lang ]; then
		install -d $BASEPATH/usr/share/man/$lang/man1
		install --mode=644 man/C/*.gz $BASEPATH/usr/share/man/$lang/man1
	fi
done

