#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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

from PyQt5.QtGui import (QFont, QColor, QKeySequence)
from PyQt5.QtCore import (QDir, Qt, pyqtSlot, pyqtSignal, QModelIndex,
                          QTranslator, QLocale, QLibraryInfo, QEvent,
                          QT_VERSION_STR)
from PyQt5.QtWidgets import (QFileDialog, QAbstractItemView, QListView,
                             QTreeView, QDialog, QApplication, QStyleFactory,
                             QTreeWidget, QTreeWidgetItem, QComboBox, QMenu,
                             QToolTip, QAction)
from datetime import (datetime, date, timedelta)
from calendar import monthrange
from packaging.version import Version


_ = gettext.gettext

def backintimePath(*path):
    return os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, *path))

def registerBackintimePath(*path):
    """
    find duplicate in common/tools.py
    """
    path = backintimePath(*path)
    if not path in sys.path:
        sys.path.insert(0, path)

registerBackintimePath('common')
import snapshots
import tools
import logger

def fontBold(font):
    font.setWeight(QFont.Bold)
    return font

def setFontBold(widget):
    widget.setFont(fontBold(widget.font()))

def fontNormal(font):
    font.setWeight(QFont.Normal)
    return font

def setFontNormal(widget):
    widget.setFont(fontNormal(widget.font()))

def equalIndent(*args):
    width = 0
    for widget in args:
        widget.setMinimumWidth(0)
        width = max(width, widget.sizeHint().width())
    if len(args) > 1:
        for widget in args:
            widget.setMinimumWidth(width)

class FileDialogShowHidden(QFileDialog):
    def __init__(self, parent, *args, **kwargs):
        super(FileDialogShowHidden, self).__init__(parent, *args, **kwargs)
        self.setOption(self.DontUseNativeDialog, True)
        self.setOption(self.HideNameFilterDetails, True)

        showHiddenAction = QAction(self)
        showHiddenAction.setShortcuts([QKeySequence(Qt.CTRL + Qt.Key_H),])
        showHiddenAction.triggered.connect(self.toggleShowHidden)
        self.addAction(showHiddenAction)

        self.showHidden(hiddenFiles(parent))

    def showHidden(self, enable):
        if enable:
            self.setFilter(self.filter() | QDir.Hidden)
        elif int(self.filter() & QDir.Hidden):
            self.setFilter(self.filter() ^ QDir.Hidden)

    def toggleShowHidden(self):
        self.showHidden(not int(self.filter() & QDir.Hidden))

def getExistingDirectories(parent, *args, **kwargs):
    """
    Workaround for selecting multiple directories
    adopted from http://www.qtcentre.org/threads/34226-QFileDialog-select-multiple-directories?p=158482#post158482
    This also give control about hidden folders
    """
    dlg = FileDialogShowHidden(parent, *args, **kwargs)
    dlg.setFileMode(dlg.Directory)
    dlg.setOption(dlg.ShowDirsOnly, True)
    dlg.findChildren(QListView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)
    dlg.findChildren(QTreeView)[0].setSelectionMode(QAbstractItemView.ExtendedSelection)

    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()
    return [str(), ]

def getExistingDirectory(parent, *args, **kwargs):
    """
    Workaround to give control about hidden folders
    """
    dlg = FileDialogShowHidden(parent, *args, **kwargs)
    dlg.setFileMode(dlg.Directory)
    dlg.setOption(dlg.ShowDirsOnly, True)

    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()[0]
    return str()

def getOpenFileNames(parent, *args, **kwargs):
    """
    Workaround to give control about hidden files
    """
    dlg = FileDialogShowHidden(parent, *args, **kwargs)
    dlg.setFileMode(dlg.ExistingFiles)

    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()
    return [str(), ]

def getOpenFileName(parent, *args, **kwargs):
    """
    Workaround to give control about hidden files
    """
    dlg = FileDialogShowHidden(parent, *args, **kwargs)
    dlg.setFileMode(dlg.ExistingFile)

    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()[0]
    return str()

def hiddenFiles(parent):
    try:
        return parent.parent.showHiddenFiles
    except: pass
    try:
        return parent.showHiddenFiles
    except: pass
    return False

def createQApplication(app_name = 'Back In Time'):
    global qapp
    try:
        return qapp
    except NameError:
        pass
    if Version(QT_VERSION_STR) >= Version('5.6') and \
        hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    qapp = QApplication(sys.argv)
    qapp.setApplicationName(app_name)
    try:
        if tools.isRoot():
            logger.debug("Trying to set App ID for root user")
            qapp.setDesktopFileName("backintime-qt-root")
        else:
            logger.debug("Trying to set App ID for non-privileged user")
            qapp.setDesktopFileName("backintime-qt")
    except Exception as e:
        logger.warning("Could not set App ID (required for Wayland App icon and more)")
        logger.warning("Reason: " + repr(e))
    qapp.setDesktopFileName("backintime-qt")
    if os.geteuid() == 0 and                                   \
        qapp.style().objectName().lower() == 'windows' and  \
        'GTK+' in QStyleFactory.keys():
            qapp.setStyle('GTK+')
    return qapp

def translator():
    translator = QTranslator()
    locale = QLocale.system().name()
    translator.load('qt_%s' % locale,
        			QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    return translator

def indexFirstColumn(idx):
    if idx.column() > 0:
        idx = idx.sibling(idx.row(), 0)
    return idx

class MyTreeView(QTreeView):
    """
    subclass QTreeView to emit a SIGNAL myCurrentIndexChanged
    if the SLOT currentChanged is called
    """
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
        self.header().setSectionsClickable(False)

        self.parent = parent
        self.snapshots = parent.snapshots
        self._resetHeaderData()

    def clear(self):
        self._resetHeaderData()
        return super(TimeLine, self).clear()

    def _resetHeaderData(self):
        self.now = date.today()
        #list of tuples with (text, startDate, endDate)
        self.headerData = []
        todayMin = datetime.combine(self.now, datetime.min.time())
        todayMax = datetime.combine(self.now, datetime.max.time())
        self.headerData.append((_('Today'), todayMin, todayMax))

        yesterdayMin = datetime.combine(self.now - timedelta(days = 1), datetime.min.time())
        yesterdayMax = datetime.combine(todayMin - timedelta(hours = 1), datetime.max.time())
        self.headerData.append((_('Yesterday'), yesterdayMin, yesterdayMax))

        thisWeekMin = datetime.combine(self.now - timedelta(self.now.weekday()), datetime.min.time())
        thisWeekMax = datetime.combine(yesterdayMin - timedelta(hours = 1), datetime.max.time())
        if thisWeekMin < thisWeekMax:
            self.headerData.append((_('This week'), thisWeekMin, thisWeekMax))

        lastWeekMin = datetime.combine(self.now - timedelta(self.now.weekday() + 7), datetime.min.time())
        lastWeekMax = datetime.combine(self.headerData[-1][1] - timedelta(hours = 1), datetime.max.time())
        self.headerData.append((_('Last week'), lastWeekMin, lastWeekMax))

        #the rest of current month. Otherwise this months header would be above today
        thisMonthMin = datetime.combine(self.now - timedelta(self.now.day - 1), datetime.min.time())
        thisMonthMax = datetime.combine(lastWeekMin - timedelta(hours = 1), datetime.max.time())
        if thisMonthMin < thisMonthMax:
            self.headerData.append((thisMonthMin.strftime('%B').capitalize(),
                                    thisMonthMin, thisMonthMax))

        #the rest of last month
        lastMonthMax = datetime.combine(self.headerData[-1][1] - timedelta(hours = 1), datetime.max.time())
        lastMonthMin = datetime.combine(date(lastMonthMax.year, lastMonthMax.month, 1), datetime.min.time())
        self.headerData.append((lastMonthMin.strftime('%B').capitalize(),
                                lastMonthMin, lastMonthMax))

    def addRoot(self, sid):
        self.rootItem = self.addSnapshot(sid)
        return self.rootItem

    @pyqtSlot(snapshots.SID)
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
            self.selectRootItem()

    def selectRootItem(self):
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
        self.setFont(0, fontNormal(self.font(0)))

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
        self.setFont(0, fontBold(self.font(0)))
        self.setBackground(0, QColor(196, 196, 196))
        self.setForeground(0, QColor(60, 60, 60))
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
        """
        QComboBox doesn't support sorting
        so this little hack is used to insert
        items in sorted order.
        """
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
        self.getName = parent.config.profileName

    def addProfileID(self, profileID):
        self.addItem(self.getName(profileID), profileID)

    def currentProfileID(self):
        return self.itemData(self.currentIndex())

    def setCurrentProfileID(self, profileID):
        for i in range(self.count()):
            if self.itemData(i) == profileID:
                self.setCurrentIndex(i)
                break

class Menu(QMenu):
    """
    Subclass QMenu to add ToolTips
    """
    def event(self, e):
        action = self.activeAction()
        if e.type() == QEvent.ToolTip and \
            action                    and \
            action.toolTip() != action.text():
                QToolTip.showText(e.globalPos(),
                                  self.activeAction().toolTip())
        else:
            QToolTip.hideText()
        return super(Menu, self).event(e)
