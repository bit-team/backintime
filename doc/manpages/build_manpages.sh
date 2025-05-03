#!/usr/bin/env sh
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
adoc_to_manpage () {
    # the .adoc-file
    adocfile="$1"
    # remove ".adoc" from name if exists
    manfile="${file%.adoc}.gz"

    echo "Convert $file into $manfile"
    asciidoctor --backend manpage "$file" --out-file=- | gzip --best > "$manfile"
}

# Script got argument
if [ $# -gt 0 ]; then
    file=$1
    adoc_to_manpage "$file"
    exit 0
fi

# No arguments...

# Each .adoc-file in current folder
for file in *.adoc; do
    adoc_to_manpage "$file"
done
exit 0

