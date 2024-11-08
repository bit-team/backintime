<!--
SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See file/folder LICENSE or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->

# Organization and building of documentation for _Back In Time_
This file describes briefly how to the several types of documentation existing
for _Back In Time_ (BIT), how they are maintained, structured and build.

> [!TIP]
> Feel free to [open issues](https://github.com/bit-team/backintime/issues)
> or contact the
> [maintenance team on the mailing list](https://mail.python.org/mailman3/lists/bit-dev.python.org/)
> if this text is difficult to understand or not helpful.

# Index

<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->
- [Overview](#overview)
- [Build & view user manual (MkDocs)](#build--view-user-manual-mkdocs)
- [Build & view source code documentation (Sphinx)](#build--view-source-code-documentation-sphinx)
- [Tips & Examples](#tips-and-examples)
<!-- TOC end -->

# Overview

The project distinguish between three types of documentation:

1. The **User manual** can be found at
   [backintime.readthedocs.io](http://backintime.readthedocs.io) and is
   generated using [MkDocs](https://www.mkdocs.org) based on simple
   [Markdown](https://en.wikipedia.org/wiki/Markdown) files.
2. The **Source Code documentation** is located at 
   [backintime-dev.readthedocs.io](http://backintime-dev.readthedocs.io) and
   generated from the Python source files using
   [Sphinx](https://www.sphinx-doc.org) (migration to
   [PyDoctor](https://pydoctor.readthedocs.io) is planned).
3. The **Maintenance and Developer documentation** is a bunch of Markdown
   files, like the one you are reading currently.


# Build & view user manual (MkDocs)

Install related dependencies:
  - `mkdocs`
  - `mkdocs-material`
  - See file [`CONTRIBUTING.md`](../../CONTRIBUTING.md) in this repo for a
    complete and up to date list of dependencies.

**Live preview HTML documentation as working on it**:

```sh
# Enter folder
$ cd doc/manual

# Start built-in server
$ mkdocs serve
```
Open [127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Every time the
underlying markdown files are modified the server will on the fly generate new
HTML.

**Generate HTML files**:

```sh
# Enter folder
$ cd doc/manual

# Build
$ mkdocs build

# Open result in default browser
$ xdg-open html/index.html
```

# Build & view source code documentation (Sphinx)

See [Using Sphinx to write and build documentation](1b_doc_sphinx_howto.md).

# Tips and Examples
- [Markdown](#markdown)
  - [Annotation boxes](#annotation-boxes--colored-highlight-boxes)

## Markdown
### Annotation boxes / Colored highlight boxes
``` markdown
> [!NOTE]  
> Highlights information that users should take into account, even when
> skimming.

> [!TIP]
> Optional information to help a user be more successful.

> [!IMPORTANT]  
> Crucial information necessary for users to succeed.

> [!WARNING]  
> Critical content demanding immediate user attention due to potential risks.

> [!CAUTION]
> Negative potential consequences of an action.
```

> [!NOTE]  
> Highlights information that users should take into account, even when
> skimming.

> [!TIP]
> Optional information to help a user be more successful.

> [!IMPORTANT]
> Crucial information necessary for users to succeed.

> [!WARNING]
> Critical content demanding immediate user attention due to potential risks.

> [!CAUTION]
> Negative potential consequences of an action.

<sub>September 2024</sub>
