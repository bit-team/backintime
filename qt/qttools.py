# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
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
import textwrap
from typing import Union, Iterable
from PyQt6.QtGui import (QAction, QFont, QPalette, QIcon)
from PyQt6.QtCore import (QDir,
                          Qt,
                          pyqtSlot,
                          pyqtSignal,
                          QModelIndex,
                          QTranslator,
                          QLocale,
                          QLibraryInfo,
                          QT_VERSION_STR)
from PyQt6.QtWidgets import (QWidget,
                             QFileDialog,
                             QAbstractItemView,
                             QListView,
                             QTreeView,
                             QDialog,
                             QApplication,
                             QStyleFactory,
                             QTreeWidget,
                             QTreeWidgetItem,
                             QComboBox,
                             QSystemTrayIcon)
from datetime import (datetime, date, timedelta)
from calendar import monthrange
from packaging.version import Version

from qttools_path import registerBackintimePath
registerBackintimePath('common')
import snapshots  # noqa: E402
import tools  # noqa: E402
import logger  # noqa: E402
import version


# |---------------|
# | Font handling |
# |---------------|


def fontBold(font):
    font.setWeight(QFont.Weight.Bold)
    return font


def setFontBold(widget):
    widget.setFont(fontBold(widget.font()))


def fontNormal(font):
    font.setWeight(QFont.Weight.Normal)
    return font


def setFontNormal(widget):
    widget.setFont(fontNormal(widget.font()))


def can_render(string, widget):
    """Check if the string can be rendered by the font used by the widget.

    Args:
        string(str): The string to check.
        widget(QWidget): The widget which font is used.

    Returns:
        (bool) True if the widgets font contain all given characters.
    """
    fm = widget.fontMetrics()

    for c in string:
        # Convert the unicode character to its integer representation
        # because fm.inFont() is not able to handle 2-byte characters
        if not fm.inFontUcs4(ord(c)):
            return False

    return True


# |--------------------------------|
# | Widget modification & creation |
# |--------------------------------|

def set_wrapped_tooltip(widget: QWidget,
                        tooltip: Union[str, Iterable[str]],
                        wrap_length: int=72):
    """Add a tooltip to the widget but insert line breaks when appropriated.

    If a list of strings is provided, each string is wrapped individually and
    then joined with a line break.

    Args:
        widget: The widget to which a tooltip should be added.
        tooltip: The tooltip as string or iterable of strings.
        wrap_length: Every line is at most this lengths.
    """
    # Always use tuple or list
    if isinstance(tooltip, str):
        tooltip = (tooltip, )

    result = []
    for paragraph in tooltip:
        result.append('\n'.join(
            textwrap.wrap(paragraph, wrap_length)
        ))

    widget.setToolTip('\n'.join(result))



def update_combo_profiles(config, combo_profiles, current_profile_id):
    """
    Updates the combo box with profiles.

    :param config: Configuration object with access to profile data.
    :param combo_profiles: The combo box widget to be updated.
    :param current_profile_id: The ID of the current profile to be selected.
    """
    profiles = config.profilesSortedByName()
    for profile_id in profiles:
        combo_profiles.addProfileID(profile_id)
        if profile_id == current_profile_id:
            combo_profiles.setCurrentProfileID(profile_id)

# |---------------------|
# | Misc / Uncatgorized |
# |---------------------|


class FileDialogShowHidden(QFileDialog):
    """File dialog able to display hidden files."""

    def __init__(self, parent, *args, **kwargs):
        super(FileDialogShowHidden, self).__init__(parent, *args, **kwargs)

        self.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self.setOption(QFileDialog.Option.HideNameFilterDetails, True)

        showHiddenAction = QAction(self)
        showHiddenAction.setShortcut('Ctrl+H')
        showHiddenAction.triggered.connect(self.toggleShowHidden)
        self.addAction(showHiddenAction)

        self.showHidden(hiddenFiles(parent))

    def showHidden(self, enable):

        if enable:
            self.setFilter(self.filter() | QDir.Filter.Hidden)
        elif self.filter() & QDir.Filter.Hidden:
            self.setFilter(self.filter() ^ QDir.Filter.Hidden)

    def toggleShowHidden(self):
        self.showHidden(not QDir.Filter(self.filter() & QDir.Filter.Hidden))


def getExistingDirectories(parent, *args, **kwargs):
    """Workaround for selecting multiple directories adopted from
    http://www.qtcentre.org/threads/34226-QFileDialog-select-multiple-directories?p=158482#post158482
    This also give control about hidden folders
    """

    dlg = FileDialogShowHidden(parent, *args, **kwargs)

    dlg.setFileMode(dlg.FileMode.Directory)
    dlg.setOption(dlg.Option.ShowDirsOnly, True)

    mode = QAbstractItemView.SelectionMode.ExtendedSelection
    dlg.findChildren(QListView)[0].setSelectionMode(mode)
    dlg.findChildren(QTreeView)[0].setSelectionMode(mode)

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.selectedFiles()

    return [str(), ]


def getExistingDirectory(parent, *args, **kwargs):
    """Workaround to give control about hidden folders"""

    dlg = FileDialogShowHidden(parent, *args, **kwargs)

    dlg.setFileMode(dlg.FileMode.Directory)
    dlg.setOption(dlg.Option.ShowDirsOnly, True)

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.selectedFiles()[0]

    return str()


def getOpenFileNames(parent, *args, **kwargs):
    """
    Workaround to give control about hidden files
    """
    dlg = FileDialogShowHidden(parent, *args, **kwargs)
    dlg.setFileMode(dlg.FileMode.ExistingFiles)

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.selectedFiles()
    return [str(), ]


def getOpenFileName(parent, *args, **kwargs):
    """Workaround to give control about hidden files"""

    dlg = FileDialogShowHidden(parent, *args, **kwargs)
    dlg.setFileMode(dlg.FileMode.ExistingFile)

    if dlg.exec() == QDialog.DialogCode.Accepted:
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
        # For more details see our X11/Wayland/Qt documentation in the
        # directory doc/maintain
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

    # Release Candidate indicator
    if version.is_release_candidate():
        app_name = f'{app_name} -- RELEASE CANDIDATE -- ' \
                   f'({version.__version__})'

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
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))

    if rc is False:
        logger.warning(
            'PyQt was not able to install a translator for language code '
            f'"{language_code}". Deactivate translation and falling back to '
            'the source language (English).')

    tools.set_lc_time_by_language_code(language_code)

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
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
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
        self.setFont(0, fontNormal(self.font(0)))

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
        self.setFont(0, fontBold(self.font(0)))

        palette = QApplication.instance().palette()
        self.setForeground(
            0, palette.color(QPalette.ColorRole.PlaceholderText))
        self.setBackground(
            0, palette.color(QPalette.ColorRole.Window))

        self.setFlags(Qt.ItemFlag.NoItemFlags)

        self.setData(0, Qt.ItemDataRole.UserRole, sid)


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
