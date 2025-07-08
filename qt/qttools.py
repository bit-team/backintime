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
"""Some helper functions and additional classes in context of Qt.

    - Helpers for Qt Fonts.
    - Helpers about path manipulation.
    - FiledialogShowHidden
    - Menu (tooltips in menus)
    - etc
"""
import os
import sys
import re
import json
import textwrap
from typing import Union, Iterable, Callable
from contextlib import contextmanager
from PyQt6.QtGui import QDesktopServices, QFont, QIcon
from PyQt6.QtCore import (QEvent,
                          QLibraryInfo,
                          QLocale,
                          Qt,
                          QObject,
                          QT_VERSION_STR,
                          QTranslator,
                          QUrl)
from PyQt6.QtWidgets import (QApplication,
                             QLabel,
                             QStyle,
                             QStyleFactory,
                             QSystemTrayIcon,
                             QWidget)
from packaging.version import Version
from qttools_path import registerBackintimePath
registerBackintimePath('common')
import tools  # noqa: E402
import logger  # noqa: E402
import bitbase  # noqa: E402
import version  # noqa: E402
from filedialog import FileDialog

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

_REX_RICHTEXT = re.compile(
    # begin of line
    r'^'
    # all characters, except a new line
    r'[^\n]*'
    # tag opening
    r'<'
    # every character (as tagname) except >
    r'[^>]+'
    # tag closing
    r'>')


def might_be_richtext(txt: str) -> bool:
    """Returns `True` if the text is rich text.

    Rich text is a subset of HTML used by Qt to allow text formatting. The
    function checks if the first line (before the first `\n') does contain a
    tag. A tag begins with with `<`, following by one or more characters and
    close with `>`.

    Qt itself does use `Qt::mightBeRichText()` internally but this is not
    available in PyQt for unknown reasons.

    Args:
        txt: The text to check.

    Returns:
        `True` if it looks like a rich text, otherwise `False`.
    """
    return bool(_REX_RICHTEXT.match(txt))


def set_wrapped_tooltip(widget: Union[QWidget, Iterable[QWidget]],
                        tooltip: Union[str, Iterable[str]],
                        wrap_length: int = 72):
    """Add a tooltip to the widget but insert line breaks when appropriated.

    If a list of strings is provided, each string is wrapped individually and
    then joined with a line break.

    Args:
        widget: The widget or list of widgets to which a tooltip should be
            added.
        tooltip: The tooltip as string or iterable of strings.
        wrap_length: Every line is at most this lengths.
    """

    if isinstance(widget, Iterable):
        for wdg in widget:
            set_wrapped_tooltip(wdg, tooltip, wrap_length)

        return

    # Always use tuple or list
    if isinstance(tooltip, str):
        tooltip = (tooltip, )

    # Richtext or plain text
    newline = {True: '<br>', False: '\n'}[might_be_richtext(tooltip[0])]

    result = []
    # Wrap each paragraph in itself
    for paragraph in tooltip:
        result.append('\n'.join(
            textwrap.wrap(paragraph, wrap_length)
        ))

    # glue all together
    widget.setToolTip(newline.join(result))


def update_combo_profiles(config, combo_profiles, current_profile_id):
    """
    Updates the combo box with profiles.

    :param config: Configuration object with access to profile data.
    :param combo_profiles: The combo box widget to be updated.
    :param current_profile_id: The ID of the current profile to be selected.
    """
    profiles = config.profilesSortedByName()
    for profile_id in profiles:
        combo_profiles.add_profile_id(profile_id)
        if profile_id == current_profile_id:
            combo_profiles.set_current_profile_id(profile_id)


def create_icon_label(
        icon_type: QStyle.StandardPixmap,
        icon_size: QStyle.PixelMetric = QStyle.PixelMetric.PM_LargeIconSize,
        fixed_size_widget: bool = False) -> QLabel:
    """Return a ``QLabel`` instance containing an icon.

    Args:
        icon_type: The icon, eg. info or warning.
        icon_size: Size reference.
        fixed_size_widget: Fix label size to its icon (default: False)

    Returns:
        The QLabel
    """
    style = QApplication.style()
    ico = style.standardIcon(icon_type)
    sz = style.pixelMetric(icon_size)

    pixmap = ico.pixmap(sz)

    label = QLabel()
    label.setPixmap(pixmap)

    if fixed_size_widget:
        label.setFixedSize(pixmap.size())

    return label


def create_icon_label_info(
        icon_size: QStyle.PixelMetric = QStyle.PixelMetric.PM_LargeIconSize,
        fixed_size_widget: bool = False) -> QLabel:
    """Return a QLabel with an info icon.

    See `create_icon_label` for details.
    """
    return create_icon_label(
        icon_type=QStyle.StandardPixmap.SP_MessageBoxInformation,
        icon_size=icon_size,
        fixed_size_widget=fixed_size_widget)


def create_icon_label_warning(
        icon_size: QStyle.PixelMetric = QStyle.PixelMetric.PM_LargeIconSize,
        fixed_size_widget: bool = False) -> QLabel:
    """Return a QLabel with a warning icon.

    See `create_icon_label` for details.
    """
    return create_icon_label(
        icon_type=QStyle.StandardPixmap.SP_MessageBoxWarning,
        icon_size=icon_size,
        fixed_size_widget=fixed_size_widget)


def custom_sort_order(header, loop, new_column, new_order):
    """Provides a toggled sort order across two columns for QTreeWidget."""
    if new_column == 0 and new_order == Qt.SortOrder.AscendingOrder:
        if loop:
            new_column, new_order = 1, Qt.SortOrder.AscendingOrder
            header.setSortIndicator(new_column, new_order)
            loop = False
        else:
            loop = True
    header.model().sort(new_column, new_order)
    return loop

# |---------------------|
# | Misc / Uncatgorized |
# |---------------------|


class MouseButtonEventFilter(QObject):
    """Catch mouse buttons 4 and 5 (mostly used as back and forward)
    and assign it to browse in file history.
    """

    def __init__(self,
                 back_handler: Callable,
                 forward_handler: Callable):
        # mouse button 4
        self._handle_back = back_handler
        # mouse button 5
        self._handle_forward = forward_handler

        super().__init__()

    def eventFilter(self, receiver, event):
        """Catch global input events."""

        # not a mouse press event
        if event.type() != QEvent.Type.MouseButtonPress:
            return super().eventFilter(receiver, event)

        try:
            # button 4 or 5 ?
            handler = {
                Qt.MouseButton.BackButton: self._handle_back,
                Qt.MouseButton.ForwardButton: self._handle_forward
            }[event.button()]

        except KeyError:
            pass

        else:  # no exception
            handler()
            return True

        return super().eventFilter(receiver, event)


def open_url(url: str) -> None:
    """Open an URL or URI"""
    QDesktopServices.openUrl(QUrl(url))


def user_manual_uri() -> str:
    """Return the URI to the user manual.

    If available the local URI is used otherwise the online version is.
    """
    uri = bitbase.USER_MANUAL_LOCAL_PATH.as_uri() \
        if bitbase.USER_MANUAL_LOCAL_AVAILABLE \
        else bitbase.USER_MANUAL_ONLINE_URL

    return uri


def open_user_manual() -> None:
    """Open the user manual in browser.

    If available the local manual is used otherwise the online version is
    opened.
    """
    open_url(user_manual_uri())


def getExistingDirectories(parent, title):
    """Workaround for selecting multiple directories adopted from
    http://www.qtcentre.org/threads/34226-QFileDialog-select-multiple-directories?p=158482#post158482
    This also give control about hidden folders
    """

    dlg = FileDialog(parent,
                     title=title,
                     show_hidden=True,
                     allow_multiselection=True,
                     dirs_only=True)
    result = dlg.result()

    if result:
        return result
    return [str(), ]


def getExistingDirectory(parent, title, start_dir=None):
    """Workaround to give control about hidden folders"""
    dlg = FileDialog(parent,
                     title=title,
                     show_hidden=True,
                     allow_multiselection=False,
                     dirs_only=True,
                     start_dir=start_dir)
    result = dlg.result()

    if result:
        return str(result)

    return str()


def getOpenFileNames(parent, title):
    """
    Workaround to give control about hidden files
    """
    dlg = FileDialog(parent,
                     title=title,
                     show_hidden=True,
                     allow_multiselection=True,
                     dirs_only=False)
    result = dlg.result()

    if result:
        return [str(r) for r in result]
    return [str(), ]


def getOpenFileName(parent, title, start_dir = None):
    """Workaround to give control about hidden files"""
    dlg = FileDialog(parent,
                     title=title,
                     show_hidden=True,
                     allow_multiselection=False,
                     dirs_only=False,
                     start_dir=start_dir)
    result = dlg.result()

    if result:
        return str(result)
    return str()


def _show_qt_debug_info(qapp):
    if not logger.DEBUG:
        return

    try:
        info = {
            # The platform name indicates eg. wayland vs. X11, see also:
            # https://doc.qt.io/qt-5/qguiapplication.html#platformName-prop
            # For more details see our X11/Wayland/Qt documentation in the
            # directory doc/maintain
            'QT QPA platform plugin': qapp.platformName(),
            'QT_QPA_PLATFORMTHEME': 
                os.environ.get('QT_QPA_PLATFORMTHEME', '<not set>'),
                # styles and themes determine the look & feel of the GUI
            'QT_STYLE_OVERRIDE':
                os.environ.get('QT_STYLE_OVERRIDE', '<not set>'),
            'QT active style': qapp.style().objectName(),
            'QT fallback style': QIcon.fallbackThemeName(),
            'QT supported styles': QStyleFactory.keys(),
            'themeSearchPaths': QIcon.themeSearchPaths(),
            'fallbackSearchPaths': QIcon.fallbackSearchPaths(),
            # The Back In Time system tray icon can only be shown if the desktop
            # environment supports this
            'Is SystemTray available':
                QSystemTrayIcon.isSystemTrayAvailable(),
        }

        # msg = '\n' + json.dumps(info, indent=4)
        msg = json.dumps(info)

    except Exception as exc:
        msg = f'Error reading QT QPA platform plugin or style: {exc}'

    logger.debug(msg)


def createQApplication(app_name=bitbase.APP_NAME):

    global qapp

    try:
        return qapp  # "singleton pattern": Reuse already instantiated qapp
    except NameError:
        pass

    if (Version(QT_VERSION_STR) >= Version('5.6')
            and hasattr(Qt, 'AA_EnableHighDpiScaling')):

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    qapp = QApplication(sys.argv)

    _show_qt_debug_info(qapp)

    # Release Candidate indicator
    if version.IS_RELEASE_CANDIDATE:
        app_name = f'{app_name} -- RELEASE CANDIDATE -- ' \
                   f'({version.__version__})'

    elif version.IS_UNSTABLE_DEV_VERSION:
        app_name = f'{app_name} -- UNSTABLE DEVELOPMENT ' \
                   f'VERSION -- ({version.__version__})'

    # This will influence the main window title
    qapp.setApplicationName(app_name)

    try:

        if tools.isRoot():
            qapp.setApplicationName(app_name + " (root)")
            qapp.setDesktopFileName("backintime-qt-root")

        else:
            qapp.setDesktopFileName("backintime-qt")

    except Exception as exc:
        logger.warning('Could not set App ID (required for Wayland App icon '
                       f'and more). Reason: {exc}')

    if (os.geteuid() == 0
            and qapp.style().objectName().lower() == 'windows'
            and 'GTK+' in QStyleFactory.keys()):

        qapp.setStyle('GTK+')

    # With "--debug" arg show the QT QPA platform name in the main window's
    # title
    if logger.DEBUG:
        qapp.setApplicationName(
            f'{qapp.applicationName()} '
            f'[QT QPA platform: "{qapp.platformName()}"]')

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
            'PyQt (the GUI library) could not install a translator for the '
            f'language code "{language_code}". Standard GUI elements will '
            'fall back to the source language (English). This does not '
            'affect the translation of Back In Time-specific GUI elements.')

    tools.set_locale_by_language_code(language_code)

    return translator


@contextmanager
def block_signals(widget: QWidget) -> None:
    """Context manager to temporary block Qt signals"""
    widget.blockSignals(True)

    yield

    widget.blockSignals(False)
