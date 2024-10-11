<!--
SPDX-FileCopyrightText: © 2024 Back In Time Team

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See directory LICENSES or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
This directory contains the source files for various types of documentation
for _Back In Time_.

- `manual`: User Manual
- `coderef`: Source Code Documentation (...coming soon...)
- `maintain`: Several documents regarding mainteanance of the _Back In Time_
  project and nearly all other documents not fitting to one of the other
  categories.

### How to reduce file size of images
For PNG images `optipng` could be used. *Attention*: By default it overwrites
the original files. The following command use the highest possible optimization
and write the result in a subfolder.

    $ optipng --dir subfolder -o7 *.png

As an alternative `pngcrush` can be used. The following determine the best
algorithm by its own.

    $ pngcrush -d subfolder -brute *.png

Applied to a set of _Back In Time_ dark mode screenshots, their file size
was reduced by approximately 13%. Both applications show no significant
differences. The visual result is indistinguishable from the original.
