#!/bin/bash

VER=`cat VERSION`
CURRENT=$(pwd)
NEW="backintime-$VER"

cd ..
bzr branch $CURRENT $NEW
tar cfz backintime-$VER.tar.gz ${NEW}/AUTHORS ${NEW}/CHANGES ${NEW}/LICENSE ${NEW}/TODO ${NEW}/README ${NEW}/TRANSLATIONS ${NEW}/VERSION ${NEW}/*.sh ${NEW}/common ${NEW}/qt4 ${NEW}/debian

