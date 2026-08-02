# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2024 Christian Buhtz <c.buhtz@posteo.jp>
# SPDX-FileCopyrightText: © 2025 Samuel Moore
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Entry of GUI application."""
import os
import sys
if not os.getenv('DISPLAY', ''):
    os.putenv('DISPLAY', ':0.0')
import pathlib
import json
import threading
import queue
import shutil
import textwrap
import signal
from collections.abc import Generator
from contextlib import contextmanager
from tempfile import TemporaryDirectory
# We need to import common/tools.py
import qttools_path
qttools_path.register_backintime_path('common')
# Workaround until the codebase is rectified/equalized.
import tools
tools.initiate_translation(None)
import qttools
import backintime
import bitbase
import config
import cli
import logger
import snapshots
import guiapplicationinstance
from mount import MountManager, MountError
import progress
import encfsmsgbox
from inhibitsuspend import InhibitSuspend
from exceptions import MountException
from statedata import StateData
from filedialog import FileDialog
from textdlg import TextDialog
from PyQt6.QtGui import (QAction,
                         QActionGroup,
                         QDesktopServices,
                         QIcon,
                         QShortcut)
from PyQt6.QtWidgets import (QApplication,
                             QDialog,
                             QFrame,
                             QGroupBox,
                             QInputDialog,
                             QLabel,
                             QLineEdit,
                             QMainWindow,
                             QMenu,
                             QMessageBox,
                             QStackedLayout,
                             QSplitter,
                             QToolBar,
                             QToolButton,
                             QVBoxLayout,
                             QWidget)
from PyQt6.QtCore import (QPoint,
                          pyqtSignal,
                          Qt,
                          QTimer,
                          QThread,
                          QUrl)
import snapshotsdialog
import logviewdialog
import languagedialog
import messagebox
import version
import timeline
from confirmrestoredialog import ConfirmRestoreDialog
from editusercallback import EditUserCallback
from shutdownagent import ShutdownAgent
from manageprofiles import SettingsDialog
from restoredialog import RestoreDialog
from restoreconfigdialog import RestoreConfigDialog
from usermessagedialog import UserMessageDialog
from aboutdlg import AboutDlg
from bitwidgets import ProfileCombo
from shutdowndlg import get_shutdown_confirmation
from statusbar import StatusBar
from placeswidget import PlacesWidget
from qtsystrayicon import QtSysTrayIcon
from fileview import FilesView
from profile_operations import ProfileOperations
from event import Event


class MainWindow(QMainWindow):
    """The main window of Back In Time"""

    def __init__(self, config, appInstance, qapp):
        QMainWindow.__init__(self)

        self.config = config
        self.appInstance = appInstance
        self.qapp = qapp
        self.snapshots = snapshots.Snapshots(config)

        self._profile_operations = None
        self._reset_profile_operations()

        self.lastTakeSnapshotMessage = None
        self.tmpDirs = []
        self.firstUpdateAll = True
        self.disableProfileChanged = False

        # related to files view ???
        self.selected_file = ''

        # "Magic" object handling shutdown procedure in different desktop
        # environments.
        self.shutdown = ShutdownAgent()

        # Import on module level not possible because of Qt restrictions.
        import icon
        globals()['icon'] = icon

        # window icon
        self.qapp.setWindowIcon(icon.BIT_LOGO)

        state_data = StateData()

        # shortcuts without buttons
        self._create_shortcuts_without_actions()

        self._create_actions()
        self._create_menubar()
        self._create_main_toolbar()

        # timeline (left widget)
        self.timeline = timeline.TimeLine(self)

        # right widget
        self.filesWidget = QGroupBox(self)
        filesLayout = QVBoxLayout(self.filesWidget)
        right = filesLayout.getContentsMargins()[2]
        filesLayout.setContentsMargins(0, 0, right, 0)

        # main splitter
        self.mainSplitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.mainSplitter.addWidget(self.timeline)
        self.mainSplitter.addWidget(self.filesWidget)

        # FilesView toolbar
        self.toolbar_filesview = self._files_view_toolbar()
        filesLayout.addWidget(self.toolbar_filesview)

        # Catch mouse button's 4 (back) and 5 (forward)
        self._mouse_button_event_filter = qttools.MouseButtonEventFilter(
            back_handler=self._slot_files_view_dir_history_previous,
            forward_handler=self._slot_files_view_dir_history_next,
        )
        self.qapp.installEventFilter(self._mouse_button_event_filter)

        # second splitter:
        # part of files-layout
        self.secondSplitter = QSplitter(self)
        self.secondSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.secondSplitter.setContentsMargins(0, 0, 0, 0)
        filesLayout.addWidget(self.secondSplitter)

        self.places = PlacesWidget(self, self.config)
        self.secondSplitter.addWidget(self.places)

        # files view stacked layout
        widget = QWidget(self)
        self.stackFilesView = QStackedLayout(widget)
        self.secondSplitter.addWidget(widget)

        # label: directory don't exist
        self._label_not_a_now_dir, self._label_not_a_backup_dir \
            = self._label_dir_dont_exist()
        self.stackFilesView.addWidget(self._label_not_a_now_dir)
        self.stackFilesView.addWidget(self._label_not_a_backup_dir)

        # files view
        sort_column, sort_order = state_data.files_view_sorting
        self.filesView = FilesView(
            self,
            self.act_restore,
            self.act_restore_to,
            self.act_snapshots_dialog,
            self.act_show_hidden,
            sort_column,
            sort_order
        )
        self.filesView.event_path_clicked.register(
            self._on_files_view_path_clicked
        )
        self.stackFilesView.addWidget(self.filesView)
        self.stackFilesView.setCurrentWidget(self.filesView)

        self.setCentralWidget(self.mainSplitter)

        self.status_bar = StatusBar(self)
        self.statusBar().addWidget(self.status_bar, 100)
        self.status_bar.set_status_message(_('Done'))

        self.snapshotsList = []

        profile_state = state_data.profile(self.config.currentProfile())

        # Dev note (buhtz, 2026-08): The purpose's of this variable were not
        # clear not me in the beginning. There was not docu about it.
        #
        # Current logical path shown in the files view.
        #
        # This is a path inside the backup tree, not an absolute filesystem
        # path. The selected backup resolves this path to the real filesystem
        # location.
        #
        # self.path represents GUI navigation state and is independent from
        # the selected backup.
        self.path = str(profile_state.last_path)

        self.widget_current_path.setText(self.path)
        self.path_history = tools.PathHistory(self.path)

        # Events
        self.event_profile_changed = Event()
        self.event_profile_changed.register([
            self.filesView.set_profile_operations,
            self.places.set_profile_operations,
        ])

        self._restore_visual_state()

        self._handle_release_candidate()

        was_imported = self._import_config_from_backup()

        # populate lists
        if not was_imported:
            self.updateProfiles()

        self.comboProfiles.currentIndexChanged \
                          .connect(self.comboProfileChanged)

        self.filesView.setFocus()

        self.timeline.event_now_selected.register([
            self._on_now_selected,
            self.places.on_now_selected,
        ])
        self.timeline.event_backup_selected.register([
            self._on_backup_selected,
            self.places.on_backup_changed
        ])

        self.forceWaitLockCounter = 0
        self._setup_timers()

        threading.Thread(
            target=self.config.setup_automation, daemon=True).start()

        self._handle_user_messages()

    def selected_backup_id(self) -> snapshots.SID | None:
        """Return the identity of the backup that is currently selected in the
        timeline widget.
        """
        backup_descriptor = self.timeline.selected_backup_descriptor()
        if not backup_descriptor:
            return None

        # mounted_path=self._profile_operations.get_mount_manager().path

        return snapshots.SID(
            date=backup_descriptor,
            cfg=self.config,
            mounted_path=self._profile_operations.get_mount_manager().path
        )

    def _setup_timers(self):
        raise_application = QTimer(self)
        raise_application.setInterval(1000)
        raise_application.setSingleShot(False)
        raise_application.timeout.connect(self.raiseApplication)
        raise_application.start()

        update_backup_messages = QTimer(self)
        update_backup_messages.setInterval(1000)
        update_backup_messages.setSingleShot(False)
        update_backup_messages.timeout.connect(self._update_backup_status)
        update_backup_messages.start()

    def _restore_visual_state(self):
        # This prevents that the restore-config-question will be overlaid
        # by the main window.
        if not self.config.isConfigured():
            return

        state_data = StateData()

        try:
            if state_data.mainwindow_maximized:
                self.showMaximized()
            else:
                self.move(*state_data.mainwindow_coords)
                self.resize(*state_data.mainwindow_dims)

        except KeyError:
            pass

        self.mainSplitter.setSizes(
            state_data.mainwindow_main_splitter_widths)
        self.secondSplitter.setSizes(
            state_data.mainwindow_second_splitter_widths)

        # FilesView: Column width
        try:
            files_view_col_widths = state_data.files_view_col_widths

        except KeyError:
            pass

        else:
            for idx, width in enumerate(files_view_col_widths):
                self.filesView.header().resizeSection(idx, width)

    def _handle_release_candidate(self):
        if not version.IS_RELEASE_CANDIDATE:
            return

        state_data = StateData()
        last_vers = state_data.msg_release_candidate

        if last_vers != version.__version__:
            state_data.msg_release_candidate = version.__version__
            self._open_release_candidate_dialog()

    def _import_config_from_backup(self):
        # config_fp = Path(self.config._LOCAL_CONFIG_PATH)
        config_fp = bitbase.context['--config']

        if config_fp.exists():
            return False

        message = _(
            '{app_name} appears to be running for the first time because no '
            'configuration is found.'
        ).format(app_name=self.config.APP_NAME)
        message = f'{message}\n\n'
        message = message + _(
            'Create a new configuration or import an existing '
            'configuration from a backup?'
        )

        import_prompt = QMessageBox(None)
        import_prompt.setWindowTitle(_('Question'))
        import_prompt.setText(message)
        import_prompt.setIcon(QMessageBox.Icon.Question)
        btn_create = import_prompt.addButton(
            _('Create'), QMessageBox.ButtonRole.ActionRole)
        btn_import = import_prompt.addButton(
            _('Import'), QMessageBox.ButtonRole.ActionRole)

        import_prompt.setDefaultButton(btn_create)
        import_prompt.exec()
        answer = import_prompt.clickedButton()

        if answer == btn_import:
            rc = RestoreConfigDialog(self.config).exec()
            if rc == QDialog.DialogCode.Rejected:
                answer = btn_create

        SettingsDialog(self).exec()

        return True

    def _message_about_encfs_config_backup(self):
        # e.g. '~/.config/backintime/config.encfs.backup'
        config_fp_backup = bitbase.context['--config'].with_suffix(
            bitbase.ENCFS_BACKUP_CONFIG_SUFFIX
        )

        if not config_fp_backup.exists():
            return

        state_data = StateData()
        if state_data.msg_encfs_global < bitbase.ENCFS_MSG_STAGE:
            state_data.msg_encfs_global = bitbase.ENCFS_MSG_STAGE
            state_data.save()
            dlg = encfsmsgbox.EncfsFinalRemoval(config_fp_backup)
            dlg.exec()

    def _handle_user_messages(self):
        self._message_about_encfs_config_backup()

        # # Ignore if debug or release/testing candidate
        # if version.IS_RELEASE_CANDIDATE or logger.DEBUG:
        #     return

        # See issue #2493. Global config is not supported anymore.
        if bitbase.GLOBAL_CONFIG_PATH.exists():
            messagebox.critical(
                self,
                f'The global config file ({bitbase.GLOBAL_CONFIG_PATH}) is '
                'no longer supported.\n\nRemove it.\n\nBack In Time only '
                'supports per-user configuration files.',
                'Global config file support dropped'
            )

        state_data = StateData()

        # SSH Cipher removal (#2176)
        cipher = cli.detect_cipher_settings()
        if cipher:
            self._open_ssh_cipher_remove_dialog(
                [entry[0] for entry in cipher]
            )
        # remove the cipher keys from config
        for _name, _val, key in cipher:
            del self.config.dict[key]

        # SSH Remote host checks deprecation (#2482)
        check_settings = cli.detect_remote_host_check_settings()
        if check_settings:
            self._open_remote_host_check_deprecation_dialog(
                [entry[0] for entry in check_settings]
            )

        # Issue: https://github.com/bit-team/backintime/issues/2080
        lang_planed_for_removal = [
            'fo',  # Faroes 18
            'ka',  # Georgian 23
            'hr',  # Croatian 24
            'vi',  # Vietnamese 35
            'is',  # Icelandic 44
            # 'ar',  # Arabic. Last activity 2025-10 45
        ]

        # Language removal message
        if self.config.language_used in lang_planed_for_removal:
            if state_data.msg_language_remove is False:
                self._open_language_remove_statement()
                state_data.msg_language_remove = True

        # Countdown of manual GUI starts finished?
        if state_data.manual_starts_countdown() == 0:

            # Do nothing if English is the current used language
            if self.config.language_used != 'en':

                # Show the message only if the current used language is
                # translated equal or less then {cutoff}%
                self._open_approach_translator_dialog(cutoff=90)

        # BIT counts down how often the GUI was started. Until the end of that
        # countdown a dialog with a text about contributing to translating
        # BIT is presented to the users.
        state_data.decrement_manual_starts_countdown()

    @property
    def showHiddenFiles(self):
        state_data = StateData()
        return state_data.mainwindow_show_hidden

    @showHiddenFiles.setter
    def showHiddenFiles(self, value):
        state_data = StateData()
        state_data.mainwindow_show_hidden = value

    def _create_actions(self):
        """Create all action objects used by this main window.

        All actions are stored as instance attributes to ``self`` and their
        names begin with ``act_``. The actions can be added to GUI elements
        (menu entries, buttons) in later steps.

        Note:
            All actions used in the main window and its child widgets should
            be created in this function.

        Note:
            Shortcuts need to be strings in a list even if it is only one
            entry. It is done this way to spare one ``if...else`` statement
            deciding between `QAction.setShortcuts()` and
            `QAction.setShortcut()` (singular; without ``s`` at the end).
        """

        action_dict = {
            # because of "icon"
            # pylint: disable=undefined-variable

            # 'Name of action attribute in "self"': (
            #     ICON, Label text,
            #     trigger_handler_function,
            #     keyboard shortcuts (type list[str])
            #     tooltip
            # ),
            'act_take_snapshot': (
                icon.TAKE_SNAPSHOT, _('Create a backup'),
                self._slot_backup_create, ['Ctrl+S'],
                _('Use modification time & size for file change detection.')),

            'act_take_snapshot_checksum': (
                icon.TAKE_SNAPSHOT, _('Create a backup (checksum mode)'),
                self._slot_backup_create_with_checksum, ['Ctrl+Shift+S'],
                _('Use checksums for file change detection.')),
            'act_pause_take_snapshot': (
                icon.PAUSE, _('Pause backup process'),
                lambda: self._send_signal_to_backup_process(signal.SIGSTOP),
                None,
                None),
            'act_resume_take_snapshot': (
                icon.RESUME, _('Resume backup process'),
                lambda: self._send_signal_to_backup_process(signal.SIGCONT),
                None,
                None),
            'act_stop_take_snapshot': (
                icon.STOP, _('Stop backup process'),
                self._slot_backup_stop, None,
                None),
            'act_update_snapshots': (
                icon.REFRESH_SNAPSHOT, _('Refresh backup list'),
                self._slot_timeline_refresh, ['F5', 'Ctrl+R'],
                None),
            'act_name_snapshot': (
                icon.SNAPSHOT_NAME, _('Name backup'),
                self._slot_backup_name, ['F2'],
                None),
            'act_remove_snapshot': (
                icon.REMOVE_SNAPSHOT, _('Remove backup'),
                self._slot_backup_remove, ['Delete'],
                None),
            'act_snapshot_logview': (
                icon.VIEW_SNAPSHOT_LOG, _('Open backup log'),
                self._slot_backup_open_log, None,
                _('View log of the selected backup.')),
            'act_last_logview': (
                icon.VIEW_LAST_LOG, _('Open last backup log'),
                self._slot_backup_open_last_log, None,
                _('View log of the latest backup.')),
            'act_settings': (
                icon.SETTINGS, _('Manage profiles…'),
                self._slot_manage_profiles, ['Ctrl+Shift+P'],
                None),
            'act_edit_user_callback': (
                icon.EDIT_USER_CALLBACK, _('Edit user-callback'),
                self._slot_edit_user_callback, None,
                None),
            'act_shutdown': (
                icon.SHUTDOWN, _('Shutdown'),
                None, None,
                _('Shut down system after backup has finished.')),
            'act_setup_language': (
                icon.LANGUAGE, _('Setup language…'),
                self._slot_setup_language, None,
                None),
            'act_quit': (
                icon.EXIT, _('Exit'),
                self.close, ['Ctrl+Q'],
                None),
            'act_help_user_manual': (
                icon.HELP, _('User manual'),
                self._slot_help_user_manual, ['F1'],
                _('Open user manual in browser (local if '
                  'available, otherwise online)'),
            ),
            'act_help_man_backintime': (
                icon.HELP, _('man page: Back In Time'),
                self._slot_help_man_backintime, None,
                _('Displays man page about Back In Time (backintime)')
            ),
            'act_help_man_config': (
                icon.HELP, _('man page: Profiles config file'),
                self._slot_help_man_config,
                None,
                _('Displays man page about profiles config file '
                  '(backintime-config)')
            ),
            'act_help_website': (
                icon.WEBSITE, _('Project website'),
                self._slot_help_website,
                None,
                _('Open Back In Time website in browser')),
            'act_help_changelog': (
                icon.CHANGELOG, _('Changelog'),
                self._slot_help_changelog,
                None,
                _('Open changelog (locally if available, '
                  'otherwise from the web)')),
            'act_help_faq': (
                icon.FAQ, _('FAQ'),
                self._slot_help_faq, None,
                _('Open Frequently Asked Questions (FAQ) in browser')),
            'act_help_bugreport': (
                icon.BUG, _('Report a bug'),
                self._slot_help_report_bug, None, None),
            'act_help_contact': (
                icon.QUESTION, _('Contact'),
                self._slot_help_contact, None,
                _('Shows additional contact options in the browser'),
            ),
            'act_help_translation': (
                icon.LANGUAGE, _('Translation'),
                self._slot_help_translation, None,
                _('Shows the message about participation '
                  'in translation again.')),
            'act_help_encryption': (
                icon.ENCRYPT,
                'About encryption transition',
                self._slot_help_encryption, None,
                'Shows support article about EncFS removal and '
                'gocryptfs replacement.'
            ),
            'act_help_about': (
                icon.ABOUT, _('About'),
                self._slot_help_about, None, None),
            'act_restore': (
                icon.RESTORE, _('Restore'),
                self._slot_restore_this, None,
                _('Restore the selected files or directories to the '
                  'original location.')),
            'act_restore_to': (
                icon.RESTORE_TO, _('Restore to …'),
                self._slot_restore_this_to, None,
                _('Restore the selected files or directories to a '
                  'new location.')),
            'act_restore_parent': (
                icon.RESTORE,
                None,  # text label is set elsewhere
                self._slot_restore_parent, None,
                _('Restore the currently shown directory and all its contents '
                  'to the original location.')),
            'act_restore_parent_to': (
                icon.RESTORE_TO,
                None,  # text label is set elsewhere
                self._slot_restore_parent_to, None,
                _('Restore the currently shown directory and all its contents '
                  'to a new location.')),
            'act_folder_up': (
                icon.UP, _('Up'),
                self._slot_files_view_dir_up, ['Alt+Up', 'Backspace'], None),
            'act_show_hidden': (
                icon.SHOW_HIDDEN, _('Show hidden files'),
                None, ['Ctrl+H'], None),
            'act_snapshots_dialog': (
                icon.SNAPSHOTS, _('Compare backups…'),
                self._slot_snapshots_dialog, None, None),
        }

        for attr in action_dict:
            ico, txt, slot, keys, tip = action_dict[attr]

            # Create action (with icon)
            action = QAction(ico, txt, self) if ico else \
                QAction(txt, self)

            # Connect handler function
            if slot:
                action.triggered.connect(slot)

            # Add keyboardshortcuts
            if keys:
                action.setShortcuts(keys)

            # Tooltip
            if tip:
                action.setToolTip(tip)

            # populate the action to "self"
            setattr(self, attr, action)

        # Release Candidate ?
        self.act_help_release_candidate = None
        if version.IS_RELEASE_CANDIDATE or logger.DEBUG:
            # pylint: disable=undefined-variable
            action = QAction(icon.QUESTION, _('Release Candidate'), self)
            action.triggered.connect(self._slot_help_release_candidate)
            action.setToolTip(
                _('Shows the message about this Release Candidate again.'))
            self.act_help_release_candidate = action

        # Fine tuning
        self.act_shutdown.toggled.connect(self._slot_shutdown_toggled)
        self.act_shutdown.setCheckable(True)
        self.act_shutdown.setEnabled(self.shutdown.can_shutdown())
        self.act_pause_take_snapshot.setVisible(False)
        self.act_resume_take_snapshot.setVisible(False)
        self.act_stop_take_snapshot.setVisible(False)
        self.act_show_hidden.setCheckable(True)
        self.act_show_hidden.setChecked(self.showHiddenFiles)
        self.act_show_hidden.toggled.connect(
            self._slot_files_view_hidden_files_toggled)

    def _create_shortcuts_without_actions(self):
        """Create shortcuts that are not related to a visual element in the
        GUI and don't have an QAction instance because of that.
        """

        shortcut_list = (
            ('Alt+Left', self._slot_files_view_dir_history_previous),
            ('Alt+Right', self._slot_files_view_dir_history_next),
            ('Alt+Down', self._slot_files_view_open_current_item),
        )

        for keys, slot in shortcut_list:
            shortcut = QShortcut(keys, self)
            shortcut.activated.connect(slot)

    def _create_menubar(self):
        """Create the menubar and connect it to actions."""

        menu_dict = {
            # The application name itself shouldn't be translated but the
            # shortcut indicator (marked with &) should be translated and
            # decided by the translator.
            _('Back In &Time'): (
                self.act_setup_language,
                self.act_shutdown,
                self.act_quit,
            ),
            _('&Backup'): (
                self.act_take_snapshot,
                self.act_take_snapshot_checksum,
                self.act_settings,
                self.act_snapshots_dialog,
                self.act_name_snapshot,
                self.act_remove_snapshot,
                self.act_snapshot_logview,
                self.act_last_logview,
                self.act_update_snapshots,
                self.act_edit_user_callback,
            ),
            _('&Restore'): (
                self.act_restore,
                self.act_restore_to,
                self.act_restore_parent,
                self.act_restore_parent_to,
            ),
            _('&Help'): (
                self.act_help_user_manual,
                self.act_help_man_backintime,
                self.act_help_man_config,
                self.act_help_website,
                self.act_help_changelog,
                self.act_help_faq,
                self.act_help_bugreport,
                self.act_help_contact,
                self.act_help_translation,
                self.act_help_encryption,
                self.act_help_about,
            )
        }

        for key in menu_dict:
            menu = self.menuBar().addMenu(key)
            menu.addActions(menu_dict[key])
            menu.setToolTipsVisible(True)

        # The action of the restore menu. It is used by the menuBar and by the
        # files toolbar.
        # It is populated to "self" because it's state to be altered.
        # See "self._enable_restore_ui_elements()" for details.
        self.act_restore_menu = self.menuBar().actions()[2]

        # fine tuning.
        # Attention: Take care of the actions() index here when modifying the
        # main menu!
        backup = self.menuBar().actions()[1].menu()
        backup.insertSeparator(self.act_settings)
        backup.insertSeparator(self.act_snapshot_logview)
        backup.insertSeparator(self.act_update_snapshots)
        help = self.menuBar().actions()[-1].menu()
        help.insertSeparator(self.act_help_website)
        help.insertSeparator(self.act_help_about)
        if self.act_help_release_candidate:
            help.addSeparator()
            help.addAction(self.act_help_release_candidate)
        restore = self.act_restore_menu.menu()
        restore.insertSeparator(self.act_restore_parent)
        restore.setToolTipsVisible(True)

        # Menu: "Back In Time" -> "Systray Icon"
        submenu_systray = self._create_submenu_systray_icon()
        self.act_group_systray = submenu_systray.actions()[0].actionGroup()
        self.menuBar().actions()[0].menu().insertMenu(
            self.act_shutdown, submenu_systray)

    def _create_submenu_systray_icon(self) -> QMenu:
        menu = QMenu(_('Systray Icon'), self)
        import icon
        menu.setIcon(icon.SETTINGS)

        ico_group_data = [
            # (_('Automatic'), QIcon.fromTheme('system-search'), 'auto'),
            (_('Automatic'),
             QIcon.fromTheme('system-run',
                             QIcon.fromTheme('system-search')),
             'auto'),
            (_('Light icon'), QtSysTrayIcon.get_light_icon(), 'light'),
            (_('Dark icon'), QtSysTrayIcon.get_dark_icon(), 'dark'),
        ]
        action_group = QActionGroup(self)
        action_group.setExclusive(True)
        action_group.triggered.connect(self._slot_systray_icon)

        val = self.config.systray()

        for txt_label, ico, data in ico_group_data:
            act = QAction(ico, txt_label, checkable=True)
            act.setData(data)

            if val == data:
                act.setChecked(True)

            action_group.addAction(act)
            menu.addAction(act)

        return menu

    def _button_styles(self):
        return (
            (
                _('Icons only'),
                Qt.ToolButtonStyle.ToolButtonIconOnly),
            (
                _('Text only'),
                Qt.ToolButtonStyle.ToolButtonTextOnly),
            (
                _('Text below icons'),
                Qt.ToolButtonStyle.ToolButtonTextUnderIcon),
            (
                _('Text beside icon'),
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon),
        )

    def _slot_systray_icon(self, action: QAction):
        self.config.set_systray(action.data())
        self.config.save()

    def _set_toolbar_button_style(self, toolbar, style):
        """Set toolbar button style and store the selected index."""
        toolbar.setToolButtonStyle(style)
        StateData().toolbar_button_style = style.value

    def _context_menu_button_style(self,
                                    point: QPoint,
                                    toolbar: QToolBar) -> None:
        """Open a context menu to modify styling of tooblar buttons
        buttons.
        """
        menu = QMenu(self)
        group = QActionGroup(self)


        for text, style in self._button_styles():
            action = QAction(text, self)
            action.setCheckable(True)
            action.setChecked(toolbar.toolButtonStyle() == style)
            group.addAction(action)
            action.triggered.connect(
                lambda _, s=style:
                self._set_toolbar_button_style(toolbar, s)
                )

        menu.addActions(group.actions())

        menu.exec(toolbar.mapToGlobal(point))

    def _create_main_toolbar(self):
        """Create the main toolbar and connect it to actions."""

        toolbar = self.addToolBar('main')
        toolbar.setFloatable(False)

        # Context menu to modify button styling for main toolbar
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        toolbar.customContextMenuRequested.connect(
            lambda point: self._context_menu_button_style(point, toolbar))

        # Restore button styling for main toolbar
        toolbar.setToolButtonStyle(
            Qt.ToolButtonStyle(StateData().toolbar_button_style))

        # Drop-Down: Profiles
        self.comboProfiles = ProfileCombo(self)
        self.comboProfilesAction = toolbar.addWidget(self.comboProfiles)

        actions_for_toolbar = [
            self.act_take_snapshot,
            self.act_pause_take_snapshot,
            self.act_resume_take_snapshot,
            self.act_stop_take_snapshot,
            self.act_update_snapshots,
            self.act_name_snapshot,
            self.act_remove_snapshot,
            self.act_snapshot_logview,
            self.act_last_logview,
            self.act_settings,
            self.act_shutdown,
        ]

        # Add each action to toolbar
        for act in actions_for_toolbar:
            toolbar.addAction(act)

            button_tip = act.text()

            # Assume an explicit tooltip if it is different from "text()".
            # Note that Qt use "text()" as "toolTip()" by default.
            if act.toolTip() != button_tip:

                if QApplication.instance().isRightToLeft():
                    # RTL/BIDI language like Hebrew
                    button_tip = f'{act.toolTip()} :{button_tip}'
                else:
                    # (default) LTR language (e.g. English)
                    button_tip = f'{button_tip}: {act.toolTip()}'

            button_tip = textwrap.fill(
                button_tip, width=26, break_long_words=False)

            toolbar.widgetForAction(act).setToolTip(button_tip)

        # toolbar sub menu: take snapshot
        submenu_take_snapshot = QMenu(self)
        submenu_take_snapshot.addAction(self.act_take_snapshot)
        submenu_take_snapshot.addAction(self.act_take_snapshot_checksum)
        submenu_take_snapshot.setToolTipsVisible(True)

        # get the toolbar buttons widget...
        button_take_snapshot = toolbar.widgetForAction(self.act_take_snapshot)
        # ...and add the menu to it
        button_take_snapshot.setMenu(submenu_take_snapshot)
        button_take_snapshot.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        # separators and stretchers
        toolbar.insertSeparator(self.act_settings)
        toolbar.insertSeparator(self.act_shutdown)

    def _label_dir_dont_exist(self) -> tuple[QLabel, QLabel]:
        """The labels will replace the filesview if a directory, selected
        in the places widget, does not exist in the backup (if selected) or
        the current file system ("Now" is selected).
        """
        def _setup_label(label_text: str) -> QLabel:
            label = QLabel(f'<strong>{label_text}</strong>', self)
            label.setWordWrap(True)

            label.setFrameShadow(QFrame.Shadow.Sunken)
            label.setFrameShape(QFrame.Shape.Panel)
            label.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            return label

        label_backup = _setup_label(_(
            "This directory doesn't exist in the selected backup."
        ))
        label_now = _setup_label(_(
            "This directory doesn't exist on the computer."
        ))

        return label_now, label_backup

    def _files_view_toolbar(self):
        """Create the filesview toolbar object, connect it to actions and
        return it for later use.

        Returns:
            The toolbar object."""

        toolbar = QToolBar(self)
        toolbar.setFloatable(False)

        actions_for_toolbar = [
            self.act_folder_up,
            self.act_show_hidden,
            self.act_restore,
            self.act_snapshots_dialog,
        ]

        toolbar.addActions(actions_for_toolbar)

        # LineEdit widget to display the current path
        self.widget_current_path = QLineEdit(self)
        self.widget_current_path.setReadOnly(True)
        toolbar.insertWidget(self.act_show_hidden, self.widget_current_path)

        # Restore sub menu
        restore_sub_menu = self.act_restore_menu.menu()
        # get the toolbar buttons widget...
        button_restore = toolbar.widgetForAction(self.act_restore)
        # ...and add the menu to it
        button_restore.setMenu(restore_sub_menu)
        button_restore.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        # Fine tuning
        toolbar.insertSeparator(self.act_restore)

        return toolbar

    def closeEvent(self, event):
        state_data = StateData()
        profile_state = state_data.profile(self.config.currentProfile())

        # Dev note (buhtz, 2025-04): Makes not much sense to me. Investigate.
        if self.shutdown.ask_before_quit():
            msg = _(
                'If this window is closed, Back In Time will not be able '
                'to shut down your system when the backup is finished.'
            )
            msg = msg + '\n'
            msg = msg + _('Close the window anyway?')

            answer = messagebox.question(text=msg, widget_to_center_on=self)
            if not answer:
                return event.ignore()

        profile_state.last_path = pathlib.Path(self.path)

        profile_state.places_sorting = self.places.get_sorting()

        if self.isMaximized():
            state_data.set_mainwindow_maximized()
        else:
            state_data.mainwindow_coords = (self.x(), self.y())
            state_data.mainwindow_dims = (self.width(), self.height())

        state_data.mainwindow_main_splitter_widths = self.mainSplitter.sizes()
        state_data.mainwindow_second_splitter_widths \
            = self.secondSplitter.sizes()
        state_data.files_view_col_widths = [
            self.filesView.header().sectionSize(idx)
            for idx
            in range(self.filesView.header().count())
        ]
        state_data.files_view_sorting = (
            self.filesView.header().sortIndicatorSection(),
            self.filesView.header().sortIndicatorOrder().value
        )

        self.filesView.model.deleteLater()

        # umount
        try:
            mnt = self._profile_operations.get_mount_manager()
            mnt.umount()

        except MountException as ex:
            messagebox.critical(self, str(ex))

        self.config.save()
        state_data.save()

        # cleanup temporary local copies of files which were opened in GUI
        for d in self.tmpDirs:
            d.cleanup()

        event.accept()

    def updateProfiles(self):
        if self.disableProfileChanged:
            return

        self.disableProfileChanged = True

        self.comboProfiles.clear()

        qttools.update_combo_profiles(
            self.config, self.comboProfiles, self.config.currentProfile())
        # profiles = self.config.profilesSortedByName()

        # self.comboProfilesAction.setVisible(len(profiles) > 1)

        self.updateProfile()

        self.disableProfileChanged = False

    def _reset_profile_operations(self):
        if self._profile_operations:
            mount = self._profile_operations.get_mount_manager()
            mount.umount()

        self._profile_operations = ProfileOperations(
            profile_id=self.config.currentProfile(),
            config=self.config
        )

    def updateProfile(self):
        profile_id = self.config.currentProfile()

        self._reset_profile_operations()

        mount = self._profile_operations.get_mount_manager()
        try:
            mount.mount()

        except MountError as exc:
            logger.error(str(exc))
            messagebox.critical(
                self,
                exc.gui_msg,
                _('Backup destination unavailable')
            )

        except FileNotFoundError as exc:
            messagebox.critical(
                self,
                str(exc),
                _('Backup destination unavailable')
            )

        self.rebuild_timeline()
        self.places.do_update()
        self._update_files_widget()
        self.updateFilesView(0)

        self.event_profile_changed.notify(self._profile_operations)

        state_data = StateData()
        profile_state = state_data.profile(profile_id)

        try:
            sorting = profile_state.places_sorting

        except KeyError:
            pass

        else:
            self.places.set_sorting(sorting)

    def comboProfileChanged(self, _index):
        if self.disableProfileChanged:
            return

        profile_id = self.comboProfiles.current_profile_id()
        if not profile_id:
            return

        old_profile_id = self.config.currentProfile()

        state_data = StateData()

        if profile_id != old_profile_id:
            old_profile_state = state_data.profile(old_profile_id)
            old_profile_state.places_sorting = self.places.get_sorting()

            # self.remount(profile_id, old_profile_id)
            self.config.setCurrentProfile(profile_id)

            profile_state = state_data.profile(profile_id)
            try:
                sorting = profile_state.places_sorting
            except KeyError:
                pass
            else:
                self.places.set_sorting(sorting)

            old_profile_state.last_path = pathlib.Path(self.path)
            path = str(profile_state.last_path)

            if not path == self.path:
                self.path = path
                self.path_history.reset(self.path)
                self.widget_current_path.setText(self.path)

            self.updateProfile()

    def raiseApplication(self):
        raiseCmd = self.appInstance.raiseCommand()
        if raiseCmd is None:
            return

        logger.debug("Raise cmd: %s" % raiseCmd, self)
        self.qapp.alert(self)

    def _update_backup_status(self, force_wait_lock=False):
        """Update the statusbar and progress indicator with latest message
        from the snapshot message file.

        This method is called via a timeout event. See
        `self.timerUpdateTakeSnapshot`. Also see
        `Snapshots.takeSnapshotMessage()` for further details.
        """
        paused, fake_busy = self._handle_wait_locker(force_wait_lock)

        takeSnapshotMessage = self.snapshots.takeSnapshotMessage()

        if fake_busy:
            if takeSnapshotMessage is None:
                takeSnapshotMessage = (0, '…')

        elif takeSnapshotMessage is None:
            takeSnapshotMessage = self.lastTakeSnapshotMessage
            if takeSnapshotMessage is None:
                takeSnapshotMessage = (0, _('Done'))

        force_update = (
            fake_busy == False
            and self.act_take_snapshot.isEnabled() == False)

        self._handle_fake_busy(fake_busy, paused)

        mount_manager = self._profile_operations.get_mount_manager()
        # mount_manager.mount()

        if not self.act_take_snapshot.isEnabled():
            # TODO: check if there is a more elegant way than always get a
            # new snapshot list which is very expensive (time)
            # See issue #2260 about redesign the IPC aspect of BIT
            mount_manager = self._profile_operations.get_mount_manager()
            snapshotsList = snapshots.listSnapshots(
                cfg=self.config,
                includeNewSnapshot=False,
                reverse=True,
                mounted_path=mount_manager.path
            )

            if snapshotsList != self.snapshotsList:
                self.snapshotsList = snapshotsList
                self._rebuild_timeline_without_refresh()
                takeSnapshotMessage = (0, _('Done'))
            else:
                if takeSnapshotMessage[0] == 0:
                    takeSnapshotMessage = (0, _('Done, no backup needed'))

            # Check `activate_shutdown` here, instead of shutdownagent.py
            # function `shutdown` should just focus on shutting down a machine
            if self.shutdown.activate_shutdown and get_shutdown_confirmation():
                self.shutdown.shutdown()

        message = self._set_take_snapshot_message(
            message=takeSnapshotMessage,
            force_update=force_update,
            fake_busy=fake_busy)

        self._update_progress_bar(message)

    def _handle_wait_locker(self, force_wait_lock):
        if force_wait_lock:
            self.forceWaitLockCounter = 10

        busy = self.snapshots.busy()

        if busy:
            self.forceWaitLockCounter = 0
            paused = tools.processPaused(self.snapshots.pid())

        else:
            paused = False

        if self.forceWaitLockCounter > 0:
            self.forceWaitLockCounter = self.forceWaitLockCounter - 1

        fake_busy = busy or self.forceWaitLockCounter > 0

        return paused, fake_busy

    def _handle_fake_busy(self, fake: bool, paused: bool):
        """What is this???"""

        if fake:  # ???
            if self.act_take_snapshot.isEnabled():
                self.act_take_snapshot.setEnabled(False)
                self.act_take_snapshot_checksum.setEnabled(False)

            if not self.act_take_snapshot.isVisible():
                for action in (self.act_pause_take_snapshot,
                               self.act_resume_take_snapshot,
                               self.act_stop_take_snapshot):
                    action.setEnabled(True)

            self.act_take_snapshot.setVisible(False)
            self.act_take_snapshot_checksum.setVisible(False)
            self.act_pause_take_snapshot.setVisible(not paused)
            self.act_resume_take_snapshot.setVisible(paused)
            self.act_stop_take_snapshot.setVisible(True)

        elif not self.act_take_snapshot.isEnabled():
            self.act_take_snapshot.setVisible(True)
            self.act_take_snapshot.setEnabled(True)
            self.act_take_snapshot_checksum.setVisible(True)
            self.act_take_snapshot_checksum.setEnabled(True)

            for action in (self.act_pause_take_snapshot,
                           self.act_resume_take_snapshot,
                           self.act_stop_take_snapshot):
                action.setVisible(False)

    def _set_take_snapshot_message(self,
                                   message: tuple[int, str],
                                   force_update: bool,
                                   fake_busy: bool) -> str:

        if message == self.lastTakeSnapshotMessage and not force_update:
            return _('Working:')

        self.lastTakeSnapshotMessage = message

        last = self.lastTakeSnapshotMessage[1].replace('\n', ' ')

        if fake_busy:
            message = '{}: {}'.format(_('Working'), last)

        elif message[0] == 0:
            message = last

        else:
            message = '{}: {}'.format(_('Error'), last)

        self.status_bar.set_status_message(message)

        return message

    def _update_progress_bar(self, message: str):

        pg = progress.ProgressFile(
            filename=self.config.takeSnapshotProgressFile()
        )

        if not pg.fileReadable():  # Why not?
            self.status_bar.progress_hide()
            return

        self.status_bar.progress_show()
        pg.load()
        pg_data = pg.get_data()

        # Ugly workaround. See #2260
        if not pg_data:
            return

        self.status_bar.set_progress_value(pg_data['percent'])
        message = ' | '.join(self.getProgressBarFormat(pg_data, message))
        self.status_bar.set_status_message(message)

    def getProgressBarFormat(self,
                             pg_data: dict,
                             message: str) -> Generator[str, None, None]:
        """Generates formatted components of a progress bar display.

        This generator yields individual parts of a progress message, including
        the percentage completed, optionally the amount sent, current
        speed, estimated time remaining (ETA), and a custom message.
        Values are extracted from the provided progress object `pg`.

        Args:
            pg (progress.ProgressFile): An object that provides progress
                information through methods like `intValue` and `strValue`.
                Expected keys include 'percent', 'sent', 'speed', and 'eta'.
            message (str): A custom message to append at the end of the
                progress bar.

        Yields:
            str: Formatted strings representing different segments of the
                progress bar.
        """
        d = (
            ('sent', _('Sent:')),
            ('speed', _('Speed:')),
            ('eta', _('ETA:'))
        )

        yield f'{pg_data["percent"]}%'

        for key, txt in d:
            value = pg_data.get(key, '')

            if not value:
                continue

            yield f'{txt} {value}'

        yield message

    def _enable_snapshot_actions(self, enable: bool = True):
        self.act_name_snapshot.setEnabled(enable)
        self.act_remove_snapshot.setEnabled(enable)
        self.act_snapshot_logview.setEnabled(enable)
        # self._enable_restore_ui_elements(enable)

    def is_now_selected(self) -> bool:
        """Workaround"""
        return self.timeline.is_now_selected()

    def _on_now_selected(self):
        print('_on_NOW_selected()')  # DEBUG
        self._enable_snapshot_actions(False)
        self.updateFilesView(2)

    def _on_backup_selected(self, _sid):
        print('_on_backup_selected()')  # DEBUG
        self._enable_snapshot_actions(True)
        self.updateFilesView(2)

    def _rebuild_timeline_without_refresh(self):
        """Initiate recreation of the timeline content based on the existing
        list of backups/snapshots without refreshing the snapshot list via
        a thread."""
        with self.timeline.preserve_selection():
            self.timeline.clear_and_reset()

            # pylint: disable-next=duplicate-code
            for sid in self.snapshotsList:
                self.timeline.create_backup_entry(
                    descriptor=sid.get_descriptor(),
                    timestamp=sid.get_timestamp(),
                    last_checked=sid.lastChecked,
                    label=sid.displayName
                )

    def rebuild_timeline(self):
        """Get a fresh list of backups/snapshots and initiate update of the
        timeline content with that list."""

        previous_selection = self.timeline.selected_backup_descriptor()

        self.timeline.clear_and_reset()

        self.snapshotsList = []  # TODO: -> backup_list ???
        backup_queue = queue.Queue()

        mount_manager = self._profile_operations.get_mount_manager()

        def _worker():
            """Proceed all backups and put their timline related information
            into a thread-safe queue."""

            for sid in snapshots.iterSnapshots(
                    cfg=self.config,
                    includeNewSnapshot=False,
                    mounted_path=mount_manager.path
            ):
                self.snapshotsList.append(sid)
                backup_queue.put(
                    (
                        sid.get_descriptor(),
                        sid.get_timestamp(),
                        sid.lastChecked,
                        sid.displayName
                    )
                )
            backup_queue.put(None)  # Finished signal

        def _process_queue():
            """Read backup data from the queue and add them to the timeline.

            The queue processing is finished when the sentinel value `None` is
            received.
            """
            while True:
                try:
                    entry = backup_queue.get_nowait()
                except queue.Empty:
                    # Queue is empty (but not finished). Try again later.
                    QTimer.singleShot(100, _process_queue)
                    return

                # Queue finished?
                if entry is None:
                    if previous_selection:
                        self.timeline.select_by_descriptor(previous_selection)
                    else:
                        self.timeline.select_now()
                    # mount_manager.umount()
                    return

                self.timeline.create_backup_entry(
                    descriptor=entry[0],
                    timestamp=entry[1],
                    last_checked=entry[2],
                    label=entry[3]
                )

        # Start getting backups
        threading.Thread(target=_worker, daemon=True).start()

        # Start updating the timeline widget with backups
        QTimer.singleShot(250, _process_queue)

    def _create_temporary_copy(self, full_path: str, sid=None):
        """Create a temporary local copy a file or directory.

        The name of is of the pattern ``backintime_[tmp_str]_[snapshotID]``.
        Clean up is done when closing BIT based on ``self.tmpDirs``.

        Args:
            full_path (str): Path to original file or directory.
            sid (snapshots.SID): Snapshot identifier.

        Returns:
            str: Path to the temporary file or directory.
        """
        if sid:
            sid = '_' + sid.sid

        d = TemporaryDirectory(prefix='backintime_', suffix=sid)
        tmp_file = os.path.join(d.name, os.path.basename(full_path))

        if os.path.isdir(full_path):
            shutil.copytree(full_path, tmp_file, symlinks=True)
        else:
            shutil.copy(full_path, d.name)

        self.tmpDirs.append(d)

        return tmp_file

    def _on_files_view_path_clicked(self, path):
        self._open_path(path)

    def _open_path(self, rel_path: str):
        rel_path = os.path.join(self.path, rel_path)

        if self.timeline.is_now_selected():
            full_path = rel_path

        else:
            backup_id = self.selected_backup_id()

            if not backup_id.isExistingPathInsideSnapshotFolder(rel_path):
                return

            full_path = backup_id.pathBackup(rel_path)

        if not os.path.exists(full_path):
            return

        if os.path.isdir(full_path):
            self.path = rel_path
            self.path_history.append(rel_path)
            self.updateFilesView(0)

            return

        # prevent backup data from being accidentally overwritten
        # by create a temporary local copy and only open that one
        if not self.timeline.is_now_selected():
            full_path = self._create_temporary_copy(full_path, backup_id)

        file_url = QUrl('file://' + full_path)
        QDesktopServices.openUrl(file_url)

    def _update_files_widget(self):
        if self.timeline.is_now_selected():
            text = _('Now')

        else:
            name = self.timeline.selected_backup_label()
            # buhtz (2023-07)3 blanks at the end of that string as a
            # workaround to a visual issue where the last character was
            # cutoff. Not sure if this is DE and/or theme related.
            # Wasn't able to reproduc in an MWE. Remove after refactoring.
            text = '{} {}   '.format(_('Backup:'), name)

        self.filesWidget.setTitle(text)

    # @pyqtSlot(int)
    def updateFilesView(self,
                        changed_from,
                        _selected_file=None,
                        _show_snapshots=False):
        """
        changed_from? WTF!
            0 - files view change directory,
            1 - files view,
            2 - time_line,
            3 - places

        To-Do : make it oboslete. Use Events for timeline and places
        """

        # if changed_from in (0, 3):
        #     _selected_file = ''

        # TODO: Places should react on filesview.event_XYZ
        if changed_from == 0:
            # update places
            self.places.setCurrentItem(None)

            # each places entry
            for place_index in range(self.places.topLevelItemCount()):
                item = self.places.topLevelItem(place_index)
                # if current path(??) is present in places, select it
                if self.path == str(item.data(0, Qt.ItemDataRole.UserRole)):
                    self.places.setCurrentItem(item)
                    break

        self._update_files_widget()

        backup_id = self.selected_backup_id()

        if backup_id:
            full_path = backup_id.pathBackup(self.path)
        else:
            # Dev note (2026-03, buhtz): Dirty WORKAROUND.
            # RootSnapshot need to be deleted. Its features
            # might go into ProfileOperations
            root_now_sid = snapshots.RootSnapshot(self.config)
            full_path = root_now_sid.pathBackup(self.path)

        # Dev note: Places (and timeline) should emit a select change event.
        # the handler in mainwindow than should decide about enable or disable
        # all this other UI elements.
        if os.path.isdir(full_path):
            enable_flag = True
            self.filesView.show_hidden(self.showHiddenFiles)
            self.filesView.set_root_path(full_path)
            self.stackFilesView.setCurrentWidget(self.filesView)

        else:
            enable_flag = False
            self.stackFilesView.setCurrentWidget(
                self._label_not_a_now_dir if self.timeline.is_now_selected()
                else self._label_not_a_backup_dir
            )

        self.toolbar_filesview.setEnabled(enable_flag)
        self._enable_restore_ui_elements(enable_flag, self.path)
        self.act_snapshots_dialog.setEnabled(
            False if self.is_now_selected() else enable_flag
        )

        # show current path
        self.widget_current_path.setText(self.path)

        # update folder_up button state
        self.act_folder_up.setEnabled(len(self.path) > 1)

    def _enable_restore_ui_elements(self, enable, path=None):
        """Enable or disable all buttons and menu entries related to the
        restore feature.

        Args:
            enable(bool): Enable or disable.

        If a specific snapshot is selected in the timeline widget then all
        restore UI elements are enabled. If "Now" (the first/root) is selected
        in the timeline all UI elements related to restoring should be
        disabled.
        """
        print('restore enabled:', enable)

        # The whole sub-menu incl. its button/entry. The related UI elements
        # are the "Restore" entry in the main-menu and the toolbar button in
        # the files-view toolbar.
        self.act_restore_menu.setEnabled(enable)

        # This two entries do appear, independent from the sub-menu above, in
        # the context menu of the files view.
        self.act_restore.setEnabled(enable)
        self.act_restore_to.setEnabled(enable)

        print(
            'menu:',
            self.act_restore_menu.text(),
            self.act_restore_menu.isEnabled()
        )

        print(
            'restore:',
            self.act_restore.isEnabled(),
            self.act_restore_to.isEnabled()
        )

        if path:
            self.act_restore_parent.setText(
                _('Restore {path}').format(path=path))
            self.act_restore_parent_to.setText(
                _('Restore {path} to …').format(path=path))

    @contextmanager
    def suspend_mouse_button_navigation(self):
        """Temporary disable the mouse button event filter."""
        self.qapp.removeEventFilter(self._mouse_button_event_filter)

        yield

        self.qapp.installEventFilter(self._mouse_button_event_filter)

    def _open_approach_translator_dialog(self, cutoff=101):
        code = self.config.language_used
        name, perc = tools.get_native_language_and_completeness(code)

        if perc > cutoff:
            return

        def _complete_text(language: str, percent: int) -> str:
            # (2023-08): Move to packages meta-data (pyproject.toml).
            _URL_PLATFORM = bitbase.URL_TRANSLATION
            _URL_PROJECT = bitbase.URL_WEBSITE

            txt = _(
                'Hello'
                '\n'
                'You have used Back In Time in the {language} '
                'language a few times by now.'
                '\n'
                'The translation of your installed version of Back In Time '
                'into {language} is {perc} complete. Regardless of your '
                'level of technical expertise, you can contribute to the '
                'translation and thus Back In Time itself.'
                '\n'
                'Please visit the {translation_platform_url} if you wish '
                'to contribute. For further assistance and questions, '
                'please visit the {back_in_time_project_website}.'
                '\n'
                'We apologize for the interruption, and this message '
                'will not be shown again. This dialog is available at '
                'any time via the help menu.'
                '\n'
                'Your Back In Time Team'
            )

            # Wrap paragraphs in <p> tags.
            result = ''
            for t in txt.split('\n'):
                result = f'{result}<p>{t}</p>'

            # Insert data in placeholder variables.
            platform_url \
                = f'<a href="{_URL_PLATFORM}">' \
                + _('translation platform') \
                + '</a>'

            project_url \
                = f'<a href="{_URL_PROJECT}">Back In Time ' \
                + _('Website') \
                + ' </a>'

            result = result.format(
                language=f'<strong>{language}</strong>',
                perc=f'<strong>{percent} %</strong>',
                translation_platform_url=platform_url,
                back_in_time_project_website=project_url
            )

            return result

        dlg = UserMessageDialog(
            parent=self,
            title=_('Your translation'),
            full_label=_complete_text(name, perc))
        dlg.exec()

    def _open_language_remove_statement(self):
        code = self.config.language_used
        name, _ = tools.get_native_language_and_completeness(code)

        txt = [
            f'The selected language ({name}) will be <strong>removed in the '
            'next version</strong>.',
            'Reason: No recent '
            f'<a href="{bitbase.URL_TRANSLATION}">translation activity</a> '
            'and no active maintainer.',
            'New translators are welcome. Guidance and support are '
            'provided by '
            f'<a href="{bitbase.URL_WEBSITE}">the project</a>.',
            'The project maintainers regret this change. However, continuing '
            'support without active maintenance leads to quality issues.'
        ]
        txt = '\n'.join(txt)

        dlg = UserMessageDialog(
            parent=self,
            title=f'{name} will be removed soon',
            full_label=txt)
        dlg.exec()

    def _open_release_candidate_dialog(self):
        html_contact_list = (
            '<ul>'
            '<li>{mastodon}</li>'
            '<li>{mailinglist}</li>'
            '<li>{issue}</li>'
            '<li>{email}</li>'
            '<li>{alternative}</li>'
            '</ul>').format(
                mastodon=_('In the Fediverse at Mastodon: {link_and_label}.') \
                    .format(link_and_label='<a href="https://fosstodon.org'
                                           '/@backintime">'
                                           '@backintime@fosstodon.org'
                                           '</a>'),
                email=_('Email to {link_and_label}.').format(
                    link_and_label='<a href="mailto:backintime-project'
                                   '@posteo.de">'
                                   'backintime-project@posteo.de</a>'),
                mailinglist=_('Mailing list {link_and_label}.').format(
                    link_and_label='<a href="https://mail.python.org/mailman3/'
                                   'lists/bit-dev.python.org/">'
                                   'bit-dev@python.org</a>'),
                issue=_('{link_and_label} on the project website.').format(
                    link_and_label='<a href="{url}">{open_issue}</a>').format(
                        url=bitbase.URL_ISSUES_CREATE_NEW,
                        open_issue=_('Open an issue')),
                alternative=_('Alternatively, you can use another channel '
                              'of your choice.')
            )

        rc_message = _(
            'This version of Back In Time is a Release Candidate and is '
            'primarily intended for stability testing in preparation for the '
            'next official release.'
            '\n'
            'No user data or telemetry is collected. However, the Back In '
            'Time team is very interested in knowing if the Release Candidate '
            'is being used and if it is worth continuing to provide such '
            'pre-release versions.'
            '\n'
            'Therefore, the team kindly asks for a short feedback on whether '
            'you have tested this version, even if you didn’t encounter any '
            'issues. Even a quick test run of a few minutes would help us a '
            'lot.'
            '\n'
            'The following contact options are available:'
            '\n'
            '{contact_list}'
            '\n'
            "In this version, this message won't be shown again but can be "
            'accessed anytime through the help menu.'
            '\n'
            'Thank you for your support and for helping us improve '
            'Back In Time!'
            '\n'
            'Your Back In Time Team').format(contact_list=html_contact_list)

        dlg = UserMessageDialog(
            parent=None,
            title=_('Release Candidate'),
            full_label=rc_message)
        dlg.exec()

    def _cipher_using_profiles(self) -> bool:
        """Check if any of the SSH profiles explicit configured a cipher."""

        ssh_cipher_profiles = []

        # all profiles
        for pid in self.config.profiles():
            # SSH only
            if 'ssh' not in self.config.snapshotsMode(pid):
                continue

            # cipher other than "default"
            if self.config.sshCipher(pid) != 'default':
                ssh_cipher_profiles.append(
                    f'{self.config.profileName(pid)} ({pid})')

        return ssh_cipher_profiles

    def _open_ssh_cipher_remove_dialog(self, ssh_cipher_profiles):
        """SSH cipher removed (#2176)"""

        def _complete_text(profiles: list[str]) -> str:
            txt = (
                'SSH Cipher are not supported anymore!',
                'Explicitly configured SSH cipher setting detected in the '
                'following backup profiles:',
                '{profiles}',
                'The setting will be removed <strong>immediately</strong>.',
                'Recommended action:',
                'Please configure the preferred cipher in the SSH client'
                'config file (e.g. ~/.ssh/config) instead.',
                'Your Back In Time Team'
            )
            txt = '\n'.join(txt)

            # Wrap paragraphs in <p> tags.
            result = ''
            for t in txt.split('\n'):
                result = f'{result}<p>{t}</p>'

            profiles = '<ul>' \
                + ''.join(f'<li>{profile}</li>' for profile in profiles) \
                + '</ul>'

            return result.format(profiles=profiles)

        dlg = UserMessageDialog(
            parent=self,
            title='Removing SSH cipher setting',
            full_label=_complete_text(ssh_cipher_profiles))
        dlg.exec()

    def _open_remote_host_check_deprecation_dialog(self, profiles):
        """SSH check remote host deprecation (#2482)"""

        def _complete_text(profiles) -> str:
            txt = (
                'Some of the profiles <strong>disabled</strong> one or two '
                'of these settings:',
                '<ul>'
                '<li>' + _('Check if remote host is online') + '</li>'
                '<li>' + _('Check if remote host supports all '
                         'necessary commands.') + '</li></ul>',
                'Those might not be supported anymore in the near future. '
                'Please contact the project and describe your needs.',
                'The affected backup profiles are:',
                '{profiles}',
            )
            txt = '\n'.join(txt)

            # Wrap paragraphs in <p> tags.
            result = ''
            for t in txt.split('\n'):
                result = f'{result}<p>{t}</p>'

            profiles = '<ul>' \
                + ''.join(f'<li>{profile}</li>' for profile in set(profiles)) \
                + '</ul>'

            return result.format(profiles=profiles)

        dlg = UserMessageDialog(
            parent=self,
            title='Deprecation of SSH Check Remote Host settings',
            full_label=_complete_text(profiles)
        )
        dlg.exec()

    # |---------------|
    # | Create Backup |
    # |---------------|
    def _slot_backup_create(self):
        self._create_backup(checksum=False)

    def _slot_backup_create_with_checksum(self):
        self._create_backup(checksum=True)

    def _create_backup(self, checksum: bool) -> None:
        sn = snapshots.Snapshots(self.config)
        real = sn.get_free_space_at_destination()

        if real is not None:
            warn = sn.config.warnFreeSpace()
            if warn >= real:
                msg = _('Only {free} free space available on the '
                        'destination, which is below the configured threshold '
                        'of {threshold}.').format(
                            free=str(real),
                            threshold=str(warn))
                qst = _('Proceed with the backup?')
                proceed = messagebox.warning(
                    f'<p>{msg}</p><p>{qst}</p>', as_question=True)

                if proceed is False:
                    return

        backintime.takeSnapshotAsync(self.config, checksum=checksum)
        self._update_backup_status(True)

    def _send_signal_to_backup_process(self, sig: signal.Signals) -> bool:
        """Send a POSIX signal to the backup process.

        If the process has already terminated, the GUI state is refreshed and
        ``False`` is returned instead of propagating ``ProcessLookupError``.

        Returns:
            ``True`` if the signal was sent successfully, otherwise
                ``False``.

        """
        try:
            os.kill(self.snapshots.pid(), sig)

        except ProcessLookupError:
            self._update_backup_status(True)

            return False

        return True

    def _slot_backup_stop(self):
        if self._send_signal_to_backup_process(signal.SIGKILL):
            self.snapshots.setTakeSnapshotMessage(0, 'Backup terminated')

        self.act_stop_take_snapshot.setEnabled(False)
        self.act_pause_take_snapshot.setEnabled(False)
        self.act_resume_take_snapshot.setEnabled(False)

    # |---------|
    # | Restore |
    # |---------|
    def _restore_confirm_delete(self,
                                warnRoot=False,
                                restoreTo=None) -> bool:

        if restoreTo:
            msg = _('All newer files in {path} will be removed. '
                    'Proceed?').format(path=restoreTo)
        else:
            msg = _('All newer files in the original directory will be '
                    'removed. Proceed?')

        if warnRoot:
            msg = f'<p>{msg}</p><p>'
            msg = msg + _(
                '{BOLD}Warning{BOLDEND}: Deleting files in the filesystem '
                'root could break the entire system.').format(
                    BOLD='<strong>', BOLDEND='</strong>')
            msg = msg + '</p>'

        return messagebox.question(text=msg, widget_to_center_on=self)

    def _restore_to(self, paths: list[str]):
        with self.suspend_mouse_button_navigation():
            dir_dialog = FileDialog(
                parent=self,
                title=_('Restore to …'),
                show_hidden=True,
                allow_multiselection=False,
                dirs_only=True)

            path_restore_to = dir_dialog.result()

            if not path_restore_to:
                return

            path_restore_to = str(path_restore_to)

            confirm_dlg = ConfirmRestoreDialog(
                parent=self,
                paths=paths,
                to_path=path_restore_to,
                backup_on_restore=self.config.backupOnRestore(),
                backup_suffix=self.snapshots.backupSuffix()
            )

            if not confirm_dlg.answer():
                return

            opt = confirm_dlg.get_values_as_dict()

            if opt['delete'] \
               and not self._restore_confirm_delete(
                   warnRoot='/' in paths, restoreTo=path_restore_to):
                return

        rd = RestoreDialog(self,
                           self.selected_backup_id(),
                           # what
                           paths if len(paths) > 1 else paths[0],
                           # where
                           path_restore_to,
                           **opt)

        rd.exec()

    def _slot_restore_this(self):
        if self.is_now_selected():
            return

        paths = self.filesView.get_selected_paths()
        # Workaround
        if not paths:
            paths = ['/']
        # paths = [f for f, idx in self.multiFileSelected(fullPath = True)]

        confirm_dlg = ConfirmRestoreDialog(
            parent=self,
            paths=paths,
            to_path=None,
            backup_on_restore=self.config.backupOnRestore(),
            backup_suffix=self.snapshots.backupSuffix()
        )

        with self.suspend_mouse_button_navigation():
            if not confirm_dlg.answer():
                return

            if confirm_dlg.delete_newer:
                if not self._restore_confirm_delete(warnRoot='/' in paths):
                    return

        opt = confirm_dlg.get_values_as_dict()

        rd = RestoreDialog(
            parent=self,
            sid=self.selected_backup_id(),
            what=paths,
            **opt)
        rd.exec()

    def _slot_restore_this_to(self):
        """Restore current in GUI selected backup to ..."""

        # paths = [f for f, _idx in self.multiFileSelected(fullPath=True)]
        paths = self.filesView.get_selected_paths()

        # Workaround
        if not paths:
            paths = ['/']

        self._restore_to(paths)

    def _slot_restore_parent(self):
        if self.is_now_selected():
            return

        confirm_dlg = ConfirmRestoreDialog(
            parent=self,
            paths=(self.path, ),
            to_path=None,
            backup_on_restore=self.config.backupOnRestore(),
            backup_suffix=self.snapshots.backupSuffix()
        )

        with self.suspend_mouse_button_navigation():
            if not confirm_dlg.answer():
                return

            opt = confirm_dlg.get_values_as_dict()

            if opt['delete'] and not self._restore_confirm_delete(
                    warnRoot=self.path == '/'):
                return

        rd = RestoreDialog(
            self,
            self.selected_backup_id(),
            self.path,
            **opt
        )
        rd.exec()

    def _slot_restore_parent_to(self):
        """Restore parent directory (of current selected) to ..."""
        if self.is_now_selected():
            return

        self._restore_to([self.path])

    # |------------|
    # | Files View |
    # |------------|
    def _slot_files_view_dir_up(self):
        if len(self.path) <= 1:
            return

        # like Path.parent
        path = os.path.dirname(self.path)

        if self.path == path:
            return

        self.path = path
        self.path_history.append(self.path)
        self.updateFilesView(0)

    def _slot_files_view_dir_history_previous(self):
        self._dir_history(self.path_history.previous())

    def _slot_files_view_dir_history_next(self):
        self._dir_history(self.path_history.next())

    def _dir_history(self, path):
        backup_id = self.selected_backup_id()

        if backup_id is None:
            # Directory history navigation is snapshot-based. When "Now" is
            # selected there is no backup context to resolve the stored path
            # against, so mouse back/forward should simply do nothing.
            return

        full_path = backup_id.pathBackup(path)

        if (os.path.isdir(full_path)
                and backup_id.isExistingPathInsideSnapshotFolder(path)):
            self.path = path
            self.updateFilesView(0)

    def _slot_files_view_open_current_item(self):
        path = self.filesView.get_current_path()

        if not path:
            return

        self._open_path(path)

    def _slot_files_view_hidden_files_toggled(self, checked: bool):
        self.showHiddenFiles = checked
        self.filesView.show_hidden(checked)
        # self.updateFilesView(1)

    # |-----------------|
    # | some more Slots |
    # |-----------------|
    def _slot_timeline_refresh(self):
        self.rebuild_timeline()
        self.updateFilesView(2)

    def _slot_backup_open_last_log(self):
        with self.suspend_mouse_button_navigation():
            # no SID argument in constructor means "show last log"
            logviewdialog.LogViewDialog(self).show()

    def _slot_backup_open_log(self):
        if self.timeline.is_now_selected():
            return

        descriptor = self.timeline.selected_backup_descriptor()
        if descriptor is None:
            return

        with self.suspend_mouse_button_navigation():
            # Workaround
            mount_manager = MountManager.create(self.config)
            sid = snapshots.SID(descriptor, self.config, mount_manager.path)

            dlg = logviewdialog.LogViewDialog(self, sid)
            dlg.exec()

            if sid != dlg.sid:
                self.timeline.select_by_descriptor(dlg.sid)

    def _slot_manage_profiles(self):
        with self.suspend_mouse_button_navigation():
            SettingsDialog(self).show()

    def _slot_shutdown_toggled(self, checked):
        self.shutdown.activate_shutdown = checked

    def _slot_snapshots_dialog(self):
        #  path = self.filesView.get_current_path()
        # print(f'slot_snapshots_dialog() :: {path=} {self.path=}')

        with self.suspend_mouse_button_navigation():
            backup_id = self.selected_backup_id()
            dlg = snapshotsdialog.SnapshotsDialog(self, backup_id, self.path)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                # ToDo: MainWindow (or its timeline) should describe to the
                # dialogs event_backup_selected
                if dlg.sid != backup_id:
                    self.timeline.select_by_descriptor(
                        dlg.sid.get_descriptor()
                    )

    def _slot_backup_name(self):
        sid = self.selected_backup_id()

        if not sid:
            # "Now" or none selected
            return

        name = sid.name

        new_name, accept = QInputDialog.getText(
            self, _('Backup name'), '', text = name)
        if not accept:
            return

        new_name = new_name.strip()
        if name == new_name:
            return

        sid.name = new_name
        item = self.timeline.get_backup_item(sid.get_descriptor())
        item.label = sid.displayName

    def _slot_backup_remove(self):
        def hideItem(item):
            try:
                item.setHidden(True)
            except RuntimeError:
                # item has been deleted
                # probably because user pressed refresh
                pass

        # try to use filter(..)
        items = [
            item for item in self.timeline.selectedItems()
            if not isinstance(item, snapshots.RootSnapshot)
        ]

        if not items:
            return

        question_msg = '{}\n{}'.format(
            ngettext(
                'Remove this backup?',
                'Remove these backups?',
                len(items)
            ),
            '\n'.join(self.timeline.get_all_selected_backup_labels())
        )

        answer = messagebox.question(
            text=question_msg,
            widget_to_center_on=self
        )

        if not answer:
            return

        self.timeline.select_now()

        for item in items:
            item.setDisabled(True)

        thread = RemoveSnapshotThread(self, items)
        thread.refreshSnapshotList.connect(self.rebuild_timeline)
        thread.hideTimelineItem.connect(hideItem)
        thread.start()

    def _slot_add_to_include(self):
        # paths = [f for f, idx in self.multiFileSelected(fullPath=True)]
        paths = self.filesView.get_selected_paths()
        include = self.config.include()
        updatePlaces = False

        for item in paths:

            if os.path.isdir(item):
                include.append((item, 0))
                updatePlaces = True
            else:
                include.append((item, 1))

        self.config.setInclude(include)

        if updatePlaces:
            self.places.do_update()

    def _slot_add_to_exclude(self):

        paths = self.filesView.get_selected_paths()
        # paths = [f for f, idx in self.multiFileSelected(fullPath = True)]
        exclude = self.config.exclude()
        exclude.extend(paths)
        self.config.setExclude(exclude)

    def _slot_setup_language(self):
        """Show a modal language settings dialog and modify the UI language
        settings."""

        dlg = languagedialog.LanguageDialog(
            used_language_code=self.config.language_used,
            configured_language_code=self.config.language())

        dlg.exec()

        # Apply/OK pressed & the language value modified
        if dlg.result() == 1 and self.config.language() != dlg.language_code:

            self.config.setLanguage(dlg.language_code)

            messagebox.info(_('The language settings take effect only after '
                              'restarting Back In Time.'),
                            widget_to_center_on=dlg)

    def _slot_help_about(self):
        with self.suspend_mouse_button_navigation():
            dlg = AboutDlg(
                using_translation=self.config.language_used != 'en',
                parent=self
            )
            dlg.exec()

    def _slot_help_user_manual(self):
        qttools.open_user_manual()

    def _slot_help_man_backintime(self):
        qttools.open_man_page(
            'backintime', self.act_help_man_backintime.icon())

    def _slot_help_man_config(self):
        qttools.open_man_page(
            'backintime-config', self.act_help_man_config.icon())

    def _slot_help_website(self):
        qttools.open_url(bitbase.URL_WEBSITE)

    def _slot_help_contact(self):
        qttools.open_url(bitbase.URL_CONTACT)

    def _slot_help_changelog(self):
        markdown = False
        if bitbase.CHANGELOG_LOCAL_PATH.exists():
            qttools.open_url(str(bitbase.CHANGELOG_LOCAL_PATH))
            return

        if bitbase.CHANGELOG_DEBIAN_GZ.exists():
            try:
                import gzip
                with gzip.open(bitbase.CHANGELOG_DEBIAN_GZ, 'rt') as handle:
                    td = TextDialog(
                        content=handle.read(),
                        markdown=markdown,
                        title=_('Changelog'),
                        icon=self.act_help_changelog.icon()
                    )
                    td.exec()
                    return
            except Exception as exc:
                logger.error(
                    f'Unexpected exception while opening changelog. {exc}'
                )

        # Fallback: Use upstream website changelog
        qttools.open_url(bitbase.URL_CHANGELOG)

    def _slot_help_faq(self):
        qttools.open_url(bitbase.URL_FAQ)

    def _slot_help_encryption(self):
        qttools.open_url(bitbase.URL_ENCRYPT_TRANSITION)

    def _slot_help_report_bug(self):
        qttools.open_url(bitbase.URL_ISSUES_CREATE_NEW)

    def _slot_help_translation(self):
        self._open_approach_translator_dialog()

    def _slot_help_release_candidate(self):
        self._open_release_candidate_dialog()

    def _slot_edit_user_callback(self):
        fp = pathlib.Path(self.config.takeSnapshotUserCallback())
        dlg = EditUserCallback(parent=self, script_path=fp)
        dlg.exec()


class RemoveSnapshotThread(QThread):
    """
    remove snapshots in background thread so GUI will not freeze
    """
    refreshSnapshotList = pyqtSignal()
    hideTimelineItem = pyqtSignal(timeline.BackupEntry)

    def __init__(self, parent, items):
        self.config = parent.config
        self.snapshots = parent.snapshots
        self.items = items
        self.mount_manager = MountManager.create(self.config)
        super().__init__(parent)

    def run(self):
        last_snapshot = snapshots.lastSnapshot(
            self.config, mounted_path=self.mount_manager.path
        )
        renew_last_snapshot = False

        # inhibit suspend/hibernate during delete
        with InhibitSuspend(reason='deleting snapshots'):

            for item, sid in [
                    (
                        x,
                        snapshots.SID(
                            date=x.descriptor,
                            cfg=self.config,
                            mounted_path=self.mount_manager.path
                        )
                    )
                    for x in self.items
            ]:
                self.snapshots.remove(sid)
                self.hideTimelineItem.emit(item)
                if sid == last_snapshot:
                    renew_last_snapshot = True

            self.refreshSnapshotList.emit()

            # set correct last snapshot again
            if renew_last_snapshot:
                self.snapshots.createLastSnapshotSymlink(
                    snapshots.lastSnapshot(
                        self.config,
                        self.mount_manager.path
                    )
                )


def _get_state_data_from_config(cfg: config.Config) -> StateData:
    """Get data related to application state from the config instance.

    It migrates state data from the config file to an instance of
    `StateData` which later is saved in a separate file.

    This function is a temporary workaround. See PR #1850.

    Args:
       cfg: The config instance.

    Returns:
        dict: The state data.
        """

    data = StateData()

    # internal.manual_starts_countdown
    data['manual_starts_countdown'] \
        = int(cfg.the_dict().get('internal.manual_starts_countdown', 10))

    # internal.msg_rc
    val = cfg.the_dict().get('internal.msg_rc', None)
    if val:
        data.msg_release_candidate = val

    # internal.msg_shown_encfs
    val = cfg.the_dict().get('internal.msg_shown_encfs', 0)
    if val:
        data.msg_encfs_global = val

    # qt.show_hidden_files
    data.mainwindow_show_hidden = cfg.the_dict().get(
        'qt.show_hidden_files', False
    )

    # Coordinates and dimensions
    val = (
        cfg.the_dict().get('qt.main_window.x', None),
        cfg.the_dict().get('qt.main_window.y', None)
    )

    if all(val):
        data.mainwindow_coords = val

    val = (
        cfg.the_dict().get('qt.main_window.width', None),
        cfg.the_dict().get('qt.main_window.height', None)
    )
    if all(val):
        data.mainwindow_dims = val

    val = (
        cfg.the_dict().get('qt.logview.width', None),
        cfg.the_dict().get('qt.logview.height', None)
    )
    if all(val):
        data.logview_dims = val

    # files view
    # Dev note (buhtz, 2024-12): Ignore the column width values because of a
    # bug. Three columns are tracked but the widget has four columns. The "Typ"
    # column is treated as "Date" and the width of the real "Date" column (4th)
    # was never stored.
    # The new state file will load and store width values for all existing
    # columns.
    # qt.main_window.files_view.name_width
    # qt.main_window.files_view.size_width
    # qt.main_window.files_view.date_width

    col = cfg.the_dict().get('qt.main_window.files_view.sort.column', 0)
    order = cfg.the_dict().get(
        'qt.main_window.files_view.sort.ascending', True)
    data.files_view_sorting = (col, 0 if order else 1)

    # splitter width
    widths = (
        cfg.the_dict().get('qt.main_window.main_splitter_left_w', None),
        cfg.the_dict().get('qt.main_window.main_splitter_right_w', None)
    )
    if all(widths):
        data.mainwindow_main_splitter_widths = widths

    widths = (
        cfg.the_dict().get('qt.main_window.second_splitter_left_w', None),
        cfg.the_dict().get('qt.main_window.second_splitter_right_w', None)
    )
    if all(widths):
        data.mainwindow_second_splitter_widths = widths

    # each profile
    for profile_id in cfg.profiles():
        profile_state = data.profile(profile_id)

        # # profile specific encfs warning
        # val = cfg.the_dict().get(f'profile{profile_id}.msg_shown_encfs', 0)
        # profile_state.msg_encfs = val

        # qt.last_path
        key = 'profile' + profile_id + '.' + 'qt.last_path'
        try:
            profile_state.last_path = pathlib.Path(cfg.the_dict()[key])
        except KeyError:
            pass

        # Places: sorting
        sorting = (
            cfg.the_dict().get(
                f'profile{profile_id}.qt.places.SortColumn', None
            ),
            cfg.the_dict().get(
                f'profile{profile_id}.qt.places.SortOrder', None
            )
        )
        if all(sorting):
            profile_state.places_sorting = sorting

        # Manage profiles - Exclude tab: sorting
        sorting = (
            cfg.the_dict().get(
                f'profile{profile_id}.qt.settingsdialog.exclude.SortColumn',
                None
            ),
            cfg.the_dict().get(
                f'profile{profile_id}.qt.settingsdialog.exclude.SortOrder',
                None
            )
        )
        if all(sorting):
            profile_state.exclude_sorting = sorting

        # Manage profiles - Include tab: sorting
        sorting = (
            cfg.the_dict().get(
                f'profile{profile_id}.qt.settingsdialog.include.SortColumn',
                None
            ),
            cfg.the_dict().get(
                f'profile{profile_id}.qt.settingsdialog.include.SortOrder',
                None
            )
        )
        if all(sorting):
            profile_state.include_sorting = sorting

    return data


def load_state_data(cfg: config.Config) -> None:
    """Initiate the `State` instance.

    The state file is loaded and its data stored in `State`. The later is a
    singleton and can be used everywhere.

    Args:
       args: Arguments given from command line.
    """
    fp = StateData.file_path()

    try:
        # load file
        StateData(json.loads(fp.read_text(encoding='utf-8')))

    except FileNotFoundError:
        logger.debug('State file not found. Using config file and migrate it'
                     'into a state file.')
        fp.parent.mkdir(parents=True, exist_ok=True)
        _get_state_data_from_config(cfg)

    except json.decoder.JSONDecodeError as exc:
        logger.warning(
            f'Unable to read and decode state file "{fp}". Ignnoring it.'
        )
        logger.debug(f'{exc=}')

        try:
            raw_content = fp.read_text(encoding='utf-8')
            logger.debug(f'raw_content="{raw_content}"')
        except Exception as exc_raw:
            logger.debug(f'{exc_raw=}')

        # Empty state data with default values
        StateData()


if __name__ == '__main__':
    cfg = backintime.startApp(bitbase.BINARY_NAME_GUI)

    raiseCmd = ''
    if len(sys.argv) > 1:
        raiseCmd = '\n'.join(sys.argv[1:])

    appInstance = guiapplicationinstance.GUIApplicationInstance(raiseCmd)
    cfg.PLUGIN_MANAGER.load(cfg=cfg)
    cfg.PLUGIN_MANAGER.appStart()

    qapp = qttools.create_qapplication(bitbase.APP_NAME)
    translator = qttools.initiate_translator(cfg.language())
    qapp.installTranslator(translator)

    load_state_data(cfg)

    mainWindow = MainWindow(cfg, appInstance, qapp)

    # if cfg.isConfigured():
    config_fp = bitbase.context['--config']
    if config_fp.exists():
        mainWindow.show()
        qapp.exec()
    else:
        messagebox.critical(
            None,
            f'Unexpected situation. Config file {config_fp} does not exists. '
            'Please contact the support or try to start Back In Time again.'
        )

    mainWindow.qapp.removeEventFilter(mainWindow._mouse_button_event_filter)

    cfg.PLUGIN_MANAGER.appExit()
    appInstance.exitApplication()

    logger.closelog()  # must be last line (log until BiT "dies" ;-)
