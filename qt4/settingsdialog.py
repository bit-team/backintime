#    Back In Time
#    Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze, Taylor Raack
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


import os
import datetime
import gettext
import copy
import grp

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import config
import tools
import qt4tools
import mount
import messagebox
from exceptions import MountException

_=gettext.gettext


class SettingsDialog( QDialog ):
    def __init__( self, parent ):
        super(SettingsDialog, self).__init__(parent)

        self.parent = parent
        self.config = parent.config
        self.snapshots = parent.snapshots
        self.config_copy_dict = copy.copy( self.config.dict )
        self.current_profile_org = self.config.get_current_profile()
        import icon
        self.icon = icon

        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle( _( 'Settings' ) )

        self.main_layout = QVBoxLayout(self)

        #profiles
        layout = QHBoxLayout()
        self.main_layout.addLayout( layout )

        layout.addWidget( QLabel( _('Profile:'), self ) )

        self.first_update_all = True
        self.disable_profile_changed = True
        self.combo_profiles = qt4tools.ProfileCombo(self)
        layout.addWidget( self.combo_profiles, 1 )
        QObject.connect( self.combo_profiles, SIGNAL('currentIndexChanged(int)'), self.current_profile_changed )
        self.disable_profile_changed = False

        self.btn_edit_profile = QPushButton(icon.PROFILE_EDIT, _('Edit'), self )
        QObject.connect( self.btn_edit_profile, SIGNAL('clicked()'), self.edit_profile )
        layout.addWidget( self.btn_edit_profile )

        # update to full system backup button
        self.btn_modify_profile_for_full_system_backup = QPushButton(icon.ADD, _('Modify for Full System Backup'), self )
        QObject.connect( self.btn_modify_profile_for_full_system_backup, SIGNAL('clicked()'), self.modify_profile_for_full_system_backup )
        layout.addWidget( self.btn_modify_profile_for_full_system_backup )

        self.btn_add_profile = QPushButton(icon.ADD, _('Add'), self)
        QObject.connect( self.btn_add_profile, SIGNAL('clicked()'), self.add_profile )
        layout.addWidget( self.btn_add_profile )

        self.btn_remove_profile = QPushButton(icon.REMOVE, _('Remove'), self)
        QObject.connect( self.btn_remove_profile, SIGNAL('clicked()'), self.remove_profile )
        layout.addWidget( self.btn_remove_profile )

        #TABs
        self.tabs_widget = QTabWidget( self )
        self.main_layout.addWidget( self.tabs_widget )

        #occupy whole space for tabs
        scrollButtonDefault = self.tabs_widget.usesScrollButtons()
        self.tabs_widget.setUsesScrollButtons(False)

        #TAB: General
        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.NoFrame)
        self.tabs_widget.addTab( scrollArea, _( 'General' ) )

        layoutWidget = QWidget(self)
        layout = QVBoxLayout(layoutWidget)

        #select mode
        self.mode = None
        vlayout = QVBoxLayout()
        layout.addLayout( vlayout )

        self.lbl_modes = QLabel( _( 'Mode:' ), self )

        self.combo_modes = QComboBox( self )
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.lbl_modes)
        hlayout.addWidget(self.combo_modes, 1)
        vlayout.addLayout(hlayout)
        store_modes = {}
        for key in list(self.config.SNAPSHOT_MODES.keys()):
            store_modes[key] = self.config.SNAPSHOT_MODES[key][1]
        self.fill_combo( self.combo_modes, store_modes )

        #encfs security warning
        self.encfsWarning = QLabel(_("<b>Warning:</b> %(app)s uses EncFS for encryption. A recent security audit "
                                     "revealed several possible attack vectors for this. "
                                     "Please take a look at 'A NOTE ON SECURITY' in 'man backintime'.") \
                                   % {'app': self.config.APP_NAME} )
        self.encfsWarning.setWordWrap(True)
        layout.addWidget(self.encfsWarning)

        #Where to save snapshots
        group_box = QGroupBox( self )
        self.mode_local = group_box
        group_box.setTitle( _( 'Where to save snapshots' ) )
        layout.addWidget( group_box )

        vlayout = QVBoxLayout( group_box )

        hlayout = QHBoxLayout()
        vlayout.addLayout( hlayout )

        self.edit_snapshots_path = QLineEdit( self )
        self.edit_snapshots_path.setReadOnly( True )
        QObject.connect( self.edit_snapshots_path, SIGNAL('textChanged(QString)'), self.on_full_path_changed )
        hlayout.addWidget( self.edit_snapshots_path )

        self.btn_snapshots_path = QToolButton(self)
        self.btn_snapshots_path.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btn_snapshots_path.setIcon(icon.FOLDER)
        self.btn_snapshots_path.setText(_('Folder'))
        self.btn_snapshots_path.setMinimumSize(32,28)
        hlayout.addWidget( self.btn_snapshots_path )
        QObject.connect( self.btn_snapshots_path, SIGNAL('clicked()'), self.on_btn_snapshots_path_clicked )

        #SSH
        group_box = QGroupBox( self )
        self.mode_ssh = group_box
        group_box.setTitle( _( 'SSH Settings' ) )
        layout.addWidget( group_box )

        vlayout = QVBoxLayout( group_box )

        hlayout1 = QHBoxLayout()
        vlayout.addLayout( hlayout1 )
        hlayout2 = QHBoxLayout()
        vlayout.addLayout( hlayout2 )
        hlayout3 = QHBoxLayout()
        vlayout.addLayout( hlayout3 )

        self.lbl_ssh_host = QLabel( _( 'Host:' ), self )
        hlayout1.addWidget( self.lbl_ssh_host )
        self.txt_ssh_host = QLineEdit( self )
        hlayout1.addWidget( self.txt_ssh_host )

        self.lbl_ssh_port = QLabel( _( 'Port:' ), self )
        hlayout1.addWidget( self.lbl_ssh_port )
        self.txt_ssh_port = QLineEdit( self )
        hlayout1.addWidget( self.txt_ssh_port )

        self.lbl_ssh_user = QLabel( _( 'User:' ), self )
        hlayout1.addWidget( self.lbl_ssh_user )
        self.txt_ssh_user = QLineEdit( self )
        hlayout1.addWidget( self.txt_ssh_user )

        self.lbl_ssh_path = QLabel( _( 'Path:' ), self )
        hlayout2.addWidget( self.lbl_ssh_path )
        self.txt_ssh_path = QLineEdit( self )
        QObject.connect( self.txt_ssh_path, SIGNAL('textChanged(QString)'), self.on_full_path_changed )
        hlayout2.addWidget( self.txt_ssh_path )

        self.lbl_ssh_cipher = QLabel( _( 'Cipher:' ), self )
        hlayout3.addWidget( self.lbl_ssh_cipher )
        self.combo_ssh_cipher = QComboBox( self )
        hlayout3.addWidget( self.combo_ssh_cipher )
        self.fill_combo( self.combo_ssh_cipher, self.config.SSH_CIPHERS )

        self.lbl_ssh_private_key_file = QLabel( _( 'Private Key:' ), self )
        hlayout3.addWidget( self.lbl_ssh_private_key_file )
        self.txt_ssh_private_key_file = QLineEdit( self )
        self.txt_ssh_private_key_file.setReadOnly( True )
        hlayout3.addWidget( self.txt_ssh_private_key_file )

        self.btn_ssh_private_key_file = QToolButton(self)
        self.btn_ssh_private_key_file.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btn_ssh_private_key_file.setIcon(icon.FOLDER)
        self.btn_ssh_private_key_file.setText(_('Key File'))
        self.btn_ssh_private_key_file.setMinimumSize(32,28)
        hlayout3.addWidget( self.btn_ssh_private_key_file )
        QObject.connect( self.btn_ssh_private_key_file, SIGNAL('clicked()'), self.on_btn_ssh_private_key_file_clicked )
        qt4tools.equal_indent(self.lbl_ssh_host, self.lbl_ssh_path, self.lbl_ssh_cipher)

        #encfs
        self.mode_local_encfs = self.mode_local
        self.mode_ssh_encfs = self.mode_ssh

        #password
        group_box = QGroupBox( self )
        self.frame_password_1 = group_box
        group_box.setTitle( _( 'Password' ) )
        layout.addWidget( group_box )

        vlayout = QVBoxLayout( group_box )
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)

        self.lbl_password_1 = QLabel( _( 'Password' ), self )
        hlayout1.addWidget( self.lbl_password_1 )
        self.txt_password_1 = QLineEdit( self )
        self.txt_password_1.setEchoMode(QLineEdit.Password)
        hlayout1.addWidget( self.txt_password_1 )

        self.lbl_password_2 = QLabel( _( 'Password' ), self )
        hlayout2.addWidget( self.lbl_password_2 )
        self.txt_password_2 = QLineEdit( self )
        self.txt_password_2.setEchoMode(QLineEdit.Password)
        hlayout2.addWidget( self.txt_password_2 )

        self.cb_password_save = QCheckBox( _( 'Save Password to Keyring' ), self )
        vlayout.addWidget( self.cb_password_save )

        self.cb_password_use_cache = QCheckBox( _( 'Cache Password for Cron (Security issue: root can read password)' ), self )
        vlayout.addWidget( self.cb_password_use_cache )

        self.keyring_supported = tools.keyring_supported()
        self.cb_password_save.setEnabled(self.keyring_supported)

        #mode change
        QObject.connect( self.combo_modes, SIGNAL('currentIndexChanged(int)'), self.on_combo_modes_changed )

        #host, user, profile id
        group_box = QGroupBox( self )
        self.frame_advanced = group_box
        group_box.setTitle( _( 'Advanced' ) )
        layout.addWidget( group_box )

        hlayout = QHBoxLayout( group_box )
        hlayout.addSpacing( 12 )

        vlayout2 = QVBoxLayout()
        hlayout.addLayout( vlayout2 )

        hlayout2 = QHBoxLayout()
        vlayout2.addLayout( hlayout2 )

        self.lbl_host = QLabel( _( 'Host:' ), self )
        hlayout2.addWidget( self.lbl_host )
        self.txt_host = QLineEdit( self )
        QObject.connect( self.txt_host, SIGNAL('textChanged(QString)'), self.on_full_path_changed )
        hlayout2.addWidget( self.txt_host )

        self.lbl_user = QLabel( _( 'User:' ), self )
        hlayout2.addWidget( self.lbl_user )
        self.txt_user = QLineEdit( self )
        QObject.connect( self.txt_user, SIGNAL('textChanged(QString)'), self.on_full_path_changed )
        hlayout2.addWidget( self.txt_user )

        self.lbl_profile = QLabel( _( 'Profile:' ), self )
        hlayout2.addWidget( self.lbl_profile )
        self.txt_profile = QLineEdit( self )
        QObject.connect( self.txt_profile, SIGNAL('textChanged(QString)'), self.on_full_path_changed )
        hlayout2.addWidget( self.txt_profile )

        self.lbl_full_path = QLabel(_('Full snapshot path: '), self)
        self.lbl_full_path.setWordWrap(True)
        vlayout2.addWidget(self.lbl_full_path)

        #Schedule
        group_box = QGroupBox( self )
        self.global_schedule_group_box = group_box
        group_box.setTitle( _( 'Schedule' ) )
        layout.addWidget( group_box )

        glayout = QGridLayout( group_box )
        glayout.setColumnStretch(1, 2)

        self.combo_automatic_snapshots = QComboBox( self )
        glayout.addWidget( self.combo_automatic_snapshots, 0, 0, 1, 2 )
        self.fill_combo( self.combo_automatic_snapshots, self.config.AUTOMATIC_BACKUP_MODES )

        self.lbl_automatic_snapshots_day = QLabel( _( 'Day:' ), self )
        self.lbl_automatic_snapshots_day.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_day.setAlignment( Qt.AlignRight | Qt.AlignVCenter )
        glayout.addWidget( self.lbl_automatic_snapshots_day, 1, 0 )

        self.combo_automatic_snapshots_day = QComboBox( self )
        glayout.addWidget( self.combo_automatic_snapshots_day, 1, 1 )

        for d in range( 1, 29 ):
            self.combo_automatic_snapshots_day.addItem( QIcon(), str(d), d )

        self.lbl_automatic_snapshots_weekday = QLabel( _( 'Weekday:' ), self )
        self.lbl_automatic_snapshots_weekday.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_weekday.setAlignment( Qt.AlignRight | Qt.AlignVCenter )
        glayout.addWidget( self.lbl_automatic_snapshots_weekday, 2, 0 )

        self.combo_automatic_snapshots_weekday = QComboBox( self )
        glayout.addWidget( self.combo_automatic_snapshots_weekday, 2, 1 )

        for d in range( 1, 8 ):
            self.combo_automatic_snapshots_weekday.addItem( QIcon(), datetime.date(2011, 11, 6 + d).strftime("%A"), d )

        self.lbl_automatic_snapshots_time = QLabel( _( 'Hour:' ), self )
        self.lbl_automatic_snapshots_time.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_time.setAlignment( Qt.AlignRight | Qt.AlignVCenter )
        glayout.addWidget( self.lbl_automatic_snapshots_time, 3, 0 )

        self.combo_automatic_snapshots_time = QComboBox( self )
        glayout.addWidget( self.combo_automatic_snapshots_time, 3, 1 )

        for t in range( 0, 2300, 100 ):
            self.combo_automatic_snapshots_time.addItem( QIcon(), datetime.time( t//100, t%100 ).strftime("%H:%M"), t )

        self.lbl_automatic_snapshots_time_custom = QLabel( _( 'Hours:' ), self )
        self.lbl_automatic_snapshots_time_custom.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_time_custom.setAlignment( Qt.AlignRight | Qt.AlignVCenter )
        glayout.addWidget( self.lbl_automatic_snapshots_time_custom, 4, 0 )

        self.txt_automatic_snapshots_time_custom = QLineEdit( self )
        glayout.addWidget( self.txt_automatic_snapshots_time_custom, 4, 1 )

        #anacron
        self.lbl_automatic_snapshots_anacron = QLabel(_('Run Back In Time repeatedly. This is useful if the computer is not running regular.'))
        self.lbl_automatic_snapshots_anacron.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_anacron.setWordWrap(True)
        glayout.addWidget(self.lbl_automatic_snapshots_anacron, 5, 0, 1, 2)

        self.lbl_automatic_snapshots_anacron_period = QLabel(_('Every:'))
        self.lbl_automatic_snapshots_anacron_period.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_anacron_period.setAlignment( Qt.AlignRight | Qt.AlignVCenter )
        glayout.addWidget(self.lbl_automatic_snapshots_anacron_period, 7, 0)

        hlayout = QHBoxLayout()
        self.sb_automatic_snapshots_anacron_period = QSpinBox(self)
        self.sb_automatic_snapshots_anacron_period.setSingleStep( 1 )
        self.sb_automatic_snapshots_anacron_period.setRange( 1, 10000 )
        hlayout.addWidget(self.sb_automatic_snapshots_anacron_period)

        self.combo_automatic_snapshots_anacron_unit = QComboBox( self )
        self.fill_combo( self.combo_automatic_snapshots_anacron_unit, self.config.REPEATEDLY_UNITS )
        hlayout.addWidget(self.combo_automatic_snapshots_anacron_unit)
        hlayout.addStretch()
        glayout.addLayout(hlayout, 7, 1)

        #udev
        self.lbl_automatic_snapshots_udev = QLabel(_('Run Back In Time as soon as the drive is connected (only once every X days).\nYou will be prompted for your sudo password.'))
        self.lbl_automatic_snapshots_udev.setWordWrap(True)
        glayout.addWidget(self.lbl_automatic_snapshots_udev, 6, 0, 1, 2)

        QObject.connect( self.combo_automatic_snapshots, SIGNAL('currentIndexChanged(int)'), self.current_automatic_snapshot_changed )

        #
        layout.addStretch()
        scrollArea.setWidget(layoutWidget)
        scrollArea.setWidgetResizable(True)

        #TAB: Include
        tab_widget = QWidget( self )
        self.tabs_widget.addTab( tab_widget, _( 'Include' ) )
        layout = QVBoxLayout( tab_widget )

        self.list_include = QTreeWidget( self )
        self.list_include.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_include.setRootIsDecorated( False )
        self.list_include.setHeaderLabels( [ _('Include files and folders'),
                                            'Count' ] )

        self.list_include_header = self.list_include.header()
        self.list_include_header.setResizeMode( 0, QHeaderView.Stretch )
        self.list_include_header.setClickable(True)
        self.list_include_header.setSortIndicatorShown(True)
        self.list_include_header.setSectionHidden(1, True)
        self.list_include_sort_loop = False
        QObject.connect(self.list_include_header,
                        SIGNAL('sortIndicatorChanged(int,Qt::SortOrder)'),
                        self.includeCustomSortOrder )

        layout.addWidget( self.list_include )
        self.list_include_count = 0

        buttons_layout = QHBoxLayout()
        layout.addLayout( buttons_layout )

        self.btn_include_file_add = QPushButton(icon.ADD, _('Add file'), self)
        buttons_layout.addWidget( self.btn_include_file_add )
        QObject.connect( self.btn_include_file_add, SIGNAL('clicked()'), self.on_btn_include_file_add_clicked )

        self.btn_include_add = QPushButton(icon.ADD, _('Add folder'), self)
        buttons_layout.addWidget( self.btn_include_add )
        QObject.connect( self.btn_include_add, SIGNAL('clicked()'), self.on_btn_include_add_clicked )

        self.btn_include_remove = QPushButton(icon.REMOVE, _('Remove'), self)
        buttons_layout.addWidget( self.btn_include_remove )
        QObject.connect( self.btn_include_remove, SIGNAL('clicked()'), self.on_btn_include_remove_clicked )

        #TAB: Exclude
        tab_widget = QWidget( self )
        self.tabs_widget.addTab( tab_widget, _( 'Exclude' ) )
        layout = QVBoxLayout( tab_widget )

        label = QLabel( _('<b>Warning:</b> Wildcards (\'foo*\', \'[fF]oo\', \'fo?\') will be ignored with mode \'SSH encrypted\'.\nOnly separate asterisk are allowed (\'foo/*\', \'foo/**/bar\')'), self )
        label.setWordWrap(True)
        self.lbl_ssh_encfs_exclude_warning = label
        layout.addWidget( label )

        self.list_exclude = QTreeWidget( self )
        self.list_exclude.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_exclude.setRootIsDecorated( False )
        self.list_exclude.setHeaderLabels( [ _('Exclude patterns, files or folders') ,
                                            'Count' ] )

        self.list_exclude_header = self.list_exclude.header()
        self.list_exclude_header.setResizeMode( 0, QHeaderView.Stretch )
        self.list_exclude_header.setClickable(True)
        self.list_exclude_header.setSortIndicatorShown(True)
        self.list_exclude_header.setSectionHidden(1, True)
        self.list_exclude_sort_loop = False
        QObject.connect(self.list_exclude_header,
                        SIGNAL('sortIndicatorChanged(int,Qt::SortOrder)'),
                        self.excludeCustomSortOrder )

        layout.addWidget( self.list_exclude )
        self.list_exclude_count = 0

        label = QLabel( _('Highly recommended:'), self )
        qt4tools.set_font_bold( label )
        layout.addWidget( label )
        label = QLabel( ', '.join(sorted(self.config.DEFAULT_EXCLUDE)), self )
        label.setWordWrap(True)
        layout.addWidget( label )

        buttons_layout = QHBoxLayout()
        layout.addLayout( buttons_layout )

        self.btn_exclude_add = QPushButton(icon.ADD, _('Add'), self)
        buttons_layout.addWidget( self.btn_exclude_add )
        QObject.connect( self.btn_exclude_add, SIGNAL('clicked()'), self.on_btn_exclude_add_clicked )

        self.btn_exclude_file = QPushButton(icon.ADD, _('Add file'), self)
        buttons_layout.addWidget( self.btn_exclude_file )
        QObject.connect( self.btn_exclude_file, SIGNAL('clicked()'), self.on_btn_exclude_file_clicked )

        self.btn_exclude_folder = QPushButton(icon.ADD, _('Add folder'), self)
        buttons_layout.addWidget( self.btn_exclude_folder )
        QObject.connect( self.btn_exclude_folder, SIGNAL('clicked()'), self.on_btn_exclude_folder_clicked )

        self.btn_exclude_default = QPushButton(icon.DEFAULT_EXCLUDE, _('Add default'), self)
        buttons_layout.addWidget(self.btn_exclude_default)
        QObject.connect(self.btn_exclude_default, SIGNAL('clicked()'), self.on_btn_exclude_default_clicked)

        self.btn_exclude_remove = QPushButton(icon.REMOVE, _('Remove'), self)
        buttons_layout.addWidget( self.btn_exclude_remove )
        QObject.connect( self.btn_exclude_remove, SIGNAL('clicked()'), self.on_btn_exclude_remove_clicked )

        #exclude files by size
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        self.cb_exclude_files_by_size = QCheckBox(_('Exclude files bigger than: '), self)
        self.cb_exclude_files_by_size.setToolTip(_('Exclude files bigger than value in %(prefix)s.\n' +\
        'With \'Full rsync mode\' disabled this will only affect new files\n' +\
        'because for rsync this is a transfer option, not an exclude option.\n' +\
        'So big files that has been backed up before will remain in snapshots\n' +\
        'even if they had changed.' %{'prefix': 'MiB'}))
        hlayout.addWidget(self.cb_exclude_files_by_size)
        self.sb_exclude_files_by_size = QSpinBox(self)
        self.sb_exclude_files_by_size.setSuffix(' MiB')
        self.sb_exclude_files_by_size.setRange( 0, 100000000 )
        hlayout.addWidget(self.sb_exclude_files_by_size)
        hlayout.addStretch()
        enabled = lambda state: self.sb_exclude_files_by_size.setEnabled(state)
        enabled(False)
        QObject.connect(self.cb_exclude_files_by_size, SIGNAL('stateChanged(int)'), enabled)

        #TAB: Auto-remove
        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.NoFrame)
        self.tabs_widget.addTab( scrollArea, _( 'Auto-remove' ) )

        layoutWidget = QWidget(self)
        layout = QGridLayout(layoutWidget)


        #remove old snapshots
        self.cb_remove_older_then = QCheckBox( _( 'Older than:' ), self )
        layout.addWidget( self.cb_remove_older_then, 0, 0 )
        QObject.connect( self.cb_remove_older_then, SIGNAL('stateChanged(int)'), self.update_remove_older_than )

        self.edit_remove_older_then = QSpinBox(self)
        self.edit_remove_older_then.setRange(1, 1000)
        layout.addWidget( self.edit_remove_older_then, 0, 1 )

        self.combo_remove_older_then = QComboBox( self )
        layout.addWidget( self.combo_remove_older_then, 0, 2 )
        self.fill_combo( self.combo_remove_older_then, self.config.REMOVE_OLD_BACKUP_UNITS )

        #min free space
        enabled, value, unit = self.config.get_min_free_space()

        self.cb_min_free_space = QCheckBox( _( 'If free space is less than:' ), self )
        layout.addWidget( self.cb_min_free_space, 1, 0 )
        QObject.connect( self.cb_min_free_space, SIGNAL('stateChanged(int)'), self.update_min_free_space )

        self.edit_min_free_space = QSpinBox(self)
        self.edit_min_free_space.setRange(1, 1000)
        layout.addWidget( self.edit_min_free_space, 1, 1 )

        self.combo_min_free_space = QComboBox( self )
        layout.addWidget( self.combo_min_free_space, 1, 2 )
        self.fill_combo( self.combo_min_free_space, self.config.MIN_FREE_SPACE_UNITS )

        #min free inodes
        self.cb_min_free_inodes = QCheckBox( _('If free inodes is less than:'), self)
        layout.addWidget(self.cb_min_free_inodes, 2, 0)

        self.edit_min_free_inodes = QSpinBox(self)
        self.edit_min_free_inodes.setSuffix(' %')
        self.edit_min_free_inodes.setSingleStep( 1 )
        self.edit_min_free_inodes.setRange( 0, 15 )
        layout.addWidget(self.edit_min_free_inodes, 2, 1)

        enabled = lambda state: self.edit_min_free_inodes.setEnabled(state)
        enabled(False)
        QObject.connect( self.cb_min_free_inodes, SIGNAL('stateChanged(int)'), enabled)

        #smart remove
        self.cb_smart_remove = QCheckBox( _( 'Smart remove' ), self )
        layout.addWidget( self.cb_smart_remove, 3, 0 )

        widget = QWidget( self )
        widget.setContentsMargins( 25, 0, 0, 0 )
        layout.addWidget( widget, 4, 0, 1, 3 )

        smlayout = QGridLayout( widget )

        self.cb_run_smart_remove_remote_in_background = QCheckBox(_('Run in background on remote Host.') + _(' EXPERIMENTAL!'), self)
        smlayout.addWidget(self.cb_run_smart_remove_remote_in_background, 0, 0, 1, 3)

        smlayout.addWidget( QLabel( _( 'Keep all snapshots for the last' ), self ), 1, 0 )
        self.edit_keep_all = QSpinBox(self)
        self.edit_keep_all.setRange(1, 10000)
        smlayout.addWidget( self.edit_keep_all, 1, 1 )
        smlayout.addWidget( QLabel( _( 'day(s)' ), self ), 1, 2 )

        smlayout.addWidget( QLabel( _( 'Keep one snapshot per day for the last' ), self ), 2, 0 )
        self.edit_keep_one_per_day = QSpinBox(self)
        self.edit_keep_one_per_day.setRange(1, 10000)
        smlayout.addWidget( self.edit_keep_one_per_day, 2, 1 )
        smlayout.addWidget( QLabel( _( 'day(s)' ), self ), 2, 2 )

        smlayout.addWidget( QLabel( _( 'Keep one snapshot per week for the last' ), self ), 3, 0 )
        self.edit_keep_one_per_week = QSpinBox(self)
        self.edit_keep_one_per_week.setRange(1, 10000)
        smlayout.addWidget( self.edit_keep_one_per_week, 3, 1 )
        smlayout.addWidget( QLabel( _( 'weeks(s)' ), self ), 3, 2 )

        smlayout.addWidget( QLabel( _( 'Keep one snapshot per month for the last' ), self ), 4, 0 )
        self.edit_keep_one_per_month = QSpinBox(self)
        self.edit_keep_one_per_month.setRange(1, 1000)
        smlayout.addWidget( self.edit_keep_one_per_month, 4, 1 )
        smlayout.addWidget( QLabel( _( 'month(s)' ), self ), 4, 2 )

        smlayout.addWidget( QLabel( _( 'Keep one snapshot per year for all years' ), self ), 5, 0, 1, 3 )

        enabled = lambda state: [smlayout.itemAt(x).widget().setEnabled(state) for x in range(smlayout.count())]
        enabled(False)
        QObject.connect( self.cb_smart_remove, SIGNAL('stateChanged(int)'), enabled)

        #don't remove named snapshots
        self.cb_dont_remove_named_snapshots = QCheckBox( _( 'Don\'t remove named snapshots' ), self )
        layout.addWidget( self.cb_dont_remove_named_snapshots, 5, 0, 1, 3 )

        #
        layout.addWidget( QWidget(self), 6, 0 )
        layout.setRowStretch( 6, 2 )
        scrollArea.setWidget(layoutWidget)
        scrollArea.setWidgetResizable(True)

        #TAB: Options
        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.NoFrame)
        self.tabs_widget.addTab( scrollArea, _( 'Options' ) )

        layoutWidget = QWidget(self)
        layout = QVBoxLayout(layoutWidget)

        self.cb_notify_enabled = QCheckBox( _( 'Enable notifications' ), self )
        layout.addWidget( self.cb_notify_enabled )

        self.cb_no_on_battery = QCheckBox( _( 'Disable snapshots when on battery' ), self )
        if not tools.power_status_available ():
            self.cb_no_on_battery.setEnabled ( False )
            self.cb_no_on_battery.setToolTip ( _( 'Power status not available from system' ) )
        layout.addWidget( self.cb_no_on_battery )

        self.cb_use_global_flock = QCheckBox(_('Run only one snapshot at a time'))
        self.cb_use_global_flock.setToolTip(_('Other snapshots will be blocked until the current snapshot is done.\n'
                                              'This is a global option. So it will effect all profiles for this user.\n'
                                              'But you need to activate this for all other users, too.'))
        layout.addWidget(self.cb_use_global_flock)

        self.cb_backup_on_restore = QCheckBox(_('Backup replaced files on restore'), self)
        self.cb_backup_on_restore.setToolTip( _('Newer versions of files will be '
                                                'renamed with trailing \'%(suffix)s\' '
                                                'before restoring.\n'
                                                'If you don\'t need them anymore '
                                                'you can remove them with \'%(cmd)s\'')
                                                %{'suffix': self.snapshots.backup_suffix(),
                                                'cmd': 'find ./ -name "*%s" -delete' % self.snapshots.backup_suffix() })
        layout.addWidget( self.cb_backup_on_restore )

        self.cb_continue_on_errors = QCheckBox( _( 'Continue on errors (keep incomplete snapshots)' ), self )
        layout.addWidget( self.cb_continue_on_errors )

        self.cb_use_checksum = QCheckBox( _( 'Use checksum to detect changes' ), self )
        layout.addWidget( self.cb_use_checksum )

        self.cb_full_rsync = QCheckBox( _( 'Full rsync mode. May be faster but:' ), self )
        label = QLabel( _('- snapshots are not read-only\n- destination file-system must support all Linux attributes (dates, rights, user, group ...)'), self)
        label.setIndent(36)
        label.setWordWrap(True)
        QObject.connect( self.cb_full_rsync, SIGNAL('stateChanged(int)'), self.update_check_for_changes )
        layout.addWidget( self.cb_full_rsync )
        layout.addWidget( label )

        self.cb_take_snapshot_regardless_of_changes = QCheckBox(_('Take a new snapshot regardless of there were changes or not.'))
        layout.addWidget(self.cb_take_snapshot_regardless_of_changes)

        self.cb_check_for_changes = QCheckBox( _( 'Check for changes (don\'t take a new snapshot if nothing changed)' ), self )
        layout.addWidget( self.cb_check_for_changes )

        #log level
        hlayout = QHBoxLayout()
        layout.addLayout( hlayout )

        hlayout.addWidget( QLabel( _('Log Level:'), self ) )

        self.combo_log_level = QComboBox( self )
        hlayout.addWidget( self.combo_log_level, 1 )

        self.combo_log_level.addItem( QIcon(), _('None'), 0 )
        self.combo_log_level.addItem( QIcon(), _('Errors'), 1 )
        self.combo_log_level.addItem( QIcon(), _('Changes & Errors'), 2 )
        self.combo_log_level.addItem( QIcon(), _('All'), 3 )

        #
        layout.addStretch()
        scrollArea.setWidget(layoutWidget)
        scrollArea.setWidgetResizable(True)

        #TAB: Expert Options
        scrollArea = QScrollArea(self)
        scrollArea.setFrameStyle(QFrame.NoFrame)
        self.tabs_widget.addTab( scrollArea, _( 'Expert Options' ) )

        layoutWidget = QWidget(self)
        layout = QVBoxLayout(layoutWidget)

        label = QLabel( _('Change these options only if you really know what you are doing !'), self )
        qt4tools.set_font_bold( label )
        layout.addWidget( label )

        label = QLabel(_("Run 'nice':"))
        layout.addWidget(label)
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        layout.addLayout(grid)

        self.cb_run_nice_from_cron = QCheckBox(_('as cron job') + self.printDefault(self.config.DEFAULT_RUN_NICE_FROM_CRON), self)
        grid.addWidget(self.cb_run_nice_from_cron, 0, 1)

        self.cb_run_nice_on_remote = QCheckBox(_('on remote host') + self.printDefault(self.config.DEFAULT_RUN_NICE_ON_REMOTE), self)
        grid.addWidget(self.cb_run_nice_on_remote, 1, 1)

        label = QLabel(_("Run 'ionice':"))
        layout.addWidget(label)
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        layout.addLayout(grid)

        self.cb_run_ionice_from_cron = QCheckBox(_('as cron job') + self.printDefault(self.config.DEFAULT_RUN_IONICE_FROM_CRON), self)
        grid.addWidget(self.cb_run_ionice_from_cron, 0, 1)

        self.cb_run_ionice_from_user = QCheckBox(_('when taking a manual snapshot') + self.printDefault(self.config.DEFAULT_RUN_IONICE_FROM_USER), self )
        grid.addWidget(self.cb_run_ionice_from_user, 1, 1)

        self.cb_run_ionice_on_remote = QCheckBox(_('on remote host') + self.printDefault(self.config.DEFAULT_RUN_IONICE_ON_REMOTE), self)
        grid.addWidget(self.cb_run_ionice_on_remote, 2, 1)

        self.nocacheAvailable = tools.check_command('nocache')
        label = QLabel(_("Run 'rsync' with 'nocache':"))
        layout.addWidget(label)
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        layout.addLayout(grid)

        self.cb_run_nocache_on_local = QCheckBox(_('on local machine') + self.printDefault(self.config.DEFAULT_RUN_NOCACHE_ON_LOCAL), self)
        self.cb_run_nocache_on_local.setEnabled(self.nocacheAvailable)
        grid.addWidget(self.cb_run_nocache_on_local, 0, 1)

        self.cb_run_nocache_on_remote = QCheckBox(_('on remote host') + self.printDefault(self.config.DEFAULT_RUN_NOCACHE_ON_REMOTE), self)
        grid.addWidget(self.cb_run_nocache_on_remote, 2, 1)

        self.cb_redirect_stdout = QCheckBox(_('Redirect stdout to /dev/null in cronjobs.')
                                            + self.printDefault(self.config.DEFAULT_REDIRECT_STDOUT_IN_CRON),
                                            self)
        self.cb_redirect_stdout.setToolTip('cron will automatically send an email with attached output of cronjobs if a MTA is installed.')
        layout.addWidget(self.cb_redirect_stdout)

        self.cb_redirect_stderr = QCheckBox(_('Redirect stderr to /dev/null in cronjobs.')
                                            + self.printDefault(self.config.DEFAULT_REDIRECT_STDERR_IN_CRON),
                                            self)
        self.cb_redirect_stderr.setToolTip('cron will automatically send an email with attached errors of cronjobs if a MTA is installed.')
        layout.addWidget(self.cb_redirect_stderr)

        #bwlimit
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        self.cb_bwlimit = QCheckBox( _( 'Limit rsync bandwidth usage: ' ), self )
        hlayout.addWidget( self.cb_bwlimit )
        self.sb_bwlimit = QSpinBox(self)
        self.sb_bwlimit.setSuffix(  _(' KB/sec') )
        self.sb_bwlimit.setSingleStep( 100 )
        self.sb_bwlimit.setRange( 0, 1000000 )
        hlayout.addWidget(self.sb_bwlimit)
        hlayout.addStretch()
        enabled = lambda state: self.sb_bwlimit.setEnabled(state)
        enabled(False)
        QObject.connect( self.cb_bwlimit, SIGNAL('stateChanged(int)'), enabled)
        self.cb_bwlimit.setToolTip(
                'uses \'rsync --bwlimit=RATE\'\n'
                'From \'man rsync\':\n'
                'This option allows you to specify the maximum transfer rate for\n'
                'the data sent over the socket, specified in units per second.\n'
                'The RATE value can be suffixed with a string to indicate a size\n'
                'multiplier, and may be a fractional value (e.g. "--bwlimit=1.5m").\n'
                'If no suffix is specified, the value will be assumed to be in\n'
                'units of 1024 bytes (as if "K" or "KiB" had been appended).\n'
                'See the --max-size option for a description of all the available\n'
                'suffixes. A value of zero specifies no limit.\n\n'
                'For backward-compatibility reasons, the rate limit will be\n'
                'rounded to the nearest KiB unit, so no rate smaller than\n'
                '1024 bytes per second is possible.\n\n'
                'Rsync writes data over the socket in blocks, and this option\n'
                'both limits the size of the blocks that rsync writes, and tries\n'
                'to keep the average transfer rate at the requested limit.\n'
                'Some "burstiness" may be seen where rsync writes out a block\n'
                'of data and then sleeps to bring the average rate into compliance.\n\n'
                'Due to the internal buffering of data, the --progress option\n'
                'may not be an accurate reflection on how fast the data is being\n'
                'sent. This is because some files can show up as being rapidly\n'
                'sent when the data is quickly buffered, while other can show up\n'
                'as very slow when the flushing of the output buffer occurs.\n'
                'This may be fixed in a future version.'
                )

        self.cb_preserve_acl = QCheckBox( _( 'Preserve ACL' ), self )
        self.cb_preserve_acl.setToolTip(
                'uses \'rsync -A\'\n'
                'From \'man rsync\':\n'
                'This option causes rsync to update the destination ACLs to be\n'
                'the same as the source ACLs. The option also implies --perms.\n\n'
                'The source and destination systems must have compatible ACL\n'
                'entries for this option to work properly.\n'
                'See the --fake-super option for a way to backup  and restore\n'
                'ACLs that are not compatible.'
                )
        layout.addWidget( self.cb_preserve_acl )

        self.cb_preserve_xattr = QCheckBox( _( 'Preserve extended attributes (xattr)' ), self )
        self.cb_preserve_xattr.setToolTip(
                'uses \'rsync -X\'\n'
                'From \'man rsync\':\n'
                'This option causes rsync to update the destination extended\n'
                'attributes to be the same as the source ones.\n\n'
                'For systems that support extended-attribute namespaces, a copy\n'
                'being done by a super-user copies all namespaces except\n'
                'system.*. A normal user only copies the user.* namespace.\n'
                'To be able to backup and restore non-user namespaces as a normal\n'
                'user, see the --fake-super option.\n\n'
                'Note that this option does not copy rsyncs special xattr values\n'
                '(e.g. those used by --fake-super) unless you repeat the option\n'
                '(e.g. -XX). This "copy all xattrs" mode cannot be used\n'
                'with --fake-super.'
                )
        layout.addWidget( self.cb_preserve_xattr )

        self.cb_copy_unsafe_links = QCheckBox( _( 'Copy unsafe links (works only with absolute links)' ), self )
        self.cb_copy_unsafe_links.setToolTip(
                'uses \'rsync --copy-unsafe-links\'\n'
                'From \'man rsync\':\n'
                'This tells rsync to copy the referent of symbolic links that\n'
                'point outside the copied tree. Absolute symlinks are also\n'
                'treated like ordinary files, and so are any symlinks in the\n'
                'source path itself when --relative is used. This option has\n'
                'no additional effect if --copy-links was also specified.\n'
                )
        layout.addWidget( self.cb_copy_unsafe_links )

        self.cb_copy_links = QCheckBox( _( 'Copy links (dereference symbolic links)' ), self )
        self.cb_copy_links.setToolTip(
                'uses \'rsync --copy-links\'\n'
                'From \'man rsync\':\n'
                'When symlinks are encountered, the item that they point to\n'
                '(the referent) is copied, rather than the symlink. In older\n'
                'versions of rsync, this option also had the side-effect of\n'
                'telling the receiving side to follow symlinks, such as\n'
                'symlinks to directories. In a modern rsync such as this one,\n'
                'you\'ll need to specify --keep-dirlinks (-K) to get this extra\n'
                'behavior. The only exception is when sending files to an rsync\n'
                'that is too old to understand -K -- in that case, the -L option\n'
                'will still have the side-effect of -K on that older receiving rsync.'
                )
        layout.addWidget( self.cb_copy_links )

        #additional rsync options
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        self.cb_rsync_options = QCheckBox( _('Paste additional options to rsync'), self)
        hlayout.addWidget(self.cb_rsync_options)
        self.txt_rsync_options = QLineEdit(self)
        self.txt_rsync_options.setToolTip( _('Options must be quoted e.g. --exclude-from="/path/to/my exclude file".') )
        hlayout.addWidget(self.txt_rsync_options)

        enabled = lambda state: self.txt_rsync_options.setEnabled(state)
        enabled(False)
        QObject.connect( self.cb_rsync_options, SIGNAL('stateChanged(int)'), enabled)

        #ssh prefix
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)
        self.cb_ssh_prefix = QCheckBox( _('Add prefix to SSH commands'), self)
        hlayout.addWidget(self.cb_ssh_prefix)
        self.txt_ssh_prefix = QLineEdit(self)
        self.txt_ssh_prefix.setToolTip( _('Prefix to run before every command on remote host.\n'
                                          'Variables need to be escaped with \$FOO.\n'
                                          'This doesn\'t touch rsync. So to add a prefix\n'
                                          'for rsync use "%(cb_rsync_options)s" with\n'
                                          '%(rsync_options_value)s\n\n'
                                          '%(default)s: %(def_value)s')
                                          % {'cb_rsync_options': self.cb_rsync_options.text(),
                                             'rsync_options_value': '--rsync-path="FOO=bar:\$FOO /usr/bin/rsync"',
                                             'default': _('default'),
                                             'def_value': self.config.DEFAULT_SSH_PREFIX})
        hlayout.addWidget(self.txt_ssh_prefix)

        enabled = lambda state: self.txt_ssh_prefix.setEnabled(state)
        enabled(False)
        QObject.connect( self.cb_ssh_prefix, SIGNAL('stateChanged(int)'), enabled)

        qt4tools.equal_indent(self.cb_rsync_options, self.cb_ssh_prefix)

        #
        layout.addStretch()
        scrollArea.setWidget(layoutWidget)
        scrollArea.setWidgetResizable(True)

        #buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent = self)
        btnRestore = button_box.addButton(_('Restore Config'), QDialogButtonBox.ResetRole)
        QObject.connect(button_box, SIGNAL('accepted()'), self.accept)
        QObject.connect(button_box, SIGNAL('rejected()'), self.reject)
        QObject.connect(btnRestore, SIGNAL('clicked()'), self.restoreConfig)
        self.main_layout.addWidget(button_box)

        self.update_profiles()
        self.on_combo_modes_changed()

        #enable tabs scroll buttons again but keep dialog size
        size = self.sizeHint()
        self.tabs_widget.setUsesScrollButtons(scrollButtonDefault)
        self.resize(size)

    def modify_profile_for_full_system_backup( self ):
        # verify to user that settings will change
        message = _("Full system backup can only create a snapshot to be restored to the same physical disk(s) "
            "with the same disk partitioning as from the source; restoring to new physical disks or the same disks "
            "with different partitioning will yield a potentially broken and unusable system.\n\n"
            "Full system backup will override some settings that may have been customized. Continue?")
        if QMessageBox.No == messagebox.warningYesNo(self, message):
            return

        # configure for full system backup
        # need full rsync
        self.config.set_full_rsync(True)
        # don't want to create a backup with any errors and give user false sense that backup was ok
        self.config.set_continue_on_errors(False)
        # make sure all files are backed up
        self.config.set_exclude_by_size_enabled(False)
        # when we restore the full system, don't want to keep old files (since we back up everything)
        self.config.set_backup_on_restore(False)
        # no need for checksum mode
        self.config.set_use_checksum(False)
        # must preserve ACLs and xattrs
        self.config.set_preserve_acl(True)
        self.config.set_preserve_xattr(True)
        # don't want links
        self.config.set_copy_links(False)
        self.config.set_copy_unsafe_links(False)
        # backup root
        self.config.set_include( [ ("/", 0) ] )

        # set UI
        self.update_profiles()

    def add_profile( self ):
        ret_val =  QInputDialog.getText(self, _('New profile'), str() )
        if not ret_val[1]:
            return

        name = ret_val[0].strip()
        if not name:
            return

        profile_id = self.config.add_profile( name )
        if profile_id is None:
            return

        self.config.set_current_profile( profile_id )
        self.update_profiles()

    def edit_profile( self ):
        ret_val =  QInputDialog.getText(self, _('Rename profile'), str() )
        if not ret_val[1]:
            return

        name = ret_val[0].strip()
        if not name:
            return

        if not self.config.set_profile_name( name ):
            return

        self.update_profiles()

    def remove_profile( self ):
        if self.question_handler( _('Are you sure you want to delete the profile "%s" ?') % self.config.get_profile_name() ):
            self.config.remove_profile()
            self.update_profiles()

    def update_automatic_snapshot_time( self, backup_mode ):
        if backup_mode == self.config.CUSTOM_HOUR:
            self.lbl_automatic_snapshots_time_custom.show()
            self.txt_automatic_snapshots_time_custom.show()
        else:
            self.lbl_automatic_snapshots_time_custom.hide()
            self.txt_automatic_snapshots_time_custom.hide()

        if backup_mode == self.config.WEEK:
            self.lbl_automatic_snapshots_weekday.show()
            self.combo_automatic_snapshots_weekday.show()
        else:
            self.lbl_automatic_snapshots_weekday.hide()
            self.combo_automatic_snapshots_weekday.hide()

        if backup_mode == self.config.MONTH:
            self.lbl_automatic_snapshots_day.show()
            self.combo_automatic_snapshots_day.show()
        else:
            self.lbl_automatic_snapshots_day.hide()
            self.combo_automatic_snapshots_day.hide()

        if backup_mode >= self.config.DAY:
            self.lbl_automatic_snapshots_time.show()
            self.combo_automatic_snapshots_time.show()
        else:
            self.lbl_automatic_snapshots_time.hide()
            self.combo_automatic_snapshots_time.hide()

        if self.config.REPEATEDLY <= backup_mode <= self.config.UDEV:
            self.lbl_automatic_snapshots_anacron_period.show()
            self.sb_automatic_snapshots_anacron_period.show()
            self.combo_automatic_snapshots_anacron_unit.show()
            self.lbl_automatic_snapshots_time.hide()
            self.combo_automatic_snapshots_time.hide()
        else:
            self.lbl_automatic_snapshots_anacron_period.hide()
            self.sb_automatic_snapshots_anacron_period.hide()
            self.combo_automatic_snapshots_anacron_unit.hide()

        if backup_mode == self.config.REPEATEDLY:
            self.lbl_automatic_snapshots_anacron.show()
        else:
            self.lbl_automatic_snapshots_anacron.hide()

        if backup_mode == self.config.UDEV:
            self.lbl_automatic_snapshots_udev.show()
        else:
            self.lbl_automatic_snapshots_udev.hide()

    def current_automatic_snapshot_changed( self, index ):
        backup_mode = self.combo_automatic_snapshots.itemData( index )
        self.update_automatic_snapshot_time( backup_mode )

    def current_profile_changed( self, index ):
        if self.disable_profile_changed:
            return

        profile_id = self.combo_profiles.currentProfileID()
        if not profile_id:
            return

        if profile_id != self.config.get_current_profile():
            self.save_profile()
            self.config.set_current_profile( profile_id )
            self.update_profile()

    def update_check_for_changes(self):
        enabled = not self.cb_full_rsync.isChecked()
        self.cb_check_for_changes.setVisible(enabled)
        self.cb_take_snapshot_regardless_of_changes.setVisible(not enabled)

    def update_profiles( self ):
        self.update_profile()
        current_profile_id = self.config.get_current_profile()

        self.disable_profile_changed = True

        self.combo_profiles.clear()

        profiles = self.config.get_profiles_sorted_by_name()
        for profile_id in profiles:
            self.combo_profiles.addProfileID(profile_id)
            if profile_id == current_profile_id:
                self.combo_profiles.setCurrentProfileID(profile_id)

        self.disable_profile_changed = False

    def update_profile( self ):
        if self.config.get_current_profile() == '1':
            self.btn_edit_profile.setEnabled( False )
            self.btn_remove_profile.setEnabled( False )
        else:
            self.btn_edit_profile.setEnabled( True )
            self.btn_remove_profile.setEnabled( True )
        self.btn_add_profile.setEnabled(self.config.is_configured('1'))

        #TAB: General
        #mode
        self.set_combo_value( self.combo_modes, self.config.get_snapshots_mode(), t = 'str' )

        #local
        self.edit_snapshots_path.setText( self.config.get_snapshots_path( mode = 'local') )

        #ssh
        self.txt_ssh_host.setText( self.config.get_ssh_host() )
        self.txt_ssh_port.setText( str(self.config.get_ssh_port()) )
        self.txt_ssh_user.setText( self.config.get_ssh_user() )
        self.txt_ssh_path.setText( self.config.get_snapshots_path_ssh() )
        self.set_combo_value( self.combo_ssh_cipher, self.config.get_ssh_cipher(), t = 'str' )
        self.txt_ssh_private_key_file.setText( self.config.get_ssh_private_key_file() )

        #local_encfs
        if self.mode == 'local_encfs':
            self.edit_snapshots_path.setText( self.config.get_local_encfs_path() )

        #password
        password_1 = self.config.get_password( mode = self.mode, pw_id = 1, only_from_keyring = True )
        password_2 = self.config.get_password( mode = self.mode, pw_id = 2, only_from_keyring = True )
        if password_1 is None:
            password_1 = ''
        if password_2 is None:
            password_2 = ''
        self.txt_password_1.setText( password_1 )
        self.txt_password_2.setText( password_2 )
        self.cb_password_save.setChecked( self.keyring_supported and self.config.get_password_save( mode = self.mode ) )
        self.cb_password_use_cache.setChecked( self.config.get_password_use_cache( mode = self.mode ) )

        host, user, profile = self.config.get_host_user_profile()
        self.txt_host.setText( host )
        self.txt_user.setText( user )
        self.txt_profile.setText( profile )

        self.set_combo_value( self.combo_automatic_snapshots, self.config.get_automatic_backup_mode() )
        self.set_combo_value( self.combo_automatic_snapshots_time, self.config.get_automatic_backup_time() )
        self.set_combo_value( self.combo_automatic_snapshots_day, self.config.get_automatic_backup_day() )
        self.set_combo_value( self.combo_automatic_snapshots_weekday, self.config.get_automatic_backup_weekday() )
        self.txt_automatic_snapshots_time_custom.setText( self.config.get_custom_backup_time() )
        self.sb_automatic_snapshots_anacron_period.setValue(self.config.get_automatic_backup_anacron_period())
        self.set_combo_value(self.combo_automatic_snapshots_anacron_unit, self.config.get_automatic_backup_anacron_unit())
        self.update_automatic_snapshot_time( self.config.get_automatic_backup_mode() )

        #TAB: Include
        self.list_include.clear()

        for include in self.config.get_include():
            self.add_include( include )

        includeSortColumn = int(self.config.get_profile_int_value('qt4.settingsdialog.include.SortColumn', 1))
        includeSortOrder  = int(self.config.get_profile_int_value('qt4.settingsdialog.include.SortOrder', Qt.AscendingOrder))
        self.list_include.sortItems(includeSortColumn, includeSortOrder)

        #TAB: Exclude
        self.list_exclude.clear()

        for exclude in self.config.get_exclude():
            self.add_exclude( exclude )
        self.cb_exclude_files_by_size.setChecked(self.config.exclude_by_size_enabled())
        self.sb_exclude_files_by_size.setValue(self.config.exclude_by_size())

        excludeSortColumn = int(self.config.get_profile_int_value('qt4.settingsdialog.exclude.SortColumn', 1))
        excludeSortOrder  = int(self.config.get_profile_int_value('qt4.settingsdialog.exclude.SortOrder', Qt.AscendingOrder))
        self.list_exclude.sortItems(excludeSortColumn, excludeSortOrder)

        #TAB: Auto-remove

        #remove old snapshots
        enabled, value, unit = self.config.get_remove_old_snapshots()
        self.cb_remove_older_then.setChecked( enabled )
        self.edit_remove_older_then.setValue( value )
        self.set_combo_value( self.combo_remove_older_then, unit )

        #min free space
        enabled, value, unit = self.config.get_min_free_space()
        self.cb_min_free_space.setChecked( enabled )
        self.edit_min_free_space.setValue( value )
        self.set_combo_value( self.combo_min_free_space, unit )

        #min free inodes
        self.cb_min_free_inodes.setChecked(self.config.min_free_inodes_enabled())
        self.edit_min_free_inodes.setValue(self.config.min_free_inodes())

        #smart remove
        smart_remove, keep_all, keep_one_per_day, keep_one_per_week, keep_one_per_month = self.config.get_smart_remove()
        self.cb_smart_remove.setChecked( smart_remove )
        self.edit_keep_all.setValue( keep_all )
        self.edit_keep_one_per_day.setValue( keep_one_per_day )
        self.edit_keep_one_per_week.setValue( keep_one_per_week )
        self.edit_keep_one_per_month.setValue( keep_one_per_month )
        self.cb_run_smart_remove_remote_in_background.setChecked(self.config.get_smart_remove_run_remote_in_background())

        #don't remove named snapshots
        self.cb_dont_remove_named_snapshots.setChecked( self.config.get_dont_remove_named_snapshots() )

        #TAB: Options
        self.cb_notify_enabled.setChecked( self.config.is_notify_enabled() )
        self.cb_no_on_battery.setChecked( self.config.is_no_on_battery_enabled() )
        self.cb_use_global_flock.setChecked(self.config.use_global_flock())
        self.cb_backup_on_restore.setChecked( self.config.is_backup_on_restore_enabled() )
        self.cb_continue_on_errors.setChecked( self.config.continue_on_errors() )
        self.cb_use_checksum.setChecked( self.config.use_checksum() )
        self.cb_full_rsync.setChecked( self.config.full_rsync() )
        self.update_check_for_changes()
        self.cb_take_snapshot_regardless_of_changes.setChecked(self.config.take_snapshot_regardless_of_changes())
        self.cb_check_for_changes.setChecked( self.config.check_for_changes() )
        self.set_combo_value( self.combo_log_level, self.config.log_level() )

        #TAB: Expert Options
        self.cb_run_nice_from_cron.setChecked( self.config.is_run_nice_from_cron_enabled() )
        self.cb_run_ionice_from_cron.setChecked( self.config.is_run_ionice_from_cron_enabled() )
        self.cb_run_ionice_from_user.setChecked( self.config.is_run_ionice_from_user_enabled() )
        self.cb_run_nice_on_remote.setChecked(self.config.is_run_nice_on_remote_enabled())
        self.cb_run_ionice_on_remote.setChecked(self.config.is_run_ionice_on_remote_enabled())
        self.cb_run_nocache_on_local.setChecked(self.config.is_run_nocache_on_local_enabled() and self.nocacheAvailable)
        self.cb_run_nocache_on_remote.setChecked(self.config.is_run_nocache_on_remote_enabled())
        self.cb_redirect_stdout.setChecked(self.config.redirect_stdout_in_cron())
        self.cb_redirect_stderr.setChecked(self.config.redirect_stderr_in_cron())
        self.cb_bwlimit.setChecked( self.config.bwlimit_enabled() )
        self.sb_bwlimit.setValue( self.config.bwlimit() )
        self.cb_preserve_acl.setChecked( self.config.preserve_acl() )
        self.cb_preserve_xattr.setChecked( self.config.preserve_xattr() )
        self.cb_copy_unsafe_links.setChecked( self.config.copy_unsafe_links() )
        self.cb_copy_links.setChecked( self.config.copy_links() )
        self.cb_rsync_options.setChecked(self.config.rsync_options_enabled() )
        self.txt_rsync_options.setText(self.config.rsync_options() )
        self.cb_ssh_prefix.setChecked(self.config.ssh_prefix_enabled() )
        self.txt_ssh_prefix.setText(self.config.ssh_prefix() )

        #update
        self.update_remove_older_than()
        self.update_min_free_space()

    def save_profile( self ):
        if self.combo_automatic_snapshots.itemData( self.combo_automatic_snapshots.currentIndex() ) == self.config.CUSTOM_HOUR:
            if not tools.check_cron_pattern(self.txt_automatic_snapshots_time_custom.text() ):
                self.error_handler( _('Custom Hours can only be a comma seperate list of hours (e.g. 8,12,18,23) or */3 for periodic backups every 3 hours') )
                return False

        #mode
        mode = str( self.combo_modes.itemData( self.combo_modes.currentIndex() ) )
        self.config.set_snapshots_mode( mode )
        mount_kwargs = {}

        #password
        password_1 = self.txt_password_1.text()
        password_2 = self.txt_password_2.text()


        if mode in ('ssh', 'local_encfs'):
            mount_kwargs = {'password': password_1
                            }

        if mode == 'ssh_encfs':
            mount_kwargs = {'ssh_password': password_1,
                            'encfs_password': password_2,
                            }

        #snapshots path
        self.config.set_host_user_profile(
                self.txt_host.text(),
                self.txt_user.text(),
                self.txt_profile.text() )

        #save ssh
        self.config.set_ssh_host(self.txt_ssh_host.text())
        self.config.set_ssh_port(self.txt_ssh_port.text())
        self.config.set_ssh_user(self.txt_ssh_user.text())
        self.config.set_snapshots_path_ssh(self.txt_ssh_path.text())
        self.config.set_ssh_cipher(self.combo_ssh_cipher.itemData( self.combo_ssh_cipher.currentIndex() ))
        self.config.set_ssh_private_key_file(self.txt_ssh_private_key_file.text())

        #save local_encfs
        self.config.set_local_encfs_path(self.edit_snapshots_path.text())

        #include list
        self.config.set_profile_int_value('qt4.settingsdialog.include.SortColumn',
                                          self.list_include_header.sortIndicatorSection())
        self.config.set_profile_int_value('qt4.settingsdialog.include.SortOrder',
                                          self.list_include_header.sortIndicatorOrder())
        self.list_include.sortItems(1, Qt.AscendingOrder)

        include_list = []
        for index in range( self.list_include.topLevelItemCount() ):
            item = self.list_include.topLevelItem( index )
            include_list.append( ( item.text(0), item.data( 0, Qt.UserRole ) ) )

        self.config.set_include( include_list )

        #exclude patterns
        self.config.set_profile_int_value('qt4.settingsdialog.exclude.SortColumn',
                                          self.list_exclude_header.sortIndicatorSection())
        self.config.set_profile_int_value('qt4.settingsdialog.exclude.SortOrder',
                                          self.list_exclude_header.sortIndicatorOrder())
        self.list_exclude.sortItems(1, Qt.AscendingOrder)

        exclude_list = []
        for index in range( self.list_exclude.topLevelItemCount() ):
            item = self.list_exclude.topLevelItem( index )
            exclude_list.append( item.text(0) )

        self.config.set_exclude( exclude_list )
        self.config.set_exclude_by_size_enabled(self.cb_exclude_files_by_size.isChecked())
        self.config.set_exclude_by_size(self.sb_exclude_files_by_size.value())

        #schedule
        self.config.set_automatic_backup_mode( self.combo_automatic_snapshots.itemData( self.combo_automatic_snapshots.currentIndex() ) )
        self.config.set_automatic_backup_time( self.combo_automatic_snapshots_time.itemData( self.combo_automatic_snapshots_time.currentIndex() ) )
        self.config.set_automatic_backup_weekday( self.combo_automatic_snapshots_weekday.itemData( self.combo_automatic_snapshots_weekday.currentIndex() ) )
        self.config.set_automatic_backup_day( self.combo_automatic_snapshots_day.itemData( self.combo_automatic_snapshots_day.currentIndex() ) )
        self.config.set_custom_backup_time( self.txt_automatic_snapshots_time_custom.text() )
        self.config.set_automatic_backup_anacron_period(self.sb_automatic_snapshots_anacron_period.value())
        self.config.set_automatic_backup_anacron_unit(self.combo_automatic_snapshots_anacron_unit.itemData(self.combo_automatic_snapshots_anacron_unit.currentIndex() ))

        #auto-remove
        self.config.set_remove_old_snapshots(
                        self.cb_remove_older_then.isChecked(),
                        self.edit_remove_older_then.value(),
                        self.combo_remove_older_then.itemData( self.combo_remove_older_then.currentIndex() ) )
        self.config.set_min_free_space(
                        self.cb_min_free_space.isChecked(),
                        self.edit_min_free_space.value(),
                        self.combo_min_free_space.itemData( self.combo_min_free_space.currentIndex() ) )
        self.config.set_min_free_inodes(
                        self.cb_min_free_inodes.isChecked(),
                        self.edit_min_free_inodes.value() )
        self.config.set_dont_remove_named_snapshots( self.cb_dont_remove_named_snapshots.isChecked() )
        self.config.set_smart_remove(
                        self.cb_smart_remove.isChecked(),
                        self.edit_keep_all.value(),
                        self.edit_keep_one_per_day.value(),
                        self.edit_keep_one_per_week.value(),
                        self.edit_keep_one_per_month.value() )
        self.config.set_smart_remove_run_remote_in_background(self.cb_run_smart_remove_remote_in_background.isChecked())

        #options
        self.config.set_notify_enabled( self.cb_notify_enabled.isChecked() )
        self.config.set_no_on_battery_enabled( self.cb_no_on_battery.isChecked() )
        self.config.set_use_global_flock(self.cb_use_global_flock.isChecked())
        self.config.set_backup_on_restore( self.cb_backup_on_restore.isChecked() )
        self.config.set_continue_on_errors( self.cb_continue_on_errors.isChecked() )
        self.config.set_use_checksum( self.cb_use_checksum.isChecked() )
        self.config.set_full_rsync( self.cb_full_rsync.isChecked() )
        self.config.set_take_snapshot_regardless_of_changes(self.cb_take_snapshot_regardless_of_changes.isChecked())
        self.config.set_check_for_changes( self.cb_check_for_changes.isChecked() )
        self.config.set_log_level( self.combo_log_level.itemData( self.combo_log_level.currentIndex() ) )

        #expert options
        self.config.set_run_nice_from_cron_enabled( self.cb_run_nice_from_cron.isChecked() )
        self.config.set_run_ionice_from_cron_enabled( self.cb_run_ionice_from_cron.isChecked() )
        self.config.set_run_ionice_from_user_enabled( self.cb_run_ionice_from_user.isChecked() )
        self.config.set_run_nice_on_remote_enabled(self.cb_run_nice_on_remote.isChecked())
        self.config.set_run_ionice_on_remote_enabled(self.cb_run_ionice_on_remote.isChecked())
        self.config.set_run_nocache_on_local_enabled(self.cb_run_nocache_on_local.isChecked())
        self.config.set_run_nocache_on_remote_enabled(self.cb_run_nocache_on_remote.isChecked())
        self.config.set_redirect_stdout_in_cron(self.cb_redirect_stdout.isChecked())
        self.config.set_redirect_stderr_in_cron(self.cb_redirect_stderr.isChecked())
        self.config.set_bwlimit_enabled( self.cb_bwlimit.isChecked() )
        self.config.set_bwlimit( self.sb_bwlimit.value() )
        self.config.set_preserve_acl( self.cb_preserve_acl.isChecked() )
        self.config.set_preserve_xattr( self.cb_preserve_xattr.isChecked() )
        self.config.set_copy_unsafe_links( self.cb_copy_unsafe_links.isChecked() )
        self.config.set_copy_links( self.cb_copy_links.isChecked() )
        self.config.set_rsync_options_enabled(self.cb_rsync_options.isChecked() )
        self.config.set_rsync_options(self.txt_rsync_options.text() )
        self.config.set_ssh_prefix_enabled(self.cb_ssh_prefix.isChecked() )
        self.config.set_ssh_prefix(self.txt_ssh_prefix.text() )

        # TODO - consider a single API method to bridge the UI layer (settings dialog) and backend layer (config)
        # when setting snapshots path rather than having to call the mount module from the UI layer
        # 
        # currently, setting snapshots path requires the path to be mounted. it seems that it might be nice,
        # since the config object is more than a data structure, but has side-effect logic as well, to have the
        # config.set_snapshots_path() method take care of everything it needs to perform its job
        # (mounting and unmounting the fuse filesystem if necessary).
        # https://en.wikipedia.org/wiki/Single_responsibility_principle

        if not self.config.SNAPSHOT_MODES[mode][0] is None:
            #pre_mount_check
            mnt = mount.Mount(cfg = self.config, tmp_mount = True, parent = self, read_only = False)
            try:
                mnt.pre_mount_check(mode = mode, first_run = True, **mount_kwargs)
            except MountException as ex:
                self.error_handler(str(ex))
                return False

            #okay, lets try to mount
            try:
                hash_id = mnt.mount(mode = mode, check = False, **mount_kwargs)
            except MountException as ex:
                self.error_handler(str(ex))
                return False

        #save password
        self.config.set_password_save(self.cb_password_save.isChecked(), mode = mode)
        self.config.set_password_use_cache(self.cb_password_use_cache.isChecked(), mode = mode)
        self.config.set_password(password_1, mode = mode)
        self.config.set_password(password_2, mode = mode, pw_id = 2)

        #save snaphots_path
        if self.config.SNAPSHOT_MODES[mode][0] is None:
            snapshots_path = self.edit_snapshots_path.text()
        else:
            snapshots_path = self.config.get_snapshots_path(mode = mode, tmp_mount = True)

        ret = self.config.set_snapshots_path( snapshots_path, mode = mode )
        if not ret:
            return ret

        #umount
        if not self.config.SNAPSHOT_MODES[mode][0] is None:
            try:
                mnt.umount(hash_id = hash_id)
            except MountException as ex:
                self.error_handler(str(ex))
                return False
        return True

    def error_handler( self, message ):
        messagebox.critical( self, message )

    def question_handler( self, message ):
        return QMessageBox.Yes == messagebox.warningYesNo( self, message )

    def exec_( self ):
        self.config.set_question_handler( self.question_handler )
        self.config.set_error_handler( self.error_handler )
        ret_val = super(SettingsDialog, self).exec_()
        self.config.clear_handlers()

        if ret_val != QDialog.Accepted:
            self.config.dict = self.config_copy_dict

        self.config.set_current_profile( self.current_profile_org )

        return ret_val

    def update_remove_older_than( self ):
        enabled = self.cb_remove_older_then.isChecked()
        self.edit_remove_older_then.setEnabled( enabled )
        self.combo_remove_older_then.setEnabled( enabled )

    def update_min_free_space( self ):
        enabled = self.cb_min_free_space.isChecked()
        self.edit_min_free_space.setEnabled( enabled )
        self.combo_min_free_space.setEnabled( enabled )


    def add_include( self, data ):
        item = QTreeWidgetItem()

        if data[1] == 0:
            item.setIcon(0, self.icon.FOLDER)
        else:
            item.setIcon(0, self.icon.FILE)

        item.setText( 0, data[0] )
        item.setData( 0, Qt.UserRole, data[1] )
        self.list_include_count += 1
        item.setText(1, str(self.list_include_count).zfill(6))
        item.setData(1, Qt.UserRole, self.list_include_count )
        self.list_include.addTopLevelItem( item )

        if self.list_include.currentItem() is None:
            self.list_include.setCurrentItem( item )

        return item

    def add_exclude( self, pattern ):
        item = QTreeWidgetItem()
        item.setText(0, pattern)
        item.setData(0, Qt.UserRole, pattern )
        self.list_exclude_count += 1
        item.setText(1, str(self.list_exclude_count).zfill(6))
        item.setData(1, Qt.UserRole, self.list_exclude_count )
        self.formatExcludeItem(item)
        self.list_exclude.addTopLevelItem(item)

        if self.list_exclude.currentItem() is None:
            self.list_exclude.setCurrentItem( item )

        return item

    def fill_combo( self, combo, d ):
        keys = list(d.keys())
        keys.sort()

        for key in keys:
            combo.addItem( QIcon(), d[ key ], key )

    def set_combo_value( self, combo, value, t = 'int' ):
        for i in range( combo.count() ):
            if t == 'int' and value == combo.itemData( i ):
                combo.setCurrentIndex( i )
                break
            if t == 'str' and value == combo.itemData( i ):
                combo.setCurrentIndex( i )
                break

    def validate( self ):
        if not self.save_profile():
            return False

        if not self.config.check_config():
            return False

        if not self.config.setup_cron():
            return False

        return self.config.save()


    def on_btn_exclude_remove_clicked ( self ):
        for item in self.list_exclude.selectedItems():
            index = self.list_exclude.indexOfTopLevelItem( item )
            if index < 0:
                continue

            self.list_exclude.takeTopLevelItem( index )

        if self.list_exclude.topLevelItemCount() > 0:
            self.list_exclude.setCurrentItem( self.list_exclude.topLevelItem(0) )

    def add_exclude_( self, pattern ):
        if not pattern:
            return

        for index in range( self.list_exclude.topLevelItemCount() ):
            item = self.list_exclude.topLevelItem( index )
            if pattern == item.text(0):
                return

        self.add_exclude( pattern )

    def on_btn_exclude_add_clicked( self ):
        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.setWindowTitle(_('Exclude pattern'))
        dlg.setLabelText('')
        dlg.resize(400, 0)
        if not dlg.exec():
            return
        pattern = dlg.textValue().strip()

        if not pattern:
            return

        self.add_exclude_( pattern )

    def on_btn_exclude_file_clicked( self ):
        for path in qt4tools.getOpenFileNames(self, _('Exclude file')):
            self.add_exclude_( path )

    def on_btn_exclude_folder_clicked( self ):
        for path in qt4tools.getExistingDirectories(self, _('Exclude folder')) :
            self.add_exclude_( path )

    def on_btn_exclude_default_clicked(self):
        for path in self.config.DEFAULT_EXCLUDE:
            self.add_exclude_(path)

    def on_btn_include_remove_clicked ( self ):
        for item in self.list_include.selectedItems():
            index = self.list_include.indexOfTopLevelItem( item )
            if index < 0:
                continue

            self.list_include.takeTopLevelItem( index )

        if self.list_include.topLevelItemCount() > 0:
            self.list_include.setCurrentItem( self.list_include.topLevelItem(0) )

    def on_btn_include_file_add_clicked( self ):
        for path in qt4tools.getOpenFileNames(self, _('Include file')):
            if not path:
                continue

            if os.path.islink(path) \
              and not (self.cb_copy_unsafe_links.isChecked() \
              or self.cb_copy_links.isChecked()):
                if self.question_handler( \
                  _('"%s" is a symlink. The linked target will not be backed up until you include it, too.\nWould you like to include the symlinks target instead?') % path ):
                    path = os.path.realpath(path)

            path = self.config.prepare_path( path )

            for index in range( self.list_include.topLevelItemCount() ):
                if path == self.list_include.topLevelItem( index ).text( 0 ):
                    continue

            self.add_include( ( path, 1 ) )

    def on_btn_include_add_clicked( self ):
        for path in qt4tools.getExistingDirectories(self, _('Include folder')):
            if not path:
                continue

            if os.path.islink(path) \
              and not (self.cb_copy_unsafe_links.isChecked() \
              or self.cb_copy_links.isChecked()):
                if self.question_handler( \
                  _('"%s" is a symlink. The linked target will not be backed up until you include it, too.\nWould you like to include the symlinks target instead?') % path ):
                    path = os.path.realpath(path)

            path = self.config.prepare_path( path )

            for index in range( self.list_include.topLevelItemCount() ):
                if path == self.list_include.topLevelItem( index ).text( 0 ):
                    continue

            self.add_include( ( path, 0 ) )

    def on_btn_snapshots_path_clicked( self ):
        old_path = self.edit_snapshots_path.text()

        path = str(qt4tools.getExistingDirectory(self,
                                                 _('Where to save snapshots'),
                                                 self.edit_snapshots_path.text() ) )
        if path:
            if old_path and old_path != path:
                if not self.question_handler( _('Are you sure you want to change snapshots folder ?') ):
                    return
            self.edit_snapshots_path.setText( self.config.prepare_path( path ) )

    def on_btn_ssh_private_key_file_clicked( self ):
        old_file = self.txt_ssh_private_key_file.text()

        if old_file:
            start_dir = self.txt_ssh_private_key_file.text()
        else:
            start_dir = self.config.get_ssh_private_key_folder()
        f = qt4tools.getOpenFileName(self, _('SSH private key'), start_dir)
        if f:
            self.txt_ssh_private_key_file.setText(f)

    def on_combo_modes_changed(self, *params):
        if not params:
            index = self.combo_modes.currentIndex()
        else:
            index = params[0]
        active_mode = str( self.combo_modes.itemData( index ) )
        if active_mode != self.mode:
            for mode in list(self.config.SNAPSHOT_MODES.keys()):
                getattr(self, 'mode_%s' % mode).hide()
            for mode in list(self.config.SNAPSHOT_MODES.keys()):
                if active_mode == mode:
                    getattr(self, 'mode_%s' % mode).show()
            self.mode = active_mode

        if self.config.mode_need_password(active_mode):
            self.lbl_password_1.setText( self.config.SNAPSHOT_MODES[active_mode][2] + ':' )
            self.frame_password_1.show()
            if self.config.mode_need_password(active_mode, 2):
                self.lbl_password_2.setText( self.config.SNAPSHOT_MODES[active_mode][3] + ':' )
                self.lbl_password_2.show()
                self.txt_password_2.show()
                qt4tools.equal_indent(self.lbl_password_1, self.lbl_password_2)
            else:
                self.lbl_password_2.hide()
                self.txt_password_2.hide()
                qt4tools.equal_indent(self.lbl_password_1)
        else:
            self.frame_password_1.hide()

        if active_mode == 'ssh_encfs':
            self.lbl_ssh_encfs_exclude_warning.show()
        else:
            self.lbl_ssh_encfs_exclude_warning.hide()
        self.updateExcludeItems()

        enabled = active_mode in ('ssh', 'ssh_encfs')
        self.cb_run_nice_on_remote.setEnabled(enabled)
        self.cb_run_ionice_on_remote.setEnabled(enabled)
        self.cb_bwlimit.setEnabled(enabled)
        self.sb_bwlimit.setEnabled(enabled and self.cb_bwlimit.isChecked())
        self.cb_run_nocache_on_remote.setEnabled(enabled)
        self.cb_run_smart_remove_remote_in_background.setHidden(not enabled)
        self.cb_ssh_prefix.setHidden(not enabled)
        self.txt_ssh_prefix.setHidden(not enabled)

        self.encfsWarning.setHidden(active_mode not in ('local_encfs', 'ssh_encfs'))

    def on_full_path_changed(self, dummy):
        if self.mode in ('ssh', 'ssh_encfs'):
            path = self.txt_ssh_path.text()
        else:
            path = self.edit_snapshots_path.text()
        self.lbl_full_path.setText(
            _('Full snapshot path: ') +
            os.path.join(
                path,
                'backintime',
                self.txt_host.text(),
                self.txt_user.text(),
                self.txt_profile.text()
                ))

    def updateExcludeItems(self):
        for index in range(self.list_exclude.topLevelItemCount()):
            item = self.list_exclude.topLevelItem(index)
            self.formatExcludeItem(item)

    def formatExcludeItem(self, item):
        if self.mode == 'ssh_encfs' and tools.patternHasNotEncryptableWildcard(item.text(0)):
            item.setIcon(0, self.icon.INVALID_EXCLUDE)
            item.setBackground(0, QBrush(Qt.lightGray))
        elif item.text(0) in self.config.DEFAULT_EXCLUDE:
            item.setIcon(0, self.icon.DEFAULT_EXCLUDE)
            item.setBackground(0, QBrush())
        else:
            item.setIcon(0, self.icon.EXCLUDE)
            item.setBackground(0, QBrush())

    def customSortOrder(self, header, loop, newColumn, newOrder):
        if newColumn == 0 and newOrder == Qt.AscendingOrder:
            if loop:
                newColumn, newOrder = 1, Qt.AscendingOrder
                header.setSortIndicator(newColumn, newOrder)
                loop = False
            else:
                loop = True
        header.model().sort(newColumn, newOrder)
        return loop

    def includeCustomSortOrder(self, *args):
        self.list_include_sort_loop = self.customSortOrder(self.list_include_header,
                                                           self.list_include_sort_loop,
                                                           *args)

    def excludeCustomSortOrder(self, *args):
        self.list_exclude_sort_loop = self.customSortOrder(self.list_exclude_header,
                                                           self.list_exclude_sort_loop,
                                                           *args)

    def printDefault(self, value):
        if value:
            value_ = _('enabled')
        else:
            value_ = _('disabled')
        return ' (%s: %s)' %(_('default'), value_)

    def restoreConfig(self, *args):
        RestoreConfigDialog(self).exec_()
        self.update_profiles()

    def accept( self ):
        if self.validate():
            super(SettingsDialog, self).accept()

class RestoreConfigDialog(QDialog):
    """
    Show a dialog that will help to restore BITs configuration.
    User can select a config from previous snapshots.
    """
    def __init__(self, parent):
        super(RestoreConfigDialog, self).__init__(parent)

        self.parent = parent
        self.config = parent.config
        self.snapshots = parent.snapshots

        import icon
        self.icon = icon
        self.setWindowIcon(icon.SETTINGS_DIALOG)
        self.setWindowTitle(_( 'Restore Settings' ))

        layout = QVBoxLayout(self)
        #show a hint on how the snapshot path will look like.
        samplePath = os.path.join( 'backintime',
                                    self.config.get_host(),
                                    self.config.get_user(), '1',
                                    snapshots.SID(datetime.datetime.now()).sid
                                    )

        #inform user to join group fuse if he hasn't already.
        #If there is no group fuse than it is most likly not nessesary.
        addFuse = ''
        try:
            user = self.config.get_user()
            fuse_grp_members = grp.getgrnam('fuse')[3]
            if not user in fuse_grp_members:
                addFuse = _(' and add your user to group \'fuse\'')
        except KeyError:
            pass

        label = QLabel(_('Please navigate to the snapshot from which you want '
                         'to restore %(appName)s\'s configuration. The path '
                         'may look like: \n%(samplePath)s\n\n'
                         'If your snapshots are on a remote drive or if they are '
                         'encrypted you need to manually mount them first. '
                         'If you use Mode SSH you also may need to set up public key '
                         'login to the remote host%(addFuse)s.\n'
                         'Take a look at \'man backintime\'.')
                         % {'appName': self.config.APP_NAME, 'samplePath': samplePath,
                         'addFuse': addFuse}, self)
        label.setWordWrap(True)
        layout.addWidget(label)

        #treeView
        self.treeView = qt4tools.MyTreeView(self)
        self.treeViewModel = QFileSystemModel(self)
        self.treeViewModel.setRootPath(QDir().rootPath())
        self.treeViewModel.setReadOnly(True)
        self.treeViewModel.setFilter(QDir.AllDirs |
                                     QDir.NoDotAndDotDot | QDir.Hidden)

        self.treeViewFilterProxy = QSortFilterProxyModel(self)
        self.treeViewFilterProxy.setDynamicSortFilter(True)
        self.treeViewFilterProxy.setSourceModel(self.treeViewModel)

        self.treeViewFilterProxy.setFilterRegExp(r'^[^\.]')

        self.treeView.setModel(self.treeViewFilterProxy)
        for col in range(self.treeView.header().count()):
            self.treeView.setColumnHidden(col, col != 0)
        self.treeView.header().hide()

        #expand users home
        self.expandAll(os.path.expanduser('~'))
        layout.addWidget(self.treeView)

        #context menu
        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.connect(self.treeView, SIGNAL('customContextMenuRequested(const QPoint&)'), self.onContextMenu)
        self.contextMenu = QMenu(self)
        self.btnShowHidden = self.contextMenu.addAction(icon.SHOW_HIDDEN, _('Show hidden files'))
        self.btnShowHidden.setCheckable(True)
        self.connect(self.btnShowHidden, SIGNAL('toggled(bool)'), self.onBtnShowHidden)

        #colors
        self.colorRed = QPalette()
        self.colorRed.setColor(QPalette.WindowText, QColor(205, 0, 0))
        self.colorGreen = QPalette()
        self.colorGreen.setColor(QPalette.WindowText, QColor(0, 160, 0))

        #wait indicator which will show that the scan for snapshots is still running
        self.wait = QProgressBar(self)
        self.wait.setMinimum(0)
        self.wait.setMaximum(0)
        self.wait.setMaximumHeight(7)
        layout.addWidget(self.wait)

        #show where a snapshot with config was found
        self.lblFound = QLabel(_('No config found'), self)
        self.lblFound.setWordWrap(True)
        self.lblFound.setPalette(self.colorRed)
        layout.addWidget(self.lblFound)

        #show profiles inside the config
        self.widgetProfiles = QWidget(self)
        self.widgetProfiles.setContentsMargins(0, 0, 0, 0)
        self.widgetProfiles.hide()
        self.gridProfiles = QGridLayout()
        self.gridProfiles.setContentsMargins(0, 0, 0, 0)
        self.gridProfiles.setHorizontalSpacing(20)
        self.widgetProfiles.setLayout(self.gridProfiles)
        layout.addWidget(self.widgetProfiles)

        self.restoreConfig = None

        self.scan = ScanFileSystem(self)

        self.treeView.myCurrentIndexChanged.connect(self.indexChanged)
        self.connect(self.scan, SIGNAL('foundConfig'), self.scanFound)
        self.connect(self.scan, SIGNAL('finished()'), self.scanFinished)

        button_box = QDialogButtonBox(self)
        self.restoreButton = button_box.addButton(_('Restore'), QDialogButtonBox.AcceptRole)
        self.restoreButton.setEnabled(False)
        button_box.addButton(QDialogButtonBox.Cancel)
        QObject.connect(button_box, SIGNAL('accepted()'), self.accept)
        QObject.connect(button_box, SIGNAL('rejected()'), self.reject)
        layout.addWidget(button_box)

        self.scan.start()

        self.resize(600, 700)

    def pathFromIndex(self, index):
        """
        return a path string for a given treeView index
        """
        sourceIndex = self.treeViewFilterProxy.mapToSource(index)
        return str(self.treeViewModel.filePath(sourceIndex))

    def indexFromPath(self, path):
        """
        return the index for path which can be used in treeView
        """
        indexSource = self.treeViewModel.index(path)
        return self.treeViewFilterProxy.mapFromSource(indexSource)

    def indexChanged(self, current, previous):
        """
        called everytime a new item is choosen in treeView.
        If there was a config found inside the selected folder, show
        available informations about the config.
        """
        cfg = self.searchConfig(self.pathFromIndex(current))
        if cfg:
            self.expandAll(os.path.dirname(os.path.dirname(cfg._LOCAL_CONFIG_PATH)))
            self.lblFound.setText(cfg._LOCAL_CONFIG_PATH)
            self.lblFound.setPalette(self.colorGreen)
            self.showProfile(cfg)
            self.restoreConfig = cfg
        else:
            self.lblFound.setText(_('No config found'))
            self.lblFound.setPalette(self.colorRed)
            self.widgetProfiles.hide()
            self.restoreConfig = None
        self.restoreButton.setEnabled(bool(cfg))

    def searchConfig(self, path):
        """
        try to find config in couple possible subfolders
        """
        snapshotPath = os.path.join('backintime',
                                    self.config.get_host(),
                                    self.config.get_user())
        tryPaths = ['', '..', 'last_snapshot']
        tryPaths.extend([os.path.join(snapshotPath, str(i), 'last_snapshot') for i in range(10)])

        for p in tryPaths:
            cfgPath = os.path.join(path, p, 'config')
            if os.path.exists(cfgPath):
                try:
                    cfg = config.Config(cfgPath)
                    if cfg.is_configured():
                        return cfg
                except:
                    pass
        return

    def expandAll(self, path):
        """
        expand all folders from filesystem root to given path
        """
        paths = [path, ]
        while len(path) > 1:
            path = os.path.dirname(path)
            paths.append(path)
        paths.append('/')
        paths.reverse()
        [self.treeView.expand(self.indexFromPath(p)) for p in paths]

    def showProfile(self, cfg):
        """
        show information about the profiles inside cfg
        """
        child = self.gridProfiles.takeAt(0)
        while child:
            child.widget().deleteLater()
            child = self.gridProfiles.takeAt(0)
        for row, profileId in enumerate(cfg.get_profiles()):
            for col, txt in enumerate( (_('Profile:') + ' ' + str(profileId),
                                        cfg.get_profile_name(profileId),
                                        _('Mode:') + ' ' + cfg.SNAPSHOT_MODES[cfg.get_snapshots_mode(profileId)][1]
                                        ) ):
                self.gridProfiles.addWidget(QLabel(txt, self), row, col)
        self.gridProfiles.setColumnStretch(col, 1)
        self.widgetProfiles.show()

    def scanFound(self, path):
        """
        scan hit a config. Expand the snapshot folder.
        """
        self.expandAll(os.path.dirname(path))

    def scanFinished(self):
        """
        scan is done. Delete the wait indicator
        """
        self.wait.deleteLater()

    def onContextMenu(self, point):
        self.contextMenu.exec_(self.treeView.mapToGlobal(point))

    def onBtnShowHidden(self, checked):
        if checked:
            self.treeViewFilterProxy.setFilterRegExp(r'')
        else:
            self.treeViewFilterProxy.setFilterRegExp(r'^[^\.]')

    def accept(self):
        """
        handle over the dict from the selected config. The dict contains
        all settings from the config.
        """
        if self.restoreConfig:
            self.config.dict = self.restoreConfig.dict
        super(RestoreConfigDialog, self).accept()

    def exec_(self):
        """
        stop the scan thread if it is still running after dialog was closed.
        """
        ret = super(RestoreConfigDialog, self).exec_()
        self.scan.stop()
        return ret

class ScanFileSystem(QThread):
    CONFIG = 'config'
    BACKUP = 'backup'
    BACKINTIME = 'backintime'

    def __init__(self, parent):
        super(ScanFileSystem, self).__init__(parent)
        self.stopper = False

    def stop(self):
        """
        prepair stop and wait for finish.
        """
        self.stopper = True
        return self.wait()

    def run(self):
        """
        search in order of hopefully fastest way to find the snapshots.
        1. /home/USER 2. /media 3. /mnt and at last filesystem root.
        Already searched paths will be excluded.
        """
        searchOrder = [os.path.expanduser('~'), '/media', '/mnt', '/']
        for scan in searchOrder:
            exclude = searchOrder[:]
            exclude.remove(scan)
            for path in self.scanPath(scan, exclude):
                self.emit(SIGNAL('foundConfig'), path)

    def scanPath(self, path, excludes = ()):
        """
        walk through all folders and try to find 'config' file.
        If found make sure it is nested in backintime/FOO/BAR/1/2345/config and
        return its path.
        Exclude all paths from excludes and also all backintime/FOO/BAR/1/2345/backup
        """
        for root, dirs, files in os.walk(path, topdown = True):
            if self.stopper:
                return
            for exclude in excludes:
                exDir, exBase = os.path.split(exclude)
                if root == exDir:
                    if exBase in dirs:
                        del dirs[dirs.index(exBase)]
            if self.CONFIG in files:
                rootdirs = root.split(os.sep)
                if len(rootdirs) > 4 and rootdirs[-5].startswith(self.BACKINTIME):
                    if self.BACKUP in dirs:
                        del dirs[dirs.index(self.BACKUP)]
                    yield root

def debug_trace():
    """
    Set a tracepoint in the Python debugger that works with Qt
    """
    from pdb import set_trace
    pyqtRemoveInputHook()
    set_trace()
