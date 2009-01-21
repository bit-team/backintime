#/bin/bash

BASEPATH=$1

#install application
install -d $BASEPATH/usr/bin
install backintime-kde4 $BASEPATH/usr/bin

#install copyright file
install -d $BASEPATH/usr/share/doc/backintime-kde4
install --mode=644 debian_specific/copyright $BASEPATH/usr/share/doc/backintime-kde4

#install python & glade file(s)
install -d $BASEPATH/usr/share/backintime
install --mode=644 kde4*.py $BASEPATH/usr/share/backintime

#install .desktop file(s)
install -d $BASEPATH/usr/share/applications/kde4
install --mode=644 backintime-kde4.desktop $BASEPATH/usr/share/applications/kde4

