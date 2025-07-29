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
"""Some comboboxes and other widegts.

Dev note (buhtz, 2025-03: Have look at "qt/manageprofiles/combobox.py" and
consolidate if possible.
"""
import itertools
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (QCheckBox,
                             QComboBox,
                             QFrame,
                             QHBoxLayout,
                             QLabel,
                             QSizePolicy,
                             QWidget)
import qttools


class SortedComboBox(QComboBox):
    """A combo box ensuring that its items are in sorted order.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sort_order = None
        self.sort_role = None

        self.set_ascending_order()
        self.set_role(Qt.ItemDataRole.DisplayRole)

    def set_ascending_order(self, ascending: bool = True) -> None:
        """Set the sort order."""
        self.sort_order = {
            True: Qt.SortOrder.AscendingOrder,
            False: Qt.SortOrder.DescendingOrder}[ascending]

    def set_role(self, role: Qt.ItemDataRole) -> None:
        """Set item data role."""
        self.sort_role = role

    def add_item(self, text, user_data=None):
        """
        QComboBox doesn't support sorting
        so this little hack is used to insert
        items in sorted order.
        """

        if self.sort_role == Qt.ItemDataRole.UserRole:
            sort_obj = user_data
        else:
            sort_obj = text

        the_list = [
            self.itemData(i, self.sort_role) for i in range(self.count())]
        the_list.append(sort_obj)

        reverse_sort = self.sort_order == Qt.SortOrder.DescendingOrder
        the_list.sort(reverse=reverse_sort)
        idx = the_list.index(sort_obj)

        self.insertItem(idx, text, user_data)

    def check_selection(self):
        """Dev note: Not sure what it is doing or why this is needed."""
        if self.currentIndex() < 0:
            self.setCurrentIndex(0)


class SnapshotCombo(SortedComboBox):
    """A combo box containing backups (aka snapshots)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_ascending_order(False)
        self.set_role(Qt.ItemDataRole.UserRole)

    def add_snapshot_id(self, sid):
        """Add the snapshot with its ID/name."""
        self.add_item(sid.displayName, sid)

    def current_snapshot_id(self):
        """Return the ID/name of the current snapshot."""
        return self.itemData(self.currentIndex())

    def set_current_snapshot_id(self, sid):
        """Select entry by its snapshot id."""
        for idx in range(self.count()):
            if self.itemData(idx) == sid:
                self.setCurrentIndex(idx)
                break


class ProfileCombo(SortedComboBox):
    """A combo box containing profile names."""

    def __init__(self, parent):
        super().__init__(parent)
        self._config = parent.config

    def add_profile_id(self, profile_id):
        """Add item using the profiles name."""
        name = self._config.profileName(profile_id)
        self.add_item(name, profile_id)

    def current_profile_id(self):
        """Return the current selected profile id."""
        return self.itemData(self.currentIndex())

    def set_current_profile_id(self, profile_id):
        """Select the item using the given profile id."""
        for i in range(self.count()):
            if self.itemData(i) == profile_id:
                self.setCurrentIndex(i)
                break


class HLineWidget(QFrame):
    """Just a horizontal line.

    It really is the case that even in the year 2025 with Qt6 there is no
    dedicated widget class to draw a horizontal line.
    """

    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class WrappedCheckBox(QWidget):
    """A checkbox with word wrap capabilities.

    QCheckBox itself is not able to wrap text in its label, without hacks."""
    def __init__(self,
                 label: str,
                 tooltip: str = None,
                 parent: QWidget = None):
        super().__init__(parent)

        self.checkbox = QCheckBox()
        self.label = QLabel(label)

        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox, stretch=0)
        layout.addWidget(self.label, stretch=1)

        self.label.setWordWrap(True)
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.label.mouseReleaseEvent = self._slot_label_clicked

        if tooltip:
            qttools.set_wrapped_tooltip([self.checkbox, self.label], tooltip)

        # # DEBUG
        # self.setStyleSheet("background: lightblue; border: 1px solid red;")
        # self.label.setStyleSheet("background: yellow;")

    def _slot_label_clicked(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()

    @property
    def checked(self) -> bool:
        """Checked state of the check box"""
        return self.checkbox.isChecked()

    @checked.setter
    def checked(self, check: bool) -> None:
        self.checkbox.setChecked(check)


class Spinner(QLabel):
    """An activity indicator widget using unicode characters"""
    # STOP = '⠿'
    STOP = ' '

    def __init__(self,
                 parent: QWidget = None,
                 font_scale: float = None):
        super().__init__(parent)

        # self.spinner_sequence = ['◐', '◓', '◑', '◒']
        # self.spinner_sequence = ['🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖',
        #                          '🕗', '🕘', '🕙', '🕚', '🕛']

        # Unicode symbols used alternately
        self._sequence = itertools.cycle(['⠋', '⠙', '⠸', '⠴', '⠦', '⠇'])

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(Spinner.STOP)

        # font size
        if font_scale:
            font = self.font()
            font.setPointSize(int(font.pointSize() * font_scale))
            self.setFont(font)

        # cycle timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(
            lambda: self.setText(next(self._sequence)))

    def start(self, interval_ms: int = 150) -> None:
        """Start the spinner"""
        self._timer.start(interval_ms)

    def stop(self) -> None:
        """Stop the spinner using `self.STOP` as label."""
        self._timer.stop()
        self.setText(Spinner.STOP)
