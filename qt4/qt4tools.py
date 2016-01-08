#    Back In Time
#    Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
                        QTreeWidget, QTreeWidgetItem, QColor, QComboBox
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

register_backintime_path('common')
import snapshots

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

    def addRoot(self, sid):
        self.rootItem = self.addSnapshot(sid)
        return self.rootItem

    @pyqtSlot(str, str, str)
    def addSnapshot(self, sid):
        item = SnapshotItem(sid)

        self.addTopLevelItem(item)

        #select the snapshot that was selected before
        if sid == self.parent.sid:
            self.setCurrentItem(item)

        if not sid.isRoot:
            self.addHeader(sid)
        return item

    def addHeader(self, sid):
        for text, startDate, endDate in self.headerData:
            if startDate <= sid.date <= endDate:
                return self._createHeaderItem(text, endDate)

        #any previous months
        year = sid.date.year
        month = sid.date.month
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
            if item.snapshotID().date == endDate:
                return False
        item = HeaderItem(text, snapshots.SID(endDate, self.parent.config))
        self.addTopLevelItem(item)
        return True

    @pyqtSlot()
    def checkSelection(self):
        if self.currentItem() is None:
            self.setCurrentItem(self.rootItem)
            if not self.parent.sid.isRoot:
                self.parent.sid = self.rootItem.snapshotID()
                self.updateFilesView.emit(2)

    def selectedSnapshotIDs(self):
        return [i.snapshotID() for i in self.selectedItems()]

    def currentSnapshotID(self):
        item = self.currentItem()
        if item:
            return item.snapshotID()

    def setCurrentSnapshotID(self, sid):
        for item in self.iterItems():
            if item.snapshotID() == sid:
                self.setCurrentItem(item)
                break

    def setCurrentItem(self, item, *args, **kwargs):
        super(TimeLine, self).setCurrentItem(item, *args, **kwargs)
        if self.parent.sid != item.snapshotID():
            self.parent.sid = item.snapshotID()
            self.updateFilesView.emit(2)

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

class TimeLineItem(QTreeWidgetItem):
    def __lt__(self, other):
        return self.snapshotID() < other.snapshotID()

    def snapshotID(self):
        return self.data(0, Qt.UserRole)

class SnapshotItem(TimeLineItem):
    def __init__(self, sid):
        super(SnapshotItem, self).__init__()
        self.setText(0, sid.displayName)
        self.setFont(0, get_font_normal(self.font(0)))

        self.setData(0, Qt.UserRole, sid)

        if sid.isRoot:
            self.setToolTip(0, _('This is NOT a snapshot but a live view of your local files'))
        else:
            self.setToolTip(0, _('Last check %s') %sid.lastChecked)

    def updateText(self):
        sid = self.snapshotID()
        self.setText(0, sid.displayName)

class HeaderItem(TimeLineItem):
    def __init__(self, name, sid):
        super(HeaderItem, self).__init__()
        self.setText(0, name)
        self.setFont(0, get_font_bold(self.font(0)))
        self.setBackgroundColor(0, QColor(196, 196, 196))
        self.setTextColor(0, QColor(60, 60, 60))
        self.setFlags(Qt.NoItemFlags)

        self.setData(0, Qt.UserRole, sid)

class SortedComboBox(QComboBox):
    #prevent inserting items abroad from addItem because this would break sorting
    insertItem = NotImplemented

    def __init__(self, parent = None):
        super(SortedComboBox, self).__init__(parent)
        self.sortOrder = Qt.AscendingOrder
        self.sortRole = Qt.DisplayRole

    def addItem(self, text, userData = None):
        '''QComboBox doesn't support sorting
        so this litle hack is used to insert
        items in sorted order.
        '''
        if self.sortRole == Qt.UserRole:
            sortObject = userData
        else:
            sortObject = text
        l = [self.itemData(i, self.sortRole) for i in range(self.count())]
        l.append(sortObject)
        l.sort(reverse = self.sortOrder)
        index = l.index(sortObject)
        super(SortedComboBox, self).insertItem(index, text, userData)

    def checkSelection(self):
        if self.currentIndex() < 0:
            self.setCurrentIndex(0)

class SnapshotCombo(SortedComboBox):
    def __init__(self, parent = None):
        super(SnapshotCombo, self).__init__(parent)
        self.sortOrder = Qt.DescendingOrder
        self.sortRole = Qt.UserRole

    def addSnapshotID(self, sid):
        assert isinstance(sid, snapshots.SID), 'sid is not snapshots.SID type: {}'.format(sid)
        self.addItem(sid.displayName, sid)

    def currentSnapshotID(self):
        return self.itemData(self.currentIndex())

    def setCurrentSnapshotID(self, sid):
        for i in range(self.count()):
            if self.itemData(i) == sid:
                self.setCurrentIndex(i)
                break

class ProfileCombo(SortedComboBox):
    def __init__(self, parent):
        super(ProfileCombo, self).__init__(parent)
        self.getName = parent.config.get_profile_name

    def addProfileID(self, profileID):
        self.addItem(self.getName(profileID), profileID)

    def currentProfileID(self):
        return self.itemData(self.currentIndex())

    def setCurrentProfileID(self, profileID):
        for i in range(self.count()):
            if self.itemData(i) == profileID:
                self.setCurrentIndex(i)
                break
