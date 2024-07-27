#!/bin/bash

VER=`cat VERSION`
CURRENT=$(pwd)
NEW="backintime-$VER"

cd ..
if [[ -n "$(which git)" ]] && [[ -x "$(which git)" ]]; then
    git clone ${CURRENT} ${NEW}
else
    cp -aR ${CURRENT} ${NEW}
fi
tar cfz backintime-$VER.tar.gz \
    ${NEW}/AUTHORS \
    ${NEW}/CHANGES \
    ${NEW}/LICENSE \
    ${NEW}/README.md \
    ${NEW}/FAQ.md \
    ${NEW}/CONTRIBUTING.md \
    ${NEW}/HISTORY.md \
    ${NEW}/TRANSLATIONS \
    ${NEW}/VERSION \
    ${NEW}/updateversion.sh \
    ${NEW}/common \
    ${NEW}/qt \
    ${NEW}/doc

rm -rf backintime-$VER

