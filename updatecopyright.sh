#!/bin/sh

find ./ -type f                \
  ! -wholename "./common/po/*" \
  ! -wholename "./.bzr/*"      \
  -exec sed -e "/Germar Reitze/s/[cC]opyright ([cC]) \([0-9]*\)-\([0-9]*\)/Copyright (C) \1-$(date +%Y)/g" -i {} +
