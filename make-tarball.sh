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

# clean up
rm ./common/man/C/*.gz

cd ..

# if [[ -n "$(which git)" ]] && [[ -x "$(which git)" ]]; then
#     git clone ${CURRENT} ${NEW}
# else
#     cp -aR ${CURRENT} ${NEW}
# fi

cp -aR ${CURRENT} ${NEW}

rm backintime-$VER.tar.gz

tar cfz backintime-$VER.tar.gz \
    --exclude="*/__pycache__" \
    --exclude="*/.pytest_cache" \
    --exclude="*/.ruff_cache" \
    --exclude="*/po/*.mo" \
    --exclude-vcs \
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
    ${NEW}/LICENSES \
    ${NEW}/doc

tar -tzf backintime-$VER.tar.gz
echo ""
echo "RESULT:"
realpath backintime-$VER.tar.gz

# rm -rf backintime-$VER

