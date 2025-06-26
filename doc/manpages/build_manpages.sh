#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.

# stop at each error immediately
set -e

BIT_VERSION=$(cat ../../VERSION)
echo "Using BIT_VERSION $BIT_VERSION"

adoc_to_manpage () {
    # the .adoc-file
    adocfile="$1"
    # remove ".adoc" from name if exists
    manfile="${adocfile%.adoc}.gz"

    echo "Convert $file into $manfile"
    asciidoctor --backend manpage --attribute=version="$BIT_VERSION" "$file" --out-file=- | gzip --best > "$manfile"
    # check return codes of asciidoctor & gzip
    read asciidoctor_return gzip_return _ <<< "${PIPESTATUS[@]}"
    if (( asciidoctor_return != 0 || gzip_return !=0 )); then
        exit 1
    fi

    # This is how Debian Lintian would validate a man page file
    LC_ALL=C.UTF-8 MANROFFSEQ='' MANWIDTH=80 man --warnings -E UTF-8 -l -Tutf8 -Z "$manfile" > /dev/null
    if [ $? -ne 0 ]; then
        echo "ERROR: Lintian-like check of $manfile" >&2
        exit 1
    fi
}

# Script got argument
if [ $# -gt 0 ]; then
    file=$1
    adoc_to_manpage "$file"
    exit
fi

# No arguments...

# Each .adoc-file in current folder
for file in *.adoc; do
    adoc_to_manpage "$file"
done
