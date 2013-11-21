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

import config
import tools
import qt4tools


_=gettext.gettext


def restore( parent, snapshot_id, what, where = '' ):
    if where is None:
        where = str( QFileDialog.getExistingDirectory( parent, QString.fromUtf8(_('Restore to ...')) ).toUtf8() )
        if len( where ) == 0 :
            return
        where = parent.config.prepare_path( where )

    RestoreDialog(parent, snapshot_id, what, where).exec_()


class RestoreDialog( QDialog ):
    def __init__( self, parent, snapshot_id, what, where = '' ):
        QDialog.__init__( self, parent )
        self.resize( 600, 500 )

        self.config = parent.config
        self.current_profile = self.config.get_current_profile()
        self.snapshots = parent.snapshots
        self.snapshot_id = snapshot_id
        self.what = what
        self.where = where
        import icon

        self.log_file = self.config.get_restore_log_file()
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

        self.setWindowIcon(icon.RESTORE_DIALOG)
        self.setWindowTitle( QString.fromUtf8( _( 'Restore' ) ) )

        self.main_layout = QVBoxLayout(self)

        #text view
        self.txt_log_view = QTextEdit( self )
        self.txt_log_view.setReadOnly( True)
        self.main_layout.addWidget( self.txt_log_view )

        #buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.main_layout.addWidget(button_box)
        self.btn_close = button_box.button(QDialogButtonBox.Close)
        QObject.connect(button_box, SIGNAL('rejected()'), self.close)

        self.btn_close.setEnabled(False)

    def callback(self, line, *params ):
        self.txt_log_view.append(QString.fromUtf8(line))
        QApplication.processEvents()
        with open(self.log_file, 'a') as log:
            log.write(line + '\n')

    def exec_(self):
        self.show()
        QApplication.processEvents()
        self.snapshots.restore( self.snapshot_id, self.what, self.callback, self.where )
        self.btn_close.setEnabled(True)
        QDialog.exec_(self)
