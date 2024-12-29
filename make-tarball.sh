#!/bin/bash
# SPDX-FileCopyrightText: © 2013 Oprea Dan
# SPDX-FileCopyrightText: © 2013 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
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

