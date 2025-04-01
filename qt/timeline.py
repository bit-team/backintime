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
from datetime import (datetime, date, timedelta)
from calendar import monthrange
from PyQt6.QtGui import QPalette
from PyQt6.QtCore import (Qt,
                          pyqtSlot,
                          pyqtSignal)
from PyQt6.QtWidgets import (QAbstractItemView,
                             QApplication,
                             QTreeWidget,
                             QTreeWidgetItem)
import snapshots
import qttools
from qttools_path import registerBackintimePath
registerBackintimePath('common')


class TimeLine(QTreeWidget):
    """A list like widget containing existing backups.

    The widget is placed on the right side of the main window.
    """
    updateFilesView = pyqtSignal(int)

    def __init__(self, parent):
        super().__init__(parent)
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
        self._root_item = None
        self._reset_header_data()

    def clear(self):
        """Clear all entries from the widget."""
        self._reset_header_data()
        return super().clear()

    def _reset_header_data(self):
        self.now = date.today()

        # list of tuples with (text, startDate, endDate)
        self._header_data = []

        # Today
        today_min = datetime.combine(self.now, datetime.min.time())
        today_max = datetime.combine(self.now, datetime.max.time())
        self._header_data.append((_('Today'), today_min, today_max))

        # Yesterday
        yesterday_min = datetime.combine(
            self.now - timedelta(days=1), datetime.min.time())
        yesterday_max = datetime.combine(
            today_min - timedelta(hours=1), datetime.max.time())
        self._header_data.append(
            (_('Yesterday'), yesterday_min, yesterday_max))

        # This week
        this_week_min = datetime.combine(
            self.now - timedelta(self.now.weekday()), datetime.min.time())
        this_week_max = datetime.combine(
            yesterday_min - timedelta(hours=1), datetime.max.time())

        if this_week_min < this_week_max:
            self._header_data.append(
                (_('This week'), this_week_min, this_week_max))

        # Last week
        last_week_min = datetime.combine(
            self.now - timedelta(self.now.weekday() + 7), datetime.min.time())
        last_week_max = datetime.combine(
            self._header_data[-1][1] - timedelta(hours=1), datetime.max.time())
        self._header_data.append(
            (_('Last week'), last_week_min, last_week_max))

        # Rest of current month. Otherwise this months header would be
        # above today.
        this_month_min = datetime.combine(
            self.now - timedelta(self.now.day - 1), datetime.min.time())
        this_month_max = datetime.combine(
            last_week_min - timedelta(hours=1), datetime.max.time())
        if this_month_min < this_month_max:
            self._header_data.append((
                this_month_min.strftime('%B').capitalize(),
                this_month_min,
                this_month_max))

        # Rest of last month
        last_month_max = datetime.combine(
            self._header_data[-1][1] - timedelta(hours=1), datetime.max.time())
        last_month_min = datetime.combine(
            date(last_month_max.year, last_month_max.month, 1),
            datetime.min.time()
        )
        self._header_data.append((
            last_month_min.strftime('%B').capitalize(),
            last_month_min,
            last_month_max))

    def add_root(self, sid):
        """Dev note: What is 'root' in this context?

        Args:
            sid: Snapshot ID

        Returns:
            The root item itself.
        """
        self._root_item = self.addSnapshot(sid)

        return self._root_item

    @pyqtSlot(snapshots.SID)
    def addSnapshot(self, sid):  # pylint: disable=invalid-name
        """Slot to handle selection of snapshots."""
        item = SnapshotItem(sid)

        self.addTopLevelItem(item)

        # Select the snapshot that was selected before
        if sid == self.parent.sid:
            self._set_current_item(item)

        if not sid.isRoot:
            self.add_header(sid)

        return item

    def add_header(self, sid):
        """Add an entry as a header item."""

        for text, start_date, end_date in self._header_data:
            if start_date <= sid.date <= end_date:
                self._create_header_item(text, end_date)
                return

        # Any previous months
        year = sid.date.year
        month = sid.date.month

        if year == self.now.year:
            text = date(year, month, 1).strftime('%B').capitalize()
        else:
            text = date(year, month, 1).strftime('%B, %Y').capitalize()

        start_date = datetime.combine(
            date(year, month, 1), datetime.min.time())
        end_date = datetime.combine(
            date(year, month, monthrange(year, month)[1]), datetime.max.time())

        if self._create_header_item(text, end_date):
            self._header_data.append((text, start_date, end_date))

    def _create_header_item(self, text, end_date):
        for item in self._iter_header_items():
            if item.snapshot_id.date == end_date:
                return False

        item = HeaderItem(text, snapshots.SID(end_date, self.parent.config))
        self.addTopLevelItem(item)

        return True

    @pyqtSlot()
    def checkSelection(self):  # pylint: disable=invalid-name
        """Slot handling selection events."""
        if self.currentItem() is None:
            self.select_root_item()

    def select_root_item(self):
        """Dev note: Don't know what 'root' means in this context."""
        self._set_current_item(self._root_item)

        if not self.parent.sid.isRoot:
            self.parent.sid = self._root_item.snapshot_id
            self.updateFilesView.emit(2)

    def selected_snapshot_ids(self):
        """Snapshot IDs of all selected entries."""
        return [i.snapshot_id for i in self.selectedItems()]

    def current_snapshot_id(self):
        """Snapshot ID of current selected entry."""
        item = self.currentItem()

        return item.snapshot_id if item else None

    def set_current_snapshot_id(self, sid):
        """Select entry related to the snapshot ID."""
        for item in self._iter_items():

            if item.snapshot_id == sid:
                self._set_current_item(item)
                break

    def _set_current_item(self, item, *args, **kwargs):
        self.setCurrentItem(item, *args, **kwargs)

        if self.parent.sid != item.snapshot_id:
            self.parent.sid = item.snapshot_id
            self.updateFilesView.emit(2)

    def _iter_items(self):
        for index in range(self.topLevelItemCount()):
            yield self.topLevelItem(index)

    def iter_snapshot_items(self):
        """Iterate over all items."""
        for item in self._iter_items():
            if isinstance(item, SnapshotItem):
                yield item

    def _iter_header_items(self):
        for item in self._iter_items():
            if isinstance(item, HeaderItem):
                yield item


class TimeLineItem(QTreeWidgetItem):
    """Base class for TimeLine entry widgets.

    Dev note (buhtz, 2025-03): I don't see a need for this. SnapshotItem and
    HeaderItem can directely derive from QTreeWidgetItem.
    """

    def __lt__(self, other):
        return self.snapshot_id < other.snapshot_id

    @property
    def snapshot_id(self):
        """Id of the related snapshot."""
        return self.data(0, Qt.ItemDataRole.UserRole)


class SnapshotItem(TimeLineItem):
    """Snapshot entry widget used in TimeLine."""

    def __init__(self, sid):
        super().__init__()
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

    def update_text(self):
        """Update the widgets text with its snapshots displayName."""
        sid = self.snapshot_id
        self.setText(0, sid.displayName)


class HeaderItem(TimeLineItem):  # pylint: disable=too-few-public-methods
    """Header entry widget used in TimeLine."""

    def __init__(self, name, sid):
        """
        Dev note (buhtz, 2024-01-14): Parts of that code are redundant with
        app.py::MainWindow.addPlace().
        """
        super().__init__()
        self.setText(0, name)
        self.setFont(0, qttools.fontBold(self.font(0)))

        palette = QApplication.instance().palette()
        self.setForeground(
            0, palette.color(QPalette.ColorRole.PlaceholderText))
        self.setBackground(
            0, palette.color(QPalette.ColorRole.Window))

        self.setFlags(Qt.ItemFlag.NoItemFlags)

        self.setData(0, Qt.ItemDataRole.UserRole, sid)
