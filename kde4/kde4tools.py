#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import os
import os.path

from PyQt4.QtGui import *
from PyQt4.QtCore import *


def get_font_bold( font ):
    font.setWeight( QFont.Bold )
    return font


def set_font_bold( widget ):
    widget.setFont( get_font_bold( widget.font() ) )

def get_font_normal( font ):
    font.setWeight( QFont.Normal )
    return font

def set_font_normal( widget ):
    widget.setFont( get_font_normal( widget.font() ) )

def equal_indent(*args):
    width = 0
    for widget in args:
        widget.setMinimumWidth(0)
        width = max(width, widget.sizeHint().width())
    if len(args) > 1:
        for widget in args:
            widget.setMinimumWidth(width)

class getExistingDirectories(QFileDialog):
    """Workaround for selecting multiple directories
    adopted from http://www.qtcentre.org/threads/34226-QFileDialog-select-multiple-directories?p=158482#post158482
    """
    def __init__(self, *args):
        QFileDialog.__init__(self, *args)
        self.setOption(self.DontUseNativeDialog, True)
        self.setFileMode(self.DirectoryOnly)
        self.findChildren(QListView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.findChildren(QTreeView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)
