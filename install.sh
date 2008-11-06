#/bin/bash

BASEPATH=$1

#install python & glade file(s)
install -d $BASEPATH/usr/share/backintime
install --mode=644 *.py $BASEPATH/usr/share/backintime
install --mode=644 *.glade $BASEPATH/usr/share/backintime

#install doc file(s)
install -d $BASEPATH/usr/share/doc/backintime
install --mode=644 CHANGES $BASEPATH/usr/share/doc/backintime
install --mode=644 README $BASEPATH/usr/share/doc/backintime
install --mode=644 LICENSE $BASEPATH/usr/share/doc/backintime
install --mode=644 TRANSLATIONS $BASEPATH/usr/share/doc/backintime
install --mode=644 AUTHORS $BASEPATH/usr/share/doc/backintime

#install .desktop file(s)
install -d $BASEPATH/usr/share/applications
install --mode=644 *.desktop $BASEPATH/usr/share/applications

#install gnome-help file(s)
install -d $BASEPATH/usr/share/gnome/help/backintime/C/figures
install --mode=644 docbook/C/*.xml $BASEPATH/usr/share/gnome/help/backintime/C
install --mode=644 docbook/C/figures/*.png $BASEPATH/usr/share/gnome/help/backintime/C/figures

install -d $BASEPATH/usr/share/omf/backintime
install --mode=644 docbook/C/*.omf $BASEPATH/usr/share/omf/backintime

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

	if [ -e docbook/$lang ]; then
		install -d $BASEPATH/usr/share/gnome/help/backintime/$lang/figures
		install --mode=644 docbook/$lang/*.xml $BASEPATH/usr/share/gnome/help/backintime/$lang
		install --mode=644 docbook/$lang/figures/*.png $BASEPATH/usr/share/gnome/help/backintime/$lang/figures

		install -d $BASEPATH/usr/share/omf/backintime
		install --mode=644 docbook/C/*.omf $BASEPATH/usr/share/omf/backintime
	fi

	if [ -e man/$lang ]; then
		install -d $BASEPATH/usr/share/man/$lang/man1
		install --mode=644 man/C/*.gz $BASEPATH/usr/share/man/$lang/man1
	fi
done

