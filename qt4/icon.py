#    Copyright (c) 2012-2013 Germar Reitze
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

from PyQt4.QtGui import QIcon

#BackInTime Logo
BIT_LOGO            = QIcon.fromTheme('document-save')
BIT_LOGO_INFO       = QIcon.fromTheme('document-save-as')

#Main toolbar
TAKE_SNAPSHOT       = BIT_LOGO
REFRESH_SNAPSHOT    = QIcon.fromTheme('view-refresh')
SNAPSHOT_NAME       = QIcon.fromTheme('stock_edit',
                      QIcon.fromTheme('gtk-edit',
                      QIcon.fromTheme('edit-rename',
                      QIcon.fromTheme('accessories-text-editor') ) ) )
REMOVE_SNAPSHOT     = QIcon.fromTheme('edit-delete')
VIEW_SNAPSHOT_LOG   = QIcon.fromTheme('text-plain',
                      QIcon.fromTheme('text-x-generic') )
VIEW_LAST_LOG       = QIcon.fromTheme('document-new')
SETTINGS            = QIcon.fromTheme('gtk-preferences',
                      QIcon.fromTheme('configure') )
SHUTDOWN            = QIcon.fromTheme('system-shutdown')
EXIT                = QIcon.fromTheme('gtk-close',
                      QIcon.fromTheme('application-exit') )

#Help menu
HELP                = QIcon.fromTheme('help-contents')
WEBSITE             = QIcon.fromTheme('go-home')
CHANGELOG           = QIcon.fromTheme('format-justify-fill')
FAQ                 = QIcon.fromTheme('help-faq',
                      QIcon.fromTheme('help-hint') )
QUESTION            = QIcon.fromTheme('stock_dialog-question',
                      QIcon.fromTheme('help-feedback') )
BUG                 = QIcon.fromTheme('stock_dialog-error',
                      QIcon.fromTheme('tools-report-bug') )
ABOUT               = QIcon.fromTheme('help-about')

#Files toolbar
UP                  = QIcon.fromTheme('go-up')
SHOW_HIDDEN         = QIcon.fromTheme('list-add')
RESTORE             = QIcon.fromTheme('edit-undo')
RESTORE_TO          = QIcon.fromTheme('document-revert')
SNAPSHOTS           = QIcon.fromTheme('file-manager',
                      QIcon.fromTheme('view-list-details') )

#Snapshot dialog
DIFF_OPTIONS        = SETTINGS
DELETE_FILE         = REMOVE_SNAPSHOT
SELECT_ALL          = QIcon.fromTheme('edit-select-all')

#Restore dialog
RESTORE_DIALOG      = VIEW_SNAPSHOT_LOG

#Settings dialog
SETTINGS_DIALOG     = SETTINGS
PROFILE_EDIT        = SNAPSHOT_NAME
ADD                 = SHOW_HIDDEN
REMOVE              = QIcon.fromTheme('list-remove')
FOLDER              = QIcon.fromTheme('folder')
FILE                = VIEW_SNAPSHOT_LOG
EXCLUDE             = REMOVE_SNAPSHOT
