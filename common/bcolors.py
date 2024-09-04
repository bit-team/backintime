# SPDX-FileCopyrightText: © 2015-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
import sys

if sys.stdout.isatty():
    HEADER = '\033[95m'  # light magenta
    OKBLUE = '\033[94m'  # light blue
    OKGREEN = '\033[92m'  # light green
    WARNING = '\033[93m'  # light yellow
    FAIL = '\033[91m'  # light red
    CRITICAL = '\033[31m'  # dark red
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
else:
    HEADER = ''
    OKBLUE = ''
    OKGREEN = ''
    WARNING = ''
    FAIL = ''
    CRITICAL = ''
    ENDC = ''
    BOLD = ''
    UNDERLINE = ''
