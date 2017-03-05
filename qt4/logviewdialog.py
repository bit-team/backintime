#    Back In Time
#    Copyright (C) 2008-2017 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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


import gettext

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import encfstools


_=gettext.gettext


class LogViewDialog( QDialog ):
    def __init__( self, parent, snapshot_id = None ):
        super(LogViewDialog, self).__init__(parent)

        self.config = parent.config
        self.snapshots = parent.snapshots
        self.main_window = parent
        self.current_profile = self.config.get_current_profile()
        self.snapshot_id = snapshot_id
        self.enable_update = False
        self.decode = None

        w = self.config.get_int_value('qt4.logview.width', 800)
        h = self.config.get_int_value('qt4.logview.height', 500)
        self.resize(w, h)

        import icon
        self.setWindowIcon(icon.VIEW_SNAPSHOT_LOG)
        if self.snapshot_id is None:
            self.setWindowTitle(_('Last Log View'))
        else:
            self.setWindowTitle(_('Snapshot Log View'))

        self.main_layout = QVBoxLayout(self)

        layout = QHBoxLayout()
        self.main_layout.addLayout( layout )

        #profiles
        self.lbl_profiles = QLabel( _('Profile:'), self )
        layout.addWidget( self.lbl_profiles )

        self.combo_profiles = QComboBox( self )
        layout.addWidget( self.combo_profiles, 1 )
        QObject.connect( self.combo_profiles, SIGNAL('currentIndexChanged(int)'), self.current_profile_changed )

        #snapshots
        self.lbl_snapshots = QLabel(_('Snapshots') + ':', self)
        layout.addWidget(self.lbl_snapshots)
        self.combo_snapshots = QComboBox(self)
        layout.addWidget(self.combo_snapshots, 1)
        QObject.connect(self.combo_snapshots, SIGNAL('currentIndexChanged(int)'), self.current_snapshot_changed)

        if self.snapshot_id is None:
            self.lbl_snapshots.hide()
            self.combo_snapshots.hide()
        else:
            self.lbl_profiles.hide()
            self.combo_profiles.hide()

        #filter
        layout.addWidget( QLabel(_('Filter:')) )

        self.combo_filter = QComboBox( self )
        layout.addWidget( self.combo_filter, 1 )
        QObject.connect( self.combo_filter, SIGNAL('currentIndexChanged(int)'), self.current_filter_changed )

        self.combo_filter.addItem( _('All'), 0 )
        self.combo_filter.addItem(' + '.join((_('Errors'), _('Changes'))), 4)
        self.combo_filter.setCurrentIndex( self.combo_filter.count() - 1 )
        self.combo_filter.addItem( _('Errors'), 1 )
        self.combo_filter.addItem( _('Changes'), 2 )
        self.combo_filter.addItem( _('Informations'), 3 )

        #text view
        self.txt_log_view = QPlainTextEdit(self)
        self.txt_log_view.setReadOnly(True)
        self.txt_log_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.main_layout.addWidget( self.txt_log_view )

        #
        self.main_layout.addWidget( QLabel(_('[E] Error, [I] Information, [C] Change')) )

        #decode path
        self.cb_decode = QCheckBox( _('decode paths'), self )
        QObject.connect( self.cb_decode, SIGNAL('stateChanged(int)'), self.on_cb_decode )
        self.main_layout.addWidget(self.cb_decode)

        #buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.main_layout.addWidget(button_box)
        QObject.connect(button_box, SIGNAL('rejected()'), self.close)

        self.update_snapshots()
        self.update_cb_decode()
        self.update_profiles()

    def on_cb_decode(self):
        if self.cb_decode.isChecked():
            self.decode = encfstools.Decode(self.config)
        else:
            if not self.decode is None:
                self.decode.close()
            self.decode = None
        self.update_log()

    def current_profile_changed( self, index ):
        if not self.enable_update:
            return
        profile_id = str(self.combo_profiles.itemData(index))
        for idx in range(self.main_window.combo_profiles.count()):
            if self.main_window.combo_profiles.itemData(idx) == profile_id:
                self.main_window.combo_profiles.setCurrentIndex(idx)
                self.main_window.on_profile_changed(idx)
                break
        self.update_cb_decode()
        self.update_log()

    def current_snapshot_changed(self, index):
        if not self.enable_update:
            return
        self.snapshot_id = str(self.combo_snapshots.itemData(self.combo_snapshots.currentIndex()))
        self.update_log()

    def current_filter_changed( self, index ):
        self.update_log()

    def update_profiles( self ):
        current_profile_id = self.config.get_current_profile()

        self.combo_profiles.clear()

        profiles = self.config.get_profiles_sorted_by_name()
        for profile_id in profiles:
            self.combo_profiles.addItem( self.config.get_profile_name( profile_id ), profile_id )
            if profile_id == current_profile_id:
                self.combo_profiles.setCurrentIndex( self.combo_profiles.count() - 1 )

        self.enable_update = True
        self.update_log()

        if len( profiles ) <= 1:
            self.lbl_profiles.setVisible( False )
            self.combo_profiles.setVisible( False )

    def update_snapshots(self):
        self.combo_snapshots.clear()
        for snapshot in self.snapshots.get_snapshots_list():
            self.combo_snapshots.addItem(self.snapshots.get_snapshot_display_name(snapshot), snapshot)
            if snapshot == self.snapshot_id:
                self.combo_snapshots.setCurrentIndex(self.combo_snapshots.count() - 1)

    def update_cb_decode(self):
        if self.config.get_snapshots_mode() == 'ssh_encfs':
            self.cb_decode.show()
        else:
            self.cb_decode.hide()
            if self.cb_decode.isChecked():
                self.cb_decode.setChecked(False)

    def update_log( self ):
        if not self.enable_update:
            return

        mode = self.combo_filter.itemData( self.combo_filter.currentIndex() )

        if self.snapshot_id is None:
            self.txt_log_view.setPlainText(self.snapshots.get_take_snapshot_log(mode, self.get_selected_profile(), decode = self.decode) )
        else:
            self.txt_log_view.setPlainText(self.snapshots.get_snapshot_log(self.snapshot_id, mode, decode = self.decode) )

    def get_selected_profile(self):
        return str(self.combo_profiles.itemData(self.combo_profiles.currentIndex()) )

    def closeEvent(self, event):
        self.config.set_int_value('qt4.logview.width', self.width())
        self.config.set_int_value('qt4.logview.height', self.height())
        event.accept()
