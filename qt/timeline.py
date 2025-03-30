# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# File was splitted from "qt/qttools.py".
"""Time line widget.
"""
from PyQt6.QtGui import QPalette
from PyQt6.QtCore import (Qt,
                          pyqtSlot,
                          pyqtSignal)
from PyQt6.QtWidgets import (QAbstractItemView,
                             QApplication,
                             QTreeWidget,
                             QTreeWidgetItem)

from datetime import (datetime, date, timedelta)
from calendar import monthrange
from qttools_path import registerBackintimePath
registerBackintimePath('common')
import snapshots  # noqa: E402
import qttools


class TimeLine(QTreeWidget):
    updateFilesView = pyqtSignal(int)

    def __init__(self, parent):
        super(TimeLine, self).__init__(parent)
        self.setRootIsDecorated(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setHeaderLabels([_('Snapshots'), 'foo'])
        self.setSortingEnabled(True)
        self.sortByColumn(1, Qt.SortOrder.DescendingOrder)
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

        # list of tuples with (text, startDate, endDate)
        self.headerData = []

        # Today
        todayMin = datetime.combine(self.now, datetime.min.time())
        todayMax = datetime.combine(self.now, datetime.max.time())
        self.headerData.append((_('Today'), todayMin, todayMax))

        # Yesterday
        yesterdayMin = datetime.combine(
            self.now - timedelta(days=1), datetime.min.time())
        yesterdayMax = datetime.combine(
            todayMin - timedelta(hours=1), datetime.max.time())
        self.headerData.append((_('Yesterday'), yesterdayMin, yesterdayMax))

        # This week
        thisWeekMin = datetime.combine(
            self.now - timedelta(self.now.weekday()), datetime.min.time())
        thisWeekMax = datetime.combine(
            yesterdayMin - timedelta(hours=1), datetime.max.time())

        if thisWeekMin < thisWeekMax:
            self.headerData.append((_('This week'), thisWeekMin, thisWeekMax))

        # Last week
        lastWeekMin = datetime.combine(
            self.now - timedelta(self.now.weekday() + 7), datetime.min.time())
        lastWeekMax = datetime.combine(
            self.headerData[-1][1] - timedelta(hours=1), datetime.max.time())
        self.headerData.append((_('Last week'), lastWeekMin, lastWeekMax))

        # Rest of current month. Otherwise this months header would be
        # above today.
        thisMonthMin = datetime.combine(
            self.now - timedelta(self.now.day - 1), datetime.min.time())
        thisMonthMax = datetime.combine(
            lastWeekMin - timedelta(hours=1), datetime.max.time())
        if thisMonthMin < thisMonthMax:
            self.headerData.append((thisMonthMin.strftime('%B').capitalize(),
                                    thisMonthMin, thisMonthMax))

        # Rest of last month
        lastMonthMax = datetime.combine(
            self.headerData[-1][1] - timedelta(hours=1), datetime.max.time())
        lastMonthMin = datetime.combine(
            date(lastMonthMax.year, lastMonthMax.month, 1),
            datetime.min.time()
        )
        self.headerData.append((lastMonthMin.strftime('%B').capitalize(),
                                lastMonthMin, lastMonthMax))

    def addRoot(self, sid):
        self.rootItem = self.addSnapshot(sid)

        return self.rootItem

    @pyqtSlot(snapshots.SID)
    def addSnapshot(self, sid):
        item = SnapshotItem(sid)

        self.addTopLevelItem(item)

        # Select the snapshot that was selected before
        if sid == self.parent.sid:
            self.setCurrentItem(item)

        if not sid.isRoot:
            self.addHeader(sid)

        return item

    def addHeader(self, sid):

        for text, startDate, endDate in self.headerData:

            if startDate <= sid.date <= endDate:
                return self._createHeaderItem(text, endDate)

        # Any previous months
        year = sid.date.year
        month = sid.date.month

        if year == self.now.year:
            text = date(year, month, 1).strftime('%B').capitalize()
        else:
            text = date(year, month, 1).strftime('%B, %Y').capitalize()

        startDate = datetime.combine(
            date(year, month, 1), datetime.min.time())
        endDate = datetime.combine(
            date(year, month, monthrange(year, month)[1]), datetime.max.time())

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
        return self.data(0, Qt.ItemDataRole.UserRole)


class SnapshotItem(TimeLineItem):
    def __init__(self, sid):
        super(SnapshotItem, self).__init__()
        self.setText(0, sid.displayName)
        self.setFont(0, qttools.fontNormal(self.font(0)))

        self.setData(0, Qt.ItemDataRole.UserRole, sid)

        if sid.isRoot:
            self.setToolTip(0, _('This is NOT a snapshot but a live '
                                 'view of your local files'))
        else:
            self.setToolTip(
                0,
                _('Last check {time}').format(time=sid.lastChecked))

    def updateText(self):
        sid = self.snapshotID()
        self.setText(0, sid.displayName)


class HeaderItem(TimeLineItem):
    def __init__(self, name, sid):
        """
        Dev note (buhtz, 2024-01-14): Parts of that code are redundant with
        app.py::MainWindow.addPlace().
        """
        super(HeaderItem, self).__init__()
        self.setText(0, name)
        self.setFont(0, qttools.fontBold(self.font(0)))

        palette = QApplication.instance().palette()
        self.setForeground(
            0, palette.color(QPalette.ColorRole.PlaceholderText))
        self.setBackground(
            0, palette.color(QPalette.ColorRole.Window))

        self.setFlags(Qt.ItemFlag.NoItemFlags)

        self.setData(0, Qt.ItemDataRole.UserRole, sid)
