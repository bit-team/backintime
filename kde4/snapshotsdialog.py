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

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *

import config
import tools
import kde4tools
import restoredialog


_=gettext.gettext


class DiffOptionsDialog( KDialog ):
    def __init__( self, parent ):
        KDialog.__init__( self, parent )
        self.config = parent.config

        self.setWindowIcon( KIcon( 'configure' ) )
        self.setCaption( QString.fromUtf8( _( 'Diff Options' ) ) )

        self.main_widget = QWidget( self )
        self.main_layout = QGridLayout()
        self.main_widget.setLayout( self.main_layout )
        self.setMainWidget( self.main_widget )

        self.diff_cmd = self.config.get_str_value( 'kde4.diff.cmd', 'kompare' )
        self.diff_params = self.config.get_str_value( 'kde4.diff.params', '%1 %2' )

        self.main_layout.addWidget( QLabel( QString.fromUtf8( _( 'Command:' ) ) ), 0, 0 )
        self.edit_command = KLineEdit( self.diff_cmd, self )
        self.main_layout.addWidget( self.edit_command, 0, 1 )

        self.main_layout.addWidget( QLabel( QString.fromUtf8( _( 'Parameters:' ) ) ), 1, 0 )
        self.edit_params = KLineEdit( self.diff_params, self )
        self.main_layout.addWidget( self.edit_params, 1, 1 )

        self.main_layout.addWidget( QLabel( QString.fromUtf8( _( 'Use %1 and %2 for path parameters' ) ) ), 2, 1 )

    def accept( self ):
        diff_cmd = str( self.edit_command.text().toUtf8() )
        diff_params = str( self.edit_params.text().toUtf8() )

        if diff_cmd != self.diff_cmd or diff_params != self.diff_params:
            self.config.set_str_value( 'kde4.diff.cmd', diff_cmd )
            self.config.set_str_value( 'kde4.diff.params', diff_params )
            self.config.save()
        
        KDialog.accept( self )


class SnapshotsDialog( KDialog ):
    def __init__( self, parent, snapshot_id, path, icon ):
        KDialog.__init__( self, parent )
        self.config = parent.config
        self.snapshots = parent.snapshots
        self.snapshots_list = parent.snapshots_list
        self.kapp = parent.kapp

        self.snapshot_id = snapshot_id
        self.path = path 
        self.icon = icon

        self.setWindowIcon( KIcon( 'view-list-details' ) )
        self.setCaption( QString.fromUtf8( _( 'Snapshots' ) ) )

        #
        self.main_widget = QWidget( self )
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout( self.main_layout )
        self.setMainWidget( self.main_widget )

        #path
        self.edit_path = KLineEdit( self.path, self )
        self.edit_path.setReadOnly( True )
        self.main_layout.addWidget( self.edit_path )

        #toolbar
        self.toolbar = KToolBar( self )
        self.toolbar.setFloatable( False )
        self.main_layout.addWidget( self.toolbar )

        #toolbar restore
        menu_restore = QMenu()
        action = menu_restore.addAction( KIcon( 'document-revert' ), QString.fromUtf8( _('Restore') ) )
        QObject.connect( action, SIGNAL('triggered()'), self.restore_this )
        action = menu_restore.addAction( KIcon( 'document-revert' ), QString.fromUtf8( _('Restore to ...') ) )
        QObject.connect( action, SIGNAL('triggered()'), self.restore_this_to )

        self.btn_restore = self.toolbar.addAction( KIcon( 'document-revert' ), '' )
        self.btn_restore.setToolTip( QString.fromUtf8( _('Restore') ) )
        self.btn_restore.setMenu(menu_restore)
        QObject.connect( self.btn_restore, SIGNAL('triggered()'), self.restore_this )

        #btn delete
        self.btn_delete = self.toolbar.addAction(KIcon('edit-delete'),'')
        self.btn_delete.setToolTip(QString.fromUtf8(_('Delete')))
        QObject.connect(self.btn_delete, SIGNAL('triggered()'), self.on_btn_delete_clicked)

        #btn select_all
        self.btn_select_all = self.toolbar.addAction(KIcon('edit-select-all'),'')
        self.btn_select_all.setToolTip(QString.fromUtf8(_('Select All')))
        QObject.connect(self.btn_select_all, SIGNAL('triggered()'), self.on_btn_select_all_clicked)

        #list different snapshots only
        self.cb_only_different_snapshots = QCheckBox( QString.fromUtf8( _( 'List only different snapshots' ) ), self )
        self.main_layout.addWidget( self.cb_only_different_snapshots )
        QObject.connect( self.cb_only_different_snapshots, SIGNAL('stateChanged(int)'), self.cb_only_different_snapshots_changed )

        #list equal snapshots only
        layout = QHBoxLayout()
        self.main_layout.addLayout(layout)
        self.cb_only_equal_snapshots = QCheckBox(QString.fromUtf8(_('List only equal snapshots to: ')), self)
        QObject.connect(self.cb_only_equal_snapshots, SIGNAL('stateChanged(int)'), self.cb_only_equal_snapshots_changed)
        layout.addWidget(self.cb_only_equal_snapshots)

        self.combo_equal_to = KComboBox(self)
        QObject.connect(self.combo_equal_to, SIGNAL('currentIndexChanged(int)'), self.on_combo_equal_to_changed)
        self.combo_equal_to.setEnabled(False)
        layout.addWidget(self.combo_equal_to)

        #deep check
        self.cb_only_different_snapshots_deep_check = QCheckBox( QString.fromUtf8( _( 'Deep check (more accurate, but slow)' ) ), self )
        self.main_layout.addWidget( self.cb_only_different_snapshots_deep_check )
        QObject.connect( self.cb_only_different_snapshots_deep_check, SIGNAL('stateChanged(int)'), self.cb_only_different_snapshots_deep_check_changed )

        #snapshots list
        self.list_snapshots = KListWidget( self )
        self.list_snapshots.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.main_layout.addWidget( self.list_snapshots )
        QObject.connect( self.list_snapshots, SIGNAL('itemSelectionChanged()'), self.on_list_snapshots_changed )
        QObject.connect( self.list_snapshots, SIGNAL('itemActivated(QListWidgetItem*)'), self.on_list_snapshots_executed )

        #diff
        layout = QHBoxLayout()
        self.main_layout.addLayout( layout )

        self.btn_diff = KPushButton( QString.fromUtf8( _('Diff') ), self )
        layout.addWidget( self.btn_diff )
        QObject.connect( self.btn_diff, SIGNAL('clicked()'), self.on_btn_diff_clicked )

        self.combo_diff = KComboBox( self )
        layout.addWidget( self.combo_diff, 2 )

        #diff options
        self.setButtons( KDialog.ButtonCode( KDialog.Ok | KDialog.Cancel | KDialog.User1 ) )
        self.setButtonGuiItem( KDialog.User1, KGuiItem( QString.fromUtf8( _('Diff Options') ), KIcon( 'configure' ) ) )
        self.setButtonText( KDialog.Ok, QString.fromUtf8( _('Go To') ) )

        QObject.connect( self, SIGNAL('user1Clicked()'), self.on_btn_diff_options_clicked )

        self.setDefaultButton( KDialog.Ok )

        #
        self.cb_only_different_snapshots_deep_check.setEnabled( False )

        full_path = self.snapshots.get_snapshot_path_to( self.snapshot_id, self.path )
        if os.path.islink( full_path ):
            self.cb_only_different_snapshots_deep_check.hide()
        elif os.path.isdir( full_path ):
            self.cb_only_different_snapshots.hide()
            self.cb_only_equal_snapshots.hide()
            self.combo_equal_to.hide()
            self.cb_only_different_snapshots_deep_check.hide()

        #update list and combobox
        self.update_snapshots()
        self.update_combo_equal_to()

    def add_snapshot_( self, snapshot_id ):
        name = self.snapshots.get_snapshot_display_name( snapshot_id )

        #add to list
        item = QListWidgetItem( QString.fromUtf8( name ), self.list_snapshots )
        item.setData( Qt.UserRole, QVariant( snapshot_id ) )

        if self.list_snapshots.currentItem() is None:
            self.list_snapshots.setCurrentItem( item )

        #add to combo
        self.combo_diff.addItem( QString.fromUtf8( name ), QVariant( snapshot_id ) )

        if self.snapshot_id == snapshot_id:
            self.combo_diff.setCurrentIndex( self.combo_diff.count() - 1 )
        elif self.combo_diff.currentIndex() < 0:
            self.combo_diff.setCurrentIndex( 0 )

    def update_snapshots( self ):
        self.list_snapshots.clear()
        self.combo_diff.clear()

        combo_index = self.combo_equal_to.currentIndex()
        if self.cb_only_equal_snapshots.isChecked() and combo_index >= 0:
            equal_to_snapshot_id = str(self.combo_equal_to.itemData(combo_index).toString().toUtf8())
            equal_to = self.snapshots.get_snapshot_path_to(equal_to_snapshot_id, self.path)
        else:
            equal_to = False
        snapshots_filtered = self.snapshots.filter_for(self.snapshot_id, self.path, 
                                self.snapshots_list, 
                                self.cb_only_different_snapshots.isChecked(), 
                                self.cb_only_different_snapshots_deep_check.isChecked(),
                                equal_to)
        for snapshot_id in snapshots_filtered:
            self.add_snapshot_( snapshot_id )

        self.update_toolbar()

    def update_combo_equal_to(self):
        self.combo_equal_to.clear()
        snapshots_filtered = self.snapshots.filter_for(self.snapshot_id, self.path, self.snapshots_list)
        for snapshot_id in snapshots_filtered:
            name = self.snapshots.get_snapshot_display_name(snapshot_id)
            self.combo_equal_to.addItem(QString.fromUtf8(name), QVariant(snapshot_id))
            
            if snapshot_id == self.snapshot_id:
                self.combo_equal_to.setCurrentIndex(self.combo_equal_to.count() - 1)
            elif self.combo_equal_to.currentIndex() < 0:
                self.combo_equal_to.setCurrentIndex(0)

    def get_list_snapshot_id( self, multiSelection = False):
        if multiSelection:
            items = self.list_snapshots.selectedItems()
            _list = []
            for item in items:
                _list.append(str( item.data( Qt.UserRole ).toString().toUtf8() ))
            return _list

        item = self.list_snapshots.currentItem()
        if item is None:
            return ''
        return str( item.data( Qt.UserRole ).toString().toUtf8() )

    def cb_only_different_snapshots_changed( self ):
        enabled = self.cb_only_different_snapshots.isChecked()
        self.cb_only_equal_snapshots.setEnabled(not enabled)
        self.cb_only_different_snapshots_deep_check.setEnabled( enabled )

        self.update_snapshots()

    def cb_only_equal_snapshots_changed( self ):
        enabled = self.cb_only_equal_snapshots.isChecked()
        self.combo_equal_to.setEnabled(enabled)
        self.cb_only_different_snapshots.setEnabled(not enabled)
        self.cb_only_different_snapshots_deep_check.setEnabled( enabled )

        self.update_snapshots()

    def cb_only_different_snapshots_deep_check_changed( self ):
        self.update_snapshots()

    def update_toolbar( self ):
        snapshot_ids = self.get_list_snapshot_id(True)

        if len(snapshot_ids) <= 0:
            enable_restore = False
            enable_delete = False
        elif len(snapshot_ids) == 1:
            enable_restore = len( snapshot_ids[0] ) > 1
            enable_delete = len( snapshot_ids[0] ) > 1
        else:
            enable_restore = False
            enable_delete = True
            for snapshot_id in snapshot_ids:
                if len(snapshot_id) <= 1:
                    enable_delete = False

        self.btn_restore.setEnabled(enable_restore)
        self.btn_delete.setEnabled(enable_delete)

    def restore_this( self ):
        snapshot_id = self.get_list_snapshot_id()
        if len( snapshot_id ) > 1:
            restoredialog.restore( self, snapshot_id, self.path )

    def restore_this_to( self ):
        snapshot_id = self.get_list_snapshot_id()
        if len( snapshot_id ) > 1:
            restoredialog.restore( self, snapshot_id, self.path, None )

    def on_list_snapshots_changed( self ):
        self.update_toolbar()

    def on_list_snapshots_executed( self, item ):
        if self.kapp.keyboardModifiers() and Qt.ControlModifier:
            return

        snapshot_id = self.get_list_snapshot_id()
        if len( snapshot_id ) <= 0:
            return

        full_path = self.snapshots.get_snapshot_path_to( snapshot_id, self.path )
        if not os.path.exists( full_path ):
            return

        self.run = KRun( KUrl( full_path ), self, True )

    def on_btn_diff_clicked( self ):
        snapshot_id = self.get_list_snapshot_id()
        if len( snapshot_id ) <= 0:
            return

        combo_index = self.combo_diff.currentIndex()
        if combo_index < 0:
            return

        snapshot2_id = str( self.combo_diff.itemData( combo_index ).toString().toUtf8() )

        path1 = self.snapshots.get_snapshot_path_to( snapshot_id, self.path )
        path2 = self.snapshots.get_snapshot_path_to( snapshot2_id, self.path )

        #check if the 2 paths are different
        if path1 == path2:
            KMessageBox.error( self, QString.fromUtf8( _('You can\'t compare a snapshot to itself') ) )
            return

        diff_cmd = self.config.get_str_value( 'kde4.diff.cmd', 'kompare' )
        diff_params = self.config.get_str_value( 'kde4.diff.params', '%1 %2' )

        if not tools.check_command( diff_cmd ):
            KMessageBox.error( self, QString.fromUtf8( _('Command not found: %s') % diff_cmd ) )
            return

        params = diff_params
        params = params.replace( '%1', "\"%s\"" % path1 )
        params = params.replace( '%2', "\"%s\"" % path2 )

        cmd = diff_cmd + ' ' + params + ' &'
        os.system( cmd  )

    def on_btn_diff_options_clicked( self ):
        DiffOptionsDialog( self ).exec_()

    def on_combo_equal_to_changed(self, index):
        self.update_snapshots()

    def on_btn_delete_clicked(self):
        snapshot_ids = self.get_list_snapshot_id(True)
        if len(snapshot_ids) == 0:
            return
        elif len(snapshot_ids) == 1:
            msg = _('Do you really want to delete "%(file)s" in snapshot "%(snapshot_id)s?\n') \
                    % {'file' : self.path, 'snapshot_id' : snapshot_ids[0]}
        else:
            msg = _('Do you really want to delete "%(file)s" in %(count)d snapshots?\n') \
                    % {'file' : self.path, 'count' : len(snapshot_ids)}
        msg += _('WARNING: This can not be revoked!')
        if KMessageBox.Yes == KMessageBox.warningYesNo(self, QString.fromUtf8(msg)):
            for snapshot_id in snapshot_ids:
                self.snapshots.delete_path(snapshot_id, self.path)

            msg = _('Exclude "%s" from future snapshots?' % self.path)
            if KMessageBox.Yes == KMessageBox.warningYesNo(self, QString.fromUtf8(msg)):
                exclude = self.config.get_exclude()
                exclude.append(self.path)
                self.config.set_exclude(exclude)
            self.update_combo_equal_to()
            self.update_snapshots()

    def on_btn_select_all_clicked(self):
        '''select all expect 'Now' '''
        def iterAllItems(self):
            for i in range(self.count()):
                yield self.item(i)

        self.list_snapshots.clearSelection()
        for item in iterAllItems(self.list_snapshots):
            if len(str(item.data(Qt.UserRole).toString().toUtf8())) > 1:
                item.setSelected(True)

    def accept( self ):
        snapshot_id = self.get_list_snapshot_id()
        if len( snapshot_id ) >= 1:
            self.snapshot_id = snapshot_id
        KDialog.accept( self )

