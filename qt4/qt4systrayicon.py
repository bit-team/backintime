#    Back In Time
#    Copyright (C) 2008-2014 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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


import sys
import os
import time
import gettext
import subprocess

_=gettext.gettext

if not os.getenv( 'DISPLAY', '' ):
    os.putenv( 'DISPLAY', ':0.0' )

sys.path = [os.path.join( os.path.dirname( os.path.abspath( os.path.dirname( __file__ ) ) ), 'common' )] + sys.path

import backintime
import config
import tools
import logger
import snapshots
import progress

from PyQt4.QtCore import QObject, SIGNAL, QTimer
from PyQt4.QtGui import QApplication, QSystemTrayIcon, QIcon, QMenu, QProgressBar, QWidget, QRegion


class Qt4SysTrayIcon:
    def __init__( self ):
        self.snapshots = snapshots.Snapshots()
        self.config = self.snapshots.config

        if len( sys.argv ) > 1:
            try:
                profile_id = int( sys.argv[1] )
                self.config.set_current_profile( profile_id )
            except:
                pass

        self.qapp = QApplication(sys.argv)

        import icon
        self.icon = icon
        self.qapp.setWindowIcon(icon.BIT_LOGO)

        self.status_icon = QSystemTrayIcon(icon.BIT_LOGO)
        #self.status_icon.actionCollection().clear()
        self.contextMenu = QMenu()

        self.menuStatusMessage = self.contextMenu.addAction(_('Done'))
        self.menuProgress = self.contextMenu.addAction('')
        self.menuProgress.setVisible(False)
        self.contextMenu.addSeparator()
        self.startBIT = self.contextMenu.addAction(icon.BIT_LOGO, _('Start BackInTime'))
        QObject.connect(self.startBIT, SIGNAL('triggered()'), self.onStartBIT)
        self.status_icon.setContextMenu(self.contextMenu)

        self.pixmap = icon.BIT_LOGO.pixmap(24)
        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        self.progressBar.resize(24, 6)
        self.progressBar.render(self.pixmap, sourceRegion = QRegion(0, -14, 24, 6), flags = QWidget.RenderFlags(QWidget.DrawChildren))

        self.first_error = self.config.is_notify_enabled()
        self.popup = None
        self.last_message = None

        self.timer = QTimer()
        QObject.connect( self.timer, SIGNAL('timeout()'), self.update_info )

        self.ppid = os.getppid()

    def prepare_exit( self ):
        self.timer.stop()

        if not self.status_icon is None:
            self.status_icon.hide()
            self.status_icon = None

        if not self.popup is None:
            self.popup.deleteLater()
            self.popup = None

        self.qapp.processEvents()

    def run( self ):
        self.status_icon.show()
        self.timer.start( 500 )

        logger.info( "[qt4systrayicon] begin loop" )

        self.qapp.exec_()

        logger.info( "[qt4systrayicon] end loop" )

        self.prepare_exit()

    def update_info( self ):
        if not tools.is_process_alive( self.ppid ):
            self.prepare_exit()
            self.qapp.exit(0)
            return

        message = self.snapshots.get_take_snapshot_message()
        if message is None and self.last_message is None:
            message = ( 0, _('Working...') )

        if not message is None:
            if message != self.last_message:
                self.last_message = message
                self.menuStatusMessage.setText('\n'.join(tools.wrap_line(self.last_message[1],\
                                                                         size = 80,\
                                                                         delimiters = '',\
                                                                         new_line_indicator = '') \
                                                                        ))
                self.status_icon.setToolTip( self.last_message[1] )

        pg = progress.ProgressFile(self.config)
        if pg.isFileReadable():
            pg.load()
            percent = pg.get_int_value('percent')
            if percent != self.progressBar.value():
                self.progressBar.setValue(percent)
                self.progressBar.render(self.pixmap, sourceRegion = QRegion(0, -14, 24, 6), flags = QWidget.RenderFlags(QWidget.DrawChildren))
                self.status_icon.setIcon(QIcon(self.pixmap))

            self.menuProgress.setText(' | '.join(self.getMenuProgress(pg)) )
            self.menuProgress.setVisible(True)
        else:
            self.status_icon.setIcon(self.icon.BIT_LOGO)
            self.menuProgress.setVisible(False)


    def getMenuProgress(self, pg):
        d = (('sent',   _('Sent:')), \
             ('speed',  _('Speed:')),\
             ('eta',    _('ETA:')) )
        for key, txt in d:
            value = pg.get_str_value(key, '')
            if not value:
                continue
            yield txt + ' ' + value

    def onStartBIT(self):
        proc = subprocess.Popen(['backintime-qt4', '&'])

if __name__ == '__main__':
    Qt4SysTrayIcon().run()

