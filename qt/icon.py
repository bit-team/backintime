# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
from PyQt6.QtGui import QIcon
import logger

logger.debug("Checking if the current theme contains the BiT icon...")

# If the current theme does not even contain the "document-save" icon
# try to use another well-known working theme (if it is installed):
for theme in ('ubuntu-mono-dark', 'gnome', 'breeze', 'breeze dark', 'hicolor', 'adwaita', 'adwaita-dark', 'yaru', 'oxygen'):
    # Check if the current theme does provide the BiT "logo" icon
    # (otherwise the theme is not fully/correctly installed)
    # and use this theme then for all icons
    # Note: "hicolor" does currently (2022) use different icon names
    #       (not fully compliant to the freedesktop.org spec)
    #       and is not recommended as main theme (it is meant as fallback only).
    if not QIcon.fromTheme('document-save').isNull():
        logger.debug(f"Found an installed theme: {QIcon.themeName()}")
        break
    # try next theme (activate it)...
    QIcon.setThemeName(theme)
    logger.debug(f"Probing theme: {theme} (activated as {QIcon.themeName()})")

if QIcon.fromTheme('document-save').isNull():
    logger.error("No supported theme installed (missing icons). "
                 "Please consult the project web site for instructions "
                 "how to fix this.")

# Dev note: Please prefer choosing icons from the freedesktop.org spec
#           to improve the chance that the icon is available and
#           each installed theme:
# https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html
#
# If there is chance that an icon may not always be available use
# the second argument of QIcon.fromTheme() to provide a fallback
# icon from the freedesktop.org spec.

# BackInTime Logo
# TODO If we knew for sure that the global var "qapp" exists then
#      we could use a built-in "standard" Qt icon as fallback if the theme does
#      not provide the icon.
#      => wait for icon.py refactoring than improve this:
#      qapp.style().standardIcon(QStyle.SP_DialogSaveButton)
BIT_LOGO            = QIcon.fromTheme('document-save')
BIT_LOGO_INFO       = QIcon.fromTheme('document-save-as')

#Main toolbar
TAKE_SNAPSHOT       = BIT_LOGO
PAUSE               = QIcon.fromTheme('media-playback-pause')
RESUME              = QIcon.fromTheme('media-playback-start')
STOP                = QIcon.fromTheme('media-playback-stop')
REFRESH_SNAPSHOT    = QIcon.fromTheme('view-refresh')
SNAPSHOT_NAME       = QIcon.fromTheme('stock_edit',
                      QIcon.fromTheme('gtk-edit',
                      QIcon.fromTheme('edit-rename',
                      QIcon.fromTheme('accessories-text-editor'))))
REMOVE_SNAPSHOT     = QIcon.fromTheme('edit-delete')
VIEW_SNAPSHOT_LOG   = QIcon.fromTheme('text-plain',
                      QIcon.fromTheme('text-x-generic'))
VIEW_LAST_LOG       = QIcon.fromTheme('document-open-recent')
SETTINGS            = QIcon.fromTheme('gtk-preferences',
                      QIcon.fromTheme('configure',
                      # Free Desktop Icon Naming Specification
                      QIcon.fromTheme('preferences-system')))
SHUTDOWN            = QIcon.fromTheme('system-shutdown')
EXIT                = QIcon.fromTheme('gtk-close',
                      QIcon.fromTheme('application-exit'))

#Help menu
HELP                = QIcon.fromTheme('help-contents')
WEBSITE             = QIcon.fromTheme('go-home')
CHANGELOG           = QIcon.fromTheme('format-justify-fill')
FAQ                 = QIcon.fromTheme('help-faq',
                      QIcon.fromTheme('help-hint'))
QUESTION            = QIcon.fromTheme('stock_dialog-question',
                      QIcon.fromTheme('help-feedback'))
BUG                 = QIcon.fromTheme('stock_dialog-error',
                      QIcon.fromTheme('tools-report-bug'))
ABOUT               = QIcon.fromTheme('help-about')

#Files toolbar
UP                  = QIcon.fromTheme('go-up')
SHOW_HIDDEN         = QIcon.fromTheme('view-hidden',  # currently only in Breeze (see #1159)
                      QIcon.fromTheme('show-hidden',  # icon installed with # BiT! #507
                      QIcon.fromTheme('list-add')))
RESTORE             = QIcon.fromTheme('edit-undo')
RESTORE_TO          = QIcon.fromTheme('document-revert')
SNAPSHOTS           = QIcon.fromTheme('file-manager',
                      QIcon.fromTheme('view-list-details',
                      QIcon.fromTheme('system-file-manager')))

#Snapshot dialog
DIFF_OPTIONS        = SETTINGS
DELETE_FILE         = REMOVE_SNAPSHOT
SELECT_ALL          = QIcon.fromTheme('edit-select-all')

#Restore dialog
RESTORE_DIALOG      = VIEW_SNAPSHOT_LOG

#Settings dialog
SETTINGS_DIALOG     = SETTINGS
PROFILE_EDIT        = SNAPSHOT_NAME
ADD                 = QIcon.fromTheme('list-add')
REMOVE              = QIcon.fromTheme('list-remove')
FOLDER              = QIcon.fromTheme('folder')
FILE                = QIcon.fromTheme('text-plain',
                      QIcon.fromTheme('text-x-generic'))
EXCLUDE             = QIcon.fromTheme('edit-delete')
# "emblem-default" is a green mark and doesn't make sense in this case.
DEFAULT_EXCLUDE     = QIcon.fromTheme('emblem-important')
INVALID_EXCLUDE     = QIcon.fromTheme('emblem-ohno',
                      QIcon.fromTheme('face-surprise'))

ENCRYPT = QIcon.fromTheme('lock', QIcon.fromTheme('security-high'))
LANGUAGE = QIcon.fromTheme('preferences-desktop-locale')
