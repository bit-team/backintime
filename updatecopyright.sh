#!/bin/sh

find ./ -type f \
  ! -wholename "./common/po/*" \
  -exec sed -e "s/[cC]opyright ([cC]) \([0-9]*\)-\([0-9]*\)/Copyright (C) \1-$(date +%Y)/g" -i {} +
find ./ -type f \
  ! -name LICENSE \
  ! -name updatecopyright.sh \
  ! -wholename "./common/po/*" \
  -exec sed -e '/Germar Reitze/!s/Copyright (C) \(.*\)/Copyright (C) \1, Germar Reitze/g' -i {} +
