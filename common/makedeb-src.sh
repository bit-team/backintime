#!/bin/bash

if [ -z $1 ]; then
	echo "ERROOR: You need to specify the install dir"
	exit 1
fi

DEST=$1

mkdir -p $DEST/src/debian/rules

#check languages
mos=""
langs=""
for langfile in `ls po/*.po`; do
	msgfmt -o po/$lang.mo po/$lang.po
done

#Start Makefile
echo -e "LANGS=$langs" >> Makefile
echo -e "SHELL=`which bash`" >> Makefile
echo -e "" >> Makefile

#add template
cat Makefile.template >> Makefile

#translate
echo -e "translate: $mos" >> Makefile
echo -e "" >> Makefile

for lang in $langs; do
	echo -e "po/$lang.mo: po/$lang.po" >> Makefile
	echo -e "\tmsgfmt -o po/$lang.mo po/$lang.po" >> Makefile
	echo -e "" >> Makefile
done

#common langs
echo "install_translations:" >> Makefile
for lang in $langs; do
	echo -e "\tinstall -d \$(DEST)/share/locale/$lang/LC_MESSAGES" >> Makefile
	echo -e "\tinstall --mode=644 po/$lang.mo \$(DEST)/share/locale/$lang/LC_MESSAGES/backintime.mo" >> Makefile
done
echo -e "" >> Makefile

echo "All OK. Now run:"
echo "    make"
echo "    sudo make install"

