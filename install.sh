#/bin/bash

BASEPATH=$1

install -d $BASEPATH/usr/share/backintime
install --mode=644 *.py $BASEPATH/usr/share/backintime
install --mode=644 *.glade $BASEPATH/usr/share/backintime

install -d $BASEPATH/usr/share/doc/backintime
install --mode=644 CHANGES $BASEPATH/usr/share/doc/backintime
install --mode=644 README $BASEPATH/usr/share/doc/backintime
install --mode=644 LICENSE $BASEPATH/usr/share/doc/backintime
install --mode=644 TRANSLATIONS $BASEPATH/usr/share/doc/backintime

install -d $BASEPATH/usr/share/applications
install --mode=644 *.desktop $BASEPATH/usr/share/applications

install -d $BASEPATH/usr/bin
install backintime $BASEPATH/usr/bin

