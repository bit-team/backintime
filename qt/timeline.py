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
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QAbstractItemView,
                             QApplication,
                             QTreeWidget,
                             QTreeWidgetItem)
import logger  # workaround. shouldn't be neccessary
import qttools
from event import Event
from qttools_path import register_backintime_path
register_backintime_path('common')

try:
    _('Warning')
except NameError:
    def _(txt):
        return txt


def start_of_day(day: date) -> datetime:
    """Add 00:00 to a date object"""
    return datetime.combine(day, datetime.min.time())


def end_of_day(day: date) -> datetime:
    """Add 23:59 to a date object"""
    return datetime.combine(day, datetime.max.time())


def _calculate_timeline_periods(today: date = date.today()
                                ) -> list[tuple[str, datetime, datetime]]:
    """Calculate timestamps for the sub-headers.

    Returns:
        A list of tuples with label, start and end datetime of each periode.
    """

    result = []

    # Today
    today_min = start_of_day(today)
    today_max = end_of_day(today)
    result.append((_('Today'), today_min, today_max))

    # Yesterday
    yesterday_min = start_of_day(today - timedelta(days=1))
    yesterday_max = end_of_day(today_min - timedelta(hours=1))
    result.append((_('Yesterday'), yesterday_min, yesterday_max))

    # This week, but not yesterday or today
    this_week_min = start_of_day(today - timedelta(today.weekday()))
    this_week_max = end_of_day(yesterday_min - timedelta(days=1))
    # Add only, if not overlapping with Yesterday
    if this_week_max > this_week_min:
        result.append((_('This week'), this_week_min, this_week_max))

    # Last week
    last_week_min = start_of_day(today - timedelta(today.weekday() + 7))
    last_week_max = end_of_day(last_week_min + timedelta(days=6))
    result.append((_('Last week'), last_week_min, last_week_max))

    # This month
    if (today.month == last_week_min.month
            and today.month == this_week_min.month):
        this_month_min = start_of_day(today.replace(day=1))
        this_month_max = end_of_day(last_week_min - timedelta(days=1))
        result.append((_('This month'), this_month_min, this_month_max))

    # Last months
    last_month_max = end_of_day(today.replace(day=1) - timedelta(days=1))
    last_month_min = start_of_day(last_month_max.replace(day=1))
    if last_month_max.date() >= last_week_min.date():
        last_month_max = end_of_day(last_week_min.date() - timedelta(days=1))
    result.append((_('Last month'), last_month_min, last_month_max))

    return result


class TimeLine(QTreeWidget):
    """A list like widget containing existing backups.

    The widget is placed on the right side of the main window.
    """
    # update_files_view = pyqtSignal(int)

    event_selection_changed = Event()
    event_now_selected = Event()
    event_backup_selected = Event()

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

        # Used headers. A of tuples with (label, start, end)
        self._header_data = None

        # Timestamp boundaries (from-to) used for the header items:
        # Today, Yesterday, This Week, Last Week, This Months, Last Months
        self._default_header_data = None

        # Helper variable. Timestamps older than this need and extra header,
        # other than a default header.
        self._specific_month_boundary = None

        self.clear_and_reset()

        self.itemSelectionChanged.connect(self._on_item_selection_changed)

    def _on_item_selection_changed(self):
        # Maybe remove
        # self.event_selection_changed.notify()
        # print('_on_item_selection_changed()')

        if self.is_now_selected():
            self.event_now_selected.notify()
            return

        self.event_backup_selected.notify(
            self.selected_backup_descriptor)

    def clear_and_reset(self):
        """Remove all entries, recalculate header data and add 'Now' entry"""

        with qttools.block_paint_updates(self):

            # # dirty signal hack
            # with self.event_selection_changed.keep_silent():
            #     with self.event_now_item_selected.keep_silent():
            #         with self.event_backup_item_selected.keep_silent():
            super().clear()
            self._header_data = []
            self._default_header_data = _calculate_timeline_periods()
            self._specific_month_boundary = self._default_header_data[-1][1]

            # "Now"
            self.addTopLevelItem(NowEntry())

    def create_backup_entry(self,
                            descriptor: str,
                            timestamp: datetime,
                            last_checked: str,
                            label: str):
        """Create and add an item representing backup.

        Also add a header if not already present.
        """
        item = BackupEntry(
            descriptor=descriptor,
            timestamp=timestamp,
            last_checked=last_checked,
            label=label
        )

        self.addTopLevelItem(item)
        self._create_header_if_necessary(timestamp)

        # Select the snapshot that was selected before
        # use FileView.preserve_selection() TODO

    def _header_in_use(self, backup_timestamp: datetime) -> bool:
        """Check if the backup timestamp fit into an already existing
        header item."""

        for _text, start, end in self._header_data:
            if start <= backup_timestamp <= end:
                return True

        return False

    def _create_header_if_necessary(self, backup_timestamp: datetime):
        """Create an header entry for the backup timestamp if necessary"""

        # Already used header fit this timestamp?
        if self._header_in_use(backup_timestamp):
            return

        # Use a default header?
        if backup_timestamp >= self._specific_month_boundary:
            for label, start, end in self._default_header_data:
                if start <= backup_timestamp <= end:
                    self._create_header_entry(label, start, end)
                    return

            logger.critical(
                'Unexpected situation. Found no default header for '
                f'{backup_timestamp=} in {self._default_header_data=}'
            )

        # Create an extra months header

        # Calculate start and end of backup months
        start = backup_timestamp.date().replace(day=1)
        end = start.replace(day=monthrange(start.year, start.month)[1])

        label = start.strftime(
            '%B' if start.year == date.today().year else '%B, %Y'
        )
        label = label.capitalize()

        self._create_header_entry(label, start_of_day(start), end_of_day(end))

    def _create_header_entry(self, label, start, end):
        item = HeaderEntry(label, end)
        self.addTopLevelItem(item)
        self._header_data.append((label, start, end))

        # DEBUG
        item.setToolTip(
            0,
            f'DEBUG - {start.strftime("%c")} to {end.strftime("%c")}'
        )

        return True

    # pylint: disable-next=invalid-name
    def checkSelection(self):  # noqa: N802
        """Slot handling selection events."""
        if self.currentItem() is None:
            # Select the 'Now' item
            self._set_current_item(self.topLevelItem(0))

    def get_all_selected_backup_descriptors(self) -> list[str]:
        """A list of all selected backup descriptors"""
        return [item.descriptor for item in self.selectedItems()]

    def is_now_selected(self) -> bool:
        """If the 'Now' item, the first in the widget, is selected."""
        model_index = self.currentIndex()
        return model_index.row() == 0

    def selected_backup_descriptor(self) -> str:
        """Return the backup descriptor of the current selected item.

        Return:
            The descriptor (formaly known as 'sid') as a string.
        """
        if self.is_now_selected():
            return None

        item = self.currentItem()

        return item.descriptor if item else None

    def selected_backup_label(self) -> str:
        """Return the label used of the current selected item.

        That is the backup descriptor plus a name string if definied
        by the user.
        """
        if self.is_now_selected():
            return None

        item = self.currentItem()

        return item.label if item else None

    def select_by_descriptor(self, backup_descriptor: str):
        """Select backup entry related to the descriptor."""
        for item in self.iter_backup_items():
            if item.descriptor == backup_descriptor:
                self._set_current_item(item)
                break

    def _set_current_item(self, item, *args, **kwargs):
        self.setCurrentItem(item, *args, **kwargs)
        self.event_selection_changed.notify()

    def _iter_items(self):
        for index in range(self.topLevelItemCount()):
            yield self.topLevelItem(index)

    def iter_backup_items(self):
        """Iterate over all items."""
        for item in self._iter_items():
            if isinstance(item, BackupEntry):
                yield item

    def _iter_header_items(self):
        for item in self._iter_items():
            if isinstance(item, HeaderEntry):
                yield item


# pylint: disable-next=too-few-public-methods
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
                 descriptor: str,
                 timestamp: datetime,
                 last_checked: str,
                 label: str):

        tooltip = _('Last check {time}').format(time=last_checked)

        super().__init__(
            timestamp=timestamp,
            tooltip=tooltip,
            label=label
        )

        self._descriptor = descriptor

    @property
    def descriptor(self) -> str:
        """Descriptor (sid) of the related backup."""
        return self._descriptor

    @property
    def label(self) -> str:
        """Text label of the entry."""
        return self.text(0)


# pylint: disable-next=too-few-public-methods
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
