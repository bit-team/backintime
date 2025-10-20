#!/bin/sh

if ! command -v rsvg-convert >/dev/null 2>&1; then
    echo "Error: rsvg-convert is not available. Do 'apt install librsvg2-bin'." >&2
    exit 1
fi

for s in 16 22 24 48 64 128 256 512; do

    # Create dir if not available
    mkdir -p ./${s}x${s}/apps

    # Convert SVG to PNG
    rsvg-convert -w $s -h $s scalable/apps/backintime.svg \
    -o ./${s}x${s}/apps/backintime.png
done

