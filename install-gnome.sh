#/bin/bash

BASEPATH=$1

#install python & glade file(s)
install -d $BASEPATH/usr/share/backintime
install --mode=644 gnome*.py $BASEPATH/usr/share/backintime
install --mode=644 *.glade $BASEPATH/usr/share/backintime

#install .desktop file(s)
install -d $BASEPATH/usr/share/applications
install --mode=644 backintime-gnome.desktop $BASEPATH/usr/share/applications

#install gnome-help file(s)
install -d $BASEPATH/usr/share/gnome/help/backintime/C/figures
install --mode=644 docbook/C/*.xml $BASEPATH/usr/share/gnome/help/backintime/C
install --mode=644 docbook/C/figures/*.png $BASEPATH/usr/share/gnome/help/backintime/C/figures

install -d $BASEPATH/usr/share/omf/backintime
install --mode=644 docbook/C/*.omf $BASEPATH/usr/share/omf/backintime

#install language files
for langfile in `ls po/*.po`; do
	lang=`echo $langfile | cut -d/ -f2 | cut -d. -f1`
	echo Gnome help: $lang

	if [ -e docbook/$lang ]; then
		install -d $BASEPATH/usr/share/gnome/help/backintime/$lang/figures
		install --mode=644 docbook/$lang/*.xml $BASEPATH/usr/share/gnome/help/backintime/$lang
		install --mode=644 docbook/$lang/figures/*.png $BASEPATH/usr/share/gnome/help/backintime/$lang/figures

		install -d $BASEPATH/usr/share/omf/backintime
		install --mode=644 docbook/C/*.omf $BASEPATH/usr/share/omf/backintime
	fi
done

