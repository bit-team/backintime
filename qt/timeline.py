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
# File was split from "qt/qttools.py".
"""Time line widget.
"""
from datetime import (datetime, date, timedelta)
from calendar import monthrange
from PyQt6.QtGui import QFont, QPalette
from PyQt6.QtCore import (Qt,
                          pyqtSlot,
                          QSignalBlocker)
from PyQt6.QtWidgets import (QAbstractItemView,
                             QApplication,
                             QTreeWidget,
                             QTreeWidgetItem)
import snapshots
import qttools
from event import Event
from qttools_path import register_backintime_path
register_backintime_path('common')

try:
    _('Warning')
except NameError:
    _ = lambda s: s


def _calculate_timeline_periods(now: date = date.today()
                                ) -> list[tuple[str, datetime, datetime]]:
    """Calculate timestamps for the sub-headers.

    Returns:
        A list of tuples with label, start and end datetime of each periode.
    """

    def start_of_day(day: date) -> datetime:
        return datetime.combine(day, datetime.min.time())

    def end_of_day(day: date) -> datetime:
        return datetime.combine(day, datetime.max.time())

    result = []

    # Today
    today_min = start_of_day(now)
    today_max = end_of_day(now)
    result.append((_('Today'), today_min, today_max))

    # Yesterday
    yesterday_min = start_of_day(now - timedelta(days=1))
    yesterday_max = end_of_day(today_min - timedelta(hours=1))
    result.append((_('Yesterday'), yesterday_min, yesterday_max))

    # This week, but not yesterday or today
    this_week_min = start_of_day(now - timedelta(now.weekday()))
    this_week_max = end_of_day(yesterday_min - timedelta(days=1))
    result.append((_('This week'), this_week_min, this_week_max))

    # Last week
    last_week_min = start_of_day(now - timedelta(now.weekday() + 7))
    last_week_max = end_of_day(last_week_min + timedelta(days=6))
    result.append((_('Last week'), last_week_min, last_week_max))

    # This month
    if now.month == last_week_min.month and now.month == this_week_min.month:
        this_month_min = start_of_day(now.replace(day=1))
        this_month_max = end_of_day(last_week_min - timedelta(days=1))
        result.append((_('This month'), this_month_min, this_month_max))

    # Last months
    last_month_max = end_of_day(now.replace(day=1) - timedelta(days=1))
    last_month_min = start_of_day(last_month_max.replace(day=1))
    result.append((_('Last month'), last_month_min, last_month_max))

    return result


class TimeLine(QTreeWidget):
    """A list like widget containing existing backups.

    The widget is placed on the right side of the main window.
    """
    # update_files_view = pyqtSignal(int)

    event_selection_changed = Event()
    event_now_item_selected = Event()
    event_backup_item_selected = Event()

    def __init__(self, parent):
        super().__init__(parent)
        self.setRootIsDecorated(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)

        self.setHeaderLabels([_('Backups')])

        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.DescendingOrder)

        self.header().setSectionsClickable(False)

        self.parent = parent
        self.snapshots = parent.snapshots

        # That timestmap is used to decide if a backup needs an extra
        # header item. It is previous to the last month or older.
        self._specific_month_boundary = None

        self._calculate_header_data()

        self.itemSelectionChanged.connect(self._on_item_selection_changed)

    def _on_item_selection_changed(self):
        # Maybe remove
        # self.event_selection_changed.notify()
        # print('_on_item_selection_changed()')

        if self.is_now_selected():
            self.event_now_item_selected.notify()
            return

        self.event_backup_item_selected.notify(self.current_backup_descriptor)

    def clear_and_rebuild_header(self):
        # blocker = QSignalBlocker(self)
        # import traceback
        # traceback.print_stack(limit=5)

        with qttools.block_paint_updates(self):

            # # dirty signal hack
            # with self.event_selection_changed.keep_silent():
            #     with self.event_now_item_selected.keep_silent():
            #         with self.event_backup_item_selected.keep_silent():
            self._calculate_header_data()
            super().clear()

            # "Now"
            self.addTopLevelItem(NowEntry())

            for label, start, end in self._header_data:
                item = HeaderEntry(label=label, timestamp=end)
                # DEBUG
                item.setToolTip(0, f'DEBUG - {start.strftime("%c")} to {end.strftime("%c")}')
                self.addTopLevelItem(item)

    def _add_header_data(self, label: str, start: datetime, end: datetime):
        if start >= end:
            return

        self._header_data.append((label, start, end))

    def _calculate_header_data(self):
        """Calculate timestamps for the sub-headers.
        """
        self.now = date.today()
        self._specific_month_boundary = None

        # list of tuples with (text, startDate, endDate)
        self._header_data = []

        # Today
        today_min = self.start_of_day(self.now)
        today_max = self.end_of_day(self.now)
        self._add_header_data(_('Today'), today_min, today_max)

        # Yesterday
        yesterday_min = self.start_of_day(self.now - timedelta(days=1))
        yesterday_max = self.end_of_day(today_min - timedelta(hours=1))
        self._add_header_data(_('Yesterday'), yesterday_min, yesterday_max)

        # This week
        this_week_min = self.start_of_day(self.now - timedelta(self.now.weekday()))
        this_week_max = self.end_of_day(yesterday_min - timedelta(hours=1))
        self._add_header_data(_('This week'), this_week_min, this_week_max)

        # Last week
        last_week_min = self.start_of_day(self.now - timedelta(self.now.weekday() + 7))
        last_week_max = self.end_of_day(self._header_data[-1][1] - timedelta(hours=1))
        self._add_header_data(_('Last week'), last_week_min, last_week_max)

        # Rest of current month, but only if Yesterday, This Week and
        # Last Week do not touch the last month.
        this_month_min = self.start_of_day(self.now.replace(day=1))
        this_month_max = self.end_of_day(this_week_min - timedelta(hours=1))
        self._add_header_data(
            _('This month'),  # this_month_min.strftime('%B').capitalize(),
            this_month_min,
            this_month_max
        )

        # Rest of last month (before last week)
        last_month_max = self.end_of_day(last_week_min) - timedelta(microseconds=1)
        last_month_min = self.start_of_day(last_month_max.date().replace(day=1))
        self._add_header_data(
            _('Last month'),  # last_month_min.strftime('%B').capitalize(),
            last_month_min,
            last_month_max
        )

        # DEBUG
        # for a, b, c in self._header_data:
        #     print(a, b, c)

        self._specific_month_boundary = last_month_min

    @pyqtSlot(snapshots.SID)
    # pylint: disable-next=invalid-name
    def addSnapshot(self, sid):  # noqa: N802
        """Slot to handle selection of snapshots."""
        # print(f'addSnapshot() :: {sid=}')
        item = BackupEntry(
            backup_descriptor=sid.get_descriptor(),
            backup_timestamp=sid.get_timestamp(),
            last_checked=sid.lastChecked,
            label=sid.displayName,
        )

        self.addTopLevelItem(item)

        # Select the snapshot that was selected before
        if sid == self.parent.sid:
            self._set_current_item(item)

        self._create_header_if_necessary(sid.get_timestamp())

        return item

    def _header_exists(self, backup_timestamp: datetime) -> bool:
        # Not necessary. The timestamps is before the boundary of existing
        # default headers.
        if backup_timestamp >= self._specific_month_boundary:
            return True

        # maybe an extra/older months exists?
        for _text, start, end in self._header_data:
            if start <= backup_timestamp <= end:
                return True

        return False

    def _create_header_if_necessary(self, backup_timestamp: datetime):
        """Create an header entry for the backup timestamp if necessary"""

        if self._header_exists(backup_timestamp):
            return

        # Any previous months
        year = backup_timestamp.year
        month = backup_timestamp.month

        # Calculate start and end of backup months
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        label = first_day.strftime('%B' if year == self.now.year else '%B, %Y')
        label = label.capitalize()

        first_day = self.start_of_day(first_day)
        last_day = self.end_of_day(last_day)

        self._add_header_data(label, first_day, last_day)

        item = HeaderEntry(label=label, timestamp=last_day)
        self.addTopLevelItem(item)

    def _remove_consecutive_header_entries(self):
        """Remove header items without backup entries."""
        previous_was_header = False
        to_remove = []

        for idx in range(self.topLevelItemCount()):
            item = self.topLevelItem(idx)

            if not isinstance(item, HeaderEntry):
                previous_was_header = False
                continue

            if previous_was_header:
                to_remove.append(idx)

            previous_was_header = True

        # Remove from behind
        for idx in reversed(to_remove):
            self.takeTopLevelItem(idx)

    def _create_header_entry(self, text, end_date):
        # Don't create if it still exists.
        for item in self._iter_header_items():
            if item.snapshot_id.date == end_date:
                return False

        item = HeaderEntry(text, snapshots.SID(end_date, self.parent.config))
        self.addTopLevelItem(item)

        return True

    # pylint: disable-next=invalid-name
    def checkSelection(self):  # noqa: N802
        """Slot handling selection events."""
        if self.currentItem() is None:
            self.select_root_item()

    def select_root_item(self):
        self._set_current_item(self.topLevelItem(0))

    def selected_snapshot_ids(self):
        """Snapshot IDs of all selected entries."""
        return [i.snapshot_id for i in self.selectedItems()]

    def is_now_selected(self) -> bool:
        """If the 'Now' item, the first in the widget, is selected."""
        model_index = self.currentIndex()
        return model_index.row() == 0

    def current_backup_descriptor(self) -> str:
        if self.is_now_selected():
            return None

        item = self.currentItem()

        return item.backup_descriptor if item else None

    def current_backup_label(self) -> str:
        if self.is_now_selected():
            return None

        item = self.currentItem()

        return item.backup_label if item else None

    def current_snapshot_id(self):
        return self.current_backup_descriptor()

    def set_current_snapshot_id(self, sid):
        """Select entry related to the snapshot ID."""
        for item in self._iter_items():

            if item.snapshot_id == sid:
                self._set_current_item(item)
                break

    def _set_current_item(self, item, *args, **kwargs):
        self.setCurrentItem(item, *args, **kwargs)

        # if self.parent.sid != item.snapshot_id:
        #     self.parent.sid = item.snapshot_id
            # self.update_files_view.emit(2)
        #    self.event_selection_changed.notify()
        self.event_selection_changed.notify()

    def _iter_items(self):
        for index in range(self.topLevelItemCount()):
            yield self.topLevelItem(index)

    def iter_snapshot_items(self):
        """Iterate over all items."""
        for item in self._iter_items():
            if isinstance(item, BackupEntry):
                yield item

    def _iter_header_items(self):
        for item in self._iter_items():
            if isinstance(item, HeaderEntry):
                yield item


class _TimeLineItemBase(QTreeWidgetItem):
    """Backup entry widget used in TimeLine."""

    def __init__(self,
                 timestamp: datetime,
                 tooltip: str,
                 label: str):
        super().__init__()

        if tooltip:
            self.setToolTip(0, tooltip)

        self.setText(0, label)
        self.setData(0, Qt.ItemDataRole.UserRole, timestamp)

    def __lt__(self, other):
        return self.data(0, Qt.ItemDataRole.UserRole) \
            < other.data(0, Qt.ItemDataRole.UserRole)


class BackupEntry(_TimeLineItemBase):
    """Backup entry widget used in TimeLine."""

    def __init__(self,
                 backup_descriptor: str,
                 backup_timestamp: datetime,
                 last_checked: str,
                 label: str):

        tooltip = _('Last check {time}').format(time=last_checked)

        super().__init__(
            timestamp=backup_timestamp,
            tooltip=tooltip,
            label=label
        )

        self._backup_descriptor = backup_descriptor
        self._backup_label = label

    @property
    def backup_descriptor(self) -> str:
        """Descriptor (sid) of the related backup."""
        return self._backup_descriptor


class NowEntry(_TimeLineItemBase):
    """Now entry widget used in TimeLine."""

    def __init__(self):
        super().__init__(
            timestamp=datetime.max,
            tooltip=_(
                'This is NOT a backup but a live view of the local files.'),
            label=_('Now')
        )


class HeaderEntry(_TimeLineItemBase):  # pylint: disable=too-few-public-methods
    """Header entry widget used in TimeLine."""

    def __init__(self, label: str, timestamp: datetime):
        """
        Dev note (buhtz, 2024-01-14): Parts of that code are redundant with
        app.py::MainWindow.addPlace().
        """
        super().__init__(
            timestamp=timestamp,
            tooltip=None,
            label=label
        )

        font = self.font(0)
        font.setWeight(QFont.Weight.Bold)
        self.setFont(0, font)

        palette = QApplication.instance().palette()
        self.setForeground(
            0, palette.color(QPalette.ColorRole.PlaceholderText))
        self.setBackground(
            0, palette.color(QPalette.ColorRole.AlternateBase))

        self.setFlags(Qt.ItemFlag.NoItemFlags)
