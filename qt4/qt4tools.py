#    Back In Time
#    Copyright (C) 2008-2017 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import sys
import gettext
from PyQt4.QtGui import QFont, QFileDialog, QListView, QAbstractItemView,      \
                        QTreeView, QDialog, QApplication, QStyleFactory,       \
                        QTreeWidget, QTreeWidgetItem, QColor
from PyQt4.QtCore import QDir, SIGNAL, Qt, pyqtSlot, pyqtSignal, QModelIndex
from datetime import datetime, date, timedelta
from calendar import monthrange

_ = gettext.gettext

def get_backintime_path(*path):
    return os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, *path))

def register_backintime_path(*path):
    '''find duplicate in common/tools.py
    '''
    path = get_backintime_path(*path)
    if not path in sys.path:
        sys.path.insert(0, path)

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

def create_qapplication(app_name = 'Back In Time'):
    global qapp
    try:
        return qapp
    except NameError:
        pass
    qapp = QApplication(sys.argv + ['-title', app_name])
    if os.geteuid() == 0 and                                   \
        qapp.style().objectName().lower() == 'windows' and  \
        'GTK+' in QStyleFactory.keys():
            qapp.setStyle('GTK+')
    return qapp

class MyTreeView(QTreeView):
    """subclass QTreeView to emit a SIGNAL myCurrentIndexChanged
    if the SLOT currentChanged is called"""
    myCurrentIndexChanged = pyqtSignal(QModelIndex, QModelIndex)

    def currentChanged(self, current, previous):
        self.myCurrentIndexChanged.emit(current, previous)
        super(MyTreeView, self).currentChanged(current, previous)

class TimeLine(QTreeWidget):
    updateFilesView = pyqtSignal(int)

    def __init__(self, parent):
        super(TimeLine, self).__init__(parent)
        self.setRootIsDecorated(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHeaderLabels([_('Snapshots'),'foo'])
        self.setSortingEnabled(True)
        self.sortByColumn(1, Qt.DescendingOrder)
        self.hideColumn(1)
        self.header().setClickable(False)

        self.parent = parent
        self.snapshots = parent.snapshots
        self._resetHeaderData()

    def clear(self):
        self._resetHeaderData()
        return super(TimeLine, self).clear()

    def _resetHeaderData(self):
        self.now = date.today()
        #list of tuples with (text, startDate, endDate)
        self.headerData = [ (#today
                                _('Today'),
                                datetime.combine(self.now, datetime.min.time()),
                                datetime.combine(self.now, datetime.max.time())
                            ),
                            (#yesterday
                                _('Yesterday'),
                                datetime.combine(self.now - timedelta(days = 1), datetime.min.time()),
                                datetime.combine(self.now - timedelta(days = 1), datetime.max.time())
                            ),
                            (#this week
                                _('This week'),
                                datetime.combine(self.now - timedelta(self.now.weekday()), datetime.min.time()),
                                datetime.combine(self.now - timedelta(days = 2), datetime.max.time())
                            ),
                            (#last week
                                _('Last week'),
                                datetime.combine(self.now - timedelta(self.now.weekday() + 7), datetime.min.time()),
                                datetime.combine(self.now - timedelta(self.now.weekday() + 1), datetime.max.time())
                            ),
                            (#the rest of current month. Otherwise this months header would be above today
                                date(self.now.year, self.now.month, 1).strftime('%B').capitalize(),
                                datetime.combine(self.now - timedelta(self.now.day), datetime.min.time()),
                                datetime.combine(self.now - timedelta(self.now.weekday() + 8), datetime.max.time())
                            )]

    def addRoot(self, sid, sName, tooltip = None):
        self.rootItem = self.addSnapshot(sid, sName, tooltip)
        return self.rootItem

    @pyqtSlot(str, str, str)
    def addSnapshot(self, sid, sName, tooltip = None):
        item = SnapshotItem()
        item.setName(sName)
        item.setSnapshotID(sid)
        item.setSort(self.snapshots.get_snapshot_datetime(sid))
        if not tooltip is None:
            item.setToolTip(0, tooltip)

        self.addTopLevelItem(item)

        #select the snapshot that was selected before
        if sid == self.parent.snapshot_id:
            self.setCurrentItem(item)

        if self.snapshots.is_snapshot_id(sid):
            self.addHeader(sid)
        return item

    def addHeader(self, sid):
        sidDatetime = self.snapshots.get_snapshot_datetime(sid)

        for text, startDate, endDate in self.headerData:
            if startDate <= sidDatetime <= endDate:
                return self._createHeaderItem(text, endDate)

        #any previous months
        year = int(sid[0 : 4])
        month = int(sid[4 : 6])
        if year == self.now.year:
            text = date(year, month, 1).strftime('%B').capitalize()
        else:
            text = date(year, month, 1).strftime('%B, %Y').capitalize()
        startDate = datetime.combine(date(year, month, 1), datetime.min.time())
        endDate   = datetime.combine(date(year, month, monthrange(year, month)[1]), datetime.max.time())
        if self._createHeaderItem(text, endDate):
            self.headerData.append((text, startDate, endDate))

    def _createHeaderItem(self, text, endDate):
        for item in self.iterHeaderItems():
            if item.data(0, Qt.UserRole) == endDate:
                return False
        item = HeaderItem()
        item.setName(text)
        item.setSort(endDate)
        self.addTopLevelItem(item)
        return True

    @pyqtSlot()
    def checkSelection(self):
        if self.currentItem() is None:
            self.setCurrentItem(self.rootItem)
            if self.parent.snapshot_id != '/':
                self.parent.snapshot_id = '/'
                self.updateFilesView.emit(2)

    def selectedSnapshotIDs(self):
        return [i.snapshotID() for i in self.selectedItems()]

    def currentSnapshotID(self):
        return self.currentItem().snapshotID()

    def iterItems(self):
        for index in range(self.topLevelItemCount()):
            yield self.topLevelItem(index)

    def iterSnapshotItems(self):
        for item in self.iterItems():
            if isinstance(item, SnapshotItem):
                yield item

    def iterHeaderItems(self):
        for item in self.iterItems():
            if isinstance(item, HeaderItem):
                yield item

class SnapshotItem(QTreeWidgetItem):
    def setName(self, name):
        self.setText(0, name)
        self.setFont(0, get_font_normal(self.font(0)))

    def setSnapshotID(self, sid):
        self.setData(0, Qt.UserRole, sid)

    def setSort(self, date):
        self.setText(1, str(date))

    def snapshotID(self):
        return str(self.data(0, Qt.UserRole))

class HeaderItem(QTreeWidgetItem):
    def setName(self, name):
        self.setText(0, name)
        self.setFont(0, get_font_bold(self.font(0)))
        self.setBackgroundColor(0, QColor(196, 196, 196))
        self.setTextColor(0, QColor(60, 60, 60))
        self.setFlags(Qt.NoItemFlags)

    def setSort(self, date):
        self.setData(0, Qt.UserRole, date)
        self.setText(1, str(date))
