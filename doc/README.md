<!--
SPDX-FileCopyrightText: © 2024 Back In Time Team

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See directory LICENSES or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
- [Overview](#overview)
- [Build user manual](#build-user-manual)
- [How to reduce file size of images](#how-to-reduce-file-size-of-images)

# Overview
This directory contains the source files for various types of documentation
for _Back In Time_.

- `manual`: User Manual
- `coderef`: Source Code Documentation (...coming soon...)
- `maintain`: Several documents regarding mainteanance of the _Back In Time_
  project and nearly all other documents not fitting to one of the other
  categories.

# Build user manual
The user manual is build from markdown files (in directory `src`) and converted
into HTML (directory `html`). The tool `mkdocs` is used for this.

```sh
$ cd backintime/doc/manual
$ mkdocs build
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: XYZ
INFO    -  Documentation built in 2.66 seconds 
$
```
Open `html/index.html` to inspect the result.

As an alternative `mkdocs` is able to provide a live preview of docs while
editing the markdown files. A local web server is used for this.

```sh
$ cd backintime/doc/manual
$ mkdocs serve
INFO    -  Building documentation...
INFO    -  Cleaning site directory
INFO    -  Documentation built in 1.40 seconds
INFO    -  [10:17:21] Watching paths for changes: 'src', 'mkdocs.yml'
INFO    -  [10:17:21] Serving on http://127.0.0.1:8000/     
```

Inspect the result in browser: [127.0.0.1:8000](http://127.0.0.1:8000).

# How to reduce file size of images
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
