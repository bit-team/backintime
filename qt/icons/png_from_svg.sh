#!/bin/sh
# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: CC0-1.0
#
# This file is released under Creative Commons Zero 1.0 (CC0-1.0) and part of
# the program "Back In Time". The program as a whole is released under GNU
# General Public License v2 or any later version (GPL-2.0-or-later).
# See LICENSES directory or go to <https://spdx.org/licenses/CC0-1.0.html>
# and <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# File-size optimized PNG files for nearly all icon resolutions created from
# SVG files. Reason: Not all desktop environments are able to handle SVG files.

error_when_unavailable() {
    cmd="$1"  # command to check
    pkg="${2:-$1}"  # package to install if command not available

    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: '$cmd' is not available. Try install with: 'apt install $pkg'" >&2
        exit 1
    fi
}

error_when_unavailable rsvg-convert librsvg2-bin
error_when_unavailable optipng

svg_to_png() {
    s=$3
    src=scalable/${2}/${1}.svg
    folder=./${s}x${s}/${2}
    png=${folder}/${1}.png

    printf "  $src to $png..."
    # Create dir if not available
    mkdir --parents $folder

    # Remove outdated PNG
    rm --force $png

    # Convert SVG to PNG
    rsvg-convert --width $s --height $s $src --output $png

    # Optimize PNG file size (without losing quality)
    # optipng -o7 $png >/dev/null 2>&1

    printf "FIN\n"
}

# Each resolution
# Additional resolutions beside Free Desktop Specs: 72, 96, 192
for s in 16 22 24 48 64 128 256 512; do
    printf "Resolution ${s}x${s}...\n"

    svg_to_png backintime apps $s
    svg_to_png backintime-symbolic apps $s
    svg_to_png show-hidden actions $s

done

