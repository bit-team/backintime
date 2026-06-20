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
# pylint: disable=wrong-import-position,wrong-import-order
import os
import sys
import atexit
import pwd
import re
import json
import textwrap
import subprocess
import tempfile
from typing import Union, Iterable, Callable
from pathlib import Path
from contextlib import contextmanager
from textdlg import TextDialog
from PyQt6.QtGui import (QCursor,
                         QDesktopServices,
                         QGuiApplication,
                         QFontMetricsF,
                         QIcon,
                         QPalette)
from PyQt6.QtCore import (QEvent,
                          QLibraryInfo,
                          QLocale,
                          Qt,
                          QObject,
                          QTranslator,
                          QUrl)
from PyQt6.QtWidgets import (QApplication,
                             QHBoxLayout,
                             QLabel,
                             QStyle,
                             QStyleFactory,
                             QSystemTrayIcon,
                             QToolTip,
                             QWidget)
from qttools_path import register_backintime_path
register_backintime_path('common')
import tools  # noqa: E402
import logger  # noqa: E402
import bitbase  # noqa: E402
import version  # noqa: E402
import messagebox  # noqa: E402


_DARK_MODE_THRESHOLD = 128

# |--------------------------------|
# | Widget modification & creation |
# |--------------------------------|


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


def in_dark_mode(widget_or_application: QWidget | QApplication) -> bool:
    """Determine if the desktop/theme is in dark mode."""
    palette = widget_or_application.palette()

    window_color = palette.color(QPalette.ColorRole.Window)

    return window_color.value() < _DARK_MODE_THRESHOLD


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


def wrap_tooltip(tooltip: Union[str, Iterable[str]],
                 wrap_length: int = 72) -> str:
    """Wrap a tooltip string but insert line breaks when appropriated.

    If a list of strings is provided, each string is wrapped individually and
    then joined with a line break.

    Args:
        tooltip: The tooltip as string or iterable of strings.
        wrap_length: Every line is at most this lengths.
    """

    # Always use tuple or list
    if isinstance(tooltip, str):
        tooltip = (tooltip, )

    # Richtext or plain text
    is_richtext = might_be_richtext(tooltip[0])

    newline = {True: '<br>', False: '\n'}[is_richtext]

    result = []
    # Wrap each paragraph in itself
    for paragraph in tooltip:
        result.append('\n'.join(
            textwrap.wrap(paragraph, wrap_length)
        ))

    # glue all together
    result = newline.join(result)

    # Qt handles the string as richttext (interpreting html tags) only,
    # if it begins with a tag.
    if is_richtext and result[0] != '<':
        result = f'<html>{result}</html>'

    return result


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

    widget.setToolTip(wrap_tooltip(tooltip, wrap_length))


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
        icon_scale_factor: float | int = None,
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

    if icon_scale_factor:
        sz = int(sz * icon_scale_factor)

    pixmap = ico.pixmap(sz)

    label = QLabel()
    label.setPixmap(pixmap)

    if fixed_size_widget:
        label.setFixedSize(pixmap.size())

    return label


def create_icon_label_info(
        icon_size: QStyle.PixelMetric = QStyle.PixelMetric.PM_LargeIconSize,
        icon_scale_factor: float | int = None,
        fixed_size_widget: bool = False) -> QLabel:
    """Return a QLabel with an info icon.

    See `create_icon_label` for details.
    """
    return create_icon_label(
        icon_type=QStyle.StandardPixmap.SP_MessageBoxInformation,
        icon_size=icon_size,
        icon_scale_factor=icon_scale_factor,
        fixed_size_widget=fixed_size_widget)


def create_icon_label_warning(
        icon_size: QStyle.PixelMetric = QStyle.PixelMetric.PM_LargeIconSize,
        icon_scale_factor: float | int = None,
        fixed_size_widget: bool = False) -> QLabel:
    """Return a QLabel with a warning icon.

    See `create_icon_label` for details.
    """
    return create_icon_label(
        icon_type=QStyle.StandardPixmap.SP_MessageBoxWarning,
        icon_size=icon_size,
        icon_scale_factor=icon_scale_factor,
        fixed_size_widget=fixed_size_widget)


def create_info_label(
        text: str,
        icon_size: QStyle.PixelMetric = QStyle.PixelMetric.PM_LargeIconSize,
        icon_scale_factor: float | int = None,
        fixed_size_widget: bool = True) -> QLabel:
    """Return a widget with an info icon and text.

    See `create_icon_label` for details.
    """
    ico = create_icon_label_info(
        icon_size, icon_scale_factor, fixed_size_widget)

    return _combine_icon_with_label(ico, text)


def create_warning_label(
        text: str,
        icon_size: QStyle.PixelMetric = QStyle.PixelMetric.PM_LargeIconSize,
        icon_scale_factor: float | int = None,
        fixed_size_widget: bool = True) -> QLabel:
    """Return a widget with a warning icon and text.

    See `create_icon_label` for details.
    """
    ico = create_icon_label_warning(
        icon_size, icon_scale_factor, fixed_size_widget)

    return _combine_icon_with_label(ico, text)


def _combine_icon_with_label(icon: QLabel, text: str) -> QWidget:
    """Horizontally combine the given `icon` with a text label

    Args:
        icon: A `QLabel` containing an icon used as first item in the
            horizontal layout.
        text: The text used in a `Qlabel` as second item in the horizontal
            layout.

    Returns:
        A widget with horizontal layout containing an icon label and a text
            label.
    """
    txt = QLabel(text)
    txt.setWordWrap(True)

    # Show URL in tooltip without anoing http-protocol prefix.
    if '<a href' in text:
        txt.setOpenExternalLinks(True)
        txt.linkHovered.connect(
            lambda url: QToolTip.showText(
                QCursor.pos(), url.replace('https://', ''))
        )

    layout = QHBoxLayout()
    layout.addWidget(icon)
    layout.addWidget(txt)

    label = QWidget()
    label.setLayout(layout)

    return label


def create_qicon_from_svg_source(svg_source: str) -> QIcon:
    """Create a QIcon instance based on SVG/XML source.

    QIcon is not capable of reading from a byte stream.
    This workaround write the SVG/XML-string to a temporary in-RAM file
    before QIcon reads it back.
    """

    svg_fn = None

    with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False
                                     ) as handle:
        handle.write(svg_source)
        svg_fn = handle.name

    atexit.register(Path(svg_fn).unlink)

    return QIcon(svg_fn)


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

    # pylint: disable-next=invalid-name
    def eventFilter(self, receiver: QObject, event: QEvent):  # noqa: N802
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


def _determine_root_mode_user() -> str:
    """Determine the users name who started BIT in root mode

    Usually pkexec is used but some users do use sudo themself.
    """
    # Try pkexec
    uid = os.getenv('PKEXEC_UID', None)
    if uid:
        return pwd.getpwuid(int(uid)).pw_name

    # Try sudo
    sudo_user = os.getenv('SUDO_USER', None)
    if sudo_user:
        return sudo_user

    return None


def open_url(url: str) -> None:
    """Open a URL with the systems default browser using xdg-open."""
    # regular user mode
    if not bitbase.IS_IN_ROOT_MODE:
        QDesktopServices.openUrl(QUrl(url))
        return

    # root mode
    user_name = _determine_root_mode_user()

    try:
        subprocess.run(
            [
                'runuser',
                '-u',
                user_name,
                '--',
                'xdg-open',
                url
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.error(f'Problem while opening "{url}" as user '
                     f'"{user_name}" while in root-mode. '
                     f'Error was: {exc}')

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.critical(f'Unknown problem while opening "{url}" as user '
                        f'"{user_name}" while in root-mode. '
                        f'Error was: {exc}')


def screen_width_in_chars(widget: QWidget, reference_char: str = 'M') -> int:
    """Width of the screen in number of characters ('em').

    The calculation is based on the width of one character, determined via
    font metrics regarding the given widget.
    """
    # Calculate width in pixel for one 'em' (letter 'M')
    metrics = QFontMetricsF(widget.font())
    char_px = metrics.horizontalAdvance(reference_char)

    # Screen width
    handle = widget.windowHandle()
    screen = handle.screen() if handle else QGuiApplication.primaryScreen()
    geom = screen.availableGeometry()

    # Screen width in 'em' (number of characters)
    return int(geom.width() / char_px)


def open_man_page(manpage: str,
                  icon: QIcon = None,
                  section: str = None) -> None:
    """Open the manpage in a text browser window.

    The position and geometry of the dialog depends on fractions of the screen.
    The the man page content's linebreaks in the dialog are adjusted to the
    width of the dialog.

    Args:
        manpage: Name of the manpage.
        icon: Icon to use for the window.
        section: Section of the man page to scroll to.
    """

    content = ''

    if section:
        # Search for one line containing only the section heading but
        # allow blanks before and behind it.
        pattern = r'(?m)^\s*' + section + r'\s*$'
    else:
        pattern = None

    # The dialog
    td = TextDialog(
        content,
        markdown=False,
        scroll_to=pattern,
        title=_('man page: {man_page_name}').format(
            man_page_name=manpage),
        icon=icon
    )

    # Determine man page width in characters...
    chars = screen_width_in_chars(td.browser_widget)
    # ...using text dialogs screen fraction and a 5% security buffer
    chars = int(chars * td.width_fraction * 0.95)

    env = os.environ.copy()
    env['MANWIDTH'] = f'{chars}'

    # Get content from man page
    try:
        proc = subprocess.run(
            ['man', manpage],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            check=False
        )
        content = proc.stdout

        if not content:
            raise FileNotFoundError(
                f'No content for man page "{manpage}".\n'
                f'Error: {proc.stderr.strip()} ({proc.returncode})'
            )

    except FileNotFoundError as exc:
        messagebox.critical(None, str(exc))
        logger.error(str(exc))
        return

    # Show dialog with content
    td.set_content(content)
    td.exec()


def user_manual_uri() -> str:
    """Return the URI to the user manual.

    If available the local URI is used otherwise the online version is.
    """
    uri = bitbase.USER_MANUAL_LOCAL_PATH.as_uri() \
        if bitbase.USER_MANUAL_LOCAL_AVAILABLE \
        else bitbase.URL_USER_MANUAL

    return uri


def open_user_manual() -> None:
    """Open the user manual in browser.

    If available the local manual is used otherwise the online version is
    opened.
    """
    open_url(user_manual_uri())


def _show_qt_debug_info(the_qapp: QApplication):
    if not logger.DEBUG:
        return

    try:
        info = {
            # The platform name indicates eg. wayland vs. X11, see also:
            # https://doc.qt.io/qt-5/qguiapplication.html#platformName-prop
            # For more details see our X11/Wayland/Qt documentation in the
            # directory doc/maintain
            'QT QPA platform plugin': the_qapp.platformName(),
            'QT_QPA_PLATFORMTHEME':
                os.environ.get('QT_QPA_PLATFORMTHEME', '<not set>'),
                # styles and themes determine the look & feel of the GUI
            'QT_STYLE_OVERRIDE':
                os.environ.get('QT_STYLE_OVERRIDE', '<not set>'),
            'QT active style': the_qapp.style().objectName(),
            'QT fallback style': QIcon.fallbackThemeName(),
            'QT supported styles': QStyleFactory.keys(),
            'themeSearchPaths': QIcon.themeSearchPaths(),
            'fallbackSearchPaths': QIcon.fallbackSearchPaths(),
            # The Back In Time system tray icon can only be shown if the
            # desktop environment supports this
            'Is SystemTray available':
                QSystemTrayIcon.isSystemTrayAvailable(),
        }

        # msg = '\n' + json.dumps(info, indent=4)
        msg = json.dumps(info)

    except Exception as exc:  # pylint: disable=broad-exception-caught
        msg = f'Error reading QT QPA platform plugin or style: {exc}'

    logger.debug(msg)


def create_qapplication(app_name=bitbase.APP_NAME) -> QApplication:
    """Create a QAppliction instance or return the existing one.

    Dev note (buhtz, 2025-10): Refactoring is needed. e.g. A QApplication
    derived class (BITApplication) to handle the singleton.
    """

    # pylint: disable-next=global-variable-undefined
    global qapp  # noqa: PLW0603

    try:
        # pylint: disable-next=used-before-assignment
        return qapp  # "singleton pattern": Reuse already instantiated qapp
    except NameError:
        pass

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

        if bitbase.IS_IN_ROOT_MODE:
            qapp.setApplicationName(app_name + " (root)")
            qapp.setDesktopFileName("backintime-qt-root")

        else:
            qapp.setDesktopFileName("backintime-qt")

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning('Could not set App ID (required for Wayland App icon '
                       f'and more). Reason: {exc}')

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

    try:
        yield
    finally:
        widget.blockSignals(False)


@contextmanager
def block_paint_updates(widget: QWidget) -> None:
    """Context manager to temporary block Qt paintng"""
    widget.setUpdatesEnabled(False)

    try:
        yield
    finally:
        widget.setUpdatesEnabled(True)
