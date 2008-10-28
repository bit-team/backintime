#!/bin/bash

rm -rf locale
mkdir -p locale

for langfile in `ls po/*.po`; do
	lang=`echo $langfile | cut -d/ -f2 | cut -d. -f1`
	echo Translate: $lang
	mkdir -p locale/$lang/LC_MESSAGES
	msgfmt -o locale/$lang/LC_MESSAGES/backintime.mo po/$lang.po
done

