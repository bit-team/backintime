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


def restore( parent, snapshot_id, what, where = '' ):
    if where is None:
        where = str( KFileDialog.getExistingDirectory( KUrl(), parent, QString.fromUtf8( _( 'Restore to ...' ) ) ).toUtf8() )
        if len( where ) == 0 :
            return
        where = parent.config.prepare_path( where )

    RestoreDialog(parent, snapshot_id, what, where).exec_()


class RestoreDialog( KDialog ):
    def __init__( self, parent, snapshot_id, what, where = '' ):
        KDialog.__init__( self, parent )
        self.setButtons(KDialog.Close)
        self.resize( 600, 500 )

        self.config = parent.config
        self.current_profile = self.config.get_current_profile()
        self.snapshots = parent.snapshots
        self.snapshot_id = snapshot_id
        self.what = what
        self.where = where

        self.setWindowIcon( KIcon( 'text-plain' ) )
        self.setCaption( QString.fromUtf8( _( 'Restore' ) ) )

        self.main_widget = QWidget( self )
        self.main_layout = QVBoxLayout( self.main_widget )
        self.setMainWidget( self.main_widget )

        #text view
        self.txt_log_view = KTextEdit( self )
        self.txt_log_view.setReadOnly( True)
        self.main_layout.addWidget( self.txt_log_view )

        #
        self.enableButton(KDialog.Close, False)

    def callback(self, line, *params ):
        self.txt_log_view.append(QString(line))
        KApplication.processEvents()

    def exec_(self):
        self.show()
        KApplication.processEvents()
        self.snapshots.restore( self.snapshot_id, self.what, self.callback, self.where )
        self.enableButton(KDialog.Close, True)
        KDialog.exec_(self)


