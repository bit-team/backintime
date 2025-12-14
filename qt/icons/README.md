<!--
SPDX-FileCopyrightText: © 2025 Back In Time Team

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# Overview
That folder contain files related to the application logo of _Back In Time_ and
other related icons.

# Content of that folder
- `scalable/apps/backintime.svg` - The logo file used in _Back In Time_ GUI.
- `scalable/apps/backintime-symbolic.svg` - The symbolic version of the logo
  used in systray. But that file is not directly used by BIT. The files XML
  content is contained as a python string in `qtsystrayicon.py`.
- `scalable/actions/show-idden.svg` - Icon used for _Show hidden fils_ button
  in the GUI.

# License
For license and copyright information on that files see its plain text headers
containing SPDX meta data. See also the [LICENSES.md](../../LICENSES.md) file.

**Important** to know is that the SPDX meta data in the SVG files need to be stored
after the `<svg>` tag. If the SPDX header is placed on top of a file some desktop
environments don't treat it as a valid SVG and won't load the icon.

