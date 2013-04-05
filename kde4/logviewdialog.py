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

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *

import config
import tools
import kde4tools


_=gettext.gettext


class LogViewDialog( KDialog ):
    def __init__( self, parent, snapshot_id = None ):
        KDialog.__init__( self, parent )
        self.setButtons(KDialog.Close)
        self.resize( 600, 500 )

        self.config = parent.config
        self.snapshots = parent.snapshots
        self.current_profile = self.config.get_current_profile()
        self.snapshot_id = snapshot_id
        self.enable_update = False

        self.setWindowIcon( KIcon( 'text-plain' ) )
        self.setCaption( QString.fromUtf8( _( 'Error Log View' ) ) )

        self.main_widget = QWidget( self )
        self.main_layout = QVBoxLayout( self.main_widget )
        self.setMainWidget( self.main_widget )

        layout = QHBoxLayout()
        self.main_layout.addLayout( layout )

        #profiles
        self.lbl_profiles = QLabel( QString.fromUtf8( _('Profile:') ), self )
        layout.addWidget( self.lbl_profiles )

        self.combo_profiles = KComboBox( self )
        layout.addWidget( self.combo_profiles, 1 )
        QObject.connect( self.combo_profiles, SIGNAL('currentIndexChanged(int)'), self.current_profile_changed )
        
        if self.snapshot_id is None:
            self.lbl_profiles.hide()
            self.combo_profiles.hide()

        #filter
        layout.addWidget( QLabel( QString.fromUtf8( _('Filter:') ), self ) )

        self.combo_filter = KComboBox( self )
        layout.addWidget( self.combo_filter, 1 )
        QObject.connect( self.combo_filter, SIGNAL('currentIndexChanged(int)'), self.current_filter_changed )
    
        self.combo_filter.addItem( QString.fromUtf8( _('All') ), QVariant( 0 ) )
        self.combo_filter.addItem( QString.fromUtf8( _('Errors') ), QVariant( 1 ) )
        set_active = True
        if self.snapshot_id is None or self.snapshots.is_snapshot_failed( self.snapshot_id ):
            self.combo_filter.setCurrentIndex( self.combo_filter.count() - 1 )
            set_active = False
        self.combo_filter.addItem( QString.fromUtf8( _('Changes') ), QVariant( 2 ) )
        if not self.snapshot_id is None and set_active:
            self.combo_filter.setCurrentIndex( self.combo_filter.count() - 1 )
        self.combo_filter.addItem( QString.fromUtf8( _('Informations') ), QVariant( 3 ) )

        #text view
        self.txt_log_view = KTextEdit( self )
        self.txt_log_view.setReadOnly( True)
        self.main_layout.addWidget( self.txt_log_view )

        #
        self.main_layout.addWidget( QLabel( QString.fromUtf8( _('[E] Error, [I] Information, [C] Change') ), self ) )

        self.update_profiles()

    def current_profile_changed( self, index ):
        self.update_log()

    def current_filter_changed( self, index ):
        self.update_log()

    def update_profiles( self ):
        current_profile_id = self.config.get_current_profile()

        self.combo_profiles.clear()
            
        profiles = self.config.get_profiles_sorted_by_name()
        for profile_id in profiles:
            self.combo_profiles.addItem( QString.fromUtf8( self.config.get_profile_name( profile_id ) ), QVariant( QString.fromUtf8( profile_id ) ) )
            if profile_id == current_profile_id:
                self.combo_profiles.setCurrentIndex( self.combo_profiles.count() - 1 )

        self.enable_update = True
        self.update_log()

        if len( profiles ) <= 1:
            self.lbl_profiles.setVisible( False )
            self.combo_profiles.setVisible( False )

    def update_log( self ):
        if not self.enable_update:
            return

        mode = self.combo_filter.itemData( self.combo_filter.currentIndex() ).toInt()[0]

        if self.snapshot_id is None:
            profile_id = str( self.combo_profiles.itemData( self.combo_profiles.currentIndex() ).toString().toUtf8() )
            self.txt_log_view.setPlainText( self.snapshots.get_take_snapshot_log( mode, profile_id ) )
        else:
            self.txt_log_view.setPlainText( self.snapshots.get_snapshot_log( self.snapshot_id, mode ) )


