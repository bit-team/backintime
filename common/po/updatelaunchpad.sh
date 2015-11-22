#!/bin/bash

#EXCEPTIONS="es.po de.po"
EXCEPTIONS="none"
TRANSLATIONFILE="launchpad-export.tar.gz"

rm -rf tmp
mkdir tmp
tar xfz $TRANSLATIONFILE -C tmp

for popath in `find tmp -name \*.po`; do
	#echo $popath
	#lang=`basename $popath | cut -d- -f4`
	lang=`basename $popath | cut -d- -f2`
	#echo $lang

	ignore="0"
	for exception in $EXCEPTIONS; do
		if [ $lang = $exception ]; then
			ignore="1"
			break
		fi
	done

	if [ $ignore = "1" ]; then
		echo "Ignore $lang"
	else
		if [ -f $lang ]; then
			echo "rm $lang"
			rm $lang
		fi

		echo "cp $popath $lang"
		cp $popath $lang
	fi
done

rm -rf tmp
rm $TRANSLATIONFILE

