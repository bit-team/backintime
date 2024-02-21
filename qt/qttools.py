#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar
#    Reitze
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

"""Some helper functions and additional classes in context of Qt.

    - Helpers for Qt Fonts.
    - Helpers about path manipulation.
    - FiledialogShowHidden
    - MyTreeView (used RestoreConfigDialog)
    - TimeLine (might be the snapshot list in the left part of the GUI)
        - TimeLineItem, SnapshotItem, HeaderItem
    - SortedcomboBox, SnapshotCombo, ProfileCombo
    - Menu (tooltips in menus)

"""
import os
import sys

from PyQt5.QtGui import (QFont, QColor, QKeySequence, QIcon)
from PyQt5.QtCore import (QDir, Qt, pyqtSlot, pyqtSignal, QModelIndex,
                          QTranslator, QLocale, QLibraryInfo,
                          QT_VERSION_STR)
from PyQt5.QtWidgets import (QFileDialog, QAbstractItemView, QListView,
                             QTreeView, QDialog, QApplication, QStyleFactory,
                             QTreeWidget, QTreeWidgetItem, QComboBox,
                             QAction, QSystemTrayIcon, QWidget)
from datetime import (datetime, date, timedelta)
from calendar import monthrange
from packaging.version import Version

from qttools_path import registerBackintimePath
registerBackintimePath('common')
import snapshots  # noqa: E402
import tools  # noqa: E402
import logger  # noqa: E402


# |---------------|
# | Font handling |
# |---------------|


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


def can_render(string, widget):
    """Check if the string can be rendered by the font used by the widget.

    Args:
        string(str): The string to check.
        widget(QWidget): The widget which font is used.

    Returns:
        (bool) True if the widgets font contain all givin characters.
    """
    fm = widget.fontMetrics()

    for c in string:
        # Convert the unicode character to its integer representation
        # because fm.inFont() is not able to handle 2-byte characters
        if not fm.inFontUcs4(ord(c)):
            return False

    return True


# |---------------------|
# | Misc / Uncatgorized |
# |---------------------|


def equalIndent(*args):
    width = 0

    for widget in args:
        widget.setMinimumWidth(0)
        width = max(width, widget.sizeHint().width())

    if len(args) > 1:
        for widget in args:
            widget.setMinimumWidth(width)


class FileDialogShowHidden(QFileDialog):
    """File dialog able to display hidden files."""

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
    """Workaround for selecting multiple directories adopted from
    http://www.qtcentre.org/threads/34226-QFileDialog-select-multiple-directories?p=158482#post158482
    This also give control about hidden folders
    """

    dlg = FileDialogShowHidden(parent, *args, **kwargs)

    dlg.setFileMode(dlg.Directory)
    dlg.setOption(dlg.ShowDirsOnly, True)

    mode = QAbstractItemView.ExtendedSelection
    dlg.findChildren(QListView)[0].setSelectionMode(mode)
    dlg.findChildren(QTreeView)[0].setSelectionMode(mode)

    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()

    return [str(), ]


def getExistingDirectory(parent, *args, **kwargs):
    """Workaround to give control about hidden folders"""

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
    """Workaround to give control about hidden files"""

    dlg = FileDialogShowHidden(parent, *args, **kwargs)
    dlg.setFileMode(dlg.ExistingFile)

    if dlg.exec_() == QDialog.Accepted:
        return dlg.selectedFiles()[0]

    return str()


def hiddenFiles(parent):

    try:
        return parent.parent.showHiddenFiles
    except Exception:
        pass

    try:
        return parent.showHiddenFiles
    except Exception:
        pass

    return False


def createQApplication(app_name='Back In Time'):

    global qapp

    try:
        return qapp  # "singleton pattern": Reuse already instantiated qapp
    except NameError:
        pass

    if (Version(QT_VERSION_STR) >= Version('5.6')
            and hasattr(Qt, 'AA_EnableHighDpiScaling')):

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    qapp = QApplication(sys.argv)

    qt_platform_name = ""

    try:
        # The platform name indicates eg. wayland vs. X11, see also:
        # https://doc.qt.io/qt-5/qguiapplication.html#platformName-prop
        # For more details see our X11/Wayland/Qt5 documentation the doc-dev
        # folder
        qt_platform_name = qapp.platformName()
        logger.debug(f"QT QPA platform plugin: {qt_platform_name}")
        logger.debug(
            "QT_QPA_PLATFORMTHEME="
            f"{os.environ.get('QT_QPA_PLATFORMTHEME') or '<not set>'}")

        # styles and themes determine the look & feel of the GUI
        logger.debug(
            "QT_STYLE_OVERRIDE="
            f"{os.environ.get('QT_STYLE_OVERRIDE') or '<not set>'}")
        logger.debug(f"QT active style: {qapp.style().objectName()}")
        logger.debug(f"QT fallback style: {QIcon.fallbackThemeName()}")
        logger.debug(f"QT supported styles: {QStyleFactory.keys()}")
        logger.debug(f"themeSearchPaths: {str(QIcon.themeSearchPaths())}")
        logger.debug(
            f"fallbackSearchPaths: {str(QIcon.fallbackSearchPaths())}")

        # The Back In Time system tray icon can only be shown if the desktop
        # environment supports this
        logger.debug("Is SystemTray available: "
                     f"{str(QSystemTrayIcon.isSystemTrayAvailable())}")

    except Exception as e:
        logger.debug(
            f"Error reading QT QPA platform plugin or style: {repr(e)}")

    qapp.setApplicationName(app_name)

    try:

        if tools.isRoot():
            qapp.setApplicationName(app_name + " (root)")
            logger.debug("Trying to set App ID for root user")
            qapp.setDesktopFileName("backintime-qt-root")

        else:
            logger.debug("Trying to set App ID for non-privileged user")
            qapp.setDesktopFileName("backintime-qt")

    except Exception as e:
        logger.warning(
            "Could not set App ID (required for Wayland App icon and more)")
        logger.warning("Reason: " + repr(e))

    if (os.geteuid() == 0
            and qapp.style().objectName().lower() == 'windows'
            and 'GTK+' in QStyleFactory.keys()):

        qapp.setStyle('GTK+')

    # With "--debug" arg show the QT QPA platform name in the main window's
    # title
    if logger.DEBUG:
        qapp.setApplicationName(
            f"{qapp.applicationName()} [{qt_platform_name}]")

    return qapp


def initiate_translator(language_code: str) -> QTranslator:
    """Creating an Qt related translator.

    Args:
        language_code: Language code to use (based on ISO-639-1).

    This is done beside the primarily used GNU gettext because Qt need to
    translate its own default elements like Yes/No-buttons. The systems
    current local is used when no language code is provided. Translation is
    deactivated if language code is unknown.
    """

    translator = QTranslator()

    if language_code:
        logger.debug(f'Language code "{language_code}".')
    else:
        logger.debug('No language code. Use systems current locale.')
        language_code = QLocale.system().name()

    rc = translator.load(
        f'qt_{language_code}',
        QLibraryInfo.location(QLibraryInfo.TranslationsPath))

    if rc is False:
        logger.warning(
            'PyQt was not able to install a translator for language code '
            f'"{language_code}". Deactivate translation and falling back to '
            'the source language (English).')

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
        self.setHeaderLabels([_('Snapshots'), 'foo'])
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
        return self.data(0, Qt.UserRole)


class SnapshotItem(TimeLineItem):
    def __init__(self, sid):
        super(SnapshotItem, self).__init__()
        self.setText(0, sid.displayName)
        self.setFont(0, fontNormal(self.font(0)))

        self.setData(0, Qt.UserRole, sid)

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
        super(HeaderItem, self).__init__()
        self.setText(0, name)
        self.setFont(0, fontBold(self.font(0)))
        self.setBackground(0, QColor(196, 196, 196))
        self.setForeground(0, QColor(60, 60, 60))
        self.setFlags(Qt.NoItemFlags)

        self.setData(0, Qt.UserRole, sid)


class SortedComboBox(QComboBox):
    # Prevent inserting items abroad from addItem because this would break
    # sorting
    insertItem = NotImplemented

    def __init__(self, parent=None):
        super(SortedComboBox, self).__init__(parent)
        self.sortOrder = Qt.AscendingOrder
        self.sortRole = Qt.DisplayRole

    def addItem(self, text, userData=None):
        """
        QComboBox doesn't support sorting
        so this little hack is used to insert
        items in sorted order.
        """

        if self.sortRole == Qt.UserRole:
            sortObject = userData
        else:
            sortObject = text

        the_list = [
            self.itemData(i, self.sortRole) for i in range(self.count())]
        the_list.append(sortObject)
        the_list.sort(reverse=self.sortOrder)
        index = the_list.index(sortObject)

        super(SortedComboBox, self).insertItem(index, text, userData)

    def checkSelection(self):
        if self.currentIndex() < 0:
            self.setCurrentIndex(0)


class SnapshotCombo(SortedComboBox):
    def __init__(self, parent=None):
        super(SnapshotCombo, self).__init__(parent)
        self.sortOrder = Qt.DescendingOrder
        self.sortRole = Qt.UserRole

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


# Since Qt 5.1 not needed anymore.
# Use menu.setToolTipsVisible(True).
# See https://bugreports.qt.io/browse/QTBUG-13663
# class Menu(QMenu):
#     """
#     Subclass QMenu to add ToolTips
#     """

#     def event(self, e):
#         action = self.activeAction()

#         if (e.type() == QEvent.ToolTip
#                 and action
#                 and action.toolTip() != action.text()):

#             QToolTip.showText(e.globalPos(), self.activeAction().toolTip())

#         else:
#             QToolTip.hideText()

#         return super(Menu, self).event(e)
