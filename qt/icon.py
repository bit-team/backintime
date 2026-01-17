# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Rudimentary icon cachging.

Will be refactored soon.
"""
from PyQt6.QtGui import QIcon
import logger

# logger.debug('Checking if the current theme contains the BIT icon...')

# If the current theme does not even contain the "document-save" icon
# try to use another well-known working theme (if it is installed):
themes_to_try = (
    'gnome',
    'breeze',
    'breeze-dark',
    'hicolor',
    'Adwaita',
    'Adwaita-dark',
    'Yaru',
    'oxygen',
)
ICON_NAME_TO_CHECK = 'document-save'
# A workaround especially for GNOME systems not offering regular icons
# specified by the Free Desktop Icon Naming Specs.
# See this thread for more discussion:
# https://lists.debian.org/debian-gtk-gnome/2026/01/msg00000.html
ICON_NAME_TO_CHECK_SYMBOLIC = f'{ICON_NAME_TO_CHECK}-symbolic'

for theme in themes_to_try:
    # Check if the current theme does provide the BiT "logo" icon
    # (otherwise the theme is not fully/correctly installed)
    # and use this theme then for all icons
    # Note: "hicolor" does currently (2022) use different icon names
    # (not fully compliant to the freedesktop.org spec)
    # and is not recommended as main theme (it is meant as fallback only).
    if not QIcon.fromTheme(ICON_NAME_TO_CHECK,
                           QIcon.fromTheme(ICON_NAME_TO_CHECK_SYMBOLIC)
                           ).isNull():
        logger.debug(
            f'Icon "{ICON_NAME_TO_CHECK}" found in theme: {QIcon.themeName()}'
        )
        break

    # try next theme (activate it)...
    QIcon.setThemeName(theme)
    logger.debug(f'Probing theme: "{theme}" '
                 f'(activated as "{QIcon.themeName()}")')

if QIcon.fromTheme(ICON_NAME_TO_CHECK,
                   QIcon.fromTheme(ICON_NAME_TO_CHECK_SYMBOLIC)
                   ).isNull():
    logger.warning(
        f'Icon theme missing or not supported. Icon "{ICON_NAME_TO_CHECK}" '
        f' and "{ICON_NAME_TO_CHECK_SYMBOLIC}" not found. An icon theme should'
        ' be installed. For example: tango-icon-theme, oxygen-icon-theme'
    )

# Dev note: Please prefer choosing icons from the freedesktop.org spec
#           to improve the chance that the icon is available and
#           each installed theme:
# https://specifications.freedesktop.org/icon-naming-spec/
# icon-naming-spec-latest.html
#
# If there is chance that an icon may not always be available use
# the second argument of QIcon.fromTheme() to provide a fallback
# icon from the freedesktop.org spec.


def load_icon(name: str) -> QIcon | None:
    return QIcon.fromTheme(
        name,
        QIcon.fromTheme(f'{name}-symbolic')
    )


def load_icon_alt(names: list[str]) -> QIcon | None:
    for name in names:
        ico = load_icon(name)

        if not ico.isNull():
            return ico

    return QIcon()


# BackInTime Logo
# TODO If we knew for sure that the global var "qapp" exists then
#      we could use a built-in "standard" Qt icon as fallback if the theme
#      does not provide the icon.
#      => wait for icon.py refactoring than improve this:
#      qapp.style().standardIcon(QStyle.SP_DialogSaveButton)
BIT_LOGO = QIcon.fromTheme('backintime')

# Loading depends on dark/light mode and is managed by systrayicon.py itself.
BIT_LOGO_SYMBOLIC_NAME = 'backintime-symbolic'

# Main toolbar
TAKE_SNAPSHOT = load_icon('document-save')
PAUSE = load_icon('media-playback-pause')
RESUME = load_icon('media-playback-start')
STOP = load_icon('media-playback-stop')
REFRESH = load_icon('view-refresh')
REFRESH_SNAPSHOT = REFRESH
SNAPSHOT_NAME = load_icon_alt([
    'stock_edit',
    'gtk-edit',
    'edit-rename',
    'accessories-text-editor'
])

EDIT_USER_CALLBACK = SNAPSHOT_NAME
REMOVE_SNAPSHOT = load_icon('edit-delete')
VIEW_SNAPSHOT_LOG  = load_icon_alt(['text-plain', 'text-x-generic'])
VIEW_LAST_LOG = load_icon('document-open-recent')
SETTINGS = load_icon_alt([
    'gtk-preferences',
    'configure',
    # Free Desktop Icon Naming Specification
    'preferences-system'
])
SHUTDOWN = load_icon('system-shutdown')
EXIT = load_icon_alt(['gtk-close', 'application-exit'])

# Help menu
HELP = load_icon_alt(['help-browser', 'help-contents'])
WEBSITE = load_icon('go-home')
CHANGELOG = load_icon('format-justify-fill')
FAQ = load_icon_alt(['help-faq', 'help-hint'])
QUESTION = load_icon_alt(['stock_dialog-question', 'help-feedback'])
BUG = load_icon_alt(['stock_dialog-error', 'tools-report-bug'])
ABOUT = load_icon('help-about')

# Files toolbar
UP = load_icon('go-up')
SHOW_HIDDEN = load_icon_alt([
    'view-hidden',  # currently only in Breeze (see #1159)
    'show-hidden',   # icon installed with BIT #507
    'list-add'
])
RESTORE = load_icon('edit-undo')
RESTORE_TO = load_icon('document-revert')
SNAPSHOTS = load_icon_alt([
    'file-manager',
    'view-list-details',
    'system-file-manager'
])

# Compare backups dialog (aka Snapshot dialog)
DIFF_OPTIONS = SETTINGS
DELETE_FILE = REMOVE_SNAPSHOT
SELECT_ALL = load_icon('edit-select-all')

# Restore dialog
RESTORE_DIALOG = VIEW_SNAPSHOT_LOG

# Settings dialog
SETTINGS_DIALOG = SETTINGS
PROFILE_EDIT = SNAPSHOT_NAME
ADD = load_icon('list-add')
REMOVE = load_icon('list-remove')
FOLDER = load_icon('folder')
FILE = load_icon_alt(['text-plain', 'text-x-generic'])
EXCLUDE = load_icon('edit-delete')
DEFAULT_EXCLUDE = load_icon('emblem-important')
INVALID_EXCLUDE = load_icon_alt(['emblem-ohno', 'face-surprise'])
ENCRYPT = load_icon_alt(['lock', 'security-high'])
LANGUAGE = load_icon('preferences-desktop-locale')
