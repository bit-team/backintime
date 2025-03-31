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
"""Some comboboxes and other widegts.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QComboBox
from qttools_path import registerBackintimePath
registerBackintimePath('common')
import snapshots  # noqa: E402


class SortedComboBox(QComboBox):
    # Prevent inserting items abroad from addItem because this would break
    # sorting
    insertItem = NotImplemented

    def __init__(self, parent=None):
        super(SortedComboBox, self).__init__(parent)
        self.sortOrder = Qt.SortOrder.AscendingOrder
        self.sortRole = Qt.ItemDataRole.DisplayRole

    def addItem(self, text, userData=None):
        """
        QComboBox doesn't support sorting
        so this little hack is used to insert
        items in sorted order.
        """

        if self.sortRole == Qt.ItemDataRole.UserRole:
            sortObject = userData
        else:
            sortObject = text

        the_list = [
            self.itemData(i, self.sortRole) for i in range(self.count())]
        the_list.append(sortObject)

        reverse_sort = self.sortOrder == Qt.SortOrder.DescendingOrder
        the_list.sort(reverse=reverse_sort)
        index = the_list.index(sortObject)

        super(SortedComboBox, self).insertItem(index, text, userData)

    def checkSelection(self):
        if self.currentIndex() < 0:
            self.setCurrentIndex(0)


class SnapshotCombo(SortedComboBox):
    def __init__(self, parent=None):
        super(SnapshotCombo, self).__init__(parent)
        self.sortOrder = Qt.SortOrder.DescendingOrder
        self.sortRole = Qt.ItemDataRole.UserRole

    def addSnapshotID(self, sid):
        assert isinstance(sid, snapshots.SID), \
            f'sid is not snapshots.SID type: {sid}'

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


class HLineWidget(QFrame):
    """Just a horizontal line.

    It really is the case that even in the year 2025 with Qt6 there is no
    dedicated widget class to draw a horizontal line.
    """

    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
