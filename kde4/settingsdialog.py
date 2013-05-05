#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
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
import os.path
import sys
import datetime
import gettext
import copy
import subprocess
import keyring

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *

import config
import tools
import kde4tools
import mount
import password


_=gettext.gettext


#class PopupAutomaticBackupAction( KAction ):
#	def __init__( self, list, id, label ):
#		KAction.__init__( self, label, list )
#		self.list = list
#		self.id = id
#		self.label = label
#	
#		QObject.connect( self, SIGNAL('triggered()'), self.on_selected )
#
#	def on_selected( self ):
#		item = self.list.currentItem()
#		if not item is None:
#			item.setText( 1, QString.fromUtf8( self.label ) )
#			item.setData( 0, Qt.UserRole, QVariant( self.id ) )


class SettingsDialog( KDialog ):
    def __init__( self, parent ):
        KDialog.__init__( self, parent )

        self.config = parent.config
        self.snapshots = parent.snapshots
        self.config_copy_dict = copy.copy( self.config.dict )
        self.current_profile_org = self.config.get_current_profile()

        self.setWindowIcon( KIcon( 'configure' ) )
        self.setCaption( QString.fromUtf8( _( 'Settings' ) ) )

        self.main_widget = QWidget( self )
        self.main_layout = QVBoxLayout( self.main_widget )
        self.setMainWidget( self.main_widget )

        #profiles
        layout = QHBoxLayout()
        self.main_layout.addLayout( layout )

        layout.addWidget( QLabel( QString.fromUtf8( _('Profile:') ), self ) )

        self.first_update_all = True
        self.disable_profile_changed = True
        self.combo_profiles = KComboBox( self )
        layout.addWidget( self.combo_profiles, 1 )
        QObject.connect( self.combo_profiles, SIGNAL('currentIndexChanged(int)'), self.current_profile_changed )
        self.disable_profile_changed = False

        self.btn_edit_profile = KPushButton( KIcon( 'edit-rename' ), QString.fromUtf8( _('Edit') ), self )
        QObject.connect( self.btn_edit_profile, SIGNAL('clicked()'), self.edit_profile )
        layout.addWidget( self.btn_edit_profile )

        self.btn_add_profile = KPushButton( KStandardGuiItem.add(), self )
        QObject.connect( self.btn_add_profile, SIGNAL('clicked()'), self.add_profile )
        layout.addWidget( self.btn_add_profile )

        self.btn_remove_profile = KPushButton( KStandardGuiItem.remove(), self )
        QObject.connect( self.btn_remove_profile, SIGNAL('clicked()'), self.remove_profile )
        layout.addWidget( self.btn_remove_profile )

        #TABs
        self.tabs_widget = KTabWidget( self )
        self.main_layout.addWidget( self.tabs_widget )

        #TAB: General
        tab_widget = QWidget( self )
        self.tabs_widget.addTab( tab_widget, QString.fromUtf8( _( 'General' ) ) )
        layout = QVBoxLayout( tab_widget )
        
        #select mode
        self.mode = None
        vlayout = QVBoxLayout()
        layout.addLayout( vlayout )
        
        self.lbl_modes = QLabel( QString.fromUtf8( _( 'Mode:' ) ), self )
        vlayout.addWidget( self.lbl_modes )
        
        self.combo_modes = KComboBox( self )
        vlayout.addWidget( self.combo_modes )
        store_modes = {}
        for key in self.config.SNAPSHOT_MODES.keys():
            store_modes[key] = self.config.SNAPSHOT_MODES[key][1]
        self.fill_combo( self.combo_modes, store_modes )
        
        #Where to save snapshots
        group_box = QGroupBox( self )
        self.mode_local = group_box
        group_box.setTitle( QString.fromUtf8( _( 'Where to save snapshots' ) ) )
        layout.addWidget( group_box )

        vlayout = QVBoxLayout( group_box )

        hlayout = QHBoxLayout()
        vlayout.addLayout( hlayout )

        self.edit_snapshots_path = KLineEdit( self )
        self.edit_snapshots_path.setReadOnly( True )
        hlayout.addWidget( self.edit_snapshots_path )

        self.btn_snapshots_path = KPushButton( KIcon( 'folder' ), '', self )
        hlayout.addWidget( self.btn_snapshots_path )
        QObject.connect( self.btn_snapshots_path, SIGNAL('clicked()'), self.on_btn_snapshots_path_clicked )
        
        #SSH
        group_box = QGroupBox( self )
        self.mode_ssh = group_box
        group_box.setTitle( QString.fromUtf8( _( 'SSH Settings' ) ) )
        layout.addWidget( group_box )

        vlayout = QVBoxLayout( group_box )

        hlayout1 = QHBoxLayout()
        vlayout.addLayout( hlayout1 )
        hlayout2 = QHBoxLayout()
        vlayout.addLayout( hlayout2 )
        hlayout3 = QHBoxLayout()
        vlayout.addLayout( hlayout3 )
        
        self.lbl_ssh_host = QLabel( QString.fromUtf8( _( 'Host:' ) ), self )
        hlayout1.addWidget( self.lbl_ssh_host )
        self.txt_ssh_host = KLineEdit( self )
        hlayout1.addWidget( self.txt_ssh_host )
        
        self.lbl_ssh_port = QLabel( QString.fromUtf8( _( 'Port:' ) ), self )
        hlayout1.addWidget( self.lbl_ssh_port )
        self.txt_ssh_port = KLineEdit( self )
        hlayout1.addWidget( self.txt_ssh_port )
        
        self.lbl_ssh_user = QLabel( QString.fromUtf8( _( 'User:' ) ), self )
        hlayout1.addWidget( self.lbl_ssh_user )
        self.txt_ssh_user = KLineEdit( self )
        hlayout1.addWidget( self.txt_ssh_user )
        
        self.lbl_ssh_path = QLabel( QString.fromUtf8( _( 'Path:' ) ), self )
        hlayout2.addWidget( self.lbl_ssh_path )
        self.txt_ssh_path = KLineEdit( self )
        hlayout2.addWidget( self.txt_ssh_path )
        
        self.lbl_ssh_cipher = QLabel( QString.fromUtf8( _( 'Cipher:' ) ), self )
        hlayout3.addWidget( self.lbl_ssh_cipher )
        self.combo_ssh_cipher = KComboBox( self )
        hlayout3.addWidget( self.combo_ssh_cipher )
        self.fill_combo( self.combo_ssh_cipher, self.config.SSH_CIPHERS )
        
        self.lbl_ssh_private_key_file = QLabel( QString.fromUtf8( _( 'Private Key:' ) ), self )
        hlayout3.addWidget( self.lbl_ssh_private_key_file )
        self.txt_ssh_private_key_file = KLineEdit( self )
        self.txt_ssh_private_key_file.setReadOnly( True )
        hlayout3.addWidget( self.txt_ssh_private_key_file )
        
        self.btn_ssh_private_key_file = KPushButton( KIcon( 'folder' ), '', self )
        hlayout3.addWidget( self.btn_ssh_private_key_file )
        QObject.connect( self.btn_ssh_private_key_file, SIGNAL('clicked()'), self.on_btn_ssh_private_key_file_clicked )
        
##		#Dummy
##		group_box = QGroupBox( self )
##		self.mode_dummy = group_box
##		group_box.setTitle( QString.fromUtf8( _( 'Dummy Settings' ) ) )
##		layout.addWidget( group_box )
##
##		vlayout = QVBoxLayout( group_box )
##
##		hlayout = QHBoxLayout()
##		vlayout.addLayout( hlayout )
##		
##		self.lbl_dummy_host = QLabel( QString.fromUtf8( _( 'Host:' ) ), self )
##		hlayout.addWidget( self.lbl_dummy_host )
##		self.txt_dummy_host = KLineEdit( self )
##		hlayout.addWidget( self.txt_dummy_host )
##		
##		self.lbl_dummy_port = QLabel( QString.fromUtf8( _( 'Port:' ) ), self )
##		hlayout.addWidget( self.lbl_dummy_port )
##		self.txt_dummy_port = KLineEdit( self )
##		hlayout.addWidget( self.txt_dummy_port )
##		
##		self.lbl_dummy_user = QLabel( QString.fromUtf8( _( 'User:' ) ), self )
##		hlayout.addWidget( self.lbl_dummy_user )
##		self.txt_dummy_user = KLineEdit( self )
##		hlayout.addWidget( self.txt_dummy_user )

        #password
        group_box = QGroupBox( self )
        self.frame_password = group_box
        group_box.setTitle( QString.fromUtf8( _( 'Password' ) ) )
        layout.addWidget( group_box )

        vlayout = QVBoxLayout( group_box )

        self.txt_password = KLineEdit( self )
        self.txt_password.setPasswordMode(True)
        vlayout.addWidget( self.txt_password )

        self.cb_password_save = QCheckBox( QString.fromUtf8( _( 'Save Password to Keyring' ) ), self )
        QObject.connect( self.cb_password_save, SIGNAL('stateChanged(int)'), self.update_password_save )
        vlayout.addWidget( self.cb_password_save )

        self.cb_password_use_cache = QCheckBox( QString.fromUtf8( _( 'Cache Password for Cron (Security issue: root can read password)' ) ), self )
        vlayout.addWidget( self.cb_password_use_cache )

        #mode change
        QObject.connect( self.combo_modes, SIGNAL('currentIndexChanged(int)'), self.on_combo_modes_changed )
        self.on_combo_modes_changed()
        
        #host, user, profile id
        group_box = QGroupBox( self )
        self.frame_advanced = group_box
        group_box.setTitle( QString.fromUtf8( _( 'Advanced' ) ) )
        layout.addWidget( group_box )
        
        hlayout = QHBoxLayout( group_box )
        hlayout.addSpacing( 12 )

        vlayout2 = QVBoxLayout()
        hlayout.addLayout( vlayout2 )

        hlayout2 = QHBoxLayout()
        vlayout2.addLayout( hlayout2 )

        self.cb_auto_host_user_profile = QCheckBox( QString.fromUtf8( _( 'Auto Host / User / Profile Id' ) ), self )
        QObject.connect( self.cb_auto_host_user_profile, SIGNAL('stateChanged(int)'), self.update_host_user_profile )
        hlayout2.addWidget( self.cb_auto_host_user_profile )

        hlayout2 = QHBoxLayout()
        vlayout2.addLayout( hlayout2 )

        self.lbl_host = QLabel( QString.fromUtf8( _( 'Host:' ) ), self )
        hlayout2.addWidget( self.lbl_host )
        self.txt_host = KLineEdit( self )
        hlayout2.addWidget( self.txt_host )

        self.lbl_user = QLabel( QString.fromUtf8( _( 'User:' ) ), self )
        hlayout2.addWidget( self.lbl_user )
        self.txt_user = KLineEdit( self )
        hlayout2.addWidget( self.txt_user )

        self.lbl_profile = QLabel( QString.fromUtf8( _( 'Profile:' ) ), self )
        hlayout2.addWidget( self.lbl_profile )
        self.txt_profile = KLineEdit( self )
        hlayout2.addWidget( self.txt_profile )

        #Schedule
        group_box = QGroupBox( self )
        self.global_schedule_group_box = group_box
        group_box.setTitle( QString.fromUtf8( _( 'Schedule' ) ) )
        layout.addWidget( group_box )

        glayout = QGridLayout( group_box )
        glayout.setColumnStretch(1, 2)

        self.combo_automatic_snapshots = KComboBox( self )
        glayout.addWidget( self.combo_automatic_snapshots, 0, 0, 1, 2 )
        self.fill_combo( self.combo_automatic_snapshots, self.config.AUTOMATIC_BACKUP_MODES )

        self.lbl_automatic_snapshots_day = QLabel( QString.fromUtf8( _( 'Day:' ) ), self )
        self.lbl_automatic_snapshots_day.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_day.setAlignment( Qt.AlignRight | Qt.AlignVCenter )
        glayout.addWidget( self.lbl_automatic_snapshots_day, 1, 0 )

        self.combo_automatic_snapshots_day = KComboBox( self )
        glayout.addWidget( self.combo_automatic_snapshots_day, 1, 1 )

        for d in xrange( 1, 29 ):
            self.combo_automatic_snapshots_day.addItem( QIcon(), QString.fromUtf8( str(d) ), QVariant( d ) )

        self.lbl_automatic_snapshots_weekday = QLabel( QString.fromUtf8( _( 'Weekday:' ) ), self )
        self.lbl_automatic_snapshots_weekday.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_weekday.setAlignment( Qt.AlignRight | Qt.AlignVCenter )
        glayout.addWidget( self.lbl_automatic_snapshots_weekday, 2, 0 )

        self.combo_automatic_snapshots_weekday = KComboBox( self )
        glayout.addWidget( self.combo_automatic_snapshots_weekday, 2, 1 )

        for d in xrange( 1, 8 ):
            self.combo_automatic_snapshots_weekday.addItem( QIcon(), QString.fromUtf8( datetime.date(2011, 11, 6 + d).strftime("%A") ), QVariant( d ) )

        self.lbl_automatic_snapshots_time = QLabel( QString.fromUtf8( _( 'Hour:' ) ), self )
        self.lbl_automatic_snapshots_time.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_time.setAlignment( Qt.AlignRight | Qt.AlignVCenter )
        glayout.addWidget( self.lbl_automatic_snapshots_time, 3, 0 )

        self.combo_automatic_snapshots_time = KComboBox( self )
        glayout.addWidget( self.combo_automatic_snapshots_time, 3, 1 )

        for t in xrange( 0, 2300, 100 ):
            self.combo_automatic_snapshots_time.addItem( QIcon(), QString.fromUtf8( datetime.time( t/100, t%100 ).strftime("%H:%M") ), QVariant( t ) )

        self.lbl_automatic_snapshots_time_custom = QLabel( QString.fromUtf8( _( 'Hours:' ) ), self )
        self.lbl_automatic_snapshots_time_custom.setContentsMargins( 5, 0, 0, 0 )
        self.lbl_automatic_snapshots_time_custom.setAlignment( Qt.AlignRight | Qt.AlignVCenter )
        glayout.addWidget( self.lbl_automatic_snapshots_time_custom, 4, 0 )

        self.txt_automatic_snapshots_time_custom = KLineEdit( self )
        glayout.addWidget( self.txt_automatic_snapshots_time_custom, 4, 1 )

        QObject.connect( self.combo_automatic_snapshots, SIGNAL('currentIndexChanged(int)'), self.current_automatic_snapshot_changed )

        #
        layout.addStretch()
        
        #TAB: Include
        tab_widget = QWidget( self )
        self.tabs_widget.addTab( tab_widget, QString.fromUtf8( _( 'Include' ) ) )
        layout = QVBoxLayout( tab_widget )

        self.list_include = QTreeWidget( self )
        self.list_include.setRootIsDecorated( False )
        #self.list_include.setEditTriggers( QAbstractItemView.NoEditTriggers )
        #self.list_include.setHeaderLabels( [ QString.fromUtf8( _('Include folders') ), QString.fromUtf8( _('Automatic backup') ) ] )
        self.list_include.setHeaderLabels( [ QString.fromUtf8( _('Include files and folders') ) ] )
        self.list_include.header().setResizeMode( 0, QHeaderView.Stretch )

        #self.popup_automatic_backup = KMenu( self )
        #keys = self.config.AUTOMATIC_BACKUP_MODES.keys()
        #keys.sort()
        #for key in keys:
        #	self.popup_automatic_backup.addAction( PopupAutomaticBackupAction( self.list_include, key, QString.fromUtf8( self.config.AUTOMATIC_BACKUP_MODES[ key ] ) ) )

        #QObject.connect( self.list_include, SIGNAL('itemActivated(QTreeWidgetItem*,int)'), self.on_list_include_item_activated )
        layout.addWidget( self.list_include )

        buttons_layout = QHBoxLayout()
        layout.addLayout( buttons_layout )

        self.btn_include_file_add = KPushButton( KStandardGuiItem.add(), self )
        self.btn_include_file_add.setText( QString.fromUtf8( _( 'Add file' ) ) )
        buttons_layout.addWidget( self.btn_include_file_add )
        QObject.connect( self.btn_include_file_add, SIGNAL('clicked()'), self.on_btn_include_file_add_clicked )
        
        self.btn_include_add = KPushButton( KStandardGuiItem.add(), self )
        self.btn_include_add.setText( QString.fromUtf8( _( 'Add folder' ) ) )
        buttons_layout.addWidget( self.btn_include_add )
        QObject.connect( self.btn_include_add, SIGNAL('clicked()'), self.on_btn_include_add_clicked )
        
        self.btn_include_remove = KPushButton( KStandardGuiItem.remove(), self )
        buttons_layout.addWidget( self.btn_include_remove )
        QObject.connect( self.btn_include_remove, SIGNAL('clicked()'), self.on_btn_include_remove_clicked )

        #TAB: Exclude
        tab_widget = QWidget( self )
        self.tabs_widget.addTab( tab_widget, QString.fromUtf8( _( 'Exclude' ) ) )
        layout = QVBoxLayout( tab_widget )

        self.list_exclude = KListWidget( self )
        layout.addWidget( self.list_exclude )

        label = QLabel( QString.fromUtf8( _('Highly recommended:') ), self )
        kde4tools.set_font_bold( label )
        layout.addWidget( label )
        layout.addWidget( QLabel( QString.fromUtf8( ', '.join(self.config.DEFAULT_EXCLUDE) ), self ) )
        
        buttons_layout = QHBoxLayout()
        layout.addLayout( buttons_layout )

        self.btn_exclude_add = KPushButton( KStandardGuiItem.add(), self )
        buttons_layout.addWidget( self.btn_exclude_add )
        QObject.connect( self.btn_exclude_add, SIGNAL('clicked()'), self.on_btn_exclude_add_clicked )
        
        self.btn_exclude_file = KPushButton( KStandardGuiItem.add(), self )
        self.btn_exclude_file.setText( QString.fromUtf8( _( 'Add file' ) ) )
        buttons_layout.addWidget( self.btn_exclude_file )
        QObject.connect( self.btn_exclude_file, SIGNAL('clicked()'), self.on_btn_exclude_file_clicked )
        
        self.btn_exclude_folder = KPushButton( KStandardGuiItem.add(), self )
        self.btn_exclude_folder.setText( QString.fromUtf8( _( 'Add folder' ) ) )
        buttons_layout.addWidget( self.btn_exclude_folder )
        QObject.connect( self.btn_exclude_folder, SIGNAL('clicked()'), self.on_btn_exclude_folder_clicked )
        
        self.btn_exclude_remove = KPushButton( KStandardGuiItem.remove(), self )
        buttons_layout.addWidget( self.btn_exclude_remove )
        QObject.connect( self.btn_exclude_remove, SIGNAL('clicked()'), self.on_btn_exclude_remove_clicked )

        #TAB: Auto-remove
        tab_widget = QWidget( self )
        self.tabs_widget.addTab( tab_widget, QString.fromUtf8( _( 'Auto-remove' ) ) )
        layout = QGridLayout( tab_widget )

        #remove old snapshots
        self.cb_remove_older_then = QCheckBox( QString.fromUtf8( _( 'Older than:' ) ), self )
        layout.addWidget( self.cb_remove_older_then, 0, 0 )
        QObject.connect( self.cb_remove_older_then, SIGNAL('stateChanged(int)'), self.update_remove_older_than )

        self.edit_remove_older_then = KIntSpinBox( 1, 1000, 1, 1, self )
        layout.addWidget( self.edit_remove_older_then, 0, 1 )

        self.combo_remove_older_then = KComboBox( self )
        layout.addWidget( self.combo_remove_older_then, 0, 2 )
        self.fill_combo( self.combo_remove_older_then, self.config.REMOVE_OLD_BACKUP_UNITS )

        #min free space
        enabled, value, unit = self.config.get_min_free_space()

        self.cb_min_free_space = QCheckBox( QString.fromUtf8( _( 'If free space is less than:' ) ), self )
        layout.addWidget( self.cb_min_free_space, 1, 0 )
        QObject.connect( self.cb_min_free_space, SIGNAL('stateChanged(int)'), self.update_min_free_space )

        self.edit_min_free_space = KIntSpinBox( 1, 1000, 1, 1, self )
        layout.addWidget( self.edit_min_free_space, 1, 1 )

        self.combo_min_free_space = KComboBox( self )
        layout.addWidget( self.combo_min_free_space, 1, 2 )
        self.fill_combo( self.combo_min_free_space, self.config.MIN_FREE_SPACE_UNITS )

        #smart remove
        self.cb_smart_remove = QCheckBox( QString.fromUtf8( _( 'Smart remove' ) ), self )
        layout.addWidget( self.cb_smart_remove, 2, 0 )

        #label = QLabel( QString.fromUtf8( _( '- keep all snapshots from today and yesterday\n- keep one snapshot for the last week and one for two weeks ago\n- keep one snapshot per month for all previous months of this year and all months of the last year \n- keep one snapshot per year for all other years' ) ),self )
        #label.setContentsMargins( 25, 0, 0, 0 )
        #layout.addWidget( label, 3, 0, 1, 3 )

        widget = QWidget( self )
        widget.setContentsMargins( 25, 0, 0, 0 )
        layout.addWidget( widget, 3, 0, 1, 3 )

        smlayout = QGridLayout( widget )

        smlayout.addWidget( QLabel( QString.fromUtf8( _( 'Keep all snapshots for the last' ) ), self ), 0, 0 )
        self.edit_keep_all = KIntSpinBox( 1, 10000, 1, 1, self )
        smlayout.addWidget( self.edit_keep_all, 0, 1 )
        smlayout.addWidget( QLabel( QString.fromUtf8( _( 'day(s)' ) ), self ), 0, 2 )

        smlayout.addWidget( QLabel( QString.fromUtf8( _( 'Keep one snapshot per day for the last' ) ), self ), 1, 0 )
        self.edit_keep_one_per_day = KIntSpinBox( 1, 10000, 1, 1, self )
        smlayout.addWidget( self.edit_keep_one_per_day, 1, 1 )
        smlayout.addWidget( QLabel( QString.fromUtf8( _( 'day(s)' ) ), self ), 1, 2 )

        smlayout.addWidget( QLabel( QString.fromUtf8( _( 'Keep one snapshot per week for the last' ) ), self ), 2, 0 )
        self.edit_keep_one_per_week = KIntSpinBox( 1, 10000, 1, 1, self )
        smlayout.addWidget( self.edit_keep_one_per_week, 2, 1 )
        smlayout.addWidget( QLabel( QString.fromUtf8( _( 'weeks(s)' ) ), self ), 2, 2 )

        smlayout.addWidget( QLabel( QString.fromUtf8( _( 'Keep one snapshot per month for the last' ) ), self ), 3, 0 )
        self.edit_keep_one_per_month = KIntSpinBox( 1, 10000, 1, 1, self )
        smlayout.addWidget( self.edit_keep_one_per_month, 3, 1 )
        smlayout.addWidget( QLabel( QString.fromUtf8( _( 'month(s)' ) ), self ), 3, 2 )

        smlayout.addWidget( QLabel( QString.fromUtf8( _( 'Keep one snapshot per year for all years' ) ), self ), 4, 0, 1, 3 )

        #don't remove named snapshots
        self.cb_dont_remove_named_snapshots = QCheckBox( QString.fromUtf8( _( 'Don\'t remove named snapshots' ) ), self )
        layout.addWidget( self.cb_dont_remove_named_snapshots, 4, 0, 1, 3 )

        #
        layout.addWidget( QWidget(), 5, 0 )
        layout.setRowStretch( 5, 2 )
        
        #TAB: Options
        tab_widget = QWidget( self )
        self.tabs_widget.addTab( tab_widget, QString.fromUtf8( _( 'Options' ) ) )
        layout = QVBoxLayout( tab_widget )

        self.cb_notify_enabled = QCheckBox( QString.fromUtf8( _( 'Enable notifications' ) ), self )
        layout.addWidget( self.cb_notify_enabled )

        self.cb_no_on_battery = QCheckBox( QString.fromUtf8( _( 'Disable snapshots when on battery' ) ), self )
        if not tools.power_status_available ():
            self.cb_no_on_battery.setEnabled ( False )
            self.cb_no_on_battery.setToolTip ( QString.fromUtf8 ( _( 'Power status not available from system' ) ) )
        layout.addWidget( self.cb_no_on_battery )

        self.cb_backup_on_restore = QCheckBox( QString.fromUtf8( _( 'Backup files on restore' ) ), self )
        layout.addWidget( self.cb_backup_on_restore )

        self.cb_continue_on_errors = QCheckBox( QString.fromUtf8( _( 'Continue on errors (keep incomplete snapshots)' ) ), self )
        layout.addWidget( self.cb_continue_on_errors )

        self.cb_use_checksum = QCheckBox( QString.fromUtf8( _( 'Use checksum to detect changes' ) ), self )
        layout.addWidget( self.cb_use_checksum )

        self.cb_full_rsync = QCheckBox( QString.fromUtf8( _( 'Full rsync mode. May be faster but snapshots are not read-only and destination filesystem must support hard-links, sym-links and all linux attributes.' ) ), self )
        QObject.connect( self.cb_full_rsync, SIGNAL('stateChanged(int)'), self.update_check_for_changes )
        layout.addWidget( self.cb_full_rsync)

        self.cb_check_for_changes = QCheckBox( QString.fromUtf8( _( 'Check for changes (don\'t take a new snapshot if nothing changed)' ) ), self )
        layout.addWidget( self.cb_check_for_changes )

        #log level
        hlayout = QHBoxLayout()
        layout.addLayout( hlayout )

        hlayout.addWidget( QLabel( QString.fromUtf8( _('Log Level:') ), self ) )

        self.combo_log_level = KComboBox( self )
        hlayout.addWidget( self.combo_log_level, 1 )
        
        self.combo_log_level.addItem( QIcon(), QString.fromUtf8( _('None') ), QVariant(0) )
        self.combo_log_level.addItem( QIcon(), QString.fromUtf8( _('Errors') ), QVariant(1) )
        self.combo_log_level.addItem( QIcon(), QString.fromUtf8( _('Changes & Errors') ), QVariant(2) )
        self.combo_log_level.addItem( QIcon(), QString.fromUtf8( _('All') ), QVariant(3) )

        #
        layout.addStretch()

        #TAB: Expert Options
        tab_widget = QWidget( self )
        self.tabs_widget.addTab( tab_widget, QString.fromUtf8( _( 'Expert Options' ) ) )
        layout = QVBoxLayout( tab_widget )

        label = QLabel( QString.fromUtf8( _('Change these options only if you really know what you are doing !') ), self )
        kde4tools.set_font_bold( label )
        layout.addWidget( label )

        #self.cb_per_diretory_schedule = QCheckBox( QString.fromUtf8( _( 'Enable schedule per included folder (see Include tab; default: disabled)' ) ), self )
        #layout.addWidget( self.cb_per_diretory_schedule )
        #QObject.connect( self.cb_per_diretory_schedule, SIGNAL('clicked()'), self.update_include_columns )

        self.cb_run_nice_from_cron = QCheckBox( QString.fromUtf8( _( 'Run \'nice\' as cron job (default: enabled)' ) ), self )
        layout.addWidget( self.cb_run_nice_from_cron )

        self.cb_run_ionice_from_cron = QCheckBox( QString.fromUtf8( _( 'Run \'ionice\' as cron job (default: enabled)' ) ), self )
        layout.addWidget( self.cb_run_ionice_from_cron )

        self.cb_run_ionice_from_user = QCheckBox( QString.fromUtf8( _( 'Run \'ionice\' when taking a manual snapshot (default: disabled)' ) ), self )
        layout.addWidget( self.cb_run_ionice_from_user )

        self.cb_preserve_acl = QCheckBox( QString.fromUtf8( _( 'Preserve ACL' ) ), self )
        layout.addWidget( self.cb_preserve_acl )

        self.cb_preserve_xattr = QCheckBox( QString.fromUtf8( _( 'Preserve extended attributes (xattr)' ) ), self )
        layout.addWidget( self.cb_preserve_xattr )

        self.cb_copy_unsafe_links = QCheckBox( QString.fromUtf8( _( 'Copy unsafe links (works only with absolute links)' ) ), self )
        layout.addWidget( self.cb_copy_unsafe_links )

        self.cb_copy_links = QCheckBox( QString.fromUtf8( _( 'Copy links (dereference symbolic links)' ) ), self )
        layout.addWidget( self.cb_copy_links )

        #
        layout.addStretch()

        self.update_profiles()

    def add_profile( self ):
        ret_val = KInputDialog.getText( QString.fromUtf8( _( 'New profile' ) ), '', '', self )
        if not ret_val[1]:
            return

        name = str( ret_val[0].toUtf8() ).strip()
        if len( name ) <= 0:
            return

        profile_id = self.config.add_profile( name )
        if profile_id is None:
            return

        self.config.set_current_profile( profile_id )
        self.update_profiles()

    def edit_profile( self ):
        ret_val = KInputDialog.getText( QString.fromUtf8( _( 'Rename profile' ) ), '', '', self )
        if not ret_val[1]:
            return

        name = str( ret_val[0].toUtf8() ).strip()
        if len( name ) <= 0:
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

    def current_automatic_snapshot_changed( self, index ):
        backup_mode = self.combo_automatic_snapshots.itemData( index ).toInt()[0]
        self.update_automatic_snapshot_time( backup_mode )

    def current_profile_changed( self, index ):
        if self.disable_profile_changed:
            return

        profile_id = str( self.combo_profiles.itemData( index ).toString().toUtf8() )
        if len( profile_id ) <= 0:
            return
        
        if profile_id != self.config.get_current_profile():
            self.save_profile()
            self.config.set_current_profile( profile_id )
            self.update_profile()

    def update_host_user_profile( self ):
        enabled = not self.cb_auto_host_user_profile.isChecked()
        self.lbl_host.setEnabled( enabled )
        self.txt_host.setEnabled( enabled )
        self.lbl_user.setEnabled( enabled )
        self.txt_user.setEnabled( enabled )
        self.lbl_profile.setEnabled( enabled )
        self.txt_profile.setEnabled( enabled )

    def update_password_save( self ):
        enabled = self.cb_password_save.isChecked()
        if enabled and tools.check_home_encrypt():
            enabled = False
        self.cb_password_use_cache.setEnabled( enabled )

    def update_check_for_changes(self):
        enabled = not self.cb_full_rsync.isChecked()
        self.cb_check_for_changes.setEnabled( enabled )

    def update_profiles( self ):
        self.update_profile()
        current_profile_id = self.config.get_current_profile()

        self.disable_profile_changed = True

        self.combo_profiles.clear()
            
        profiles = self.config.get_profiles_sorted_by_name()
        for profile_id in profiles:
            self.combo_profiles.addItem( QString.fromUtf8( self.config.get_profile_name( profile_id ) ), QVariant( QString.fromUtf8( profile_id ) ) )
            if profile_id == current_profile_id:
                self.combo_profiles.setCurrentIndex( self.combo_profiles.count() - 1 )

        self.disable_profile_changed = False

    def update_profile( self ):
        if self.config.get_current_profile() == '1':
            self.btn_edit_profile.setEnabled( False )
            self.btn_remove_profile.setEnabled( False )
        else:
            self.btn_edit_profile.setEnabled( True )
            self.btn_remove_profile.setEnabled( True )

        #TAB: General
        #mode
        self.set_combo_value( self.combo_modes, self.config.get_snapshots_mode(), type = 'str' )
        
        #local
        self.edit_snapshots_path.setText( QString.fromUtf8( self.config.get_snapshots_path( mode = 'local') ) )
        
        #ssh
        self.txt_ssh_host.setText( QString.fromUtf8( self.config.get_ssh_host() ) )
        self.txt_ssh_port.setText( QString.fromUtf8( str(self.config.get_ssh_port()) ) )
        self.txt_ssh_user.setText( QString.fromUtf8( self.config.get_ssh_user() ) )
        self.txt_ssh_path.setText( QString.fromUtf8( self.config.get_snapshots_path_ssh() ) )
        self.set_combo_value( self.combo_ssh_cipher, self.config.get_ssh_cipher(), type = 'str' )
        self.txt_ssh_private_key_file.setText( QString.fromUtf8( self.config.get_ssh_private_key_file() ) )
        
##		#dummy
##		self.txt_dummy_host.setText( QString.fromUtf8( self.config.get_dummy_host() ) )
##		self.txt_dummy_port.setText( QString.fromUtf8( self.config.get_dummy_port() ) )
##		self.txt_dummy_user.setText( QString.fromUtf8( self.config.get_dummy_user() ) )

        #password
        password = self.config.get_password( mode = self.mode, only_from_keyring = True )
        if password is None:
            password = ''
        self.txt_password.setText( QString.fromUtf8( password ) )
        self.cb_password_save.setChecked( self.config.get_password_save( mode = self.mode ) )
        self.cb_password_use_cache.setChecked( self.config.get_password_use_cache( mode = self.mode ) )
        self.update_password_save()

        self.cb_auto_host_user_profile.setChecked( self.config.get_auto_host_user_profile() )
        host, user, profile = self.config.get_host_user_profile()
        self.txt_host.setText( QString.fromUtf8( host ) )
        self.txt_user.setText( QString.fromUtf8( user ) )
        self.txt_profile.setText( QString.fromUtf8( profile ) )
        self.update_host_user_profile()

        self.set_combo_value( self.combo_automatic_snapshots, self.config.get_automatic_backup_mode() )
        self.set_combo_value( self.combo_automatic_snapshots_time, self.config.get_automatic_backup_time() )
        self.set_combo_value( self.combo_automatic_snapshots_day, self.config.get_automatic_backup_day() )
        self.set_combo_value( self.combo_automatic_snapshots_weekday, self.config.get_automatic_backup_weekday() )
        self.txt_automatic_snapshots_time_custom.setText( self.config.get_custom_backup_time() )
        self.update_automatic_snapshot_time( self.config.get_automatic_backup_mode() )

        #TAB: Include
        self.list_include.clear()

        for include in self.config.get_include():
            self.add_include( include )

        #TAB: Exclude
        self.list_exclude.clear()
    
        for exclude in self.config.get_exclude():
            self.add_exclude( exclude )

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

        #smart remove
        smart_remove, keep_all, keep_one_per_day, keep_one_per_week, keep_one_per_month = self.config.get_smart_remove()
        self.cb_smart_remove.setChecked( smart_remove )
        self.edit_keep_all.setValue( keep_all )
        self.edit_keep_one_per_day.setValue( keep_one_per_day )
        self.edit_keep_one_per_week.setValue( keep_one_per_week )
        self.edit_keep_one_per_month.setValue( keep_one_per_month )

        #don't remove named snapshots
        self.cb_dont_remove_named_snapshots.setChecked( self.config.get_dont_remove_named_snapshots() )

        #TAB: Options
        self.cb_notify_enabled.setChecked( self.config.is_notify_enabled() )
        self.cb_backup_on_restore.setChecked( self.config.is_backup_on_restore_enabled() )
        self.cb_continue_on_errors.setChecked( self.config.continue_on_errors() )
        self.cb_use_checksum.setChecked( self.config.use_checksum() )
        self.cb_full_rsync.setChecked( self.config.full_rsync() )
        self.update_check_for_changes()
        self.cb_check_for_changes.setChecked( self.config.check_for_changes() )
        self.set_combo_value( self.combo_log_level, self.config.log_level() )

        #TAB: Expert Options
        #self.cb_per_diretory_schedule.setChecked( self.config.get_per_directory_schedule() )
        self.cb_run_nice_from_cron.setChecked( self.config.is_run_nice_from_cron_enabled() )
        self.cb_run_ionice_from_cron.setChecked( self.config.is_run_ionice_from_cron_enabled() )
        self.cb_run_ionice_from_user.setChecked( self.config.is_run_ionice_from_user_enabled() )
        self.cb_no_on_battery.setChecked( self.config.is_no_on_battery_enabled() )
        self.cb_preserve_acl.setChecked( self.config.preserve_acl() )
        self.cb_preserve_xattr.setChecked( self.config.preserve_xattr() )
        self.cb_copy_unsafe_links.setChecked( self.config.copy_unsafe_links() )
        self.cb_copy_links.setChecked( self.config.copy_links() )

        #update
        #self.update_include_columns()
        self.update_remove_older_than()
        self.update_min_free_space()

    def save_profile( self ):
        if self.combo_automatic_snapshots.itemData( self.combo_automatic_snapshots.currentIndex() ).toInt()[0] == self.config.CUSTOM_HOUR:
            if not tools.check_cron_pattern(str( self.txt_automatic_snapshots_time_custom.text().toUtf8() ) ):
                self.error_handler( _('Custom Hours can only be a comma seperate list of hours (e.g. 8,12,18,23) or */3 for periodic backups every 3 hours') )
                return False
            
        #mode
        mode = str( self.combo_modes.itemData( self.combo_modes.currentIndex() ).toString().toUtf8() )
        self.config.set_snapshots_mode( mode )
        mount_kwargs = {}
        
        #password
        password = str( self.txt_password.text().toUtf8() )
        
        #ssh
        ssh_host = str( self.txt_ssh_host.text().toUtf8() )
        ssh_port = str( self.txt_ssh_port.text().toUtf8() )
        ssh_user = str( self.txt_ssh_user.text().toUtf8() )
        ssh_path = str( self.txt_ssh_path.text().toUtf8() )
        ssh_cipher = str( self.combo_ssh_cipher.itemData( self.combo_ssh_cipher.currentIndex() ).toString().toUtf8() )
        ssh_private_key_file = str( self.txt_ssh_private_key_file.text().toUtf8() )
        if mode == 'ssh':
            mount_kwargs = {'host': ssh_host,
                            'port': int(ssh_port),
                            'user': ssh_user,
                            'path': ssh_path,
                            'cipher': ssh_cipher,
                            'private_key_file': ssh_private_key_file,
                            'password': password
                            }
            
##		#dummy
##		dummy_host = str( self.txt_dummy_host.text().toUtf8() )
##		dummy_port = str( self.txt_dummy_port.text().toUtf8() )
##		dummy_user = str( self.txt_dummy_user.text().toUtf8() )
##		if mode == 'dummy':
##			#values must have exactly the same Type (str, int or bool) 
##			#as they are set in config or you will run into false-positive
##			#HashCollision warnings
##			mount_kwargs = {'host': dummy_host,
##							'port': int(dummy_port),
##							'user': dummy_user,
##							'password': password
##							}
            
        if not self.config.SNAPSHOT_MODES[mode][0] is None:
            #pre_mount_check
            mnt = mount.Mount(cfg = self.config, tmp_mount = True)
            try:
                mnt.pre_mount_check(mode = mode, first_run = True, **mount_kwargs)
            except mount.MountException as ex:
                self.error_handler(str(ex))
                return False

            #okay, lets try to mount
            try:
                hash_id = mnt.mount(mode = mode, check = False, **mount_kwargs)
            except mount.MountException as ex:
                self.error_handler(str(ex))
                return False
        
        #snapshots path
        self.config.set_auto_host_user_profile( self.cb_auto_host_user_profile.isChecked() )
        self.config.set_host_user_profile(
                str( self.txt_host.text().toUtf8() ),
                str( self.txt_user.text().toUtf8() ),
                str( self.txt_profile.text().toUtf8() ) )
                
        if self.config.SNAPSHOT_MODES[mode][0] is None:
            snapshots_path = str( self.edit_snapshots_path.text().toUtf8() )
        else:
            snapshots_path = self.config.get_snapshots_path(mode = mode, tmp_mount = True)
            
        self.config.set_snapshots_path( snapshots_path, mode = mode )
        
        #save ssh
        self.config.set_ssh_host(ssh_host)
        self.config.set_ssh_port(ssh_port)
        self.config.set_ssh_user(ssh_user)
        self.config.set_snapshots_path_ssh(ssh_path)
        self.config.set_ssh_cipher(ssh_cipher)
        self.config.set_ssh_private_key_file(ssh_private_key_file)
        
##		#save dummy
##		self.config.set_dummy_host(dummy_host)
##		self.config.set_dummy_port(dummy_port)
##		self.config.set_dummy_user(dummy_user)

        #save password
        if self.cb_password_save.isChecked() and mode in self.config.SNAPSHOT_MODES_NEED_PASSWORD:
            if self.config.get_keyring_backend() == '':
                self.config.set_keyring_backend('kwallet')
            if self.config.get_keyring_backend() == 'gnomekeyring':
                if keyring.backend.GnomeKeyring().supported() == 1:
                    keyring.set_keyring(keyring.backend.GnomeKeyring())
                else:
                    self.config.set_keyring_backend('kwallet')
            if self.config.get_keyring_backend() == 'kwallet':
                if keyring.backend.KDEKWallet().supported() == 1:
                    keyring.set_keyring(keyring.backend.KDEKWallet())
                else:
                    #in Kubuntu keyring.backend.KDEKWallet is included in python-keyring
                    #but Debian uses an extra package for this: python-keyring-kwallet
                    self.error_handler( _('Can\'t connect to KWallet to save password. On Debian you need to install:\n\'apt-get install python-keyring-kwallet\''))
                    return False
        self.config.set_password_save(self.cb_password_save.isChecked(), mode = mode)
        self.config.set_password_use_cache(self.cb_password_use_cache.isChecked(), mode = mode)
        self.config.set_password(password, mode = mode)

        #include list 
        include_list = []
        for index in xrange( self.list_include.topLevelItemCount() ):
            item = self.list_include.topLevelItem( index )
            #include_list.append( [ str( item.text(0).toUtf8() ), item.data( 0, Qt.UserRole ).toInt()[0] ] )
            include_list.append( ( str( item.text(0).toUtf8() ), item.data( 0, Qt.UserRole ).toInt()[0] ) )
        
        self.config.set_include( include_list )

        #exclude patterns
        exclude_list = []
        for index in xrange( self.list_exclude.count() ):
            exclude_list.append( str( self.list_exclude.item( index ).text().toUtf8() ) )

        self.config.set_exclude( exclude_list )

        #schedule
        self.config.set_automatic_backup_mode( self.combo_automatic_snapshots.itemData( self.combo_automatic_snapshots.currentIndex() ).toInt()[0] )
        self.config.set_automatic_backup_time( self.combo_automatic_snapshots_time.itemData( self.combo_automatic_snapshots_time.currentIndex() ).toInt()[0] )
        self.config.set_automatic_backup_weekday( self.combo_automatic_snapshots_weekday.itemData( self.combo_automatic_snapshots_weekday.currentIndex() ).toInt()[0] )
        self.config.set_automatic_backup_day( self.combo_automatic_snapshots_day.itemData( self.combo_automatic_snapshots_day.currentIndex() ).toInt()[0] )
        self.config.set_custom_backup_time( str( self.txt_automatic_snapshots_time_custom.text().toUtf8() ) )

        #auto-remove
        self.config.set_remove_old_snapshots( 
                        self.cb_remove_older_then.isChecked(), 
                        self.edit_remove_older_then.value(),
                        self.combo_remove_older_then.itemData( self.combo_remove_older_then.currentIndex() ).toInt()[0] )
        self.config.set_min_free_space( 
                        self.cb_min_free_space.isChecked(), 
                        self.edit_min_free_space.value(),
                        self.combo_min_free_space.itemData( self.combo_min_free_space.currentIndex() ).toInt()[0] )
        self.config.set_dont_remove_named_snapshots( self.cb_dont_remove_named_snapshots.isChecked() )
        self.config.set_smart_remove( 
                        self.cb_smart_remove.isChecked(),
                        self.edit_keep_all.value(),
                        self.edit_keep_one_per_day.value(),
                        self.edit_keep_one_per_week.value(),
                        self.edit_keep_one_per_month.value() )

        #options
        self.config.set_notify_enabled( self.cb_notify_enabled.isChecked() )
        self.config.set_backup_on_restore( self.cb_backup_on_restore.isChecked() )
        self.config.set_continue_on_errors( self.cb_continue_on_errors.isChecked() )
        self.config.set_use_checksum( self.cb_use_checksum.isChecked() )
        self.config.set_full_rsync( self.cb_full_rsync.isChecked() )
        self.config.set_check_for_changes( self.cb_check_for_changes.isChecked() )
        self.config.set_log_level( self.combo_log_level.itemData( self.combo_log_level.currentIndex() ).toInt()[0] )

        #expert options
        #self.config.set_per_directory_schedule( self.cb_per_diretory_schedule.isChecked() )
        self.config.set_run_nice_from_cron_enabled( self.cb_run_nice_from_cron.isChecked() )
        self.config.set_run_ionice_from_cron_enabled( self.cb_run_ionice_from_cron.isChecked() )
        self.config.set_run_ionice_from_user_enabled( self.cb_run_ionice_from_user.isChecked() )
        self.config.set_no_on_battery_enabled( self.cb_no_on_battery.isChecked() )
        self.config.set_preserve_acl( self.cb_preserve_acl.isChecked() )
        self.config.set_preserve_xattr( self.cb_preserve_xattr.isChecked() )
        self.config.set_copy_unsafe_links( self.cb_copy_unsafe_links.isChecked() )
        self.config.set_copy_links( self.cb_copy_links.isChecked() )
        
        #umount
        if not self.config.SNAPSHOT_MODES[mode][0] is None:
            try:
                mnt.umount(hash_id = hash_id)
            except mount.MountException as ex:
                self.error_handler(str(ex))
                return False
        return True

    def error_handler( self, message ):
        KMessageBox.error( self, QString.fromUtf8( message ) )

    def question_handler( self, message ):
        return KMessageBox.Yes == KMessageBox.warningYesNo( self, QString.fromUtf8( message ) )

    def exec_( self ):
        self.config.set_question_handler( self.question_handler )
        self.config.set_error_handler( self.error_handler )
        ret_val = KDialog.exec_( self )
        self.config.clear_handlers()

        if ret_val != QDialog.Accepted:
            self.config.dict = self.config_copy_dict
            
        self.config.set_current_profile( self.current_profile_org )

        return ret_val

    def update_snapshots_location( self ):
        '''Update snapshot location dialog'''
        self.config.set_question_handler( self.question_handler )
        self.config.set_error_handler( self.error_handler )
        self.snapshots.update_snapshots_location()
    
    #def update_include_columns( self ):
    #	if self.cb_per_diretory_schedule.isChecked():
    #		self.list_include.showColumn( 1 )
    #		self.global_schedule_group_box.hide()
    #	else:
    #		self.list_include.hideColumn( 1 )
    #		self.global_schedule_group_box.show()

    #def on_list_include_item_activated( self, item, column ):
    #	if not self.cb_per_diretory_schedule.isChecked():
    #		return
    #	
    #	if item is None:
    #		return

    #	#if column != 1:
    #	#	return

    #	self.popup_automatic_backup.popup( QCursor.pos() )

    #def on_popup_automatic_backup( self ):
    #	print "ABC"

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
            item.setIcon( 0, KIcon('folder') )
        else:
            item.setIcon( 0, KIcon('text-plain') )

        item.setText( 0, QString.fromUtf8( data[0] ) )
        #item.setText( 0, QString.fromUtf8( data[0] ) )
        #item.setText( 1, QString.fromUtf8( self.config.AUTOMATIC_BACKUP_MODES[ data[1] ] ) )
        item.setData( 0, Qt.UserRole, QVariant( data[1] ) )
        self.list_include.addTopLevelItem( item )

        if self.list_include.currentItem() is None:
            self.list_include.setCurrentItem( item )

        return item

    def add_exclude( self, pattern ):
        item = QListWidgetItem( KIcon('edit-delete'), QString.fromUtf8( pattern ), self.list_exclude )

        if self.list_exclude.currentItem() is None:
            self.list_exclude.setCurrentItem( item )

        return item

    def fill_combo( self, combo, dict ):
        keys = dict.keys()
        keys.sort()

        for key in keys:
            combo.addItem( QIcon(), QString.fromUtf8( dict[ key ] ), QVariant( key ) )

    def set_combo_value( self, combo, value, type = 'int' ):
        for i in xrange( combo.count() ):
            if type == 'int' and value == combo.itemData( i ).toInt()[0]:
                combo.setCurrentIndex( i )
                break
            if type == 'str' and value == combo.itemData( i ).toString():
                combo.setCurrentIndex( i )
                break

    def validate( self ):
        if not self.save_profile():
            return False

        if not self.config.check_config():
            return False

        if not self.config.setup_cron():
            return False

        self.config.save()

        #start Password_Cache if not running
        daemon = password.Password_Cache(self.config)
        if not daemon.status():
            try:
                subprocess.check_call(['backintime', '--pw-cache', 'start'], stdout=open(os.devnull, 'w'))
            except subprocess.CalledProcessError:
                self.error_handler( _('start Password Cache failed') )

        return True

    def on_btn_exclude_remove_clicked ( self ):
        self.list_exclude.takeItem( self.list_exclude.currentRow() )

        if self.list_exclude.count() > 0:
            self.list_exclude.setCurrentItem( self.list_exclude.item(0) )

    def add_exclude_( self, pattern ):
        if len( pattern ) == 0:
            return

        for index in xrange( self.list_exclude.count() ):
            if pattern == self.list_exclude.item( index ).text().toUtf8():
                return

        self.add_exclude( pattern )
    
    def on_btn_exclude_add_clicked( self ):
        ret_val = KInputDialog.getText( QString.fromUtf8( _( 'Exclude pattern' ) ), '', '', self )
        if not ret_val[1]:
            return

        pattern = str( ret_val[0].toUtf8() ).strip()

        if len( pattern ) == 0:
            return

        if pattern.find( ':' ) >= 0:
            KMessageBox.error( self, QString.fromUtf8( _('Exclude patterns can\'t contain \':\' char !') ) )
            return
    
        self.add_exclude_( pattern )

    def on_btn_exclude_file_clicked( self ):
        path = str( KFileDialog.getOpenFileName( KUrl(), '', self, QString.fromUtf8( _( 'Exclude file' ) ) ).toUtf8() )
        self.add_exclude_( path )

    def on_btn_exclude_folder_clicked( self ):
        path = str( KFileDialog.getExistingDirectory( KUrl(), self, QString.fromUtf8( _( 'Exclude folder' ) ) ).toUtf8() )
        self.add_exclude_( path )

    def on_btn_include_remove_clicked ( self ):
        item = self.list_include.currentItem()
        if item is None:
            return

        index = self.list_include.indexOfTopLevelItem( item )
        if index < 0:
            return

        self.list_include.takeTopLevelItem( index )

        if self.list_include.topLevelItemCount() > 0:
            self.list_include.setCurrentItem( self.list_include.topLevelItem(0) )

    def on_btn_include_file_add_clicked( self ):
        path = str( KFileDialog.getOpenFileName( KUrl(), '', self, QString.fromUtf8( _( 'Include file' ) ) ).toUtf8() )
        if len( path ) == 0 :
            return

        path = self.config.prepare_path( path )

        for index in xrange( self.list_include.topLevelItemCount() ):
            if path == str( self.list_include.topLevelItem( index ).text( 0 ).toUtf8() ):
                return

        #self.add_include( [ path, self.config.NONE ] )
        self.add_include( ( path, 1 ) )

    def on_btn_include_add_clicked( self ):
        path = str( KFileDialog.getExistingDirectory( KUrl(), self, QString.fromUtf8( _( 'Include folder' ) ) ).toUtf8() )
        if len( path ) == 0 :
            return

        path = self.config.prepare_path( path )

        for index in xrange( self.list_include.topLevelItemCount() ):
            if path == str( self.list_include.topLevelItem( index ).text( 0 ).toUtf8() ):
                return

        #self.add_include( [ path, self.config.NONE ] )
        self.add_include( ( path, 0 ) )

    def on_btn_snapshots_path_clicked( self ):
        old_path = str( self.edit_snapshots_path.text().toUtf8() )

        path = str( KFileDialog.getExistingDirectory( KUrl( self.edit_snapshots_path.text() ), self, QString.fromUtf8( _( 'Where to save snapshots' ) ) ).toUtf8() )
        if len( path ) > 0 :
            if len( old_path ) > 0 and old_path != path:
                if not self.question_handler( _('Are you sure you want to change snapshots folder ?') ):
                    return
            self.edit_snapshots_path.setText( QString.fromUtf8( self.config.prepare_path( path ) ) )

    def on_btn_ssh_private_key_file_clicked( self ):
        old_file = str( self.txt_ssh_private_key_file.text().toUtf8() )

        if len(old_file) > 0:
            start_dir = KUrl( self.txt_ssh_private_key_file.text() )
        else:
            start_dir = KUrl( self.config.get_ssh_private_key_folder() )
        file = str( KFileDialog.getOpenFileName( start_dir, QString.fromUtf8(''), self, QString.fromUtf8( _( 'SSH private key' ) ) ).toUtf8() )
        if len( file ) > 0 :
            self.txt_ssh_private_key_file.setText( QString.fromUtf8( self.config.prepare_path( file ) ) )
        
    def on_combo_modes_changed(self, *params):
        if len(params) == 0:
            index = self.combo_modes.currentIndex()
        else:
            index = params[0]
        active_mode = str( self.combo_modes.itemData( index ).toString().toUtf8() )
        if active_mode != self.mode:
            for mode in self.config.SNAPSHOT_MODES.keys():
                if active_mode == mode:
                    getattr(self, 'mode_%s' % mode).show()
                else:
                    getattr(self, 'mode_%s' % mode).hide()
            self.mode = active_mode
        if active_mode in self.config.SNAPSHOT_MODES_NEED_PASSWORD:
            self.frame_password.show()
        else:
            self.frame_password.hide()
        
    def accept( self ):
        if self.validate():
            KDialog.accept( self )

