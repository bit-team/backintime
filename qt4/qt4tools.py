#    Back In Time
#    Copyright (C) 2008-2014 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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

def getExistingDirectories(parent, *args, **kwargs):
    """Workaround for selecting multiple directories
    adopted from http://www.qtcentre.org/threads/34226-QFileDialog-select-multiple-directories?p=158482#post158482
    This also give control about hidden folders
    """
    dlg = QFileDialog(parent, *args, **kwargs)
    dlg.setOption(dlg.DontUseNativeDialog, True)
    dlg.setOption(dlg.HideNameFilterDetails, True)
    dlg.setFileMode(dlg.Directory)
    dlg.setOption(dlg.ShowDirsOnly, True)
    if hidden_files(parent):
        dlg.setFilter(dlg.filter() | QDir.Hidden)
    dlg.findChildren(QListView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)
    dlg.findChildren(QTreeView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)
    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()
    #TODO: repl QStringList
    return [str(), ]

def getExistingDirectory(parent, *args, **kwargs):
    """Workaround to give control about hidden folders
    """
    dlg = QFileDialog(parent, *args, **kwargs)
    dlg.setOption(dlg.DontUseNativeDialog, True)
    dlg.setOption(dlg.HideNameFilterDetails, True)
    dlg.setFileMode(dlg.Directory)
    dlg.setOption(dlg.ShowDirsOnly, True)
    if hidden_files(parent):
        dlg.setFilter(dlg.filter() | QDir.Hidden)
    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()[0]
    return str()

def getOpenFileNames(parent, *args, **kwargs):
    """Workaround to give control about hidden files
    """
    dlg = QFileDialog(parent, *args, **kwargs)
    dlg.setOption(dlg.DontUseNativeDialog, True)
    dlg.setOption(dlg.HideNameFilterDetails, True)
    dlg.setFileMode(dlg.ExistingFiles)
    if hidden_files(parent):
        dlg.setFilter(dlg.filter() | QDir.Hidden)
    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()
    #TODO: repl QStringList
    return [str(), ]

def getOpenFileName(parent, *args, **kwargs):
    """Workaround to give control about hidden files
    """
    dlg = QFileDialog(parent, *args, **kwargs)
    dlg.setOption(dlg.DontUseNativeDialog, True)
    dlg.setOption(dlg.HideNameFilterDetails, True)
    dlg.setFileMode(dlg.ExistingFile)
    if hidden_files(parent):
        dlg.setFilter(dlg.filter() | QDir.Hidden)
    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()[0]
    return str()

def hidden_files(parent):
    try:
        return parent.parent.show_hidden_files
    except: pass
    try:
        return parent.show_hidden_files
    except: pass
    return False
